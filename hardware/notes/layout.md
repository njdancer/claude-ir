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
3. **AMS1117 LDO (U1) caps tight (v2 — no buck):** the v2 board uses a
   SOT-223 AMS1117-3.3 linear LDO, NOT the v1 AP63203 buck — there is no
   inductor or SW node. Place the input cap (C1) hard against VIN/GND and the
   **10 µF output cap within ~3 mm of VOUT** (PSRR/transient for the C3 WiFi
   bursts — SI review). No switching loop / SW-keepout applies any more.
4. **USB-C (J2) native USB (v2 — no CH340C):** v2 uses the C3's native USB
   PHY (the CH340C bridge is gone). J2 on the board edge; route D+/D− as a
   tight pair on F.Cu over continuous ground, < 30 mm, no layer
   change if possible. ESD/TVS (D1) and fuse (F1) sit between J2 and the
   rest: order on VBUS must be J2 → F1 → D1 → U1 (fuse before TVS,
   per H1.4).
5. **AHT20 (U5) away from heat (v2 — was DHT22):** the v2 sensor is the
   **AHT20 I²C** part (SCL = C3 IO10, SDA = C3 IO7; bus also broken out on
   header J4), NOT the v1 AM2302/DHT22 single-wire part. Place it the maximum
   practical distance from U1 (LDO) and U3 (WiFi heat); prefer a board corner
   with slots/perimeter routing between it and heat sources if space allows.
   Sensor must sample room air, not board air. Its 100 nF decoupling and the
   I²C pull-ups (R28/R29, 4.7 kΩ, populated) travel with it — see constraint 10.
6. **TSOP receiver (U4) faces the user/room AND keeps its distance from the
   TX array (revised 2026-06-14):** board edge, lens unobstructed; its RC
   filter (R27/C9, net `IR_RX_VS`) directly at the Vs pin. **Hard separation:
   ≥20 mm from Q3 and from *every* IR LED (D2–D5).** Rationale: U4 is a
   dev/debug part used both to capture fresh reference signals from the OEM
   remote and to self-validate our own TX. The earlier east-corner placement
   put it ~11 mm from D2 and ~19 mm from Q3 — that is *near-field*: the TSOP's
   wide (~±45°) acceptance cone + enclosure reflection saturate its AGC during
   TX, so self-validation reads a clipped blob, not recoverable mark/space
   timing, and the receiver (the most EMI-sensitive part on the board) sits in
   the 400 mA / 38 kHz drive loop's near field. **As-built (2026-06-14):** U4
   moved to the **south long edge at (153.0, 110.5), rot 180 so the lens fires
   south (+y, outward)**, between the MCU and the U5 sensor; the Vs RC filter
   sits in-line to its west — C9 at (144.5, 110.5), R27 at (140.0, 110.5).
   Achieved separation: **31 mm to Q3, 34–46 mm to D2–D5**, 44 mm to USB. At
   that distance it still hears its own TX via room/enclosure bounce (good for
   "did it fire + coarse timing") without saturating. Re-routed via the
   standard pipeline (rip → router → stub_heal → pour); DRC = 0 errors (the
   lone unconnected is the pre-existing accepted USB_D+ J2/A6 item, unrelated).
   **Enclosure: add an optical baffle rib between the TX window (east) and the
   RX window (south) in the 3D print.** Tight near-field loopback timing, if
   ever wanted, is a job for an external aimed RX (breadboard-style), not the
   onboard window.

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
10. **Decoupling (v2 — U2/CH340C and C4 deleted):** the +3.3V rail carries
    **two identical bypass banks, one per IC** — *not* a duplication bug.
    There are two consumers on the rail: U3 (the C3 module) and U5 (the AHT20),
    so each gets a 100 nF + 10 µF pair (C5/C7 are the 100 nF, C8/C10 the 10 µF;
    all four sit on +3.3V↔GND, so the exact ref↔IC assignment is free — Phase B
    picks by shortest route).
    - **U3 (ESP32-C3):** 100 nF + 10 µF hard against the 3V3 pin (pin 1); the
      100 nF gets the shorter loop. The module courtyard bounds the caps to
      ~7 mm on this 2-layer board (accepted — see ROADMAP; the module also has
      internal decoupling).
    - **U5 (AHT20):** 100 nF at VDD (pin 2); the second 10 µF rides along as
      local rail bulk. (The AHT20 strictly needs only the 100 nF — the 10 µF is
      generous; keep for rail stiffness or drop to save a part.)
    - **As-built the placer scattered these** (both 10 µF landed at U3, both
      100 nF orphaned ~50 mm SW, U5 left with no local cap). **Phase B must
      re-pair one bank to each IC.**
    - **C6 (1 µF) is NOT a decoupling cap** — it is U3's EN power-on-reset RC
      (with the 10 kΩ EN pull-up, ~10 ms POR delay) at the EN pin. (The old
      "CH340C V3" note was wrong; that chip is gone.)
    - LDO caps (C1 at VIN; C2/C3 at VOUT) are covered by constraint 3.
