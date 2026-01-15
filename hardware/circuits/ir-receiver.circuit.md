---
name: IR Receiver
description: |
  38kHz IR receiver module for development and signal verification.

  Exposed nets:
  - 3V3: 3.3V power supply
  - GND: Ground
  - IR_RX: Demodulated output signal (to ESP32 GPIO19)
---

# IR Receiver

TSOP38238 IR receiver module for development and debugging.
Built-in 38kHz bandpass filter, AGC, and demodulator.
Production boards may omit this component.

## Interface Nets

[3V3]: net
[GND]: net
[IR_RX]: net

## Receiver Module

[U4]: ir_receiver(TSOP38238)

Output is active-low: pulls LOW when 38kHz modulated IR detected.
Preserves pulse timing from original transmission after demodulation.

### Power Connections

[3V3 --- U4.VCC]
[U4.GND --- GND]

### Signal Output

Connects to ESP32 GPIO19 which supports external interrupts
for timing-accurate edge capture.

[U4.OUT --- IR_RX]

### Decoupling

100nF ceramic close to VCC pin suppresses power supply noise
that could trigger false IR detections.

[U4.VCC --- 100nF --- GND]
