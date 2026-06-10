# USB-to-Serial Bridge

CH340C USB-UART bridge with auto-reset circuit for ESP32 programming. The
CH340C has a built-in oscillator (no external crystal) and the SOP-16 package
is hand-solderable.

## Power configuration

Operating at 3.3V: VCC and V3 are tied together, which bypasses the chip's
internal regulator. V3 needs a 100nF decoupling capacitor close to the pin.

**Critical:** the R232 pin must be tied LOW for TTL-level output. Tied HIGH it
outputs RS232 levels, which would damage the ESP32.

## UART wiring

TX/RX are crossed: CH340C TXD → ESP32 RXD (GPIO3), CH340C RXD ← ESP32 TXD
(GPIO1).

## Auto-reset circuit

Enables automatic bootloader entry when programming tools (esptool,
cargo-espflash) toggle DTR and RTS. Two cross-coupled NPN transistors form an
XOR-like gate that prevents the chip from being held in reset when both DTR
and RTS assert — which is exactly what happens when a serial terminal opens
the port.

| DTR | RTS | EN   | GPIO0 | Result               |
|-----|-----|------|-------|----------------------|
| 0   | 0   | HIGH | HIGH  | normal operation     |
| 0   | 1   | HIGH | LOW   | boot mode select     |
| 1   | 0   | LOW  | HIGH  | reset                |
| 1   | 1   | HIGH | HIGH  | normal operation     |

The key insight: the transistor emitters are **not** grounded. Each emitter
connects to the *opposite* input signal (Q1: base←DTR via 10kΩ, collector→EN,
emitter→RTS; Q2: base←RTS via 10kΩ, collector→GPIO0, emitter→DTR). With both
inputs asserted, neither transistor has a path to pull its output low.

**Bypass jumpers (JP2/JP3):** in series with DTR and RTS, so auto-reset can be
disconnected when debugging serial without spurious resets. Default: jumpers
installed (auto-reset enabled).
