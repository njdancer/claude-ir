# IR LED Circuit Troubleshooting Checklist

## Current Symptoms
- Serial commands work ✓
- IR LED not visible on camera ✗
- Collector voltage: 2.4V (should be ~0.2V when ON, ~3.3V when OFF)
- Current through LED: ~10mA (should be ~190mA when transmitting)

## Verification Steps

### Step 1: Power OFF - LED Polarity (Diode Mode)
- [ ] Set multimeter to diode test mode (⏵|◁ symbol)
- [ ] Red probe on longer leg, black probe on shorter leg
  - **Expected**: ~0.6-1.2V reading (forward voltage)
- [ ] Reverse probes
  - **Expected**: "OL" or very high reading (reverse bias)
- [ ] **Confirm**: Longer leg = Anode, connects to 3.3V side
- [ ] **Confirm**: Shorter leg/flat edge = Cathode, connects to Collector

### Step 2: Power OFF - Transistor Pinout (Continuity Mode)
- [ ] 2N2222 flat side facing you, pins are E-B-C (left to right)
- [ ] Left pin (Emitter) has continuity to ESP8266 GND pin
- [ ] Middle pin (Base) has continuity through resistor to D2
- [ ] Right pin (Collector) has continuity to IR LED cathode

### Step 3: Power OFF - Full Circuit Continuity
- [ ] 3.3V → 10Ω resistor → IR LED anode (path exists)
- [ ] IR LED cathode → Transistor collector (direct connection)
- [ ] Transistor base → 470Ω resistor → D2 (path exists)
- [ ] Transistor emitter → GND (direct connection, beep sound)

### Step 4: Power ON - Idle Voltages
- [ ] D2: Should be ~0V when idle
- [ ] Base: Should be ~0V when idle
- [ ] Collector: Should be ~3.2-3.3V when transistor OFF
- [ ] Emitter: Should be 0V (GND reference)

### Step 5: Power ON - Active Transmission
**Send command**: `POWER:OFF` (sends Coolix code)

**Measure immediately during transmission:**
- [ ] D2: Should pulse between 0V-3.3V rapidly (38kHz)
- [ ] Collector: Should drop to ~0.2V when transistor saturated
- [ ] Current through 10Ω resistor: (3.3V - 1.2V - 0.2V) / 10Ω = ~190mA

### Step 6: Visual Confirmation
- [ ] Point IR LED at phone camera
- [ ] Send `POWER:OFF` command
- [ ] Camera should show bright purple/white flashing

## Diagnostic Results

### If LED polarity is backwards:
- **Symptom**: Collector ~2.4V, low current (~10mA)
- **Fix**: Flip the IR LED 180 degrees

### If transistor pins are wrong:
- **Symptom**: No voltage change on any pin during command
- **Fix**: Re-check 2N2222 pinout, rewire if needed

### If resistor is wrong value:
- **Symptom**: Very low current OR LED not visible
- **Fix**: Verify 10Ω resistor (brown-black-black bands)

### If LED is damaged:
- **Symptom**: All voltages correct but no light on camera
- **Fix**: Replace IR LED with new 940nm LED

### If transistor is damaged:
- **Symptom**: Collector stays at 3.3V, never drops
- **Fix**: Replace 2N2222 transistor

## Expected Voltage Summary

| Point | Idle (Transistor OFF) | Transmitting (Transistor ON) |
|-------|----------------------|------------------------------|
| 3.3V  | 3.3V                 | 3.3V                         |
| IR Anode | 3.3V              | 3.3V                         |
| IR Cathode (Collector) | 3.3V | ~0.2V                   |
| Base  | 0V                   | ~2.6V (pulsing)              |
| Emitter | 0V                 | 0V                           |
| D2    | 0V                   | 3.3V (pulsing at 38kHz)      |

**Current LED behavior**: Collector at 2.4V suggests LED barely conducting (~10mA) → likely backwards or damaged
