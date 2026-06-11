# ESP32 IR Remote - Bill of Materials (HISTORICAL — do not order from this)

> **⚠️ DEMOTED 2026-06-11.** This hand-curated document is **stale**: it
> disagrees with the schematic on reference designators (it predates the
> v1.2 changes: J1 removed, J3–J6 added, R27–R30 added) and carried several
> wrong LCSC codes that have since been fixed in the schematic (R13/R22 had
> the 18Ω code, Q3 had the 2N7002 code, R14/R15 had 0805 codes on 1206
> footprints). **The schematic is the single source of truth for parts;
> the generated [`esp32-ir-remote_bom.csv`](esp32-ir-remote_bom.csv)
> (regenerate via `kicad-cli sch export bom`, see `scripts/build-site.sh`)
> is the orderable BOM.** This file is kept only for the part-selection
> rationale and supplier notes below.

## Status

- [x] Power - complete
- [x] USB-UART - complete
- [x] ESP32 & Auto-Reset - complete
- [x] IR Transmitter - complete
- [x] IR Receiver & Sensors - complete
- [x] Status LEDs - complete
- [x] Headers & Mechanical - complete

## Preferences

- **Passives**: Through-hole preferred
- **LCSC**: Basic or Extended OK

---

## 1. Power Subsection

| Ref   | Description    | Value         | LCSC Part | Stock    | Datasheet | Verified | Notes                             |
| ----- | -------------- | ------------- | --------- | -------- | --------- | -------- | --------------------------------- |
| U5    | Buck Converter | AP63203WU-7   | C780769   | 3838     | local     | ✓        | Fixed 3.3V, TSOT-23-6             |
| D1    | TVS Diode      | SMBJ5.0A      | C83333    | 71460    |           | ✓        | Littelfuse, DO-214AA, 5V standoff |
| F1    | Polyfuse       | 1812L110/33MR | C142747   | 62380    |           | ✓        | Littelfuse, 1.1A hold, 1812 SMD   |
| L1    | Inductor       | SRP5030T-4R7M | C2045677  | 222      |           | ✓        | BOURNS, 4.7µH, 4.6A, 5x5mm        |
| C1    | Input Cap      | 10µF 16V X5R  | C18185764 | 413200   |           | ✓        | CCTC, 0805 MLCC                   |
| C2,C3 | Output Cap     | 22µF 16V X5R  | C98190    | 1694250  |           | ✓        | Samsung, 0805 MLCC, qty 2         |
| C4    | Bootstrap Cap  | 100nF 50V X7R | C1591     | 20454800 |           | ✓        | Samsung, 0603 MLCC                |

---

## 2. USB-UART Subsection

| Ref   | Description     | Value        | LCSC Part | Stock    | Datasheet | Verified | Notes                      |
| ----- | --------------- | ------------ | --------- | -------- | --------- | -------- | -------------------------- |
| U2    | USB-UART Bridge | CH340C       | C84681    | 12199    |           | ✓        | WCH, SOP-16                |
| J1    | USB-C Connector | USB4085-GF-A | C7095263  | 342      |           | ✓        | GCT, through-hole USB-C    |
| R1,R2 | CC Resistors    | 5.1kΩ 1%     | C26033    | 230100   |           | ✓        | UNI-ROYAL, 1206 SMD, qty 2 |
| C9    | V3 Decoupling   | 100nF 50V    | C1591     | 20454800 |           | ✓        | Samsung, 0603 (same as C4) |

---

## 3. ESP32 & Auto-Reset Subsection

