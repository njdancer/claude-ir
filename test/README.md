# C++ Unit Tests

Unit tests for the ActronAir IR Controller firmware using PlatformIO's native testing framework.

## Running Tests

### Run all tests

```bash
pio test -e native
```

### Run with verbose output

```bash
pio test -e native -v
```

### Run specific test

```bash
pio test -e native --filter test_parsing
```

## Test Coverage

### Temperature Validation (`validateTemperature`)

- ✓ Valid whole numbers (16.0, 20.0, 22.0, 25.0, 30.0)
- ✓ Valid half increments (16.5, 20.5, 22.5, 25.5, 29.5)
- ✓ Invalid below minimum (<16.0)
- ✓ Invalid above maximum (>30.0)
- ✓ Invalid wrong increments (20.1, 22.3, 25.7)
- ✓ Boundary conditions (exactly 16.0 and 30.0)

### Mode Parsing (`parseMode`)

- ✓ Valid modes (COOL, HEAT, DRY, FAN, AUTO)
- ✓ Invalid modes (returns 255)
- ✓ Case sensitivity (uppercase required)

### Fan Speed Parsing (`parseFanSpeed`)

- ✓ Valid speeds (AUTO, 20, 40, 60, 80, 100)
- ✓ Invalid speeds (returns 255)
- ✓ Unsupported values (50, 0)

### String Formatting (`getModeString`, `getFanString`)

- ✓ Valid mode/fan codes → correct strings
- ✓ Invalid codes → "UNKNOWN"

### Round-trip Tests

- ✓ Parse → Format should return original string
- ✓ All modes tested
- ✓ All fan speeds tested

## Test Output

Example successful test run:

```
test/test_parsing.cpp:48:test_temperature_valid_whole_numbers       [PASSED]
test/test_parsing.cpp:55:test_temperature_valid_half_increments     [PASSED]
test/test_parsing.cpp:62:test_temperature_invalid_below_min         [PASSED]
test/test_parsing.cpp:69:test_temperature_invalid_above_max         [PASSED]
test/test_parsing.cpp:76:test_temperature_invalid_wrong_increments  [PASSED]
test/test_parsing.cpp:83:test_temperature_boundary_conditions       [PASSED]
test/test_parsing.cpp:92:test_parseMode_valid_modes                 [PASSED]
test/test_parsing.cpp:100:test_parseMode_invalid_modes              [PASSED]
test/test_parsing.cpp:108:test_parseMode_case_sensitive             [PASSED]
test/test_parsing.cpp:117:test_parseFanSpeed_valid_speeds           [PASSED]
test/test_parsing.cpp:126:test_parseFanSpeed_invalid_speeds         [PASSED]
test/test_parsing.cpp:133:test_getModeString_valid_modes            [PASSED]
test/test_parsing.cpp:141:test_getModeString_invalid_mode           [PASSED]
test/test_parsing.cpp:147:test_getFanString_valid_speeds            [PASSED]
test/test_parsing.cpp:156:test_getFanString_invalid_speed           [PASSED]
test/test_parsing.cpp:162:test_mode_roundtrip                       [PASSED]
test/test_parsing.cpp:173:test_fan_roundtrip                        [PASSED]

-----------------------
17 Tests 0 Failures 0 Ignored
OK
```

## Adding More Tests

To add new tests:

1. Create a new test file in `/test` directory (e.g., `test_newfeature.cpp`)
2. Include `<unity.h>` header
3. Write test functions with `TEST_ASSERT_*` macros
4. Add tests to `main()` with `RUN_TEST()`
5. Run with `pio test -e native`

## Test Framework

Uses **Unity** test framework (built into PlatformIO):

- `TEST_ASSERT_TRUE(condition)` - Assert condition is true
- `TEST_ASSERT_FALSE(condition)` - Assert condition is false
- `TEST_ASSERT_EQUAL(expected, actual)` - Assert values are equal
- `TEST_ASSERT_EQUAL_STRING(expected, actual)` - Assert strings are equal
- `TEST_ASSERT_EQUAL_UINT8(expected, actual)` - Assert uint8_t values are equal

[Full Unity documentation](http://www.throwtheswitch.org/unity)

## CI Integration

These tests can run in CI/CD pipelines:

```yaml
# Example GitHub Actions
- name: Run Unit Tests
  run: pio test -e native
```

No ESP8266 hardware required - tests run on the host machine!

## Limitations

**What these tests cover:**
- Command parsing logic
- Temperature validation
- String formatting
- State management functions

**What these tests DON'T cover:**
- Actual IR transmission (hardware-dependent)
- Serial communication (hardware-dependent)
- Arduino-specific functionality
- ESP8266-specific features

For full integration testing, use the actual hardware with Serial Monitor testing.
