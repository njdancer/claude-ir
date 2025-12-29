# POC: ActronAir IR Control System

**Status**: Ready for implementation
**Background**: See `/re-findings.md` for complete reverse engineering results

---

## Mission

Build a proof-of-concept IR control system to validate our ability to send IR commands to an ActronAir air conditioner and provide a UI for testing and further reverse engineering.

---

## What We've Already Done

✅ **Hardware**: ESP8266 NodeMCU + CHQ1838 IR receiver working
✅ **Firmware**: PlatformIO project with IRremoteESP8266 library
✅ **Protocol**: Fully reverse-engineered BOSCH144 + COOLIX protocols
✅ **Captures**: 60+ captures of all main functions (temp, mode, fan, power, swing, etc.)
✅ **Analysis**: Complete protocol documentation in `/re-findings.md`

**Key Discovery**: ActronAir is rebranded Midea - uses standard BOSCH144 (climate) + COOLIX (special functions) protocols already supported by IRremoteESP8266!

---

## Your Tasks

### 1. Hardware: Add IR Transmitter

**Current state**: ESP8266 has IR receiver only (GPIO14/D5)

**Add**:
- IR LED(s) for transmission
- BJT transistor for driving LED(s)
- Appropriate resistors

**Available components**:
- IR LEDs (940nm typical)
- BJT transistors (2N2222, BC547, or similar)
- Resistors

**Requirements**:
- Use IRremoteESP8266 library's default transmit pin (GPIO4/D2) or configure custom
- Design circuit for sufficient IR power (multiple LEDs in series/parallel if needed)
- Provide updated wiring diagram

**Deliverable**:
- Wiring diagram (Markdown/ASCII art or suggest tool)
- Parts list with values (resistor sizes, etc.)
- Photos or verification of working circuit

---

### 2. Firmware: Add AC Control Support

**Current state**:
- ESP8266 firmware captures IR signals
- IRremoteESP8266 library installed
- Serial communication at 115200 baud

**Add**:
- IR transmit capability using `IRsend` class
- Command interface for sending BOSCH144 + COOLIX commands
- Choose communication method: **Serial or WiFi** (your decision)

**If Serial**:
- Parse commands from serial input (JSON, text protocol, your choice)
- Send appropriate IR codes
- Respond with success/failure

**If WiFi**:
- Create simple HTTP API or WebSocket server
- Parse commands from network requests
- Send appropriate IR codes
- Respond with JSON status

**Protocol Support Required**:
- **BOSCH144**: Temperature (16-30°C, 0.5°C steps), Modes (COOL/HEAT/FAN/DRY/AUTO), Fan (20-100%, AUTO)
- **COOLIX**: Power OFF, Swing toggle, Boost, LED

**Use IRremoteESP8266 existing functions**:
- `IRBosch144Ac` class for BOSCH144 commands
- `IRCoolixAC` class for COOLIX commands
- Library handles all encoding/checksums automatically!

**Bonus**:
- Keep IR receive capability for debugging
- Echo received commands back to control UI

**Deliverable**:
- Updated firmware code
- Communication protocol documentation
- Test commands for verification

---

### 3. Control UI: React Application

**Create**: Web-based control interface for testing IR commands

**Stack**:
- React + React Router (required)
- Your choice for styling (Tailwind, MUI, vanilla CSS, etc.)
- Your choice for state management
- Your choice for build tool (Vite, CRA, Next.js, etc.)

**Core Features**:

#### A. Climate Control Panel
- **Temperature**: Slider or buttons (16-30°C, 0.5°C steps)
- **Mode**: Buttons for COOL/HEAT/FAN/DRY/AUTO
- **Fan Speed**: Slider or buttons (AUTO/20/40/60/80/100%)
- **Power**: ON/OFF toggle
- **Send**: Button to transmit current state via BOSCH144

#### B. Special Functions Panel
- **Swing**: Toggle button (sends COOLIX)
- **Boost**: Toggle button (sends COOLIX)
- **LED**: Toggle button (sends COOLIX)