| Ref           | Description    | Value              | LCSC Part | Stock   | Datasheet | Verified | Notes                  |
| ------------- | -------------- | ------------------ | --------- | ------- | --------- | -------- | ---------------------- |
| U1            | ESP32 Module   | ESP32-WROOM-32E-N4 | C701341   | 1001    | local     | ✓        | ESPRESSIF, 4MB flash   |
| Q1,Q2         | N-MOSFET       | 2N7002             | C8545     | 779450  |           | ✓        | CJ, SOT-23, qty 2 (v1.3: was S8050 NPN; shares line with Q4,Q5) |
| C6            | EN Delay Cap   | 1µF 16V X5R        | C52923    | 1182500 |           | ✓        | Samsung, 0805 MLCC     |
| R4,R5,R17,R18 | Pull-ups/Base  | 10kΩ 1%            | C17902    | 896900  |           | ✓        | UNI-ROYAL, 1206, qty 4 |
| SW1,SW2       | Tactile Switch | TS-1088R-02026     | C455280   | 52750   |           | ✓        | XUNPU, 6x6mm TH, qty 2 |

---

## 4. IR Transmitter Subsection

| Ref           | Description   | Value     | LCSC Part | Stock   | Datasheet | Verified | Notes                        |
| ------------- | ------------- | --------- | --------- | ------- | --------- | -------- | ---------------------------- |
| D2,D3,D4,D5   | IR LED        | TSAL6200  | C55528    | 955     |           | ✓        | Vishay, 940nm 5mm TH, qty 4  |
| Q3            | N-ch MOSFET   | IRLML6344 | C5364313  | 38870   |           | ✓        | Hottech, SOT-23, logic-level |
| R3,R6,R10,R12 | LED Current   | 18Ω 1%    | C711458   | 75600   |           | ✓        | FOJAN, 1206, qty 4           |
| R7            | Gate Resistor | 10kΩ 1%   | C17902    | 896900  |           | ✓        | (same as pull-ups)           |
| R8            | Gate Pulldown | 100kΩ 1%  | C25803    | 1034300 |           | ✓        | UNI-ROYAL, 1206              |

---

## 5. IR Receiver & Sensors Subsection

| Ref | Description   | Value     | LCSC Part | Stock    | Datasheet | Verified | Notes                         |
| --- | ------------- | --------- | --------- | -------- | --------- | -------- | ----------------------------- |
| U3  | IR Receiver   | TSOP38238 | C141632   | 2829     |           | ✓        | Vishay, 38kHz, 3-pin TH       |
| U4  | Temp/Humidity | AM2302N   | C6705248  | 1680     |           | ✓        | VBsemi, DHT22 compatible      |
| C7  | Decoupling    | 100nF 50V | C1591     | 20454800 |           | ✓        | Samsung, 0603 (same as C4,C9) |

---

## 6. Status LEDs Subsection

All indicator LEDs are 3mm through-hole Everlight 204 series. Target brightness: ~15-30 mcd.
- Power rail LEDs: direct-driven from rails
- TX/RX LEDs: direct-driven active-low from 3.3V to GPIO
- IR TX LED: direct-driven active-high from GPIO
- Blue user LEDs: MOSFET low-side switching from 5V (Vf=3.4V requires 5V supply)

### 6a. 3mm LEDs

| Ref     | Description     | Value               | LCSC Part | Stock  | Vf   | Iv@20mA | Notes                     |
| ------- | --------------- | ------------------- | --------- | ------ | ---- | ------- | ------------------------- |
| D6      | 5V Power LED    | 204-10SURD/S530-A3  | C99772    | 14860  | 2.0V | 80mcd   | Everlight, 3mm Red        |
| D7      | 3.3V Power LED  | 204-10SYGD/S530-E3  | C85161    | 66860  | 2.0V | 100mcd  | Everlight, 3mm Y-Green    |
| D8,D9   | Serial TX/RX    | 204-10UYD/S530-A3-L | C85160    | 103440 | 2.0V | 200mcd  | Everlight, 3mm Amber ×2   |
| D10     | IR TX Indicator | 204-10SURD/S530-A3  | C99772    | 14860  | 2.0V | 80mcd   | Everlight, 3mm Red        |
| D11,D12 | User LEDs       | 204-10SUBC/S400-A4  | C86881    | 33130  | 3.4V | 800mcd  | Everlight, 3mm Blue ×2    |

### 6b. LED Driver MOSFETs (for blue LEDs only)

