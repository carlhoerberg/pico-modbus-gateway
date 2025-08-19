# Override print and start debug server
import debug_server

try:
    import network

    RUNNING_ON_HARDWARE = True
except ImportError:
    RUNNING_ON_HARDWARE = False
    print("[INFO] Running in local test mode - hardware features disabled")

import time
import asyncio
from modbus_rtu import ModbusRTU
from modbus_tcp_server import ModbusTCPServer
from http_server import HTTPServer
from config import WIFI_SSID, WIFI_PASSWORD, UART_ID, BAUDRATE, PARITY, STOP_BITS
from ota_updater import OTAUpdater


# WiFi connection
def connect_wifi(ssid, password):
    """Connect to WiFi network - retry forever until successful (hardware only)"""
    if not RUNNING_ON_HARDWARE:
        print(f"[INFO] Local test mode - simulating WiFi connection to {ssid}")
        return True

    print(f"[DEBUG] Initializing WiFi connection to SSID: {ssid}")
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    print(f"[DEBUG] WiFi interface activated")

    while True:
        print(f"[DEBUG] Attempting to connect to {ssid}...")
        wlan.connect(ssid, password)
        print(f"[DEBUG] Connection request sent to {ssid}")

        print("Connecting to WiFi...")
        # Wait for connection attempt (up to 15 seconds)
        wait_time = 15
        while wait_time > 0:
            status = wlan.status()
            if status < 0 or status >= 3:
                break
            wait_time -= 1
            print(f"[DEBUG] Connection status: {status}, waiting: {wait_time}s")
            time.sleep(1)

        status = wlan.status()
        if status == 3:
            print("[INFO] Connected to WiFi!")
            ifconfig = wlan.ifconfig()
            print(f"[DEBUG] Network configuration:")
            print(f"[DEBUG]   IP Address: {ifconfig[0]}")
            print(f"[DEBUG]   Subnet Mask: {ifconfig[1]}")
            print(f"[DEBUG]   Gateway: {ifconfig[2]}")
            print(f"[DEBUG]   DNS Server: {ifconfig[3]}")
            return True
        else:
            print(f"[WARNING] Failed to connect to WiFi. Status: {status}")
            status_messages = {
                0: "Link down",
                1: "Link join",
                2: "Link no IP",
                -1: "Link fail",
                -2: "No AP found",
                -3: "Wrong password",
            }
            print(
                f"[WARNING] Status meaning: {status_messages.get(status, 'Unknown status')}"
            )
            print("[INFO] Retrying in 5 seconds...")
            time.sleep(5)


# Main application
async def main():
    """Main application"""
    # Connect to WiFi (will retry forever until successful)
    print("[DEBUG] Starting WiFi connection...")
    connect_wifi(WIFI_SSID, WIFI_PASSWORD)

    # Check for OTA updates (hardware only)
    if RUNNING_ON_HARDWARE:
        print("[DEBUG] Checking for OTA updates...")
        ota_updater = OTAUpdater("carlhoerberg/pico-modbus-gateway")
        try:
            await ota_updater.check_and_update()
        except Exception as e:
            print(f"[WARNING] OTA update failed: {e}")
            print("[INFO] Continuing with current version...")

    # Get IP address for display
    if RUNNING_ON_HARDWARE:
        wlan = network.WLAN(network.STA_IF)
        ip_address = wlan.ifconfig()[0]
    else:
        # Use localhost for local testing
        ip_address = "127.0.0.1"
        print(f"[INFO] Local test mode - using IP address: {ip_address}")

    # Initialize Modbus RTU
    print("[DEBUG] Initializing Modbus RTU interface...")
    modbus = ModbusRTU(
        uart_id=UART_ID,
        baudrate=BAUDRATE,
        parity=PARITY,
        stop_bits=STOP_BITS,
    )

    # Initialize HTTP server (use port 8080 for local testing to avoid root requirement)
    http_port = 80 if RUNNING_ON_HARDWARE else 8080
    http_server = await HTTPServer(modbus, port=http_port).start()
    print(f"[INFO] Access the web interface at: http://{ip_address}:{http_port}")

    # Initialize Modbus TCP server (use port 5020 for local testing)
    modbus_port = 502 if RUNNING_ON_HARDWARE else 5020
    modbus_tcp_server = await ModbusTCPServer(modbus, port=modbus_port).start()
    print(f"[INFO] Modbus TCP server available at: {ip_address}:{modbus_port}")

    # Start TCP log server
    tcp_log_server = await debug_server.tcp_log_server(4138)
    print(f"[INFO] TCP log server available at: {ip_address}:4138")

    await asyncio.gather(
        http_server.wait_closed(),
        modbus_tcp_server.wait_closed(),
        tcp_log_server.wait_closed(),
    )


# Run the application
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutting down...")