11. **No jumpers / no auto-reset links (v2):** JP1 (LDO-disconnect), the
    R21/R26 auto-reset 0 Ω links, and the Q1/Q2 reset FETs were all **deleted**
    in v2 — the C3's native USB-Serial-JTAG handles reset/boot/download over
    USB-C, and the rail runs from the single LDO (desolder U1 to bench-inject).
    Silkscreen pin-1 / button labels still required (H2.4).

## Layer policy (signal vs power on a 2-layer GND-pour board)

The rule for what drops to B.Cu when a power trace and a signal trace must
cross on F.Cu:

- **Keep the high-frequency / sensitive signal contiguous on F.Cu; dip the
  POWER trace to B.Cu to cross — short and perpendicular.** The signal needs
  the intact GND plane directly beneath it as its return reference; a DC power
  trace does not (it carries current at ~0 Hz and only wants copper + low IR
  drop). Routing the *signal* on B.Cu instead would strip its reference (B.Cu's
  "reference" up on F.Cu is signals/power, not a plane) and add via
  discontinuities — all to a trace whose edges are the thing that cares.
- The one cost of a B.Cu power dip is that it **slots the GND pour** for its
  length, forcing return currents of any signal crossing that slot to detour.
  So keep the dip short, cross perpendicular, **flank it with GND stitching
  vias**, and never run a long power trace on B.Cu. Priority order: (1) signal
  on F.Cu over solid GND, (2) power on F.Cu if it can, (3) when they must
  cross, power takes the short B.Cu dip — never the signal.
