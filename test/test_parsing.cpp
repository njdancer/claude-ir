/*
 * Unit Tests for ActronAir IR Controller
 *
 * Tests command parsing and validation logic
 * Run with: pio test -e native
 */

#include <unity.h>
#include <math.h>
#include <stdint.h>
#include <cstring>

// Mock Bosch144 constants (from ir_Bosch.h)
#define kBosch144Cool 0
#define kBosch144Heat 3
#define kBosch144Dry 1
#define kBosch144Fan 4
#define kBosch144Auto 2

#define kBosch144FanAuto 0
#define kBosch144FanLow 1
#define kBosch144FanMedium 2
#define kBosch144FanMediumHigh 3
#define kBosch144FanHigh 4
#define kBosch144FanMax 5

// ===== Functions Under Test =====

bool validateTemperature(float temp) {
  // Check range: 16.0 to 30.0
  if (temp < 16.0 || temp > 30.0) {
    return false;
  }

  // Check 0.5° increments
  float remainder = fmod(temp, 0.5);
  return (remainder < 0.01 || remainder > 0.49);  // Allow small floating point errors
}

uint8_t parseMode(const char* modeStr) {
  if (strcmp(modeStr, "COOL") == 0) return kBosch144Cool;
  if (strcmp(modeStr, "HEAT") == 0) return kBosch144Heat;
  if (strcmp(modeStr, "DRY") == 0)  return kBosch144Dry;
  if (strcmp(modeStr, "FAN") == 0)  return kBosch144Fan;
  if (strcmp(modeStr, "AUTO") == 0) return kBosch144Auto;
  return 255;  // Invalid
}

uint8_t parseFanSpeed(const char* fanStr) {
  if (strcmp(fanStr, "AUTO") == 0) return kBosch144FanAuto;
  if (strcmp(fanStr, "20") == 0)   return kBosch144FanLow;
  if (strcmp(fanStr, "40") == 0)   return kBosch144FanMedium;
  if (strcmp(fanStr, "60") == 0)   return kBosch144FanMediumHigh;
  if (strcmp(fanStr, "80") == 0)   return kBosch144FanHigh;
  if (strcmp(fanStr, "100") == 0)  return kBosch144FanMax;
  return 255;  // Invalid
}

const char* getModeString(uint8_t mode) {
  switch (mode) {
    case kBosch144Cool: return "COOL";
    case kBosch144Heat: return "HEAT";
    case kBosch144Dry:  return "DRY";
    case kBosch144Fan:  return "FAN";
    case kBosch144Auto: return "AUTO";
    default: return "UNKNOWN";
  }
}

const char* getFanString(uint8_t fanSpeed) {
  if (fanSpeed == kBosch144FanAuto) return "AUTO";
  if (fanSpeed == kBosch144FanLow) return "20";
  if (fanSpeed == kBosch144FanMedium) return "40";
  if (fanSpeed == kBosch144FanMediumHigh) return "60";
  if (fanSpeed == kBosch144FanHigh) return "80";
  if (fanSpeed == kBosch144FanMax) return "100";
  return "UNKNOWN";
}

// ===== Temperature Validation Tests =====

void test_temperature_valid_whole_numbers(void) {
  TEST_ASSERT_TRUE(validateTemperature(16.0));
  TEST_ASSERT_TRUE(validateTemperature(20.0));
  TEST_ASSERT_TRUE(validateTemperature(22.0));
  TEST_ASSERT_TRUE(validateTemperature(25.0));
  TEST_ASSERT_TRUE(validateTemperature(30.0));
}

void test_temperature_valid_half_increments(void) {
  TEST_ASSERT_TRUE(validateTemperature(16.5));
  TEST_ASSERT_TRUE(validateTemperature(20.5));
  TEST_ASSERT_TRUE(validateTemperature(22.5));
  TEST_ASSERT_TRUE(validateTemperature(25.5));
  TEST_ASSERT_TRUE(validateTemperature(29.5));
}

void test_temperature_invalid_below_min(void) {
  TEST_ASSERT_FALSE(validateTemperature(15.9));
  TEST_ASSERT_FALSE(validateTemperature(15.0));
  TEST_ASSERT_FALSE(validateTemperature(10.0));
  TEST_ASSERT_FALSE(validateTemperature(0.0));
}

