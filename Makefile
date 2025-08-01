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
	mpremote cp ota_updater.py :
	mpremote cp index.html :
	@echo "Upload complete!"

# Upload and run main.py
.PHONY: run
run: upload
	@echo "Starting Modbus Gateway..."
	mpremote run main.py

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
	-mpremote rm ota_updater.py
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
dev: upload run
