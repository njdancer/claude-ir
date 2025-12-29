# ActronAir IR Protocol Specification (BOSCH144)

## Overview
- **Protocol**: BOSCH144 (144 bits / 18 bytes)
- **Transmission**: Message sent 3× for redundancy
- **Structure**: State-based (complete AC state in every transmission)
- **Remote**: Compatible with multiple ActronAir remote models

## Byte Structure

```
Bytes 0-5:   First copy of state (header + temp + mode/fan bits)
Bytes 6-11:  Exact duplicate of bytes 0-5
Bytes 12-17: Footer (mode/fan/swing flags + checksums)
```

## Detailed Byte Map

| Byte | Function | Description |
|------|----------|-------------|
| 0 | Header | Always 0xB2 |
| 1 | Header | Always 0x4D |
| 2 | Fan Speed (High) | Upper bits of fan encoding |
| 3 | Fan Speed (Low) | Lower bits of fan encoding |
| 4 | Temperature + Mode | Combined temp and mode encoding |
| 5 | Checksum | Bitwise inverse of byte 4 (~byte[4]) |
| 6-11 | Repeat | Exact duplicate of bytes 0-5 |
| 12 | Footer | Always 0xD5 |
| 13 | Fan Speed % | Direct fan percentage (or 0x66 for AUTO) |
| 14 | Temperature +0.5°C | 0x00=whole degree, 0x20=+0.5°C |
| 15 | Unknown | Usually 0x00 |
| 16 | Unknown | Usually 0x00 |
| 17 | Checksum | Likely checksum of footer bytes |

## Temperature Encoding

### Whole Degrees (Byte 4 - Base Component)
Temperature uses a **lookup table** (non-linear encoding):

| Temp (°C) | Byte 4 (COOL mode) | Byte 4 (hex) | Binary |
|-----------|-------------------|--------------|---------|
| 16 | 0 | 0x00 | 0000 0000 |
| 18 | 16 | 0x10 | 0001 0000 |
| 20 | 32 | 0x20 | 0010 0000 |
| 21 | 96 | 0x60 | 0110 0000 |
| 22 | 112 | 0x70 | 0111 0000 |
| 23 | 80 | 0x50 | 0101 0000 |
| 24 | 64 | 0x40 | 0100 0000 |
| 25 | 192 | 0xC0 | 1100 0000 |
| 26 | 208 | 0xD0 | 1101 0000 |
| 27 | 144 | 0x90 | 1001 0000 |
| 30 | 176 | 0xB0 | 1011 0000 |

**Note**: Values above are for COOL mode. Other modes add mode bits to byte 4 (see Mode Encoding).

### Half Degree (Byte 14)
- `0x00` = whole degree (e.g., 20.0°C)
- `0x20` = add 0.5°C (e.g., 20.5°C)

### Temperature Range
- **COOL mode**: 16°C - 30°C (may vary by model)
- **Other modes**: Range may differ

## Mode Encoding

Modes are encoded in **bytes 2-3** and **byte 4** (mode bits added to temperature value):

### Byte 2-3 Patterns
- **Group A** (0xBF, 0x40): COOL, HEAT, FAN
- **Group B** (0x1F, 0xE0): DRY, AUTO

### Byte 4 Mode Bits (at 20°C example)
| Mode | Byte 4 | Binary | Mode Bits |
|------|--------|---------|-----------|
| COOL | 0x20 | 0010 0000 | (base) |
| DRY  | 0x24 | 0010 0100 | bit 2 |
| HEAT | 0x2C | 0010 1100 | bits 2+3 |
| FAN  | 0xE4 | 1110 0100 | bits 2+5+6+7 |
| AUTO | 0x28 | 0010 1000 | bit 3 |

**Pattern**: Mode bits are **OR'd** with the base temperature value.

### Complete Mode Map
| Mode | Bytes 2-3 | Byte 4 (20°C) | Byte 13 |
|------|-----------|---------------|---------|
| COOL | 0xBF, 0x40 | 0x20 | varies by fan |
| DRY  | 0x1F, 0xE0 | 0x24 | varies by fan |
| HEAT | 0xBF, 0x40 | 0x2C | varies by fan |
| FAN  | 0xBF, 0x40 | 0xE4 | varies by fan |
| AUTO | 0x1F, 0xE0 | 0x28 | varies by fan |

## Fan Speed Encoding

Fan speed is encoded in **bytes 2-3** and **byte 13**:

### Byte 13 - Direct Percentage
| Fan Speed | Byte 13 (hex) | Byte 13 (decimal) |
|-----------|---------------|-------------------|
| AUTO | 0x66 | 102 |
| 20% | 0x14 | 20 |
| 40% | 0x28 | 40 |
| 60% | 0x3C | 60 |
| 80% | 0x50 | 80 |
| 100% | 0x64 | 100 |

**Pattern**: Byte 13 = fan percentage in decimal (except AUTO = 0x66)

