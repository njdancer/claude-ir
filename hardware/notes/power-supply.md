# Power Supply

USB-C power entry with overcurrent and overvoltage protection, followed by a
synchronous buck converter for 3.3V regulation.

## USB-C input

The USB-C receptacle (GCT USB4085, 14-pin USB 2.0) provides 5V power and the
USB data lines; the shield ties to ground for EMI. The CC lines each have
5.1kΩ pull-downs to advertise the board as a default-power 5V sink — without
these, a USB-C host or PD supply will not provide VBUS.

## Input protection

- **Overcurrent:** PTC resettable fuse, 1.1A hold / ~2.2A trip, protects
  against downstream shorts.
- **Overvoltage:** TVS diode clamps spikes below ~6.5V. The AP63203 tolerates
  up to ~32V input, but fast clamping protects everything else on the rail.

Reverse-polarity protection is intentionally omitted on the USB-C input —
the connector enforces orientation (per spec §Power Delivery).

## Buck converter (AP63203WU)

Fixed 3.3V output, so no feedback divider is needed — FB ties directly to the
output rail. 1.1MHz switching frequency keeps the passives small.

- **Bootstrap:** 100nF between BST and SW for high-side gate drive.
- **Inductor:** 4.7µH (datasheet typical; chosen in H1.4 over the original
  3.9µH for availability), ≥2.7A saturation current, low DCR.
- **Input cap:** 10µF ceramic for load-transient stability.
- **Output caps:** 2× 22µF ceramic in parallel for low ESR and ripple.

**Enable jumper (JP1):** the EN pin has an internal pull-up to VIN, so the
jumper open = converter enabled (normal operation). Closing JP1 to ground
disables the buck so an external 3.3V supply can be tested via the breakout
header without back-driving the regulator (battery experiments are deferred
to v2).

## Power indicators

- **Red LED on VBUS** (D6, USB power present, before the buck).
  Vf ≈ 2.0V; R15 1kΩ from 5V gives ~3mA — indicator-dim by design.
- **Green LED on 3.3V** (D7, regulated rail up, after the buck).
  Vf ≈ 2.0V; R16 470Ω gives ~2.8mA (was 150Ω/~9mA; reduced in the H1.4
  review to match the other indicators).
