/*
 * BOSCH144 frame construction tests.
 *
 * Fixtures come from two independent sources, making these tests a
 * cross-check between them:
 *   1. Our own IR captures of the ActronAir remote (re-findings.md tables)
 *   2. IRremoteESP8266's ir_Bosch implementation (bit layout + checksum)
 *
 * Run with: pio test -e native
 */

#include <unity.h>
#include <string.h>

#include "bosch144_protocol.h"

using namespace bosch144;

static uint8_t frame[kStateLength];

// ===== Structure rules (re-findings.md "Validation Rules") =====

void test_structure_headers_and_inverses(void) {
  buildFrame(22, false, kModeCool, kFanAuto, frame);
  TEST_ASSERT_EQUAL_HEX8(0xB2, frame[0]);
  TEST_ASSERT_EQUAL_HEX8(0x4D, frame[1]);  // ~0xB2
  TEST_ASSERT_EQUAL_HEX8((uint8_t)~frame[2], frame[3]);
  TEST_ASSERT_EQUAL_HEX8((uint8_t)~frame[4], frame[5]);
  TEST_ASSERT_EQUAL_HEX8(0xD5, frame[12]);
}

void test_structure_section2_is_copy_of_section1(void) {
  buildFrame(24, false, kModeHeat, kFan60, frame);
  TEST_ASSERT_EQUAL_MEMORY(&frame[0], &frame[6], 6);
}

void test_structure_validate_accepts_built_frames(void) {
  buildFrame(20, false, kModeCool, kFan40, frame);
  TEST_ASSERT_TRUE(validate(frame));
}

void test_structure_validate_rejects_corruption(void) {
  buildFrame(20, false, kModeCool, kFan40, frame);
  frame[9] ^= 0x01;  // break section redundancy
  TEST_ASSERT_FALSE(validate(frame));
}

// ===== Checksum (byte 17 = low byte of sum of bytes 12..16) =====

// Fixture: IRremoteESP8266 kBosch144DefaultState section 3 is
// D5 65 00 00 00 3A, and 0xD5+0x65 = 0x13A -> checksum 0x3A.
void test_checksum_library_default_state_fixture(void) {
  uint8_t section3[kStateLength] = {0};
  section3[12] = 0xD5;
  section3[13] = 0x65;
  TEST_ASSERT_EQUAL_HEX8(0x3A, checksum(section3));
}

void test_checksum_set_on_build(void) {
  buildFrame(25, false, kModeAuto, kFanAuto, frame);
  TEST_ASSERT_EQUAL_HEX8(checksum(frame), frame[17]);
}

// ===== Temperature encoding (re-findings.md byte 4 table, COOL mode) =====

static void assertTempByte4(uint8_t tempC, uint8_t expectedByte4) {
  buildFrame(tempC, false, kModeCool, kFanAuto, frame);
  TEST_ASSERT_EQUAL_HEX8(expectedByte4, frame[4]);
}

void test_temp_byte4_captured_values(void) {
  // All values below were captured from the physical remote (re-findings.md)
  assertTempByte4(16, 0x00);
  assertTempByte4(18, 0x10);
  assertTempByte4(20, 0x20);
  assertTempByte4(21, 0x60);
  assertTempByte4(22, 0x70);
  assertTempByte4(23, 0x50);
  assertTempByte4(24, 0x40);
  assertTempByte4(25, 0xC0);
  assertTempByte4(26, 0xD0);
  assertTempByte4(27, 0x90);
  assertTempByte4(30, 0xB0);
}

void test_temp_byte4_library_only_values(void) {
  // Not in the re-findings table; values from IRremoteESP8266's Celsius map.
  assertTempByte4(17, 0x00);  // distinguished from 16C by byte 15 (TempS3)
  assertTempByte4(19, 0x30);
  assertTempByte4(29, 0xA0);
  // DISCREPANCY: re-findings.md recorded 28C as 0x90 (same as 27C, which
  // would be ambiguous); the library map says 0x80. Encoding per library.
  // ROADMAP H1.0 follow-up: re-verify against the temp-28 capture.
  assertTempByte4(28, 0x80);
}

