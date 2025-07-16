# Pico Modbus Gateway

A Modbus TCP to RTU gateway implementation for Raspberry Pi Pico (or compatible microcontrollers) using MicroPython. This gateway allows TCP/IP clients and HTTP clients to communicate with Modbus RTU devices over RS485.

## Features

- **Modbus TCP Server** on port 502
- **HTTP Web Interface** on port 80 for testing and configuration
- **HTTP API** - Full Modbus functionality available via REST endpoints
- **Modbus RTU Client** via RS485/UART
- **Web-based Configuration** - WiFi and ModbusRTU settings configurable via web interface
- **OTA Updates** - Over-the-air firmware updates from GitHub
- **Concurrent Operation** - handles multiple TCP and HTTP connections simultaneously
- **Thread Safety** - prevents RTU request intermingling using async locks

## Supported Modbus Functions

### Data Access Functions
- **Function Code 01**: Read Coils
- **Function Code 02**: Read Discrete Inputs
- **Function Code 03**: Read Holding Registers
- **Function Code 04**: Read Input Registers
- **Function Code 05**: Write Single Coil
- **Function Code 06**: Write Single Register
- **Function Code 15**: Write Multiple Coils
- **Function Code 16**: Write Multiple Holding Registers

All standard Modbus data access functions are supported with proper bit packing/unpacking for coil operations and comprehensive error handling.

## Hardware Requirements

- Raspberry Pi Pico W (or compatible MicroPython board with WiFi)
- WaveShare Pico-2CH-RS485 HAT (or compatible RS485 module)
- WiFi connectivity

## Pin Configuration

Fixed pin assignments for WaveShare Pico-2CH-RS485 HAT:
- **UART0**: TX=GP0, RX=GP1 (Channel 0)
- **UART1**: TX=GP4, RX=GP5 (Channel 1)
- **Direction Control**: Automatic (no DE pin required)
- **Serial Settings**: Configurable via web interface

## Installation

### Hardware Deployment

1. Flash MicroPython firmware to your Pico W
2. Copy all Python files to the Pico's filesystem:
   - `main.py`
   - `config.py`
   - `http_server.py`
   - `modbus_rtu.py`
   - `modbus_tcp_server.py`
   - `ota_updater.py`
   - `index.html`
3. Update WiFi credentials in `config.py`:
   ```python
   WIFI_SSID = "YOUR_WIFI_SSID"
   WIFI_PASSWORD = "YOUR_WIFI_PASSWORD"
   ```
4. Reset the Pico to start the gateway

### Local Testing

For development and testing without hardware:

1. Install MicroPython on your local machine
2. Clone/download this repository
3. Run main.py directly:
   ```bash
   micropython main.py
   ```

**Local test mode features:**
- HTTP server on `http://127.0.0.1:80`
- Web interface for API testing
- ModbusTCP server simulation
- Configuration interface (simulated)

**Disabled in local mode:**
- WiFi connection
- UART/RS485 communication
- OTA updates
- Device restart

**Note:** Some versions of MicroPython may have socket compatibility issues that prevent the servers from starting locally. The code is designed to work correctly on MicroPython running on actual Pico hardware. If you encounter socket-related errors during local testing, this is a limitation of the local MicroPython environment.

## Usage

### Web Interface

Access `http://[PICO_IP_ADDRESS]` to use the web-based interface:

#### Modbus Testing
- Select Modbus function (Read Coils/Discrete Inputs/Registers, Write Coils/Registers)
- Set slave ID, start address, and count/values
- For coil operations: use boolean values (1/0, true/false, on/off)
- Execute requests and view responses

#### Configuration Management
- **WiFi Configuration**: Update SSID and password (device restarts automatically)
- **ModbusRTU Configuration**: 
  - UART ID selection (0 or 1)
  - Baudrate (1200-115200)
  - Parity (None, Odd, Even)
  - Stop bits (1 or 2)
  - Pin assignments shown automatically

### Modbus TCP Client

