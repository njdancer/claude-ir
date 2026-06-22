# Temperature / Humidity Sensor

> **v2 (as-built): AHT20** (U5), an **I²C** temperature + humidity sensor,
> swapped in during the v2 redesign. It replaced the v1 AM2302/DHT22 single-wire
> part. Where this note disagrees with the schematic, the schematic wins.

The AHT20 provides temperature (±0.3 °C, inside the spec's ±1 °C requirement)
and relative humidity for the "Follow Me" feature, where the AC adjusts output
based on the temperature at the remote's location.

## Interface

- **I²C bus** (not single-wire): SCL on C3 **IO10** (U3 pin 10), SDA on C3
  **IO7** (U3 pin 6). The bus is also broken out on the spare header **J4**
  (SCL = pin 4, SDA = pin 3) for external I²C devices.
- **VDD** on +3.3V (pin 2), **GND** on pin 5; pins 1 and 6 are NC.
- **Decoupling:** 100 nF at VDD, placed with the sensor (see `layout.md`
  constraint 10 — U5 gets one 100 nF + 10 µF bank).

## I²C pull-ups

The bus pull-ups are **R28/R29 (4.7 kΩ to +3.3V, LCSC C17936)** on SDA/SCL, and
they **are populated** (verified: schematic `dnp` clear / `in_bom yes`, PCB
footprint attr `smd`). A bare AHT20 has no internal pull-ups, so the on-board
sensor needs these; 4.7 kΩ is the standard value for a short 3.3 V bus. (The
old `esp32-mcu.md` line that called these "DNP for Qwiic" was a v1 leftover —
there is no Qwiic connector in v2; the bus serves the on-board AHT20 plus the
J4 breakout.)

## Placement

Keep the sensor the maximum practical distance from U1 (LDO) and U3 (WiFi
self-heating) so it samples room air, not board air — see `layout.md`
constraint 5.

## Thermal isolation — TI SNOA967A (adopt before fab)

Fabio flagged TI app note **SNOA967A, "Temperature sensors: PCB guidelines for
surface mount devices"** (Jul 2017, rev Jan 2019). It is directly on point: an
SMT sensor tends to read **PCB temperature, not air**, because heat conducts to
its die mainly through copper (k≈385) and FR4 (k≈0.25) — air (k≈0.028) is the
insulator. Our use case is its headline example ("thermostat / wireless sensor
node ambient air measurement"), so its **Section 2 (air-temperature)** guidance
applies; **Section 3 (component-temperature) is the *opposite* goal and a
cautionary mirror** of our current accidental layout.

**Gap it exposes.** `pcb_pour.py` floods solid GND on *both* layers up to U5 and
deliberately ties every island into one plane. That makes a continuous copper
thermal highway from U1 (LDO, ~0.83 W) and U3 (WiFi) straight to the sensor —
exactly what §2.1 says to avoid, and exactly what §3.1.2 *recommends when you
want* an IC's temperature. Today our distance-only mitigation (constraint 5) is
partly defeated by the shared pour. Note: the LDO's 257 mm² NW thermal pour is
good for the LDO and **not in conflict** with this — once U5 is islanded, that
heat stays in the NW corner instead of riding the plane to the sensor.

**Recommendations, ranked by value/effort for our 2-layer JLC board:**

1. **Isolate U5's ground (§2.1) — top priority, low cost, do this.** Don't let
   the main GND plane reach the sensor. Give U5 a *local* GND pour island (both
   layers, via-stitched together) tied to the main plane only through a single
   **thin neck** (or only via stitching), with a **copper-free moat** around it.
   Hatch the main pour where it approaches the sensor. This is a `pcb_pour.py`
   change (a sensor keepout/island like the existing `antenna_keepout`), not a
   schematic change → netlist-invariant.
2. **Isolation slot or perforation (§2.3 / §2.4) — high value, ~small JLC fee.**
   A milled slot (or row of drills) around U5 leaving a thin FR4 neck cuts the
   FR4 conduction path (air gap >> FR4). The zone table already *intends* "over a
   vent slot" — formalize it as real `Edge.Cuts`/perforation geometry. JLC min
   internal slot ≈1.0 mm. Our enclosure is custom-printed, so add a matching vent
   window over the sensor so isolated copper actually sees room air.
3. **Solder-mask cut-out over U5's local copper (§2.1).** Mask (k≈0.245) insulates;
   exposing the local plane lets it equilibrate with air faster. Cheap silk/mask
   layer edit.
4. **Corner partitioning (§2.2) — already done.** U5 is in the far corner; keep it
   the farthest point from U1 and U3 through any floorplan change.
5. **Thin board / low thermal mass (§2.6) — note only, don't act.** 0.8–1.0 mm
   FR4 responds faster than 1.6 mm, but that's a global mechanical/cost change;
   not worth it for a remote that reads slow room drift.

**Not for us:** the daughter-card edge-connector (§2.5) and flex-PCB (§2.6 fig 19)
sensor carriers are over-engineered here — we want the AHT20 on-board, SMD-placed.
Package response-rate (§1.2) is moot: AHT20 is already chosen (a DFN-class part,
low thermal mass); the §2 *layout* techniques are package-agnostic and apply
regardless. Bonus: isolation also improves the AHT20's **RH** reading (board heat
depresses local relative humidity).

**Status:** captured as a queued layout requirement (see `ROADMAP.md`). Deferred
behind the pending U3-rotation floorplan decision so it's folded into the next
pour/route pass rather than done twice — the U5 corner is stable across that
decision, but its pour topology will be regenerated.
