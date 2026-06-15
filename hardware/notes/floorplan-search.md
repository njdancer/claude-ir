# Generative floorplan search

> Bold approach to "find a better layout" (Nick, 2026-06-15): stop hand-nudging
> anchors — **generate many candidate floorplans, route each with FreeRouting,
> score the routed result, and rank.** FreeRouting (~10 s/board, deterministic)
> is the routability *oracle*; `scripts/pcb_score.py` is the fitness function.
> This orchestrates the mature tools we already use (pcbnew place / FreeRouting
> route / kicad-cli DRC) — it does **not** reinvent routing or DRC, so it clears
> the CLAUDE.md "stand on giants / has a machine validator" bar.

## Pieces

| Script | Role |
|--------|------|
| `scripts/pcb_score.py` | Read a *routed* board, emit a quality vector + scalar (lower = better): USB-on-B.Cu length + vias, B.Cu signal slotting, total track/via, decoupling distance, sensor↔heat separation. |
| `scripts/pcb_floorplan.py` | `apply_anchors(b, anchors, holes, draw_outline)` places a candidate anchor dict (refactored out of Phase A `main()`). |
| `scripts/pcb_place_v2.py` | Phase B support re-seat (ASSIGN map) — reused per candidate. |
| `scripts/pcb_search.py` | The driver: generate → legalize → route → DRC-gate → score → rank. |

## Search space

Physics-fixed anchors are **never moved** (only treated as obstacles): the
antenna/MCU at the N long edge, USB-C at the W short edge, the IR LED fan firing
E, the TSOP on the S edge, the VBUS chain in the W power zone. The search varies
the **flexible** groups Nick flagged:

- status-LED row (D6/D7/D10/D11/D12): zone + orientation
- buttons (SW1/SW2): zone
- J4 spare header: zone (incl. "under the ESP")
- LDO group (U1): NW corner vs. NW
- sensor (U5): far-from-heat corner (SE vs. E)

plus ±0.6 mm jitter. Two named candidates always run: **baseline** (the merged
floorplan — a control that must reproduce its exact score) and **user_hyp**
(Nick's LEDs+buttons-bottom-left / J4-under-ESP / LDO-alone idea).

## Per-candidate pipeline (each stage its own process — SWIG-safe)

```
copy pristine board → _apply (place anchors + LEGALIZE flex off collisions +
outline) → pcb_place_v2 (re-seat support) → pcb_rip → FreeRouting
(export/route/import) → pcb_pour (GND) → kicad-cli DRC → pcb_score
```

Hard gates: **0 DRC errors + 0 unconnected** (illegal candidates are scored
below every legal one). The **legalizer** (`_legalize`) spiral-nudges each flex
anchor to the nearest collision-free slot near its zone target (reusing
`pcb_place_v2`'s courtyard/overlap/keepout helpers) so a chosen zone arrangement
becomes a *legal* placement before routing — without it every rearrangement
collided.

## Run

```bash
JAVA25=/tmp/fr/jdk-25*/bin/java FREEROUTING_JAR=/tmp/fr/freerouting-2.2.4.jar \
  /usr/bin/python3.12 scripts/pcb_search.py <N> <seed>
# results -> hardware/fab/search_results.json (gitignored); best -> /tmp/search_best.kicad_pcb
```

The winner is a *placement*; finalize it through the normal route ritual
(ldo_pour, silk, DRC, `hardware_validate.py`, baseline refresh in
`kicad/kicad:10.0.2`) and **render the top few for a human serviceability call**
(the scorer rewards SI/routability, not button reachability or aesthetics).

## Results (2026-06-15, N=40 + item-2 probe)

**Verdict: the merged 2-layer floorplan is already near-optimal; the board is
the constraint, not the placement.**

- Of 40 candidates only **3 were DRC-legal**; the best (`rand31`, score **687.9**
  vs baseline **709.7**, ~3 %) differs from baseline in **one** way — the **LDO
  tucked into the NW corner** (everything else identical), which trims
  USB-on-B.Cu 56→49 mm and decoupling distance. That margin is within the
  run-to-run jitter noise (the same zone combo scored 619 legal in one pilot and
  6553 illegal in another when ±0.6 mm jitter tipped a tight courtyard) — i.e.
  not a robust win, not worth churning the board + re-baselining for.
- Nick's "everything bottom-left + J4 under the ESP" hypothesis routed **worse /
  illegal** — a 5-LED row + 2 buttons + caps don't fit cleanly in the SW corner.
- **Item 2 (USB → F.Cu) does NOT yield to a keepout here (hard data).** Forcing
  the pair off B.Cu pushed USB-on-B.Cu **49→108 mm with +1 unrouted** — strictly
  worse. Root cause is geometric: U3's USB pins (IO18/IO19) sit on the module's
  **east** side (x≈158) facing *away* from the **west** USB-C (J2, x≈113), so the
  shortest path ducks **under the module on B.Cu** (F.Cu is blocked by the module
  pads; N is the antenna keepout). The B.Cu run is the natural optimum and is
  functional for full-speed USB (note: `autorouting-freerouting.md`). `pcb_usb_keepout.py`
  is kept for the record / a future 4-layer board.

**Real levers (for a future re-spin, where the search has room):**
1. **Module orientation/placement** so the C3's USB pins face J2 — the only
   placement fix for the USB pair, but it moves the antenna off the N edge
   (RF implications — needs care).
2. **4-layer board** (dedicated GND plane + coupled D+/D−) — already the
   documented next-rev lever; the search tooling will have real degrees of
   freedom there (layer assignment, module rotation).

## Notes / limits

- The scorer rewards USB-on-F.Cu but placement alone can't force it to 0 vias —
  that needs the B.Cu-keepout / per-net layer rule (brief item 2). Run that on
  the chosen winner.
- Weights in `pcb_score.WEIGHTS` are for *ranking*, not physical units — tune
  them if priorities shift.
- Determinism: FreeRouting is single-threaded sequential (no seed needed); the
  generator's RNG is seeded, so a run is reproducible.
