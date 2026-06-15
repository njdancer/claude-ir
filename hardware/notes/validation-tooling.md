# Validation/fab tooling: adopt KiBot

**Status (2026-06-15): DONE — gate + ibom adopted; fab deliberately kept.**

- ✅ **KiBot owns the ERC/DRC error gate** in CI (its preflights fail on real
  violations). `hardware_validate.py` keeps the bespoke checks (netlist
  freshness, polarity truth table, page-extent, BOM-LCSC) + parity/unconnected
  and still emits the PR-report count facts.
- ✅ **Version-drift killed.** WARNING-severity baseline count changes
  (lib/silk heuristics that drift across KiCad patch releases) are now
  informational, not failures. Errors + parity/unconnected (version-stable)
  still gate. (Answers the 10.0.3↔10.0.2 drift question directly.)
- ✅ **InteractiveHtmlBom** generated in CI into the fab package.
- 🟰 **Fab outputs stay in `scripts/fab-outputs.py`** — a deliberate decision,
  not a TODO. Its assembly-split logic (the hand-solder kit, no-LCSC→DNP, the
  kit CSV + orientation report, the "refuse to emit on an unclassified
  footprint" safety guard) is genuinely project-specific, and the only KiBot
  win there — its built-in JLC rotation DB — can't be trusted without the
  dead-board gate below. Migrating would mean re-implementing the safe custom
  logic to *maybe* save a tiny rotation table. Revisit only if a future part
  makes the rotation table painful.

The schematic instance-path bug that blocked KiBot is fixed (see below).

Same "shoulders of giants" pass as the FreeRouting one: our CI gate
(`scripts/ci/hardware_validate.py`) and fab generation (`scripts/fab-outputs.py`,
`bom_report.py`, the `pcb_checks.py`/`pcb_metrics.py` geometry parsers) reinvent
a lot that **KiBot** + native KiCad rules already do.

## Recommendation

| We hand-rolled | Adopt |
|---|---|
| ERC/DRC/parity gate + `ci-baseline.json` counts (`hardware_validate.py`) | **KiBot** `erc`/`drc` preflights (fail on errors; allow-list noise via `filters:`) |
| Gerbers/drill/pos/BOM + hand-maintained JLC rotation tables (`fab-outputs.py`) | **KiBot** outputs + built-in `rot_footprint` DB → retire `fab-outputs.py` |
| Interactive BOM (none today) | **InteractiveHtmlBom** (KiBot `ibom` output) — useful for the hand-solder kit |
| Geometry checks (`pcb_checks.py`) | mostly **already native** — see below |

**Stays bespoke Python** (no standard tool expresses these): netlist
partition-freshness, the polarity/orientation truth table (our best dead-board
catcher), schematic page-extent, LDO thermal **copper-area** (DRU has no
area constraint), and `bom_report.py` (LCSC/JLC-specific; KiCost has no LCSC).

### `.kicad_dru` is narrower than the research assumed

The project's `design_settings` (in `.kicad_pro`) already enforce edge clearance
(0.2), via/track/hole minimums, silk, text height etc. via native
`kicad-cli pcb drc`, and `antenna_keepout` is a real keepout rule-area
(FreeRouting + DRC already honour it — 0 intrusions). FreeRouting also respects
the per-netclass widths (Power 0.6 / IR_Drive 0.5 / Default 0.2, verified). So
the only genuinely *additive* DRU rules would be **per-netclass minimum track
width** (catch a manually-narrowed Power/IR track) and a **USB diff-pair**
gap/skew rule. Low value for this board — fold into the KiBot work, not urgent.

## ✅ RESOLVED — schematic instance-path inconsistency (was the blocker)

KiBot 1.9.0 (pip, `--no-compile` + `lxml`/`requests`/`pyyaml`/`colorama`/
`qrcodegen`) installs and the config is correct, but it **crashes parsing our
schematic**: `v6_sch.py load_project → instances[0].path.split('/')[0]`
IndexError. Cause: **16 of the v2-redesign symbols** (U1, U3, U5, J4, J5, R7,
R8, R20, R25, R27–R30, JP1, + 2 power flags) carry instance `(path "/")`
instead of the root-sheet UUID `(path "/09f96520-…-04cd")` that the other 61
symbols use. KiCad itself tolerates the mix; KiBot's stricter parser does not.

This is a genuine latent schematic bug from the v2 re-architecture, not just a
KiBot quirk. **Do NOT hand-edit it:** normalizing the paths by hand *changes the
netlist* (U5's NC pads gain `unconnected-(U5-NC-Pad1/6)` nets → schematic-parity
19→21), so it must be done by **re-saving the schematic in KiCad 10** (Nick's
Mac), which will normalize the paths the canonical way. Heads-up: that re-save
**will change the committed netlist** (regenerate `esp32-ir-remote.net` + refresh
the parity/netlist baseline in the same commit) — expect the 2 U5 NC nets.

## Plan once unblocked

1. Re-save schematic in KiCad 10 (normalizes instance paths) → regenerate `.net`
   + refresh baseline. Confirm KiBot parses it.
2. `hardware/esp32-ir-remote.kibot.yaml` (staged): `erc` + `drc`
   (`schematic_parity`) preflights + `ibom`; then `gerber`/`excellon`/`position`/
   `bom`/zip with `rot_footprint`. **CPL ROTATION IS THE DEAD-BOARD GATE:** KiBot's
   built-in DB disagrees with `fab-outputs.py` (KiBot `^SOT-23→180` vs ours `270`;
   USB-C offset Y-axis vs our X-axis). Feed KiBot **our** validated
   `JLC_ROTATION`/`JLC_OFFSET` table (via `rot_footprint` `rotations:`/`offsets:`)
   and **diff KiBot's CPL against `fab-outputs.py`'s** before trusting it — a
   blind switch could flip Q3 (AO3400A) or shift the USB-C connector.
3. Slim `hardware_validate.py` to the 3 bespoke checks wrapping KiBot's exit code;
   retire `fab-outputs.py`; keep `bom_report.py`.
4. CI: swap `kicad/kicad:10.0.2` → pinned `ghcr.io/inti-cmnb/kicad10_auto[_full]`
   by digest; `kibot -c …`. (Confirm a published k10.0.2/10.0.3 KiBot image.)

## Env (this container)

KiBot 1.9.0 in `/tmp/kv10` (install with `pip install --no-compile kibot` then
`pip install --no-compile lxml requests pyyaml colorama qrcodegen`; delete any
`*.pyc` under `site-packages/kibot`). Run with `/tmp/kv10/bin/kibot`.
