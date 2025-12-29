#!/usr/bin/env bash

#
# flash.sh - Flash firmware to ESP8266 from macOS host
#
# Usage:
#   ./scripts/flash.sh              # Auto-detect serial port
#   SERIAL_PORT=/dev/cu.* ./scripts/flash.sh  # Manual override
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "============================================"
echo "ESP8266 Firmware Flash Script"
echo "============================================"
echo

# Check if PlatformIO is installed
if ! command -v pio &> /dev/null; then
    echo -e "${RED}ERROR: PlatformIO not found!${NC}"
    echo
    echo "Please install PlatformIO on your macOS host:"
    echo "  pip install platformio"
    echo "  or"
    echo "  brew install platformio"
    echo
    exit 1
fi

# Detect serial port if not specified
if [ -z "$SERIAL_PORT" ]; then
    echo "Auto-detecting serial port..."

    # Look for common ESP8266/NodeMCU serial devices
    SERIAL_PORT=$(ls /dev/cu.usbserial-* 2>/dev/null | head -n 1)

    if [ -z "$SERIAL_PORT" ]; then
        SERIAL_PORT=$(ls /dev/cu.SLAB_USBtoUART* 2>/dev/null | head -n 1)
    fi

    if [ -z "$SERIAL_PORT" ]; then
        SERIAL_PORT=$(ls /dev/cu.wchusbserial* 2>/dev/null | head -n 1)
    fi

    if [ -z "$SERIAL_PORT" ]; then
        echo -e "${RED}ERROR: Could not auto-detect serial port!${NC}"
        echo
        echo "Please ensure your ESP8266 is connected via USB."
        echo
        echo "You can manually specify the port:"
        echo "  SERIAL_PORT=/dev/cu.YOUR_DEVICE ./scripts/flash.sh"
        echo
        echo "Available serial devices:"
        ls -1 /dev/cu.* 2>/dev/null || echo "  (none found)"
        echo
        exit 1
    fi
fi

echo -e "${GREEN}✓ Using serial port: $SERIAL_PORT${NC}"
echo

# Flash the firmware
echo "Flashing firmware..."
echo "Running: pio run --target upload --upload-port $SERIAL_PORT"
echo

pio run --target upload --upload-port "$SERIAL_PORT"

echo
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}✓ Firmware flashed successfully!${NC}"
echo -e "${GREEN}============================================${NC}"
echo
echo "Next steps:"
echo "  1. Run the serial monitor: ./scripts/monitor.sh"
echo "  2. Or start a capture session: ./scripts/capture.sh"
echo
