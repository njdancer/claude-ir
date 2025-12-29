# ESP32 IR Remote Control Development Board - Hardware Specification v1.0

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

The power subsystem MUST implement overcurrent protection (trip at 2A), overvoltage protection (clamp below 6V), and reverse polarity protection. These protections guard against common development mistakes such as incorrect power supply connections.

### Battery Provisions

While this development board does not implement battery charging circuitry, it MUST provide connection points and monitoring capability for future battery integration. Specifically:

- Solder pads or headers for connecting a TP4056 charging module
- Battery input connection via JST-PH 2-pin connector
- Voltage divider network enabling battery voltage monitoring through ESP32 ADC

These provisions allow testing of battery-powered operation modes (particularly deep sleep power consumption) without requiring a complete charging circuit implementation. The board does not constrain physical mounting of battery holders, which may be connected externally during testing.

## Component Specifications

### Microcontroller Module

**Specified Module**: ESP32-DevKitC-32E (Espressif official development board)

The board MUST use the ESP32-DevKitC-32E module, selected for its official support, comprehensive documentation, and widespread availability. This 38-pin module uses the ESP32-WROOM-32E core with integrated USB-to-UART conversion (CP2102) and includes onboard 3.3V regulation for the ESP32 chip itself.

The module exposes sufficient GPIO pins to support:

- 4× IR LED driver signals
- 1× IR receiver input
- I2C interface (SDA/SCL) for temperature sensor
- UART0 (USB programming)
- User programmable GPIO for expansion

**Power Architecture**: The board MUST provide independent 3.3V regulation rather than relying on the module's onboard regulator. Module regulators typically limit to 500-600mA which is marginal under the ~470mA peak load calculated for this design. Independent regulation provides:

- Adequate current headroom for reliable operation
- Reduced thermal stress on the module
- Flexibility for future expansion beyond module regulator capacity

The module connects to the board's 3.3V rail via its 3V3 pin, and to the USB programming connection via its existing USB port.

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

**Interface**: I2C
**Mounting**: Breakout board with pin headers (female headers on main board)

**Sensor Requirements**:

- Temperature accuracy: ±1.0°C across 18-28°C range (typical indoor AC environment)
- Supply voltage: 3.3V compatible
- Interface: I2C (configurable address to avoid conflicts)
- Sleep current: <10µA (for battery operation testing)
- Response time: <1 second for room temperature changes

**Additional Capabilities** (optional but useful):

- Humidity sensing (enables comfort index calculations)
- Pressure sensing (enables weather-aware operation modes)

