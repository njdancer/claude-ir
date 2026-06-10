# Roadmap

**Goal:** a fabricated, verified ESP32 IR remote board running reliable
firmware that controls the ActronAir AC, eventually exposed to HomeKit.

This is the project's state file. Update it in every commit that completes,
adds, or reorders work. Conventions: `[ ]` todo, `[x]` done, `[~]` in
progress. Each phase lists its **gate** (what must be true to move on) and
**needs** (Mac = KiCad/serial required; Nick = human action required).

## Now

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
- [~] **H1.2 Library hygiene:** census done this session; edits pending
      (KiCad GUI / surgical):
  - [x] ~~Two ESP32 symbols~~ **NOT an orphan — no removal.** `RF_Module:ESP32-
        WROOM-32E` = U3 (the MCU, 39 nodes). The second symbol is **J1**, an
        intentional *DevKitC debug breakout header* ("Debug breakout header
        matching ESP32-DevKitC V4 pinout", 2×19 pin-header footprint, 38 pins
        mirroring U3's GPIOs). Keep both. H1.4 should verify J1↔U3 pin mapping
        matches the real DevKitC pinout.
  - [ ] **Convention cleanup (8 symbols):** 6 resistors use
        `PCM_JLCPCB-Resistors` and 2 transistors use `PCM_JLCPCB-Transistors`;
        everything else uses generic `Device:*` (44 symbols). Standardize the
        8 onto generic symbols carrying LCSC in fields. *KiCad GUI edit.*
  - [ ] **LCSC backfill (15 of 65 comps), KiCad GUI edit — mapping
        pre-computed below.** All 65 comps have footprints ✓; 15 lack an LCSC
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
  - [ ] **Kill the dual-BOM problem:** after the schematic carries all LCSC
        fields, regenerate the BOM from it (`kicad-cli sch export bom` / the
        kicad MCP) so `esp32-ir-remote_bom.csv` is complete, then either delete
        `hardware/BOM.md` or demote it to rationale-only (it currently
        disagrees with the schematic on designators, R15 value, R21 identity,
        J1/J2, and JP2/JP3 — all already correct in the schematic).
  - [ ] **Spec reconciliation (schematic wins):** `specs/hardware-dev-board-v1.md`
        §Auto-Reset + BOM still describe JP2/JP3 header bypass jumpers, but the
        schematic uses R21/R26 0Ω SMD links (already fixed in
        `hardware/notes/usb-serial.md`). Update the spec via the `spec-writing`
        skill: §Auto-Reset diagram/table, BOM jumper row, and the
        jumper-config summary. Also fix the stale "JP2/JP3" silkscreen note in
        H2.4 below.
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
  - [ ] **HIGH:** R13 gate resistor 10kΩ → ~330Ω–1kΩ (10k too slow for 38kHz IR).
  - [ ] **MED:** L1 → 4.7µH (decided above); add TSOP Vs RC filter (~100Ω+100nF).
  - [ ] **LOW:** D7 green 150Ω→470Ω–1k; confirm J1 GPIO6-11 breakout intent;
        remove redundant PWR_FLAG on U2 V3 (clears the 1 ERC error); firmware
        guard vs stuck-high IR_TX.
  - [x] Replaced 3 broken (HTML-saved) datasheet PDFs with genuine vendor PDFs;
        YAGEO 100nF cap one still HTML (generic passive, low priority).
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
