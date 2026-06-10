# PCB Layout Constraints (H2.1)

Placement and routing constraints for the v1.2 board. Written before any
placement so layout (H2.2+) is execution against a checklist, not
improvisation. Board design rules and net classes live in the KiCad project
(`.kicad_pro` net_settings + board rules) — this note records *why* and the
constraints that rules can't express.

## Stackup & fab rules (set in project, 2026-06-11)

- JLCPCB 2-layer, 1oz copper. Board minimums: clearance 0.15 mm, track
  0.15 mm, via 0.5/0.3 mm, through-hole drill 0.3 mm, copper-to-edge 0.3 mm.
  (JLCPCB's absolute floor is 0.127 mm/5 mil; we keep margin.)
- Net classes:
  - **Power** (0.6 mm track, 0.8/0.4 via): `+5V`, `+3.3V`, `GND`,
    `Net-(U1-SW)`, `Net-(F1-Pad2)` — sized for ~400 mA IR pulses + WiFi
    peaks (≥0.5 mm @1oz handles 1 A+ with trivial rise).
  - **IR_Drive** (0.5 mm): `IR_DRAIN`, `EXT_IR_A`, `Net-(D2-A..D5-A)` —
    each LED string pulses ~100 mA; the shared drain return carries all four.
  - Default 0.2 mm for signals.

## Placement constraints (hard)

1. **WROOM-32E antenna keepout (U3):** module at a board edge, antenna
   section overhanging or flush with the edge; **no copper on any layer
   under the antenna** (the section past the module's shield can), and keep
   other components ≥5 mm from the antenna zone. KiCad's footprint shows the
   keepout outline — respect it on both layers and in the GND pour.
2. **IR LEDs (D2–D5, THT, 5 mm) on the board edge** pointing outward at
   0°/45°/90°/135° fan-out so the array covers a wide arc toward the AC
   unit. They are hand-soldered THT — leave finger room. D2/D3 and D4/D5
   are series pairs; keep each pair's anode-cathode chain short.
3. **AP63203 buck (U1) switching loop tight:** C1/C2 (input caps) hard
   against VIN/GND pins; L1 adjacent to SW; C3 (output) close to L1 return
   with short GND back to U1. Keep the SW node (`Net-(U1-SW)`) copper area
   minimal — it's the noisy node. No signal traces under the buck loop.
4. **USB-C (J2) + CH340C (U2) short data traces:** J2 on board edge;
   U2 close to J2; route D+/D− as a loosely coupled pair, < 30 mm, no layer
   change if possible. ESD/TVS (D1) and fuse (F1) sit between J2 and the
   rest: order on VBUS must be J2 → F1 → D1 → U1 (fuse before TVS,
   per H1.4).
5. **DHT22 (U5) away from heat:** maximum practical distance from U1 (buck)
   and U3 (WiFi heat); prefer a board corner with slots/perimeter routing
   between it and heat sources if space allows. Sensor must sample room
   air, not board air.
6. **TSOP receiver (U4) faces the user/room:** board edge, lens unobstructed;
   its RC filter (R27/C9, net `IR_RX_VS`) directly at the Vs pin.

## Placement constraints (soft / serviceability)

7. **Connection points on edges:** J3 (Qwiic JST-SH) on an edge for cable
   access; J4 (spare-GPIO 2×5) and J6 (JTAG 2×5, DNP) in reachable positions
   with pin-1 marked; J5 (ext-IR, DNP) near the IR array edge.
8. **Buttons (SW1 RESET, SW2 BOOT)** on the same edge/face, reachable when
   the board is on a bench with USB plugged in; don't put them under the
   antenna end.
9. **Status LEDs (D6–D12)** visible from one viewing angle; group serial
   TX/RX (D8/D9) together; user LEDs (D11/D12) together. THT 3 mm,
   hand-soldered.
10. **Decoupling:** C4/C5/C7 (100 nF) at their IC power pins (U2, U3);
    C10 at U3's 3V3 entry; C6 (1 µF) at CH340C V3.
11. **JP1 (buck disable)** and **R21/R26 (auto-reset 0Ω links)** accessible
    for rework; silkscreen labels required (H2.4).

## Routing notes

- 2-layer plan: **B.Cu as continuous GND pour**, F.Cu for signals + power;
  stitch vias liberally, especially around the buck and under U3's GND pad
  (U3 pad 39 thermal vias to the back pour).
- The IR drive loop (3V3 → R9-R12 → LED strings → Q3 → GND) pulses 400 mA
  at 38 kHz: keep the loop area small and its GND return short to the pour;
  don't share its return path under the TSOP receiver or DHT22 traces.
- USB D+/D− cross under no other signals; GND pour unbroken beneath them.
- `IR_RX_VS` filter (R27/C9) and TSOP output trace away from the buck and
  the IR drive loop (receiver is the most EMI-sensitive part on the board).
- Strapping nets (GPIO0/2/12/15, EN) are short and local: buttons + R-C
  near U3.

## Board outline (to decide at H2.2 placement)

Not yet drawn (Edge.Cuts empty). Drivers: IR LED fan on one edge, USB-C +
buttons on the opposite/adjacent edge, antenna overhang on a third, DHT22
in the far corner from the buck. Mounting: 4× M3 holes (add via
`add_mounting_hole`), ≥2.5 mm from edges. Target compact 2-layer —
roughly 60×45 mm first attempt, grow only if routing demands it.

## H2.2 exit criteria

- All hard constraints above satisfied; photo/3D render to Nick **before
  routing starts** (cheap to move parts now, expensive later).
