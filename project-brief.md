# ESP8266 IR Remote Reverse Engineering Project

## Project Goal

Reverse engineer the IR protocol of an ActronAir air conditioner remote control using an ESP8266 (NodeMCU) dev board, with the eventual goal of building a custom HomeKit-compatible smart controller.

## Hardware Setup (Already Complete)

- **Board:** ESP8266 NodeMCU (likely NodeMCU v2 / ESP-12E)
- **IR Receiver:** CHQ1838 (38kHz, compatible with TSOP1838/VS1838B)
- **Wiring:**
  - CHQ1838 Pin 1 (OUT) → GPIO14 (D5 on NodeMCU)
  - CHQ1838 Pin 2 (GND) → GND
  - CHQ1838 Pin 3 (VCC) → 3.3V
- **IR LED:** Present on breadboard but not yet wired (will need transistor driver circuit later)

## Development Environment

- **Host OS:** macOS
- **Container Runtime:** Podman (used as Docker runtime for devcontainers)
- **IDE Support:** Maintain VS Code compatibility but primary interaction will be via CLI
- **Build System:** PlatformIO CLI (not Arduino IDE)
- **Language:** C++ (Arduino framework on ESP8266)

### Important: Hybrid Approach Required

**USB passthrough is not supported on Podman/macOS.** Podman 5.0+ uses Apple’s Virtualization framework (applehv) which doesn’t support USB device passthrough. The `--usb` flag only works with QEMU backends, which are deprecated on Mac.

Therefore, we must use a **hybrid approach**:

- **Devcontainer handles:** Code editing, compilation (`pio run`), analysis scripts, unit tests
- **Host (macOS) handles:** Flashing firmware (`pio run --target upload`), serial monitor (`pio device monitor`)

The project directory is mounted into the devcontainer, so build artifacts (in `.pio/`) are accessible from both environments. This is actually a clean separation of concerns.

## Key Libraries

- **IRremoteESP8266** (v2.8.6): The de facto library for IR send/receive on ESP8266. Supports 100+ protocols including many AC units. ActronAir is NOT in the supported list, so we’ll likely be capturing raw timings and potentially contributing a new protocol.
- **For later - HomeKit:** Arduino-HomeKit-ESP8266 (Mixiaoxiao) for native HomeKit support without bridge

## Your Tasks

### Phase 1: Environment Setup

1. **Create a devcontainer configuration** for this project that:

- Uses PlatformIO CLI for building/compiling
- Includes Python 3 for analysis scripts
- Mounts the project directory so build artifacts are accessible from host
- Does NOT attempt USB passthrough (not supported on macOS/Podman)

1. **Create the PlatformIO project structure:**

   ```
   project/
   ├── .devcontainer/
   │   ├── devcontainer.json
   │   └── Dockerfile (if needed)
   ├── platformio.ini
   ├── src/
   │   └── main.cpp
   ├── lib/
   ├── include/
   ├── test/
   ├── captures/           # Directory for captured IR data
   ├── analysis/           # Scripts for analyzing captures
   └── scripts/            # Helper scripts for host-side operations
   ```

1. **Create host-side helper scripts** (to be run on macOS, outside container):

- `scripts/flash.sh` - Detects serial port, flashes firmware
- `scripts/monitor.sh` - Opens serial monitor
- `scripts/capture.sh` - Runs serial monitor and saves output to timestamped file in captures/
  These scripts should be simple wrappers that:
- Auto-detect the serial port (look for `/dev/cu.usbserial-*` or `/dev/cu.SLAB_USBtoUART`)
- Use PlatformIO CLI commands
- Can be run from the project root

1. **Verify the setup:**

- Build compiles successfully in devcontainer: `pio run`
- Flash works from host: `./scripts/flash.sh`
- Serial monitor works from host: `./scripts/monitor.sh`
- Instruct me to press a button on any IR remote to verify receiver works

1. **Document the workflow clearly** in README.md:

- How to start devcontainer
- How to build (in container)
- How to flash and monitor (on host)
- How to run captures

### Phase 2: IR Capture System

1. **Create robust IR capture firmware** that:

- Captures raw timing data for all IR signals
- Outputs structured data (JSON or easily parseable format) suitable for automated analysis
- Includes timestamps
- Handles the large buffer sizes needed for AC protocols (often 100+ bits)
- Can differentiate between multiple captures

