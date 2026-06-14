# ESP32 IR Remote Control Development Board - Hardware Specification v1.4

## Overview

This specification defines the hardware requirements for a development board that enables testing and development of an ESP32-based smart AC remote control system using infrared transmission. The board serves as a transition from the current ESP8266 breadboard proof-of-concept to a manufacturable design suitable for firmware development and eventual production refinement.

> ⚠️ **SUPERSEDED ARCHITECTURE — read this first (v2.0, 2026-06).** The
> fabricated board is the **v2 ESP32-C3 cost-down redesign**, NOT the
> ESP32-WROOM-32E architecture described in the body of this document below.
> The as-built board:
> - **MCU: ESP32-C3-WROOM-02-N4** (LCSC C2934560), not WROOM-32E. The C3's
>   native USB-Serial-JTAG let the **entire CH340C USB-serial subsystem be
>   deleted** (no bridge, no auto-reset FETs).
> - **Power: AMS1117-3.3 LDO** (U1), not the AP63203 buck + inductor.
> - **Temp/humidity: AHT20** I2C sensor (U5), not the AM2302/DHT22.
> - **USB-C: SMD 16P XKB U262** receptacle (J2), not the THT GCT part.
> - Status LEDs moved to 0805 SMD; JTAG header and TX/RX activity LEDs removed.
>
> The **as-built description is the v2 change set in [`ROADMAP.md`](../ROADMAP.md)**
> (the project state file) and the live schematic/netlist under `hardware/`.
> The WROOM-32E content below is retained for v1.4 design rationale only and
> is being rewritten for v2 as a follow-up. Where this spec body and the
> schematic disagree, **the schematic wins.**

