import time
from machine import Pin, UART
import uasyncio as asyncio


class ModbusRTU:
    def __init__(self, uart_id=0, baudrate=9600, tx_pin=0, rx_pin=1, de_pin=2):
        self.uart = UART(uart_id, baudrate=baudrate, tx=Pin(tx_pin), rx=Pin(rx_pin))
        self.de_pin = Pin(de_pin, Pin.OUT)  # Direction Enable pin for RS485
        self.de_pin.value(0)  # Start in receive mode
        self.lock = asyncio.Lock()  # Prevent concurrent RTU requests

    def _calculate_crc(self, data):
        """Calculate Modbus CRC16"""
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc >>= 1
                    crc ^= 0xA001
                else:
                    crc >>= 1
        return crc.to_bytes(2, "little")

    def _send_request(self, frame):
        """Send Modbus RTU frame"""
        # Calculate and append CRC
        crc = self._calculate_crc(frame)
        complete_frame = frame + crc

        # Switch to transmit mode
        self.de_pin.value(1)
        time.sleep_ms(1)

        # Send frame
        self.uart.write(complete_frame)

        # Wait for transmission to complete
        time.sleep_ms(10)

        # Switch back to receive mode
        self.de_pin.value(0)
        time.sleep_ms(1)

        return complete_frame

    def _receive_response(self, expected_length=None, timeout=1000):
        """Receive Modbus RTU response"""
        start_time = time.ticks_ms()
        response = b""

        while time.ticks_diff(time.ticks_ms(), start_time) < timeout:
            if self.uart.any():
                response += self.uart.read()
                if len(response) >= 4:  # Minimum valid response
                    # Check if we have a complete frame
                    if len(response) >= 4:
                        expected_len = (
                            response[2] + 5 if response[1] in [1, 2, 3, 4] else 8
                        )
                        if len(response) >= expected_len:
                            break
            time.sleep_ms(10)

        if len(response) < 4:
            return None

        # Verify CRC
        data = response[:-2]
        received_crc = response[-2:]
        calculated_crc = self._calculate_crc(data)

        if received_crc != calculated_crc:
            return None

        return response

    async def read_holding_registers(self, slave_id, start_addr, count):
        """Read holding registers (Function Code 3)"""
        async with self.lock:
            frame = bytes(
                [
                    slave_id,
                    0x03,  # Function code
                    (start_addr >> 8) & 0xFF,
                    start_addr & 0xFF,
                    (count >> 8) & 0xFF,
                    count & 0xFF,
                ]
            )

            self._send_request(frame)
            response = self._receive_response()

            if response is None:
                return None

            if response[1] & 0x80:  # Error response
                return {"error": response[2]}

            # Parse data
            byte_count = response[2]
            data = response[3 : 3 + byte_count]
            registers = []

            for i in range(0, byte_count, 2):
                reg_val = (data[i] << 8) | data[i + 1]
                registers.append(reg_val)

            return registers

    async def write_single_register(self, slave_id, register_addr, value):
        """Write single register (Function Code 6)"""
        async with self.lock:
            frame = bytes(
                [
                    slave_id,
                    0x06,  # Function code
                    (register_addr >> 8) & 0xFF,
                    register_addr & 0xFF,
                    (value >> 8) & 0xFF,
                    value & 0xFF,
                ]
            )

            self._send_request(frame)
            response = self._receive_response()

            if response is None:
                return False

            if response[1] & 0x80:  # Error response
                return {"error": response[2]}

            return True

    async def read_input_registers(self, slave_id, start_addr, count):
        """Read input registers (Function Code 4)"""
        async with self.lock:
            frame = bytes(
                [
                    slave_id,
                    0x04,  # Function code
                    (start_addr >> 8) & 0xFF,
                    start_addr & 0xFF,
                    (count >> 8) & 0xFF,
                    count & 0xFF,
                ]
            )

            self._send_request(frame)
            response = self._receive_response()

            if response is None:
                return None

            if response[1] & 0x80:  # Error response
                return {"error": response[2]}

            # Parse data
            byte_count = response[2]
            data = response[3 : 3 + byte_count]
            registers = []

            for i in range(0, byte_count, 2):
                reg_val = (data[i] << 8) | data[i + 1]
                registers.append(reg_val)

            return registers

    async def write_multiple_registers(self, slave_id, start_addr, values):
        """Write multiple holding registers (Function Code 16)"""
        async with self.lock:
            count = len(values)
            byte_count = count * 2

            frame = bytes(
                [
                    slave_id,
                    0x10,  # Function code
                    (start_addr >> 8) & 0xFF,
                    start_addr & 0xFF,
                    (count >> 8) & 0xFF,
                    count & 0xFF,
                    byte_count,
                ]
            )

            # Add register values
            for value in values:
                frame += bytes([(value >> 8) & 0xFF, value & 0xFF])

            self._send_request(frame)
            response = self._receive_response()

            if response is None:
                return False

            if response[1] & 0x80:  # Error response
                return {"error": response[2]}

            return True

    async def read_coils(self, slave_id, start_addr, count):
        """Read coils (Function Code 1)"""
        async with self.lock:
            frame = bytes(
                [
                    slave_id,
                    0x01,  # Function code
                    (start_addr >> 8) & 0xFF,
                    start_addr & 0xFF,
                    (count >> 8) & 0xFF,
                    count & 0xFF,
                ]
            )

            self._send_request(frame)
            response = self._receive_response()

            if response is None:
                return None

            if response[1] & 0x80:  # Error response
                return {"error": response[2]}

            # Parse data
            byte_count = response[2]
            data = response[3 : 3 + byte_count]
            coils = []

            for byte_val in data:
                for bit in range(8):
                    if len(coils) < count:
                        coils.append(bool(byte_val & (1 << bit)))

            return coils[:count]

    async def read_discrete_inputs(self, slave_id, start_addr, count):
        """Read discrete inputs (Function Code 2)"""
        async with self.lock:
            frame = bytes(
                [
                    slave_id,
                    0x02,  # Function code
                    (start_addr >> 8) & 0xFF,
                    start_addr & 0xFF,
                    (count >> 8) & 0xFF,
                    count & 0xFF,
                ]
            )

            self._send_request(frame)
            response = self._receive_response()

            if response is None:
                return None

            if response[1] & 0x80:  # Error response
                return {"error": response[2]}

            # Parse data
            byte_count = response[2]
            data = response[3 : 3 + byte_count]
            inputs = []

            for byte_val in data:
                for bit in range(8):
                    if len(inputs) < count:
                        inputs.append(bool(byte_val & (1 << bit)))

            return inputs[:count]

    async def write_single_coil(self, slave_id, coil_addr, value):
        """Write single coil (Function Code 5)"""
        async with self.lock:
            coil_value = 0xFF00 if value else 0x0000
            frame = bytes(
                [
                    slave_id,
                    0x05,  # Function code
                    (coil_addr >> 8) & 0xFF,
                    coil_addr & 0xFF,
                    (coil_value >> 8) & 0xFF,
                    coil_value & 0xFF,
                ]
            )

            self._send_request(frame)
            response = self._receive_response()

            if response is None:
                return False

            if response[1] & 0x80:  # Error response
                return {"error": response[2]}

            return True

    async def write_multiple_coils(self, slave_id, start_addr, values):
        """Write multiple coils (Function Code 15)"""
        async with self.lock:
            count = len(values)
            byte_count = (count + 7) // 8  # Round up to nearest byte

            frame = bytes(
                [
                    slave_id,
                    0x0F,  # Function code
                    (start_addr >> 8) & 0xFF,
                    start_addr & 0xFF,
                    (count >> 8) & 0xFF,
                    count & 0xFF,
                    byte_count,
                ]
            )

            # Pack coil values into bytes
            coil_bytes = []
            for i in range(byte_count):
                byte_val = 0
                for bit in range(8):
                    coil_index = i * 8 + bit
                    if coil_index < count and values[coil_index]:
                        byte_val |= 1 << bit
                coil_bytes.append(byte_val)

            frame += bytes(coil_bytes)

            self._send_request(frame)
            response = self._receive_response()

            if response is None:
                return False

            if response[1] & 0x80:  # Error response
                return {"error": response[2]}

            return True
