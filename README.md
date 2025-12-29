# ESP8266 IR Remote Reverse Engineering

Reverse engineering the IR protocol of an ActronAir air conditioner remote control using an ESP8266 (NodeMCU) dev board.

## Hardware Setup

- **Board:** ESP8266 NodeMCU (NodeMCU v2 / ESP-12E)
- **IR Receiver:** CHQ1838 (38kHz, compatible with TSOP1838/VS1838B)
- **Wiring:**
  - CHQ1838 Pin 1 (OUT) → GPIO14 (D5 on NodeMCU)
  - CHQ1838 Pin 2 (GND) → GND
  - CHQ1838 Pin 3 (VCC) → 3.3V

## Development Environment

- **Host OS:** macOS
- **Container Runtime:** Podman (used as Docker runtime)
- **Build System:** PlatformIO CLI inside devcontainer
- **Flashing/Monitoring:** PlatformIO CLI on macOS host (USB passthrough not supported on Podman/macOS)

### Hybrid Approach

Because Podman on macOS doesn't support USB passthrough, this project uses a hybrid approach:

- **Devcontainer:** Code editing, compilation (`pio run`), analysis scripts
- **Host macOS:** Flashing firmware (`pio run --target upload`), serial monitor

The project directory is mounted into the devcontainer, so build artifacts in `.pio/` are accessible from both environments.

## Prerequisites

### On macOS Host

PlatformIO CLI must be installed on the host for flashing and monitoring:

```bash
# Option 1: Using pip
pip install platformio

# Option 2: Using Homebrew
brew install platformio
```

### For Devcontainer

- Docker Desktop or Podman
- VS Code with Dev Containers extension (optional, but recommended)

## Project Structure

```
.
├── .devcontainer/          # Devcontainer configuration
│   └── devcontainer.json
├── platformio.ini          # PlatformIO configuration
├── src/
│   └── main.cpp            # IR capture firmware
├── lib/                    # Custom libraries (if needed)
├── include/                # Header files
├── test/                   # Unit tests
├── captures/               # Captured IR data (timestamped files)
├── analysis/               # Python scripts for protocol analysis
├── scripts/                # Host-side helper scripts
│   ├── flash.sh            # Flash firmware from host
│   ├── monitor.sh          # Serial monitor from host
│   └── capture.sh          # Capture and save IR data
└── README.md
```

## Quick Start

### 1. Start the Devcontainer

Using VS Code:
```bash
# Open the project in VS Code
code .

# Press Cmd+Shift+P and select "Dev Containers: Reopen in Container"
```

Or using CLI:
```bash
# If using Podman
podman build -t esp8266-ir .devcontainer/
podman run -it -v $(pwd):/workspace esp8266-ir
```

### 2. Build the Firmware (in Devcontainer)

```bash
# Inside the devcontainer
pio run
```

This will:
- Download the ESP8266 platform and toolchain
- Download the IRremoteESP8266 library
- Compile the firmware
- Generate `.pio/build/nodemcuv2/firmware.bin`

### 3. Flash the Firmware (on macOS Host)

```bash
# From the project root on macOS (NOT in devcontainer)
./scripts/flash.sh
```

This script will:
- Auto-detect your ESP8266's serial port
- Flash the firmware using PlatformIO
- Display success message

Manual serial port override:
```bash
SERIAL_PORT=/dev/cu.usbserial-0001 ./scripts/flash.sh
```

### 4. Test the Setup

```bash
# Open serial monitor
./scripts/monitor.sh
```

You should see:
```
==========================================
ESP8266 IR Receiver - ActronAir Analysis
==========================================

IR Receiver Pin: GPIO14 (D5)
Capture Buffer: 1024 uint16_t values
Timeout: 50 ms
Min Unknown Size: 12

✓ IR Receiver initialized and listening...
✓ Point remote at receiver and press buttons

Waiting for IR signals...
```

Now press any button on any IR remote (TV, AC, etc.) pointing at the receiver. You should see a capture output.

