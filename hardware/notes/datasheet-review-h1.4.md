# H1.4 — Adversarial datasheet review

Per-subsystem review (2026-06-10): one agent per subsystem independently
re-derived required connections from the part datasheet, then diffed against the
exported netlist. The schematic is the source of truth. Findings below are
**verified** — the orchestrator re-checked every ERROR/HIGH item against the
netlist directly (one agent's "showstopper" was a false positive; see note).

## Verified clean (no change needed)

- **Power (U1 AP63203WU):** TSOT-23-6 pinout correct (VIN=3, GND=4, SW=5, BST=6,
  EN=2, FB=1). C4 100nF bootstrap SW→BST ✓. Input C1 10µF, output C2+C3 22µF ✓
  (matches datasheet typical). Fixed-3.3V part: FB tied to output, no external
  divider ✓. JP1 (2-pad solder jumper) pulls EN→GND to disable buck; EN floats
  high via internal pull-up otherwise ✓.
- **VBUS protection ordering:** `J2 VBUS → F1 fuse → +5V rail (D1 TVS clamps to
  GND here) → U1 VIN`. Fuse is **before** the TVS — the correct/recommended
  order. ✓
- **USB-serial (U2 CH340C):** V3 tied to VCC on +3.3V ✓; R232 (pin 15) tied to
  GND → TTL output mode ✓; UD+/UD- → J2 D+/D- (both orientations shorted) ✓;
  TXD→GPIO3 / RXD←GPIO1 crossed correctly ✓. (Note: R232-high inverts RXD, it
  does **not** raise output voltage — the "RS232 damages ESP32" framing in older
  notes is imprecise, but grounding R232 is still correct.)
- **USB-C (J2):** CC1/CC2 each have a 5.1kΩ Rd pull-down to GND (R1/R2) → correct
  UFP/device config ✓; all four VBUS pins commoned and fused ✓; shield→GND ✓.
- **Auto-reset (Q1/Q2):** correctly wired classic cross-coupled circuit
  (see false-positive note). ✓
- **MCU strapping (U3 ESP32-WROOM-32E):** GPIO12/MTDI has NO pull-up (only U3 +
  J1 pad) → flash-voltage strap safe ✓; GPIO0 pull-up R6 + BOOT/auto-reset ✓;
  EN pull-up R5 + C6 1µF RC (~10ms POR) ✓; GPIO2 pull-down R7, GPIO15 pull-down
  R8 ✓. All GND pins tied ✓.
- **IR-RX (U4 TSOP38238):** pinout OUT/GND/Vs correct ✓; output has internal 30k
  pull-up, no external pull-up needed/added ✓.
- **Temp (U5 AM2302/DHT22):** VDD→3.3V, DATA→GPIO4, GND✓; DATA pull-up R22 10kΩ
  present ✓; NC pin grounded (accepted practice) ✓.
- **Status LEDs:** all 7 LEDs have series resistors, current math sane (~1.5–9mA),
  no GPIO exceeds sink/source limits; blue D11/D12 driven from +5V via 2N7002
  low-side (Q4/Q5) with 100kΩ gate pulldowns (off at boot) ✓; IR-TX MOSFET
  topology (Q3 low-side, gate pulldown R14) ✓; IRLML6344 is logic-level, fully
  enhanced at 3.3V, Id 5A ≫ 0.42A load ✓.

## Action items (real, verified)

| # | Sev | Subsystem | Finding | Action |
|---|-----|-----------|---------|--------|
| 1 | HIGH | IR-TX | **R13 = 10kΩ gate series resistor is too high for the 38kHz carrier.** With IRLML6344 Ciss≈620pF, τ≈6µs and gate reaches good enhancement only ~8µs into each ~13µs half-period — the FET sits in its linear region much of each cycle, cutting IR output and heating Q3. | Lower R13 to ~330Ω–1kΩ. *(GUI edit)* |
| 2 | MED | Power | **L1 = 3.9µH** is within the AP63203 range (2.2–10µH) but 4.7µH is the datasheet typical and has far better JLCPCB **Basic** stock at the needed rating. | Switch L1 → **4.7µH**, Isat ≥~2.7A, DCR <100mΩ; pick a Basic part. Resolves the open L1 question. *(GUI + LCSC)* |
| 3 | MED | IR-RX | **TSOP38238 Vs has no RC supply filter** — only the shared-rail 100nF. Vishay recommends ~100Ω series + ≥100nF local cap; the high-current IR-TX shares the 3.3V rail, which is exactly the spike source this guards. | Add ~100Ω series + 100nF local cap at U4 Vs. *(GUI edit, adds R+C)* |
| 4 | LOW | MCU | GPIO6–11 (module-internal SPI-flash pins) are broken out on the J1 DevKitC header. Firmware uses only GPIO16/17/18/19, so unused — but confirm exposing them on J1 is intentional and they are never routed as I/O. | Confirm at H1.5 / layout. |
| 5 | LOW | Status LED | **D7 green uses 150Ω (~8.7mA)** vs the 470Ω/1kΩ used everywhere else — ~3× brighter, looks unintentional. | Consider 470Ω–1kΩ. *(GUI edit, minor)* |
| 6 | LOW | IR-TX | IR LEDs run ~95–105mA each (3.3V, 18Ω, 4 parallel ≈ 0.42A burst) — relies on the TSAL6200 **pulsed** rating (fine for IR bursts), but a stuck-high `IR_TX` GPIO would exceed the 100mA DC max. AP63203 (2A) sources the 0.42A burst with margin. | Add a firmware/HW guard against sustained IR_TX high. *(F-phase)* |
| 7 | LOW | repo | 4/5 local "datasheet" PDFs were saved LCSC **HTML** pages. Replaced the ESP32, TSOP38238 and TSAL6200 files with genuine vendor PDFs; the YAGEO 100nF cap one is still HTML (generic passive, low priority). | YAGEO PDF when convenient. |
| 8 | — | (→H1.2) | Cap voltage ratings unspecified (input C1 should be ≥16V on the 5V rail); D1 is a generic `D_TVS` symbol, not the SMBJ5.0A. | Fold into the H1.2 LCSC backfill / part-spec pass. |

The H1.1 ERC error (PWR_FLAG on CH340C V3 = U2.4) is **benign**: V3 is correctly
tied to VCC on +3.3V (item above); the flag is the redundant-flag-on-power-output
pattern. Remove/relocate the PWR_FLAG to clear the ERC error during the GUI pass.

## Note: false positive caught by verification

The USB-serial agent reported a "showstopper" — Q1/Q2 auto-reset transistor
**bases floating, auto-reset non-functional.** Direct netlist re-check **refutes
it.** The base nets each have two nodes (the agent's parse missed the resistor):
`Q1.B ←R3(10kΩ)← {Q2.E, DTR via R21}`, `Q1.C→EN`, `Q1.E→{RTS via R26}`;
`Q2.B ←R4(10kΩ)← {Q1.E, RTS via R26}`, `Q2.C→GPIO0`, `Q2.E→{DTR via R21}`. This
is the documented cross-coupled circuit (emitters tied to the opposite DTR/RTS
signal, not GND) and matches `usb-serial.md`'s truth table. It is finicky by
nature — bench-verify auto-bootload during bring-up (H3.3 procedure).
