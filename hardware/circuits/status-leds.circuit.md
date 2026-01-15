---
name: Status LEDs
description: |
  Serial activity and user-programmable status LEDs.

  Exposed nets:
  - 3V3: 3.3V power supply
  - 5V: 5V power supply (for MOSFET-driven LEDs)
  - GND: Ground
  - SERIAL_TXD: ESP32 GPIO1 (UART TX)
  - SERIAL_RXD: ESP32 GPIO3 (UART RX)
  - USER_LED1: ESP32 GPIO16
  - USER_LED2: ESP32 GPIO17
---

# Status LEDs

Visual indicators for serial activity and user-programmable status.
Serial LEDs are directly GPIO-driven; user LEDs use MOSFET drivers
to support higher-Vf blue LEDs from 5V supply.

## Interface Nets

[3V3]: net
[5V]: net
[GND]: net
[SERIAL_TXD]: net
[SERIAL_RXD]: net
[USER_LED1]: net
[USER_LED2]: net

## Serial Activity LEDs

Amber LEDs indicate UART TX/RX activity during programming and debug.
Cathodes connect directly to GPIO pins - LEDs light when GPIO is LOW.
This provides activity indication without additional GPIO.

### TX LED (D8)

[D8]: led(amber)

Vf ≈ 2.0V, target ~5mA: R = (3.3 - 2.0) / 0.005 = 260Ω, use 470Ω.
Cathode to GPIO1 (TXD) - lights during transmit activity.

[3V3 --- 470Ω --- D8.A]
[D8.K --- SERIAL_TXD]

### RX LED (D9)

[D9]: led(amber)

Same configuration as TX LED, cathode to GPIO3 (RXD).

[3V3 --- 470Ω --- D9.A]
[D9.K --- SERIAL_RXD]

## User Programmable LEDs

Blue LEDs driven through N-channel MOSFETs for:
- Consistent brightness (5V supply handles 3.2V forward voltage)
- Minimal GPIO current draw (~nA gate current)
- GPIO protection from LED faults

### User LED 1 (D11 - Blue)

[D11]: led(blue)
[Q4]: nmos(2N7002)

Vf ≈ 3.2V, target ~5mA from 5V: R = (5 - 3.2) / 0.005 = 360Ω, use 150Ω for brighter.

[5V --- 150Ω --- D11.A]
[D11.K --- Q4.D]
[Q4.S --- GND]

Gate drive with pull-down for clean off-state during boot.

[USER_LED1 --- Q4.G]
[USER_LED1 --- 10kΩ --- GND]

### User LED 2 (D12 - Blue)

[D12]: led(blue)
[Q5]: nmos(2N7002)

Same circuit as User LED 1.

[5V --- 150Ω --- D12.A]
[D12.K --- Q5.D]
[Q5.S --- GND]

[USER_LED2 --- Q5.G]
[USER_LED2 --- 10kΩ --- GND]
