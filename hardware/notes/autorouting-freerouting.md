# Autorouting rework: adopt FreeRouting (negotiated congestion)

**Status (2026-06-15): proven end-to-end, integration in progress.**

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

## Open items before this fully lands

1. **USB pair → F.Cu.** FreeRouting does not honour "F.Cu only, no layer
   change" — it routed `/USB_D+` on B.Cu (21 mm), slotting the GND return (the
   exact SI regression the old `HARD_F` rule prevented) and incidentally
   blocking a GND via under R1.2. Constrain it: a **B.Cu keepout** under the
   J2→module USB corridor, or per-net layer rules via a FreeRouting `.rules`
   file (`-dr`). Verify the pair lands on F.Cu over solid B.Cu ground.
2. **GND handling.** We want pour-only GND. Routing signals then dropping all
   GND traces can strand a GND pad whose pour patch has no B-via (seen: R1.2,
   blocked by USB_D+ on B.Cu — fixes once #1 is done). Either keep FR's GND
   routing and only fix edge-clearance GND traces, or harden `pcb_pour.py`
   island tying. The robust GND F↔B stitcher used during bring-up (find GND-F/B
   fill polys with no via inside + GND on the other layer + a safe spot) should
   fold into `pcb_pour.py`.
3. **CI.** Add Java 25 + the pinned FreeRouting jar (or
   `ghcr.io/freerouting/freerouting:2.2.4` as a separate Docker step) to the
   hardware job. The CI KiCad image has no Java.
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