void test_temperature_invalid_above_max(void) {
  TEST_ASSERT_FALSE(validateTemperature(30.1));
  TEST_ASSERT_FALSE(validateTemperature(31.0));
  TEST_ASSERT_FALSE(validateTemperature(35.0));
}

void test_temperature_invalid_wrong_increments(void) {
  TEST_ASSERT_FALSE(validateTemperature(20.1));
  TEST_ASSERT_FALSE(validateTemperature(22.3));
  TEST_ASSERT_FALSE(validateTemperature(25.7));
  TEST_ASSERT_FALSE(validateTemperature(28.9));
}

void test_temperature_boundary_conditions(void) {
  // Exact boundaries
  TEST_ASSERT_TRUE(validateTemperature(16.0));   // Min
  TEST_ASSERT_TRUE(validateTemperature(30.0));   // Max

  // Just outside boundaries
  TEST_ASSERT_FALSE(validateTemperature(15.99));
  TEST_ASSERT_FALSE(validateTemperature(30.01));
}

// ===== Mode Parsing Tests =====

void test_parseMode_valid_modes(void) {
  TEST_ASSERT_EQUAL_UINT8(kBosch144Cool, parseMode("COOL"));
  TEST_ASSERT_EQUAL_UINT8(kBosch144Heat, parseMode("HEAT"));
  TEST_ASSERT_EQUAL_UINT8(kBosch144Dry, parseMode("DRY"));
  TEST_ASSERT_EQUAL_UINT8(kBosch144Fan, parseMode("FAN"));
  TEST_ASSERT_EQUAL_UINT8(kBosch144Auto, parseMode("AUTO"));
}

void test_parseMode_invalid_modes(void) {
  TEST_ASSERT_EQUAL_UINT8(255, parseMode("INVALID"));
  TEST_ASSERT_EQUAL_UINT8(255, parseMode("cool"));  // lowercase
  TEST_ASSERT_EQUAL_UINT8(255, parseMode(""));
  TEST_ASSERT_EQUAL_UINT8(255, parseMode("HOT"));
  TEST_ASSERT_EQUAL_UINT8(255, parseMode("COLD"));
}

void test_parseMode_case_sensitive(void) {
  // These should fail (lowercase)
  TEST_ASSERT_EQUAL_UINT8(255, parseMode("cool"));
  TEST_ASSERT_EQUAL_UINT8(255, parseMode("heat"));

  // These should pass (uppercase)
  TEST_ASSERT_EQUAL_UINT8(kBosch144Cool, parseMode("COOL"));
  TEST_ASSERT_EQUAL_UINT8(kBosch144Heat, parseMode("HEAT"));
}

// ===== Fan Speed Parsing Tests =====

void test_parseFanSpeed_valid_speeds(void) {
  TEST_ASSERT_EQUAL_UINT8(kBosch144FanAuto, parseFanSpeed("AUTO"));
  TEST_ASSERT_EQUAL_UINT8(kBosch144FanLow, parseFanSpeed("20"));
  TEST_ASSERT_EQUAL_UINT8(kBosch144FanMedium, parseFanSpeed("40"));
  TEST_ASSERT_EQUAL_UINT8(kBosch144FanMediumHigh, parseFanSpeed("60"));
  TEST_ASSERT_EQUAL_UINT8(kBosch144FanHigh, parseFanSpeed("80"));
  TEST_ASSERT_EQUAL_UINT8(kBosch144FanMax, parseFanSpeed("100"));
}

void test_parseFanSpeed_invalid_speeds(void) {
  TEST_ASSERT_EQUAL_UINT8(255, parseFanSpeed("INVALID"));
  TEST_ASSERT_EQUAL_UINT8(255, parseFanSpeed("50"));   // Not supported
  TEST_ASSERT_EQUAL_UINT8(255, parseFanSpeed("0"));
  TEST_ASSERT_EQUAL_UINT8(255, parseFanSpeed(""));
  TEST_ASSERT_EQUAL_UINT8(255, parseFanSpeed("auto")); // lowercase
}

