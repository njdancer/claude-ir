# Roadmap

**Goal:** a fabricated, verified ESP32 IR remote board running reliable
firmware that controls the ActronAir AC, eventually exposed to HomeKit.

This is the project's state file. Update it in every commit that completes,
adds, or reorders work. Conventions: `[ ]` todo, `[x]` done, `[~]` in
progress. Each phase lists its **gate** (what must be true to move on) and
**needs** (Mac = KiCad/serial required; Nick = human action required).

## Now

➡️ **Active phase: H1 — Schematic verification.** Next actions: H1.0 (commit
reference captures — data-loss risk) then H1.1 (run
`./scripts/hardware-check.sh` on the Mac for an ERC baseline).

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

- [ ] **H1.0 Preserve the ground truth (first Mac session, 5 min):** the 60+
      IR captures are gitignored and exist ONLY on Nick's Mac. Copy the key
      reference set (per `re-findings.md` §Capture Files Summary: temp range,
      modes, fan speeds, power, swing, boost, LED) into `captures/reference/`
      (now tracked) and commit. These are irreplaceable protocol fixtures.
- [ ] **H1.1 Baseline:** run `./scripts/hardware-check.sh`; fix any script
      issues; commit regenerated netlist + ERC fixes. Record violation count
      here even if zero.
- [ ] **H1.2 Library hygiene:** resolve known smells found by symbol census:
  - [ ] Two ESP32 symbols present (`RF_Module:ESP32-WROOM-32E` AND custom
        `ESP32-WROOM-32E-Breakout`) — confirm one is orphaned and remove it
  - [ ] Mixed conventions: generic `Device:R`/`Device:C` alongside
        part-specific `PCM_JLCPCB-*` symbols — standardize on generic symbols
        with LCSC part numbers in fields
  - [ ] Verify every symbol has a footprint and LCSC field; cross-check
        against `hardware/esp32-ir-remote_bom.csv` and `hardware/BOM.md`
- [ ] **H1.3 Hierarchical refactor (netlist-gated):** split the flat sheet
      into sub-sheets matching `hardware/notes/` (power, usb-serial, mcu,
      ir-tx, ir-rx, temp-sensor, status-leds). Gate: netlist diff before vs
      after is electrically empty (net names may change; connectivity may not).
- [ ] **H1.4 Adversarial datasheet review:** one subagent per subsystem,
      given only the datasheet (`hardware/datasheets/`) + exported netlist,
      independently re-derives required connections and reports mismatches.
      Specific items the review MUST cover:
  - [ ] ESP32 strapping pins incl. GPIO12/MTDI (flash voltage — must not be
        pulled high at boot) and GPIO6-11 not used as I/O
  - [ ] CH340C: R232 tied LOW, V3/VCC config at 3.3V, decoupling
  - [ ] AP63203: BST cap, inductor rating, input/output caps per datasheet
  - [ ] USB-C: CC pull-downs, VBUS protection ordering (fuse before TVS)
  - [ ] IR MOSFET gate network and LED current math vs TSAL6200 datasheet
  - [ ] Every IC power pin decoupled; every unused input handled
- [ ] **H1.5 Human gate:** export schematic PDF (`kicad-cli sch export pdf`),
      Nick eyeballs it. Findings fixed → ERC clean → netlist committed.

**Gate:** ERC clean, datasheet review findings resolved, Nick has seen the PDF.

## Phase H2 — PCB layout *(needs: Mac)*

66 footprints are imported; 0 tracks routed. Layout is greenfield.

- [ ] **H2.1 Constraints first:** set up JLCPCB 2-layer design rules in the
      board; document placement constraints in `hardware/notes/layout.md`:
      IR LEDs on board edge at 0/45/90/135°, WROOM antenna keepout
      (no copper under antenna, module at board edge), AP63203 switching loop
      tight, USB-C/CH340C short data traces, DHT22 away from heat sources.
- [ ] **H2.2 Placement** per constraints; Nick sanity-checks a 3D render /
      screenshot before routing starts (cheap to move parts now).
- [ ] **H2.3 Routing + ground pour;** power nets sized for 400mA IR + WiFi
      peaks.
- [ ] **H2.4 DRC clean** with JLCPCB rules; silkscreen: labels for jumpers
      (JP1 buck-disable, JP2/JP3 auto-reset), buttons, LED meanings, pin-1s.
- [ ] **H2.5 Review:** exported PDF plots + 3D render reviewed (subagent pass
      for common layout errors, then Nick).

**Gate:** DRC clean, placement/routing reviewed, Nick approves the render.

## Phase H3 — Fabrication *(needs: Mac, Nick, 💰)*

- [ ] **H3.1 Outputs:** gerbers + drill, BOM CSV + CPL in JLCPCB format;
      verify part stock at JLCPCB/LCSC; note any hand-solder-only parts
      (THT LEDs, headers, DHT22, TSOP).
- [ ] **H3.2 Order checklist for Nick:** board qty, assembly option, expected
      cost. **Nick places the order** — never order anything autonomously.
- [ ] **H3.3 While boards ship:** write `hardware/bring-up.md` — per-subsystem
      power-on test procedure (what to probe, expected values, in what order:
      bare power → buck output → USB enumeration → flash blink → serial →
      IR loopback → AC test), so bring-up day is execution, not improvisation.

**Gate:** boards + parts ordered; bring-up procedure written and reviewed.

## Phase F1 — ESP32 bring-up firmware *(parallel with H2/H3, any environment)*

- [ ] **F1.1** Add `[env:esp32]` to `platformio.ini` (espressif32, WROOM-32E,
      pins per `hardware/notes/README.md`: IR TX 18, IR RX 19, DHT22 4,
      user LEDs 16/17).
- [ ] **F1.2** Port `src/main.cpp` to build for both envs (pin/board
      abstraction, keep serial protocol identical so the web app works
      unchanged). IRremoteESP8266 supports ESP32.
- [ ] **F1.3** Host-side protocol codec tests: encode (temp, mode, fan) →
      bytes, assert byte-for-byte against `re-findings.md` byte maps; round
      trip decode. Runs in `pio test -e native`, using `captures/reference/`
      (populated by H1.0) plus the byte maps in `re-findings.md` as fixtures.
- [ ] **F1.4** Fix the state-model weakness: per-payload (BOSCH144 vs COOLIX)
      freshness tracking instead of blind toggles for swing/boost.

**Gate:** ESP32 env builds; native tests pass; serial protocol unchanged.

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
