/*
 * BOSCH144 protocol frame construction for ActronAir (rebranded Midea) AC.
 *
 * Pure C++ (no Arduino dependencies) so it runs in native host tests.
 * Bit layout mirrors IRremoteESP8266's ir_Bosch.{h,cpp} (Bosch144Protocol
 * union), cross-checked against our own captures documented in
 * re-findings.md. Uses explicit shifts/masks instead of bitfields for
 * portability between xtensa and host.
 *
 * Frame structure (18 bytes / 144 bits):
 *   bytes 0-5   Section 1: header 0xB2, fan + mode + temp, with each odd
 *               byte the bitwise inverse of the preceding even byte
 *   bytes 6-11  Section 2: exact copy of Section 1 (redundancy)
 *   bytes 12-17 Section 3: footer 0xD5, fan/mode/temp detail bits,
 *               checksum = low byte of sum(bytes 12..16)
 *
 * Power OFF is a separate 96-bit message (kOffMessage) identical to the
 * COOLIX 0xB27BE0 command with inverted-byte pairs.
 */

#ifndef BOSCH144_PROTOCOL_H_
#define BOSCH144_PROTOCOL_H_

#include <stdint.h>
#include <string.h>

namespace bosch144 {

constexpr uint8_t kStateLength = 18;
constexpr uint8_t kOffMessageLength = 12;

// Mode encoding: bit 0 -> Section 3 (byte 13 bit 0), bits 1-2 -> Section 1
// (byte 4 bits 2-3). Values match IRremoteESP8266's kBosch144* constants.
constexpr uint8_t kModeCool = 0b000;
constexpr uint8_t kModeDry  = 0b011;
constexpr uint8_t kModeAuto = 0b101;
constexpr uint8_t kModeHeat = 0b110;
constexpr uint8_t kModeFan  = 0b010;

// Fan encoding: bits 0-5 -> Section 3 (byte 13 bits 1-6), bits 6-8 ->
// Section 1 (byte 2 bits 5-7). Byte 13 works out to the fan percentage in
// decimal (0x66 = "auto"), which is how re-findings.md discovered it.
constexpr uint16_t kFan20    = 0b111001010;
constexpr uint16_t kFan40    = 0b100010100;
constexpr uint16_t kFan60    = 0b010011110;
constexpr uint16_t kFan80    = 0b001101000;
constexpr uint16_t kFan100   = 0b001110010;
constexpr uint16_t kFanAuto  = 0b101110011;
constexpr uint16_t kFanAuto0 = 0b000110011;  // forced in DRY/AUTO modes

constexpr uint8_t kTempMinC = 16;
constexpr uint8_t kTempMaxC = 30;

// Per-degree code: bits 2-5 -> byte 4 high nibble (TempS1), bit 1 -> byte 15
// bit 4 (TempS3), bit 0 -> byte 14 bit 5 (TempS4, also the half-degree flag
// for Celsius). Non-linear (Gray-code-like); validated against captures for
// all temps in re-findings.md except 17/19/28/29C which come from the
// IRremoteESP8266 map (re-findings recorded 28C as 0x90, the library says
// 0x80 - flagged for bench re-verification, see ROADMAP).
constexpr uint8_t kCelsiusMap[15] = {
    0b000010,  // 16C
    0b000000,  // 17C
    0b000100,  // 18C
    0b001100,  // 19C
    0b001000,  // 20C
    0b011000,  // 21C
    0b011100,  // 22C
    0b010100,  // 23C
    0b010000,  // 24C
    0b110000,  // 25C
    0b110100,  // 26C
    0b100100,  // 27C
    0b100000,  // 28C
    0b101000,  // 29C
    0b101100,  // 30C
};

// Power OFF (96 bits): COOLIX 0xB27BE0 expanded with inverted-byte pairs,
// sent twice. Identical to IRremoteESP8266's kBosch144Off.
constexpr uint8_t kOffMessage[kOffMessageLength] = {
    0xB2, 0x4D, 0x7B, 0x84, 0xE0, 0x1F,
    0xB2, 0x4D, 0x7B, 0x84, 0xE0, 0x1F};

/// Checksum for Section 3: low byte of the sum of bytes 12..16.
inline uint8_t checksum(const uint8_t frame[kStateLength]) {
  uint16_t sum = 0;
  for (uint8_t i = 12; i <= 16; i++) sum += frame[i];
  return static_cast<uint8_t>(sum);
}

/// Recompute byte 17 in place. Call after any manual frame edit.
inline void updateChecksum(uint8_t frame[kStateLength]) {
  frame[17] = checksum(frame);
}

/// Build a complete 18-byte ON/state frame.
/// @param tempC Whole degrees Celsius, 16-30 (clamped).
/// @param halfDegree Add 0.5C (sets TempS4 / byte 14 bit 5).
/// @param mode One of kMode*.
/// @param fan One of kFan*. Ignored (forced to kFanAuto0) in DRY/AUTO,
///        matching both the library and the physical remote's behaviour.
/// @param quiet Quiet/silent mode flag (byte 14 bit 7).
inline void buildFrame(uint8_t tempC, bool halfDegree, uint8_t mode,
                       uint16_t fan, uint8_t frame[kStateLength],
                       bool quiet = false) {
  if (tempC < kTempMinC) tempC = kTempMinC;
  if (tempC > kTempMaxC) tempC = kTempMaxC;
  const uint8_t tempCode = kCelsiusMap[tempC - kTempMinC];
  const uint8_t tempS1 = tempCode >> 2;
  const uint8_t tempS3 = (tempCode >> 1) & 0b1;
  // For Celsius, bit 0 of the map is always 0; the half-degree flag lives in
  // the same bit position (TempS4).
  const uint8_t tempS4 = (tempCode & 0b1) | (halfDegree ? 1 : 0);

  const uint8_t modeS1 = mode >> 1;
  const uint8_t modeS3 = mode & 0b1;

  if (mode == kModeAuto || mode == kModeDry) fan = kFanAuto0;
  const uint8_t fanS1 = fan >> 6;
  const uint8_t fanS3 = fan & 0b111111;

  frame[0] = 0xB2;
  // Byte 2 low 5 bits are timer fields, observed all-ones when no timer.
  frame[2] = static_cast<uint8_t>(fanS1 << 5) | 0b00011111;
  // Byte 4 low 2 bits are timer fields, observed zero when no timer.
  frame[4] = static_cast<uint8_t>(tempS1 << 4) |
             static_cast<uint8_t>(modeS1 << 2);
  frame[1] = ~frame[0];
  frame[3] = ~frame[2];
  frame[5] = ~frame[4];
  memcpy(&frame[6], &frame[0], 6);  // Section 2 = copy of Section 1

  frame[12] = 0xD5;
  frame[13] = static_cast<uint8_t>(fanS3 << 1) | modeS3;
  frame[14] = static_cast<uint8_t>(tempS4 << 5) |
              static_cast<uint8_t>((quiet ? 1 : 0) << 7);
  frame[15] = static_cast<uint8_t>(tempS3 << 4);  // bit 0 = Fahrenheit, unused
  frame[16] = 0x00;
  updateChecksum(frame);
}

/// Structural validation per re-findings.md "Validation Rules" plus the
/// Section 3 checksum. True if the frame is internally consistent.
inline bool validate(const uint8_t frame[kStateLength]) {
  if (frame[0] != 0xB2 || frame[12] != 0xD5) return false;
  for (uint8_t i = 0; i <= 4; i += 2) {
    if (frame[i + 1] != static_cast<uint8_t>(~frame[i])) return false;
  }
  if (memcmp(&frame[0], &frame[6], 6) != 0) return false;
  return frame[17] == checksum(frame);
}

/// Extract whole degrees Celsius from a frame (half degree via byte 14).
/// Returns 0 if the temp code is not in the Celsius map.
inline uint8_t decodeTempC(const uint8_t frame[kStateLength]) {
  const uint8_t code = static_cast<uint8_t>(((frame[4] >> 4) << 2) |
                                            (((frame[15] >> 4) & 0b1) << 1));
  for (uint8_t i = 0; i < sizeof(kCelsiusMap); i++) {
    // Compare ignoring bit 0 (half-degree flag is carried separately).
    if ((kCelsiusMap[i] & ~0b1) == code) return kTempMinC + i;
  }
  return 0;
}

inline bool decodeHalfDegree(const uint8_t frame[kStateLength]) {
  return (frame[14] & 0b100000) != 0;
}

inline uint8_t decodeMode(const uint8_t frame[kStateLength]) {
  return static_cast<uint8_t>((((frame[4] >> 2) & 0b11) << 1) |
                              (frame[13] & 0b1));
}

inline uint16_t decodeFan(const uint8_t frame[kStateLength]) {
  return static_cast<uint16_t>(((frame[2] >> 5) << 6) |
                               ((frame[13] >> 1) & 0b111111));
}

}  // namespace bosch144

#endif  // BOSCH144_PROTOCOL_H_