## Workflow

### Capturing IR Data

#### Interactive Capture

For real-time monitoring:

```bash
./scripts/monitor.sh
```

Press buttons on the remote and observe the output in real-time.

#### Saved Capture Session

For systematic data collection:

```bash
# Capture with a descriptive label
./scripts/capture.sh power-on

# Or without label
./scripts/capture.sh
```

This will:
- Save all serial output to `captures/TIMESTAMP_LABEL.txt`
- Display output in real-time
- Press Ctrl+C when done to save and exit

Example capture workflow:
```bash
./scripts/capture.sh power-on       # Press power button
./scripts/capture.sh power-off      # Press power again
./scripts/capture.sh temp-up        # Press temp up
./scripts/capture.sh temp-down      # Press temp down
./scripts/capture.sh mode-cool      # Change to cool mode
./scripts/capture.sh mode-heat      # Change to heat mode
```

### Making Changes to the Code

1. Edit `src/main.cpp` in the devcontainer (or locally with your IDE)
2. Build in devcontainer: `pio run`
3. Flash from host: `./scripts/flash.sh`
4. Monitor from host: `./scripts/monitor.sh`

### Analysis (Phase 2)

Python scripts in the `analysis/` directory will parse captured data to:
- Extract raw timing patterns
- Identify encoding schemes (NEC, RC5, custom, etc.)
- Compare multiple captures of the same button
- Identify which bits change between different commands
- Generate protocol documentation

## Troubleshooting

### Serial Port Not Found

If the flash/monitor scripts can't find your serial port:

```bash
# List all serial devices
ls -l /dev/cu.*

# Look for devices like:
# /dev/cu.usbserial-*
# /dev/cu.SLAB_USBtoUART
# /dev/cu.wchusbserial*

# Manually specify the port
SERIAL_PORT=/dev/cu.YOUR_DEVICE ./scripts/flash.sh
```

### Build Fails in Devcontainer

```bash
# Clean and rebuild
pio run --target clean
pio run
```

### No IR Signals Captured

1. Check wiring:
   - CHQ1838 OUT → GPIO14 (D5)
   - CHQ1838 GND → GND
   - CHQ1838 VCC → 3.3V

2. Verify the receiver is working:
   - Most IR receivers have no visible indication, but some remotes' IR LEDs can be seen through a phone camera

3. Try a different remote (TV, stereo, etc.) to verify hardware works

4. Check serial monitor is connected and showing the startup banner

### Buffer Overflow Warning

If you see buffer overflow warnings, increase `kCaptureBufferSize` in `src/main.cpp`:

```cpp
const uint16_t kCaptureBufferSize = 2048;  // Increase from 1024
```

Then rebuild and reflash.

## Output Format

Each IR capture outputs:

1. **Human Readable:** Protocol name (if recognized), bits, value
2. **Raw Timings (JSON):** Complete timing array for analysis
3. **Source Code:** C++ code to replay the signal
4. **Statistics:** Capture count, timing, memory usage

Example:
```
========================================
CAPTURE #1 @ 12345 ms
========================================

--- Human Readable ---
Protocol: UNKNOWN
Bits: 0
Value: 0x0

--- Raw Timings (JSON) ---
{
  "protocol": "UNKNOWN",
  "bits": 0,
  "value": "0x0",
  "timestamp": 12345,
  "rawlen": 227,
  "raw_timings": [
    9000,
    4500,
    ...
  ]
}

--- Source Code (for replay) ---
uint16_t rawData[227] = {9000, 4500, ...};

--- Statistics ---
Total Captures: 1
Time Since Last: 0 ms
Free Heap: 45328 bytes

========================================
END CAPTURE
========================================
```

---

# POC: ActronAir IR Control System

A complete proof-of-concept implementation for controlling an ActronAir AC unit via IR transmission. This POC validates the protocol analysis and demonstrates end-to-end control through a web interface.

## Architecture Overview

