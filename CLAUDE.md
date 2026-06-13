# CLAUDE.md

ESP32/ESP8266 smart controller for an ActronAir (rebranded Midea) air
conditioner. The IR protocol is fully reverse-engineered and breadboard
transmission to the real AC works. Current mission: get the custom ESP32 dev
board (`hardware/`) to a fabricated, verified, working unit, then build the
production firmware on it.

## How to work in this repo

**Take charge.** The owner (Nick) has asked Claude to drive this project to
completion. Don't wait for direction:

1. **Start every session** by reading `ROADMAP.md` and `git log --oneline -10`.
2. Continue the first unchecked item in the active phase. If a session ended
   mid-task, the roadmap's "Now" section says exactly where.
3. **Update `ROADMAP.md` as part of every commit** that completes or changes
   work — it is the project's state file and must never go stale.
4. Commit early and often with descriptive messages. Everything is in git;
   bold moves are recoverable, silent stalls are not.
5. Only stop to ask when (a) money is about to be spent (fab orders, parts),
   (b) a decision genuinely changes project direction, or (c) hardware
   interaction is needed. Batch hardware requests into one clear,
   numbered checklist — Nick's bench time is the scarcest resource.

**Don't repeat the circuit.md mistake.** No new file formats, DSLs, or
meta-tooling unless it directly de-risks the board AND has a machine
validator. Prefer existing tools (KiCad, kicad-cli, PlatformIO, pytest/Unity)
over inventing anything.

## Sources of truth

| Artifact | Truth for | Notes |
|----------|-----------|-------|
| `hardware/*.kicad_sch` / `.kicad_pcb` | The board design | Edit only via KiCad (GUI or kicad-cli/MCP); never hand-edit s-expressions unless surgically necessary |
| `hardware/esp32-ir-remote.net` | Reviewable electrical state | Regenerate with `scripts/hardware-check.sh` after EVERY schematic change; commit alongside |
| `hardware/notes/*.md` | Design rationale only | If a note contradicts the schematic, the schematic wins — fix the note |
| `specs/hardware-dev-board-v1.md` | Board requirements | RFC-style spec; update via `spec-writing` skill conventions |
| `re-findings.md` | IR protocol knowledge | BOSCH144 + COOLIX, byte maps, timings |
| `ROADMAP.md` | Project state & next actions | Living document, update constantly |

**Schematic change ritual:** edit → `./scripts/hardware-check.sh` (ERC must
pass) → review the netlist diff (`git diff hardware/esp32-ir-remote.net`) →
commit schematic + netlist together. Refactors (e.g. hierarchical sheets)
must produce an electrically-empty netlist diff.

**CI is the authoritative gate** (`.github/workflows/ci.yml`): every PR runs
ERC/DRC vs `hardware/ci-baseline.json`, the netlist partition-freshness
check, schematic↔PCB parity, BOM LCSC lint, firmware builds + native tests,
and app typecheck/unit/e2e — open a PR and watch CI rather than re-running
the battery by hand. Local scripts remain for fast feedback only. If a
design change legitimately alters accepted ERC/DRC counts, refresh the
baseline inside the CI KiCad image (`kicad/kicad:10.0.2`):
`python3 scripts/ci/hardware_validate.py --update-baseline` and commit it
with the change. Build artifacts (`hardware/fab/`, generated BOM CSVs) are
gitignored — CI regenerates them on every PR (artifact upload) and the
Pages deploy publishes them on every merge; freeze an order package by
tagging the ordered commit (e.g. `order/v1.4`).

## Environments

**Nick's Mac (primary for hardware work):**
- KiCad 9 installed: `kicad-cli` found automatically by
  `scripts/hardware-check.sh` (app bundle path); kicad MCP server configured
  in `.mcp.json` for netlist/connection queries.
- Serial/USB works: `./scripts/flash.sh`, `./scripts/monitor.sh`,
  `python3 scripts/capture.py <label>`.
- Firmware builds run in the podman devcontainer (`pio run`); flash/monitor
  run on the host (USB passthrough doesn't work under podman/macOS).

**Remote/web sessions (no KiCad, no serial):** firmware, analysis, app code,
docs, research, and planning only. Don't attempt KiCad operations; queue them
in `ROADMAP.md` for a Mac session instead.

## Commands

```bash
pio run                          # build ESP8266 firmware (devcontainer or host)
pio test -e native               # host-side unit tests
./scripts/flash.sh               # flash from macOS host
./scripts/monitor.sh             # serial monitor (115200)
python3 scripts/capture.py <lbl> # capture one IR signal to captures/
python3 analysis/decoder.py      # analyze capture corpus
./scripts/hardware-check.sh      # ERC + regenerate netlist (needs kicad-cli)
python3 scripts/ci/hardware_validate.py  # full design gate (what CI runs)
python3 scripts/ci/bom_report.py # BOM cost/stock from JLCPCB API
python3 scripts/fab-outputs.py   # regenerate JLCPCB order package (gitignored)

cd app && pnpm dev               # web control UI (React Router)
cd app && pnpm test              # vitest unit tests
cd app && pnpm test:e2e          # playwright e2e
```

## Key technical facts

- **Protocols:** BOSCH144 (144-bit, climate state: power-on/temp/mode/fan) and
  COOLIX (24-bit, discrete commands: power-off 0xB27BE0, swing, boost, LED).
  Both natively supported by IRremoteESP8266. Full byte maps in
  `re-findings.md`.
- **Two-payload architecture:** the remote is NOT state-based. BOSCH144 and
  COOLIX carry disjoint attributes, so AC state can be partially stale after
  any single command. Firmware state models must track per-payload freshness
  and must not assume one command syncs everything (see `src/main.cpp`'s
  blind swing/boost toggles — a known weakness to fix in the ESP32 firmware).
- **Breadboard (working reference):** ESP8266 NodeMCU, IR RX on GPIO14 (D5),
  IR TX on GPIO4 (D2) via 2N2222. Wiring in `wiring.md`.
- **ESP32 board:** GPIO map and per-subsystem rationale in
  `hardware/notes/README.md`. Schematic ~complete; PCB layout not started.
