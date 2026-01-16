---
name: USB-to-Serial Bridge
description: |
  CH340C USB-UART bridge with auto-reset circuit for ESP32 programming.

  Exposed nets:
  - USB_DP: USB D+ from connector
  - USB_DM: USB D- from connector
  - 3V3: 3.3V power supply
  - GND: Ground
  - TXD: Serial transmit (to ESP32 RXD)
  - RXD: Serial receive (from ESP32 TXD)
  - ESP_EN: ESP32 enable signal (directly connected to chip)
  - ESP_GPIO0: ESP32 boot mode pin (directly connected to chip)
---

# USB-to-Serial Bridge

CH340C provides USB-to-UART conversion for programming and serial console.
Built-in oscillator eliminates external crystal. SOP-16 package is hand-solderable.

## Interface Nets

[USB_DP]: net
[USB_DM]: net
[3V3]: net
[GND]: net
[TXD]: net
[RXD]: net
[ESP_EN]: net
[ESP_GPIO0]: net

## CH340C IC

[U2]: ch340c

### Power Connections

Operating at 3.3V: tie VCC and V3 together. The V3 pin bypasses the
internal regulator when connected to VCC.

[3V3 --- U2.VCC]
[3V3 --- U2.V3]
[U2.GND --- GND]

V3 requires 100nF decoupling capacitor close to pin.

[U2.V3 --- 100nF --- GND]

### USB Interface

[USB_DP --- U2.UDP]
[USB_DM --- U2.UDM]

### TTL Level Selection

R232 pin must be tied LOW for TTL-level output (3.3V compatible with ESP32).
If tied HIGH, outputs RS232 levels which would damage ESP32.

[U2.R232 --- GND]

### UART Interface

TX/RX are crossed: CH340C TXD connects to ESP32 RXD, and vice versa.
These connections go to the main ESP32 circuit.

[U2.TXD --- TXD]
[U2.RXD --- RXD]

## Auto-Reset Circuit

The auto-reset circuit enables automatic bootloader entry when programming
tools (esptool, cargo-espflash) assert DTR and RTS signals.

Cross-coupled NPN transistors form an XOR-like gate that prevents the chip
from being held in reset when both DTR and RTS are asserted (which happens
when opening a serial port).

### Truth Table

| DTR | RTS | EN    | GPIO0 |
|-----|-----|-------|-------|
| 0   | 0   | HIGH  | HIGH  | (normal operation)
| 0   | 1   | HIGH  | LOW   | (boot mode select)
| 1   | 0   | LOW   | HIGH  | (reset)
| 1   | 1   | HIGH  | HIGH  | (normal operation)

### Bypass Jumpers

JP2 and JP3 allow disconnecting DTR/RTS for debugging serial without
triggering resets. Default: jumpers installed (auto-reset enabled).

[JP2]: jumper_2_open
[JP3]: jumper_2_open

[U2.nDTR --- JP2.A]
[U2.nRTS --- JP3.A]

### Cross-Coupled Transistors

The key insight: emitters are NOT grounded. Each transistor's emitter
connects to the opposite input signal, creating the XOR behavior.

[Q1]: npn_transistor
[Q2]: npn_transistor

Internal nets for the cross-coupling:

[DTR_INTERNAL]: net
[RTS_INTERNAL]: net
[Q1_BASE]: net
[Q2_BASE]: net

[JP2.B --- DTR_INTERNAL]
[JP3.B --- RTS_INTERNAL]

Q1 controls EN pin:
- Base driven by DTR through 10kΩ
- Collector pulls EN low when conducting
- Emitter connected to RTS (cross-coupled)

[DTR_INTERNAL --- 10kΩ --- Q1_BASE]
[Q1_BASE --- Q1.B]
[Q1.C --- ESP_EN]
[Q1.E --- RTS_INTERNAL]

Q2 controls GPIO0 pin:
- Base driven by RTS through 10kΩ
- Collector pulls GPIO0 low when conducting
- Emitter connected to DTR (cross-coupled)

[RTS_INTERNAL --- 10kΩ --- Q2_BASE]
[Q2_BASE --- Q2.B]
[Q2.C --- ESP_GPIO0]
[Q2.E --- DTR_INTERNAL]