```
Browser → React Router App (Node.js) → Serial → ESP8266 → IR LED → AC Unit
         (Client UI + Server API)
```

The system consists of three components:
1. **Hardware**: IR LED transmitter circuit on ESP8266
2. **Firmware**: IR transmit capability with serial command interface
3. **React Router App**: Full-stack web application for AC control

## Hardware: IR Transmitter Circuit

### Additional Components Required

Beyond the IR receiver setup, you'll need:
- **IR LED**: 940nm (5mm, clear lens)
- **Transistor**: 2N2222 or BC547 (NPN)
- **Resistors**:
  - 470Ω (base resistor)
  - 10Ω (LED current limiting)

### Circuit Diagram

```
ESP8266 GPIO4 (D2) ─┬─[470Ω]─── 2N2222 Base
                    │              │
                    │         Collector
                    │              │
                    │         IR LED Cathode (-)
                    │              │
                    │         IR LED Anode (+)
                    │              │
                    │          [10Ω]
                    │              │
                    └──────────── 3.3V

ESP8266 GND ────────────────── Emitter
```

### Complete Wiring

**IR Receiver (existing):**
- CHQ1838 OUT → GPIO14 (D5)
- CHQ1838 GND → GND
- CHQ1838 VCC → 3.3V

**IR Transmitter (new):**
- GPIO4 (D2) → 470Ω resistor → 2N2222 Base
- 2N2222 Collector → IR LED Cathode (-)
- IR LED Anode (+) → 10Ω resistor → 3.3V
- 2N2222 Emitter → GND

### Testing the IR LED

**Visual Test**: Use your phone camera (especially front-facing cameras work well) to view the IR LED. When transmitting, you should see a purple/white glow.

**Range Test**: The IR LED should work at 2-3 meters from the AC unit for reliable control.

## Firmware: Serial Command Interface

The firmware supports both IR receive (for debugging) and IR transmit (for control). It implements the ActronAir protocol using the IRremoteESP8266 library.

### Supported Commands

The firmware accepts commands via serial at 115200 baud:

| Command | Parameters | Example | Description |
|---------|------------|---------|-------------|
| `POWER:ON` | - | `POWER:ON` | Power on (BOSCH144) |
| `POWER:OFF` | - | `POWER:OFF` | Power off (COOLIX 0xB27BE0) |
| `TEMP:<value>` | 16.0-30.0 (0.5° steps) | `TEMP:22.5` | Set temperature |
| `MODE:<mode>` | COOL/HEAT/DRY/FAN/AUTO | `MODE:COOL` | Set mode |
| `FAN:<speed>` | AUTO/20/40/60/80/100 | `FAN:60` | Set fan speed |
| `SWING` | - | `SWING` | Toggle swing (COOLIX) |
| `BOOST` | - | `BOOST` | Activate boost (COOLIX) |
| `LED` | - | `LED` | Toggle LED (COOLIX) |
| `STATE` | - | `STATE` | Query current state |
| `DEBUG:ON/OFF` | - | `DEBUG:ON` | Enable debug logging |

**Response Format**: All commands respond with `OK:<message>` on success or `ERROR:<message>` on failure.

**Example Session**:
```
> STATE
< OK:Power=OFF,Temp=22.0,Mode=COOL,Fan=AUTO

> POWER:ON
< OK:Power ON, sent BOSCH144 command

> TEMP:24.5
< OK:Temperature set to 24.5C

> STATE
< OK:Power=ON,Temp=24.5,Mode=COOL,Fan=AUTO
```

### Protocol Details

**ActronAir uses two IR protocols:**
- **BOSCH144**: For climate control (power on + temp/mode/fan)
- **COOLIX**: For power off and special functions (swing, boost, LED)

Both protocols are fully supported by the IRremoteESP8266 library - no custom encoding required!

### Building and Flashing the POC Firmware

The POC firmware is in the main `src/main.cpp` with IR transmit capability enabled.

