# ActronAir IR Protocol Reverse Engineering

## Hardware Setup
- ESP8266 NodeMCU with CHQ1838 IR receiver
- Firmware flashed and working
- Serial: `/dev/cu.usbserial-*` at 115200 baud

## Capture Tool
**Single script**: `./scripts/capture.py <label>`
- Auto-detects serial port
- Waits for ONE IR signal
- Saves full capture to `captures/<timestamp>_<label>.txt`
- Prints state array to stdout
- Exits immediately after capture

## Critical Understanding: State-Based Protocol

**The remote does NOT send discrete commands.**

Instead:
1. Remote maintains internal state (temp, mode, fan, swing, etc.)
2. When ANY button is pressed, remote broadcasts COMPLETE state
3. AC receives full state and updates

**Example**: Pressing "temp up" sends:
- NOT: "increase temp by 0.5"
- INSTEAD: "Power=ON, Mode=COOL, Temp=21.5°C, Fan=AUTO, Swing=ON, etc."

## Workflow: One Button Press at a Time

You can ONLY instruct the user to:
- **"Press the [BUTTON] button once"**

You CANNOT ask them to:
- "Set the temperature to X" (you don't control the remote's state)
- "Press button A then button B" (script exits after first press)
- "Toggle setting to X" (you don't know current state)

### Proper Workflow Example

```
User tells you current state: "20°C, COOL, Fan AUTO"

You: "Press TEMP UP once"
[Run: python3 scripts/capture.py temp-up]
[User presses button → capture → script exits]
[You see: state array for 20.5°C]

You: "Press MODE once"
[Run: python3 scripts/capture.py mode-1]
[User presses button → capture → script exits]
[You see: state array for DRY mode]
```

## Analysis Tools

**Decoder**: `python3 analysis/decoder.py`
- Loads all captures from `captures/`
- Shows byte-by-byte comparison
- Identifies changing bytes
- Analyzes temperature patterns

## Current Protocol Knowledge

**Protocol**: BOSCH144 (18 bytes)
- Bytes 0-5: State (header + mode/fan/temp)
- Bytes 6-11: Exact copy of 0-5
- Bytes 12-17: Footer (checksums, additional flags)

**Temperature**: Non-linear lookup table
- Byte 4: Base temp value (mode bits OR'd in)
- Byte 14: 0x00=whole degree, 0x20=+0.5°C
- Byte 5: Inverse checksum of byte 4

**Modes**: Encoded in bytes 2-3 and byte 4
- COOL/HEAT/FAN: bytes 2-3 = varies by fan
- DRY/AUTO: bytes 2-3 = varies by fan
- Byte 4: temp value + mode bits

**Fan Speed**: Bytes 2-3 + byte 13
- Byte 13: Direct percentage (20, 40, 60, 80, 100) or 0x66 for AUTO
- Bytes 2-3: Complex encoding pattern

**Swing**: Unknown
- Previous testing suggested no IR signal, but this is impossible
- Likely either: wrong parsing, or state embedded in other commands

## Testing Strategy

### Systematic Capture
1. User tells you current remote state
2. You instruct: "Press [BUTTON] once"
3. You run: `python3 scripts/capture.py <descriptive-label>`
4. Script captures and shows state array
5. You analyze changes
6. Repeat with next button

### Comparing States
- Use decoder to compare captures
- Look for byte differences
- Build mapping of feature → byte/bits
- Validate with multiple captures

### Example Session
```
User: "Remote is: 24°C, COOL, Fan 80%"

You: Press TEMP DOWN once
[Capture: temp-down-from-24]
State changes: byte 4 and byte 14 change

You: Press TEMP DOWN once
[Capture: temp-down-2]
State changes: only byte 4 changes (confirms 23.0°C)

You: Press FAN once
[Capture: fan-from-80]
State changes: bytes 2, 3, 13 change
```

## Key Rules

1. **One button press = one capture**
   - Script auto-exits after each capture
   - Cannot chain button presses

2. **Trust user's current state**
   - They can see the remote display
   - You cannot verify remotely

3. **Label captures descriptively**
   - Use context: `temp-down-from-24`, `mode-to-heat`, `fan-auto`
   - Makes analysis easier

4. **Capture EVERYTHING**
   - Script saves full output to file
   - Shows minimal summary on screen
   - Don't lose data to filtering

5. **Build incrementally**
   - Map one feature at a time
   - Temperature, then modes, then fan, etc.
   - Verify patterns with multiple captures

## Troubleshooting

**"No state array found"**:
- IR signal WAS received (script exited)
- Check capture file - data is there
- Pattern might be different than expected

**Timeout**:
- User didn't press button
- IR receiver not working
- Button doesn't send IR (possible for some features)

**Inconsistent results**:
- Remote state different than expected
- Multiple features changed at once
- Checksum/footer bytes updating

## Files

- `scripts/capture.py` - Single capture script
- `analysis/decoder.py` - Analyze captures
- `analysis/protocol_spec.md` - Current protocol documentation
- `captures/*.txt` - All capture data

---

**Remember**: You run the capture script, user presses ONE button, script exits. Repeat.
