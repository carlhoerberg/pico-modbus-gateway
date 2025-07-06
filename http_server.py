import socket
import json
import uasyncio as asyncio
from ota_updater import OTAUpdater


class HTTPServer:
    def __init__(self, modbus_rtu, port=80):
        self.modbus = modbus_rtu
        self.port = port
        self.socket = None
        self.ota_updater = OTAUpdater("carlhoerberg/pico-modbus-gateway")

    async def start(self):
        """Start the HTTP server"""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(("0.0.0.0", self.port))
        self.socket.listen(5)
        self.socket.setblocking(False)

        print(f"HTTP Server listening on port {self.port}")

        while True:
            try:
                client_socket, addr = self.socket.accept()
                asyncio.create_task(self.handle_client(client_socket))
            except OSError:
                await asyncio.sleep(0.1)

    async def handle_client(self, client_socket):
        """Handle HTTP client request"""
        try:
            client_socket.setblocking(False)
            request = b""

            # Read request
            while True:
                try:
                    chunk = client_socket.recv(1024)
                    if not chunk:
                        break
                    request += chunk
                    if b"\r\n\r\n" in request:
                        break
                except OSError:
                    await asyncio.sleep(0.01)

            # Parse HTTP request
            try:
                request_str = request.decode("utf-8")
            except:
                request_str = request.decode()
            lines = request_str.split("\r\n")

            if not lines or not lines[0]:
                client_socket.close()
                return

            # Parse HTTP request line safely
            request_parts = lines[0].split(" ")
            if len(request_parts) < 2:
                client_socket.close()
                return

            method = request_parts[0]
            path = request_parts[1]

            # Route handling
            if path == "/":
                response = self.serve_index()
            elif path.startswith("/api/"):
                response = await self.handle_api(path, request_str)
            else:
                response = self.serve_404()

            # Send response
            client_socket.send(response.encode())
            client_socket.close()

        except Exception as e:
            print(f"Error handling client: {e}")
            try:
                client_socket.close()
            except:
                pass

    def serve_index(self):
        """Serve main HTML page"""
        try:
            with open("index.html", "r") as f:
                html = f.read()
        except OSError:
            return self.serve_404()

        return f"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nContent-Length: {len(html)}\r\n\r\n{html}"

    def serve_404(self):
        """Serve 404 error"""
        html = "<html><body><h1>404 Not Found</h1></body></html>"
        return f"HTTP/1.1 404 Not Found\r\nContent-Type: text/html\r\nContent-Length: {len(html)}\r\n\r\n{html}"

    async def handle_api(self, path, request_str):
        """Handle API requests"""
        try:
            # Parse query parameters
            if "?" in path:
                path, query = path.split("?", 1)
                params = {}
                for param in query.split("&"):
                    if "=" in param:
                        key, val = param.split("=", 1)
                        params[key] = val
            else:
                params = {}

            # API routing
            if path == "/api/read_coils":
                return await self.api_read_coils(params)
            elif path == "/api/read_discrete":
                return await self.api_read_discrete(params)
            elif path == "/api/read_holding":
                return await self.api_read_holding(params)
            elif path == "/api/read_input":
                return await self.api_read_input(params)
            elif path == "/api/write_coil":
                return await self.api_write_coil(params)
            elif path == "/api/write_single":
                return await self.api_write_single(params)
            elif path == "/api/write_coils":
                return await self.api_write_coils(params)
            elif path == "/api/write_multiple":
                return await self.api_write_multiple(params)
            elif path == "/api/ota_update":
                return await self.api_ota_update(params)
            elif path == "/api/wifi_config":
                return await self.api_wifi_config(params)
            else:
                return self.api_error("Unknown API endpoint")

        except Exception as e:
            return self.api_error(f"API Error: {str(e)}")

    async def api_read_coils(self, params):
        """API: Read coils"""
        slave_id = int(params.get("slave_id", 1))
        start_addr = int(params.get("start_addr", 0))
        count = int(params.get("count", 1))

        result = await self.modbus.read_coils(slave_id, start_addr, count)

        if result is None:
            response = {"success": False, "error": "Communication timeout"}
        elif isinstance(result, dict) and "error" in result:
            response = {"success": False, "error": f"Modbus error: {result['error']}"}
        else:
            response = {"success": True, "data": result}

        json_str = json.dumps(response)
        return f"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {len(json_str)}\r\n\r\n{json_str}"

    async def api_read_discrete(self, params):
        """API: Read discrete inputs"""
        slave_id = int(params.get("slave_id", 1))
        start_addr = int(params.get("start_addr", 0))
        count = int(params.get("count", 1))

        result = await self.modbus.read_discrete_inputs(slave_id, start_addr, count)

        if result is None:
            response = {"success": False, "error": "Communication timeout"}
        elif isinstance(result, dict) and "error" in result:
            response = {"success": False, "error": f"Modbus error: {result['error']}"}
        else:
            response = {"success": True, "data": result}

        json_str = json.dumps(response)
        return f"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {len(json_str)}\r\n\r\n{json_str}"

    async def api_read_holding(self, params):
        """API: Read holding registers"""
        slave_id = int(params.get("slave_id", 1))
        start_addr = int(params.get("start_addr", 0))
        count = int(params.get("count", 1))

        result = await self.modbus.read_holding_registers(slave_id, start_addr, count)

        if result is None:
            response = {"success": False, "error": "Communication timeout"}
        elif isinstance(result, dict) and "error" in result:
            response = {"success": False, "error": f"Modbus error: {result['error']}"}
        else:
            response = {"success": True, "data": result}

        json_str = json.dumps(response)
        return f"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {len(json_str)}\r\n\r\n{json_str}"

    async def api_read_input(self, params):
        """API: Read input registers"""
        slave_id = int(params.get("slave_id", 1))
        start_addr = int(params.get("start_addr", 0))
        count = int(params.get("count", 1))

        result = await self.modbus.read_input_registers(slave_id, start_addr, count)

        if result is None:
            response = {"success": False, "error": "Communication timeout"}
        elif isinstance(result, dict) and "error" in result:
            response = {"success": False, "error": f"Modbus error: {result['error']}"}
        else:
            response = {"success": True, "data": result}

        json_str = json.dumps(response)
        return f"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {len(json_str)}\r\n\r\n{json_str}"

    async def api_write_single(self, params):
        """API: Write single register"""
        slave_id = int(params.get("slave_id", 1))
        register_addr = int(params.get("start_addr", 0))
        value = int(params.get("value", 0))

        result = await self.modbus.write_single_register(slave_id, register_addr, value)

        if result is None:
            response = {"success": False, "error": "Communication timeout"}
        elif isinstance(result, dict) and "error" in result:
            response = {"success": False, "error": f"Modbus error: {result['error']}"}
        else:
            response = {"success": True, "message": "Register written successfully"}

        json_str = json.dumps(response)
        return f"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {len(json_str)}\r\n\r\n{json_str}"

    async def api_write_multiple(self, params):
        """API: Write multiple holding registers"""
        slave_id = int(params.get("slave_id", 1))
        start_addr = int(params.get("start_addr", 0))
        values_str = params.get("values", "0")

        # Parse values - expect comma-separated integers
        try:
            values = [int(v.strip()) for v in values_str.split(",")]
        except ValueError:
            response = {
                "success": False,
                "error": "Invalid values format. Use comma-separated integers.",
            }
            json_str = json.dumps(response)
            return f"HTTP/1.1 400 Bad Request\r\nContent-Type: application/json\r\nContent-Length: {len(json_str)}\r\n\r\n{json_str}"

        result = await self.modbus.write_multiple_registers(
            slave_id, start_addr, values
        )

        if result is None:
            response = {"success": False, "error": "Communication timeout"}
        elif isinstance(result, dict) and "error" in result:
            response = {"success": False, "error": f"Modbus error: {result['error']}"}
        else:
            response = {
                "success": True,
                "message": f"Written {len(values)} registers successfully",
            }

        json_str = json.dumps(response)
        return f"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {len(json_str)}\r\n\r\n{json_str}"

    async def api_write_coil(self, params):
        """API: Write single coil"""
        slave_id = int(params.get("slave_id", 1))
        coil_addr = int(params.get("start_addr", 0))
        value_str = params.get("value", "0").lower()

        # Parse boolean value
        value = value_str in ["1", "true", "on", "yes"]

        result = await self.modbus.write_single_coil(slave_id, coil_addr, value)

        if result is None:
            response = {"success": False, "error": "Communication timeout"}
        elif isinstance(result, dict) and "error" in result:
            response = {"success": False, "error": f"Modbus error: {result['error']}"}
        else:
            response = {"success": True, "message": "Coil written successfully"}

        json_str = json.dumps(response)
        return f"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {len(json_str)}\r\n\r\n{json_str}"

    async def api_write_coils(self, params):
        """API: Write multiple coils"""
        slave_id = int(params.get("slave_id", 1))
        start_addr = int(params.get("start_addr", 0))
        values_str = params.get("values", "0")

        # Parse values - expect comma-separated boolean values
        try:
            values = []
            for v in values_str.split(","):
                v = v.strip().lower()
                values.append(v in ["1", "true", "on", "yes"])
        except ValueError:
            response = {
                "success": False,
                "error": "Invalid values format. Use comma-separated boolean values.",
            }
            json_str = json.dumps(response)
            return f"HTTP/1.1 400 Bad Request\r\nContent-Type: application/json\r\nContent-Length: {len(json_str)}\r\n\r\n{json_str}"

        result = await self.modbus.write_multiple_coils(slave_id, start_addr, values)

        if result is None:
            response = {"success": False, "error": "Communication timeout"}
        elif isinstance(result, dict) and "error" in result:
            response = {"success": False, "error": f"Modbus error: {result['error']}"}
        else:
            response = {
                "success": True,
                "message": f"Written {len(values)} coils successfully",
            }

        json_str = json.dumps(response)
        return f"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {len(json_str)}\r\n\r\n{json_str}"

    async def api_ota_update(self, params):
        """API: Perform OTA update"""
        try:
            # Check if force update is requested
            force_update = params.get("force", "false").lower() in ["true", "1", "yes"]

            response = {"success": False}

            if force_update:
                # Force update - download and replace files regardless of version
                print("[OTA API] Force update requested")
                update_result = await self.ota_updater.perform_update()
                if update_result:
                    response = {
                        "success": True,
                        "message": "OTA update completed successfully. Device will restart.",
                        "action": "restart_pending",
                    }
                    # Restart immediately
                    self.ota_updater.restart_device()
                else:
                    response = {
                        "success": False,
                        "error": "OTA update failed. Check logs for details.",
                    }
            else:
                # Normal update - check for newer version first
                print("[OTA API] Checking for available updates")
                update_available = await self.ota_updater.check_for_updates()

                if isinstance(update_available, tuple) and update_available[0]:
                    # Update available
                    print("[OTA API] Update available, performing update")
                    update_result = await self.ota_updater.perform_update()
                    if update_result:
                        response = {
                            "success": True,
                            "message": "OTA update completed successfully. Device will restart.",
                            "action": "restart_pending",
                        }
                        # Restart immediately
                        self.ota_updater.restart_device()
                    else:
                        response = {
                            "success": False,
                            "error": "OTA update failed. Check logs for details.",
                        }
                else:
                    # No update available
                    response = {
                        "success": True,
                        "message": "No updates available. Device is already running the latest version.",
                        "action": "no_update",
                    }

        except Exception as e:
            print(f"[OTA API] Error: {e}")
            response = {"success": False, "error": f"OTA update error: {str(e)}"}

        json_str = json.dumps(response)
        return f"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {len(json_str)}\r\n\r\n{json_str}"

    async def api_wifi_config(self, params):
        """API: Update WiFi configuration"""
        try:
            ssid = params.get("ssid", "").strip()
            password = params.get("password", "").strip()

            if not ssid:
                response = {"success": False, "error": "WiFi SSID cannot be empty"}
                json_str = json.dumps(response)
                return f"HTTP/1.1 400 Bad Request\r\nContent-Type: application/json\r\nContent-Length: {len(json_str)}\r\n\r\n{json_str}"

            # Read current config file
            try:
                with open("config.py", "r") as f:
                    config_content = f.read()
            except OSError:
                response = {"success": False, "error": "Could not read config file"}
                json_str = json.dumps(response)
                return f"HTTP/1.1 500 Internal Server Error\r\nContent-Type: application/json\r\nContent-Length: {len(json_str)}\r\n\r\n{json_str}"

            # Update WiFi settings in config
            lines = config_content.split("\n")
            updated_lines = []
            ssid_updated = False
            password_updated = False

            for line in lines:
                if line.startswith("WIFI_SSID = "):
                    updated_lines.append(f'WIFI_SSID = "{ssid}"')
                    ssid_updated = True
                elif line.startswith("WIFI_PASSWORD = "):
                    updated_lines.append(f'WIFI_PASSWORD = "{password}"')
                    password_updated = True
                else:
                    updated_lines.append(line)

            # If not found, add them
            if not ssid_updated:
                updated_lines.insert(3, f'WIFI_SSID = "{ssid}"')
            if not password_updated:
                updated_lines.insert(4, f'WIFI_PASSWORD = "{password}"')

            new_config = "\n".join(updated_lines)

            # Write updated config file
            try:
                with open("config.py", "w") as f:
                    f.write(new_config)
            except OSError:
                response = {"success": False, "error": "Could not write config file"}
                json_str = json.dumps(response)
                return f"HTTP/1.1 500 Internal Server Error\r\nContent-Type: application/json\r\nContent-Length: {len(json_str)}\r\n\r\n{json_str}"

            response = {
                "success": True,
                "message": "WiFi configuration updated successfully. Device will restart immediately.",
                "ssid": ssid,
                "action": "restart_immediate",
            }

            # Import machine module for restart
            import machine

            # Restart immediately after response
            machine.reset()

        except Exception as e:
            response = {"success": False, "error": f"WiFi config error: {str(e)}"}

        json_str = json.dumps(response)
        return f"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {len(json_str)}\r\n\r\n{json_str}"

    def api_error(self, message):
        """Return API error response"""
        response = {"success": False, "error": message}
        json_str = json.dumps(response)
        return f"HTTP/1.1 500 Internal Server Error\r\nContent-Type: application/json\r\nContent-Length: {len(json_str)}\r\n\r\n{json_str}"
