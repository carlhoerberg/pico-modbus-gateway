import builtins
import time
import asyncio
import machine

# Store original print function
_original_print = builtins.print

# Ring buffer for last 10 messages
_message_buffer = []
_buffer_size = 16


def print(*args, **kwargs):
    """Override print to store in buffer and send to stdout"""
    # Always print to stdout first
    _original_print(*args, **kwargs)

    # Convert args to string (same as print does)
    sep = kwargs.get("sep", " ")
    message = sep.join(str(arg) for arg in args)

    # Add to ring buffer
    _add_to_buffer(message)


def _add_to_buffer(message):
    """Add message to ring buffer"""
    timestamp = time.time()
    # On hardware, time.time() gives seconds since boot
    formatted_msg = f"[{timestamp:.3f}] {message}\n"

    # Add to buffer (ring buffer behavior)
    _message_buffer.append(formatted_msg)
    if len(_message_buffer) > _buffer_size:
        _message_buffer.pop(0)


async def tcp_log_server(port=4132):
    """TCP server to send log buffer and handle reboot commands"""

    async def handle_client(reader, writer):
        try:
            # Send current log buffer immediately on connect
            for message in _message_buffer:
                writer.write(message.encode("utf-8"))
            await writer.drain()

            # Listen for commands
            data = await asyncio.wait_for(reader.readline(), timeout=10)
            if not data:
                return

            message = data.decode("utf-8").strip().lower()

            if message == "reboot":
                try:
                    _original_print("[INFO] Rebooting device...")
                    machine.reset()
                except AttributeError:
                    raise SystemExit("Rebooting device...")

        except Exception as e:
            _original_print(f"[DEBUG] TCP log client error: {e} ({type(e).__name__})")
        finally:
            writer.close()
            await writer.wait_closed()

    server = await asyncio.start_server(handle_client, "0.0.0.0", port)
    _original_print(f"[DEBUG] TCP log server listening on port {port}")
    return server


# Override the built-in print
builtins.print = print
