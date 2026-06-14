# IR Receiver

TSOP38238 receiver module for development and signal verification — loopback
testing of our own transmissions and capturing the physical remote, exactly as
the ESP8266 breadboard did. Production boards may omit it.

The module integrates the 38kHz bandpass filter, AGC, and demodulator. Output
is active-low: it pulls LOW while 38kHz-modulated IR is detected, preserving
the mark/space timing of the original transmission.

- Output goes to ESP32-C3 GPIO6 (v2 map; was GPIO19 on the v1 WROOM-32E),
  which supports external interrupts for timing-accurate edge capture.
- 100nF decoupling close to VCC — the TSOP parts are sensitive to supply
  noise, which shows up as false detections.

## Placement (revised 2026-06-14)

The receiver is dev/debug-only (production may omit it) and serves two jobs:
capturing fresh reference signals from the OEM remote, and self-validating
our own transmissions. Both want the lens on an accessible, user-facing board
edge — but self-validation also constrains *distance to our own TX*.

The original layout placed U4 in the IR-TX corner, ~11 mm from the nearest
LED (D2) and ~19 mm from the driver MOSFET (Q3). That is too close: the
TSOP's wide acceptance cone plus enclosure reflection saturate its AGC while
we transmit, so loopback returns a clipped blob rather than recoverable
mark/space timing — and the most EMI-sensitive part on the board ends up in
the 400 mA / 38 kHz drive loop's near field. It was the worst of both worlds:
too close to be EMI-clean, not usefully coupled for clean timing.

Revised target (see `layout.md` constraint 6): **south long edge, ~(150, 111),
lens facing south, ≥20 mm from Q3 and every IR LED.** At that distance U4
still hears its own TX via room/enclosure bounce (enough to confirm a burst
fired and check coarse timing) without saturating, and gets a clean window to
point the physical remote at. Pair it with an **optical baffle rib** between
the TX (east) and RX (south) windows in the 3D-printed enclosure. Reliable
*near-field* loopback timing, if ever needed, belongs on an external aimed
receiver (as on the breadboard), not the onboard one.