// ===== Mode String Formatting Tests =====

void test_getModeString_valid_modes(void) {
  TEST_ASSERT_EQUAL_STRING("COOL", getModeString(kBosch144Cool));
  TEST_ASSERT_EQUAL_STRING("HEAT", getModeString(kBosch144Heat));
  TEST_ASSERT_EQUAL_STRING("DRY", getModeString(kBosch144Dry));
  TEST_ASSERT_EQUAL_STRING("FAN", getModeString(kBosch144Fan));
  TEST_ASSERT_EQUAL_STRING("AUTO", getModeString(kBosch144Auto));
}

void test_getModeString_invalid_mode(void) {
  TEST_ASSERT_EQUAL_STRING("UNKNOWN", getModeString(99));
  TEST_ASSERT_EQUAL_STRING("UNKNOWN", getModeString(255));
}

// ===== Fan String Formatting Tests =====

void test_getFanString_valid_speeds(void) {
  TEST_ASSERT_EQUAL_STRING("AUTO", getFanString(kBosch144FanAuto));
  TEST_ASSERT_EQUAL_STRING("20", getFanString(kBosch144FanLow));
  TEST_ASSERT_EQUAL_STRING("40", getFanString(kBosch144FanMedium));
  TEST_ASSERT_EQUAL_STRING("60", getFanString(kBosch144FanMediumHigh));
  TEST_ASSERT_EQUAL_STRING("80", getFanString(kBosch144FanHigh));
  TEST_ASSERT_EQUAL_STRING("100", getFanString(kBosch144FanMax));
}

void test_getFanString_invalid_speed(void) {
  TEST_ASSERT_EQUAL_STRING("UNKNOWN", getFanString(99));
  TEST_ASSERT_EQUAL_STRING("UNKNOWN", getFanString(255));
}

// ===== Round-trip Tests =====

void test_mode_roundtrip(void) {
  // Parse then format should give original string
  const char* modes[] = {"COOL", "HEAT", "DRY", "FAN", "AUTO"};

  for (int i = 0; i < 5; i++) {
    uint8_t parsed = parseMode(modes[i]);
    const char* formatted = getModeString(parsed);
    TEST_ASSERT_EQUAL_STRING(modes[i], formatted);
  }
}

void test_fan_roundtrip(void) {
  // Parse then format should give original string
  const char* fans[] = {"AUTO", "20", "40", "60", "80", "100"};

  for (int i = 0; i < 6; i++) {
    uint8_t parsed = parseFanSpeed(fans[i]);
    const char* formatted = getFanString(parsed);
    TEST_ASSERT_EQUAL_STRING(fans[i], formatted);
  }
}

// ===== Test Setup and Main =====

void setUp(void) {
  // Called before each test
}

void tearDown(void) {
  // Called after each test
}

int main(int argc, char **argv) {
  UNITY_BEGIN();

  // Temperature validation tests
  RUN_TEST(test_temperature_valid_whole_numbers);
  RUN_TEST(test_temperature_valid_half_increments);
  RUN_TEST(test_temperature_invalid_below_min);
  RUN_TEST(test_temperature_invalid_above_max);
  RUN_TEST(test_temperature_invalid_wrong_increments);
  RUN_TEST(test_temperature_boundary_conditions);

  // Mode parsing tests
  RUN_TEST(test_parseMode_valid_modes);
  RUN_TEST(test_parseMode_invalid_modes);
  RUN_TEST(test_parseMode_case_sensitive);

  // Fan speed parsing tests
  RUN_TEST(test_parseFanSpeed_valid_speeds);
  RUN_TEST(test_parseFanSpeed_invalid_speeds);

  // String formatting tests
  RUN_TEST(test_getModeString_valid_modes);
  RUN_TEST(test_getModeString_invalid_mode);
  RUN_TEST(test_getFanString_valid_speeds);
  RUN_TEST(test_getFanString_invalid_speed);

  // Round-trip tests
  RUN_TEST(test_mode_roundtrip);
  RUN_TEST(test_fan_roundtrip);

  return UNITY_END();
}
