#!/usr/bin/env python3
"""
Simple serial port capture tool - RAW dump everything.
Automatically exits after capturing one complete IR signal.
"""

import serial
import sys
import time

def main():
    if len(sys.argv) < 3:
        print("Usage: serial_capture.py <port> <output_file> [timeout_seconds]", file=sys.stderr)
        sys.exit(1)

    port = sys.argv[1]
    output_file = sys.argv[2]
    timeout_seconds = int(sys.argv[3]) if len(sys.argv) > 3 else 60
    baud_rate = 115200

    try:
        # Open serial port
        ser = serial.Serial(port, baud_rate, timeout=1)
        print("Waiting for IR signal...", file=sys.stderr)

        capture_complete = False
        start_time = time.time()

        with open(output_file, 'a') as f:
            while not capture_complete:
                # Check timeout
                if time.time() - start_time > timeout_seconds:
                    print("\nTimeout - no IR received", file=sys.stderr)
                    ser.close()
                    sys.exit(1)

                if ser.in_waiting > 0:
                    # Read available data
                    data = ser.read(ser.in_waiting)
                    try:
                        text = data.decode('utf-8', errors='replace')

                        # Write to file
                        f.write(text)
                        f.flush()

                        # Write to stdout (user sees everything)
                        sys.stdout.write(text)
                        sys.stdout.flush()

                        # Check for end marker
                        if "END CAPTURE" in text:
                            capture_complete = True
                            print("\n", file=sys.stderr)
                    except Exception as e:
                        print(f"Error: {e}", file=sys.stderr)
                else:
                    time.sleep(0.01)

    except KeyboardInterrupt:
        print("\n\nCapture stopped by user", file=sys.stderr)
        ser.close()
        sys.exit(0)
    except serial.SerialException as e:
        print(f"Serial port error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
