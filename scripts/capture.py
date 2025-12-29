#!/usr/bin/env python3
"""
Single IR capture script - captures one IR signal and exits.
Usage: ./capture.py <label>
"""

import serial
import sys
import time
import re
from pathlib import Path
from datetime import datetime

def find_serial_port():
    """Auto-detect ESP8266 serial port"""
    import glob
    for pattern in ['/dev/cu.usbserial-*', '/dev/cu.SLAB_USBtoUART*', '/dev/cu.wchusbserial*']:
        ports = glob.glob(pattern)
        if ports:
            return ports[0]
    return None

def main():
    if len(sys.argv) < 2:
        print("Usage: ./capture.py <label>", file=sys.stderr)
        sys.exit(1)

    label = sys.argv[1]

    # Find serial port
    port = find_serial_port()
    if not port:
        print("ERROR: No serial port found", file=sys.stderr)
        sys.exit(1)

    # Setup output file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"captures/{timestamp}_{label}.txt"
    Path("captures").mkdir(exist_ok=True)

    # Write header
    with open(output_file, 'w') as f:
        f.write(f"# IR Capture: {label}\n")
        f.write(f"# Time: {datetime.now()}\n")
        f.write(f"# Port: {port}\n")
        f.write("=" * 60 + "\n\n")

    print(f"[{label}] Waiting for IR...", file=sys.stderr)

    try:
        ser = serial.Serial(port, 115200, timeout=1)
        buffer = ""

        with open(output_file, 'a') as f:
            start_time = time.time()

            while True:
                if time.time() - start_time > 60:
                    print("\nTimeout", file=sys.stderr)
                    sys.exit(1)

                if ser.in_waiting > 0:
                    data = ser.read(ser.in_waiting)
                    text = data.decode('utf-8', errors='replace')

                    # Save everything to file
                    f.write(text)
                    f.flush()

                    buffer += text

                    # Check for completion
                    if "END CAPTURE" in text:
                        # Extract state array
                        match = re.search(r'uint8_t state\[(\d+)\]\s*=\s*\{([^}]+)\}', buffer)
                        if match:
                            size = match.group(1)
                            state = match.group(2)
                            print(f"\n✓ State[{size}]: {{{state}}}")
                        else:
                            print(f"\n✓ Captured (check file for details)")

                        print(f"✓ Saved: {output_file}", file=sys.stderr)
                        ser.close()
                        sys.exit(0)

                time.sleep(0.01)

    except KeyboardInterrupt:
        print("\nCancelled", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
