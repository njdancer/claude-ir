# Roadmap

**Goal:** a fabricated, verified ESP32 IR remote board running reliable
firmware that controls the ActronAir AC, eventually exposed to HomeKit.

This is the project's state file. Update it in every commit that completes,
adds, or reorders work. Conventions: `[ ]` todo, `[x]` done, `[~]` in
progress. Each phase lists its **gate** (what must be true to move on) and
**needs** (Mac = KiCad/serial required; Nick = human action required).

## Now

🔬 **AUTORESEARCH LOOP for layout/routing — BUILT + RUNNING; Layout-B power
corner is the blocker (2026-06-16, Nick: "run the Layout-B search, but first
replicate Karpathy's autoresearch for iteratively improving the board; we can
totally remap GPIO — I don't care what pins").** Replicated Karpathy's ratchet
loop (immutable evaluator + editable artifact + history log + keep-if-better) on
the board — design + 1:1 mapping in
[`hardware/notes/autoresearch.md`](hardware/notes/autoresearch.md). New tooling:
- **`scripts/pcb_experiment.py`** — the immutable evaluator (the "prepare.py"):
  one candidate → apply ANCHORS floorplan + legalize flex/holes + optional GPIO
  remap → `pcb_place_v2` → rip → FreeRouting → pour → DRC → `pcb_score`; logs a
  line to `hardware/fab/experiments.jsonl`, ratchets the best board aside.
- **`scripts/pcb_gpio_remap.py`** — the new lever Nick unlocked: reassign nets
  among U3's permutable pads (6 free + 4 spare; USB/strap/power locked) so each
  signal exits the side facing its zone. The placement re-seat is net-driven so
  remap + re-place is self-consistent. Reflection into the sources of truth
  (firmware build_flags + schematic + netlist) is queued for a winning remap.
- **Bug fixed (benefits all placement):** `pcb_place_v2.keepout_box` read only
  U3's footprint antenna keepout, missing the **board-level** rule area that
  extends past the module — it stranded the U3 decoupling caps just below the
  footprint keepout (passed the placer, failed DRC `items_not_allowed`). Now
  unions all rule areas.
- **Finding (Layout B, ~12 experiments): USB + every peripheral net route
  cleanly; the POWER chain is the blocker.** Root cause is the WROOM-02 pinout —
  **its 3V3/EN/GND pins cluster at the *antenna end* of the module**, so with the
  antenna on the W board edge (rot90) the 3V3 pad (pad1) is double-cornered by
  the board edge + the antenna keepout: its decoupling caps have no legal home
  and the +5V/+3.3V/VBUS chain won't close (14 unrouted, all in the N power/USB
  zone — zero peripheral nets). **GPIO remap can't fix this** (power pins are
  hardware-fixed). This is the *same class* of failure as Layout A's cram strip:
  both edge-mount orientations that win USB break power on 2 layers.
- **✅ RESULT — Layout B ROUTES 0 DRC / 0 unrouted on 2 layers.** The
  autoresearch loop closed it. The "power doesn't route" conclusion was a
  **stale-keepout bug** (`pcb_pour` rebuilt the antenna keepout N/S-only; antenna-W
  fell through and extended it across the power chain) — fixed (edge-agnostic).
  Then the loop drove placement to a clean solution:
  - **U1 (LDO) → open NE** for a **433 mm² +3.3V tab thermal pour** (Nick's
    "big fat thermal pour" ask); F1/D1 spread along the N edge so nothing crams.
    `pcb_ldo_pour` is now U1-tracking (was hardcoded NW) + scored.
  - **J2 USB-C → rot180** so the **mouth faces N off the board edge** (rot90/270
    faced sideways — unusable; Nick caught it). rot180 is also shallower (4.7 mm)
    so pads sit on-board with the mouth overhanging.
  - **U5 (AHT20) → far from the LDO** (~38 mm to U1; sensor accuracy).
  - **GPIO remap proven** (USER_LED2 off the far-W pad) — gets USB to 2 vias vs
    4, but **not required**: the board routes 0/0 without it, so the committed
    board stays schematic-parity-valid (no GPIO reflection needed yet).
  - USB pair lands on **B.Cu (2–4 vias, ~9 mm)** — functional for full-speed
    (same as the shipping merged board); F.Cu is marginal/flips with placement.
    Forcing it (B.Cu keepout) is the remaining optional SI optimisation.
  - Config lives in `pcb_floorplan.ANCHORS` (Layout B west-end). Reproduce:
    `pcb_experiment.py` pipeline. **`hardware/notes/autoresearch.md`** has the
    loop; `experiments.jsonl` (gitignored) the run log.
- **USB→F.Cu via B.Cu keepout — TRIED, backfires (2026-06-16).** A B.Cu
  track/via keepout over the J2→U3 lane pushed the pair to route *around* it
  (B.Cu 9→20 mm, 4 vias) instead of onto F.Cu — same geometric backfire as the
  merged board. B.Cu (2–4 vias) is the natural optimum here and is fine for
  full-speed; accepted. (F.Cu *did* land 0-via in one earlier placement, so it's
  placement-marginal, not forced-able cheaply.)
- **➡️ NEXT:** (a) ~~optional USB→F.Cu~~ (backfires, accepted B.Cu);
  (b) re-verify the USB-C **3D model seating** at rot180 (FAB/pads are correct;
  the `(model …)` offset was tuned for the old rotation); (c) CI baseline refresh
  for the new layout (silk/DRC counts drift) in `kicad/kicad:10.0.2`; (d) Nick
  sign-off + finalise. Fallback unchanged: merged board on `main` routes 0/0.

🧭 **U3-ROTATION TO FIX USB — TWO LAYOUTS TRIED, NEITHER ROUTES ON 2 LAYERS
(2026-06-16, Nick: rotate the module so its USB pins face J2; stay 2-layer, no
4-layer).** This revisits item (2) below (USB-on-B.Cu). Confirmed the USB win is
real but it does NOT come for free on 2 layers. **Decision pending — Nick to
pick the next move (see end).**

- **U3 rotation → pin-side map (measured from the footprint pads, reusable):**
  | rot | antenna | USB pins | IR pins |
  |-----|---------|----------|---------|
  | 0 (current) | N | E | W |
  | 90  | **W** | **N** | S |
  | 180 | S | W | E |
  | 270 | E | S | N |
- **Layout A — "180-flip" (U3 rot180 on the S edge, antenna S).** USB superb
  (0–7 mm B.Cu, often 0 vias) but a generative search (`pcb_search.py`, 12+
  candidates) **never closed**: every one left **11–15 unrouted** + 3–5 DRC. Root
  cause: U3 on the edge crams ALL routing into a thin N strip and re-sides every
  non-USB/IR pin to a worse side. Dead end on 2L. (Also fixed a real bug along
  the way: F1/D1 were jammed 5 mm apart — a FIXED anchor poisoning every
  candidate; spread to 8 mm + moved J5 off the IR fan. Commit 86b92a6.)
- **Layout B — "west-end" (U3 rot90 at the W end, antenna overhangs W edge).**
  Nick's better idea: USB pins face N (USB-C on N edge beside them), IR pins S,
  IR fan stays E, **the whole centre is open** for distributed peripherals (no
  cram strip). Antenna-W **confirmed** (bbox extends to x104, pad-free). USB
  good (11 mm, 2 vias) but the **first hand-placement still left 16 unrouted**.
  Committed as the floorplan def (`pcb_floorplan.py` ANCHORS, commit 06baf56);
  **board left at MERGED (rot0, 0/0).** NOT yet searched — the open centre may
  let a *search* close it where A's strip couldn't; that's the untested question.
- **Baseline that still works:** the MERGED board (U3 rot0, git HEAD
  `hardware/esp32-ir-remote.kicad_pcb`) routes **0 DRC / 0 unrouted** with USB on
  B.Cu (56 mm) — fine for full-speed USB. This is the safe fallback.
- **State of the tools for a fresh agent:**
  - `pcb_floorplan.py` ANCHORS = **Layout B (west-end)**. Running it APPLIES B to
    the board; `git checkout hardware/*.kicad_pcb` restores the 0/0 merged board.
  - `pcb_search.py` FIXED is currently the **Layout-A (rot180)** frame + N-band/
    column zones + U4 as a flex part. To search Layout B, retarget FIXED to the
    west-end frame (U3 126,92,90 · J2 130,73,270 · Q3+fan E · J5 193,76) and move
    the flex zones into the open centre (x135–180).
  - Pipeline per candidate: `pcb_floorplan` → `pcb_place_v2` → `pcb_rip` →
    `pcb_route_fr {export,route,import}` → `pcb_pour` → DRC → `pcb_score`.
  - ⚠️ **Container restarted** — KiCad + FreeRouting in `/tmp` are GONE. Reinstall
    KiCad (CLAUDE.md recipe) and FreeRouting (JDK25 + freerouting-2.2.4.jar,
    `JAVA25=` + `FREEROUTING_JAR=` env) before routing. `/tmp/board_merged.*` is
    also gone — the merged 0/0 board IS git HEAD.
- **➡️ DECISION PENDING (Nick):** (a) **run the Layout-B west-end search** (fair
  test of the open-centre idea, ~15 min); (b) **accept the current 0/0 board**
  (USB-on-B.Cu is fine for full-speed); (c) **firmware pin-reassignment** — leave
  U3 at rot0 but remap GPIO *functions* so each signal exits the side facing its
  zone (eases routing without rotation; touches firmware + schematic). Nick
  leaned toward handing this to a FRESH agent — this entry is the handoff.

