# PCB Layout Constraints (H2.1)

> ⚠️ Predates the **v2 ESP32-C3 redesign** (see [`ROADMAP.md`](../../ROADMAP.md)).
> The WROOM-32E antenna-keepout constraint below still applies in spirit to the
> C3 module (U3), but exact references are v1; the schematic/PCB win.

Placement and routing constraints for the v1.2 board. Written before any
placement so layout (H2.2+) is execution against a checklist, not
improvisation. Board design rules and net classes live in the KiCad project
(`.kicad_pro` net_settings + board rules) — this note records *why* and the
constraints that rules can't express.

## Stackup & fab rules (set in project, 2026-06-11)

- JLCPCB 2-layer, 1oz copper. Board minimums: clearance 0.15 mm, track
  0.15 mm, via 0.5/0.3 mm, through-hole drill 0.3 mm, copper-to-edge 0.3 mm.
  (JLCPCB's absolute floor is 0.127 mm/5 mil; we keep margin.)
- Net classes:
  - **Power** (0.6 mm track, 0.8/0.4 via): `+5V`, `+3.3V`, `GND`,
    `Net-(U1-SW)`, `Net-(F1-Pad2)` — sized for ~400 mA IR pulses + WiFi
    peaks (≥0.5 mm @1oz handles 1 A+ with trivial rise).
  - **IR_Drive** (0.5 mm): `IR_DRAIN`, `EXT_IR_A`, `Net-(D2-A..D5-A)` —
    each LED string pulses ~100 mA; the shared drain return carries all four.
  - Default 0.2 mm for signals.

## Placement constraints (hard)

1. **WROOM-32E antenna keepout (U3):** module at a board edge, antenna
   section overhanging or flush with the edge; **no copper on any layer
   under the antenna** (the section past the module's shield can), and keep
   other components ≥5 mm from the antenna zone. KiCad's footprint shows the
   keepout outline — respect it on both layers and in the GND pour.
2. **IR LEDs (D2–D5, THT, 5 mm) on the board edge**, each bent 90° at
   solder time to lie horizontal and fire outward over the edge, fanned at
   −67.5°/−22.5°/+22.5°/+67.5° from the edge normal (TSAL6200 half-intensity
   beam is ±17°, so 45° splay covers a ~170° arc — the spec's 180°
   requirement leans on wall reflections at the extremes, per
   ir-transmitter.md). Footprints sit ≥4 mm behind the edge for the bend
   radius, rotated to their fan angle, with silkscreen aim guides. Each LED
   is an independent string (own 18Ω resistor from +3.3V, all cathodes to
   `IR_DRAIN`) — they are NOT series pairs. Hand-soldered; leave finger room.
3. **AP63203 buck (U1) switching loop tight:** C1 (input cap) hard
   against VIN/GND pins; L1 adjacent to SW; C2/C3 (output) close to L1 return
   with short GND back to U1. Keep the SW node (`Net-(U1-SW)`) copper area
   minimal — it's the noisy node. No signal traces under the buck loop.
4. **USB-C (J2) + CH340C (U2) short data traces:** J2 on board edge;
   U2 close to J2; route D+/D− as a loosely coupled pair, < 30 mm, no layer
   change if possible. ESD/TVS (D1) and fuse (F1) sit between J2 and the
   rest: order on VBUS must be J2 → F1 → D1 → U1 (fuse before TVS,
   per H1.4).
5. **DHT22 (U5) away from heat:** maximum practical distance from U1 (buck)
   and U3 (WiFi heat); prefer a board corner with slots/perimeter routing
   between it and heat sources if space allows. Sensor must sample room
   air, not board air.
6. **TSOP receiver (U4) faces the user/room:** board edge, lens unobstructed;
   its RC filter (R27/C9, net `IR_RX_VS`) directly at the Vs pin.

## Placement constraints (soft / serviceability)

7. **Connection points on edges:** J3 (Qwiic JST-SH) on an edge for cable
   access; J4 (spare-GPIO 2×5) and J6 (JTAG 2×5, DNP) in reachable positions
   with pin-1 marked; J5 (ext-IR, DNP) near the IR array edge.
8. **Buttons (SW1 RESET, SW2 BOOT)** on the same edge/face, reachable when
   the board is on a bench with USB plugged in; don't put them under the
   antenna end.
9. **Status LEDs (D6–D12)** visible from one viewing angle; group serial
   TX/RX (D8/D9) together; user LEDs (D11/D12) together. THT 3 mm,
   hand-soldered.
10. **Decoupling:** C4/C5/C7 (100 nF) at their IC power pins (U2, U3);
    C10 at U3's 3V3 entry; C6 (1 µF) at CH340C V3.
11. **JP1 (buck disable)** and **R21/R26 (auto-reset 0Ω links)** accessible
    for rework; silkscreen labels required (H2.4).

## Routing notes

- 2-layer plan: **B.Cu as continuous GND pour**, F.Cu for signals + power;
  stitch vias liberally, especially around the buck and under U3's GND pad
  (U3 pad 39 thermal vias to the back pour).
- **Buck B-layer keepout** (`buck_b_keepout` rule area, no-tracks on B.Cu):
  (104.3,93.5)–(117.5,103.7), covering the switching loop (U1/L1/C1–C4/SW).
  South edge is y=103.7 (not further) because the BST bootstrap net needs a
  short B.Cu jog at y≈103.9–104.2 under D6's neighborhood — BST and JP1-B
  both must exit U1 through the same south lane and provably cross on F.Cu
  alone. When re-running `scripts/pcb_finish.py`, pass
  `BLOCK="B:104.0,93.2,117.8,103.7"` so the healer respects it.
- The IR drive loop (3V3 → R9-R12 → LED strings → Q3 → GND) pulses 400 mA
  at 38 kHz: keep the loop area small and its GND return short to the pour;
  don't share its return path under the TSOP receiver or DHT22 traces.
- USB D+/D− cross under no other signals; GND pour unbroken beneath them.
- `IR_RX_VS` filter (R27/C9) and TSOP output trace away from the buck and
  the IR drive loop (receiver is the most EMI-sensitive part on the board).
- Strapping nets (GPIO0/2/12/15, EN) are short and local: buttons + R-C
  near U3.

## v2 enclosure-driven floorplan (restructure, 2026-06-14)

The first PCB was placed by dumping all parts and nudging to clear DRC — no
functional zoning, a spider-web of long traces radiating from the MCU/power
cluster, and ~⅓ of the 80×55 mm board empty. This restructure reverses that:
**pick the enclosure → fix the outline → floorplan into functional zones →
place + route within each zone.** The zones below are 1:1 with the planned
hierarchical schematic sheets, so the schematic split *is* the floorplan.

**Enclosure:** Hammond ABS project box, **end-panel family (1591 series)** —
TBD exact part (purchase, pending Nick). The board sits on a shelf facing the
AC; IR fires horizontally out one short **end panel**, USB-C exits the
opposite end. Board outline = the chosen box's internal PCB envelope;
mounting holes = the box's molded standoff pattern. Long-thin form factor
(≈90×44 for a 1591A-class box) also physically separates the noisy
power/USB end from the EMI-sensitive IR-RX/sensor end — better EMF, shorter
returns.

**Functional zones (long-thin board, IR end = "front"):**

| Zone | Edge / region | Parts | Schematic sheet |
|------|---------------|-------|-----------------|
| IR-TX | front end panel | Q3, R9–R12, D2–D5 (5 mm, fanned ±67.5/±22.5°) | `ir-tx` |
| IR-RX | front, EMI-isolated from TX loop | U4 TSOP, R27/C9 | `ir-rx` |
| MCU core | center; C3 antenna overhangs a long edge | U3 ESP32-C3, decoupling, strapping R's, SW1/SW2, EN/boot RC | `mcu` |
| Sensor | corner away from LDO heat, over a vent slot | U5 AHT20 | `sensor` |
| Power | rear end panel | J2 USB-C, F1, D1 TVS, U1 AMS1117, C1/2/3 | `power` |
| Status/IO | top-visible row + service edge | D6–D12, J4 spare, J5 ext-IR | `io` |

VBUS order on the power end stays J2 → F1 → D1 → U1 (fuse before TVS, H1.4).
All hard constraints in the "Placement constraints" section above still
apply *within* each zone (antenna keepout, IR-LED bend room, tight LDO loop,
sensor heat isolation, TSOP RC filter at the Vs pin).

**Execution path (all behind existing machine validators):**
1. Pin exact Hammond part → set Edge.Cuts + mounting holes to its template.
2. Schematic → 6 hierarchical sheets (KiCad GUI; netlist-invariant — the
   `.net` diff MUST be empty, that is the proof it was purely structural).
3. Rewrite `scripts/pcb_place_v2.py` with explicit per-zone coordinates
   against the new outline; re-run `pcb_router.py` → `pcb_pour.py` →
   `pcb_silk.py`. Render to Nick **before routing** (H2.2 exit criterion).

## H2.2 exit criteria

- All hard constraints above satisfied; photo/3D render to Nick **before
  routing starts** (cheap to move parts now, expensive later).
