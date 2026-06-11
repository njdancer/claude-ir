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
cargo-espflash) toggle DTR and RTS. Two cross-coupled 2N7002 N-channel
MOSFETs form an XOR-like gate that prevents the chip from being held in
reset when both DTR and RTS assert — which is exactly what happens when a
serial terminal opens the port.

*(Rev 1.2: Q1/Q2 changed from S8050 NPN BJTs to 2N7002 MOSFETs. The SOT-23
pinouts map 1:1 — B→G, E→S, C→D on the same pads — so the swap is layout-
neutral and consolidates Q1/Q2/Q4/Q5 onto one BOM line. Trade-off: each FET's
body diode adds a path from its source line into its output (RTS→EN, DTR→
GPIO0) that conducts only if the output is forced ~0.6V below the source
line — in practice only while RESET/BOOT is held with the port idle, briefly
loading a CH340 pin through the diode. Harmless, and the buttons still win;
desolder R21/R26 to break the path entirely if it ever matters.)*

| DTR | RTS | EN   | GPIO0 | Result               |
|-----|-----|------|-------|----------------------|
| 0   | 0   | HIGH | HIGH  | normal operation     |
| 0   | 1   | HIGH | LOW   | boot mode select     |
| 1   | 0   | LOW  | HIGH  | reset                |
| 1   | 1   | HIGH | HIGH  | normal operation     |

The key insight: the transistor sources are **not** grounded. Each source
connects to the *opposite* input signal (Q1: gate←DTR via 10kΩ, drain→EN,
source→RTS; Q2: gate←RTS via 10kΩ, drain→GPIO0, source→DTR). With both
inputs asserted, neither transistor sees a gate-source voltage, so neither
can pull its output low. The 10kΩ resistors (R3/R4) were the BJT base
resistors; for the FETs they're unnecessary but harmless (the gate draws no
DC current), so they stay to keep the layout untouched.

**Bypass links (R21/R26, 0Ω):** in series on the DTR and RTS lines (R21 on
DTR→Q2 emitter, R26 on RTS→Q1 emitter), so auto-reset can be disconnected when
debugging serial without spurious resets. Implemented as 0Ω SMD resistors
rather than through-hole header+shunt jumpers so JLCPCB places them at assembly;
desolder either to break auto-reset. Default: both populated (auto-reset
enabled). *(Spec §Auto-Reset still describes the older JP2/JP3 header jumpers —
queued for the spec reconciliation in ROADMAP H1.2.)*
