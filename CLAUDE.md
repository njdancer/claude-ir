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

**Stand on the shoulders of giants — don't reinvent the wheel.** Before
writing a home-grown tool for anything non-trivial (routing, validation,
BOM/fab generation, geometry checks, simulation), STOP and check whether the
community already has a mature, widely-used solution. We learned this the hard
way: a hand-rolled greedy autorouter + rip-up "finisher" never converged on a
congested 2-layer board and was replaced by **FreeRouting** (negotiated
congestion), which routed it cleanly in seconds. The bar for building our own
is high: it must be genuinely unavailable in the ecosystem, or every existing
option must be inadequate for a reason we can articulate. Default to adopting
and wiring in (KiCad-native rules, FreeRouting, KiBot, ngspice, …) over
authoring bespoke logic. When you do find we've rolled our own where a standard
tool exists, flag it — there are probably more such opportunities lurking.

**Persevere on long tasks — don't stall, don't self-truncate.** Big jobs
(re-layouts, migrations, sweeps) are expected to span many tool calls and
even multiple context windows. Keep going until the work is actually done:
- Don't stop early, ask to "continue later", or wrap up just because a lot
  has happened. Don't fear running out of context — the session
  auto-compacts and hands you a summary to continue from; a mid-task compact
  is normal, not a reason to rush or cut scope.
- **Commit AND push after every meaningful increment** (a working sub-step,
  a green validator run) so progress is durable and visible — pushes to the
  working branch are pre-authorised for this kind of multi-step work. Keep
  `ROADMAP.md` updated in those commits so a fresh session can resume exactly
  where you left off.
- **Delegate parallelisable, self-contained sub-tasks to subagents** (the
  Agent tool) — e.g. extracting an asset, drafting a script, a focused
  search — to move faster, then integrate and verify their output yourself.
- Only stop for the genuine gates above (money / direction / bench time).
  "This is taking a while" is not a gate.

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
