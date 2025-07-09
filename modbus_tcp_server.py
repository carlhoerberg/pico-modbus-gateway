import socket
import struct
import uasyncio as asyncio


class ModbusTCPServer:
    def __init__(self, modbus_rtu, port=502):
        self.modbus_rtu = modbus_rtu
        self.port = port
        self.socket = None
        self.transaction_id = 0

    async def start(self):
        """Start the Modbus TCP server"""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(socket.getaddrinfo("0.0.0.0", self.port)[0][-1])
        self.socket.listen(5)
        self.socket.setblocking(False)

        print(f"Modbus TCP Server listening on port {self.port}")

        while True:
            try:
                client_socket, addr = self.socket.accept()
                print(f"Modbus TCP connection from {addr}")
                asyncio.create_task(self.handle_client(client_socket))
            except OSError:
                await asyncio.sleep(0.1)

    async def handle_client(self, client_socket):
        """Handle Modbus TCP client connection"""
        try:
            client_socket.setblocking(False)

            while True:
                try:
                    # Read MBAP header (7 bytes)
                    header = await self._read_exact(client_socket, 7)
                    if not header:
                        break

                    # Parse MBAP header
                    transaction_id, protocol_id, length, unit_id = struct.unpack(
                        ">HHHB", header
                    )

                    # Verify protocol ID (should be 0 for Modbus)
                    if protocol_id != 0:
                        print(f"Invalid protocol ID: {protocol_id}")
                        break

                    # Read PDU (length - 1 byte for unit_id)
                    pdu = await self._read_exact(client_socket, length - 1)
                    if not pdu:
                        break

                    # Process Modbus request
                    response_pdu = await self._process_modbus_request(unit_id, pdu)

                    if response_pdu:
                        # Create MBAP header for response
                        response_length = len(response_pdu) + 1  # +1 for unit_id
                        response_header = struct.pack(
                            ">HHHB", transaction_id, 0, response_length, unit_id
                        )

                        # Send response
                        full_response = response_header + response_pdu
                        await self._send_all(client_socket, full_response)

                except OSError:
                    break
                except Exception as e:
                    print(f"Error handling Modbus TCP request: {e}")
                    break

        finally:
            try:
                client_socket.close()
            except:
                pass

    async def _read_exact(self, sock, length):
        """Read exactly 'length' bytes from socket"""
        data = b""
        while len(data) < length:
            try:
                chunk = sock.recv(length - len(data))
                if not chunk:
                    return None
                data += chunk
            except OSError:
                await asyncio.sleep(0.01)
        return data

    async def _send_all(self, sock, data):
        """Send all data through socket"""
        total_sent = 0
        while total_sent < len(data):
            try:
                sent = sock.send(data[total_sent:])
                if sent == 0:
                    raise RuntimeError("Socket connection broken")
                total_sent += sent
            except OSError:
                await asyncio.sleep(0.01)

    async def _process_modbus_request(self, unit_id, pdu):
        """Process Modbus PDU and return response PDU"""
        if len(pdu) < 1:
            return bytes([0x80, 0x01])  # Illegal function

        function_code = pdu[0]

        try:
            if function_code == 0x03:  # Read Holding Registers
                return await self._handle_read_holding_registers(unit_id, pdu)
            elif function_code == 0x04:  # Read Input Registers
                return await self._handle_read_input_registers(unit_id, pdu)
            elif function_code == 0x06:  # Write Single Register
                return await self._handle_write_single_register(unit_id, pdu)
            elif function_code == 0x10:  # Write Multiple Registers
                return await self._handle_write_multiple_registers(unit_id, pdu)
            elif function_code == 0x01:  # Read Coils
                return await self._handle_read_coils(unit_id, pdu)
            elif function_code == 0x02:  # Read Discrete Inputs
                return await self._handle_read_discrete_inputs(unit_id, pdu)
            elif function_code == 0x05:  # Write Single Coil
                return await self._handle_write_single_coil(unit_id, pdu)
            elif function_code == 0x0F:  # Write Multiple Coils
                return await self._handle_write_multiple_coils(unit_id, pdu)
            else:
                return bytes([function_code | 0x80, 0x01])  # Illegal function

        except Exception as e:
            print(f"Error processing function {function_code}: {e}")
            return bytes([function_code | 0x80, 0x04])  # Server device failure

    async def _handle_read_holding_registers(self, unit_id, pdu):
        """Handle Read Holding Registers (0x03)"""
        if len(pdu) < 5:
            return bytes([0x83, 0x03])  # Illegal data value

        start_addr = struct.unpack(">H", pdu[1:3])[0]
        count = struct.unpack(">H", pdu[3:5])[0]

        # Forward to RTU
        result = await self.modbus_rtu.read_holding_registers(
            unit_id, start_addr, count
        )

        if result is None:
            return bytes([0x83, 0x04])  # Server device failure
        elif isinstance(result, dict) and "error" in result:
            return bytes([0x83, result["error"]])
        else:
            # Build response
            byte_count = len(result) * 2
            response = bytes([0x03, byte_count])
            for reg in result:
                response += struct.pack(">H", reg)
            return response

    async def _handle_read_input_registers(self, unit_id, pdu):
        """Handle Read Input Registers (0x04)"""
        if len(pdu) < 5:
            return bytes([0x84, 0x03])  # Illegal data value

        start_addr = struct.unpack(">H", pdu[1:3])[0]
        count = struct.unpack(">H", pdu[3:5])[0]

        # Forward to RTU
        result = await self.modbus_rtu.read_input_registers(unit_id, start_addr, count)

        if result is None:
            return bytes([0x84, 0x04])  # Server device failure
        elif isinstance(result, dict) and "error" in result:
            return bytes([0x84, result["error"]])
        else:
            # Build response
            byte_count = len(result) * 2
            response = bytes([0x04, byte_count])
            for reg in result:
                response += struct.pack(">H", reg)
            return response

    async def _handle_write_single_register(self, unit_id, pdu):
        """Handle Write Single Register (0x06)"""
        if len(pdu) < 5:
            return bytes([0x86, 0x03])  # Illegal data value

        register_addr = struct.unpack(">H", pdu[1:3])[0]
        value = struct.unpack(">H", pdu[3:5])[0]

        # Forward to RTU
        result = await self.modbus_rtu.write_single_register(
            unit_id, register_addr, value
        )

        if result is None:
            return bytes([0x86, 0x04])  # Server device failure
        elif isinstance(result, dict) and "error" in result:
            return bytes([0x86, result["error"]])
        else:
            # Echo back the request for successful write
            return pdu

    async def _handle_write_multiple_registers(self, unit_id, pdu):
        """Handle Write Multiple Holding Registers (0x10)"""
        if len(pdu) < 6:
            return bytes([0x90, 0x03])  # Illegal data value

        start_addr = struct.unpack(">H", pdu[1:3])[0]
        count = struct.unpack(">H", pdu[3:5])[0]
        byte_count = pdu[5]

        if len(pdu) < 6 + byte_count:
            return bytes([0x90, 0x03])  # Illegal data value

        if byte_count != count * 2:
            return bytes([0x90, 0x03])  # Illegal data value

        # Extract values
        values = []
        for i in range(0, byte_count, 2):
            value = struct.unpack(">H", pdu[6 + i : 6 + i + 2])[0]
            values.append(value)

        # Forward to RTU
        result = await self.modbus_rtu.write_multiple_registers(
            unit_id, start_addr, values
        )

        if result is None:
            return bytes([0x90, 0x04])  # Server device failure
        elif isinstance(result, dict) and "error" in result:
            return bytes([0x90, result["error"]])
        else:
            # Return start address and count for successful write
            return pdu[0:5]  # Function code + start address + count

    async def _handle_read_coils(self, unit_id, pdu):
        """Handle Read Coils (0x01)"""
        if len(pdu) < 5:
            return bytes([0x81, 0x03])  # Illegal data value

        start_addr = struct.unpack(">H", pdu[1:3])[0]
        count = struct.unpack(">H", pdu[3:5])[0]

        # Forward to RTU
        result = await self.modbus_rtu.read_coils(unit_id, start_addr, count)

        if result is None:
            return bytes([0x81, 0x04])  # Server device failure
        elif isinstance(result, dict) and "error" in result:
            return bytes([0x81, result["error"]])
        else:
            # Build response
            byte_count = (len(result) + 7) // 8
            response = bytes([0x01, byte_count])

            # Pack coils into bytes
            for i in range(byte_count):
                byte_val = 0
                for bit in range(8):
                    coil_index = i * 8 + bit
                    if coil_index < len(result) and result[coil_index]:
                        byte_val |= 1 << bit
                response += bytes([byte_val])

            return response

    async def _handle_read_discrete_inputs(self, unit_id, pdu):
        """Handle Read Discrete Inputs (0x02)"""
        if len(pdu) < 5:
            return bytes([0x82, 0x03])  # Illegal data value

        start_addr = struct.unpack(">H", pdu[1:3])[0]
        count = struct.unpack(">H", pdu[3:5])[0]

        # Forward to RTU
        result = await self.modbus_rtu.read_discrete_inputs(unit_id, start_addr, count)

        if result is None:
            return bytes([0x82, 0x04])  # Server device failure
        elif isinstance(result, dict) and "error" in result:
            return bytes([0x82, result["error"]])
        else:
            # Build response
            byte_count = (len(result) + 7) // 8
            response = bytes([0x02, byte_count])

            # Pack inputs into bytes
            for i in range(byte_count):
                byte_val = 0
                for bit in range(8):
                    input_index = i * 8 + bit
                    if input_index < len(result) and result[input_index]:
                        byte_val |= 1 << bit
                response += bytes([byte_val])

            return response

    async def _handle_write_single_coil(self, unit_id, pdu):
        """Handle Write Single Coil (0x05)"""
        if len(pdu) < 5:
            return bytes([0x85, 0x03])  # Illegal data value

        coil_addr = struct.unpack(">H", pdu[1:3])[0]
        coil_value = struct.unpack(">H", pdu[3:5])[0]

        # Convert coil value (0xFF00 = ON, 0x0000 = OFF)
        value = coil_value == 0xFF00

        # Forward to RTU
        result = await self.modbus_rtu.write_single_coil(unit_id, coil_addr, value)

        if result is None:
            return bytes([0x85, 0x04])  # Server device failure
        elif isinstance(result, dict) and "error" in result:
            return bytes([0x85, result["error"]])
        else:
            # Echo back the request for successful write
            return pdu

    async def _handle_write_multiple_coils(self, unit_id, pdu):
        """Handle Write Multiple Coils (0x0F)"""
        if len(pdu) < 6:
            return bytes([0x8F, 0x03])  # Illegal data value

        start_addr = struct.unpack(">H", pdu[1:3])[0]
        count = struct.unpack(">H", pdu[3:5])[0]
        byte_count = pdu[5]

        if len(pdu) < 6 + byte_count:
            return bytes([0x8F, 0x03])  # Illegal data value

        # Extract coil values
        values = []
        for i in range(byte_count):
            byte_val = pdu[6 + i]
            for bit in range(8):
                if len(values) < count:
                    values.append(bool(byte_val & (1 << bit)))

        # Forward to RTU
        result = await self.modbus_rtu.write_multiple_coils(unit_id, start_addr, values)

        if result is None:
            return bytes([0x8F, 0x04])  # Server device failure
        elif isinstance(result, dict) and "error" in result:
            return bytes([0x8F, result["error"]])
        else:
            # Return start address and count for successful write
            return pdu[0:5]  # Function code + start address + count
