# IR Transmitter Wiring Guide

## Overview

Add an IR LED transmitter circuit to your ESP8266 NodeMCU to enable IR transmission. The circuit uses a transistor to drive the IR LED with sufficient current.

---

## Components Needed

| Component             | Quantity | Notes                                                     |
| --------------------- | -------- | --------------------------------------------------------- |
| 940nm IR LED (5mm)    | 1-2      | Standard IR LED, get extras for parallel config if needed |
| 2N2222 NPN Transistor | 1        | Or BC547, PN2222 - any general-purpose NPN                |
| 470Ω resistor         | 1        | Base resistor (controls transistor)                       |
| 10Ω resistor          | 1        | LED current limiting resistor                             |
| Breadboard            | 1        | For prototyping                                           |
| Jumper wires          | 5-6      | Male-to-male for breadboard                               |

---

## Circuit Diagram

### Schematic

```
ESP8266 NodeMCU

GPIO4 (D2) ----[470Ω]----> Base (B)
                              |
                         2N2222 NPN
                              |
                         Collector (C)
                              |
                         IR LED Cathode (short leg, flat side)
                              |
                         IR LED Anode (long leg)
                              |
                           [10Ω]
                              |
                            3.3V

GND --------------------> Emitter (E)
```

### Pin Identification

**2N2222 Transistor (TO-92 package, flat side facing you):**

```
    ___
   /   \
  | 2N2 |
  | 222 |
  |_____|
   | | |
   E B C
```

- **E** = Emitter (leftmost) → ESP8266 GND
- **B** = Base (middle) → GPIO4 via 470Ω resistor
- **C** = Collector (rightmost) → IR LED cathode

**IR LED:**

- **Anode** (+, longer leg) → 10Ω resistor → 3.3V
- **Cathode** (-, shorter leg, flat side) → Transistor collector

---

## Breadboard Layout

```
ESP8266 NodeMCU Layout:
         ┌─────────┐
    3V3  │1      30│  GND
    GND  │2      29│  ...
    D1   │3      28│  ...
    D2   │4 ← TX  27│  ...  (GPIO4 - IR Transmit)
    D3   │5      26│  ...
    D4   │6      25│  ...
    D5   │7 ← RX  24│  ...  (GPIO14 - IR Receive, already wired)
    ...  │8      23│  ...
         └─────────┘
```

### Breadboard Wiring Steps

1. **Place the transistor** on breadboard (flat side facing you)

   - Emitter (left pin) → breadboard ground rail
   - Base (middle pin) → empty row
   - Collector (right pin) → empty row

2. **Connect 470Ω resistor** (base resistor)

   - One end → GPIO4 (D2) on ESP8266
   - Other end → transistor base (middle pin)

3. **Place IR LED** on breadboard

   - Cathode (short leg, flat side) → same row as transistor collector
   - Anode (long leg) → empty row

4. **Connect 10Ω resistor** (LED current limiting)

   - One end → IR LED anode
   - Other end → 3.3V power rail

5. **Connect ground**

   - Transistor emitter → ground rail
   - ESP8266 GND → ground rail

6. **Connect power**
   - ESP8266 3V3 → power rail
   - 10Ω resistor → power rail

---

## Power Calculations

**Current through IR LED:**

- Supply voltage: 3.3V
- IR LED forward voltage: ~1.2V @ 20mA
- Current limiting resistor: 10Ω
- **Current: (3.3V - 1.2V) / 10Ω = 210mA**

This provides sufficient IR power for 2-5 meter range (typical room distance).

**Transistor specifications:**

- 2N2222 max collector current: 600mA
- Our circuit: ~210mA
- **Safety margin: >2.8x** ✓

---

## Testing Procedure

### 1. Visual Inspection

- ✓ Transistor oriented correctly (E-B-C)
- ✓ IR LED polarity correct (long leg = anode to power)
- ✓ No short circuits
- ✓ All connections tight

### 2. Resistance Check (Power OFF)

Use multimeter to verify:

- GPIO4 to GND through resistor+transistor: Should read ~470Ω + transistor resistance
- 3.3V to GND through LED circuit: Should read ~10Ω + LED resistance

### 3. IR LED Test (Use Phone Camera)

