---
name: IR Transmitter
description: |
  Four IR LEDs driven by MOSFET for omnidirectional 940nm transmission.

  Exposed nets:
  - 3V3: 3.3V power supply (for LEDs)
  - GND: Ground
  - IR_TX: GPIO control signal (from ESP32 GPIO18)
---

# IR Transmitter

Four TSAL6200 IR LEDs positioned at 0, 45, 90, and 135 degrees provide
omnidirectional coverage for room-wide IR transmission. Single N-channel
MOSFET drives all LEDs simultaneously for maximum efficiency.

## Interface Nets

[3V3]: net
[GND]: net
[IR_TX]: net

## IR LEDs

TSAL6200: 940nm wavelength matches receiver sensitivity.
[vf_led ==> 1.5V] forward voltage, targeting [i_led ==> 100mA] per LED.

[D2]: ir_led(940nm, TSAL6200)
[D3]: ir_led(940nm, TSAL6200)
[D4]: ir_led(940nm, TSAL6200)
[D5]: ir_led(940nm, TSAL6200)

## Current Limiting Resistors

LEDs powered from 3.3V for efficiency (vs 5V which wastes power in resistors).
R = (3.3V - 1.5V) / 0.1A = 18Ω

Power dissipation per resistor: I²R = 0.1² × 18 = 0.18W (use 1/4W rating).

[R9]: resistor(18Ω)
[R10]: resistor(18Ω)
[R11]: resistor(18Ω)
[R12]: resistor(18Ω)

[3V3 --- R9.1]
[R9.2 --- D2.A]

[3V3 --- R10.1]
[R10.2 --- D3.A]

[3V3 --- R11.1]
[R11.2 --- D4.A]

[3V3 --- R12.1]
[R12.2 --- D5.A]

## Common Cathode Connection

All LED cathodes connect to MOSFET drain for single-switch control.

[IR_LED_CATHODE]: net

[D2.K --- IR_LED_CATHODE]
[D3.K --- IR_LED_CATHODE]
[D4.K --- IR_LED_CATHODE]
[D5.K --- IR_LED_CATHODE]

## MOSFET Driver

IRLML6344 logic-level N-channel MOSFET handles 4 × 100mA = 400mA total.
[vgs_th ==> 1.0V] threshold, fully enhanced at 3.3V gate drive.
[rds_on ==> 27mΩ] at Vgs=2.5V minimizes power loss.

[Q3]: nmos(IRLML6344)

[IR_LED_CATHODE --- Q3.D]
[Q3.S --- GND]

### Gate Drive Circuit

10kΩ series resistor limits inrush current and provides ESD protection.
100kΩ pull-down ensures MOSFET is OFF during boot/reset when GPIO is high-Z.

[MOSFET_GATE]: net

[IR_TX --- 10kΩ --- MOSFET_GATE]
[MOSFET_GATE --- 100kΩ --- GND]
[MOSFET_GATE --- Q3.G]

## IR Transmit Indicator LED

Red LED lights when IR is transmitting, providing visual feedback.
Directly driven from IR_TX signal (in parallel with MOSFET gate drive).

[D10]: led(red)

Vf ≈ 1.9V, target ~10mA: R = (3.3 - 1.9) / 0.01 = 140Ω, use 470Ω for dimmer.

[IR_TX --- 470Ω --- D10.A]
[D10.K --- GND]
