# Autorouting rework: adopt FreeRouting (negotiated congestion)

**Status (2026-06-15): DONE — wired into the pipeline, board committed.**
The home-grown `pcb_router.py` + `pcb_finish.py` are retired (deleted; in git
history). The ROUTE stage is now `scripts/pcb_route_fr.py` (export DSN →
FreeRouting → import SES). The full pipeline regenerates a **DRC-clean,
CI-passing** board (0 unconnected, parity 19, all `hardware_validate.py` checks
green), and the FreeRouting run is **byte-for-bit deterministic** (verified:
two runs produce md5-identical `.ses`). Determinism flags: `-mt 1 -is
sequential -us greedy`, pinned jar 2.2.4.

## Why we're replacing the home-grown router

`scripts/pcb_router.py` is a deterministic A* maze router that places nets one
at a time in a fixed order and freezes each once placed; `scripts/pcb_finish.py`
is a separate rip-up post-pass that tries to heal whatever the router left
unrouted. On this 2-layer board that combo fails by construction:

- J4's GPIO nets straddle **both** sides of the centred ESP32-C3 module, so
  ~5 nets run long cross-board traces that saturate the module-west escape
  lanes. **One west-pin escape always loses** (it's +3.3V/U3.1, or I2C_SCL, or
  a LED net depending on route order) — tweaking the order just moves which net
  fails.
- The finisher then mangles the route healing it: dangling stubs, co-located
  duplicate vias, ripped-and-not-restored neighbours (e.g. IR_TX). Every
  "improvement" pass shifted the failure elsewhere; it never converged clean.

The fix is **negotiated-congestion routing** (PathFinder, McMurchie/Ebeling):
route everything every iteration allowing overlaps, raise the cost of contended
resources across iterations so nets *negotiate*, repeat until overlap-free.
FreeRouting implements exactly this as its core loop, headless and (v2.2.0+)
deterministically — so we adopt it rather than rebuild it (CLAUDE.md: prefer
existing tools, don't invent meta-tooling).

## Proven result

KiCad 10.0.3 (system `pcbnew`) + FreeRouting **2.2.4** (Java **25**):

- `pcbnew.ExportSpecctraDSN(board, dsn)` / `pcbnew.ImportSpecctraSES(board, ses)`
  — the **two-arg BOARD\* overloads** work headless (no PCB_EDIT_FRAME). KiCad
  `kicad-cli` has **no** specctra support; Python is the only headless path.
- `java -jar freerouting-2.2.4.jar --gui.enabled=false -de board.dsn -do board.ses -mp 100 -mt 1 -is sequential -us greedy`
  routed **all 127 nets to 0 unrouted in ~11 s** (pass1 12 → pass2 4 → pass3 0).
- After import + `pcb_pour.py` + `pcb_ldo_pour.py`: **0 unconnected, no keepout
  intrusion, no dangling/duplicate vias.** The antenna keepout round-trips in
  the DSN on both layers and is honoured. The +3.3V/U3.1 escape that the old
  router never placed clean just routes.

## Determinism

FreeRouting v2.2.0 made the maze-expansion tie-breaking fully deterministic, so
the **routing pass is reproducible** with fixed inputs (no seed flag — they
removed the nondeterminism). The optimizer is the randomized part; pin it down:
`-mt 1` (single thread — essential), `-is sequential` (no random item
selection), `-us greedy`, bounded `-mp N`. Pin the jar/Docker version.
**Not yet verified bit-for-bit** — verify by double-routing and `diff`-ing the
two `.ses`; if they differ, commit the `.ses` (or routed `.kicad_pcb`) as a
checked-in artifact and have CI re-import + DRC instead of re-routing.

## Pipeline change

Old: floorplan → place → **router → finish** → pour → ldo_pour → silk.
New: floorplan → place → **rip → export DSN → FreeRouting → import SES** →
pour → ldo_pour → silk. Pours come **after** routing (KiCad exports pours as
`(plane ...)` which would constrain the router — export the ripped,
pour-free board). Orchestrated by `scripts/pcb_route_fr.py`
(export/route/import stages). Retire `pcb_router.py` + `pcb_finish.py` (keep in
git history).

## How GND is handled (resolved)

We **keep** FreeRouting's GND routing rather than going pour-only: dropping all
GND traces strands a GND pad whose pour patch has no via to the B plane (seen:
R1.2, where `/USB_D+` on B.Cu blocks the via). Keeping FR's GND traces
guarantees 0 unconnected; the GND **pour** is added on top as the plane (so GND
is both routed and poured — redundant but robust). `pcb_route_fr.py`'s import
stage drops only the few GND traces FR routes right up to the board edge
(`copper_edge_clearance`, redundant with the pour). `pcb_pour.py` removes
unconnected GND fill islands (`ISLAND_REMOVAL_MODE_ALWAYS`) so no isolated
copper. Result: clean DRC with no manual stitching.

## Remaining refinements (optional, not blocking)

1. **USB pair → F.Cu (SI nicety).** FreeRouting does not honour "F.Cu only" and
   routed `/USB_D+` partly on B.Cu. For this board's **full-speed** native-USB
   (12 Mbps) with GND poured on both layers, B.Cu routing is functional — its
   return reference is the F.Cu pour above it. The old `HARD_F` F.Cu-only rule
   was best-practice, not a requirement. If we want it back: a **B.Cu keepout**
   under the J2→module USB corridor, or per-net layer rules via a FreeRouting
   `.rules` file (`-dr`). Note J2 (USB-C, west) and U3's USB pins (east of the
   module) are on opposite sides, so F.Cu-only forces a long detour around the
   module's south — the reason it's a 2-layer compromise either way.
2. **Pour-only GND (cosmetic).** If the redundant GND traces are unwanted, pair
   refinement #1 (USB off B.Cu near J2) with a hardened `pcb_pour.py` island
   tie so R1.2-type pads stitch, then exclude GND from FR routing.
3. **CI re-route (optional).** CI currently *validates the committed board* (it
   doesn't re-route), and the board is deterministic, so CI needs no Java. If we
   ever want CI to regenerate-and-diff the board, add Java 25 + the pinned jar
   (or `ghcr.io/freerouting/freerouting:2.2.4` as a separate step).
4. **Cosmetic:** FreeRouting warns on the `Ω` glyph in resistor values in the
   DSN (non-ASCII) — harmless.

## Env (this container)

- Java 25 JRE: `/tmp/fr/jdk-25.0.3+9-jre/bin/java` (Temurin, from Adoptium).
- FreeRouting jar: `/tmp/fr/freerouting-2.2.4.jar` (GitHub release, GPL-3.0).
- pcbnew bits: `/tmp/kv10/bin/python` (system 3.12 + numpy, has working pcbnew).
- DSN/SES artifacts land in `hardware/fab/` (gitignored).

## Sources

FreeRouting CLI args & determinism notes, KiCad specctra round-trip (pcbnew
`ExportSpecctraDSN`/`ImportSpecctraSES` BOARD\* overloads), PathFinder
(McMurchie/Ebeling 1995) — see the research captured in the session that
introduced this file.
