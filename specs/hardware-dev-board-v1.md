# ESP32 IR Remote Control Development Board - Hardware Specification v1.1

## Overview

This specification defines the hardware requirements for a development board that enables testing and development of an ESP32-based smart AC remote control system using infrared transmission. The board serves as a transition from the current ESP8266 breadboard proof-of-concept to a manufacturable design suitable for firmware development in Rust and eventual production refinement.

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

The GPIO expansion header exposes 3.3V and 5V rails, enabling experimentation with external battery and power management circuits on a separate prototyping board. A jumper (JP1) on the buck converter's EN pin allows disabling the internal regulator when testing external power solutions (see Voltage Regulation section).

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
CH340C DTR# ────[JP2]───── Auto-reset circuit Q1 base
CH340C RTS# ────[JP3]───── Auto-reset circuit Q2 base
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
4. **Inductor (L1)**: 3.9µH, ≥2.7A saturation current, low DCR
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
- Package: Through-hole or equivalent hand-solderable mounting
- Size: 6mm×6mm typical (other sizes acceptable)
- Actuation force: 100-300gf (comfortable for frequent development use)
- Positioning: Accessible while USB cable is connected

**Note**: With the auto-reset circuit in place, manual button presses are typically only needed for:
- Recovery from crashed firmware
- Debugging boot mode issues
- Testing without USB connection

Normal firmware upload uses the auto-reset circuit automatically.

### Development Headers

**ESP32 Breakout Header** (2×19 pins):

The board includes a debug breakout header matching the ESP32-DevKitC V4 pinout. This 38-pin header (2 rows of 19) exposes all ESP32 GPIO pins plus power rails, enabling:

- External serial console via UART0 (GPIO1/TXD, GPIO3/RXD)
- I2C peripherals via GPIO21 (SDA) and GPIO22 (SCL)
- Additional GPIO access for prototyping and expansion
- Power rails: 3.3V (pin 1), 5V (pin 19), GND (pins 14, 20, 26)

**Pin Numbering**: Column-first ordering matches DevKitC - left column pins 1-19, right column pins 20-38.

**Header Specifications**:

