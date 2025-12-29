#!/usr/bin/env python3
"""
ActronAir IR Protocol Decoder
Analyzes BOSCH144 captures from the ESP8266 IR receiver
"""

import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class ActronAirDecoder:
    """Decoder for ActronAir BOSCH144 IR protocol (18 bytes)"""

    def __init__(self):
        self.captures: Dict[str, List[int]] = {}

    def parse_capture_file(self, filepath: Path) -> Optional[Tuple[str, List[int]]]:
        """Extract state array from a capture file"""
        try:
            content = filepath.read_text()

            # Extract label from filename
            label = filepath.stem.split('_', 2)[-1] if '_' in filepath.stem else filepath.stem

            # Find the state array line (allow for any whitespace/formatting)
            match = re.search(r'uint8_t state\[18\]\s*=\s*\{([^}]+)\}', content, re.MULTILINE)
            if not match:
                return None

            # Parse hex values - handle various separators
            hex_string = match.group(1).strip()
            hex_values = re.findall(r'0x[0-9A-Fa-f]+', hex_string)
            state = [int(v, 16) for v in hex_values]

            if len(state) != 18:
                print(f"Warning: {filepath.name} has {len(state)} bytes, expected 18")
                return None

            return label, state

        except Exception as e:
            print(f"Error parsing {filepath.name}: {e}")
            return None

    def load_captures(self, captures_dir: Path):
        """Load all capture files from directory"""
        for filepath in sorted(captures_dir.glob("*.txt")):
            result = self.parse_capture_file(filepath)
            if result:
                label, state = result
                self.captures[label] = state
                print(f"✓ Loaded: {label}")

    def compare_all(self):
        """Generate comparison table of all captures"""
        if not self.captures:
            print("No captures loaded")
            return

        labels = list(self.captures.keys())

        print("\n" + "=" * 100)
        print("BYTE-BY-BYTE COMPARISON")
        print("=" * 100)

        # Header
        print(f"{'Byte':<6}", end="")
        for label in labels:
            print(f"{label:<20}", end="")
        print()
        print("-" * 100)

        # Each byte
        for byte_idx in range(18):
            print(f"{byte_idx:>4}  ", end="")

            values = [self.captures[label][byte_idx] for label in labels]

            # Check if all values are the same
            all_same = all(v == values[0] for v in values)

            for value in values:
                if all_same:
                    print(f"0x{value:02X} (constant)    ", end="")
                else:
                    print(f"0x{value:02X}              ", end="")
            print()

        print("=" * 100)

    def find_differences(self):
        """Identify which bytes change across captures"""
        if not self.captures:
            return

        labels = list(self.captures.keys())
        changing_bytes = []

        for byte_idx in range(18):
            values = set(self.captures[label][byte_idx] for label in labels)
            if len(values) > 1:
                changing_bytes.append(byte_idx)

        print("\n" + "=" * 100)
        print("CHANGING BYTES")
        print("=" * 100)

        if not changing_bytes:
            print("All bytes are constant across captures")
            return

        print(f"Bytes that change: {changing_bytes}")
        print()

        for byte_idx in changing_bytes:
            print(f"\nByte {byte_idx}:")
            values_map = {}
            for label in labels:
                value = self.captures[label][byte_idx]
                if value not in values_map:
                    values_map[value] = []
                values_map[value].append(label)

            for value in sorted(values_map.keys()):
                labels_str = ", ".join(values_map[value])
                print(f"  0x{value:02X} ({value:3d}): {labels_str}")

        print("=" * 100)

    def analyze_temperature(self):
        """Analyze temperature encoding pattern"""
        temp_captures = {k: v for k, v in self.captures.items() if k.startswith('temp-')}

        if len(temp_captures) < 2:
            print("\nNeed at least 2 temperature captures for analysis")
            return

        print("\n" + "=" * 100)
        print("TEMPERATURE ANALYSIS")
        print("=" * 100)

        # Try to extract temperature from label
        temp_data = []
        for label, state in sorted(temp_captures.items()):
            try:
                temp_str = label.replace('temp-', '')
                temp_c = int(temp_str)
                temp_data.append((temp_c, state[4], label))
            except ValueError:
                continue

        if len(temp_data) < 2:
            print("Could not extract temperature values from labels")
            return

        temp_data.sort()

        print(f"\n{'Temp (°C)':<12} {'Byte 4':<10} {'Byte 5':<10} {'Label':<20}")
        print("-" * 100)

        for temp_c, byte4, label in temp_data:
            byte5 = self.captures[label][5]
            print(f"{temp_c:<12} 0x{byte4:02X} ({byte4:3d})  0x{byte5:02X} ({byte5:3d})  {label}")

        # Calculate encoding
        if len(temp_data) >= 2:
            print("\nEncoding analysis:")
            t1, b1, _ = temp_data[0]
            t2, b2, _ = temp_data[1]

            temp_diff = t2 - t1
            byte_diff = b2 - b1

            if temp_diff != 0:
                ratio = byte_diff / temp_diff
                print(f"  Temperature difference: {temp_diff}°C")
                print(f"  Byte 4 difference: 0x{byte_diff:02X} ({byte_diff} decimal)")
                print(f"  Encoding: 0x{int(ratio):02X} ({int(ratio)} decimal) per °C")

                # Predict base temperature
                base_temp = t1 - (b1 / ratio)
                print(f"  Predicted base (0x00): {base_temp:.1f}°C")

        # Check if byte 5 is inverse
        print("\nByte 5 relationship to Byte 4:")
        for temp_c, byte4, label in temp_data:
            byte5 = self.captures[label][5]
            inverse = ~byte4 & 0xFF
            if byte5 == inverse:
                print(f"  {label}: Byte 5 = ~Byte 4 ✓")
            else:
                print(f"  {label}: Byte 5 = {hex(byte5)}, ~Byte 4 = {hex(inverse)} ✗")

        print("=" * 100)

    def decode_state(self, state: List[int]) -> Dict:
        """Decode a state array into human-readable fields"""
        # Based on analysis so far
        decoded = {
            'header': state[0:4],
            'temperature_byte': state[4],
            'temperature_checksum': state[5],
            'repeat': state[6:12],
            'footer': state[12:18],
        }

        # Decode temperature (assuming 0x08 per degree, base = 16°C)
        if state[4] % 8 == 0:
            decoded['temperature_c'] = 16 + (state[4] // 8)
        else:
            decoded['temperature_c'] = None

        # Verify checksum
        decoded['checksum_valid'] = (state[5] == (~state[4] & 0xFF))

        # Verify repeat section
        decoded['repeat_valid'] = (state[0:6] == state[6:12])

        return decoded


def main():
    if len(sys.argv) > 1:
        captures_dir = Path(sys.argv[1])
    else:
        captures_dir = Path(__file__).parent.parent / "captures"

    if not captures_dir.exists():
        print(f"Captures directory not found: {captures_dir}")
        sys.exit(1)

    print(f"Loading captures from: {captures_dir}")
    print()

    decoder = ActronAirDecoder()
    decoder.load_captures(captures_dir)

    print(f"\nTotal captures loaded: {len(decoder.captures)}")

    if decoder.captures:
        decoder.compare_all()
        decoder.find_differences()
        decoder.analyze_temperature()


if __name__ == "__main__":
    main()