| Ref   | Description | Value  | LCSC Part | Stock  | Notes                     |
| ----- | ----------- | ------ | --------- | ------ | ------------------------- |
| Q4,Q5 | LED Drivers | 2N7002 | C8545     | 798650 | JSCJ, SOT-23, N-ch, qty 2 |

### 6c. LED Resistors

Target: ~20-30 mcd brightness. Using only 470Ω and 1kΩ to minimize unique parts.

| Ref     | Description        | Value    | LCSC Part | Stock   | Current | ~mcd | Notes                    |
| ------- | ------------------ | -------- | --------- | ------- | ------- | ---- | ------------------------ |
| R15     | 5V LED Resistor    | 1kΩ 1%   | C4410     | 870400  | 3.0mA   | 12   | UNI-ROYAL 1206           |
| R16     | 3.3V LED Resistor  | 470Ω 1%  | C4502     | 53000   | 2.8mA   | 14   | UNI-ROYAL 1206           |
| R17,R18 | TX/RX Resistors    | 470Ω 1%  | C4502     | 53000   | 2.8mA   | 28   | UNI-ROYAL 1206, qty 2    |
| R19     | IR TX LED Resistor | 470Ω 1%  | C4502     | 53000   | 2.8mA   | 11   | UNI-ROYAL 1206           |
| R20,R21 | Blue LED Resistors | 1kΩ 1%   | C4410     | 870400  | 1.6mA   | 64   | UNI-ROYAL 1206, qty 2    |
| R23,R24 | Gate Pulldowns     | 100kΩ 1% | C25803    | 1034300 | -       | -    | UNI-ROYAL 1206, qty 2    |

**Note**: Only 3 unique resistor values for LEDs: 470Ω, 1kΩ, 100kΩ. Blue LEDs brighter due to InGaN efficiency.

---

## 7. Headers & Mechanical

| Ref     | Description       | Value       | LCSC Part | Stock  | Datasheet | Verified | Notes                        |
| ------- | ----------------- | ----------- | --------- | ------ | --------- | -------- | ---------------------------- |
| J2      | Breakout Header   | 2x20 Female | C50982    |        |           | ✓        | BOOMELE, 2.54mm, cut to 2x19 |
| JP1     | Buck Disable      | 1x2 Male    | C124375   |        |           | ✓        | Ckmtw, 2.54mm TH             |
| JP2,JP3 | Auto-reset Bypass | 1x2 Male    | C124375   |        |           | ✓        | qty 2 (same as JP1)          |
| -       | Jumper Shunts     | 2.54mm      | C5305     | 165800 |           | ✓        | BOOMELE, qty 2-3             |

---

## Summary

| Category       | Unique Parts | Total Qty |
| -------------- | ------------ | --------- |
| ICs            | 5            | 5         |
| Transistors    | 2            | 3         |
| Diodes/LEDs    | 6            | 12        |
| Capacitors     | 4            | 9         |
| Resistors      | ~7           | ~22       |
| Inductors      | 1            | 1         |
| Connectors     | 2            | 2         |
| Switches       | 1            | 2         |
| Jumpers/Shunts | 2            | 5-6       |
| Fuses          | 1            | 1         |
| **Total**      | **~31**      | **~62**   |

---

## Schematic Update Notes

1. **Blue LEDs use MOSFET drivers** - 2× 2N7002 with 100kΩ gate pulldowns, powered from 5V rail
2. **LED resistor values** - use 1kΩ for 5V LEDs (red power, blue user), 470Ω for 3.3V LEDs (green power, amber TX/RX, red IR)
3. **Fix R15** - currently shows "22µF" (should be 1kΩ)
4. **L1** - BOM specifies 4.7µH, schematic may show 3.9µH (both acceptable per AP63203 datasheet)

Reference designators in this BOM are indicative only. The schematic is the source of truth for designators.

---

## Notes

- Datasheets stored in `hardware/datasheets/`
- Existing datasheets: AP63203WU-7.pdf, ESP32-WROOM-32E-N4.pdf
- All LEDs are Everlight 204 series 3mm for consistency
- Blue LEDs (InGaN) are inherently brighter; reduced current via 1kΩ resistor for similar perceived brightness