1. **Create capture logging system:**

- Serial output that can be piped to files
- Each capture should be saved with metadata (timestamp, optional label)
- Format should be suitable for both human review and automated parsing

1. **Build host-side analysis tooling:**

- Parse captured raw timing data
- Identify patterns (header marks/spaces, bit encoding schemes)
- Compare multiple captures of the same button to verify consistency
- Compare different buttons to identify which bits change
- Generate test fixtures from captures

### Phase 3: Protocol Analysis (Iterative)

1. **Systematic capture process:**

- I will send specific commands (power on, power off, temp up, temp down, mode changes, etc.)
- You will capture and label each one
- Build up a corpus of labeled captures

1. **Analysis workflow:**

- Identify the IR encoding scheme (likely NEC-like or similar pulse-distance encoding)
- Map out the bit structure
- Identify checksum/validation bytes if present
- Document findings

1. **Unit tests:**

- Write tests that validate our understanding of the protocol
- Tests should run on the host (not requiring hardware)
- Use captured data as test fixtures

### Phase 4: Transmission (Later)

Once we understand the protocol:

- Wire up IR LED with transistor driver
- Implement transmission
- Verify by sending commands to the actual AC unit

## Important Notes

### Serial Port on macOS

The NodeMCU typically shows up as something like:

- `/dev/cu.usbserial-0001`
- `/dev/cu.SLAB_USBtoUART`
- `/dev/tty.usbserial-*`

To find your device:

```bash
# List all serial devices
ls /dev/cu.*

# Or watch for changes when plugging/unplugging
ls /dev/cu.* # unplug board
ls /dev/cu.* # plug board back in - the new one is your device
```

The host-side scripts should auto-detect this, but may need manual override via environment variable.

### Host Prerequisites

The flash/monitor scripts run on the macOS host (not in the container), so PlatformIO CLI must be installed on the host:

```bash
# Install PlatformIO on macOS
pip install platformio
# or
brew install platformio
```

The scripts should check for this and give a helpful error if PlatformIO is not found.

### IRremoteESP8266 Library Details

- GPIO14 (D5) is a good choice for IR receive
- For AC protocols, use large capture buffer (1024+ uint16_t)
- The library’s `resultToSourceCode()` outputs raw data in a format that can be replayed
- `resultToHumanReadableBasic()` gives protocol info if recognized
- For unknown protocols, we’ll get raw timings which is what we need for reverse engineering

### ActronAir Remote Details

- Brand: ActronAir (Australian AC manufacturer)
- Remote shows: Temperature display, Mode button, Swing, Fan speed, Boost, LED, Humidity controls
- Display shows “24.0” in the photo - likely supports 0.5°C increments
- AC protocols typically send complete state with every button press (not just deltas)

## Communication Protocol With Me

1. **Before making changes:** Briefly explain what you’re about to do
1. **After each phase:** Summarize what was done and what’s next
1. **When you need me to interact with hardware:** Give clear instructions (e.g., “Press the power button on the ActronAir remote, pointing at the receiver”)
1. **When ready for manual testing:** Escalate with clear test instructions
1. **Save all captures:** Every IR capture should be persisted to a file with metadata

## Success Criteria for Phase 1

- [ ] Devcontainer builds and runs successfully with Podman
- [ ] PlatformIO can compile code for ESP8266 inside devcontainer (`pio run`)
- [ ] Host-side scripts exist and are documented
- [ ] Can flash firmware from host: `./scripts/flash.sh`
- [ ] Serial communication works from host: `./scripts/monitor.sh`
- [ ] IR receiver test passes - any IR remote triggers a capture
- [ ] Capture script works and saves data to files: `./scripts/capture.sh`
- [ ] README documents the full workflow

## Let’s Begin

Start by:

1. Creating the devcontainer configuration
1. Creating the initial PlatformIO project structure
1. Creating the host-side helper scripts
1. Building the firmware in the devcontainer

Then instruct me to:

1. Start the devcontainer (if you provide the command)
1. Run the flash script on host
1. Run the monitor script and press buttons on a remote

Ask me to perform any hardware interactions you need (pressing buttons, checking connections, etc.).