#### C. Current State Display
- Show last sent command
- Show current AC state (based on what we've sent)
- Visual feedback (loading, success, error)

#### D. Reverse Engineering Panel (Bonus)
- **IR Capture View**: Display incoming IR signals if receiver still active
- **Hex Dump**: Show raw bytes in both BOSCH144 and COOLIX formats
- **Byte Comparison**: Compare current vs. previous capture
- **Decode Info**: Parse and display human-readable values
  - Temperature, mode, fan from BOSCH144
  - Function type from COOLIX
- **Capture History**: Save captures with labels for later analysis

#### E. Claude Code Integration (Extra Bonus - Optional)
If feasible:
- Text area for asking questions about captures
- Integration with Claude Code CLI or API
- Context: Send capture data + question
- Display Claude's analysis of protocol details
- Collaborative troubleshooting workflow

**Communication**:
- If firmware uses Serial: Implement WebSerial API for browser ↔ ESP8266
- If firmware uses WiFi: Standard HTTP fetch/WebSocket to ESP8266
- Handle connection status, errors, retries

**Deliverable**:
- React app source code
- README with setup instructions
- Build instructions
- Screenshots/demo

---

## Implementation Decisions (Your Call)

### Communication: Serial vs. WiFi

**Option A: Serial** (Simpler)
- Pros: No network config, works offline, direct connection
- Cons: Requires physical USB connection, WebSerial browser API needed
- Best for: Initial testing, debugging, portable setup

**Option B: WiFi** (More Flexible)
- Pros: Wireless control, multiple clients, can integrate with home automation
- Cons: Network configuration, security considerations
- Best for: Permanent installation, integration with other systems

**Recommendation**: Start with serial for quick validation, add WiFi later if needed

### UI Architecture

**Suggested structure**:
```
/src
  /components
    ClimateControl.jsx      # Main AC control panel
    SpecialFunctions.jsx    # Swing/Boost/LED buttons
    StateDisplay.jsx        # Current state visualization
    CapturePanel.jsx        # Reverse engineering tools
  /services
    irService.js            # Communication with ESP8266
    protocolDecoder.js      # Parse BOSCH144/COOLIX
  /utils
    constants.js            # Protocol constants, temp ranges
  App.jsx                   # Main app + routing
```

### Testing Strategy

**Phase 1**: Send simple COOLIX commands (Power OFF, Swing) - easiest to validate
**Phase 2**: Send BOSCH144 with fixed values (e.g., 24°C, COOL, AUTO fan)
**Phase 3**: Send variable BOSCH144 (user-controlled temp/mode/fan)
**Phase 4**: Verify AC responds correctly to all commands

---

## Resources Available

### Protocol Details
- **Complete documentation**: `/re-findings.md`
- **Capture files**: `/captures/*.txt` (60+ examples)
- **Analysis tools**: `/analysis/decoder.py`

### Protocol Specifications
See `/re-findings.md` for:
- BOSCH144 byte structure (18 bytes)
- COOLIX command codes (24 bits)
- Temperature lookup table
- Mode encoding
- Fan speed encoding
- All checksums and validation rules

### IRremoteESP8266 Library
**Already installed** in project at:
- `.pio/libdeps/nodemcuv2/IRremoteESP8266/`

**Key classes to use**:
- `IRBosch144Ac` - BOSCH144 AC control ([docs](https://github.com/crankyoldgit/IRremoteESP8266/blob/master/src/ir_Bosch.h))
- `IRCoolixAC` - COOLIX AC control ([docs](https://github.com/crankyoldgit/IRremoteESP8266/blob/master/src/ir_Coolix.h))
- `IRsend` - Low-level IR transmit

**Example usage**:
```cpp
#include <IRsend.h>
#include <ir_Bosch.h>

IRBosch144Ac ac(IR_LED_PIN);

void sendACCommand(uint8_t temp, uint8_t mode, uint8_t fan) {
  ac.begin();
  ac.setTemp(temp);
  ac.setMode(mode);
  ac.setFan(fan);
  ac.send();
}
```

### Existing Firmware
**Location**: `/src/main.cpp` (currently receives IR only)

**Current capabilities**:
- IR receive on GPIO14/D5
- Serial output at 115200 baud
- Decodes BOSCH144 and COOLIX protocols
- Outputs state arrays and timing data

**You'll modify this** to add transmit capability

---

## Success Criteria

### Minimum Viable POC
1. ✅ IR LED circuit working (visible on camera, confirmed with receiver)
2. ✅ Can send Power OFF (COOLIX 0xB27BE0) and AC turns off
3. ✅ Can send Power ON with state (BOSCH144) and AC turns on at specified temp/mode
4. ✅ Can change temperature and AC responds
5. ✅ UI communicates with ESP8266 successfully

### Full POC
6. ✅ All modes work (COOL/HEAT/FAN/DRY/AUTO)
7. ✅ All fan speeds work (20-100%, AUTO)
8. ✅ Special functions work (Swing, Boost, LED)
9. ✅ UI shows current state accurately
10. ✅ Can capture and decode incoming IR (for further reverse engineering)

### Stretch Goals
11. ⭐ Reverse engineering panel fully functional
12. ⭐ Capture history and comparison tools
13. ⭐ Claude Code integration for collaborative analysis
14. ⭐ WiFi support for wireless control
15. ⭐ Multiple preset modes (Sleep, Eco, Custom)

---

## Project Structure

```
claude-ir/
├── src/                    # ESP8266 firmware (PlatformIO)
│   └── main.cpp           # Update with transmit support
├── ui/                     # React control application (YOU CREATE)
│   ├── src/
│   ├── package.json
│   └── README.md
├── captures/               # 60+ IR capture files
├── analysis/
│   ├── decoder.py         # Protocol analysis tool
│   └── protocol_spec.md   # Original spec (superseded by re-findings.md)
├── scripts/
│   └── capture.py         # IR capture script (still useful for new captures)
├── re-findings.md         # ⭐ COMPLETE PROTOCOL DOCUMENTATION
├── poc-prompt.md          # This file
└── platformio.ini         # PlatformIO config
```

---

## Getting Started

1. **Read `/re-findings.md`** - Understand the protocols thoroughly
2. **Design IR transmitter circuit** - Based on available components
3. **Choose communication method** - Serial or WiFi (recommend serial first)
4. **Update firmware** - Add IRsend + command parsing
5. **Create React UI** - Climate control + special functions
6. **Test with simple COOLIX** - Power OFF is easiest first test
7. **Test with BOSCH144** - Fixed state, then variable
8. **Iterate and improve** - Add reverse engineering features

---

## Important Notes

### Protocol Library Already Does Heavy Lifting!
- ✅ **Don't manually build BOSCH144 bytes** - use `IRBosch144Ac` class
- ✅ **Don't manually calculate checksums** - library handles it
- ✅ **Don't manually encode modes/temps** - use setter methods
- ✅ **Don't manually create COOLIX codes** - use `IRCoolixAC` class methods

**The library handles all encoding!** Your job is:
1. Hardware: Wire IR LED correctly
2. Firmware: Call library functions with user values
3. UI: Provide user-friendly interface to set values

### Testing Without AC Unit
- IR LED visibility: Use phone camera (IR shows as purple on camera)
- Protocol verification: Use the IR receiver to echo back transmitted commands
- Loopback test: Transmit on one pin, receive on another

### Communication Protocol Design
**Keep it simple!** Examples:

**Serial (text-based)**:
```
> SET TEMP 24.5
< OK TEMP 24.5
> SET MODE COOL
< OK MODE COOL
> SEND
< SENT BOSCH144 18 BYTES
```

**WiFi (JSON API)**:
```json
POST /api/ac/state
{
  "temp": 24.5,
  "mode": "COOL",
  "fan": "AUTO"
}

Response: {"status": "ok", "sent": "BOSCH144"}
```

---

## Questions?

If you need clarification on:
- **Protocol details**: See `/re-findings.md` sections
- **Existing captures**: Check `/captures` directory for examples
- **Library usage**: Check IRremoteESP8266 examples in `.pio/libdeps/nodemcuv2/IRremoteESP8266/examples/`
- **Hardware**: Standard IR LED circuits, plenty of online resources

**You have full autonomy** to:
- Choose serial vs WiFi communication
- Design firmware command protocol
- Structure React UI as you see fit
- Add features beyond requirements
- Make technical decisions

**Primary goal**: Prove we can control the AC by sending valid IR commands!

---

## Final Checklist

Before considering POC complete:

**Hardware**:
- [ ] IR transmitter circuit designed and built
- [ ] IR LED transmitting (verified with camera or receiver)
- [ ] Circuit stable and reliable

**Firmware**:
- [ ] IR transmit code working
- [ ] Communication protocol implemented
- [ ] Can send BOSCH144 commands
- [ ] Can send COOLIX commands
- [ ] Tested and debugged

**UI**:
- [ ] React app running
- [ ] Can set temperature/mode/fan
- [ ] Can trigger special functions
- [ ] Communication with ESP8266 working
- [ ] State display accurate
- [ ] Error handling implemented

**Integration**:
- [ ] Can turn AC on/off
- [ ] Can change temperature
- [ ] Can change modes
- [ ] Can change fan speed
- [ ] AC responds correctly to all commands

**Documentation**:
- [ ] Wiring diagram provided
- [ ] Firmware README updated
- [ ] UI README created
- [ ] Usage instructions documented

---

**Good luck! You have everything you need in `/re-findings.md` and the capture files. The hard reverse engineering work is done - now make it come alive!** 🚀
