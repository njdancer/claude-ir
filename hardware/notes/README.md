# Hardware Engineering Notes

> ⚠️ **The board is now the v2 ESP32-C3 cost-down redesign** (ESP32-C3-WROOM-02,
> AMS1117 LDO, AHT20 sensor, SMD USB-C; CH340C/JTAG/buck removed). Several notes
> below still describe the v1 WROOM-32E architecture and are being updated. The
> as-built description is the v2 change set in [`ROADMAP.md`](../../ROADMAP.md);
> where a note disagrees with the schematic, the schematic wins.

Design rationale for the ESP32 IR Remote Control Development Board (v1.1).

**Source of truth: the KiCad project** (`hardware/esp32-ir-remote.kicad_sch` /
`.kicad_pcb`). These notes capture *why* the circuit is the way it is — design
decisions, calculations, and constraints. They intentionally do not enumerate
connections; the schematic and exported netlist do that. If a note and the
schematic disagree, the schematic wins and the note should be fixed.

## Verification workflow

Every schematic change should be followed by:

```bash
./scripts/hardware-check.sh
```

This runs ERC and regenerates `hardware/esp32-ir-remote.net` via `kicad-cli`
(found in PATH or the macOS KiCad.app bundle). Commit the regenerated netlist
alongside the schematic change — the netlist diff is the reviewable record of
what changed electrically, since `.kicad_sch` diffs are dominated by graphics.

## Subsystems

| Note | Scope |
|------|-------|
| [power-supply.md](./power-supply.md) | USB-C input, protection, AP63203 buck regulation |
| [usb-serial.md](./usb-serial.md) | v2 native USB (no bridge); USB-C connector data path + hand-solder note |
| [esp32-mcu.md](./esp32-mcu.md) | WROOM-32E module, strapping pins, buttons, breakout header |
| [ir-transmitter.md](./ir-transmitter.md) | 4× TSAL6200 array with MOSFET driver |
| [ir-receiver.md](./ir-receiver.md) | TSOP38238 development receiver |
| [temp-sensor.md](./temp-sensor.md) | DHT22/AM2302 for Follow Me |
| [status-leds.md](./status-leds.md) | Serial activity and user LEDs |
| [layout.md](./layout.md) | PCB layout constraints: placement, routing, stackup (H2) |

## GPIO pin assignments

| GPIO | Function          | Direction | Notes                    |
|------|-------------------|-----------|--------------------------|
| 0    | Boot mode         | Input     | Strapping pin, pull-up   |
| 1    | UART TXD          | Output    | Also drives TX LED       |
| 2    | (Available)       | I/O       | Strapping pin, pull-down |
| 3    | UART RXD          | Input     | Also drives RX LED       |
| 4    | Temp sensor data  | I/O       | DHT22 single-wire        |
| 15   | (Available)       | I/O       | Strapping pin, pull-down |
| 16   | User LED 1        | Output    | Blue LED via MOSFET      |
| 17   | User LED 2        | Output    | Blue LED via MOSFET      |
| 18   | IR transmit       | Output    | 38kHz modulated signal   |
| 19   | IR receive        | Input     | Demodulated signal       |

All other GPIOs are available on the breakout header for expansion.

## Top-level design rationale

**Power architecture.** A synchronous buck converter (AP63203) was chosen over
an LDO for efficiency: an LDO would dissipate ~0.6W as heat at typical load
where the buck dissipates ~0.09W, enabling a smaller package. The 2A rating
provides headroom for simultaneous WiFi TX and IR emission peaks.

**IR LED drive.** A single MOSFET drives all four LEDs so they emit
simultaneously for maximum coverage. 100mA per LED gives good range at
reasonable power, and the 3.3V supply (rather than 5V) reduces resistor power
dissipation.

**Serial LEDs.** Active-low drive (cathode to GPIO) gives activity indication
without consuming extra GPIO pins — the UART signals themselves create the
blinking pattern during serial communication.

**Boot configuration.** The strapping pins (GPIO0, GPIO2, GPIO15) all have
pull resistors to guarantee boot into flash execution mode, and the auto-reset
circuit allows programming without manual button presses (buttons are still
fitted for recovery).

**Development-board posture.** The board prioritizes ease of assembly and
debugging over miniaturization: hand-solderable packages only, DevKitC-
compatible breakout header, and features (IR receiver, extensive status LEDs)
that a production board would omit. See `specs/hardware-dev-board-v1.md` for
the full requirements spec.