🧪 **GENERATIVE FLOORPLAN SEARCH built + run (2026-06-15, Nick: "generate a
bunch of layouts, autoroute them, score, find the optimum").** New reusable
tooling (`scripts/pcb_score.py` + `pcb_search.py`, refactored `pcb_floorplan.py`,
note `hardware/notes/floorplan-search.md`): sample floorplans over the flexible
groups → legalize → FreeRouting (the routability oracle) → DRC-gate → score →
rank. Orchestrates mature tools; clears the "machine validator" bar.
- **Finding: the merged 2-layer floorplan is already near-optimal.** N=40 → only
  3 DRC-legal; best (LDO-in-NW-corner) ~3 % over baseline, **within jitter
  noise** — not worth churning the board. Nick's "everything bottom-left" idea
  routed worse/illegal (SW corner can't hold a 5-LED row + 2 buttons + caps).
- **USB/SI is board-limited, not placement-limited** — see item (2): the USB
  pair on B.Cu is geometric (module USB pins face away from J2). **The real
  lever is a 4-layer re-spin**, where the search gains real DOF (layer
  assignment, module rotation). Tooling is ready for that.
- Board left UNCHANGED (merged state); no marginal-noise churn. The LDO-corner
  tweak is available on request if Nick wants the ~3 %.

🔧 **PHASE B DONE — decoupling re-seat + full re-route (2026-06-15, Nick: "do
the full restructure now").** The MOD "decoupling far from pins" finding is
fixed. Root cause: `pcb_place_v2.py`'s net heuristic can't distribute a *shared*
rail — a +3.3V bypass cap pad sees the whole net, so it could only seat at the
nearest rail pin, which piled every MCU/sensor bypass onto the LDO and left
**U5 (AHT20) with no local cap** (both 10 µF stacked on U3, both 100 nF orphaned
~50 mm SW). Fix = an explicit `ASSIGN` map in `pcb_place_v2.py` pinning each
bypass/EN/RC/pull-up to the specific (anchor, pad) it serves, so every IC gets
its own bank:
- **U3 (C3):** C7 100 nF + C8 10 µF on 3V3 (~7–8 mm, module-courtyard bound —
  the accepted limit); C6 1 µF EN-POR RC on EN. (Before: U3 had *two* 10 µF and
  *no* local 100 nF.)
- **U5 (AHT20):** C5 100 nF + C10 10 µF on VDD + I²C pull-ups R28/R29 — all
  ~2–4 mm. **U5 went from bare to a full local bank.**
- **U1 (LDO):** C1 in-cap on VIN, C2/C3 out-caps on VOUT.
- **Re-route:** rip → FreeRouting (0 unrouted, pass #4) → GND + LDO pour → silk.
  **DRC 0 errors / 0 unconnected / 0 parity.** `hardware_validate.py` EXIT 0
  (netlist unchanged — schematic untouched — 43 polarity invariants, parity 0).
- **Item 1 (Power width + DRU) folded in:** the new route holds the 0.6 mm
  Power class (min 0.50 mm at a few pad necks; the old 0.2 mm +3.3V segments are
  gone), so the deferred **Power min-width DRU (0.5 mm)** is now added to
  `esp32-ir-remote.kicad_dru`.
- **Cosmetic:** +1 `silk_over_copper` in the now-denser SE sensor corner (a ref
  over a track; placer dodges pads/courtyards not copper) — accepted tradeoff
  for U5's local decoupling. Baseline refresh owed (below).
- ⚠️ **CI baseline refresh owed** — DRC/silk counts drifted (full re-route);
  refresh `ci-baseline.json` in `kicad/kicad:10.0.2` (done this session — see
  commit). Done locally on KiCad 10.0.3 + FreeRouting 2.2.4.

🔭 **Deferred follow-ups from the JP1/tooling brief (2026-06-15):**
- ✅ **(1) Power width + DRU** — done above.
- ⛔ **(2) Force USB D+/D− onto F.Cu — INVESTIGATED, not viable on the current
  2-layer placement (2026-06-15).** Tried the B.Cu-keepout under the J2→U3 lane
  (`scripts/pcb_usb_keepout.py`): it **backfires** — USB-on-B.Cu went 49→108 mm
  with +1 unrouted. Root cause is geometric, not tooling: U3's USB pins
  (IO18/IO19) are on the module's **east** side (x≈158) facing *away* from the
  **west** USB-C (J2, x≈113), so the shortest path ducks **under the module on
  B.Cu** (F.Cu blocked by module pads, N blocked by the antenna keepout). The
  B.Cu run is the natural optimum and is fine for full-speed USB. Real fix =
  re-orient the module so its USB pins face J2 (moves the antenna off the N
  edge — RF care) **or a 4-layer board**. Folded into the re-spin levers below.
- [ ] **(3) Cut CPL/BOM over from `fab-outputs.py` to KiBot.** Already
  de-risked: `esp32-ir-remote-fab.kibot.yaml` + `scripts/ci/cpl_crosscheck.py`
  (gating) prove KiBot ≡ fab-outputs.py (43/43, 0 delta). Point the order
  package at KiBot's position+bom+gerber/zip; slim `fab-outputs.py` to its
  special core (hand-solder-kit narrative, refuse-on-unclassified, orientation
  report); keep cpl_crosscheck green. HARD GATE: cross-check proves the tools
  *agree*, not that absolute angle is right — JLC-preview-verify Q3 (SOT-23,
  we use 270) + J2 (USB-C, +1.44 mm X) on the first assembled order. Plan in
  `validation-tooling.md` → "Plan once unblocked" step 2. Unrelated to layout.

🧮 **CAP AUDIT + v2 doc reconciliation (2026-06-15, Nick asked).** Audited all
nine caps (C1–C3, C5–C10; no C4 — deleted with U2/CH340C in v2). Verdict on the
"are C7/C8 and C5/C10 duplicated?" question: **no copy-paste bug.** Within a
pair the two values do different jobs (100 nF HF + 10 µF bulk); the two *banks*
are identical only because the +3.3V rail has **two consumers** — U3 (C3
module) and U5 (AHT20) — so it's one bank per IC. Full map: C1 = LDO VIN
(10 µF); C2/C3 = LDO VOUT (22 µF ×2); C5+C10 / C7+C8 = the two 100 nF+10 µF
banks; C6 = U3 EN power-on-reset RC (1 µF, NOT decoupling); C9 = TSOP Vs filter.
- **Real defect found (not the duplication):** the placer scattered the banks —
  both 10 µF at U3, both 100 nF orphaned ~50 mm SW, **U5 left with no local
  decoupling.** This is already the queued "MOD — decoupling far from pins" item
  and belongs to **restructure Phase B** (re-seat decoupling against new
  anchors); doing a piecemeal re-route now would be overwritten by Phase B, so
  **not** done here. Captured the correct one-bank-per-IC intent in
  `layout.md` constraint 10 so Phase B places it right.
- **I²C pull-ups — checked, already populated:** an earlier pass mis-read
  R28/R29 (4.7 kΩ on SDA/SCL) as DNP (a buggy grep that slurped past the comp
  block). Verified properly: schematic `dnp` clear + `in_bom yes`, PCB attr
  `smd` → they ARE fitted. Corrected `temp-sensor.md` / `layout.md` and the
  stale "DNP for Qwiic" line in `esp32-mcu.md` (no Qwiic/J3 in v2). No design
  change needed.
- **Docs reconciled v1→v2:** `layout.md` constraints 5 (DHT22→AHT20 I²C),
  10 (decoupling rewrite — no C4/U2, C6 is EN-RC not CH340C), 11 (JP1 + R21/R26
  + Q1/Q2 all deleted); `temp-sensor.md` fully rewritten (AHT20/I²C). Pulled
  `origin/main` (JP1-removal merge) into the branch first.
- **KiCad-in-session:** pulled `kicad/kicad:10.0.2` via Docker
  (`registry-1.docker.io/...`, Docker Hub anon pull was rate-limited) — kicad-cli
  10.0.2 confirmed working for headless ERC/DRC/validate if needed.

⚡ **POWER SIMPLIFIED — JP1 LDO-disconnect jumper REMOVED, single supply
(2026-06-15, Nick's call).** The series jumper on the 3V3 output was deleted:
the rail now runs from the one AMS1117 LDO, and to bench-inject or prototype a
battery you desolder the SOT-223 (≈60 s) — far cheaper than carrying a jumper +
its problems (the open-jumper state left the LDO output with no stability cap).
A real second supply would need an OR-ing front end (ideal-diode / power-path
PMIC), not a rail tap — deferred to a later rev. Done end-to-end in-container on
KiCad 10.0.3 (installed this session — see below):
- **Schematic:** JP1 symbol + its label/wire stubs removed; `/LDO_OUT` net
  collapsed into `+3.3V` (U1 VO drives the rail directly); the now-redundant
  `+3.3V` PWR_FLAG removed (it only existed because the open jumper left the
  rail undriven — with the regulator on the net it caused a power-output↔
  power-output ERC conflict). ERC clean (only container lib-table noise).
- **PCB:** JP1 footprint removed; the 5 `/LDO_OUT` copper objects re-netted to
  `+3.3V`; **2 stitching vias added at the old JP1 pad sites** (the THT
  TestPoint pads had been silently bridging F.Cu↔B.Cu — removing them stranded
  the B.Cu segments) + a short F.Cu bridge across the old jumper gap. Re-poured
  GND + LDO thermal pour. **DRC 0 violations / 0 unconnected.**
- **`pcb_ldo_pour.py`** now pours the tab on `+3.3V` (257 mm², bonded to the
  tab as rail copper — a better heat path than the old isolated island).
- **Validators updated + green:** `golden_netlist_v2.py` (LDO_OUT row dropped,
  35 nets), `hardware_validate.py` polarity (`U1.2 = +3.3V`) + LCSC allowlist
  (JP1 gone); `ci-baseline.json` `drc_parity` 21→19. `hardware_validate.py`
  EXIT 0 (0 unconnected, parity 19, 43 polarity invariants, netlist≡schematic).
  Baseline `drc_parity` edited by hand (NOT `--update-baseline`, which would
  clobber the CI-correct lib counts with this container's lib-table noise).
- Docs: `power-supply.md` fully rewritten v1→v2 (was still describing the
  AP63203 buck + old buck-EN jumper); `layout.md` gained a **layer policy**
  section (signal-on-F.Cu / power-takes-short-B.Cu-dips + autorouter-ruleset
  findings); `CLAUDE.md` Environments updated (see below).
- ⚠️ **CI baseline note:** counts validated locally on 10.0.3; CI runs 10.0.2.
  Parity/unconnected/polarity are version-proof, but if a silk/lib count drifts
  by 1–2 on the first CI run, refresh from the `kicad/kicad:10.0.2` container.

🔧 **CLAUDE.md fix: KiCad IS installable in remote sessions (2026-06-15).** The
old guidance ("Don't attempt KiCad operations; queue for a Mac session") was
wrong — install works fine. Recorded the recipe (the `add-apt-repository` needs
`/usr/bin/python3.12` because the active `python3` is 3.11 vs apt_pkg-3.12;
`pcbnew` binds to python3.12). Only serial/USB + heavy GUI schematic re-layout
stay Mac-bound.

✅ **TOOLING IMPROVEMENTS DONE (2026-06-15, Nick picked all 4 threads).**
Four-agent research → four shipped increments (each its own commit):
- ✅ **Rotation-DB cite fix (safe):** `matthewlai/JLCKicadTools` is deprecated;
  re-cited `bennymeg/Fabrication-Toolkit` (live, KiBot's `bennymeg_mode`
  tracks it) in `fab-outputs.py` + `validation-tooling.md`; corrected the false
  "KiBot has a built-in rotation DB" premise (it doesn't). Flagged the genuine
  SOT-23 disagreement (−90 vs 180) — JLC-preview every SOT-23 + USB-C.
- ✅ **KiBot quick wins:** `check_zone_fills` preflight (stale-pour guard) +
  narrow DRC `filters` (board-only mounting-hole/logo + USB-C silk-edge) +
  **KiDiff** PR visual diff (PCB+sch, base→head PDF artifact, non-gating).
- ✅ **Net-class/DRU:** net classes already live in `.kicad_pro` (nothing to
  migrate) + design_settings already enforce JLC floors; added a *focused*
  `esp32-ir-remote.kicad_dru` (IR_Drive min-width 0.45 mm). Per-layer
  preferred-direction confirmed the WRONG tool for a 2-layer GND-pour board.
  Finding: `+3.3V` routing has 0.2 mm segments → Power min-width DRU deferred
  to the next re-route; USB-on-F.Cu `.rules`/keepout is the real open lever.
- ✅ **CPL/BOM → KiBot (gated):** `esp32-ir-remote-fab.kibot.yaml` (KiBot
  `position`+`rot_footprint`+`bom`, our values) + `scripts/ci/cpl_crosscheck.py`
  (gating) prove KiBot ≡ fab-outputs.py — **43/43 placements, 0 delta**,
  negative test fails as intended. Cutover de-risked; fab-outputs.py stays the
  producer pending the first-order JLC-preview sign-off.
- Kept genuinely-special bespoke (pressure-tested): polarity truth table,
  netlist partition-freshness/golden, page-extents guard, hand-solder kit
  narrative + refuse-on-unclassified guard.

🚀 **AUTOROUTER REPLACED + LDO THERMAL DONE (2026-06-15).** Two big wins:

- **FreeRouting replaces the home-grown router.** The hand-rolled greedy A*
  `pcb_router.py` + rip-up `pcb_finish.py` never converged on the congested
  module-west escape (one net always frozen out, finisher mangled the route).
  Both are **retired**; the ROUTE stage is now `scripts/pcb_route_fr.py`
  (KiCad DSN → FreeRouting 2.2.4 negotiated-congestion → SES). Routes all 127
  nets to **0 unrouted in ~7 s**, **byte-for-bit deterministic** (`-mt 1 -is
  sequential -us greedy`, pinned jar), board passes the full
  `hardware_validate.py` gate (0 unconnected, parity 19). Rationale + the
  optional refinements (USB→F.Cu nicety; pour-only GND) in
  [`hardware/notes/autorouting-freerouting.md`](hardware/notes/autorouting-freerouting.md).
  Pipeline is now: floorplan → place → rip → **route_fr** → pour → ldo_pour →
  silk. Env: Java 25 + jar at `/tmp/fr/`, pcbnew via `/tmp/kv10/bin/python`.
- **LDO thermal solved.** U1 relocated to the open NW corner, **rot90 so the
  SOT-223 tab faces north into a 257 mm² to-the-edge pour** that *displaces*
  GND in the corner (no slivers). T_J ≈ 75 °C at the 0.85 W worst case
  (was ~140 °C bare). `pcb_ldo_pour.py` + `pcb_floorplan.py` anchors.

✅ **KiBot adopted (2026-06-15).** Same "shoulders of giants" lens applied to
validation/fab. Done: **KiBot owns the ERC/DRC error gate** in CI +
**InteractiveHtmlBom** generated into the fab package; the v2 schematic
instance-path bug that blocked KiBot's parser is fixed (netlist regenerated,
parity baseline 19→21). **Version-drift killed** —
`hardware_validate.py` warning-count baseline changes are now informational
(KiCad patch-release lib/silk heuristics no longer fail CI); it keeps the
bespoke checks + parity/unconnected. `.kicad_dru` skipped (the project's
`design_settings` + `antenna_keepout` already enforce geometry natively).
**`fab-outputs.py` deliberately kept** (project-specific assembly split + safety
guard; KiBot's rotation DB is hardware-gated) — rationale in
[`hardware/notes/validation-tooling.md`](hardware/notes/validation-tooling.md).
- ⚠️ If we ever migrate fab to KiBot: its rotation DB disagrees with ours
  (SOT-23 270 vs 180; USB-C offset axis) — diff the CPL + validate against JLC's
  placement preview first, or Q3/USB-C could place wrong (dead board).

✅ **SI RE-LAYOUT DONE (2026-06-14, Nick: "full re-layout pass").** [SUPERSEDED
by the FreeRouting re-route above — the `HARD_F`/`STRONG_F` router rules it
describes no longer exist.] Re-ran the
deterministic pipeline (`rip → place → router → pour → pcb_ldo_pour → silk →
stamp`) with the hand-tuned **anchors fixed** (IR fan + U4 south-edge
relocation synced into `pcb_floorplan.py`, so all that work is preserved) and
the router taught real SI rules. Validated locally on KiCad 10.0.3 (installed
in this container; global lib-tables wired so `hardware_validate.py` counts are
trustworthy). **Every metric improved or held — nothing regressed:**
- **USB D+/D− pair fully off B.Cu** (was D+ 5.3 mm on B.Cu + 4 vias): both now
  100 % F.Cu, 0 vias, no plane crossing — `pcb_router.HARD_F` forbids B.Cu for
  the pair. (D+ 62 mm vs D− 50 mm = 12.7 mm skew is electrically irrelevant at
  full-speed USB, ~76 ps vs an 83 ns bit period — return-path continuity >
  length-match here.)
- **IR_RX 5.5 → 2.7 mm** single short B.Cu crossing; **IR_RX_VS 0 mm** —
  `STRONG_F` penalty + routing the SI-critical nets first.
- **LDO thermal stack** (`pcb_ldo_pour.py`): two-sided now — F.Cu tab pour
  68.5 mm² **+ B.Cu /LDO_OUT island 43.8 mm² + 6 thermal vias** (0.3/0.6 mm)
  tying the tab through the FR-4 to the bottom island (≈112 mm² total, was bare
  ~20). Bottom island kept tight to the tab — the west power zone is the
  least-bad place to slot B.Cu (far from IR_RX/USB returns). θ_JA est.
  ~110 → ~90 °C/W ⇒ T_J at the 0.85 W worst case ~120 → ~101 °C (24 °C margin
  at 25 °C ambient; ~116 °C in a 40 °C enclosure). Clears 125 °C at the rated
  load — short of the 1-in² ideal but the dense power zone caps further gain;
  relocating U1 to open copper is the remaining lever. **Validated locally on
  real KiCad 10.0.3 in-container: `kicad-cli pcb drc` 0 violations / 0
  unconnected; `hardware_validate.py` all checks pass (no baseline drift).**
- **0 unconnected** (was 1: the USB-C A6↔B6 reversibility tie now routes →
  reversible USB works); **silk_overlap 44 → 0, silk_over_copper 53 → 0**;
  DRC 0 errors. Baseline refreshed (`ci-baseline.json`).
- **Decoupling left ~7 mm** — bounded by the WROOM module courtyard (caps
  can't sit <3 mm from a module edge; module has internal decoupling), so this
  is an accepted module-design reality, not placer-fixable without collision
  risk.
- ⚠️ Baseline generated on **10.0.3**; CI uses **10.0.2** — counts should match
  but watch the first CI run and refresh from the container if a silk count
  differs by 1–2. Open a PR and let CI gate (ERC/DRC/parity/freshness/silk).
- Note: true USB diff-pair coupling + a fully solid 2-layer ground are
  physically limited on 2 layers; a **4-layer board** (dedicated GND plane,
  coupled D+/D−) is the proper next-rev lever if SI ever matters more.

🔧 **Earlier this session:** LDO thermal pour first landed standalone
(`68e2410`); now folded into the pipeline above.

🔍 **LAYOUT REVIEW DONE (2026-06-14) — see
[`hardware/notes/layout-review-2026-06-14.md`](hardware/notes/layout-review-2026-06-14.md).**
Objective parse (`scripts/pcb_metrics.py` + `scripts/pcb_checks.py`, no
kicad-cli needed) + research-backed benchmarks. Restructure verdict: **solid
bones** — real zoning, good utilisation, 80 % B.Cu ground, 4 mm via stitching,
clean net-class widths, all 36 multi-pad nets routed. Action items before fab,
by severity:
- [ ] **MAJOR — LDO thermal copper (reliability).** U1 tab `/LDO_OUT` has only
      ~20–30 mm² copper, no pour → at the rated 0.85 W, θ_JA≈135 °C/W →
      T_J≈140 °C **>125 °C limit even at 25 °C ambient**. Needs a ~1 in²
      (≥1000 mm²) top-side pour on the tab net + thermal vias (target θ_JA
      ≈55 °C/W → T_J≈72 °C). The ROADMAP's own "thermal pour under SOT-223 tab"
      requirement is currently **unmet**.
- [ ] **MAJOR — USB D+/D− not a matched pair.** D+ runs F.Cu+B.Cu with 4 vias;
      D− all F.Cu, 0 vias; 3.5 mm skew, D+ crosses the plane. Re-route both
      legs together on F.Cu over solid B.Cu, no vias (FS-tolerant but should
      not pass review).
- [ ] **MAJOR — reclaim B.Cu as solid ground.** Still slotted by ~211 mm of
      signal/power across 19 nets incl. `/IR_RX` + `/USB_D+`. Push signals
      (esp. IR_RX, USB) to F.Cu.
- [x] **MOD — decoupling far from pins (2026-06-15).** Fixed via the Phase B
      ASSIGN re-seat (see "Now"); LDO out-caps now on VOUT (JP1 removed), each
      IC has a local HF+bulk bank. U3 ~7–8 mm is the accepted courtyard limit.
- [ ] **MOD — antenna mid-edge not corner** (firing side clean, lateral 15 mm
      not met). **MINOR — H1 hole 1.5 mm from J4; silk min 0.8 mm → 1.0 mm.**
- [ ] **Verify on CI** (no kicad-cli here): DRC unconnected/clearance/courtyard,
      ERC, teardrops, acute angles — open a PR and let the hardware job gate.

🏗️ **BOARD RESTRUCTURE — enclosure-driven re-floorplan + schematic split
(NEW TOP PRIORITY, 2026-06-14, Nick's call).** The current board is
structurally sound but was placed by dumping parts and nudging for DRC: no
functional zoning, spider-web traces radiating from the MCU/power cluster,
~⅓ of the 80×55 mm board empty, and a single flat A3 schematic sheet.
Restructure approach (full rationale + zone table in
[`hardware/notes/layout.md`](hardware/notes/layout.md) "v2 enclosure-driven
floorplan"):

- **Enclosure decided (Nick, 2026-06-14):** **custom 3D-printed, tailored to
  the board** — no stock box, no purchase gate. Free outline: shape it to the
  component layout; place 4× M3 holes wherever the floorplan makes convenient
  (the print adapts). Long-thin still preferred for EMF separation.
**Sequencing reality:** the PCB floorplan is fully scriptable (pcbnew via the
`/tmp/kv10` env, confirmed present) so it goes FIRST and is where the visible
win is. The **schematic hierarchical split is GUI-bound** — there's no
schematic-edit MCP and s-expr scripting is banned (it caused the off-sheet
render bug), so it's a separate focused KiCad-GUI effort, done after the PCB
is settled. Execute in phases, commit+push each:

- ⚠️ **Hardcoded old bounds (100,60,180,115) in `pcb_router.py`,
  `pcb_pour.py`, `pcb_place_v2.py`, `pcb_silk.py`** must be updated to the new
  outline (106,70,198,114) before Phase C, or the east IR zone (x180–198) is
  off-grid. Spark is **1 gr_poly (600 pts)**, not 8 — logo footprint already
  extracted to `hardware/libraries/Branding.pretty/Claude_Spark_Logo.kicad_mod`.
- [~] **Phase A — outline + anchor placement.** New long-thin Edge.Cuts;
      place zone anchors (U3 center w/ antenna over a long edge; U1+J2+F1+D1
      power/USB one short end; Q3+D2–D5 IR-TX other short end; U4 IR-RX near
      front but EMI-isolated; U5 sensor far corner; D6–D12+J4+J5 status/IO
      edge) + 4× M3 holes wherever clean. Render, iterate.
- [x] **Phase B — support re-seat + holes (2026-06-15).** `pcb_place_v2.py`
      gained an explicit ASSIGN map (shared rails can't be net-targeted); each
      IC now gets its own bank, U5 no longer bare. Re-routed, DRC 0/0/0.
- [ ] **Phase C — route + pour + silk.** `pcb_router.py → pcb_pour.py →
      pcb_silk.py`. **Render to Nick before routing commits** (H2.2 rule).
**STATUS 2026-06-14 (end of autonomous PCB session):** the restructure is
substantively DONE and pushed. Board: long-thin 92×44, zoned (power/USB W,
MCU+antenna N-centre, IR fan E, status cluster + buttons S), USB mouth
overhanging the W edge, 4 M3 holes clear, **0 DRC errors** (kicad-cli). All
review blockers addressed: bent-LED model + east-firing fan (geometry
verified: D2..D5 fire +67.5/+22.5/−22.5/−67.5° around east), TSOP off the LED
column, ground plane reclaimed (B-signal 40%→24%, critical nets F-pinned),
status LEDs clustered + captioned, underside metadata block (logo + stamped
rev/commit/date/URL). **Remaining (blocked or polish):**
- [x] **Relocated IR-RX off the TX corner (2026-06-14, done w/ Nick).** U4
      (TSOP) was at (175,73), ~11 mm from D2 and ~19 mm from Q3 — near-field,
      so it saturated during self-TX (clipped, not clean loopback timing) and
      the most EMI-sensitive part sat in the 400 mA/38 kHz drive loop. **Moved
      U4 → south long edge (153.0, 110.5), rot 180 (lens fires south/outward);
      Vs filter in-line west: C9 (144.5, 110.5), R27 (140.0, 110.5).**
      Separation now **31 mm to Q3, 34–46 mm to D2–D5** (rationale: `layout.md`
      constraint 6 + `notes/ir-receiver.md`). Done in a fresh KiCad 10.0.3
      install in this remote container (apt + kicad-10 PPA), full pipeline
      re-run (rip → `pcb_router` → `pcb_stub_heal` → `pcb_pour`); **DRC = 0
      errors**, 1 unconnected = the pre-existing accepted USB_D+ J2/A6 item
      (unrelated to U4). Schematic untouched → netlist unchanged. **Still owed:
      enclosure optical baffle rib between TX (east) and RX (south) windows;
      CI baseline refresh (below) since the full re-route + silk drifted
      counts — must run in `kicad/kicad:10.0.2` (this env lacks the global libs
      → inflates lib_footprint_issues, so don't refresh the baseline here).**
- [ ] **CI baseline refresh** — every count drifted (full restructure); must
      run `hardware_validate.py --update-baseline` inside `kicad/kicad:10.0.2`
      (can't locally). Open a PR and let CI be the gate (per CLAUDE.md).
- [x] **Silk polish DONE (2026-06-14).** Nick: "the silkscreen's a bit shit."
      Root cause of the front mess: the BOM workflow left each footprint's
      **LCSC part-number field visible on F.SilkS** at full 1.27mm — 25 part
      codes (C2934560, C6186, …) piled on the designators → illegible. Fixes
      in `pcb_silk.py`: (a) hide *every* footprint field except Reference (not
      just Value) — kills the LCSC codes; (b) 0.2mm separation margin in the
      ref placer so adjacent refs can't pack edge-to-edge (was colliding
      R20/R29); (c) `STATUS` caption moved below the D6–D12 LED row (was
      overlapping R19); (d) back-silk Claude logo re-seated as a header above
      the attribution block (was stranded 34mm east over the IR array).
      **Result (kicad-cli DRC): silk_overlap 44→0, silk_over_copper 53→0**;
      remaining 2 silk_edge_clearance are J2 (USB-C) silk vs the board edge —
      inherent to the edge-overhang connector, cosmetic. Diff is silk-only
      (25 `hide yes` + a few text moves); **zero copper/pad/net/zone lines
      touched → electrically identical, netlist/parity unaffected.** Front
      now fully legible; back logo grouped with its caption.
- [x] **Silk follow-up (2026-06-14, Nick's review of the above).** Two asks:
      - **Per-LED captions** — the single "STATUS" word was useless. Replaced
        with abbreviated function captions under each status LED, anchored to
        the footprint (`STATUS_FN` in `pcb_silk.py`, tracks re-layout):
        D6=`5V`, D7=`3V3`, D10=`TX`, D11=`USR1`, D12=`USR2` (mapping verified
        against the netlist: D6/D7 = +5V/+3V3 rails, D10 = IR_TX/GPIO5,
        D11/D12 = USER_LED1/2 on GPIO3/4). `status-leds.md` rewritten v1→v2
        (was still documenting the deleted serial + blue-MOSFET LEDs). DRC
        still 0 silk_overlap / 0 silk_over_copper.
      - **Merged main (PR #22, IR-RX relocation) into this branch:** the new
        U4 (IR receiver) at (153,110.5) sits directly below the LED-caption
        row, so the silk was regenerated against main's board (took main's
        electrical state verbatim — diff vs main is silk-only, 0 electrical
        lines — and re-ran `pcb_silk.py`). Caught in review: D10's `IR` caption
        would read as if it labelled the adjacent receiver, so **D10 → `TX`**
        (transmit activity; the serial-TX LED that could've clashed is gone).
      - **Git "-dirty" stamp on published assets** — root cause: `pcb_silk.py`
        bakes the silk git line on a dirty tree, so the committed board (which
        CI renders) always reads "-dirty" + the *parent* hash. Fix:
        `scripts/stamp_silk.py` re-stamps that one line (text-only, idempotent,
        non-fatal) from the CURRENT commit; wired into the CI hardware job
        (after validation, before render + fab) and `build-site.sh` (Pages,
        CI-guarded so local previews don't dirty the tree). CI checkout is
        clean at the build SHA → published renders/GLB/gerbers show the exact
        commit, no "-dirty". Committed file's own stamp is now a placeholder
        CI overwrites at publish (resolves the bake-then-commit fixed point).
- [ ] **Phase E schematic split** — GUI-bound, still pending.
- [ ] check_models() flags the bent .wrl "missing" though it exists — likely a
      ${KIPRJMOD} path-resolution quirk in the validator; verify on Pages.

- [x] **Phase C-rework — from 3 adversarial subagent reviews (2026-06-14).**
  Round-1 board routes clean (0 DRC) but review found real blockers:
  - **IR-LED bend geometry (mech, BLOCKER + Nick):** flat `LED_D5.0mm` has an
    ambiguous bend plane; rotating it doesn't reliably aim the beam. Fix: bent
    3D model + silk bend-line/arrow defining the fold, footprint rotated so the
    fold fires at the fan angle. Widen pitch 8→~11mm (bend/finger room). Move
    TSOP U4 off the LED column (self-blinding / TX reflection).
  - **Ground-plane fragmentation (SI, BLOCKER):** B.Cu is used as a signal
    layer, slotting the GND plane; IR_DRAIN return + long IR_RX run past the
    receiver. Fix: router penalty to keep signals on F.Cu and reclaim B.Cu as
    near-solid GND; keep IR drive loop tight on F.Cu; stitch antenna+RX corners.
    (Antenna keepout itself verified CLEAN — the mech reviewer's "antenna
    off-edge" was a false positive from misreading the board as y60-top.)
  - **Silk mess (DFM, MAJOR):** 169 silk warnings (RDs over pads/edge,
    illegible status row). Fix: re-run/extend `pcb_silk.py` for the new board.
  - **Status LEDs (Nick + DFM):** cluster them (not spread) + clear labels.
  - Minor: J2 ~0.5mm east (pad-to-edge slack), H1/H2 screw-head vs J4/U4,
    AMS1117 out-cap closer, stale buck note in layout.md → fix to LDO.
- [ ] **Phase C2 — underside metadata (B.SilkS).** The Claude spark already
      exists as **8× top-level `gr_poly` on F.SilkS** (bbox ≈126.8–131.0 ×
      98.9–103.1, added in `d37cee9`); the matching "designed by Claude"
      `gr_text` was stripped by `pcb_silk.py` phase-1 (explains lost-text /
      kept-icon). Plan: extract those 8 polys into a **B.SilkS logo
      footprint** (reuse geometry — identical mark), **delete the stray
      F.SilkS polys**, and have `pcb_silk.py` place the footprint + a stamped
      text block (rev `v2` + `git rev-parse --short HEAD`[-dirty] + date +
      URL + attribution). See layout.md "Underside metadata block".
- [ ] **Phase D — validate.** `hardware_validate.py`, open PR, watch CI
      (ERC/DRC/parity/freshness), refresh baseline only if counts legit-change.
- [ ] **Phase E — schematic → 6 hierarchical sheets** (GUI; gate: empty
      `.net` diff). Last, since it's GUI-bound and PCB-independent.
- Note: v1 order package (`order/v2.0` tagging) is paused behind this — no
  point freezing an outline we're about to change.

🐞 **SCHEMATIC RENDER BUG FOUND & FIXED (2026-06-14, Nick caught it).** The
published schematic PDF was missing the three v2-swapped ICs — **U3 (ESP32-C3),
U1 (AMS1117 LDO), U5 (AHT20)**. Root cause: the v2 IC-swap scripts dropped the
new symbols at a constant **off-sheet column (x≈330mm, past the A4 297mm edge)**,
so `kicad-cli sch export pdf/svg` cropped them out. They were still wired by net
labels → netlist correct (U3 = 20 nodes), ERC clean, so nothing flagged it
(**ERC has no "symbol off the page" rule** — gap in our gate). Fixes this commit:
- **Schematic:** page A4 → **A3** so the off-sheet cluster (max x≈377) falls
  inside the page and renders. Pure paper-size change → netlist-invariant by
  construction (paper size isn't in the `.net`); CI freshness check will confirm.
- **3D models:** vendored the missing STEP files into `hardware/lib/3dshapes/`
  and repointed every `(model …)` from `${KICAD10_3DMODEL_DIR}` (didn't resolve
  in the Pages render / local lint) to `${KIPRJMOD}`: ESP32-C3-WROOM-02, SOT-223,
  LED_0805 (×5), R_0805 (R6/R7 → existing bundled copy), and USB-C (C393939
  TYPE-C16PIN, fetched via JLC MCP). **`check_models()` now 0 missing.**
- ⚠️ **Could not render-verify here (remote session, no kicad-cli).** Needs a
  PR (CI ERC/DRC/parity/freshness) and/or Pages rebuild to confirm the PDF shows
  all parts and the GLB renders them.

**Queued (Mac/KiCad):**
- [ ] **Proper schematic re-layout** — A3 is a stopgap; relocate U3/U1/U5 + their
      support cluster into a clean position on the canvas (or go hierarchical),
      then revert to A4 if it fits. Do this in the KiCad GUI, not by scripting
      s-expressions (that's what caused this).
- [x] **Verify USB-C 3D model alignment — DONE 2026-06-14.** It did need a tweak:
      `offset (0 −1.087 −0.085), rotate (0 0 180)` (was `0 0 0`) seats the C393939
      **SMD terminal plane** on the board top with the THT legs going down into the
      holes, centered, mouth overhanging the south edge. GLB-mesh + multi-angle
      render verified (see the seated-model note in the Now section above).
- [ ] Add an off-sheet-symbol guard to `hardware_validate.py` so this can't
      recur silently (assert every placed symbol's origin is within page extents).

✅ **BOARD v2 — ESP32-C3 cost-down redesign COMPLETE & CI-GREEN
(2026-06-14).** Schematic + PCB + validation all done on PR #11; every CI job
passes (app, **hardware**, bom-report, firmware). State:
- **Schematic:** ESP32-C3 + AMS1117 LDO + AHT20 + SMD USB-C (XKB U262), all
  the deletes/swaps done. `golden_netlist_v2.py` GOLDEN OK (36/36), ERC
  0err/1warn.
- **PCB:** fully routed (grid A* router, no freerouting), **0 unconnected**,
  GND poured both layers with per-pad solid connection + stitched/island-tied
  vias. DRC = only the 3 baseline-accepted (H1-in-C3-antenna-keepout). Silk
  auto-placed (overlap 44→35). Reproducible pipeline:
  `rip → pcb_place_v2 → pcb_router → pcb_pour` (+ `pcb_silk`, `pcb_swap_usbc`).
- **Validation:** POLARITY truth table rebuilt for v2 (43 invariants/16 parts,
  verified live); `fab-outputs.py` HAND_SOLDER kit (4×IR LED + TSOP + headers)
  + JLC_ROTATION/OFFSET (incl. USB-C +1.44mm datum) refreshed; `ci-baseline.json`
  regenerated in kicad:10.0.2 (`hardware_validate.py` EXIT 0 in-container).
- **Next (Nick's bench / $$):** order-time JLC-preview verification of the
  flagged rotations (U3 ESP32-C3 MCU especially, U5 AHT20, J2 USB-C datum),
  then freeze the order package by tagging the commit (e.g. `order/v2.0`) and
  place the 5-board JLCPCB assembly order. (3D STEP models now vendored — see
  the render-bug fix at the top of this section.)

✅ **J2 USB-C 3D model SEATED & render-verified (2026-06-14).** Completes the
"Verify USB-C 3D model alignment" TODO below. The vendored
`USB_C_XKB_U262-16XN-4BVC11.step` (C393939 SHOU HAN, fetched via JLC MCP) was
repointed `${KIPRJMOD}`-relative but left at `offset (0 0 0)`. Took three passes,
each catching a different trap:
1. **X/Y** — measured the connector's four mounting-foot centroids and solved
   against the footprint's THT post-holes → `offset_y −1.087` (with `rotate
   (0 0 180)`, which flips local Y): feet 108.880/113.087 vs holes 108.895/113.075
   (±0.015 mm), centered x=135.0, mouth overhanging the south edge.
2. **Z datum** — the GLB height frame places the **board-top surface at height
   1.510 mm**, not 0 (board spans 0→1.510). The first Z guesses seated against 0
   and sank the part through the board.
3. **Z feature (Nick caught it)** — even seated at board-top I'd put the **leg
   tips** on the surface, leaving the SMD terminals floating 0.85 mm in the air.
   The correct seating datum is the **SMD terminal plane** (the solder tabs over
   the pad row, at model height 2.360), not the leg tips. Dropped 0.85 mm so the
   terminal plane rests on the board top (1.510) and the four THT legs go **down
   into the holes** (tips at 0.660, ~0.85 mm into the board).

Final: **`offset (0 −1.087 −0.085), rotate (0 0 180)`**. Verified by side-profile
(terminals on the surface, body resting on the board — not bisected, not
floating), bottom, and low-angle iso renders. **Lessons:** (a) never judge 3D
seating from a top render — profile/section it; (b) get the board-top height
datum from the board mesh, don't assume 0; (c) seat on the part's **terminal /
solder plane**, not its lowest geometry (legs/pegs sit below it). Diff is the
`(model …)` offset only — copper/pads/nets/DRC and pad-driven fab CPL/gerbers all
unchanged.

---

### v2 change set + cost rationale (reference, as-built)

🟢 **BOARD v2 — ESP32-C3 cost-down redesign (2026-06-13, Nick:
"build it as cheaply as possible, any redesign OK").** The v1.4 BOM is
**$16.2/board**, 65% of it just two parts: AM2302 ($6.83) + WROOM-32E
($3.78). v2 attacks the architecture, not just parts. Target **~$7.3/board
(−55%)** with nearly everything SMD-assembled and a hand-solder kit shrunk
to only easy through-hole bits (4× IR LED, TSOP, pin headers).

**The change set (Nick approved scope + 3 design calls — keep buck, SMD 0805
LEDs, Qwiic + small 4-pin spare header):**
1. **MCU: ESP32-WROOM-32E → ESP32-C3-WROOM-02-N4** (C2934560, $3.11). The C3
   has a **native USB-Serial-JTAG controller**: USB serial + auto-download/
   reset over the USB lines, no bridge chip.
2. **DELETE the whole USB-serial subsystem:** U2 CH340C, Q1/Q2 auto-reset
   FETs, R3/R4 (cross-couple), R21/R26 (DTR/RTS bypass links), C5 (CH340
   decoupling). Flash/monitor run straight over USB-C.
3. **Temp sensor: AM2302 → AHT20** (C2757850, $0.80, I2C, SMD). Kills the
   single most expensive part AND the 335-unit stock crisis; more accurate
   (±0.3 °C, factory-cal). Onboard, SMD-assembled. Drops single-wire pullup
   R22; **un-DNPs the I2C pullups R28/R29** (now real, shared AHT20+Qwiic
   bus). [[board-v1-macro-direction]]
4. **USB-C: THT GCT receptacle → SMD 16P** (C393939, $0.065 vs $1.42).
   Revisited 2026-06-13: at the 5-board minimum the THT part premium
   ($1.42×5 = $7.10) exceeds the one-time SMD feeder ($0.065×5 + $3 = $3.33)
   — SMD is ~$3.77 cheaper *and* no hand-soldering. Break-even ≈2.2 boards,
   below the floor. The 16P SMD has through-hole mounting posts, so it's
   mechanically sturdy despite SMD signal pads. Vendor C393939's EasyEDA
   footprint (verify pads vs JLC part) when wiring the schematic.
5. **Status LEDs: 3mm THT → 0805 SMD** (D6/D7/D10/D11/D12), factory-placed.
   **Drop the amber TX/RX activity LEDs (D8/D9 + R17/R18)** — meaningless
   once the console is native USB.
6. **Delete the JTAG header (J6)** — C3 does JTAG over native USB.
7. **IR LED resistors 18Ω → 22Ω Basic** (R9-R12, C17958): ~86 mA/LED vs
   ~108 mA (negligible IR-range loss), and it dodges a feeder fee (no Basic
   18Ω exists, but 22Ω is Basic). Still machine-placed, no hand-soldering.
8. **Power: AP63203 buck → AMS1117-3.3 LDO** (C6186, Basic — no feeder).
   Removes the buck + L1 inductor + bootstrap cap (kit loses the inductor).
   LDO verified for the load (pt3 below). **User LEDs: yellow 0805** (low-Vf),
   direct-driven from GPIO → **delete Q4/Q5 + R23/R24**; system LEDs (5V/3V3
   power, IR-TX) red 0805. **Keep:** IR TX array (Q3/AO3400A + 4× TSAL6200),
   TSOP38238 RX, USB-C protection (F1 + D1 + R1/R2 CC).

**Refinements (2026-06-13 pt 2, Nick's BOM audit):**
- **Drop J3 Qwiic** — a 1mm-pitch SMD that's miserable to hand-solder and
  would otherwise need a 5th feeder. I2C expansion preserved by breaking
  SDA/SCL out on the spare header. R28/R29 (4.7k I2C pullups) stay fitted
  for the AHT20 bus.
- **Spare header J4 → 2×5** carrying **5V, 3V3, 2×GND, SDA(7), SCL(10),
  GPIO0, GPIO1**: covers I2C expansion (post-Qwiic), 2 spare ADC GPIO, and
  **external power injection** — a future battery+boost module can feed 5V
  here (the AP63203 buck can't run off a 1-cell LiPo directly: dropout needs
  Vin ≳ 3.8V — which is exactly why we dropped it, see below). **JP1
  repurposed as an LDO-disconnect series jumper on the 3V3 output**: open it
  to isolate the LDO and run the rail from an external buck/boost/battery
  prototype fed through the header.
- **Power: buck → AMS1117-3.3 LDO** (Nick, 2026-06-13): the buck can't run off
  a 1S LiPo anyway, and on USB power the LDO's ~0.8W of heat is fine. Basic
  part (no feeder), drops the inductor + bootstrap cap, simpler layout.
- **LDO load check (Nick: "make sure it can manage our load"):** 3V3 rail
  worst case = C3 WiFi-TX peak ~345mA + IR array (4×86mA=344mA, but 38kHz-
  pulsed ~⅓ duty → ~115mA avg, bulk-cap filtered) + misc ~30mA ≈ **~490mA
  sustained** (~720mA transient). AMS1117 (1A): ~2× current margin; dropout
  ~0.8V@0.5A vs ~1.4V headroom (USB 4.7V min post-fuse − 3.3V) → regulates
  even through the WiFi peak at low USB volts. Dissipation (5−3.3)×0.49 ≈
  **0.83W** → SOT-223 + copper pour (θ_JA ~40°C/W) → ΔT ~35°C, Tj <85°C ≪
  125°C. **Layout requirement: copper thermal pour under the SOT-223 tab.**
  Output cap ≥22µF for stability (have C2).
- **All status LEDs → Basic 0805** (blue dropped — not in JLC Basic in any
  package). User-LED color TBD from the Basic palette (red/yellow/green/
  white); a low-Vf pick (red/yellow) also lets us **delete Q4/Q5 + R23/R24**
  and direct-drive from GPIO (the FETs only existed for blue's 3.4V Vf).
  3V3 power LED → yellow (green barely lights on 3.3V).

**Assembly split → 3 feeder fees** (~$9/order, one-time not per-board):
only C3 + AHT20 + SMD USB-C stay machine-placed as Extended; the buck→LDO
and 18→22Ω swaps each dropped a feeder (AMS1117 + 22Ω are Basic). At the
5-board minimum, paying to load the SMD USB-C beats the THT part premium
(see item 4). Hand-solder kit: **4× IR LED, TSOP, pin headers** — all easy
through-hole (the inductor's gone with the buck). Everything else is Basic +
machine-placed. Per-board parts ≈ $6.85 (−58% vs v1.4's $16.2).

**New C3 GPIO map** (functional pins avoid all strapping pins; spare/unused
strapping GPIO2/8 left NC to keep boot deterministic):

| GPIO | Function | Notes |
|------|----------|-------|
| EN | Reset (SW1) | RC: R5 pullup + C6 |
| 9 | Boot (SW2) | strapping, internal + R6 pullup |
| 5 | IR transmit | → R13 → Q3 gate; → R19 → D10 indicator |
| 6 | IR receive | TSOP38238 out |
| 7 | I2C SDA | AHT20 + Qwiic (R28 pullup) |
| 10 | I2C SCL | AHT20 + Qwiic (R29 pullup) |
| 3 | User LED1 | → Q4 gate (blue, low-side from 5V) |
| 4 | User LED2 | → Q5 gate |
| 18/19 | USB D−/D+ | native USB-Serial-JTAG |
| 0,1,20,21 | spare → J4 | 0/1 = ADC1; 20/21 = UART0 (ROM log/debug) |

**Execution (staged commits on this branch; CI is the gate):**
- [x] **Firmware** ported: new `[env:esp32-c3]` (native USB CDC build flags,
      new pins), banner de-hardcoded, CI builds esp32-c3 not esp32dev.
      `pio run -e esp32-c3` → SUCCESS (host). Retired the WROOM-32E esp32dev
      env. F1.3 native tests + nodemcuv2 unchanged.
- [x] **AHT20 vendored** (C2757850) into `hardware/libraries/` via jlcpcb
      MCP; symbol lib registered, 3D model path made `${KIPRJMOD}`-relative
      (CI render-safe per the vendoring lesson). Pinout: 2=VDD 3=SCL 4=SDA
      5=GND (1/6 NC).
- [x] **Bench upgraded to KiCad 10** (Nick; CI already on 10.0.2). v10's
      netlist exporter uses the expanded multi-line s-expr (+`libparts`);
      fixed `fab-outputs.py`'s brittle single-line parser to reuse
      `hardware_validate.py`'s tokenizer (was silently parsing 0 comps →
      empty BOM/CPL), added a lib-table self-heal to `hardware-check.sh`,
      regenerated the committed netlist under v10 (verified electrically
      empty). Full local validation passes on 10.0.3 = CI. **First CI run on
      this branch: green.** PR <https://github.com/njdancer/claude-ir/pull/11>.
- [x] **Schematic redesign DONE + machine-verified (autonomous, 2026-06-14).**
      All 20 deletes + 3 IC swaps (U1→AMS1117, U3→ESP32-C3, U5→AHT20) + full
      rewire via `connect_to_net`. **`scripts/ci/golden_netlist_v2.py` → GOLDEN
      OK: all 36 multi-pin nets match the intended v2 design exactly** (C3
      pinout, LDO + JP1 disconnect, AHT20 I2C bus, native USB D±, IO2/IO8
      strap pull-ups, direct-GPIO user LEDs, repurposed J4). BOM attrs set:
      0805 LEDs (red system / yellow user), 22Ω IR (C17958), LCSC on all new
      parts. Commits on PR #11. **The electrical redesign — the hard, dead-
      board-risk part — is complete and verified.**
- [ ] **Schematic cleanup (next):** ERC is 219 violations, but **~197 are
      orphan graphics** from the deletions (99 unconnected_wire_endpoint, 44
      endpoint_off_grid, 25 label_dangling, 18 no_connect_dangling, 11
      wire_dangling) — the netlist is correct, the dangling wire/label/NC
      stubs left by removed symbols need sweeping. Plus: real residue = 13
      multiple_net_names (dual functional+GPIO labels, acceptable), 4
      pin_to_pin + 1 power_pin_not_driven (PWR_FLAG/pin-type config, e.g.
      AHT20 VDD is `unspecified` type). Then: **J2 → SMD USB-C footprint**
      (verify pad names vs C393939 — pad-map risk), **un-DNP R28/R29** (I2C
      pull-ups now fitted).
- [~] **PCB re-layout — clean reproducible pipeline + placement fix
      (autonomous, 2026-06-14 session 2).** Diagnosed the root causes of the
      stuck routes and built a deterministic, re-runnable pipeline:
      **rip → `pcb_place_v2.py` → `pcb_router.py` → `pcb_stub_heal.py` →
      `pcb_pour.py`**.
      - **`scripts/pcb_place_v2.py`** (new): collision-checked greedy placer
        that re-seats the C3-support parts (R5/R6/R7/R8/R28/R29/C6 +
        decoupling) at the nearest free slot to their C3 pin, highest-priority
        pin-pullups first. The v1.4→v2 swap had left them ~45mm from the new
        C3 pins; this closed **IO8_STRAP + I2C_SDA** (router went 7→4 unrouted).
      - **`scripts/pcb_stub_heal.py`** (rewritten): the grid router targets
        each pad's bounding *box*; for round THT pads the bbox corners are
        outside the copper, so legs stop ~1mm shy → DRC unconnected. This
        reads the DRC report and adds ONE short bridge from the pad anchor to
        the nearest same-net track **vertex** (never a mid-segment point →
        no dangling), with a **foreign-clearance guard** that rejects any
        bridge that would short. Closed 6 THT shortfalls cleanly, correctly
        *refused* 2 that would short (IR_RX_VS, SPARE_IO1 — dense sensor/header
        corners). NOTE: earlier blind/geometric heal variants caused real
        shorts — the targeted+guarded version is the keeper.
      - **State: no shorts**, DRC non-cosmetic = 2 antenna-keepout (accepted),
        1 U3/H1 courtyard (accepted), 2 starved-thermal, 5 track_dangling,
        3 holes_co_located, 1 hole_to_hole. **8 unconnected**, all now
        characterised:
        * **STRUCTURAL (need design changes):** CC1 (R1↔J2.A5), USB_D±
          (A6↔B6, A7↔B7) — all three are the **THT USB-C escape problem**
          (0.85mm-pitch through-holes can't fan the inner data/CC pins out).
          → **fix = the SMD-16P USB-C swap (item 4 above)**, which the BOM
          plan already calls for. ESP_BOOT (R6↔U3.8) — pin 8 is boxed in by
          the **D1 TVS** sitting under the C3 south pins → **fix = relocate
          the power-entry cluster (D1/F1/U1) out from under C3**.
        * **LOCAL rework:** IR_RX_VS + SPARE_IO1 (rip the bad stub, re-route),
          2 GND zone islands (stitching), 5 track_dangling (stub cleanup).
      - Helper venv `/tmp/kv10` persists (app python + numpy). silk_overlap is
        ~90 (baseline 44) — a silk pass is still owed before CI green.
      **Next placement step:** SMD USB-C swap + power-cluster relocation, then
      one more rip→route→heal→pour cycle should reach 0 real unconnected.
- [~] **SMD USB-C swap DONE + structural routing closed (session 2 cont.).**
      `scripts/pcb_swap_usbc.py`: J2 THT GCT → **SMD XKB U262-16XN-4BVC11
      (= JLCPCB C393939)**, the part the BOM plan already specifies. Renames
      the footprint's shield posts SH→S1 to match the symbol's shield pin
      (golden expects J2.S1). Schematic J2 footprint + LCSC (→C393939) updated
      to match → **GOLDEN still OK (36/36), ERC = 1 (baseline), parity holds.**
      The single SMD pad row fans the data/CC pins to B.Cu — **closed all 3
      THT-escape gaps (CC1, USB_D+, USB_D−)** in one move. Also relocated
      **D1 (TVS) out from under the C3 south pins** and dropped **R6 (BOOT
      pullup) vertically under pin 8** → **ESP_BOOT now routes**. R1 moved
      beside the new A5. **Structural unrouted: 4 → 1** (only IO8_STRAP left —
      a 1.5mm-pin-pitch packing limit: two 1206 pullups can't both sit under
      adjacent pins 7/8; needs R7 as 0805 or a hand L-route). Remaining 8
      DRC-unconnected are now **mostly GND-pour** (3 zone islands + U3.9
      thermal + J2 shield S1↔A1 — the pour/stitching needs a pass after the
      part moves; 4 starved_thermal corroborate), plus IO8_STRAP, IR_RX_VS,
      SPARE_IO1. silk still ~90 (owe a silk pass). **The expensive structural
      problems are solved; the remainder is GND-pour tuning + 1 pin + cosmetics.**
- [ ] **Validation rebuild + green CI (remaining):** rewrite the POLARITY
      table in `hardware_validate.py` for the v2 netlist (currently all v1.4
      parts — D8/D9/Q1/Q2/Q4/Q5/U2 buck/CH340/AM2302/L1); update
      `fab-outputs.py` HAND_SOLDER (kit = 4×IR LED + TSOP + USB-C + headers)
      + JLC_ROTATION for SOT-223/ESP32-C3-WROOM-02/AHT20/0805; refresh
      `ci-baseline.json` in the kicad:10.0.2 container; regen fab-outputs +
      bom_report. Then the PCB DRC must reach the accepted-baseline set.
- [ ] **Re-layout** (Mac): module footprint changed + ~12 parts gone → placement
      redo + freerouting/heal/pour/DRC (the H2 pipeline). Board can shrink.
- [ ] **Fab + CI validation rebuild:** new HAND_SOLDER split (kit = IR LEDs +
      TSOP + headers only), JLC_ROTATION for C3/AHT20/USB-C/SOT-23 packages,
      rebuild the polarity truth table for the new netlist, add a USB-D±→C3
      pin invariant + C3 strapping check, refresh ci-baseline. Run
      `bom_report.py` to confirm the cost.



✅ **AM2302 (U5) 3D model seating FIXED & visually verified (2026-06-13, remote
session).** Nick reported the temp-sensor pins didn't line up with the holes in
the 3D viewer, the silk outline was off by a different amount, and suspected a
180° rotation. All three were the same root cause: the vendored EasyEDA
`AM2302.step` is oriented 180° about its vertical axis vs how KiCad's silk/fab/
courtyard were drawn, so the body sat on the wrong side of the pin row and the
pins landed +2.05 mm off in board-Y. **Fix: `(rotate (xyz 0 0 180))` +
`(offset (xyz 3.81 -1.35 9.2))`** (was offset y −0.7, rotate 0). Method, since
this repo has no KiCad on Mac-only assumptions: installed kicad-cli 9.0.9 (PPA)
in the remote container, exported the board to GLB (KiCad bakes all STEP
assembly transforms), parsed the mesh in board coordinates, and measured the 4
pin-leg centroids vs the pad centers — iterated to **dX=0.000, dY=0.000 on all
four pins**, re-confirmed against the real board file (not just an isolated
copy). Visual check (kicad-cli render, bottom view) shows each pin dead-centre
in its via; top/iso show the body now flush inside the silk with the grille
facing up. **Copper/pads/drills/silk/courtyard/netlist UNCHANGED** — the diff is
2 lines inside the `(model …)` block only, so zero fab/electrical impact (CPL
uses footprint origin + pads, not the model offset). No effect on the actual
board. Supersedes the "model seating NOT fixed — defer to Nick's Mac" note
below.

🐛 **Hotfix (2026-06-13): Pages deploy was failing since the CI overhaul
merge.** `fab-outputs.py`'s isometric render passed `--rotate=-30,0,45`;
kicad-cli 10's arg parser reads a value starting with `-` as a flag
(`Unknown argument: -30,0,45`) and aborts. Fixed by adopting the same
leading-space trick `build-site.sh` already uses (`--rotate " -30,0,45"`).
`ci.yml` was green throughout — only the separate `pages.yml` workflow broke.

🔄 **CI pipeline overhaul (2026-06-13, Nick's request): software-style
process — open a PR, watch CI; no local check battery required.** New
`.github/workflows/ci.yml` runs on every PR + main:
1. **hardware** (kicad/kicad:10.0.2, same image as Pages):
   `scripts/ci/hardware_validate.py` — ERC + DRC (incl. schematic parity)
   compared against `hardware/ci-baseline.json` (errors gate strictly,
   warnings gate on increase; refresh with `--update-baseline` inside the
   CI image), **netlist freshness as an electrical partition check**
   (KiCad-version-proof: compares pad partitions + component
   value/footprint sets, not text — this also codifies the previously
   ad-hoc session "partition check"), BOM LCSC lint (allowlist J4/J5/JP1),
   3D-model path check (warn-only). Then regenerates the fab package and
   uploads it as a CI artifact.
2. **firmware**: `pio test -e native` (35 tests) + ESP8266/ESP32 builds —
   previously local-only.
3. **app**: typecheck, vitest, build, Playwright e2e (mock serial).
4. **bom-report** (non-gating telemetry): `scripts/ci/bom_report.py` pulls
   live JLCPCB price tiers/stock/Basic-Extended per BOM line; markdown in
   the job summary, JSON artifact per run (cost history), HTML+JSON on the
   Pages site. First run already caught drift: **C17922 (18Ω) is now
   Extended at JLC** (so 4 Extended SMT lines, not 3) and re-confirmed the
   AM2302 squeeze (35 in stock, $6.83/ea ≈ 42% of per-board part cost).
**Polarity/orientation automation (2026-06-13, Nick: "don't rely on me for
correctness"):**
5. **Polarity truth table** in `hardware_validate.py` (gating): 66 pin→net
   invariants across all 23 polarized/orientation-critical parts (every
   diode direction, FET pinout, IC power pin, fuse/inductor path), locked
   from the reviewed design — any future flip fails CI with the exact pin.
6. **CPL rotation corrections** in `fab-outputs.py`: JLC's per-package
   zero-orientation offsets applied to the CPL (SOT-23 +270, TSOT-23 +180,
   SOIC +270, ESP32-WROOM +270 — JLCKicadTools community DB values); every
   assembled footprint MUST be classified (offset or symmetric) or the
   script refuses; new `esp32-ir-remote-orientation-report.csv` makes the
   JLC-preview check a mechanical per-part comparison against
   final_top.png. ⚠️ First order still verifies the offsets in the preview
   — if one is wrong, fix the table, not the order.
7. **🐛 REAL BUG FOUND & FIXED by this work — D1 TVS marking was inverted.**
   The schematic symbol (`D_TVS`) is bidirectional so no electrical check
   could see it, but the `D_SMB` footprint prints its cathode band at
   pad 1, which was wired to GND; correct unidirectional orientation is
   cathode→+5V. Anyone hand-soldering to the board's own marking would put
   the TVS forward across the rail (board won't power). Fix: D1 rotated
   180° in place (pads are symmetric — copper untouched, verified pad
   positions identical) + schematic symbol rotated to match + netlist
   updated; the silk band now marks the +5V pad. Kit CSV + bring-up.md
   instructions updated ("align band with the on-board marker"). The new
   polarity table locks D1.1(K)=+5V forever.
**Build artifacts are out of git:** `hardware/fab/` +
`esp32-ir-remote_bom.csv` untracked/gitignored; Pages regenerates and
publishes the full fab package + cost report on every merge
(`build-site.sh`). Freeze an order by tagging the commit (`order/v1.4`).
The committed netlist STAYS tracked — it's the reviewable electrical diff,
and CI now enforces its freshness. SPICE was evaluated and **rejected** for
rev 1: the analog content is a vendor-qualified buck module, an
analytically-verified gate-drive RC, and LED resistor math — dead boards
come from footprints/rotations/pinouts, which simulation can't see (the
checks above can). **Baseline committed** (`hardware/ci-baseline.json`,
reviewed from the CI container run): DRC errors = the 3 documented accepted
ones (H1 antenna keepout), unconnected = the 7 pour-fragment notices,
ERC = 7 deliberate dual-label warnings + 1 lib_symbol_mismatch. Residual
parity 71 = accepted name/metadata residue, re-verified harmless this
session: dual-label picks (PCB `UART_TX` vs netlist `/ESP_GPIO1`), stale
auto-names on label-less 2-pin nets (`unconnected-(D11-A-Pad2)` actually
contains D11.2+R25.2 — the known KiCad netlister quirk; proper fix = put
labels on those nets, queued below), one stale PCB-side LCSC field
(C124375) + DNP-attr mismatch — all inert for fab outputs, which are
netlist-driven. Cleanup debt (cosmetic, any KiCad session): label the
auto-named 2-pin nets, clear the stale C124375 footprint field, sync DNP
attrs onto J6/R28-R30 footprints — would shrink the parity baseline
toward ~10.

✅ **Board v1.4: pre-order review pass — SMT-only assembly + Basic-part swaps
(2026-06-11, remote session, Nick approved scope).** Full design review before
H3.2 ordering (electrical re-verify came back clean — third independent pass).
Changes, all verified with the standard battery (ERC **0 errors**/7 dual-label
warnings — the 2 "J4 errors" were orphan IO25/26 label+wire stubs, now real
no_connects; DRC = 3 accepted errors + 7 pour notices, zero real unconnected;
netlist↔PCB partition IDENTICAL, 235 pads):
1. **Assembly model: SMT-only + hand-solder kit.** The old fab BOM/CPL told
   JLC to place 13 THT parts that bring-up.md said are hand-soldered — incl.
   the IR LEDs, which a P&P line can't bend over the edge (they'd arrive
   vertical), and even the J4/J5 headers in the CPL. New
   `scripts/fab-outputs.py` regenerates the whole `hardware/fab/` package
   with the split defined in ONE table; kit list =
   `fab/esp32-ir-remote-hand-solder-kit.csv` (LCSC codes, polarity notes,
   fit-before-first-power flags for F1/J2/L1/D1).
2. **Basic-part swaps (fee/stock):** Q3 IRLML6344→**AO3400A** (C20917,
   field-only, SOT-23 identical); SW1/SW2 TS-1088R→**TS-1187A** (C318884,
   new 4-pad footprint `lib:SW-SMD_TS-1187A-5.1x5.1`, same-row pads common
   → numbered 1/1+2/2 so the 2-pin symbol maps unchanged). PCB: footprints
   swapped in place; the 0.6mm +5V feed under SW1's new bottom pads rerouted
   south (y=111.5 corridor); bridge tracks join pad pairs; pours refilled.
3. **Result: 23 assembled BOM lines / 47 placements, only 3 Extended**
   (U1/U2/U3) vs ~17-18 before → ~$42/order less in loading fees + no THT
   assembly fees. Q3's stale PCB-side LCSC (C8545! the H1.2 bug, never
   synced) fixed to C20917.
4. **Docs reconciled:** power-supply.md (4.7µH, real LED currents),
   status-leds.md (1k/100k actuals), esp32-mcu.md (J1 section → J3/J4/J6
   reality, GPIO34 input-only note), ir-transmitter.md (AO3400A),
   bring-up.md (rev 1.4: solder F1/J2/L1/D1 before first power), spec →
   **v1.4** + index. Headless toolchain: ghcr.io/inti-cmnb/kicad9_auto
   (KiCad 9.0.7; docker hub was rate-limited), baseline reproduced exactly
   before any edit.
   Nick's render review (2026-06-13): TS-1187A switch STEP vendored
   (EasyEDA via jlcpcb MCP; model terminals verified to land on the
   footprint pads — DONE, models resolve in CI). ✅ AM2302 (U5) model
   seating FIXED 2026-06-13 (see the "Now" entry above): rotate Z 180 +
   offset y −1.35; pins verified dead-centre in the vias by parsing the
   KiCad-baked GLB mesh in board coords (dX=dY=0.000) and by bottom-view
   render. The earlier pcbnew-Python attempt failed because SWIG returns
   m_Offset by value (mutated a throwaway copy) and raw STEP parsing
   couldn't resolve the model's internal transforms — solved here by
   letting kicad-cli's GLB export bake every transform, then measuring the
   mesh. Copper unaffected (4 pads @ 2.54 pitch, fab-safe); model-block
   diff only. Remaining cosmetic debts: lib_footprint_issues DRC warnings
   63→73 (re-serialization noise); PCB still carries single-pad nets
   named ESP_GPIO25/26 on U3 (harmless).

⚠️ **AM2302 stock at LCSC: 35 units ($6.82)** — order the kit parts early or
substitute a generic DHT22.

**Next: H3.2 — Nick orders.** Suggested: 5 PCBs / 2 assembled (economic SMT,
top side), kit parts on the same LCSC cart (see kit CSV; add spares, esp.
2-3× AM2302). At upload, eyeball polarized parts (U1/U2/D1/Q1-Q5) in JLC's
placement preview — kicad-cli rotations vs JLC conventions is the classic
dead-board cause. H1.5 (schematic PDF eyeball) still open.

✅ **Board v1.3 follow-up: R21/R26 0Ω→470Ω + hygiene (2026-06-11, Nick OK'd
larger changes for correctness).** The FET swap's one real regression — a held
RESET/BOOT with the port idle shorted a CH340 pin through the 2N7002 body
diode at ~25mA (the BJTs leaked 0.27mA) — is fixed by making the bypass links
470Ω (C23179, Basic): diode current capped ~5mA, EN/GPIO0 lows ~0.15V (5×
margin to V_IL), desolder-to-disable preserved, BOM line count unchanged.
R3/R4 gate resistors deliberately KEPT (electrically invisible to FET gates,
free ESD protection; removal = copper churn for zero gain). Hygiene: 5 unused
embedded lib symbols purged from the schematic (4 PCM_JLCPCB leftovers — one
with cross-contaminated 0Ω/2N7002 metadata — + orphaned Q_NPN_BEC); netlist
byte-identical after purge. Silk label now "auto-rst 470R"; gerbers + renders
regenerated via kicad-cli (copper geometry verified identical to the frozen
package modulo net-name attributes; B-silk no longer carries pcbnew's
plot-pads-on-silk noise). Same verification battery as the FET swap: ERC 9
(2 pre-existing J4 errors + 7 dual-label warnings), DRC 3 accepted / 7 pour
notices / parity 0, partition check identical.

✅ **Board v1.3: auto-reset Q1/Q2 → 2N7002 MOSFETs (2026-06-11, Nick's request).**
S8050 NPN BJTs (C2146) swapped for 2N7002 N-FETs (C8545, already on the
board as Q4/Q5). SOT-23 pinouts map 1:1 (B→G, E→S, C→D) so the layout is
untouched — verified headlessly (kicad/kicad:9.0.6 container): ERC delta is
−2 warnings / no new violations, netlist diff electrically empty (same pads,
same partitions; nets renamed Net-(Q1-B)→(Q1-G) etc. and renamed in the PCB
to match), DRC unchanged vs accepted baseline, netlist↔PCB partition check
identical, schematic parity 0. BOM consolidates 35→34 unique lines (one
Basic part fewer). **Bonus fix found during regen: the committed BOM CSV +
fab BOM still ordered C10 as 100nF C14663 — stale vs the M-4 remediation
(10µF C19702); both now corrected.** Fab outputs in `hardware/fab/` updated
(BOM + raw CPL; gerbers/CPL positions unaffected — no copper changed).
Trade-off note (body diode) recorded in `hardware/notes/usb-serial.md` and
spec v1.3 §Auto-Reset.

🎉 **BOARD LAYOUT COMPLETE — FAB-READY (2026-06-11, unattended session).**
H2.0–H2.4 + H3.1 all done. The 80×55 mm 2-layer board is placed, fully
routed (freerouting via podman + custom heal pipeline), poured, stitched,
silkscreened, and verified:
- **Partition check: netlist↔PCB IDENTICAL** (every net, machine-checked).
- **Connectivity: zero splits** (exact copper model) — every pad/track wired.
- **DRC: 3 errors, all accepted+documented** = H1 mounting hole encroaching
  the WROOM antenna-keepout corner (use a **nylon screw** at H1 — see
  bring-up.md). Plus 7 pour-fragment notices (cosmetic fill islands;
  electrically complete) and silk-overlap warnings.
- **Fab outputs in `hardware/fab/`:** `esp32-ir-remote-gerbers.zip`,
  `…-jlcpcb-bom.csv` (35 lines, DNP excluded), `…-jlcpcb-cpl.csv`
  (67 placements), plus top/bottom/iso renders.

⚠️ **Design deviations made unattended (Nick: review before ordering):**
1. **J4 spare header: GPIO25/26 pins are now NC** (schematic change,
   no-connects added). The center-south routing was saturated; 2 of 8 spare
   GPIOs were sacrificed. J4 carries 3V3/5V/GPIO23/32/33/34/2×GND.
2. USB D+/D− are routed on **split corridors, not length-matched** —
   acceptable for USB full-speed (12 Mbps) on a dev board.
3. Board minimums relaxed to JLCPCB documented floor (clearance 0.127,
   track 0.127; all via/through-hole drills kept ≥0.3 — the 0.2 floor is
   multilayer-only).
4. H1 mounting hole sits in the antenna-keepout corner (nylon screw).

All layout-review findings (H-1/H-2/M-1/M-3/M-4) are remediated and
re-verified (2026-06-11 second pass); M-2 (IR_RX trace passes near the IR
TX array) is accepted for rev 1 — see H2.5 below.

**Next:** Nick reviews the renders/3D viewer + the deviations above,
then H3.2 order (Nick only). H1.5 (schematic PDF eyeball) still open.
F1.4/F1.5 firmware+bench unchanged. The fab files are submission-ready
pending Nick's go.

✅ **Board v1.2 change set COMPLETE (2026-06-11, headless via kicad-edit MCP +
scripted s-expr surgery, every step netlist-verified).** ERC is now **0 errors**
(8 deliberate dual-label warnings). J1 removed; Qwiic/spare-GPIO/ext-IR/JTAG
connection points added; all H1.4 fixes in; LCSC coverage complete (only the 3
hand-solder pin headers blank); BOM regenerated from schematic, `BOM.md` demoted.
Five latent BOM bugs found & fixed (R13/R22→18Ω code, Q3→2N7002 code, R14/R15→
0805 codes on 1206 footprints). **Remaining H1:** H1.3 hierarchical refactor
(optional, netlist-gated) and **H1.5 Nick eyeballs the schematic PDF** (on the
Pages site). Then H2 layout. F1.4 firmware + F1.5 bench check still pending.

✅ **GitHub Pages live at <https://njdancer.github.io/claude-ir/>** — every
push to main publishes schematic PDF/SVG, BOM CSV, and all rendered docs.

➡️ **Active phase: H1 — Schematic verification.** Done this session: H1.0
(28 protocol fixtures preserved), H1.1 (ERC baseline = 9 violations, all
expected; netlist resynced), H1.2 census (no orphan; LCSC backfill mapped),
**H1.4 datasheet review (clean — see `datasheet-review-h1.4.md`)**. The board
is electrically sound; remaining H1 work is a **batch of small KiCad-GUI edits**
(H1.2 convention cleanup + LCSC fields + the H1.4 action items: R13 gate
resistor, L1→4.7µH, TSOP Vs filter, drop redundant PWR_FLAG) then H1.3
hierarchical refactor and H1.5 human PDF review. These need the KiCad GUI =
a Mac bench session. F1.1–F1.3 done; F1.4 firmware + F1.5 bench check pending
(no ESP board was on USB this session — only Bluetooth/Cricut ports present).

### Board v1.2 change set — **DONE (2026-06-11)**, commits 83a91b9…

All items landed headlessly (kicad-edit MCP + scripted s-expression surgery),
each verified by ERC + machine-checked netlist-partition diff and committed
separately:
1. **J1 removed** (38-pin DevKitC breakout + harness; 22 freed GPIOs NC'd,
   GPIO6-11 flash pins no longer broken out — closes the H1.4 LOW item).
2. **J3 Qwiic** JST-SH (C160404): GND/3V3/SDA=21/SCL=22 + R28/R29 4.7k
   pull-up footprints (C17936, DNP).
3. **J4 spare header** 2×5: 3V3/5V/GPIO23·25·26·32·33·34/2×GND.
4. **J5 ext-IR header** + R30 18Ω series footprint (DNP): EXT_IR_A net →
   +3.3V; cathode side on IR_DRAIN (Q3 drain, now labelled).
5. **J6 JTAG** 2×5 DNP, ARM 10-pin layout incl. EN as nRESET.
6. **H1.4 fixes:** R13 470Ω; L1 4.7µH = SWPA6045S4R7MT **C78804** (no Basic
   4.7µH power inductor exists anymore — one Extended feeder fee accepted);
   TSOP Vs RC filter (R27 100Ω C17901 + C9, net IR_RX_VS + PWR_FLAG);
   D7's R16 → 470Ω; redundant PWR_FLAG removed → **ERC 0 errors**.
7. **H1.2:** 8 PCM_JLCPCB symbols → generic (electrically-empty, verified);
   LCSC backfill complete; **5 latent BOM bugs fixed** (R13/R22 carried the
   18Ω code C17955; Q3 carried the 2N7002 code C8545 → C53550; R14 → C17900,
   R15 → C4410 — both had 0805 codes on 1206 footprints); BOM regenerated
   (`esp32-ir-remote_bom.csv`, with DNP column); `BOM.md` demoted to
   rationale-only.

### Tooling: sticky PR comment with renders + stats (2026-06-14)

Every PR now gets one auto-updating sticky comment (`pr-comment` job in
`ci.yml`, non-gating). It shows board renders (top/bottom/iso) plus
hardware (ERC/DRC vs baseline, board dimensions/layers, netlist comp/net
counts, BOM LCSC coverage), BOM cost/stock, firmware flash/RAM per env, and
app unit-test counts. Each section degrades to a "—" row if its facts file
is missing, and it runs even when an upstream job failed (`always()`) so a
red PR still shows the board. Pieces:
- `scripts/ci/pr_report.py` assembles the Markdown from facts JSONs +
  parses the PCB Edge.Cuts bbox for dimensions (reuses `hardware_validate`'s
  sexp parser). `hardware_validate.py --json` emits the hardware facts;
  `firmware_size.py` / `app_facts.py` parse the build/test logs.
- GitHub markdown can't inline workflow artifacts, so renders are pushed to
  a long-lived **`pr-assets`** orphan branch (`publish_pr_assets.sh`, one
  `pr-<N>/` subdir per PR, overwritten each run) and embedded via
  raw.githubusercontent. Cache-busted by `?<sha>`. Repo is public so this
  works without auth. Comment posted by `marocchino/sticky-pull-request-comment`.
- Caveat: fork PRs get a read-only token, so the branch push + comment would
  fail there; fine for this repo's same-repo `claude/*` branches.

### Tooling: 3D viewer now shows real STEP colors (2026-06-11)

The flat one-color-per-component look of the Pages 3D viewer was a KiCad 9
Linux bug: `kicad-cli pcb export glb` dropped all STEP model colors, so
`scripts/fix_glb_materials.py` painted each part a single hand-picked color.
Verified in containers that **KiCad 10.0.2 exports per-face STEP colors
correctly** (resistor end caps, gold pins, WROOM shield/PCB, etc.), so the
Pages CI image is bumped `kicad/kicad:9.0.6 → 10.0.2` (kicad-cli 10 reads
the v9 files without migration; full `build-site.sh` verified in the image).
The fixer script now only adds the metallic/roughness factors kicad-cli
still omits (color-classified: gold/silver → metal) and forces translucent
silk/board-body opaque — this also fixed a live bug where white silkscreen was
tinted green by an unclamped 1.1 multiplier. (The soldermask was *also* forced
opaque here, which silently buried every copper trace — fixed 2026-06-14, see
note below.) The recolor-by-name table
remains as a fallback for KiCad 9 exports (e.g. local Mac builds until the
bench moves to 10). Note: real *texture maps* (IC markings, FR4 weave) don't
exist in STEP/GLB sources at all — that would need a Blender-style bake
pipeline, deliberately out of scope.

### Tooling: 3D viewer now shows copper traces (2026-06-14)

The Pages 3D viewer rendered the board as a featureless green slab — no
traces, pads, or vias visible. Root cause was *not* the export
(`kicad-cli pcb export glb --include-tracks` is valid and the copper mesh
(`esp32-ir-remote_copper`) survives the whole center→optimize→draco
pipeline). It was `scripts/fix_glb_materials.py` forcing **all** translucent
board materials opaque, including the soldermask — a flat sheet kicad-cli
exports just above the copper plane, so an opaque mask hides everything
beneath it. Fix: the soldermask is now exempted (kept `alphaMode:BLEND`,
α=`SOLDERMASK_ALPHA`=0.75, glossier roughness to cut model-viewer haze) while
silk/body still go opaque; copper now reads through as the familiar
darker-green routing. Verified before/after in model-viewer (side-by-side
render). A validation assert now fails the build if no translucent soldermask
survives, so a future refactor can't silently re-bury the traces. Tune
visibility-vs-milkiness via the two constants near the top of `main()`.

### Tooling: 3D models are vendored (2026-06-11)

All 21 STEP models the board uses live in `hardware/lib/3dshapes/` and every
footprint's model path is `${KIPRJMOD}`-relative. Reason: the `kicad/kicad:9.0`
CI container ships **no** 3D library, so `${KICAD9_3DMODEL_DIR}` paths silently
drop from Pages-built GLB/renders (the "only the inductor rendered" bug).
If a footprint changes, re-vendor its model the same way (copy STEP, rewrite
path) or the deployed viewer regresses (CI's model-path check warns on broken
paths). The Pages pipeline builds everything in `_site/` from source on every
push — never commit site artifacts. `hardware/fab/` is likewise gitignored
since the 2026-06-13 CI overhaul: CI regenerates it per PR, Pages publishes
it per merge, and order packages are frozen via git tag.

### Tooling: second KiCad MCP (`kicad-edit`) — **needs a session restart**

Installed and configured `mixelpixx/KiCAD-MCP-Server` at
`tools/kicad-mcp-server/` (gitignored): `npm install && npm run build` done, a
`--system-site-packages` venv (`.venv`, KiCad py3.9 + pcbnew 9.0.6 + cairosvg
etc.) created, smoke-tested (MCP handshake returns **155 tools**, "SERVER
READY"). Added to `.mcp.json` as **`kicad-edit`** (alongside the existing
read-only `kicad`). **Battle-tested on the v1.2 change set (2026-06-11).
Our install IS upstream HEAD (8fd5c8c, 2026-06-03) — the bugs below are
open upstream (#234/#235 have issues/PRs pending; the ignored-`angle` and
field-dropping-replace bugs appear unreported — worth filing):**
- `get_board_2d_view` needs an explicit `layers` list on KiCad 9+ (upstream
  issue #235).
- `add_schematic_component` **ignores its `angle` param** (symbol placed at 0°;
  only the ref text rotates). Fix the instance `(at x y angle)` by hand after.
- `replace_schematic_component` **drops the Datasheet and LCSC fields** and
  doesn't adapt to symbol-geometry differences (the PCM NMOS symbol is the
  *mirror* of `Q_NMOS_GSD` — pins land in air; fix with `(mirror y)`).
- Delete/add operations **re-serialize the whole .kicad_sch onto one line**;
  re-pretty-print before committing (s-expr formatter snippet in git history,
  commit ea57f23) or diffs become useless.
- Labels are emitted with `bottom` justification → text sits offset/overlapping
  in renders (upstream issue #234); power-symbol refs (#FLG04 etc.) aren't
  hidden, so ref+value both render ("doubled" text). Cosmetic; GUI cleanup in
  H1.3.
- KiCad 9's own netlister drops/renames **label-less 2-pin nets** (false
  `wire_dangling` ERC + net missing from netlist). Name the net with a label.
- **PCB-side bugs found during H2.0 (2026-06-11):** `sync_schematic_to_board`
  only *adds* — it does not remove deleted components (J1 stayed), update
  changed footprints/values, and it **splits dual-labelled nets** (U3 pads
  landed on `ESP_GPIOxx` nets while peripherals stayed on functional names —
  7 broken connections, repaired via pcbnew pad-net reassignment).
  `edit_component` changes the footprint *name* but not the pad geometry.
  `assign_net_to_class` is advertised but unimplemented ("Unknown command");
  `create_netclass` doesn't persist — net classes were written into
  `.kicad_pro` `net_settings` JSON directly (eeschema needs `*`-prefixed
  patterns for local nets: `/IR_DRAIN`). Its auto-save also refuses after its
  *own* writes ("disk changed externally") — reload via `open_project`.
- **Headless pcbnew (KiCad 9.0.6) quirks** (not kicad-edit): only the FIRST
  `FootprintLoad` per process returns a typed object — do one swap per
  process. `PCB_FIELD(fp, 0, name)` clobbers the Reference field (id 0).
  `LoadBoard` returns None if any item sits on a `Rescue` layer (the
  EasyEDA-converted `IND-SMD_L6.7-W6.7.kicad_mod` had `(layer "")` ×4 — fixed
  to F.Fab in `hardware/lib/`).
It exposes schematic/PCB
*editing* (add_schematic_component/wire, place_component, route, autoroute),
*rendering* (`get_board_2d_view`, `kicad://board/preview.png`), and *export*
(svg/pdf/3d/bom/gerber/CPL). Two potential uses: (a) do some of the **Board v1.2
change set** edits headlessly instead of the GUI bench session (evaluate
carefully — MCP edits on a hand-drawn schematic are unproven; verify every
change with `hardware-check.sh` + netlist diff); (b) generate board preview
PNGs for the Pages docs below.

### Publishing: GitHub Pages artifacts — **DONE (2026-06-10)**

Live at <https://njdancer.github.io/claude-ir/>, verified end-to-end (index,
schematic PDF, rendered docs all 200). A stale custom domain (`nick.dncr.me`,
no DNS record) on the `njdancer.github.io` user-pages repo was 301-ing all
project pages into the void; Nick removed it 2026-06-10.
- **`scripts/build-site.sh`** is the single source of truth for site content:
  schematic PDF + per-sheet SVGs + grouped BOM CSV (with LCSC) via `kicad-cli`,
  plus every tracked `*.md` rendered to HTML with pandoc (repo paths mirrored
  under `docs/` so relative links survive; `.md`→`.html` hrefs rewritten).
  Runs identically locally (KiCad app bundle) and in CI.
- **`.github/workflows/pages.yml`** runs the script in the `kicad/kicad:9.0`
  image and deploys via `upload-pages-artifact` + `deploy-pages`. Pages enabled
  with `build_type=workflow` via `gh api`.
- **After H2 layout:** add PCB 2D/3D renders to `build-site.sh`
  (`kicad-cli pcb render` / `pcb export svg`); a commented stub marks the spot.
  The `kicad-edit` MCP's `get_board_2d_view` can supplement with PNGs.

## Done (context for new sessions)

- [x] ESP8266 breadboard: capture + transmit firmware, verified against real AC
- [x] Protocol fully reverse-engineered (`re-findings.md`): BOSCH144 + COOLIX,
      two-payload architecture confirmed by transmission experiments
- [x] Web control UI scaffold (`app/`) with mock/real serial layers and tests
- [x] Hardware spec v1.1 (`specs/hardware-dev-board-v1.md`)
- [x] Flat KiCad schematic ~complete; BOM + JLCPCB part assignments
- [x] circuit.md experiment removed; rationale salvaged to `hardware/notes/`;
      `scripts/hardware-check.sh` added (ERC + netlist regeneration)

## Phase H1 — Schematic verification *(needs: Mac)*

Make the schematic provably correct before any layout effort builds on it.

- [x] **H1.0 Preserve the ground truth:** 28 curated, valid-decode fixtures
      copied into tracked `captures/reference/` with clean names + a
      provenance/decode `README.md` (temp sweep 16–26 incl. half-degrees,
      modes 1–5, fan 1–6, power on/on-2/off/button, swing A/B, boost, LED).
      Gap recorded: no valid `temp-28` capture exists (both bench attempts
      failed to decode) — folded into the F1.5 bench checklist.
- [x] **H1.1 Baseline:** ERC = **9 violations (1 error, 8 warnings)**, all
      expected, no schematic fixes needed yet:
  - 1 error `pin_to_pin`: PWR_FLAG (#FLG03) on CH340C V3 output (U2.4), the
    redundant-flag-on-power-output pattern → owned by H1.4 (CH340C V3/VCC).
  - 8 warnings `multiple_net_names`: every MCU GPIO net is dual-labelled
    `ESP_GPIOxx` + functional (`IR_TX/RX`, `TEMP_DATA`, `USER_LED1/2`,
    `UART_TX/RX`, `ESP_VDD`/`+3.3V`). Deliberate; KiCad just picks one name.
    Natural cleanup in the H1.3 hierarchical refactor.
  - **Script fix:** `hardware-check.sh` now prefers the KiCad app-bundle CLI
    over a Homebrew `kicad-cli` on PATH whose broken library path produced
    ~146 bogus `lib_symbol_issues`/`footprint_link_issues` (153→9).
  - **Netlist resynced:** committed `.net` was stale vs the schematic —
    regenerating surfaced an already-committed design change (auto-reset
    bypass JP2/JP3 header jumpers → R21/R26 0Ω SMD links) plus the LCSC
    fields from e1f89f4. `usb-serial.md` updated to match; spec lags (H1.2).
- [x] **H1.2 Library hygiene — DONE 2026-06-11:** census done this session; edits pending
      (KiCad GUI / surgical):
  - [x] ~~Two ESP32 symbols~~ **NOT an orphan — no removal.** `RF_Module:ESP32-
        WROOM-32E` = U3 (the MCU, 39 nodes). The second symbol is **J1**, an
        intentional *DevKitC debug breakout header* ("Debug breakout header
        matching ESP32-DevKitC V4 pinout", 2×19 pin-header footprint, 38 pins
        mirroring U3's GPIOs). Keep both. H1.4 should verify J1↔U3 pin mapping
        matches the real DevKitC pinout.
  - [x] **Convention cleanup (8 symbols) — DONE 2026-06-11:** 6 resistors use
        `PCM_JLCPCB-Resistors` and 2 transistors use `PCM_JLCPCB-Transistors`;
        everything else uses generic `Device:*` (44 symbols). Standardize the
        8 onto generic symbols carrying LCSC in fields. *KiCad GUI edit.*
  - [x] **LCSC backfill — DONE 2026-06-11 (headless).** All 65 comps have footprints ✓; 15 lack an LCSC
        field. `hardware/BOM.md` (hand-curated) has the LCSC numbers but is
        **stale vs the schematic on reference designators** (it even swaps
        J1/J2 and mislabels R21) — so match by *function/value*, NOT by ref.
        Schematic is the source of truth (BOM.md's own footer agrees). Add
        these LCSC fields to the schematic symbols (high-confidence,
        function-matched to BOM.md):

        | Sch ref | Function (schematic value) | LCSC |
        |---------|----------------------------|------|
        | C10 | 100nF decoupling | C1591 (same as C4/C7/C9) |
        | D1  | TVS (SMBJ5.0A) | C83333 |
        | D4,D5 | IR LED TSAL6200 (match D2,D3) | C55528 |
        | D6  | Red 5V power LED | C99772 |
        | D7  | Y-green 3.3V power LED | C85161 |
        | D8,D9 | Amber serial TX/RX LED | C85160 |
        | D10 | Red IR-TX indicator LED | C99772 |
        | D11,D12 | Blue user LED | C86881 |
        | F1  | Polyfuse 1.1A (1812) | C142747 |
        | SW1,SW2 | Tact switch TS-1088R | C455280 |
        | L1  | Inductor — **DECIDED (H1.4): use 4.7µH** (3.9µH is in-range but 4.7µH = datasheet typical + better JLCPCB Basic stock, zero downside). Spec Isat ≥~2.7A, DCR <100mΩ, Basic part. |
  - [x] **Kill the dual-BOM problem — DONE 2026-06-11:** after the schematic carries all LCSC
        fields, regenerate the BOM from it (`kicad-cli sch export bom` / the
        kicad MCP) so `esp32-ir-remote_bom.csv` is complete, then either delete
        `hardware/BOM.md` or demote it to rationale-only (it currently
        disagrees with the schematic on designators, R15 value, R21 identity,
        J1/J2, and JP2/JP3 — all already correct in the schematic).
  - [x] **Spec reconciliation — DONE** (spec v1.2). `specs/hardware-dev-board-v1.md`
        updated: auto-reset JP2/JP3→R21/R26 0Ω, L1→4.7µH, J1/J2, assembly model
        now JLCPCB-PCBA/Basic-parts, H1.4 fixes (gate R, TSOP filter), and the
        v1.2 macro feature set (see "Board v1.2 change set" below). BOM tables
        flagged stale → regenerate from schematic. Index updated. Still TODO:
        fix the stale "JP2/JP3" silkscreen note in H2.4 below.
- [ ] **H1.3 Hierarchical refactor (netlist-gated):** split the flat sheet
      into sub-sheets matching `hardware/notes/` (power, usb-serial, mcu,
      ir-tx, ir-rx, temp-sensor, status-leds). Gate: netlist diff before vs
      after is electrically empty (net names may change; connectivity may not).
- [x] **H1.4 Adversarial datasheet review — DONE.** 6 parallel subagents (one
      per subsystem) re-derived required connections from datasheets vs the
      netlist; every ERROR/HIGH item re-verified against the netlist directly.
      Full record: [`hardware/notes/datasheet-review-h1.4.md`](hardware/notes/datasheet-review-h1.4.md).
      **All MUST-cover items checked & clean** (strapping incl. GPIO12 safe &
      GPIO6-11 flash-internal; CH340C R232-LOW + V3/VCC@3.3V; AP63203 BST/caps;
      USB-C CC pull-downs + fuse-before-TVS ✓; IR MOSFET + LED math; decoupling).
      A reported "auto-reset bases floating" showstopper was a **false positive**
      (refuted by netlist re-check — circuit is the correct cross-coupled design).
      **Action items fold into the H1.2 GUI session** (none block; all small):
  - [x] **HIGH (done):** R13 gate resistor 10kΩ → ~330Ω–1kΩ (10k too slow for 38kHz IR).
  - [x] **MED (done):** L1 → 4.7µH (decided above); add TSOP Vs RC filter (~100Ω+100nF).
  - [x] **LOW (done except firmware item):** D7 green 150Ω→470Ω (R16); confirm J1 GPIO6-11 breakout intent;
        remove redundant PWR_FLAG on U2 V3 (clears the 1 ERC error); firmware
        guard vs stuck-high IR_TX.
  - [x] Replaced 3 broken (HTML-saved) datasheet PDFs with genuine vendor PDFs;
        YAGEO 100nF cap one still HTML (generic passive, low priority).
- [ ] **H1.5 Human gate:** export schematic PDF (`kicad-cli sch export pdf`),
      Nick eyeballs it. Findings fixed → ERC clean → netlist committed.

**Gate:** ERC clean, datasheet review findings resolved, Nick has seen the PDF.

## Phase H2 — PCB layout *(needs: Mac)*

72 footprints imported & synced to the v1.2 schematic (H2.0, 2026-06-11);
0 tracks routed; Edge.Cuts empty. Layout is greenfield.

- [x] **H2.0 Schematic→PCB sync (2026-06-11):** J1 deleted; J3–J6 + R27–R30
      added; L1/Q4/Q5/R20/R21/R23–R26 footprints swapped to match schematic
      (pcbnew scripting — kicad-edit's sync couldn't); R13/R16/L1 values
      fixed; 7 split dual-label nets repaired; EXT_IR_A/IR_RX_VS/C7/C8 pad
      nets corrected. **Verified: net-partition diff netlist↔PCB identical.**
- [x] **H2.1 Constraints first (2026-06-11):** JLCPCB 2-layer rules in the
      project (clearance/track 0.15, via 0.5/0.3, drill 0.3, edge 0.3) +
      net classes Power 0.6mm / IR_Drive 0.5mm (11 nets). Constraints doc:
      `hardware/notes/layout.md` — antenna keepout, IR LED edge fan
      0/45/90/135°, buck loop, USB order J2→F1→D1→U1, DHT22 placement,
      B.Cu GND pour plan, outline drivers, H2.2 exit criteria.
- [x] **H2.2 Placement DONE (2026-06-11):** all 76 footprints placed per
      constraints, zero courtyard overlaps (polygon-exact check); placement
      iterated during routing (R5-R7 pullups to NE, auto-reset cluster
      reunified, R22/R23 relocated, U1 rotated 180, H1 into the keepout
      corner). Render review happens with the final package (unattended).
- [x] **H2.3 Routing + pours DONE (2026-06-11):** freerouting (official
      container via podman; 115 nets, 26 s) + custom heal pipeline
      (scripts/pcb_router.py grid A*, pcb_finish.py connectivity healer with
      bounded rip-up, orphan-pour-fragment bonding). Dual-layer GND pours,
      antenna keepout rule areas, ~150 stitching vias. Zero splits;
      partition check identical.
- [x] **H2.4 DRC + silkscreen DONE (2026-06-11):** 3 accepted errors (H1 in
      antenna keepout - nylon screw), 7 pour-island notices, silk warnings;
      refs tidied 0.8mm + 23 functional labels (JP1, R21/R26, header pinouts,
      LED meanings, board name + docs URL).
- [x] **H2.5 Review DONE (2026-06-11):** adversarial subagent reviews (BOM,
      fab files, layout) all ran and ALL findings remediated: H-1 SW-node
      direct fat route, H-2 power/IR width upgrade (0.2→0.5 where lanes
      allow, DRC-driven selective neckdowns), M-1 buck B-keepout rule area
      ((104.3,93.5)–(117.5,103.7); see layout.md for why the south edge is
      y=103.7 — BST bootstrap B-jog), M-3 J5 moved clear (121.3,63.9),
      M-4 C10→10µF C19702. M-2 (IR_RX runs along the TX array edge) is a
      documented judgment call — TSOP has its Vs RC filter and 38 kHz AGC;
      acceptable on rev 1. The remediation broke + re-healed several nets
      (BST/JP1-B corridor war, J5-area GPIO22/33, USER_LED2, +5V@J4 missing
      via, 2 undersized healer vias) — final state re-verified from scratch:
      **DRC = 3 accepted errors / 7 pour notices, zero real unconnected,
      schematic parity 0.**

**Gate:** DRC clean, placement/routing reviewed, Nick approves the render.

## Phase H3 — Fabrication *(needs: Mac, Nick, 💰)*

- [x] **H3.1 Outputs DONE (2026-06-11, regenerated for v1.4):**
      `hardware/fab/` has gerbers.zip, JLCPCB BOM (**23 assembled lines,
      only 3 Extended: U1/U2/U3**) + CPL (47 placements, top only) +
      **hand-solder kit CSV** (12 LCSC lines + 2 generic headers; all THT,
      L1/F1/D1/J3, polarity + fit-before-power notes). Regenerate any time
      with `scripts/fab-outputs.py` (the HAND_SOLDER table there is the
      assembly-split source of truth). LCSC codes validated live this
      session via the jlcpcb MCP; **AM2302 stock now 35 units** — order
      soon or substitute.
- [ ] **H3.2 Order checklist for Nick** — **Nick places the order, never
      autonomous.** Suggested package:
  0. Download the fab package from the Pages site (<https://njdancer.github.io/claude-ir/>
     → "Fabrication package") or the `fab-package` CI artifact of the
     main-branch run you're ordering from, then **tag that commit**
     (`git tag order/v1.4 && git push origin order/v1.4`).
  1. JLCPCB: 5× PCB (80×55, 2-layer) + economic SMT assembly ×2, top side,
     upload `esp32-ir-remote-gerbers.zip` + `-jlcpcb-bom.csv` +
     `-jlcpcb-cpl.csv`. Expect ~4 Extended loading fees (~$12 — C17922 18Ω
     flipped to Extended per the CI BOM report) + setup/stencil.
  2. **In the placement preview, walk `esp32-ir-remote-orientation-report.csv`**
     (in the fab package): one row per orientation-critical part (U1, U2,
     U3, Q1-Q5, SW1/2) — confirm each pin-1/polarity marker matches
     final_top.png. The CPL is already rotation-corrected (JLC offsets per
     package), so the preview SHOULD be correct; any mismatch = fix the
     JLC_ROTATION table in `scripts/fab-outputs.py`, regenerate, re-upload.
  3. Same cart: kit parts from `fab/esp32-ir-remote-hand-solder-kit.csv`
     (add spares; 2-3× AM2302 C83988 while stock lasts; generic 2.54mm
     headers for J4/J5).
- [x] **H3.3 DONE early (2026-06-11):** `hardware/bring-up.md` written —
      per-subsystem power-on procedure incl. the rev-1.2 quirks (nylon screw
      at H1, JP1 solder-bridge, J4 6-GPIO note).

**Gate:** boards + parts ordered; bring-up procedure written and reviewed.

## Phase F1 — ESP32 bring-up firmware *(parallel with H2/H3, any environment)*

- [x] **F1.1** `[env:esp32dev]` added to `platformio.ini` (espressif32, pins
      via build_flags: IR TX 18, IR RX 19, user LEDs 16/17). Builds clean.
- [x] **F1.2** `src/main.cpp` builds for both envs (pins from build_flags,
      serial protocol unchanged). Not yet flashed to real hardware.
- [x] **F1.3** Protocol frame builder (`include/bosch144_protocol.h`, pure
      C++) + 18 native tests (`test/test_bosch144_protocol/`) asserting
      byte-for-byte against re-findings tables and IRremoteESP8266 layout.
      Discoveries: byte-17 checksum = sum(bytes 12..16) (was "unknown");
      re-findings 28°C entry likely mislabeled (0x90 vs library 0x80).
      Also fixed: TEMP:x.5 silently truncated to whole degrees — half-degree
      flag (byte 14 bit 5) now patched into the frame before send.
- [ ] **F1.4** Fix the state-model weakness: per-payload (BOSCH144 vs COOLIX)
      freshness tracking instead of blind toggles for swing/boost.
- [ ] **F1.5 Bench verification (Nick, breadboard, ~10 min):**
  - [ ] Flash `pio run -e nodemcuv2 -t upload`; smoke-test POWER/TEMP/MODE
        against the AC (regression check after refactor)
  - [ ] `TEMP:22.5` — AC display should show 22.5 (half-degree fix)
  - [ ] `TEMP:28` — verify AC shows 28 not 27 (resolves the 0x80/0x90
        question; also check `temp-28.txt` when committing captures in H1.0)

**Gate:** ESP32 env builds ✓; native tests pass ✓ (35/35); serial protocol
unchanged ✓; bench regression check pending (F1.5).

## Phase F2 — Production firmware & integration *(after bring-up)*

- [ ] **F2.1 Decision (research first, then ask Nick):** custom HomeKit stack
      vs ESPHome/Home Assistant integration vs Matter. Deliverable: a short
      decision doc with a recommendation. Spec mentions Rust as an aspiration —
      evaluate cost/benefit honestly against esp-idf/Arduino maturity for
      IR + HomeKit.
- [ ] **F2.2** Implement chosen path: WiFi config, climate entity, Follow Me
      (DHT22 feedback loop), OTA updates.
- [ ] **F2.3** Reliability: watchdog, brownout handling, IR send retry policy,
      state resync strategy (periodic full BOSCH144 refresh?).

**Gate:** controlling the AC from a phone, surviving a week unattended.

## Parked / explicitly out of scope for now

- Battery power (deferred to board v2 per spec)
- Humidity/timer/special-function protocol capture (Known Limitations in
  `re-findings.md`) — revisit only if a feature needs them
- circuit.md or any custom hardware description format — decided against
