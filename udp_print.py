import builtins
import socket

# UDP socket for logging
_udp_socket = None
_server_ip = "192.168.0.2"
_server_port = 4138

# Store original print function
_original_print = builtins.print


def _init_udp():
    """Initialize UDP socket for logging"""
    global _udp_socket

    try:
        _udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        _udp_socket.connect(socket.getaddrinfo(_server_ip, _server_port)[0][-1])
        _original_print(
            f"[DEBUG] UDP logging enabled - sending to {_server_ip}:{_server_port}"
        )
    except Exception as e:
        _original_print(f"[WARNING] Failed to create UDP socket: {e}")


def print(*args, **kwargs):
    """Override print to send to both stdout and UDP"""
    # Always print to stdout first
    _original_print(*args, **kwargs)

    # Send to UDP if enabled
    if _udp_socket:
        try:
            # Convert args to string (same as print does)
            sep = kwargs.get("sep", " ")
            message = sep.join(str(arg) for arg in args)

            # Send UDP packet with newline
            _udp_socket.write((message + "\n").encode("utf-8"))
        except Exception as e:
            # Don't print UDP errors to avoid recursion, just fail silently
            pass


# Initialize UDP logging when module is imported
_init_udp()

# Override the built-in print
builtins.print = print