### Bytes 2-3 - Fan Encoding
| Fan Speed | Byte 2 | Byte 3 | Bytes 2-3 |
|-----------|--------|--------|-----------|
| AUTO | 0xBF | 0x40 | 10111111 01000000 |
| 20% | 0xFF | 0x00 | 11111111 00000000 |
| 40% | 0x9F | 0x60 | 10011111 01100000 |
| 60% | 0x5F | 0xA0 | 01011111 10100000 |
| 80% | 0x3F | 0xC0 | 00111111 11000000 |
| 100% | 0x3F | 0xC0 | 00111111 11000000 |

**Note**: 80% and 100% share same bytes 2-3 (0x3F, 0xC0), differentiated only by byte 13.

## Swing / Air Direction

**Finding**: SWING button does **NOT** send standalone IR signals.

Swing may be:
- A local remote display feature only
- Encoded within other command transmissions (not yet identified)
- Model-specific feature not present in all remotes

## Checksums

### Byte 5
- **Always** bitwise inverse of byte 4: `byte[5] = ~byte[4]`
- Validates temperature + mode encoding

### Byte 17
- Appears to be checksum of footer bytes (12-16)
- Algorithm not yet fully reverse-engineered
- Changes with byte 13, 14, and other footer bytes

## Example State Decoding

### Example 1: Cool 24°C, Fan AUTO
```
State: {0xB2, 0x4D, 0xBF, 0x40, 0x40, 0xBF, 0xB2, 0x4D, 0xBF, 0x40, 0x40, 0xBF, 0xD5, 0x66, 0x00, 0x00, 0x00, 0x39}

Byte 0-1: 0xB2, 0x4D (header)
Byte 2-3: 0xBF, 0x40 (Group A - COOL/HEAT/FAN)
Byte 4: 0x40 (temp 24°C in COOL mode)
Byte 5: 0xBF (checksum: ~0x40 = 0xBF ✓)
Byte 6-11: Repeat of 0-5
Byte 12: 0xD5 (footer)
Byte 13: 0x66 (Fan AUTO)
Byte 14: 0x00 (whole degree, not +0.5°C)
Byte 17: 0x39 (checksum)

Decoded: COOL mode, 24.0°C, Fan AUTO
```

### Example 2: Heat 20.5°C, Fan 60%
```
State: {0xB2, 0x4D, 0x5F, 0xA0, 0x2C, 0xD3, 0xB2, 0x4D, 0x5F, 0xA0, 0x2C, 0xD3, 0xD5, 0x3C, 0x20, 0x00, 0x00, 0x??}

Byte 2-3: 0x5F, 0xA0 (Fan 60%)
Byte 4: 0x2C (0x20 temp base + 0x0C HEAT mode bits)
Byte 5: 0xD3 (checksum: ~0x2C = 0xD3 ✓)
Byte 13: 0x3C (60 decimal = Fan 60%)
Byte 14: 0x20 (+0.5°C)

Decoded: HEAT mode, 20.5°C, Fan 60%
```

## Implementation Notes

### Encoding a Command
1. Start with header: `0xB2, 0x4D`
2. Set bytes 2-3 for fan speed (see fan table)
3. Look up temperature base value from table
4. Add mode bits to temperature value → byte 4
5. Calculate byte 5 = ~byte 4
6. Duplicate bytes 0-5 to bytes 6-11
7. Set byte 12 = 0xD5
8. Set byte 13 = fan percentage (or 0x66 for AUTO)
9. Set byte 14 = 0x00 (whole) or 0x20 (+0.5°C)
10. Set bytes 15-16 = 0x00
11. Calculate byte 17 checksum (TBD algorithm)

### Decoding a Capture
1. Verify byte 0-1 = 0xB2, 0x4D (valid header)
2. Verify bytes 6-11 match bytes 0-5 (redundancy check)
3. Verify byte 5 = ~byte 4 (checksum)
4. Read byte 13 for fan speed percentage
5. Read bytes 2-3 to determine mode group
6. Read byte 4 and lookup temperature from table
7. Read byte 14 for +0.5°C flag

## Testing Coverage

✅ Temperature: 16-30°C in 0.5°C increments
✅ Modes: COOL, DRY, HEAT, FAN, AUTO
✅ Fan Speeds: AUTO, 20%, 40%, 60%, 80%, 100%
✅ Swing: Confirmed no standalone IR signal
⚠️ Power: Not yet tested (likely separate command)
⚠️ Other features: Boost, LED, Humidity, Timer (if present)

## Known Limitations

1. **Temperature lookup table incomplete**: Only tested 16-30°C range
2. **Byte 17 checksum algorithm**: Not fully reverse-engineered
3. **Swing encoding**: Not identified (may not be transmitted)
4. **Mode-specific temperature ranges**: Not fully tested
5. **Power ON/OFF**: Separate command format (if different)

## Hardware Used

- **ESP8266 NodeMCU** with CHQ1838 IR receiver
- **ActronAir Remote** (multiple models tested)
- **IRremoteESP8266 library** for protocol decoding

## Capture Date

Initial reverse engineering: 2025-12-28

---

*This specification is based on empirical testing and may not cover all edge cases or remote models.*