void test_temp_16_vs_17_differ_only_in_byte15(void) {
  uint8_t f16[kStateLength], f17[kStateLength];
  buildFrame(16, false, kModeCool, kFanAuto, f16);
  buildFrame(17, false, kModeCool, kFanAuto, f17);
  TEST_ASSERT_EQUAL_HEX8(f16[4], f17[4]);          // same byte 4
  TEST_ASSERT_EQUAL_HEX8(0x10, f16[15]);           // TempS3 set for 16C
  TEST_ASSERT_EQUAL_HEX8(0x00, f17[15]);
}

void test_temp_clamped_to_range(void) {
  buildFrame(10, false, kModeCool, kFanAuto, frame);
  TEST_ASSERT_EQUAL_UINT8(16, decodeTempC(frame));
  buildFrame(35, false, kModeCool, kFanAuto, frame);
  TEST_ASSERT_EQUAL_UINT8(30, decodeTempC(frame));
}

// ===== Half-degree flag (re-findings.md byte 14: 0x00 whole, 0x20 +0.5C) ==

void test_half_degree_sets_byte14_bit5(void) {
  buildFrame(20, false, kModeCool, kFanAuto, frame);
  TEST_ASSERT_EQUAL_HEX8(0x00, frame[14]);
  buildFrame(20, true, kModeCool, kFanAuto, frame);
  TEST_ASSERT_EQUAL_HEX8(0x20, frame[14]);
  TEST_ASSERT_TRUE(decodeHalfDegree(frame));
  TEST_ASSERT_TRUE(validate(frame));  // checksum still consistent
}

// ===== Mode encoding (re-findings.md byte 4 mode bits at 20C) =====

static void assertModeByte4(uint8_t mode, uint8_t expectedByte4) {
  buildFrame(20, false, mode, kFanAuto, frame);
  TEST_ASSERT_EQUAL_HEX8(expectedByte4, frame[4]);
}

void test_mode_bits_in_byte4_at_20C(void) {
  assertModeByte4(kModeCool, 0x20);  // no mode bits
  assertModeByte4(kModeDry,  0x24);  // bit 2
  assertModeByte4(kModeHeat, 0x2C);  // bits 2+3
  assertModeByte4(kModeAuto, 0x28);  // bit 3
  // NOTE: re-findings.md records the remote sending 0xE4 in FAN mode
  // (temp nibble 0xE = "no setpoint"). The library (and we) keep the last
  // temp instead; the AC accepted this during breadboard testing. The
  // mode bits (bit 2) are what matter:
  buildFrame(20, false, kModeFan, kFanAuto, frame);
  TEST_ASSERT_EQUAL_HEX8(0x24, frame[4]);
}

void test_mode_groups_in_bytes2_3(void) {
  // Group A (COOL/HEAT/FAN): bytes 2-3 follow the fan table
  buildFrame(20, false, kModeCool, kFanAuto, frame);
  TEST_ASSERT_EQUAL_HEX8(0xBF, frame[2]);
  TEST_ASSERT_EQUAL_HEX8(0x40, frame[3]);
  // Group B (DRY/AUTO): fan forced to Auto0 -> 0x1F/0xE0
  buildFrame(20, false, kModeDry, kFan80, frame);  // fan request ignored
  TEST_ASSERT_EQUAL_HEX8(0x1F, frame[2]);
  TEST_ASSERT_EQUAL_HEX8(0xE0, frame[3]);
  buildFrame(20, false, kModeAuto, kFan80, frame);
  TEST_ASSERT_EQUAL_HEX8(0x1F, frame[2]);
  TEST_ASSERT_EQUAL_HEX8(0xE0, frame[3]);
}

// ===== Fan encoding (re-findings.md fan tables, COOL mode) =====

static void assertFan(uint16_t fan, uint8_t b2, uint8_t b3, uint8_t b13) {
  buildFrame(20, false, kModeCool, fan, frame);
  TEST_ASSERT_EQUAL_HEX8(b2, frame[2]);
  TEST_ASSERT_EQUAL_HEX8(b3, frame[3]);
  TEST_ASSERT_EQUAL_HEX8(b13, frame[13]);
}

void test_fan_bytes_match_captures(void) {
  // byte 13 is the percentage in decimal (0x66 = auto) - COOL: ModeS3=0
  assertFan(kFanAuto, 0xBF, 0x40, 0x66);
  assertFan(kFan20,   0xFF, 0x00, 0x14);  // 20
  assertFan(kFan40,   0x9F, 0x60, 0x28);  // 40
  assertFan(kFan60,   0x5F, 0xA0, 0x3C);  // 60
  assertFan(kFan80,   0x3F, 0xC0, 0x50);  // 80
  assertFan(kFan100,  0x3F, 0xC0, 0x64);  // 100
}