Connect to port 502 on the Pico's IP address using any Modbus TCP client:
```python
# Example using pymodbus
from pymodbus.client.sync import ModbusTcpClient

client = ModbusTcpClient('192.168.1.100', port=502)
result = client.read_holding_registers(0, 10, unit=1)
```

### HTTP API

Direct API access for programmatic control:

#### Read Functions
```
GET /api/read_coils?slave_id=1&start_addr=0&count=10
GET /api/read_discrete?slave_id=1&start_addr=0&count=10
GET /api/read_holding?slave_id=1&start_addr=0&count=10
GET /api/read_input?slave_id=1&start_addr=0&count=10
```

#### Write Functions
```
GET /api/write_coil?slave_id=1&start_addr=0&value=1
GET /api/write_single?slave_id=1&start_addr=0&value=1234
GET /api/write_coils?slave_id=1&start_addr=0&values=1,0,1,0,1
GET /api/write_multiple?slave_id=1&start_addr=0&values=1,2,3,4,5
```

#### Configuration API
```
GET /api/wifi_config?ssid=NetworkName&password=Password123
GET /api/modbus_config?uart_id=0&baudrate=9600&parity=0&stop_bits=1
GET /api/ota_update?force=false
```

**Note**: For coil operations, use boolean values: `1/0`, `true/false`, `on/off`, `yes/no`

## API Response Format

All API responses return JSON:

**Read Operations**:
```json
{
  "success": true,
  "data": [1, 2, 3, 4, 5]
}
```

**Coil Read Operations**:
```json
{
  "success": true,
  "data": [true, false, true, false, true]
}
```

**Write Operations**:
```json
{
  "success": true,
  "message": "Register written successfully"
}
```

**Error Responses**:
```json
{
  "success": false,
  "error": "Communication timeout"
}
```

## Configuration

All configuration can be done via the web interface or by editing `config.py`:

### WiFi Settings
```python
WIFI_SSID = "your_network_name"
WIFI_PASSWORD = "your_password"
```

### ModbusRTU Settings
```python
UART_ID = 0          # 0 or 1 (selects pin assignment)
BAUDRATE = 9600      # 1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200
PARITY = 0           # 0=None, 1=Odd, 2=Even
STOP_BITS = 1        # 1 or 2
```

Pin assignments are automatic based on UART_ID:
- UART0: TX=GP0, RX=GP1
- UART1: TX=GP4, RX=GP5

### Server Ports
- HTTP Server: Port 80 (configurable)
- Modbus TCP Server: Port 502 (standard)

## Architecture

### Classes

- **ModbusRTU**: Handles RTU protocol communication over UART/RS485
- **ModbusTCPServer**: Implements Modbus TCP server on port 502
- **HTTPServer**: Provides web interface and REST API on port 80

### Async Operation

The gateway uses `asyncio` for concurrent operation:
- Both servers run simultaneously using `asyncio.gather()`
- RTU requests are serialized using `asyncio.Lock()` to prevent interference
- Non-blocking socket operations with proper error handling

### Protocol Translation

TCP requests are translated to RTU:
1. Parse Modbus TCP MBAP header
2. Extract PDU (Protocol Data Unit)
3. Forward to RTU device via RS485
4. Translate response back to TCP format

## Error Handling

- **Communication Timeouts**: 1-second timeout for RTU responses
- **CRC Validation**: Automatic CRC calculation and verification
- **Modbus Exceptions**: Proper error code translation
- **Connection Management**: Automatic cleanup of failed connections

## Development

### Adding New Functions

To add support for additional Modbus function codes:

1. Add handler in `ModbusRTU` class
2. Add TCP handler in `ModbusTCPServer._process_modbus_request()`
3. Add HTTP API endpoint in `HTTPServer.handle_api()`
4. Update web interface if needed

### Debugging

Enable debug output by adding print statements or use the web interface to test individual requests.

## License

MIT License

Copyright (c) 2024 Carl Hörberg

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