1. Upload the firmware (main.cpp)
2. Open Serial Monitor at 115200 baud
3. Send command: `POWER:OFF`
4. **Point phone camera at IR LED**
5. You should see **purple/white flashing** on camera screen
6. (Note: IR light is invisible to human eye but visible on phone cameras)

### 4. Loopback Test

1. IR receiver already on GPIO14 (D5)
2. Enable debug mode: `DEBUG:ON`
3. Send command: `POWER:OFF`
4. Check Serial Monitor for: `DEBUG: Received IR - Protocol: COOLIX`
5. This confirms IR LED is transmitting and receiver is picking it up

### 5. Protocol Verification

Send each command and verify IR transmission:

```
POWER:OFF     → Should see IR flash (COOLIX)
TEMP:22       → Should see IR flash (BOSCH144)
MODE:COOL     → Should see IR flash (BOSCH144)
SWING         → Should see IR flash (COOLIX)
```

---

## Troubleshooting

### IR LED Not Transmitting (No flash on camera)

**Check 1: Transistor connections**

- Verify E-B-C pinout matches your transistor datasheet
- Try swapping collector and emitter if using different transistor

**Check 2: IR LED polarity**

- Long leg (anode) should go to 3.3V via resistor
- Short leg (cathode) should go to transistor collector
- Try reversing if not working

**Check 3: Power supply**

- Measure voltage at 3.3V pin: should be 3.2-3.4V
- If using USB power, try different USB port/cable

**Check 4: Resistor values**

- Verify 470Ω resistor (Yellow-Purple-Brown or Yellow-Purple-Black-Black)
- Verify 10Ω resistor (Brown-Black-Black or Brown-Black-Gold-Gold)

### IR LED Weak/Short Range

**Solution 1: Add second IR LED in parallel**

```
                         [LED1 Cathode]---[LED1 Anode]---[10Ω]---3.3V
                              |
Transistor Collector ---------|
                              |
                         [LED2 Cathode]---[LED2 Anode]---[10Ω]---3.3V
```

This doubles the IR power output.

**Solution 2: Reduce current limiting resistor**

- Change 10Ω → 5Ω for more current (~350mA)
- Monitor ESP8266 temperature (should stay cool)

**Solution 3: Focus the beam**

- Point IR LED directly at AC unit's receiver
- Use reflector or lens to focus IR beam
- Keep distance under 5 meters for best results

### IR Transmission But AC Not Responding

**Check 1: Aim**

- Point IR LED directly at AC unit's IR receiver
- AC receiver is usually near display/indicator lights
- Try different angles

**Check 2: Distance**

- Start at 1-2 meters
- Gradually increase distance
- Optimal range: 2-5 meters

**Check 3: Protocol verification**

- Use `DEBUG:ON` mode
- Send command
- Verify firmware is transmitting correct protocol (BOSCH144 or COOLIX)
- Compare with captures in `/captures` directory

---

## Advanced: Multiple IR LEDs for Extended Range

If you need longer range (>5m) or wider coverage, add 2-3 IR LEDs in parallel:

```
                         [LED1]---[10Ω]
                              |
Transistor Collector ---------|---[LED2]---[10Ω]---3.3V
                              |
                         [LED3]---[10Ω]
```

**Benefits:**

- Increased range (up to 8-10m)
- Wider beam angle
- More reliable transmission

**Note:** Total current = 210mA × number of LEDs. Keep under 500mA to avoid overloading ESP8266's 3.3V regulator.

---

## Permanent Installation

Once testing is successful:

1. **PCB/Perfboard** - Transfer circuit to permanent board
2. **Enclosure** - 3D print or use project box
3. **Status LED** - Add visible LED on GPIO2 (D4, built-in) for transmission indicator
4. **Power supply** - Use 5V USB wall adapter for reliable power

---

## Final Checklist

Before considering hardware complete:

- [ ] IR LED transmits (verified with phone camera)
- [ ] Loopback test successful (receiver picks up transmission)
- [ ] All protocols tested (POWER:OFF, TEMP:22, SWING)
- [ ] AC unit responds to Power OFF command
- [ ] AC unit responds to temperature changes
- [ ] Range tested (works at 2-5 meters)
- [ ] Circuit stable (no intermittent issues)

---

## Next Steps

Once hardware is working:

1. Test all serial commands with Serial Monitor
2. Verify AC unit responds to all commands
3. Proceed to React Router app development
4. Final integration testing

**Good luck with the build!** 🔧