**Recommended Part**: Bosch BME280 on breakout board meets all requirements and adds humidity/pressure sensing. Pre-assembled breakout boards (Adafruit #2652, SparkFun SEN-13676, or generic) avoid hand-soldering the small LGA package while providing necessary pull-ups and level shifting.

### USB-C Power Connector

**Connector Requirements**:

- Mounting: Through-hole or large SMD with hand-solderable pins (not fine-pitch SMT-only)
- Pinout: USB 2.0 minimum (VBUS, GND, CC1, CC2 accessible; D+/D- optional)
- Mechanical strength: Through-hole anchor pins or large mounting pads
- Current rating: ≥3A continuous

**Specified Connector**: GCT USB4085-GF-A (fully through-hole USB-C receptacle)

This connector is specified due to its through-hole construction enabling reliable hand assembly and its availability from major distributors. Alternative through-hole USB-C receptacles with equivalent pinout are acceptable.

**Power Delivery Configuration**: CC1 and CC2 pins MUST connect to ground through 5.1kΩ ±5% resistors to signal 5V/3A power capability to USB-PD sources. This resistor configuration enables the board to draw sufficient current from modern USB-C chargers without implementing complex PD negotiation. D+/D- pins remain unconnected (USB data handled by ESP32 module's onboard USB interface).

### Voltage Regulation

The board MUST regulate the USB 5V input to stable 3.3V for powering the ESP32 module, IR receiver, temperature sensor, and status LEDs. A buck (step-down) switching regulator is REQUIRED for efficiency and thermal performance.

**Regulator Requirements**:

- Type: Buck (step-down) switching regulator
- Input voltage: 4.5-5.5V (USB voltage range)
- Output voltage: 3.3V ±3% (3.2-3.4V)
- Output current: ≥1A continuous (supports 470mA peak + margin)
- Switching frequency: 50-500kHz (balances efficiency and component size)
- Efficiency: ≥80% at 300mA load
- Package: Hand-solderable (TO-220, SOIC-8, or equivalent through-hole/large SMD)
- Protection: Thermal shutdown, current limiting, short circuit protection

**Recommended Implementation**: LM2596-3.3 (fixed 3.3V output) in TO-220-5 package

- Through-hole package (easiest hand assembly)
- Fixed 3.3V output version simplifies design (no feedback resistors needed)
- 3A output capability (ample headroom)
- ~85% efficiency (vs ~60% for LDO)
- Power dissipation: ~0.15W at 330mA average (vs 0.6W for LDO)
- Excellent documentation and reference designs available
- Wide availability and low cost

**Required Support Components**:

1. **Input capacitor**: 100µF electrolytic, 16V (placed close to VIN pin)
2. **Output capacitor**: 220µF electrolytic or 47µF low-ESR ceramic, 10V (placed close to output)
3. **Inductor**: 68-100µH, ≥1.5A saturation current, low DCR (<0.2Ω)
   - Package: Radial through-hole or large SMD (hand-solderable)
   - Suggested: Bourns 1140 series or similar power inductor
4. **Catch diode**: 1N5822 Schottky diode (3A, 40V) in DO-201AD through-hole package
   - Note: Some LM2596 modules have integrated diode; check datasheet
5. **Bypass capacitors**: 100nF ceramic at input and output

**PCB Layout Considerations**:

- Keep switching node (connection between inductor, diode, and SW pin) traces short and thick
- Input capacitor must be placed immediately adjacent to VIN and GND pins
- Output capacitor placed close to output and load
- Ground plane provides good thermal dissipation for TO-220 package
- Consider adding copper pour area under TO-220 for heat spreading

**Alternative**: Pre-assembled buck converter modules (e.g., MP1584EN module) can be used if board space permits, trading flexibility for assembly simplicity.

### Protection Components

The power input path MUST include:

**Overcurrent Protection**:

- Type: Resettable PTC fuse (polyfuse) or equivalent resettable overcurrent device
- Hold current: 1.0-1.2A (allows normal operation)
- Trip current: 1.8-2.2A (protects against shorts)
- Package: Through-hole radial preferred
- **Suggested Part**: Bourns MF-R110 or equivalent

**Overvoltage Protection**:

- Type: TVS (Transient Voltage Suppression) diode
- Clamp voltage: 5.5-6.5V (protects 5V circuit, below regulator absolute maximum)
- Transient power rating: ≥400W
- Package: Hand-solderable (DO-214AA/SMB, DO-214AB/SMC, or through-hole)
- Placement: Immediately after USB connector, before other circuitry
- **Suggested Part**: SMBJ5.0A or equivalent

**Reverse Polarity Protection**:

The circuit MUST prevent damage if incorrect polarity is applied (non-compliant charger or reversed battery connection).

- **Option A - Schottky Diode**: Series diode (e.g., 1N5817: 1A, 0.4V drop, simple)
- **Option B - P-MOSFET**: P-channel MOSFET with gate-source resistor (e.g., AO3401: efficient, ~0V drop, more complex)

Either approach is acceptable. Series diode is simpler but dissipates ~0.2W; P-MOSFET is more efficient but requires careful gate biasing.

### Status Indicators

The board MUST include visible LED indicators for debugging and status monitoring:

**Power LED** (suggested color: Green):

- Function: Illuminated whenever regulated 3.3V is present
- Connection: 3.3V rail through current-limiting resistor
- Target current: 2-5mA (balance visibility and power consumption)

**Serial TX/RX LEDs** (suggested color: Yellow/Amber):

- Function: Visual confirmation of serial communication during programming
- Connection: UART0 TX/RX lines with series resistors (may require additional current-limiting)
- Target current: 2-5mA per LED

**IR Transmit LED** (suggested color: Red):

- Function: Indicates IR transmission activity
- Connection: Paralleled with IR LED driver circuit or GPIO-controlled
- Target current: 5-10mA (must be visible during brief transmission pulses)

**User Programmable LEDs** (suggested quantity: 2, suggested color: Blue):

- Function: Software-controlled for debugging and status indication
- Connection: Available GPIO pins through current-limiting resistors
- Target current: 2-5mA per LED
- PCB silkscreen MUST label GPIO numbers for firmware reference

**LED Requirements**:

- Package: Through-hole (3mm or 5mm diameter) or equivalent hand-solderable package
- Mounting: Positioned for visibility when board is horizontal (vertical mounting or edge-mount)
- Current-limiting resistors: Calculated based on LED forward voltage and target current

All status LED current-limiting resistors SHOULD target 2-5mA for adequate brightness while minimizing power consumption during battery operation testing.

### Control Switches

The board MUST include two momentary push buttons for ESP32 control:

**RESET Button**:

- Function: Initiates complete ESP32 system reset (equivalent to power cycle)
- Connection: Connects ESP32 EN (enable) pin to ground when pressed
- Pull-up: 10kΩ resistor to 3.3V on EN pin (enables ESP32 to run when button released)

**BOOT Button**:

- Function: Enters bootloader/programming mode when held during reset
- Connection: Connects GPIO0 to ground when pressed
- Pull-up: 10kΩ resistor to 3.3V on GPIO0 (normal operation mode when released)
- Usage: Hold BOOT, press RESET, release both to enter programming mode

**Switch Requirements**:

- Type: Tactile momentary switch, normally-open (NO)
- Package: Through-hole or equivalent hand-solderable mounting
- Size: 6mm×6mm typical (other sizes acceptable)
- Actuation force: 100-300gf (comfortable for frequent development use)
- Positioning: Accessible while USB cable is connected

Both buttons enable standard ESP32 programming and debugging workflows and are essential for development.

### Development Headers

The board MUST expose the following connections via pin headers for development and expansion:

**UART Debug Header** (4-pin):

- Pinout: GND, 3.3V, TX (GPIO1), RX (GPIO3)
- Purpose: External serial console, connection to USB-UART adapters
- Labeling: Clearly marked on silkscreen with pin functions

**I2C Expansion Header** (4-pin):

- Pinout: GND, 3.3V, SDA (GPIO21), SCL (GPIO22)
- Purpose: Additional I2C peripherals beyond the temperature sensor
- Note: Shares I2C bus with BME280; address conflicts must be avoided

**GPIO Expansion Header** (8-10 pins):

- Pinout: Multiple GPIO pins not otherwise allocated, plus GND and 3.3V
- Purpose: Breakout board connection, peripheral testing, firmware expansion
- GPIO priority: Pins supporting ADC, PWM, and touch sensing
- Labeling: Each pin labeled with GPIO number on silkscreen

**Battery Connection** (2-3 pin):

- Pinout: Battery positive (B+), Battery negative (GND), optional battery voltage sense
- Purpose: External battery connection during power consumption testing
- Connector type: JST-PH 2-pin connector or pin header

**Header Specifications**:

- Pitch: 2.54mm (0.1") PREFERRED for compatibility with standard jumper wires and modules
- Pitch alternatives: Other pitches acceptable if hand-solderable and clearly documented
- Gender: Female headers RECOMMENDED on board (accepts male pins from modules/jumpers)
- Orientation: Right-angle or vertical based on board layout optimization

The key requirement is development flexibility - enabling connection of external modules, test equipment, and expansion boards during firmware development.

## Circuit Design Requirements

### IR Transmitter Driver Circuit

Each IR LED MUST drive through an independent NPN transistor configured as a common-emitter switch.

**Transistor Requirements**:

- Type: NPN bipolar junction transistor
- Collector current: ≥100mA continuous, ≥200mA peak
- Current gain (hFE): ≥100 (ensures saturation with 3mA base current)
- Package: Through-hole (TO-92, TO-220, or equivalent hand-solderable)
- **Suggested Parts**: 2N2222A, PN2222A, BC337, or equivalent general-purpose NPN

**Base Drive Circuit**:

- ESP32 GPIO → Base resistor → Transistor base
- Base resistor value: 1kΩ typical (limits base current to ~3mA at 3.3V GPIO high)
- This ensures transistor saturation (VCE < 0.3V) when driving 100mA collector current

**Collector Load Circuit**:

- Supply voltage (5V) → Current-limiting resistor → IR LED → Transistor collector
- Current-limiting resistor calculation for 100mA target current:
  ```
  R_limit = (V_supply - V_LED_forward - V_CE_sat) / I_target
  R_limit = (5V - 1.5V - 0.3V) / 0.1A = 32Ω
  ```
- Use nearest standard value (33Ω recommended)
- Resistor power rating: ≥0.5W (dissipates ~0.3W during transmission)

**GPIO Control Architecture**:

- All four IR LED driver transistors MAY share a common ESP32 GPIO pin (simultaneous activation)
- OR use independent GPIO pins for each LED (selective activation during testing)
- The specification permits either approach; firmware can test which provides better performance

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

The GPIO pin MUST support external interrupts to capture timing-accurate signal edges for protocol decoding.

### Temperature Sensor Interface

The temperature sensor breakout board connects via I2C using ESP32's default I2C pins (GPIO21 = SDA, GPIO22 = SCL).

**I2C Connection Requirements**:

- Pull-up resistors: 4.7kΩ on both SDA and SCL lines
- Pull-up provisioning: If breakout board includes pull-ups, main board pull-ups are optional
- Pull-up location: Main board SHOULD provide footprints for optional I2C pull-up resistors
- Supply voltage: 3.3V and GND from regulated supply

**Mounting**:

- Connection method: Pin headers (female headers on main board recommended)
- Rationale: Allows breakout board removal for testing or replacement without desoldering
- Alternative: Direct soldering acceptable if header mounting is impractical

The I2C bus is shared with any additional sensors connected to the I2C expansion header. All devices must use unique I2C addresses.

### Battery Voltage Monitoring

To enable battery voltage measurement, the board MUST implement a 50% voltage divider from the battery positive terminal to an ESP32 ADC-capable GPIO pin:

```
Battery+ ----[100kΩ]----+----[100kΩ]---- GND
                        |
                   [100nF cap]
                        |
                  ESP32 ADC Pin (GPIO34, GPIO35, GPIO36, or GPIO39)
```

This divider scales the 3.0-4.2V battery range to 1.5-2.1V suitable for the ESP32's ADC. The 100nF capacitor provides low-pass filtering to reduce ADC noise.

### USB-C Power Entry

The USB-C connector's VBUS pin connects to the protection circuit as follows:

```
USB VBUS ----[PTC Fuse]----[Reverse Protection]----[TVS to GND]----[Voltage Regulator]
```

CC1 and CC2 pins each connect through 5.1kΩ resistors to GND. Shield pins connect to PCB ground plane. D+/D- pins remain unconnected as USB data communication is handled by the ESP32 module's integrated USB-UART chip.

## Power Budget Analysis

### Current Consumption Estimates

**3.3V Rail Loads** (WiFi active, periodic IR transmission):

- ESP32 module: 80-120mA (WiFi idle)
- WiFi transmission peaks: 240mA for <1s bursts
- IR receiver: 0.5mA
- BME280: 1.8µA (negligible)
- Status LEDs (6× @ 3mA): 18mA
- **3.3V rail total: ~330mA average, ~470mA peak**

**5V Rail Loads** (IR transmission):

- IR LEDs (4× @ 100mA, 30% duty cycle): 120mA average during active periods
- IR LEDs powered directly from 5V (not through buck converter)

**Buck Converter Power Analysis**:

- Input power (from USB): ~330mA × 3.3V / 0.85 efficiency = ~1.28W → 256mA @ 5V
- Peak input power: ~470mA × 3.3V / 0.85 = ~1.82W → 364mA @ 5V
- Buck converter power dissipation: ~0.15W at average load (vs 0.6W for LDO)
- Thermal performance: Minimal heat generation, TO-220 package provides adequate cooling

**Total USB Current Draw**:

- Average: 256mA (3.3V loads) + 120mA (IR LEDs) = ~376mA
- Peak: 364mA (3.3V loads) + 400mA (IR LEDs 100% duty) = ~764mA
- Well within USB-C 3A capability

**Battery Capacity Estimate** (future):

- With 3000mAh cell @ 3.7V: 11.1Wh capacity
- Average power consumption: ~1.3W → 8.5 hours continuous active use
- With deep sleep (10s active per 10 minutes): weeks of operation
- Buck converter efficiency improves battery life vs LDO (15-20% longer runtime)

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
- Maximum load: 1A continuous (buck converter rated for 3A)

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

**Battery Charging Circuit**:

- Solder pads for TP4056 charging IC (SOP-8 footprint)
- Pads for charging indicator LEDs and current programming resistor
- Connection path from USB 5V to charging circuit input

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

### Core Components

| Qty | Reference | Part/Requirement            | Description                              | Package/Notes             |
| --- | --------- | --------------------------- | ---------------------------------------- | ------------------------- |
| 1   | U1        | **ESP32-DevKitC-32E**       | ESP32 Development Module (specified)     | 38-pin DIP                |
| 4   | LED1-LED4 | 940nm IR LED, ≥100mA        | Suggested: TSAL6200 (Vishay)             | 5mm through-hole          |
| 4   | Q1-Q4     | NPN, ≥100mA, hFE≥100        | Suggested: 2N2222A, PN2222A, BC337       | TO-92 or equivalent       |
| 1   | U2        | 38kHz IR Receiver           | Suggested: TSOP1838, TSOP4838 (Vishay)   | 3-pin through-hole module |
| 1   | U3        | BME280 Breakout             | Recommended: Adafruit #2652, SparkFun    | Breakout with headers     |
| 1   | J1        | **USB4085-GF-A (GCT)**      | USB-C Receptacle (specified footprint)   | Through-hole              |
| 1   | U4        | Buck Converter IC           | Recommended: LM2596-3.3 (fixed 3.3V)     | TO-220-5 through-hole     |

### Protection and Power

| Qty | Reference | Part/Requirement            | Description                           | Package/Notes      |
| --- | --------- | --------------------------- | ------------------------------------- | ------------------ |
| 1   | F1        | PTC Fuse, 1.1A/2A           | Suggested: Bourns MF-R110             | Through-hole radial |
| 1   | D1        | TVS Diode, 5.5-6.5V clamp   | Suggested: SMBJ5.0A                   | DO-214AA or larger |
| 1   | D2        | Schottky or P-MOSFET        | Reverse protection (see spec notes)   | See spec section   |
| 2   | R1-R2     | 5.1kΩ ±5% 1/4W              | USB-C CC resistors                    | Axial or 1206 SMD  |

### Buck Converter Support Components

| Qty | Reference | Part/Requirement            | Description                           | Package/Notes        |
| --- | --------- | --------------------------- | ------------------------------------- | -------------------- |
| 1   | L1        | 68-100µH, ≥1.5A, low DCR    | Power inductor (Bourns 1140 series)   | Radial or large SMD  |
| 1   | D3        | Schottky 3A, 40V            | Catch diode (e.g., 1N5822)            | DO-201AD through-hole |
| 1   | C1        | 100µF 16V electrolytic      | Buck input capacitor                  | Radial through-hole  |
| 1   | C2        | 220µF 10V electrolytic      | Buck output capacitor                 | Radial through-hole  |
| 2   | C3-C4     | 100nF ceramic               | Bypass capacitors (input/output)      | 1206 SMD or radial   |
| 2+  | C5-C7     | 100nF ceramic               | Additional bypass capacitors          | 1206 SMD or radial   |

### IR Transmitter Circuit

| Qty | Reference | Part/Requirement      | Description                        | Package/Notes      |
| --- | --------- | --------------------- | ---------------------------------- | ------------------ |
| 4   | R3-R6     | 33Ω ≥0.5W             | LED current limiting (~100mA)      | Axial, 1W preferred |
| 4   | R7-R10    | 1kΩ 1/4W              | Transistor base resistors          | Axial or 1206 SMD  |

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
| 1   | J2        | 4-pin Header           | UART debug header            | 2.54mm preferred            |
| 2   | J3-J4     | 4-pin Header           | I2C and temp sensor headers  | 2.54mm preferred            |
| 1   | J5        | 8-10 pin Header        | GPIO expansion header        | 2.54mm preferred            |
| 1   | J6        | 2-pin Connector        | Battery connection           | JST-PH or header            |

### Battery Monitoring

| Qty | Reference | Part/Requirement | Description                  | Package/Notes     |
| --- | --------- | ---------------- | ---------------------------- | ----------------- |
| 2   | R19-R20   | 100kΩ ±1%        | Voltage divider resistors    | Axial or 1206 SMD |
| 1   | C8        | 100nF ceramic    | ADC filtering capacitor      | 1206 SMD or radial |

### Optional Components (Unpopulated)

These components have PCB footprints but are not populated in initial builds:

| Qty | Reference | Part/Requirement       | Description                      | Purpose/Notes                    |
| --- | --------- | ---------------------- | -------------------------------- | -------------------------------- |
| 1   | U5        | TP4056 or equivalent   | Li-ion charging IC               | Future battery charging circuit  |
| 2   | R21-R22   | 4.7kΩ 1/4W             | I2C pull-up resistors (optional) | If not present on sensor breakout |
| 1   | J7        | U.FL connector         | External antenna connector       | Future WiFi range extension      |

---

**Document Version**: 1.0
**Date**: 2025-12-29
**Author**: Development Team
**Status**: Ready for Implementation

**Design Decisions Made**:
- ESP32 Module: ESP32-DevKitC-32E selected for official support and availability
- Voltage Regulation: Buck converter (LM2596-3.3 recommended) for ~85% efficiency and minimal heat generation (~0.15W vs 0.6W for LDO)
- Hand Assembly: Through-hole and large SMD components permitted; 2.54mm headers preferred but not required; BGA excluded

**Remaining Implementation Tasks**:
- GPIO pin assignment mapping (requires ESP32-DevKitC-32E pinout verification to avoid conflicts)
- PCB layout design following constraints in this specification
- BOM finalization with specific vendor part numbers
