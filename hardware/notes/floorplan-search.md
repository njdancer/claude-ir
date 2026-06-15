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

## Notes / limits

- The scorer rewards USB-on-F.Cu but placement alone can't force it to 0 vias —
  that needs the B.Cu-keepout / per-net layer rule (brief item 2). Run that on
  the chosen winner.
- Weights in `pcb_score.WEIGHTS` are for *ranking*, not physical units — tune
  them if priorities shift.
- Determinism: FreeRouting is single-threaded sequential (no seed needed); the
  generator's RNG is seeded, so a run is reproducible.
