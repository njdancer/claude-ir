# Roadmap

**Goal:** a fabricated, verified ESP32 IR remote board running reliable
firmware that controls the ActronAir AC, eventually exposed to HomeKit.

This is the project's state file. Update it in every commit that completes,
adds, or reorders work. Conventions: `[ ]` todo, `[x]` done, `[~]` in
progress. Each phase lists its **gate** (what must be true to move on) and
**needs** (Mac = KiCad/serial required; Nick = human action required).

## Now

➡️ **Active phase: H1 — Schematic verification.** H1.0 done (28 protocol
fixtures preserved in `captures/reference/`). Next action: H1.1 — run
`./scripts/hardware-check.sh` on the Mac for an ERC baseline and commit the
regenerated netlist. F1.1–F1.3 are already done; F1.5 lists a ~10-minute
breadboard check for whenever the ESP8266 is plugged in (no ESP board was on
USB this session — only Bluetooth/Cricut serial ports present).

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