- On *this* board the stakes are modest (38 kHz IR carrier; fastest edges are
  the C3's digital/flash/crystal, not controlled-impedance nets), but the
  discipline is free and pays off for WiFi-adjacent and IR_RX nets.

**Autorouter rulesets — what's standard vs not (researched 2026-06-15):**

- **Per-layer "preferred direction" (H-on-top/V-on-bottom) does NOT apply
  here.** It's a multi-*signal*-layer convention to reduce crossings when both
  layers route; with B.Cu as a near-solid GND pour it would just force more
  vias and break the reference. KiCad doesn't even export a `(direction …)`
  token to the DSN; FreeRouting's `preferred_direction_horizontal` is a soft
  cost set via CLI/`.rules`, not the board. Skip it. To reduce layer changes,
  raise FreeRouting's `via_costs` (CLI/JSON) instead.
- **Set width/clearance/via-size/membership in KiCad net classes** — these *do*
  export into the Specctra DSN (`(class …)` with per-class `(rule (width…)
  (clearance…))` + `(via …)`), so FreeRouting consumes them. Prefer this over
  hand-coding per-net geometry in our pcb_*.py. (Gap: KiCad always writes the
  *default* netclass clearance for copper-to-hole in the DSN — verify hole
  clearance with DRC after import.)
- **Keep USB on F.Cu** the only way FreeRouting honours it: a B.Cu keepout
  corridor under the J2→module USB lane, or a saved FreeRouting `.rules` file
  fed with `-dr` (KiCad can't express "this net F.Cu-only" in the DSN). USB-FS
  needs no length/skew matching (skew budget ≫ our lengths).
- **Net classes are already the rule home** (Default/IR_Drive/Power in
  `.kicad_pro`, JLC-appropriate via 0.3/0.6), and FreeRouting + DRC honour
  them — nothing to migrate out of Python here. The JLC floors (edge clearance,
  via/track/hole minima, silk) are already enforced by `design_settings`, so a
  wholesale community `.kicad_dru` (labtroll) would be redundant. We added a
  *focused* `hardware/esp32-ir-remote.kicad_dru` instead: an **IR_Drive
  min-track-width (0.45 mm)** rule that locks the 400 mA drive nets.
- ⚠️ **Finding:** the FreeRouting `+3.3V` (Power-class) routing has 0.2 mm
  segments (only IR_Drive is uniformly at class width). Not dangerous at our
  currents but under the Power nominal 0.6 mm — widen on the next re-route, then
  add a Power min-width DRU. (This is why the bridge across the old JP1 gap is
  0.4 mm: 0.6 mm clears the GND pour by <0.3 mm there, and the rail is the weak
  link anyway, not the bridge.)

## Routing notes

> ⚠️ Several bullets below predate the v2 LDO redesign + FreeRouting and are
> stale (AP63203 buck, L1, `buck_b_keepout`, `JP1-B`, `pcb_finish.py`, DHT22).
> They are kept for historical context; the active routing model is the layer
> policy above + `hardware/notes/autorouting-freerouting.md`.

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
- `IR_RX_VS` filter (R27/C9) and TSOP output trace away from the LDO and
  the IR drive loop (receiver is the most EMI-sensitive part on the board).
  With U4 relocated to the south edge (constraint 6), the IR_RX_OUT trace
  back to U3 must NOT run under or alongside the IR drive loop / Q3.
- Strapping nets (GPIO0/2/12/15, EN) are short and local: buttons + R-C
  near U3.

## v2 enclosure-driven floorplan (restructure, 2026-06-14)

The first PCB was placed by dumping all parts and nudging to clear DRC — no
functional zoning, a spider-web of long traces radiating from the MCU/power
cluster, and ~⅓ of the 80×55 mm board empty. This restructure reverses that:
**pick the enclosure → fix the outline → floorplan into functional zones →
place + route within each zone.** The zones below are 1:1 with the planned
hierarchical schematic sheets, so the schematic split *is* the floorplan.

**Enclosure (decided 2026-06-14, Nick):** assume a **custom 3D-printed
enclosure tailored to the board** — so the board is NOT constrained to a
stock box. Shape the outline to suit the component layout (the zones below),
and place **4× M3 mounting holes wherever the floorplan makes them
convenient** (≥2.5 mm from edges/copour, clear of courtyards); the printed
enclosure adapts to wherever they land. Free outline removes the prior
purchase/size gate entirely. Still target a tidy, compact shape — long-thin
remains attractive because it separates the noisy power/USB end from the
EMI-sensitive IR-RX/sensor end (better EMF, shorter returns) — but it is now
a design choice, not a box constraint.

**Underside metadata block (B.SilkS, new requirement):** the board carries no
branding today (front has only the title + URL; `pcb_silk.py` phase-1 strips
all board texts). Add a back-silk block in a free region of the GND pour:
- **Claude starburst icon** + **"Designed by Claude"** (orange on the
  website; mono silk here). Icon must be authored as a B.SilkS logo footprint
  (`bitmap2component` from a mono starburst) — it does not exist in the
  hardware tree yet.
- **Board rev** (`v2`), **git short-hash + dirty flag** of the generating
  commit (auto-stamped by the silk step via `git rev-parse --short HEAD`, so
  it never goes stale — it trails its own commit by one, which is
  conventional and fine), **generation date**, project URL, and the
  non-commercial/"directed by Nick Dancer" line to match the site.
Implement inside `pcb_silk.py` (extend `LABELS` with a B.SilkS group +
a stamping helper) so it regenerates with every pipeline run.

**Functional zones (long-thin board, IR end = "front"):**

| Zone | Edge / region | Parts | Schematic sheet |
|------|---------------|-------|-----------------|
| IR-TX | front end panel | Q3, R9–R12, D2–D5 (5 mm, fanned ±67.5/±22.5°) | `ir-tx` |
| IR-RX | **south long edge: U4@(153,110.5) lens south; C9@(144.5), R27@(140)**, ≥31 mm from Q3/D2–D5 | U4 TSOP, R27/C9 | `ir-rx` |
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
