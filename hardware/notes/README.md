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

## GPIO pin assignments (v2 board, ESP32-C3; r2 GPIO remap 2026-07-02)

The r2 autoresearch loop remapped the free GPIOs so each signal exits the
module on the side facing its board zone (B.Cu ground-plane slotting fell
390→167 mm). `scripts/ci/golden_netlist_v2.py` asserts this map; firmware
pins live in `platformio.ini` `[env:esp32-c3]` build_flags.

| GPIO | Function     | Direction | Notes                                     |
|------|--------------|-----------|-------------------------------------------|
| EN   | Reset (SW1)  | Input     | R5 pull-up + C6 POR RC                    |
| 9    | Boot (SW2)   | Input     | strapping, R6 pull-up                     |
| 10   | IR transmit  | Output    | 38 kHz → R13 → Q3 gate; D10 TX indicator  |
| 6    | IR receive   | Input     | TSOP38238                                 |
| 20   | I2C SDA      | I/O       | AHT20 + J4; R28 pull-up (UART0-RX pin)    |
| 21   | I2C SCL      | Output    | AHT20 + J4; R29 pull-up (UART0-TX pin) — ROM boot spew clocks the bus once per boot; firmware must bus-clear at init |
| 3    | User LED 1   | Output    | direct drive, yellow 0805                 |
| 1    | User LED 2   | Output    | direct drive, yellow 0805                 |
| 18/19| USB D−/D+    | I/O       | native USB-Serial-JTAG                    |
| 2, 8 | (strapping)  | —         | pull-ups only, left NC                    |
| 0,4,5,7 | spares    | I/O       | broken out on J4                          |

## Top-level design rationale

**Power architecture.** v2 uses a single AMS1117-3.3 LDO from USB 5 V (the v1
AP63203 buck was dropped in the cost-down: a 1S LiPo can't feed the buck's
dropout anyway, and on USB power the LDO's ~0.85 W is handled by a ~1050 mm²
top-side thermal pour + B.Cu island stitched under the tab — θ_JA ≈ 45–55 °C/W,
T_J ≈ 72 °C worst case). See [power-supply.md](./power-supply.md).

**IR LED drive.** A single MOSFET drives all four LEDs so they emit
simultaneously for maximum coverage. ~86 mA per LED (22 Ω Basic-part series
resistors) gives good range at reasonable power.

**Boot configuration.** The C3's strapping pins (IO2, IO8, IO9) carry
pull-ups; flashing runs over native USB-Serial-JTAG (no auto-reset circuit
needed — SW1/SW2 remain for manual recovery).

**Development-board posture.** The board prioritizes ease of assembly and
debugging over miniaturization: hand-solderable packages only, DevKitC-
compatible breakout header, and features (IR receiver, extensive status LEDs)
that a production board would omit. See `specs/hardware-dev-board-v1.md` for
the full requirements spec.
