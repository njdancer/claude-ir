#!/usr/bin/env bash

#
# capture.sh - Capture IR data and save to timestamped file
#
# Usage:
#   ./scripts/capture.sh [label]              # Auto-detect serial port
#   SERIAL_PORT=/dev/cu.* ./scripts/capture.sh [label]  # Manual override
#
# Examples:
#   ./scripts/capture.sh power-on
#   ./scripts/capture.sh temp-up
#   ./scripts/capture.sh "mode-cool-24deg"
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get optional label from first argument
LABEL="${1:-unlabeled}"

# Generate timestamp
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Create capture filename
CAPTURE_FILE="captures/${TIMESTAMP}_${LABEL}.txt"

# Detect serial port if not specified
if [ -z "$SERIAL_PORT" ]; then
    SERIAL_PORT=$(ls /dev/cu.usbserial-* 2>/dev/null | head -n 1)
    if [ -z "$SERIAL_PORT" ]; then
        SERIAL_PORT=$(ls /dev/cu.SLAB_USBtoUART* 2>/dev/null | head -n 1)
    fi
    if [ -z "$SERIAL_PORT" ]; then
        SERIAL_PORT=$(ls /dev/cu.wchusbserial* 2>/dev/null | head -n 1)
    fi
    if [ -z "$SERIAL_PORT" ]; then
        echo -e "${RED}ERROR: No serial port found${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}[$LABEL] Waiting for IR...${NC}"

# Write metadata header to capture file
cat > "$CAPTURE_FILE" << EOF
# IR Capture Session
# Timestamp: $(date)
# Label: $LABEL
# Serial Port: $SERIAL_PORT
# Baud Rate: 115200
========================================

EOF


# Capture serial output and display to console while saving to file
# Using Python serial capture tool (works in non-interactive terminals)
python3 "$(dirname "$0")/serial_capture.py" "$SERIAL_PORT" "$CAPTURE_FILE"

echo
echo -e "${GREEN}✓ Saved: $CAPTURE_FILE${NC}"