```bash
# Build firmware (in devcontainer or host)
pio run

# Flash to ESP8266 (from host)
./scripts/flash.sh

# Test via serial monitor
./scripts/monitor.sh

# Try a command
POWER:ON
```

## React Router Web App

A full-stack React application providing a web interface for AC control. Built with React Router v7 framework mode.

### Features

- **Real-time AC Control**: Power, temperature, mode, fan speed, special functions
- **State Display**: Shows current AC state (refreshed after each command)
- **Responsive UI**: Tailwind CSS styling, works on desktop and mobile
- **Loading States**: Visual feedback during command execution
- **Error Handling**: Displays communication errors
- **Mock Serial Mode**: Allows development and testing without hardware

### Tech Stack

- **React Router v7**: Framework mode (client + server in one codebase)
- **TypeScript**: Type-safe development
- **Tailwind CSS**: Utility-first styling
- **Vite**: Fast development server with HMR
- **Node.js SerialPort**: ESP8266 communication (server-side)
- **Vitest**: Unit testing (52 tests)
- **Playwright**: E2E testing (11 tests)

### Setup and Installation

```bash
# Navigate to app directory
cd app/

# Install dependencies (using pnpm)
pnpm install

# Start development server
pnpm run dev

# Open browser
# http://localhost:5173
```

**First Run**: The app will attempt to connect to the ESP8266 via serial. Make sure:
1. ESP8266 is connected via USB
2. Firmware is flashed with POC code
3. Serial port is correct (see Configuration below)

### Configuration

**Serial Port**: Edit `app/lib/serial.server.ts` to set your serial port:

```typescript
// macOS
path: '/dev/cu.usbserial-0001'

// Linux
path: '/dev/ttyUSB0'

// Windows
path: 'COM3'
```

**Auto-detect**: On macOS/Linux, the app will try common port patterns.

**Mock Mode**: For development without hardware, set environment variable:

```bash
MOCK_SERIAL=true pnpm run dev
```

This uses a simulated ESP8266 that responds to all commands without real hardware.

### Testing

The app includes comprehensive test coverage:

**Unit Tests (52 tests, all passing)**:
```bash
# Run all unit tests
pnpm test

# Watch mode (run tests on file changes)
pnpm test:watch

# Coverage report
pnpm test:coverage

# Interactive UI
pnpm test:ui
```

Tests cover:
- Mock serial manager (40 tests)
- Serial helper functions (12 tests)
- Command parsing, state management, error handling

**E2E Tests (11 tests, 8 passing, 3 skipped)**:
```bash
# Run E2E tests (automatically starts dev server)
pnpm test:e2e

# Run with UI (interactive mode)
pnpm test:e2e --ui

# Debug mode
pnpm test:e2e --debug
```

E2E tests validate:
- Full control workflows (power, mode, fan)
- State persistence across multiple commands
- Error handling and loading states
- Button interactions and UI feedback

