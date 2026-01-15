# Example: ESP32 IR Controller

This example shows a complete circuit.md file for an ESP32-based infrared remote controller.

```markdown
---
name: ESP32 IR Controller
description: |
  Smart controller for AC unit with HomeKit integration.
  
  Exposed nets:
  - VBUS: 5V USB power input
  - 3V3: Regulated 3.3V rail
  - GND: Ground
---

# ESP32 IR Controller

A smart IR blaster for controlling an AC unit, with WiFi connectivity for 
HomeKit integration.

## Power Supply

[VBUS]: net
[3V3]: net
[GND]: net

USB provides 5V which we regulate down to 3.3V for the ESP32.

[U1]: ams1117(3.3V)

[VBUS --- U1.VIN]
[U1.VOUT --- 3V3]
[U1.GND --- GND]

Input capacitor for stability and output capacitor per datasheet.
AMS1117 requires low-ESR capacitors, 10µF ceramic recommended.

[VBUS --- 10µF --- GND]
[3V3 --- 10µF --- GND]

The regulator has dropout of [dropout ==> 1.1V] so we need at least 
4.4V input for stable 3.3V output.

## MCU

[U2]: esp32_wroom_32

[3V3 --- U2.VCC]
[U2.GND --- GND]

### Decoupling

Each VCC pin needs local decoupling:

[3V3 --- 100nF --- GND]

### Boot Configuration

EN pin needs an RC delay for stable boot. Pull high with 10k, 
filter with 100nF to ground.

[EN]: net

[3V3 --- 10kΩ --- EN]
[EN --- 100nF --- GND]
[EN --- U2.EN]

GPIO0 must be high for normal boot (low = download mode).
External pull-up ensures normal operation.

[GPIO0]: net

[3V3 --- 10kΩ --- GPIO0]
[GPIO0 --- U2.GPIO0]

## IR Transmitter

[IR_OUT]: net
[IR_LED_CATHODE]: net

GPIO4 will output the 38kHz modulated IR signal.

[U2.GPIO4 --- IR_OUT]

We use a transistor to drive the IR LED since GPIO can't source
enough current directly. IR LED forward voltage is approximately 
[vf_ir ==> 1.2V] and we want [i_led ==> 100mA] for good range.

[Q1]: 2n2222

[IR_OUT --- 1kΩ --- Q1.B]
[Q1.E --- GND]

IR LED with current limiting resistor.
R = (3.3V - 1.2V) / 100mA = 21Ω, use 22Ω standard value.

[D1]: ir_led(940nm)
[R_LED]: resistor(22Ω)

[3V3 --- D1.A]
[D1.K --- IR_LED_CATHODE]
[IR_LED_CATHODE --- R_LED.1]
[R_LED.2 --- Q1.C]

## Status LED

[STATUS]: net

Simple status LED on GPIO2 (directly driveable).
Green LED, ~10mA, Vf ≈ 2V, so R = (3.3-2)/0.01 = 130Ω, use 150Ω.

[D2]: led(green)

[U2.GPIO2 --- STATUS]
[STATUS --- 150Ω --- D2.A]
[D2.K --- GND]

## USB Connector

[J1]: usb_c_power_only

[J1.VBUS --- VBUS]
[J1.GND --- GND]

USB-C requires pull-downs on CC lines to advertise as a sink device.
5.1kΩ indicates we accept 5V default power.

[J1.CC1 --- 5.1kΩ --- GND]
[J1.CC2 --- 5.1kΩ --- GND]
```

## Key Patterns Demonstrated

### Functional Grouping
The circuit is organized by function (Power, MCU, IR, Status, USB) with prose
explaining each section's purpose.

### Design Rationale
Calculations and component value justifications are inline:
- Current limiting resistor values
- Voltage drop calculations
- Why specific values were chosen

### Properties for Key Values
Important parameters captured with `[key ==> value]` syntax:
- `[dropout ==> 1.1V]`
- `[vf_ir ==> 1.2V]`
- `[i_led ==> 100mA]`

### Mixed Declaration Styles
- Named passives when referenced elsewhere: `[R_LED]: resistor(22Ω)`
- Inline passives for simple cases: `[3V3 --- 10kΩ --- EN]`

### Descriptive Net Names
Nets describe function: `IR_OUT`, `IR_LED_CATHODE`, `STATUS`, not `NET1`.
