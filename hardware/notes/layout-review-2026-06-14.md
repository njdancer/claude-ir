# PCB Layout Review — v2 board (2026-06-14)

> **RESOLVED (2026-06-14, same day):** the Major findings were actioned via an
> SI re-layout (commits `68e2410` LDO pour, `19e86f3` re-route). Net result,
> DRC-validated on KiCad 10.0.3: USB pair 100 % F.Cu (off B.Cu), IR_RX 5.5→2.7 mm,
> LDO tab copper ~20→69 mm², unconnected 1→0, silk_overlap 44→0.
>
> **LDO thermal — second pass (2026-06-14):** the top-only 69 mm² pour left no
> worst-case margin (T_J ≈ 120 °C at 0.85 W), so `pcb_ldo_pour.py` now also
> lays a **B.Cu /LDO_OUT island (43.8 mm²) + 6 thermal vias** under the tab
> (≈112 mm² two-sided, FR-4 bypassed). θ_JA ≈ 110→90 °C/W ⇒ T_J ≈ 101 °C at
> 25 °C (24 °C margin), ~116 °C in a 40 °C enclosure — now **under the 125 °C
> limit at the rated load**. Still short of the 1-in² ideal (the dense west
> power zone caps the island size); relocating U1 to open board copper is the
> remaining lever if more margin is wanted. DRC 0 / unconnected 0,
> `hardware_validate.py` clean (no baseline drift). Decoupling
> (~7 mm) is a module-courtyard limit and accepted; a 4-layer board is the
> proper lever for a fully solid ground + coupled USB pair. See ROADMAP "Now".
> The findings below are the original as-reviewed snapshot.

Objective + subjective review of the restructured long-thin ESP32-C3 board
(`esp32-ir-remote.kicad_pcb`, commit at review time `f7d6d02`). Done in a
remote session **without kicad-cli**, so DRC/ERC counts could not be re-run;
every number below is parsed directly from the `.kicad_pcb` s-expressions by
`scripts/pcb_metrics.py` + `scripts/pcb_checks.py` (geometry is exact; the
DRC-class checks KiCad would run are flagged "unverified here").

Benchmarks come from a research pass over IPC-2221/2152, Espressif's ESP32-C3
hardware-design guideline, TI/ON-Semi/Richtek thermal app-notes, ADI MT-031,
and JLCPCB capabilities (sources cited inline below).

## Scorecard (measured vs. benchmark)

| Metric | Measured | Benchmark | Verdict |
|---|---|---|---|
| Board / stackup | 92 × 44 mm, 2-layer 1 oz, AR 2.09:1 | — | OK (long-thin as designed) |
| Area utilisation | parts span x109.5–192.2 / y72.2–112.5 of 106–198 / 70–114 | fill the outline | **Good** — the old "⅓ empty" problem is fixed |
| Component density | 1.4 parts/100 mm² (~9 parts/in²) | well under fab limits | Good (lots of breathing room) |
| Routing completion | all 36 multi-pad signal nets have copper; GND on pour + 50 pads + 120 vias | 0 unrouted | Looks complete (DRC-unconnected **unverified here**) |
| Track widths | 0.25 signal / 0.5 IR / 0.6 power mm | IPC-2221: 0.5 A→~0.15 mm, 1 A→~0.3 mm @1 oz/10 °C | Good, ample margin |
| B.Cu ground plane | 1 fragment, 3240 mm² = **80 %** | solid, >80 %, unbroken | Coverage good **but slotted** (below) |
| F.Cu ground pour | 31 fragments, 2526 mm² = 62 % | continuous-as-possible | Expected for a signal layer |
| GND stitching | 120 vias, median NN spacing 4.0 mm (1 sparse) | ≤ λ/20 ≈ 6 mm @2.4 GHz | **Good** |
| Antenna keepout | flush to north edge (y70.4 vs 70.0); 0 tracks/0 vias inside; pour dammed | Espressif: edge, no copper any layer, prefer corner, 15 mm all-round | Firing side good; lateral 15 mm not met (below) |
| Silk min text | 0.8 mm (5 instances) | JLCPCB min 0.8 / **recommend ≥1.0 mm** | At the floor — bump to 1.0 mm |
| Edge clearance | min real pad 1.45 mm (J2 USB mouth 0.03 mm intentional) | ≥0.3 mm copper-to-edge | OK |

## Findings by severity

### Major — worth fixing before fab

1. **LDO thermal copper is inadequate for the stated worst case.**
   U1 (AMS1117 SOT-223) tab = pad 2 `/LDO_OUT`, a 2×3.8 mm tab. The whole
   `/LDO_OUT` net carries only **~20–30 mm² of copper** (33.6 mm of 0.6 mm
   track, **no pour**). The board's own worst case is 5→3.3 V @ ~0.5 A =
   **0.85 W**. Per the AMS1117 datasheet + Richtek AN044: minimal-pad
   θ_JA ≈ 135 °C/W → T_J = 25 + 0.85×135 ≈ **140 °C — exceeds the 125 °C
   limit even at 25 °C ambient**. The "1 in² (≈1000 mm²) pour → θ_JA ≈ 55 °C/W
   → T_J ≈ 72 °C" rule is the target. The adjacent GND pour helps a little
   through the FR-4, but the tab net itself needs a deliberate pour (ideally
   top-side) + thermal vias. The ROADMAP already lists "copper thermal pour
   under the SOT-223 tab" as a requirement — **it is currently unmet.**
   *(Sources: AMS1117 DS; Richtek AN044; TI SNVA036.)*

