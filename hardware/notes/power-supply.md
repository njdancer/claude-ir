# Power Supply

USB-C power entry with overcurrent and overvoltage protection, followed by an
**AMS1117-3.3 LDO** for 3.3V regulation. (This replaced the v1 AP63203 buck in
the v2 cost-down redesign — see the v2 change set in `ROADMAP.md`.)

## USB-C input

The USB-C receptacle (SMD 16-pin, XKB U262-16XN-4BVC11 = JLCPCB C393939)
provides 5V power and the USB 2.0 data lines; the shield ties to ground for
EMI. The CC lines each have 5.1kΩ pull-downs (R1/R2) to advertise the board as
a default-power 5V sink — without these, a USB-C host or PD supply will not
provide VBUS. The 16P part has through-hole mounting posts, so it is
mechanically sturdy despite SMD signal pads.

## Input protection

- **Overcurrent:** PTC resettable fuse F1, 1.1A hold / ~2.2A trip, protects
  against downstream shorts.
- **Overvoltage:** TVS diode D1 (SMB) clamps spikes on +5V. **Orientation is
  load-bearing:** pad 1 = cathode = silk band = **+5V**, anode = GND (the
  polarity table locks `D1.1 = +5V`). A reversed D1 sits forward across the
  rail and the board won't power — align the band with the on-board +5V marker.

Reverse-polarity protection is intentionally omitted on the USB-C input — the
connector enforces orientation.

## 3.3V regulation (AMS1117-3.3 LDO, U1)

A linear regulator was chosen over the buck for the v2 cost-down: it's a Basic
JLCPCB part (no feeder fee), drops the inductor + bootstrap cap, and simplifies
the layout. On USB power its dissipation is acceptable (see thermal, below).

**Load check (does the LDO cover our worst case?):** the 3V3 rail worst case is
C3 WiFi-TX peak ~345mA + the IR array (4×86mA = 344mA, but 38kHz-pulsed at ~⅓
duty → ~115mA average, bulk-cap filtered) + misc ~30mA ≈ **~490mA sustained**
(~720mA transient). The AMS1117 (1A rated) gives ~2× current margin. Dropout is
~0.8V at 0.5A vs ~1.4V of headroom (USB 4.7V min post-fuse − 3.3V), so it keeps
regulating even through the WiFi peak at low USB voltage.

- **Output cap:** ≥22µF ceramic for stability (C2/C3), placed at the VOUT pin.
- **Input cap:** ceramic at VIN (C1) for transient stability.

**Thermal.** Dissipation is (5 − 3.3) × 0.49 ≈ **0.83W**. A bare SOT-223 tab
(θ_JA ≈ 135 °C/W) would reach T_J ≈ 140 °C — over the 125 °C limit. U1 is
therefore placed in the open NW corner, rotated so the tab faces a large
top-side `+3.3V` pour (~257 mm² to the board edges, displacing GND in that
corner with no slivers) over the solid B.Cu ground plane. That brings θ_JA to
~65 °C/W → **T_J ≈ 75–80 °C** at 25 °C ambient. See `scripts/pcb_ldo_pour.py`.

## Single-supply design (no LDO-disconnect jumper)

The board runs from the **one** on-board LDO; there is no jumper to isolate it.
An earlier revision carried a series "LDO-disconnect" jumper (JP1) on the 3V3
output so an external supply could drive the rail without fighting the
regulator. It was **removed** — the isolation it provided is rarely needed and
is trivially achieved by desoldering the SOT-223 (≈60 s with hot air or a drag
of the iron), and removing the node split lets C2/C3 sit directly on VOUT where
the AMS1117 wants its stability cap. For bench bring-up, the natural order is to
populate the board *without* U1, current-limit-inject 3.3V to validate the
digital side, then solder U1 last — no jumper required.

**Why not just tie a second 3.3V supply to the rail?** You can't load-share two
stiff voltage sources by paralleling them — whichever sits even ~20mV higher
hogs the load, and if an external supply exceeds the LDO setpoint it back-drives
VOUT (the LDO's series pass element can only source, so its error amp drives the
pass FET off and it delivers ~0). A real second supply (battery backup,
USB-or-battery) needs an **OR-ing front end** — ideal-diode OR-ing (e.g.
LTC4412-class) or a battery power-path PMIC — not a rail tap. That is a separate
design deferred to a later revision; the single LDO is the rev-1 scope.

## Power indicators

- **Red LED on +5V** (D6, USB power present). R15 1kΩ from 5V → ~3mA,
  indicator-dim by design.
- **Yellow LED on +3.3V** (D7, regulated rail up). Yellow (not green — green
  barely lights at 3.3V). R16 470Ω → ~2.8mA.