void test_fan_80_and_100_differ_only_in_byte13(void) {
  uint8_t f80[kStateLength], f100[kStateLength];
  buildFrame(20, false, kModeCool, kFan80, f80);
  buildFrame(20, false, kModeCool, kFan100, f100);
  TEST_ASSERT_EQUAL_HEX8(f80[2], f100[2]);
  TEST_ASSERT_EQUAL_HEX8(f80[3], f100[3]);
  TEST_ASSERT_EQUAL_HEX8(0x50, f80[13]);
  TEST_ASSERT_EQUAL_HEX8(0x64, f100[13]);
}

// ===== OFF message =====

void test_off_message_is_coolix_power_off_with_inverses(void) {
  // COOLIX power off = 0xB27BE0; BOSCH144 OFF interleaves inverted bytes
  TEST_ASSERT_EQUAL_HEX8(0xB2, kOffMessage[0]);
  TEST_ASSERT_EQUAL_HEX8(0x7B, kOffMessage[2]);
  TEST_ASSERT_EQUAL_HEX8(0xE0, kOffMessage[4]);
  for (uint8_t i = 0; i <= 4; i += 2) {
    TEST_ASSERT_EQUAL_HEX8((uint8_t)~kOffMessage[i], kOffMessage[i + 1]);
  }
  // ...sent twice (section redundancy, like the main frame)
  TEST_ASSERT_EQUAL_MEMORY(&kOffMessage[0], &kOffMessage[6], 6);
}

// ===== Round trips =====

void test_roundtrip_all_settings(void) {
  const uint8_t modes[] = {kModeCool, kModeHeat, kModeFan};
  const uint16_t fans[] = {kFanAuto, kFan20, kFan40, kFan60, kFan80, kFan100};
  for (uint8_t t = kTempMinC; t <= kTempMaxC; t++) {
    for (uint8_t m = 0; m < 3; m++) {
      for (uint8_t f = 0; f < 6; f++) {
        buildFrame(t, false, modes[m], fans[f], frame);
        TEST_ASSERT_TRUE(validate(frame));
        TEST_ASSERT_EQUAL_UINT8(t, decodeTempC(frame));
        TEST_ASSERT_EQUAL_UINT8(modes[m], decodeMode(frame));
        TEST_ASSERT_EQUAL_UINT16(fans[f], decodeFan(frame));
      }
    }
  }
}

void test_roundtrip_dry_auto_force_fan_auto0(void) {
  buildFrame(22, false, kModeDry, kFan100, frame);
  TEST_ASSERT_EQUAL_UINT8(kModeDry, decodeMode(frame));
  TEST_ASSERT_EQUAL_UINT16(kFanAuto0, decodeFan(frame));
}

// ===== Test runner =====

void setUp(void) {}
void tearDown(void) {}

int main(int argc, char **argv) {
  UNITY_BEGIN();
  RUN_TEST(test_structure_headers_and_inverses);
  RUN_TEST(test_structure_section2_is_copy_of_section1);
  RUN_TEST(test_structure_validate_accepts_built_frames);
  RUN_TEST(test_structure_validate_rejects_corruption);
  RUN_TEST(test_checksum_library_default_state_fixture);
  RUN_TEST(test_checksum_set_on_build);
  RUN_TEST(test_temp_byte4_captured_values);
  RUN_TEST(test_temp_byte4_library_only_values);
  RUN_TEST(test_temp_16_vs_17_differ_only_in_byte15);
  RUN_TEST(test_temp_clamped_to_range);
  RUN_TEST(test_half_degree_sets_byte14_bit5);
  RUN_TEST(test_mode_bits_in_byte4_at_20C);
  RUN_TEST(test_mode_groups_in_bytes2_3);
  RUN_TEST(test_fan_bytes_match_captures);
  RUN_TEST(test_fan_80_and_100_differ_only_in_byte13);
  RUN_TEST(test_off_message_is_coolix_power_off_with_inverses);
  RUN_TEST(test_roundtrip_all_settings);
  RUN_TEST(test_roundtrip_dry_auto_force_fan_auto0);
  return UNITY_END();
}