2. **USB D+/D− is not a matched pair.** `/USB_D+` routes on **both F.Cu and
   B.Cu with 4 vias**; `/USB_D−` is all F.Cu with **0 vias**. Lengths 46.5 vs
   50.1 mm (**3.5 mm skew**), and D+ crosses the reference plane. This breaks
   the layout note's own rule ("tight pair on F.Cu, no layer change, <30 mm").
   Full-speed USB is forgiving (skew budget ~3.8 mm, so it will *work*), but
   it's the kind of asymmetry that should not survive review: route both legs
   together on F.Cu over the solid B.Cu ground, no vias.
   *(Sources: USB-IF; Silabs AN0046; TI SPRAAR7.)*

3. **B.Cu "ground plane" is slotted by ~211 mm of signal/power across 19
   nets** — including the two most return-sensitive ones (`/IR_RX` 5.5 mm,
   `/USB_D+` 5.3 mm) plus `+3.3V` (82.8 mm). On a 2-layer board B.Cu is the
   return reference; every bottom-side trace is a slot the return current must
   detour around (bigger loop area → EMI + the IR-RX/USB references getting
   chopped). The ROADMAP flagged this in "Phase C-rework" and claims partial
   reclaim, but the bottom layer is still carrying real signal traffic. Push
   signals to F.Cu (especially IR_RX and USB) and keep B.Cu as near-solid GND.
   *(Sources: ADI MT-031; Altium "never cross a plane gap".)*

### Moderate

4. **Decoupling caps sit far from their pins.** Nearest MCU bypass to U3 is
   C10 at **6.9 mm**, C8 at 8.8 mm (guideline: HF 100 nF within ~1–2 mm). LDO
   input cap C1 is **11.5 mm** from U1's VIN; the output caps C2/C3 are
   **~20 mm** away and sit on `+3.3V` (the far side of jumper JP1), so there
   is **no output cap on `/LDO_OUT` itself** — with JP1 open (its documented
   "run from external supply" mode) the AMS1117 loses its stability cap and
   can oscillate. The WROOM module's internal decoupling softens the MCU case,
   but this is the signature of the automated "nearest-free-slot" placer: caps
   land where there's room, not hugging the pin. *(Sources: Sierra/Protoexpress;
   Intel mounting-inductance; AMS1117 DS stability note.)*

5. **Antenna is mid-edge, not at a corner.** The keepout is correctly flush
   to the north long edge with no copper inside it (good), but the module sits
   in the **centre** of that edge, so there's board + GND pour + parts within a
   few mm to east, west and south — Espressif asks for the antenna at a
   corner/edge with **15 mm clearance in all directions**. The firing
   direction (north, off the board) is clean; the lateral/rear 15 mm is not
   met. For a WROOM module with an integrated antenna this is a common, mostly
   acceptable compromise, but corner placement would be measurably better.
   *(Source: Espressif ESP32-C3 PCB Layout Design.)*

### Minor / polish

6. **H1 mounting hole too close to J4.** Nearest pad is **J4.9 (1.5 mm)**;
   an M3 pan-head/washer (~3 mm radius) would foul the J4 header. H2/H3/H4 are
   fine (4.8–8.8 mm). Move H1 or shrink/relocate the header pin.
7. **Silk min text 0.8 mm** — at the JLCPCB floor; bump reference designators
   to ≥1.0 mm for legibility. (ROADMAP already tracks ~46–90 silk-overlap
   warnings — same pass.)
8. **Could not verify here:** DRC unconnected/clearance/courtyard counts, ERC,
   teardrops, acute-angle/acid-trap count, actual pour-to-keepout clearance.
   These need a kicad-cli run (open a PR; CI gates them).

## Subjective take

The restructure worked. Compared to the "dump parts and nudge for DRC" v1,
this board has real functional zoning (power/USB west, MCU+antenna north-centre,
IR fan east, status/IO south), genuine board utilisation, a solid 80 % bottom
ground with healthy 4 mm via stitching, and clean net-class track widths. As a
**first working dev/proto board it's in good shape** and would very likely come
back functional.

What's left is the gap between "routes clean / DRC-green" and
"power-integrity-clean" — and it's exactly the gap an automated placer/router
leaves: the *connectivity* is right but the *physics* placement isn't tuned.
The three things I'd not ship without a second look are the **LDO thermal
copper** (a real >125 °C risk at the rated load, and the one that can cook a
board), the **USB pair asymmetry**, and **reclaiming B.Cu as solid ground**
(get IR_RX and USB off the bottom layer). The decoupling distances and the
mid-edge antenna are second-order — fix them in the same placement pass since
you're moving caps anyway.

Net: solid bones, ready to iterate; one genuine reliability item (LDO heat)
and two SI cleanups stand between this and a confident production candidate.

## Reproduce

```bash
python3 scripts/pcb_metrics.py   # geometry, coverage, tracks, vias, silk
python3 scripts/pcb_checks.py    # decoupling, USB pair, antenna, holes, LDO
```