> **Revision note (v1.4):** Pre-order cost/availability pass. The assembly
> model is now explicitly **SMT-only machine assembly plus a hand-solder
> kit** (see [Assembly Considerations](#assembly-considerations)): JLCPCB
> places only top-side SMD parts, and every through-hole part plus the easy
> two-terminal SMD Extended parts ship loose. Two Basic-part substitutions:
> the IR driver MOSFET Q3 (IRLML6344 → AO3400A, same SOT-23/pinout, meets
> all stated requirements) and the BOOT/RESET switches (TS-1088R → XKB
> TS-1187A-B-A-B, SMD 5.1×5.1mm 4-pad — same-row terminals internally
> common). Only three Extended parts remain machine-placed: the buck
> regulator, the CH340C, and the WROOM module.
>
> **Revision note (v1.3):** Auto-reset transistors Q1/Q2 changed from NPN BJTs
> (S8050) to 2N7002 N-channel MOSFETs. The SOT-23 pinouts map 1:1 (B→G, E→S,
> C→D), so the change is layout-neutral; it consolidates Q1/Q2 onto the same
> BOM line as Q4/Q5 (JLCPCB Basic part C8545). Circuit topology and truth
> table are unchanged. The R21/R26 bypass links changed from 0Ω to **470Ω**
> to limit FET body-diode current into the CH340C while RESET/BOOT is held
> (restores BJT-grade benignity); they remain desolder-to-disable. See
> [Auto-Reset Circuit](#auto-reset-circuit).
>
> **Revision note (v1.2):** The board target shifted toward "get it fabricated." The
> bulky 2×19 ESP32-DevKitC debug breakout header is **removed** and replaced with a
> small set of purposeful connection points (I2C Qwiic, a compact spare-GPIO + power
> header, an external IR-emitter header, and an unpopulated JTAG footprint) — see
> [Connection Points and Expansion](#connection-points-and-expansion). The
> WROOM-32E (PCB antenna) is retained; the U.FL external-antenna option is deferred.
> This revision also reconciles the spec to the KiCad schematic (the source of
> truth): auto-reset bypass jumpers JP2/JP3 are now R21/R26 0Ω SMD links, and the
> buck inductor L1 is 4.7µH. Several H1.4 datasheet-review fixes are folded in (IR-TX
> gate resistor, IR-RX supply filter). The Bill of Materials below lags the schematic
> on reference designators and MUST be regenerated from it (see the BOM note).

### Design Philosophy

The board prioritizes ease of assembly and debugging over miniaturization. Components MUST be hand-solderable, which excludes packages like BGA but permits both through-hole and large SMD components (SOT-223, SOIC, etc.). Standard 2.54mm (0.1") pin headers are PREFERRED for development flexibility, but other pitches and connection methods are acceptable where hand assembly remains feasible.

The design intentionally includes features (such as IR receiver and extensive status LEDs) that may be omitted from production boards but facilitate rapid development iteration.

### Manufacturing Target

The board MUST be manufacturable through JLCPCB's standard PCB service with components readily available through common distributors (Digikey, Mouser, LCSC). Two-layer PCB construction is acceptable given the modest component count and frequency requirements.

## Functional Requirements

### Primary Functions

The board MUST provide:

1. **Omnidirectional IR Transmission**: Reliable infrared signal transmission across a 180-degree horizontal arc at distances up to 10 meters. The system must function with indirect line-of-sight (wall reflections) to match typical consumer remote control behavior.

2. **Environmental Sensing**: Accurate room temperature measurement (±1°C) for implementing "Follow Me" functionality where the AC unit adjusts output based on temperature at the remote's location.

3. **Development Support**: Comprehensive debugging capabilities including IR signal reception verification, serial communication monitoring, and visual feedback of system state.

### IR Transmission Characteristics

The IR transmitter MUST generate 940nm infrared pulses modulated at 38kHz carrier frequency compatible with the COOLIX and BOSCH144 protocols identified in the reverse engineering phase. The transmission pattern must support both sustained transmission (for BOSCH144's 144-bit messages) and short burst commands (for COOLIX's 24-bit special functions).

Unlike the current breadboard implementation which requires precise aiming, the production system must achieve reliable communication when the remote is casually pointed toward the AC unit or nearby surfaces. This requires multiple IR emitters with overlapping coverage areas rather than a single high-power directional emitter.

### Power Delivery

The board MUST operate from USB-C power (5V nominal) and maintain stable 3.3V regulation under varying load conditions. Peak current draw during WiFi transmission with simultaneous IR emission (approximately 350-400mA) must not cause voltage droop exceeding 100mV at the ESP32's power pins.

The power subsystem MUST implement overcurrent protection (trip at 2A) and overvoltage protection (clamp below 6V). Reverse polarity protection is omitted for the USB-C input as the connector enforces correct orientation; reverse protection MAY be added on the battery input path when that feature is implemented.

### Battery Support

Battery operation is **deferred to v2**. This development board is USB-powered only.

The spare-GPIO + power header (see [Connection Points and Expansion](#connection-points-and-expansion)) exposes 3.3V and 5V rails, enabling experimentation with external battery and power management circuits on a separate prototyping board. A jumper (JP1) on the buck converter's EN pin allows disabling the internal regulator when testing external power solutions (see Voltage Regulation section).

## Component Specifications

### Microcontroller Module

**Specified Module**: ESP32-WROOM-32E-N4 (Espressif WiFi+BT module)

The board MUST use the ESP32-WROOM-32E-N4 module directly, rather than a development board. This provides full control over the supporting circuitry while using a proven, FCC/CE certified RF module. The module integrates:

- ESP32-D0WD-V3 dual-core Xtensa LX6 @ 240MHz
- 4MB SPI flash (N4 variant)
- 520KB internal SRAM
- 40MHz crystal oscillator
- PCB trace antenna
- All required RF matching and filtering

**Module Specifications**:

- Dimensions: 18mm × 25.5mm × 3.1mm
- Pins: 38 castellated pads at 1.27mm pitch
- Operating voltage: 3.0-3.6V (3.3V nominal)
- Operating temperature: -40°C to +85°C
- Deep sleep current: <5µA

The module exposes sufficient GPIO pins to support:

- 4× IR LED driver signals
- 1× IR receiver input
- I2C interface (SDA/SCL) for temperature sensor
- UART0 (programming and debug)
- User programmable GPIO for expansion

**Required Support Circuitry**: Unlike a development board, the bare module requires external circuitry for:

1. **Power regulation**: 3.3V supply (provided by AP63203 synchronous buck converter per this spec)
2. **USB-to-UART bridge**: For programming and serial communication (see USB-to-UART Bridge section)
3. **Auto-reset circuit**: Transistor network for automatic bootloader entry (see Auto-Reset Circuit section)
4. **EN pin conditioning**: RC delay circuit for reliable power-on reset
5. **Strapping pin management**: Pull-ups/pull-downs on boot mode pins

**Power Architecture**: The board provides 3.3V regulation via the AP63203 synchronous buck converter specified in the Voltage Regulation section. The module draws:

- Typical: 80-120mA (WiFi idle)
- Peak: 240mA (WiFi TX burst)
- Deep sleep: <5µA

The 2A-rated buck converter provides adequate headroom for the module plus all peripherals.

**Mounting**: The module's castellated pads can be hand-soldered to the PCB. For easier assembly, the PCB layout SHOULD include:

- Extended pads beyond the module footprint for solder iron access
- Solder mask relief around pads
- Clear silkscreen indicating pin 1 orientation

### Infrared Emitters

**Quantity**: 4 emitters
**Package**: 5mm (T-1 3/4) through-hole or equivalent hand-solderable package

The board MUST position four IR LEDs with their optical axes oriented at approximately 0°, 45°, 90°, and 135° from the board's centerline, providing overlapping hemispherical coverage. All emitters drive simultaneously during transmission to maximize signal strength across the coverage area.

**LED Requirements**:

- Peak wavelength: 940nm ±10nm (matches TSOP receiver sensitivity peak)
- Continuous forward current: ≥100mA
- Peak pulsed current: ≥1A (at 10% duty cycle, for future high-power modes)
- Forward voltage: 1.2-1.5V typical
- Radiant intensity: ≥30 mW/sr @ 100mA
- Viewing angle: ≥20° for adequate coverage overlap

**Suggested Part**: Vishay TSAL6200 meets all requirements and is widely available.

Each LED MUST be driven through an independent NPN transistor with base current limiting and collector current limiting resistors. The current limiting resistor value MUST provide 80-100mA LED current when driven from the regulated supply, balancing transmission power against LED lifetime and power dissipation.

### Infrared Receiver

**Quantity**: 1
**Purpose**: Development and debugging only
**Package**: Through-hole 3-pin module or equivalent hand-solderable package

**Receiver Requirements**:

- Center frequency: 38kHz (matches COOLIX/BOSCH144 carrier frequency)
- Supply voltage: 3.3V compatible
- Output: Active-low demodulated signal
- Built-in bandpass filter and AGC
- Minimum detectable power: <1 mW/m² typical for IR receiver modules

**Suggested Parts**: Vishay TSOP1838, TSOP4838, or equivalent 38kHz receiver modules.

The IR receiver enables verification of transmitted waveforms and debugging of protocol encoding. It MUST connect to a GPIO pin configured with interrupt capability to capture timing-accurate signal edges. While essential during development, production boards may omit this component.

### Temperature Sensor

**Interface**: Single-wire (proprietary protocol)
**Mounting**: Through-hole module with pin headers

**Sensor Requirements**:

- Temperature accuracy: ±0.5°C across 18-28°C range (typical indoor AC environment)
- Supply voltage: 3.3V compatible
- Sleep current: <10µA (for battery operation testing)
- Response time: <2 seconds for room temperature changes

**Additional Capabilities**:

- Humidity sensing (enables comfort index calculations)

**Specified Part**: DHT22 (AM2302) temperature and humidity sensor module. The module includes the required pull-up resistor on the data line. Connect to any available GPIO pin.

### USB-C Power Connector

**Connector Requirements**:

- Mounting: Through-hole or large SMD with hand-solderable pins (not fine-pitch SMT-only)
- Pinout: USB 2.0 minimum (VBUS, GND, CC1, CC2 accessible; D+/D- optional)
- Mechanical strength: Through-hole anchor pins or large mounting pads
- Current rating: ≥3A continuous

**Specified Connector**: GCT USB4085-GF-A (fully through-hole USB-C receptacle)

This connector is specified due to its through-hole construction enabling reliable hand assembly and its availability from major distributors. Alternative through-hole USB-C receptacles with equivalent pinout are acceptable.

**Power Delivery Configuration**: CC1 and CC2 pins MUST connect to ground through 5.1kΩ ±5% resistors to signal 5V/3A power capability to USB-PD sources. This resistor configuration enables the board to draw sufficient current from modern USB-C chargers without implementing complex PD negotiation.

**USB Data Lines**: D+ and D- pins connect to the USB-to-UART bridge IC for programming and serial communication (see USB-to-UART Bridge section).

### USB-to-UART Bridge

The board MUST include a USB-to-UART bridge IC to enable programming and serial communication with the ESP32 module. This replaces the functionality provided by the CP2102 on the ESP32-DevKitC.

**Bridge IC Requirements**:

- USB 2.0 Full Speed (12 Mbps) support
- 3.3V I/O compatible (no level shifting required)
- Baud rates up to 921600 (required for fast firmware upload)
- DTR and RTS flow control signals (required for auto-reset circuit)
- Package: Hand-solderable (SOIC, SSOP, or QFN with exposed pad)
- Built-in oscillator preferred (reduces external component count)
- Windows/macOS/Linux driver support

**Recommended ICs** (in order of preference):

1. **CP2102N** (Silicon Labs) - QFN-28 or QFN-24
   - Direct replacement for DevKitC's CP2102
   - Excellent driver support across all platforms
   - Built-in oscillator, minimal external components
   - Configurable GPIO pins (optional features)
   - Note: QFN package requires careful hand-soldering or reflow

2. **CH340C** (WCH) - SOP-16
   - Lower cost alternative
   - Built-in oscillator (no external crystal needed)
   - Wider pin pitch (easier hand soldering than QFN)
   - Good driver support (built into modern OS versions)
   - Requires 100nF decoupling capacitor

3. **CH340G** (WCH) - SOP-16
   - Similar to CH340C but requires external 12MHz crystal
   - Slightly lower cost, slightly more complex BOM

**Recommended Implementation**: CH340C in SOP-16 package

The CH340C offers the best balance of hand-solderability, cost, and simplicity for this development board. Its SOP-16 package (1.27mm pitch) is manageable with a fine-tip soldering iron, and the built-in oscillator eliminates the need for an external crystal.

**CH340C Circuit Requirements**:

```
USB D+ ──────────────────── CH340C UD+
USB D- ──────────────────── CH340C UD-
3.3V ────┬─────────────── CH340C VCC
         │
         └─────────────── CH340C V3 ───[100nF]─── GND
GND ─────────────────────── CH340C GND
GND ─────────────────────── CH340C R232 (pin 15)
CH340C TXD ─────────────── ESP32 U0RXD (GPIO3)
CH340C RXD ─────────────── ESP32 U0TXD (GPIO1)
CH340C DTR# ────[R21 470Ω]── Auto-reset circuit (cross-coupled, DTR side)
CH340C RTS# ────[R26 470Ω]── Auto-reset circuit (cross-coupled, RTS side)
```

**Notes**:
- TX/RX are crossed: CH340C TXD connects to ESP32 RXD, and vice versa
- **3.3V Operation**: V3 must be tied to VCC (both connected to 3.3V). This bypasses the internal regulator. Add 100nF decoupling capacitor from V3 to GND.
- **R232 Pin**: Must be tied to GND for TTL-level output compatible with ESP32. If tied high, outputs RS232 levels (wrong).
- DTR# and RTS# are active-low outputs used by the auto-reset circuit
- Refer to CH340C datasheet for physical pin assignments during PCB layout

**ESD Protection**: A USB ESD protection device (e.g., USBLC6-2SC6) SHOULD be placed on D+/D- lines near the USB connector to protect the bridge IC from electrostatic discharge.

### Voltage Regulation

The board MUST regulate the USB 5V input to stable 3.3V for powering the ESP32 module, IR receiver, temperature sensor, and status LEDs. A synchronous buck (step-down) switching regulator is REQUIRED for efficiency and thermal performance.

**Regulator Requirements**:

- Type: Synchronous buck (step-down) switching regulator
- Input voltage: 3.8-32V (wide input range)
- Output voltage: 3.3V ±1%
- Output current: ≥2A continuous
- Switching frequency: ≥500kHz (enables smaller external components)
- Efficiency: ≥90% at typical loads
- Package: Hand-solderable (TSOT26 or larger)
- Protection: Thermal shutdown, overcurrent protection, overvoltage protection

**Specified Implementation**: AP63203 (Diodes Incorporated) - Fixed 3.3V synchronous buck converter

- **Datasheet**: https://www.diodes.com/assets/Datasheets/AP63200-AP63201-AP63203-AP63205.pdf
- Synchronous topology (no external catch diode needed)
- Fixed 3.3V output (±1% accuracy, no feedback resistors needed)
- 2A output capability (ample headroom)
- 1.1MHz switching frequency (small external components)
- ~92-93% efficiency at typical loads
- TSOT26 package (0.95mm pitch, hand-solderable with fine-tip iron)
- Built-in soft-start (4ms), OVP, OCP, thermal shutdown
- Frequency spread spectrum for EMI reduction

**Required Support Components**:

1. **Input capacitor (C1)**: 10µF ceramic, 10V or higher (placed close to VIN pin)
2. **Output capacitors (C2, C3)**: 2× 22µF ceramic, 10V or higher (placed close to output)
3. **Bootstrap capacitor (C4)**: 100nF ceramic (between BST and SW pins)
4. **Inductor (L1)**: 4.7µH, ≥2.7A saturation current, low DCR (AP63203 datasheet typical; prefer a JLCPCB Basic part)
   - Package: SMD power inductor (hand-solderable)
   - Size: 4x4mm or 5x5mm typical

**No catch diode required** - the AP63203's synchronous topology uses an integrated low-side MOSFET instead.

**PCB Layout Considerations**:

- Keep switching node (SW pin to inductor) trace short and away from sensitive signals
- Input capacitor must be placed immediately adjacent to VIN and GND pins
- Output capacitors placed close to FB pin and load
- Use multiple vias for ground connections to bottom plane
- Bootstrap capacitor placed close to BST and SW pins

**Buck Converter Disable Jumper (JP1)**:

A 2-pin header (JP1) connects the AP63203 EN pin to GND, allowing the internal regulator to be disabled for external power experimentation:

```
AP63203 EN pin ────┬──── (internal pullup to VIN)
                   │
                  JP1 (2-pin header)
                   │
                  GND
```

- **JP1 open (default)**: EN floats high via internal pullup → buck converter enabled, normal USB operation
- **JP1 shorted**: EN pulled to GND → buck converter disabled, output goes high-impedance

**Use case**: When prototyping external battery/buck-boost circuits on a separate board, install the JP1 jumper to disable the internal regulator, then feed external 3.3V via the GPIO expansion header's 3V3 pin.

### Protection Components

The power input path MUST include:

**Overcurrent Protection**:

- Type: Resettable PTC fuse (polyfuse) or equivalent resettable overcurrent device
- Hold current: 1.0-1.2A (allows normal operation)
- Trip current: 1.8-2.2A (protects against shorts)
- Package: Through-hole radial or SMD
- **Suggested Part**: Bourns MF-R110 or equivalent

**Overvoltage Protection**:

- Type: TVS (Transient Voltage Suppression) diode
- Clamp voltage: 5.5-6.5V (protects 5V circuit, below regulator absolute maximum)
- Transient power rating: ≥400W
- Package: Hand-solderable (DO-214AA/SMB, DO-214AB/SMC, or through-hole)
- Placement: After fuse, before voltage regulator
- **Suggested Part**: SMBJ5.0A or equivalent

**Reverse Polarity Protection**: Omitted for USB-C input. The USB-C connector physically enforces correct orientation, and the CC resistor configuration ensures proper power negotiation. Reverse protection SHOULD be added on the battery input path when that feature is implemented (P-MOSFET recommended for efficiency).

### Status Indicators

The board MUST include visible LED indicators for debugging and status monitoring. All status LEDs use 3mm through-hole package for compact layout while maintaining hand-solderability.

**Power Rail LEDs** (direct-driven from power rails):

These LEDs connect directly to their respective power rails through current-limiting resistors, providing immediate visual confirmation of power presence without GPIO involvement.

*5V Rail Indicator* (Red):
- Function: Illuminated whenever USB 5V input is present (before buck converter)
- Connection: 5V rail → resistor → LED → GND
- Resistor value: 680Ω for ~5mA with Vf=1.9V red LED
- Purpose: Distinguishes input power issues from buck converter failures

*3.3V Rail Indicator* (Green):
- Function: Illuminated whenever regulated 3.3V is present (after buck converter)
- Connection: 3.3V rail → resistor → LED → GND
- Resistor value: 470Ω for ~3mA with Vf=2.0V green LED
- Purpose: Confirms buck converter operation

**GPIO-Controlled LEDs** (MOSFET-driven from 5V rail):

All GPIO-controlled status LEDs are driven through individual N-channel MOSFETs configured as low-side switches. This design provides:
- Consistent brightness across all LED colors (including blue with Vf ~3.2V)
- Minimal GPIO current draw (~nA gate current vs mA LED current)
- GPIO protection from LED faults
- Ability to use any LED color regardless of forward voltage

*Circuit per LED*:
```
5V ─── R_limit ─── LED(+) ─── LED(-) ─── MOSFET drain
                                         MOSFET source ─── GND
                              GPIO ─── MOSFET gate
                              100kΩ ─── GND (gate pulldown)
```

*MOSFET Requirements*:
- Type: N-channel enhancement mode, logic-level
- Gate threshold: <2V (fully enhanced at Vgs=3.3V)
- Drain current: ≥50mA (adequate for indicator LEDs)
- Package: SOT-23
- **Suggested Part**: 2N7002 or equivalent small-signal MOSFET

*Serial TX/RX LEDs* (Amber, qty 2):
- Function: Visual confirmation of serial communication during programming
- Connection: GPIO-controlled via MOSFET
- Resistor value: 150Ω for ~10mA with Vf=2.0V amber LED (brighter for brief pulses)

*IR Transmit Indicator* (Red):
- Function: Indicates IR transmission activity
- Connection: GPIO-controlled via MOSFET
- Resistor value: 330Ω for ~10mA with Vf=1.9V red LED

*User Programmable LEDs* (Blue, qty 2):
- Function: Software-controlled for debugging and status indication
- Connection: GPIO-controlled via MOSFET
- Resistor value: 330Ω for ~5mA with Vf=3.2V blue LED
- PCB silkscreen MUST label GPIO numbers for firmware reference

**LED Package Requirements**:

- All status indicator LEDs: 3mm (T-1) through-hole package
- IR emitter LEDs remain 5mm (T-1 3/4) for maximum optical output
- Mounting: Positioned for visibility when board is horizontal

**LED Summary Table**:

| Function | Color | Qty | Drive Method | Supply | R_limit |
|----------|-------|-----|--------------|--------|---------|
| 5V Power | Red | 1 | Direct | 5V | 680Ω |
| 3.3V Power | Green | 1 | Direct | 3.3V | 470Ω |
| Serial TX | Amber | 1 | MOSFET | 5V | 150Ω |
| Serial RX | Amber | 1 | MOSFET | 5V | 150Ω |
| IR TX | Red | 1 | MOSFET | 5V | 330Ω |
| User LED 1 | Blue | 1 | MOSFET | 5V | 330Ω |
| User LED 2 | Blue | 1 | MOSFET | 5V | 330Ω |

### Control Switches

The board MUST include two momentary push buttons for ESP32 control:

**RESET Button**:

- Function: Initiates complete ESP32 system reset (equivalent to power cycle)
- Connection: Connects ESP32 EN (enable) pin to ground when pressed
- Pull-up: Shared with auto-reset circuit (see Auto-Reset Circuit section)

**BOOT Button**:

- Function: Enters bootloader/programming mode when held during reset
- Connection: Connects GPIO0 to ground when pressed
- Pull-up: Shared with auto-reset circuit (see Auto-Reset Circuit section)
- Usage: Hold BOOT, press RESET, release both to enter programming mode (manual override of auto-reset)

**Switch Requirements**:

- Type: Tactile momentary switch, normally-open (NO)
- Package: SMD or through-hole, hand-rework-friendly
- Actuation force: 100-300gf (comfortable for frequent development use)
- Positioning: Accessible while USB cable is connected
- **Specified Part (v1.4)**: XKB TS-1187A-B-A-B (LCSC C318884, JLCPCB Basic),
  SMD 5.1×5.1mm, 4 gull-wing terminals. Terminals on the same row are
  internally common, so the part behaves as SPST between the two rows; the
  footprint numbers the rows 1/1 and 2/2 and bridge tracks under the body
  join each pair. (Replaces the Extended TS-1088R from v1.2/v1.3.)

**Note**: With the auto-reset circuit in place, manual button presses are typically only needed for:
- Recovery from crashed firmware
- Debugging boot mode issues
- Testing without USB connection

Normal firmware upload uses the auto-reset circuit automatically.

### Connection Points and Expansion

The large 2×19 ESP32-DevKitC breakout header of earlier revisions is **removed**.
In its place the board MUST provide a small set of purposeful connection points so
that GPIO access, I2C expansion, and external-power prototyping survive without the
bulky header. The intent is to design in headroom now — footprints are cheap before
fabrication and impossible to add after — while keeping the populated board compact.

GPIO budget: after removing the breakout, the following ESP32 GPIOs are free and
safe to expose — GPIO5, 13, 14, 21, 22, 23, 25, 26, 27, 32, 33, 34, 35. GPIO6–11 are
the module's internal SPI-flash bus and MUST NOT be exposed or used as I/O. GPIO12 is
a flash-voltage strapping pin and MUST NOT be pulled high; it MAY be wired only to the
unpopulated JTAG footprint (see below), which presents no load unless a debugger is
attached.

**I2C Qwiic/STEMMA-QT connector** (REQUIRED): A 4-pin JST-SH (1.0mm) Qwiic-standard
connector on `GND, 3V3, SDA=GPIO21, SCL=GPIO22`. This is the primary expansion path —
it gives plug-and-play access to the I2C sensor/display ecosystem (light level,
pressure, air quality, an OLED status display, etc.) with no future board changes,
satisfying the deferred "additional I2C sensors" provision. Onboard I2C pull-ups
(see Optional Components) MUST have footprints; populate them if the attached module
lacks its own.

**Spare-GPIO + power header** (REQUIRED): A compact 2.54mm header exposing a versatile
subset of the free GPIOs plus power rails, replacing the breakout's "user GPIO" and
"3V3/5V rails for external-power prototyping" roles. RECOMMENDED signal set, chosen for
peripheral coverage: GPIO25 (DAC1), GPIO26 (DAC2), GPIO32 (ADC1/touch), GPIO33
(ADC1/touch), GPIO34 (ADC1, input-only), GPIO23 (general). The header MUST also expose
`3V3`, `5V`, and at least one `GND`. A 2×5 (10-pin) arrangement is suggested. The 3V3/5V
pins together with the buck-disable jumper JP1 provide the external-battery prototyping
hook referenced in [Battery Support](#battery-support).

**External IR-emitter header** (REQUIRED): A 2-pin 2.54mm header allowing an IR LED on
a flying lead to be aimed at the AC unit when the enclosure lacks line-of-sight. It
MUST tie an additional IR-LED branch (its own series current-limit resistor footprint)
across the existing IR drive — anode side to the IR supply rail through the resistor,
cathode to the IR MOSFET (Q3) drain — so the external emitter switches with the onboard
array and no extra driver is needed. The series-resistor footprint MAY be left
unpopulated until an external emitter is used.

**JTAG debug footprint** (OPTIONAL, unpopulated): A 2×5 2.54mm footprint on the ESP32
JTAG pins (GPIO12=TDI, GPIO13=TCK, GPIO14=TMS, GPIO15=TDO) plus 3V3 and GND, for an
ESP-PROG/OpenOCD hardware debugger. Left unpopulated (DNP); serial flashing over the
CH340C is the default path. Because the footprint is unloaded when no debugger is
attached, the GPIO12 flash-voltage strap and the GPIO15 default state are preserved.

**Common requirements**: 2.54mm pitch where pin headers are used, for jumper-wire and
ribbon compatibility. Every exposed pin MUST be silkscreen-labelled with its function
(e.g. `GPIO21/SDA`, `5V`, `GND`, `TDI`). Connectors SHOULD be selected from JLCPCB
**Basic** parts where a suitable one exists, to avoid assembly feeder fees.

## Circuit Design Requirements

### IR Transmitter Driver Circuit

All four IR LEDs are driven through a single N-channel MOSFET configured as a low-side switch. This design was chosen over individual NPN transistors for:

- **Power efficiency**: MOSFETs have no base current draw and lower on-state losses
- **Simpler drive**: Single GPIO controls all LEDs simultaneously
- **3.3V compatibility**: Logic-level MOSFET fully enhances at 3.3V gate drive

**MOSFET Requirements**:

- Type: N-channel enhancement mode MOSFET
- Drain current: ≥500mA continuous (handles 4 × 100mA LEDs)
- Gate threshold: <2V (must be fully enhanced at Vgs = 3.3V)
- Rds(on): <50mΩ at Vgs = 2.5V (minimizes power loss)
- Package: SOT-23 (hand-solderable with fine-tip iron)
- **Specified Part (v1.4)**: AO3400A (Alpha & Omega, LCSC C20917, JLCPCB
  Basic) - Vgs_th ≤ 1.45V, Rds_on = 48mΩ @ Vgs = 2.5V, Id = 5.7A. Meets
  every requirement above; replaces the Extended IRLML6344 (~19mV / ~8mW
  difference at the 0.42A burst — immaterial).

**LED Power Supply**:

LEDs are powered from the 3.3V regulated rail (not 5V) for improved efficiency:

- 3.3V supply reduces voltage drop across current-limiting resistors
- Power dissipated in resistors: 0.18W per LED (vs 0.35W from 5V)
- Total system efficiency improved ~28% during IR transmission
- Buck converter has adequate headroom (675mA peak vs 2A rating)

**Current Limiting Circuit**:

- Supply voltage (3.3V) → Current-limiting resistor → IR LED anode
- IR LED cathode → MOSFET drain (all 4 cathodes joined)
- Current-limiting resistor calculation for 100mA target current:
  ```
  R_limit = (V_supply - V_LED_forward - V_DS_on) / I_target
  R_limit = (3.3V - 1.5V - 0.01V) / 0.1A = 17.9Ω
  ```
- Use nearest standard value (18Ω, E24 series)
- Resistor power rating: ≥0.25W (dissipates ~0.18W during transmission)

**Gate Drive Circuit**:

- ESP32 GPIO18 (IR_TX) → gate series resistor → MOSFET gate
- 100kΩ pull-down resistor from gate to GND
- MOSFET source → GND
- Gate series resistor provides ESD protection and edge control, but MUST be small
  enough to switch the MOSFET cleanly at the 38kHz carrier: a 10kΩ value against
  the MOSFET input capacitance slows the gate edges to several microseconds — a
  large fraction of the ~13µs carrier half-period. The gate series resistor MUST
  be in the **~330Ω–1kΩ** range (H1.4 review; the schematic fits 470Ω).
- Gate pull-down ensures MOSFET is OFF during boot/reset when GPIO is high-impedance

The external IR-emitter header (see [Connection Points and Expansion](#connection-points-and-expansion))
adds an optional fifth IR branch on this same drain node, switched by the same MOSFET.

### IR Receiver Interface

The IR receiver module connects directly to the 3.3V rail, ground, and an ESP32 GPIO pin.

**Connection Requirements**:

- Power: 3.3V and GND from regulated supply
- Signal: GPIO19 (IR_RX), interrupt-capable, not a strapping pin
- Supply filter: the TSOP datasheet RECOMMENDS a series resistor (~100Ω) from 3.3V to
  the receiver Vs pin plus a ≥100nF capacitor from that local Vs node to GND. This RC
  filter MUST be provided here: the high-current IR transmitter shares the same 3.3V
  rail, so TX-induced supply spikes are exactly the disturbance the filter rejects.
  Place the cap as close to the receiver package as practical. (H1.4 review.)
- Output pull-up: NOT required. The TSOP382 output stage has an internal ~30kΩ
  pull-up; no external pull-up should be added.

**Signal Characteristics**:

- Output type: Active-low demodulated pulses (receiver outputs LOW when 38kHz modulated IR detected)
- Timing: Preserves pulse timing from original IR transmission after demodulation
- Pull-up: none required (TSOP382 has an internal ~30kΩ pull-up; see above)
- **GPIO Assignment**: GPIO19 (IR_RX) - interrupt-capable, not a strapping pin

The GPIO pin MUST support external interrupts to capture timing-accurate signal edges for protocol decoding.

### Temperature Sensor Interface

The DHT22 temperature/humidity sensor connects via a single-wire proprietary protocol to any available GPIO pin.

**Connection Requirements**:

- Data pin: GPIO4 (TEMP_DATA) - not a strapping pin
- Pull-up resistor: 10kΩ on data line (typically included on DHT22 module)
- Supply voltage: 3.3V and GND from regulated supply

**Mounting**:

- Connection method: Pin headers (female headers on main board recommended)
- Rationale: Allows sensor removal for testing or replacement without desoldering
- Alternative: Direct soldering acceptable if header mounting is impractical

### USB-C Power Entry

The USB-C connector's VBUS pin connects to the protection circuit as follows:

```
USB VBUS ----[PTC Fuse]----+----[TVS to GND]----[Voltage Regulator]
                           |
                          GND (TVS clamps overvoltage)
```

CC1 and CC2 pins each connect through 5.1kΩ resistors to GND. Shield pins connect to PCB ground plane. D+/D- pins connect to the USB-to-UART bridge IC for programming and serial communication.

### Auto-Reset Circuit

The auto-reset circuit enables automatic bootloader entry when programming tools (esptool, cargo-espflash) assert DTR and RTS signals. This eliminates the need to manually press BOOT and RESET buttons during firmware upload.

**Circuit Function**:

The ESP32 enters bootloader mode when:
- EN (enable) pin is pulsed LOW (reset)
- GPIO0 is held LOW during reset release

The auto-reset circuit uses two cross-coupled N-channel MOSFETs (2N7002) that form an XOR-like gate. This prevents the chip from being held in reset when both DTR and RTS are asserted together (which happens when opening a serial port).

**Truth Table**:

| DTR | RTS | EN | GPIO0 |
|-----|-----|----|-------|
| 0 | 0 | HIGH | HIGH | (normal operation) |
| 0 | 1 | HIGH | LOW | (boot mode select) |
| 1 | 0 | LOW | HIGH | (reset) |
| 1 | 1 | HIGH | HIGH | (normal operation) |

**Circuit Schematic** (per ESP32-S2-SAOLA-1 reference design):

```
                    ┌────────────────────────────────────────┐
                    │                                        │
DTR ───┬───[10kΩ]───┴──┤Gate                                 │
       │               │     Q1 (2N7002)                     │
       │          ┌────┤Drain ────────┬──[10kΩ]── 3.3V       │
       │          │    │              │                      │
       │          │    └Source────────│────┐                 │
       │          │                   │    │                 │
       │          │                   EN   │                 │
       │          │                   │    │                 │
       │          │              [1µF cap] │                 │
       │          │                   │    │                 │
       │          │                  GND   │                 │
       │          │                        │                 │
       └──────────│────────────────────────│─────────────────┘
                  │                        │
RTS ───┬──────────│────────────────────────┘
       │          │
       └──[10kΩ]──┴──┤Gate
                     │     Q2 (2N7002)
                ┌────┤Drain ────────┬──[10kΩ]── 3.3V
                │    │              │
                │    └Source────────│──── DTR (cross-coupled)
                │                   │
                │                 GPIO0
                │
                └──── RTS (to Q1 source, cross-coupled)
```

**Key insight**: The sources are NOT grounded - each transistor's source connects to the opposite input signal (DTR to Q2 source, RTS to Q1 source). This cross-coupling creates the XOR behavior: with both inputs asserted, neither FET sees a gate-source voltage, so neither can pull its output low.

**MOSFET body diodes**: Each 2N7002's body diode (source→drain) creates a path from its input line into its output node (RTS→EN via Q1, DTR→GPIO0 via Q2) that conducts only when the output is pulled ~0.6V below the source line — in practice only while RESET or BOOT is held pressed with the serial port idle (lines high). The 470Ω R21/R26 links (v1.3) limit this current to ~5mA; the buttons still dominate the node, and desoldering R21/R26 breaks the paths entirely.

**Component Requirements**:

| Ref | Value | Purpose |
|-----|-------|---------|
| Q1, Q2 | 2N7002 N-channel MOSFET | Cross-coupled signal translation (shared BOM line with Q4/Q5) |
| R (×2) | 10kΩ | Gate series resistors (carried over from the BJT design; not required for FETs but layout-neutral) |
| R (×2) | 10kΩ | Pull-ups for EN and GPIO0 |
| C | 1µF ceramic | EN pin RC delay (power-on reset) |

**Reference**: This circuit matches the ESP32-S2-SAOLA-1 topology from Espressif (which uses NPN BJTs; this board substitutes pin-compatible 2N7002 MOSFETs on the same SOT-23 pads). See also: [Espressif's Automatic Reset](https://qsantos.fr/2025/05/09/espressifs-automatic-reset/) for detailed explanation.

**Manual Override**:

The BOOT and RESET buttons (see Control Switches section) remain functional and can override the auto-reset circuit for manual bootloader entry when needed.

**Auto-Reset Bypass Links (R21, R26 — 470Ω)**:

Two inline links allow disabling the auto-reset circuit for debugging. Earlier
revisions used through-hole header+shunt jumpers (JP2/JP3), then 0Ω SMD links;
since v1.3 they are **470Ω** so they also limit the 2N7002 body-diode current
into the CH340C during button presses (see MOSFET body diodes above). 470Ω is
electrically transparent to auto-reset: EN/GPIO0 still reach ~0.15V against
their 10kΩ pull-ups, well below the 0.825V V_IL. JLCPCB places them at assembly
and the populated board stays low-profile.

```
CH340C DTR# ────[R21 470Ω]──── Auto-reset circuit (DTR side)
CH340C RTS# ────[R26 470Ω]──── Auto-reset circuit (RTS side)
```

| Link | Populated (default) | Removed |
|------|---------------------|---------|
| R21 | DTR connected, auto-reset enabled | DTR disconnected |
| R26 | RTS connected, auto-reset enabled | RTS disconnected |

- **Default configuration**: Both links populated. Auto-reset works normally for programming.
- **Debug configuration**: Desolder one or both links to use serial communication without triggering resets.

The board ships with R21 and R26 populated. (Note: the cross-coupled circuit ties each
transistor's emitter to the *opposite* DTR/RTS signal rather than to ground — verified
correctly wired in the H1.4 netlist review, but it is a finicky topology worth
confirming during bring-up.)

## Power Budget Analysis

### Current Consumption Estimates

**3.3V Rail Loads** (WiFi active, periodic IR transmission):

- ESP32 module: 80-120mA (WiFi idle)
- WiFi transmission peaks: 240mA for <1s bursts
- CH340C USB-UART bridge: ~15mA (active)
- IR receiver: 0.5mA
- BME280: 1.8µA (negligible)
- Status LEDs (6× @ 3mA): 18mA
- **3.3V rail total: ~345mA average, ~485mA peak**

**5V Rail Loads** (IR transmission):

- IR LEDs (4× @ 100mA, 30% duty cycle): 120mA average during active periods
- IR LEDs powered directly from 5V (not through buck converter)

**Buck Converter Power Analysis**:

- Input power (from USB): ~345mA × 3.3V / 0.92 efficiency = ~1.24W → 248mA @ 5V
- Peak input power: ~485mA × 3.3V / 0.92 = ~1.74W → 348mA @ 5V
- Buck converter power dissipation: ~0.09W at average load (vs 0.6W for LDO)
- Thermal performance: Minimal heat generation, TSOT26 package adequate without heatsinking

**Total USB Current Draw**:

- Average: 268mA (3.3V loads) + 120mA (IR LEDs) = ~388mA
- Peak: 376mA (3.3V loads) + 400mA (IR LEDs 100% duty) = ~776mA
- Well within USB-C 3A capability

### Voltage Rail Requirements

The board requires two voltage rails:

**5V Rail** (from USB-C):

- Powers IR LED driver circuits directly (for maximum LED brightness)
- Input to buck converter
- Available at header pins for 5V-tolerant peripherals
- Protected by PTC fuse and TVS diode

**3.3V Rail** (buck converter output):

- Powers ESP32 module via its 3V3 pin
- Powers IR receiver module
- Powers temperature sensor breakout board
- Powers status LEDs
- Maximum load: 2A continuous (AP63203 rated capacity)

## PCB Design Constraints

### Board Dimensions

The board SHOULD maintain dimensions approximately 100mm × 70mm (similar to Arduino Mega footprint) providing adequate spacing for through-hole components while fitting standard project enclosures. Exact dimensions may adjust based on final component layout.

### Layer Stack

A standard 2-layer PCB is REQUIRED:

- **Top Layer**: Component placement and signal routing
- **Bottom Layer**: Continuous ground plane with minimal signal routing

### Copper Requirements

**Power Traces**:

- USB 5V input: ≥25 mil (0.635mm) width
- Buck converter switching node (SW pin to inductor/diode): ≥30 mil (0.762mm) width, keep as short as possible
- 3.3V regulated output: ≥20 mil (0.508mm) width
- IR LED collector traces: ≥15 mil (0.381mm) width

**Buck Converter Critical Traces**:

- VIN to buck IC: ≥25 mil, keep input capacitor close
- SW (switching node): ≥30 mil, minimize length and area to reduce EMI
- Output (VOUT): ≥20 mil, place output capacitor close to load
- Ground connections: Use multiple vias to bottom ground plane

**Signal Traces**:

- General GPIO: 10 mil (0.254mm) minimum
- I2C lines (SDA/SCL): 12 mil (0.305mm) with matched lengths where practical

**Ground Plane**:

- Solid pour on bottom layer
- Top layer ground fills in unused areas
- Thermal reliefs on through-hole ground connections to enable soldering
- Buck converter ground connections: NO thermal reliefs (direct connection for low impedance)

### Component Spacing

Through-hole components MUST maintain minimum 2.54mm (0.1") spacing between adjacent component bodies to enable hand soldering with standard soldering irons. Pin headers SHOULD align on 2.54mm grid to support standard jumper wires and ribbon cables.

### Mounting Holes

The board MUST include four mounting holes (3.2mm diameter) positioned near corners, inset 5mm from board edges. These holes enable standoff mounting at standard 3mm spacing.

### Silkscreen Requirements

The silkscreen MUST clearly label:

- All pin headers with function (e.g., "GPIO21/SDA", "BAT+", "GND")
- Positive orientation for polarized components (LEDs, electrolytic capacitors, diodes)
- Reference designators for all components
- USB-C connector position and orientation
- Board revision number and date code

Component values MAY be omitted from silkscreen if space is limited, relying on reference designator cross-reference to BOM.

## Manufacturing Notes for JLCPCB

### PCB Specification

Order the PCB with the following JLCPCB standard options:

- Base Material: FR-4
- Layers: 2
- Thickness: 1.6mm
- Copper Weight: 1 oz (35µm)
- Surface Finish: HASL (lead-free) or ENIG if budget permits
- Silkscreen: White on green solder mask
- Remove Order Number: No (specify location if desired)

### Assembly Considerations

The board targets **JLCPCB SMT-only machine assembly** (top side only) with parts
sourced from **LCSC**, plus a **hand-solder kit** of loose parts ordered alongside.
The split is definitive and lives in one place — the `HAND_SOLDER` table in
`scripts/fab-outputs.py`, which generates the assembly BOM/CPL and the kit list
(`hardware/fab/esp32-ir-remote-hand-solder-kit.csv`) so they cannot drift apart.

The kit MUST contain every through-hole part (machine assembly cannot bend the IR
LEDs over the board edge at their fan angles, and THT lines carry both Extended
loading and per-joint fees) and SHOULD contain easy two-terminal SMD Extended parts
(TVS, polyfuse, power inductor) and optional connectors (Qwiic). Parts in the
series power path (USB-C receptacle, polyfuse, inductor, TVS) MUST be flagged
fit-before-first-power in the kit notes and in `hardware/bring-up.md`.

To minimize assembly cost, part selection MUST prefer JLCPCB **"Basic"** parts (kept
permanently loaded on the pick-and-place, no per-part feeder fee) over **"Extended"**
parts wherever a suitable Basic part exists. Where a choice forces an Extended part,
that SHOULD be noted with the reason — as of v1.4 the machine-placed Extended lines
are exactly three: the AP63203 buck regulator, the CH340C bridge, and the
ESP32-WROOM-32E module (no Basic equivalents exist). Every SMD component MUST carry
an LCSC part number and footprint in the schematic so the BOM and CPL export cleanly
to JLCPCB.

### Component Sourcing

All components SHOULD be sourced from LCSC. Prefer JLCPCB Basic parts (see above). Where
a required through-hole component is unavailable from LCSC, specify a Digikey/Mouser
alternative.

## Expansion and Future Provisions

### Deferred Features

Several previously-deferred provisions are now **implemented as on-board connection
points** (see [Connection Points and Expansion](#connection-points-and-expansion)):
the I2C Qwiic connector covers "additional I2C sensors", and the unpopulated JTAG
footprint covers hardware debug. The following remain genuinely deferred:

**Battery Charging Circuit** (deferred to v2):

Battery operation requires power-path management beyond simple charging (charger IC,
load-sharing, protection, reverse-polarity). It is more than a footprint and stays out
of v1. The spare-GPIO + power header exposes 3.3V and 5V rails, and JP1 disables the
internal buck converter, enabling external battery-circuit prototyping before
integrating into a future battery-capable board.

**External Antenna** (deferred):

The board retains the WROOM-32**E** module with its built-in PCB trace antenna — the
simplest, lowest-cost path, adequate for an in-room AC remote. Adding a U.FL external
antenna would require switching to the WROOM-32**UE** variant plus a U.FL footprint;
this is deferred unless WiFi range proves inadequate during bring-up.

**Additional I2C Sensors** — *now provided* via the Qwiic connector; no separate
per-sensor footprints are designed in (any I2C light/pressure/air-quality sensor or
OLED display attaches over Qwiic).

**JTAG Debug** — *now provided* as an unpopulated 2×5 footprint on GPIO12–15.

### Future Board Revisions

Subsequent board revisions MAY:

- Migrate to SMD components for reduced size
- Remove IR receiver (development-only component)
- Integrate battery charging circuit
- Reduce status LED count
- Minimize GPIO header exposure
- Integrate external antenna permanently

This development board intentionally over-provisions debugging and expansion features. Production boards will optimize for cost and size based on lessons learned during development.

## Bill of Materials

> **⚠️ This BOM lags the schematic and MUST be regenerated from it.** The KiCad
> schematic is the source of truth for reference designators and parts. The tables
> below were authored earlier and use stale designators (e.g. they list `J2` as the
> breakout header, whereas in the schematic `J2` is the USB-C receptacle; LED and
> resistor numbers also differ). Once the schematic carries an LCSC field on every
> symbol, regenerate the BOM with `kicad-cli sch export bom` (or the kicad MCP) and
> treat that export — plus `hardware/BOM.md`'s curated LCSC numbers, matched **by
> function, not by designator** — as the live BOM. The tables here are retained only
> for requirement intent (values, ratings, suggested parts), not designators. See
> ROADMAP H1.2.

This BOM specifies exact parts only where necessary for compatibility (e.g., ESP32 module pinout, USB-C connector footprint). For other components, requirements are listed with suggested parts.

**BOM Status**: Work in progress. The following items require confirmation after selecting specific vendor parts:

- **TVS diode (D1)**: Confirm polarity orientation (unidirectional vs bidirectional) based on selected part
- **Status LED resistors (R11-R16)**: Calculate values based on selected LED forward voltage to achieve 2-5mA target current
- **IR LED resistors (R3-R6)**: Verify 18Ω value against selected LED forward voltage for 100mA target

### Core Components

| Qty | Reference | Part/Requirement            | Description                              | Package/Notes             |
| --- | --------- | --------------------------- | ---------------------------------------- | ------------------------- |
| 1   | U1        | **ESP32-WROOM-32E-N4**      | ESP32 WiFi+BT Module (4MB flash)         | 38-pin castellated, 1.27mm pitch |
| 1   | U2        | **CH340C**                  | USB-to-UART Bridge IC                    | SOP-16 (1.27mm pitch)     |
| 4   | LED1-LED4 | 940nm IR LED, ≥100mA        | Suggested: TSAL6200 (Vishay)             | 5mm through-hole          |
| 1   | Q1        | **IRLML6344**               | IR LED driver MOSFET (logic-level N-ch)  | SOT-23                    |
| 2   | Q5-Q6     | **2N7002** N-channel MOSFET | Auto-reset circuit (schematic refs Q1/Q2) | SOT-23                    |
| 1   | U3        | 38kHz IR Receiver           | Suggested: TSOP1838, TSOP4838 (Vishay)   | 3-pin through-hole module |
| 1   | U4        | DHT22 (AM2302)              | Temperature/humidity sensor module       | 3-pin through-hole module |
| 1   | J1        | USB-C Receptacle            | Through-hole preferred for hand assembly | Through-hole              |
| 1   | U5        | **AP63203**                 | Synchronous buck converter (fixed 3.3V)  | TSOT26                    |

### Protection and Power

| Qty | Reference | Part/Requirement            | Description                           | Package/Notes      |
| --- | --------- | --------------------------- | ------------------------------------- | ------------------ |
| 1   | F1        | PTC Fuse, 1.1A/2A           | Overcurrent protection                | Through-hole or SMD |
| 1   | D1        | TVS Diode, 5.5-6.5V clamp   | Overvoltage protection                | DO-214AA or larger |
| 2   | R1-R2     | 5.1kΩ ±5%                   | USB-C CC resistors                    | 0805 or 1206 SMD   |

### USB-to-UART Bridge Circuit

| Qty | Reference | Part/Requirement            | Description                           | Package/Notes      |
| --- | --------- | --------------------------- | ------------------------------------- | ------------------ |
| 1   | C9        | 100nF ceramic               | CH340C V3 pin decoupling              | 0805 or 1206 SMD   |
| 2   | R23-R24   | 10kΩ 1/4W                   | Auto-reset base resistors             | Axial or 1206 SMD  |

### Buck Converter Support Components

| Qty | Reference | Part/Requirement            | Description                           | Package/Notes        |
| --- | --------- | --------------------------- | ------------------------------------- | -------------------- |
| 1   | L1        | 4.7µH, Isat ≥2.7A, DCR <100mΩ | Power inductor for AP63203 (datasheet typical; better JLCPCB Basic stock than 3.9µH) | SMD 4x4mm or 5x5mm   |
| 1   | C1        | 10µF ceramic, ≥10V          | Buck input capacitor                  | 0805 or 1206 SMD     |
| 2   | C2-C3     | 22µF ceramic, ≥10V          | Buck output capacitors                | 0805 or 1206 SMD     |
| 1   | C4        | 100nF ceramic               | Bootstrap capacitor (BST to SW)       | 0603 or 0805 SMD     |

### IR Transmitter Circuit

| Qty | Reference | Part/Requirement      | Description                        | Package/Notes      |
| --- | --------- | --------------------- | ---------------------------------- | ------------------ |
| 4   | R3-R6     | 18Ω ≥0.25W            | LED current limiting (~100mA)      | Axial or 1206 SMD  |
| 1   | R7        | 10kΩ 1/4W             | MOSFET gate series resistor        | Axial or 1206 SMD  |
| 1   | R8        | 100kΩ 1/4W            | MOSFET gate pull-down              | Axial or 1206 SMD  |

### Status LEDs

| Qty | Reference  | Part/Requirement   | Description                 | Package/Notes               |
| --- | ---------- | ------------------ | --------------------------- | --------------------------- |
| 1   | LED5       | LED (Green sugg.)  | Power indicator             | 3mm or 5mm through-hole     |
| 2   | LED6-LED7  | LED (Amber sugg.)  | Serial TX/RX indicators     | 3mm or 5mm through-hole     |
| 1   | LED8       | LED (Red sugg.)    | IR transmit indicator       | 3mm or 5mm through-hole     |
| 2   | LED9-LED10 | LED (Blue sugg.)   | User programmable           | 3mm or 5mm through-hole     |
| 6   | R11-R16    | Resistor, calc.    | LED current limiting (2-5mA) | Calculated per LED Vf       |

### Controls and Headers

| Qty | Reference | Part/Requirement       | Description                  | Package/Notes               |
| --- | --------- | ---------------------- | ---------------------------- | --------------------------- |
| 2   | SW1-SW2   | Tactile Switch, NO     | RESET and BOOT buttons       | Through-hole, 6×6mm typical |
| 2   | R17-R18   | 10kΩ 1/4W              | Pull-up resistors (EN, GPIO0) | Axial or 1206 SMD           |
| 1   | C10       | 1µF ceramic            | EN pin RC delay capacitor    | 0805 or 1206 SMD            |
| 1   | —         | 4-pin JST-SH (Qwiic)   | I2C Qwiic/STEMMA-QT connector (GPIO21/22 + 3V3/GND) | 1.0mm SH; prefer JLCPCB Basic |
| 1   | —         | 2×5 2.54mm header      | Spare-GPIO + power header (GPIO25/26/32/33/34/23 + 3V3/5V/GND) | 2.54mm |
| 1   | —         | 2-pin 2.54mm header    | External IR-emitter header (+ series-resistor footprint) | 2.54mm |
| 1   | JP1       | 2-pad solder jumper    | Buck converter disable (EN→GND) | SMD, open by default |
| 2   | R21, R26  | 470Ω SMD resistor      | Auto-reset bypass links (DTR/RTS) + body-diode current limit, populated by default | 0603 SMD |

*(Designators marked "—" are assigned in the schematic; the 2×19 breakout header of
earlier revisions is removed.)*

### Optional Components (Unpopulated)

These components have PCB footprints but are not populated in initial builds:

| Qty | Reference | Part/Requirement       | Description                      | Purpose/Notes                    |
| --- | --------- | ---------------------- | -------------------------------- | -------------------------------- |
| 2   | —         | 4.7kΩ SMD              | I2C pull-ups for the Qwiic bus   | Populate if attached module lacks its own |
| 1   | —         | 2×5 2.54mm header      | JTAG debug footprint (GPIO12–15 + 3V3/GND) | DNP; for ESP-PROG/OpenOCD |
| 1   | —         | series resistor (IR)   | External IR-emitter current limit | Populate when an external emitter is used |

*(U.FL external-antenna footprint is **not** designed in — the board keeps the
WROOM-32E PCB antenna; adding U.FL would require the WROOM-32UE variant. See Deferred
Features.)*

---

**Document Version**: 1.3
**Date**: 2026-06-11
**Author**: Development Team
**Status**: In Implementation - layout complete, fab outputs ready; auto-reset Q1/Q2 moved to 2N7002 MOSFETs (v1.3)

**Design Decisions Made**:
- ESP32 Module: ESP32-WROOM-32E-N4 selected for full control over support circuitry while using certified RF module (PCB antenna retained; U.FL/-32UE deferred)
- USB-to-UART Bridge: CH340C selected for hand-solderability (SOP-16), built-in oscillator, and low cost
- Auto-Reset Circuit: Cross-coupled 2N7002 N-channel MOSFETs (v1.3; pin-compatible swap from S8050 NPN BJTs, BOM-consolidated with Q4/Q5) with R21/R26 470Ω bypass links (debug disconnect + body-diode current limit)
- Voltage Regulation: AP63203 synchronous buck converter (L1 = 4.7µH) with disable jumper (JP1) for external power experimentation
- Protection: PTC fuse + TVS diode; USB D+/D- ESD protection omitted (adequate for dev board use)
- IR LED Driver: Single IRLML6344 logic-level MOSFET (SOT-23) with gate pull-down (gate series resistor ~330Ω–1kΩ, not 10kΩ); LEDs powered from 3.3V rail
- IR GPIO Assignment: GPIO18 (IR_TX), GPIO19 (IR_RX) - adjacent pins, avoids strapping pins
- Temperature Sensor GPIO: GPIO4 (TEMP_DATA)
- User LEDs: GPIO16 (USER_LED1), GPIO17 (USER_LED2)
- Temperature Sensor: DHT22 (AM2302) single-wire module replacing BME280
- Connection Points: 2×19 DevKitC breakout header REMOVED; replaced by I2C Qwiic (GPIO21/22), spare-GPIO + power header, external IR-emitter header, and an unpopulated JTAG footprint (GPIO12–15)
- Jumper Configuration: JP1 ships open (buck enabled); R21/R26 470Ω auto-reset links ship populated
- Assembly: JLCPCB PCBA from LCSC parts, preferring JLCPCB "Basic" parts; through-hole parts hand-soldered or via JLCPCB THT option; BGA excluded

**Remaining Implementation Tasks**:
- Footprint assignment for all schematic components
- PCB layout design following constraints in this specification
- BOM finalization with specific vendor part numbers (see BOM Status section for pending confirmations)
