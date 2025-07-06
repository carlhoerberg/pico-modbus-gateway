import network
import time
from machine import Pin, UART
import uasyncio as asyncio
from modbus_rtu import ModbusRTU
from modbus_tcp_server import ModbusTCPServer
from http_server import HTTPServer
from config import WIFI_SSID, WIFI_PASSWORD, UART_ID, BAUDRATE, PARITY, STOP_BITS
from ota_updater import OTAUpdater


# WiFi connection
def connect_wifi(ssid, password):
    """Connect to WiFi network - retry forever until successful"""
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
            print("[SUCCESS] Connected to WiFi!")
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

    # Check for OTA updates
    print("[DEBUG] Checking for OTA updates...")
    ota_updater = OTAUpdater("carlhoerberg/pico-modbus-gateway")
    try:
        await ota_updater.check_and_update()
    except Exception as e:
        print(f"[WARNING] OTA update failed: {e}")
        print("[INFO] Continuing with current version...")

    # Get IP address for display
    wlan = network.WLAN(network.STA_IF)
    ip_address = wlan.ifconfig()[0]

    # Initialize Modbus RTU
    print("[DEBUG] Initializing Modbus RTU interface...")
    # Use settings from config.py - pin assignments are handled automatically
    modbus = ModbusRTU(
        uart_id=UART_ID,
        baudrate=BAUDRATE,
        parity=PARITY,
        stop_bits=STOP_BITS,
    )
    parity_str = ["None", "Odd", "Even"][PARITY]
    pin_map = {0: {"tx": 0, "rx": 1}, 1: {"tx": 4, "rx": 5}}
    pins = pin_map[UART_ID]
    print(
        f"[DEBUG] Modbus RTU initialized on UART{UART_ID} (TX=GP{pins['tx']}, RX=GP{pins['rx']}), {BAUDRATE} baud, {parity_str} parity, {STOP_BITS} stop bits"
    )

    # Initialize HTTP server
    print("[DEBUG] Initializing HTTP server on port 80...")
    http_server = HTTPServer(modbus, port=80)

    # Initialize Modbus TCP server
    print("[DEBUG] Initializing Modbus TCP server on port 502...")
    modbus_tcp_server = ModbusTCPServer(modbus, port=502)

    print("[SUCCESS] Starting Modbus Gateway...")
    print(f"[INFO] Access the web interface at: http://{ip_address}")
    print(f"[INFO] Modbus TCP server available at: {ip_address}:502")

    # Start both servers concurrently
    print("[DEBUG] Starting HTTP and Modbus TCP servers...")
    await asyncio.gather(http_server.start(), modbus_tcp_server.start())
    print("[SUCCESS] All servers started successfully!")


# Run the application
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Error: {e}")
