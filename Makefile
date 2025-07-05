# Makefile for Raspberry Pi Pico Modbus Gateway
# Uses mpremote to upload files to the Pico

# Default target
.PHONY: all
all: upload

# Upload all Python files and assets to the Pico
.PHONY: upload
upload:
	@echo "Uploading all files to Raspberry Pi Pico..."
	mpremote cp main.py :
	mpremote cp config.py :
	mpremote cp modbus_rtu.py :
	mpremote cp modbus_tcp_server.py :
	mpremote cp http_server.py :
	mpremote cp index.html :
	@echo "Upload complete!"

# Upload and run main.py
.PHONY: run
run: upload
	@echo "Starting Modbus Gateway..."
	mpremote run main.py

# Upload individual files
.PHONY: upload-main
upload-main:
	@echo "Uploading main.py..."
	mpremote cp main.py :

.PHONY: upload-config
upload-config:
	@echo "Uploading config.py..."
	mpremote cp config.py :

.PHONY: upload-modbus-rtu
upload-modbus-rtu:
	@echo "Uploading modbus_rtu.py..."
	mpremote cp modbus_rtu.py :

.PHONY: upload-modbus-tcp
upload-modbus-tcp:
	@echo "Uploading modbus_tcp_server.py..."
	mpremote cp modbus_tcp_server.py :

.PHONY: upload-http
upload-http:
	@echo "Uploading http_server.py..."
	mpremote cp http_server.py :

.PHONY: upload-html
upload-html:
	@echo "Uploading index.html..."
	mpremote cp index.html :

# Reset and soft reboot the Pico
.PHONY: reset
reset:
	@echo "Resetting Pico..."
	mpremote reset

# Connect to Pico REPL
.PHONY: repl
repl:
	@echo "Connecting to Pico REPL (Ctrl+X to exit)..."
	mpremote repl

# List files on the Pico
.PHONY: ls
ls:
	@echo "Files on Pico:"
	mpremote ls

# Remove all project files from Pico
.PHONY: clean
clean:
	@echo "Removing project files from Pico..."
	-mpremote rm main.py
	-mpremote rm config.py
	-mpremote rm modbus_rtu.py
	-mpremote rm modbus_tcp_server.py
	-mpremote rm http_server.py
	-mpremote rm index.html
	@echo "Clean complete!"

# Show Pico device info
.PHONY: info
info:
	@echo "Pico device information:"
	mpremote exec "import os; print('Python:', os.uname())"

# Monitor serial output
.PHONY: monitor
monitor:
	@echo "Monitoring Pico output (Ctrl+C to exit)..."
	mpremote repl --capture-output

# Development workflow: clean, upload, and run
.PHONY: dev
dev: clean upload run

# Help target
.PHONY: help
help:
	@echo "Available targets:"
	@echo "  upload         - Upload all files to Pico"
	@echo "  run            - Upload and run main.py"
	@echo "  upload-main    - Upload only main.py"
	@echo "  upload-config  - Upload only config.py"
	@echo "  upload-modbus-rtu - Upload only modbus_rtu.py"
	@echo "  upload-modbus-tcp - Upload only modbus_tcp_server.py"
	@echo "  upload-http    - Upload only http_server.py"
	@echo "  upload-html    - Upload only index.html"
	@echo "  reset          - Reset the Pico"
	@echo "  repl           - Connect to Pico REPL"
	@echo "  ls             - List files on Pico"
	@echo "  clean          - Remove project files from Pico"
	@echo "  info           - Show Pico device info"
	@echo "  monitor        - Monitor serial output"
	@echo "  dev            - Clean, upload, and run (development workflow)"
	@echo "  help           - Show this help message"