**Note**: 3 E2E tests are skipped due to a known limitation: Playwright's `dispatchEvent()` doesn't trigger React 19's `onChange` handler for range inputs due to React's event delegation system. Diagnostic testing confirmed:
- ✅ Elements render correctly
- ✅ Initial values display properly
- ❌ Synthetic events don't trigger React's onChange (value doesn't update)

The temperature slider **works correctly in manual testing** - this is purely a test automation limitation. Temperature control logic is fully covered by unit tests (52/52 passing). For the POC, rely on manual testing for temperature slider validation.

### Project Structure

```
app/
├── app/
│   ├── routes/
│   │   └── home.tsx              # Main control page (loader + action + UI)
│   ├── components/               # UI components (if split out)
│   ├── lib/
│   │   ├── serial.server.ts      # Real serial manager
│   │   └── serial.mock.server.ts # Mock serial for testing
│   └── test/
│       └── setup.ts              # Test configuration
├── tests/
│   ├── unit/
│   │   ├── serial.mock.test.ts       # Mock serial tests (40)
│   │   └── serial.helpers.test.ts    # Helper function tests (12)
│   └── e2e/
│       └── control-flow.test.ts      # E2E workflow tests (11)
├── package.json
├── vitest.config.ts              # Unit test config
├── playwright.config.ts          # E2E test config
└── react-router.config.ts        # Framework config
```

### Development Workflow

**With Hardware (Real ESP8266)**:
1. Connect ESP8266 via USB
2. Verify serial port in `serial.server.ts`
3. Start app: `pnpm run dev`
4. Open http://localhost:5173
5. Control your AC unit!

**Without Hardware (Mock Mode)**:
1. Set `MOCK_SERIAL=true`
2. Start app: `pnpm run dev`
3. Open http://localhost:5173
4. Test UI with simulated responses

**Making Changes**:
1. Edit files in `app/` directory
2. Vite HMR will auto-reload
3. Run tests: `pnpm test`
4. Test in browser

### Building for Production

```bash
# Build production bundle
pnpm run build

# Start production server
pnpm run start
```

The production build creates an optimized bundle with:
- Server-side rendering
- Minified assets
- Type-checked code

## Usage Guide

### Quick Start

1. **Flash the firmware**:
   ```bash
   ./scripts/flash.sh
   ```

2. **Start the web app**:
   ```bash
   cd app/
   pnpm install
   pnpm run dev
   ```

3. **Open browser**: http://localhost:5173

4. **Control your AC**:
   - Click "Power ON" to turn on the AC
   - Adjust temperature with slider (16-30°C)
   - Select mode (COOL/HEAT/DRY/FAN/AUTO)
   - Set fan speed (AUTO or 20-100%)
   - Use special functions (Swing, Boost, LED)

### Testing the POC

**Phase 1: Verify IR Transmission**
```bash
# Monitor serial output
./scripts/monitor.sh

# In another terminal, use the web app to send a command
# Watch the serial output for IR transmission confirmation
```

**Phase 2: Verify AC Responds**
- Point ESP8266 IR LED at AC unit (2-3 meter range)
- Use web app to send "Power ON" command
- AC unit should power on and beep
- Try changing temperature, mode, fan speed

**Phase 3: Test All Functions**
- Power ON/OFF
- Temperature range: 16.0°C to 30.0°C (0.5° increments)
- All modes: COOL, HEAT, DRY, FAN, AUTO
- All fan speeds: AUTO, 20%, 40%, 60%, 80%, 100%
- Special functions: Swing, Boost, LED

## Troubleshooting

### Web App Issues

**Error: "Serial port not initialized"**
- Check ESP8266 is connected via USB
- Verify serial port path in `app/lib/serial.server.ts`
- Try: `ls -l /dev/cu.*` (macOS) or `ls -l /dev/ttyUSB*` (Linux)

**Error: "Cannot find module 'serialport'"**
- Run: `cd app/ && pnpm install`

**App shows "Power: OFF" but AC is on**
- The app tracks state based on commands sent, not actual AC state
- The AC doesn't report its state back
- Click the command you want to send to sync

**Commands not reaching ESP8266**
- Check serial monitor: `./scripts/monitor.sh`
- Send a command from the web app
- You should see command appear in serial output
- If not, check serial port configuration

### IR Transmission Issues

**AC unit not responding**
- Verify IR LED is working (use phone camera)
- Check distance (should be <3 meters)
- Check line of sight (IR requires direct view)
- Verify wiring (GPIO4 → resistor → transistor → LED)

**IR LED not lighting up**
- Check transistor orientation (flat side reference)
- Verify resistor values (470Ω base, 10Ω LED)
- Test with multimeter: GPIO4 should pulse when sending

**Commands work sometimes**
- Check LED current (should be ~100-150mA when transmitting)
- Ensure LED is pointed at AC unit
- Try moving ESP8266 closer

### Serial Communication Issues

**"Error: Port is not open"**
- Close any other serial monitors (Arduino IDE, screen, etc.)
- Unplug and replug ESP8266
- Restart the web app

**"Error: Timeout"**
- ESP8266 not responding to commands
- Verify firmware is flashed correctly
- Check serial baud rate (should be 115200)
- Monitor serial output to see if ESP8266 is running

## Testing Documentation

### Test Coverage Summary

| Test Type | Count | Status | Coverage |
|-----------|-------|--------|----------|
| C++ Unit Tests (Firmware) | 17 | ✅ All passing | IR protocols, command parsing |
| JavaScript Unit Tests | 52 | ✅ All passing | Serial manager, helpers |
| E2E Tests | 11 | ⚠️ 8 passing, 3 skipped | Full control workflows (excl. temp slider) |

**Total**: 77 automated tests passing, 3 skipped (temp slider - manual testing required)

**Skipped Tests**: Temperature slider tests skipped due to Playwright/React 19 event delegation incompatibility. Temperature control fully validated by unit tests + manual testing.

### Running All Tests

```bash
# Firmware tests (in project root)
pio test

# Web app unit tests
cd app/
pnpm test

# Web app E2E tests
pnpm test:e2e

# All web app tests with coverage
pnpm test:coverage && pnpm test:e2e
```

### CI/CD Compatibility

All tests run without hardware using mock serial interface:
- Set `MOCK_SERIAL=true` environment variable
- Tests simulate ESP8266 responses
- Validates UI logic, state management, error handling
- Ready for GitHub Actions, GitLab CI, etc.

## Protocol Analysis Results

For complete protocol analysis and reverse engineering findings, see:
- **`re-findings.md`**: Detailed protocol documentation
- **`captures/`**: 60+ IR capture files
- **Analysis scripts**: Python tools for protocol analysis (if created)

**Key Findings**:
- ActronAir uses **BOSCH144** for climate control (power on + state)
- ActronAir uses **COOLIX** for power off and special functions
- Both protocols are standard and supported by IRremoteESP8266
- Temperature range: 16.0-30.0°C in 0.5° increments
- 5 modes: COOL, HEAT, DRY, FAN, AUTO
- 6 fan speeds: AUTO, 20%, 40%, 60%, 80%, 100%

## Project Status

- ✅ **Phase 1**: Environment Setup (COMPLETE)
  - ✅ Devcontainer configured
  - ✅ PlatformIO project created
  - ✅ Host-side scripts working
  - ✅ Build and flash verified

- ✅ **Phase 2**: Protocol Analysis (COMPLETE)
  - ✅ Systematic capture of ActronAir remote
  - ✅ Protocol identified (BOSCH144 + COOLIX)
  - ✅ All commands documented
  - ✅ Protocol tested and validated

- ✅ **Phase 3**: Transmission POC (COMPLETE)
  - ✅ IR LED transmitter circuit assembled
  - ✅ Firmware with IR transmit implemented
  - ✅ Serial command interface working
  - ✅ React Router web app built
  - ✅ Comprehensive test suite (80 tests)
  - ✅ AC unit control verified

- ⏸️ **Phase 4**: HomeKit Integration (NOT STARTED)
  - [ ] Implement HomeKit accessory
  - [ ] Create custom AC controller
  - [ ] HomeKit pairing and control

## Next Steps

Potential enhancements:
- **HomeKit Integration**: Make the AC controllable via HomeKit/Siri
- **State Polling**: Add IR receive to detect AC state changes from physical remote
- **Scheduling**: Add timer functionality (turn on/off at specific times)
- **MQTT Integration**: For Home Assistant or other home automation platforms
- **Mobile App**: Native iOS/Android app instead of web interface
- **Multi-Zone Support**: Control multiple AC units

## References

- [IRremoteESP8266 Library](https://github.com/crankyoldgit/IRremoteESP8266)
- [Adding Support for a New AC Protocol](https://github.com/crankyoldgit/IRremoteESP8266/wiki/Adding-support-for-a-new-AC-protocol)
- [PlatformIO Documentation](https://docs.platformio.org/)
- [ESP8266 Arduino Core](https://github.com/esp8266/Arduino)

## License

This project is for educational and personal use.