- Pitch: 2.54mm (0.1") for compatibility with standard jumper wires and breadboards
- Gender: Female headers RECOMMENDED (accepts male pins from modules/jumpers)
- Row spacing: 22.86mm (0.9") to match DevKitC module width

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
- **Specified Part**: IRLML6344 (Infineon) - Vgs_th = 0.5-1.1V, Rds_on = 27mΩ @ Vgs = 2.5V

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

- ESP32 GPIO18 (IR_TX) → 10kΩ resistor → MOSFET gate
- 100kΩ pull-down resistor from gate to GND
- MOSFET source → GND
- Gate series resistor limits inrush current and provides ESD protection
- Gate pull-down ensures MOSFET is OFF during boot/reset when GPIO is high-impedance

### IR Receiver Interface

The IR receiver module connects directly to the 3.3V rail, ground, and an ESP32 GPIO pin.

**Connection Requirements**:

- Power: 3.3V and GND from regulated supply
- Signal: ESP32 GPIO pin with interrupt capability (e.g., GPIO4, GPIO5, or other interrupt-capable pins)
- Decoupling: 100nF ceramic capacitor between VCC and GND, placed as close to receiver package as practical
- Purpose: Suppresses power supply noise that could trigger false IR detections

**Signal Characteristics**:

- Output type: Active-low demodulated pulses (receiver outputs LOW when 38kHz modulated IR detected)
- Timing: Preserves pulse timing from original IR transmission after demodulation
- Pull-up: May require weak pull-up if receiver output is open-drain (check receiver datasheet)
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

The auto-reset circuit uses two cross-coupled NPN transistors that form an XOR-like gate. This prevents the chip from being held in reset when both DTR and RTS are asserted together (which happens when opening a serial port).

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
DTR ───┬───[10kΩ]───┴──┤Base                                 │
       │               │     Q1 (NPN)                        │
       │          ┌────┤Collector ────┬──[10kΩ]── 3.3V       │
       │          │    │              │                      │
       │          │    └Emitter───────│────┐                 │
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
       └──[10kΩ]──┴──┤Base
                     │     Q2 (NPN)
                ┌────┤Collector ────┬──[10kΩ]── 3.3V
                │    │              │
                │    └Emitter───────│──── DTR (cross-coupled)
                │                   │
                │                 GPIO0
                │
                └──── RTS (to Q1 emitter, cross-coupled)
```

**Key insight**: The emitters are NOT grounded - each transistor's emitter connects to the opposite input signal (DTR to Q2 emitter, RTS to Q1 emitter). This cross-coupling creates the XOR behavior.

**Component Requirements**:

| Ref | Value | Purpose |
|-----|-------|---------|
| Q1, Q2 | NPN (S8050, 2N2222A, BC337) | Cross-coupled signal translation |
| R (×2) | 10kΩ | Base current limiting |
| R (×2) | 10kΩ | Pull-ups for EN and GPIO0 |
| C | 1µF ceramic | EN pin RC delay (power-on reset) |

**Reference**: This circuit matches the ESP32-S2-SAOLA-1 schematic from Espressif. See also: [Espressif's Automatic Reset](https://qsantos.fr/2025/05/09/espressifs-automatic-reset/) for detailed explanation.

**Manual Override**:

The BOOT and RESET buttons (see Control Switches section) remain functional and can override the auto-reset circuit for manual bootloader entry when needed.

**Auto-Reset Bypass Jumpers (JP2, JP3)**:

Two inline shunt jumpers allow disabling the auto-reset circuit for debugging:

```
CH340C DTR# ────[JP2]──── Auto-reset circuit (Q1 base)
CH340C RTS# ────[JP3]──── Auto-reset circuit (Q2 base)
```

| Jumper | Installed (default) | Removed |
|--------|---------------------|---------|
| JP2 | DTR connected, auto-reset enabled | DTR disconnected |
| JP3 | RTS connected, auto-reset enabled | RTS disconnected |

- **Default configuration**: Both jumpers installed. Auto-reset works normally for programming.
- **Debug configuration**: Remove one or both jumpers to use serial communication without triggering resets.

The board ships with JP2 and JP3 installed.

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

This board is designed for manual assembly, not JLCPCB's SMT service. Order PCB only. All components will be hand-soldered.

However, the design SHOULD consider potential future migration to JLCPCB assembly by:

- Avoiding exotic through-hole parts not in JLCPCB's component library
- Using standard footprints where SMD alternatives exist
- Documenting through-hole to SMD migration paths in future revisions

### Component Sourcing

Prefer components available from LCSC (JLCPCB's component supplier) to enable potential future assembly service use. Where through-hole components are unavailable from LCSC, specify Digikey/Mouser part numbers as alternatives.

## Expansion and Future Provisions

### Deferred Features

The following capabilities are NOT implemented in this revision but MUST have physical provisions enabling future addition:

**Battery Charging Circuit** (deferred to v2):

Battery operation requires power path management beyond simple charging. The GPIO expansion header exposes 3.3V and 5V rails, and JP1 allows disabling the internal buck converter, enabling external battery circuit prototyping before integrating into v2.

**External Antenna**:

- Unpopulated U.FL connector footprint
- Trace to ESP32 antenna switching pin
- Enables replacement of PCB trace antenna with external antenna for extended WiFi range

**Additional I2C Sensors**:

- Spare I2C header pins
- Footprints for common sensor packages (e.g., pressure, light level)

**JTAG Debug**:

- 10-pin 2.54mm header footprint for JTAG
- Connected to GPIO12, GPIO13, GPIO14, GPIO15 per ESP32 JTAG standard
- Allows use of hardware debugger (OpenOCD, ESP-PROG)

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
| 2   | Q5-Q6     | NPN, general purpose        | Auto-reset circuit. Suggested: 2N2222A   | TO-92 or equivalent       |
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
| 1   | L1        | 3.9µH, ≥2.7A, low DCR       | Power inductor for AP63203            | SMD 4x4mm or 5x5mm   |
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
| 1   | J2        | 2×19 Female Header     | ESP32 breakout header        | 2.54mm, 22.86mm row spacing |
| 1   | JP1       | 2-pin Header           | Buck converter disable jumper| 2.54mm, no jumper installed |
| 2   | JP2-JP3   | 2-pin Header + Shunt   | Auto-reset bypass jumpers    | 2.54mm, jumpers installed   |

### Optional Components (Unpopulated)

These components have PCB footprints but are not populated in initial builds:

| Qty | Reference | Part/Requirement       | Description                      | Purpose/Notes                    |
| --- | --------- | ---------------------- | -------------------------------- | -------------------------------- |
| 2   | R21-R22   | 4.7kΩ 1/4W             | I2C pull-up resistors (optional) | If not present on sensor breakout |
| 1   | J7        | U.FL connector         | External antenna connector       | Future WiFi range extension      |

---

**Document Version**: 1.6
**Date**: 2026-01-03
**Author**: Development Team
**Status**: In Implementation - Schematic Review Complete

**Design Decisions Made**:
- ESP32 Module: ESP32-WROOM-32E-N4 selected for full control over support circuitry while using certified RF module
- USB-to-UART Bridge: CH340C selected for hand-solderability (SOP-16), built-in oscillator, and low cost
- Auto-Reset Circuit: Discrete NPN transistor approach (cross-coupled) with bypass jumpers (JP2, JP3) for debugging
- Voltage Regulation: AP63203 synchronous buck converter with disable jumper (JP1) for external power experimentation
- Protection: PTC fuse + TVS diode; USB D+/D- ESD protection omitted (adequate for dev board use)
- IR LED Driver: Single IRLML6344 logic-level MOSFET (SOT-23) with gate pull-down; LEDs powered from 3.3V rail
- IR GPIO Assignment: GPIO18 (IR_TX), GPIO19 (IR_RX) - adjacent pins, avoids strapping pins
- Temperature Sensor GPIO: GPIO4 (TEMP_DATA)
- User LEDs: GPIO16 (USER_LED1), GPIO17 (USER_LED2)
- Temperature Sensor: DHT22 (AM2302) single-wire module replacing BME280
- Breakout Header: DevKitC V4-compatible 2×19 header exposes all GPIO, power rails, UART, and I2C
- Jumper Configuration: JP1 ships open (buck enabled), JP2/JP3 ship with shunts installed (auto-reset enabled)
- Hand Assembly: Through-hole and large SMD components; TSOT26, SOP-16, SOT-23, 0805/1206 passives; BGA excluded

**Remaining Implementation Tasks**:
- Footprint assignment for all schematic components
- PCB layout design following constraints in this specification
- BOM finalization with specific vendor part numbers (see BOM Status section for pending confirmations)
