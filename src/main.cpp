/*
 * ESP8266 IR Controller - ActronAir AC Control
 *
 * Hardware:
 *   - ESP8266 NodeMCU
 *   - CHQ1838 IR Receiver on GPIO14 (D5) - for debugging
 *   - IR LED transmitter on GPIO4 (D2) via 2N2222 transistor
 *
 * Purpose:
 *   Full-duplex IR control for ActronAir AC unit
 *   - Receive IR signals for debugging
 *   - Transmit BOSCH144 (climate control) and COOLIX (special functions) commands
 *
 * Serial Protocol:
 *   Commands: POWER:ON|OFF, TEMP:<16-30>, MODE:<mode>, FAN:<speed>, SWING, BOOST, LED, STATE
 *   Response: OK:<message> or ERROR:<message>
 */

#include <Arduino.h>
#include <IRremoteESP8266.h>
#include <IRsend.h>
#include <IRrecv.h>
#include <IRutils.h>
#include <ir_Bosch.h>
#include <ir_Coolix.h>

// Pin Configuration
const uint16_t kIrLedPin = 4;    // GPIO4 (D2) - IR TX
const uint16_t kIrRecvPin = 14;  // GPIO14 (D5) - IR RX (debugging)

// Serial Configuration
const uint32_t kBaudRate = 115200;
const uint16_t kSerialTimeout = 5000;  // ms - Wait up to 5 seconds for newline

// IR Objects
IRsend irsend(kIrLedPin);
IRrecv irrecv(kIrRecvPin, 1024, 50, true);
IRBosch144AC acBosch(kIrLedPin);
IRCoolixAC acCoolix(kIrLedPin);

// AC State
struct ACState {
  bool power;
  float temperature;  // 16.0 to 30.0 in 0.5° steps
  uint8_t mode;       // kBosch144Cool, kBosch144Heat, etc.
  uint16_t fanSpeed;  // kBosch144FanAuto, kBosch144Fan20, etc. (uint16_t!)
} acState;

// Debug mode
bool debugMode = false;

// Special function state tracking
bool swingState = false;   // false = 0xB9F505 (OFF), true = 0xB9F504 (ON)
bool boostState = false;   // false = 0xB9F502 (OFF), true = 0xB9F501 (ON)

// Function Prototypes
void setup();
void loop();
void handleSerialCommand();
void sendBosch144Command();
void sendCoolixCommand(uint32_t code);
void printState();
String getModeString(uint8_t mode);
String getFanString(uint16_t fanSpeed);
uint8_t parseMode(const String& modeStr);
uint16_t parseFanSpeed(const String& fanStr);
bool validateTemperature(float temp);

void setup() {
  // Initialize serial
  Serial.begin(kBaudRate);
  Serial.setTimeout(kSerialTimeout);
  delay(500);

  // Print startup banner
  Serial.println();
  Serial.println(F("========================================="));
  Serial.println(F(" ActronAir IR Controller"));
  Serial.println(F("========================================="));
  Serial.println();

  // Initialize IR transmitter
  acBosch.begin();
  acCoolix.begin();
  Serial.println(F("✓ IR Transmitter initialized on GPIO4 (D2)"));

  // Initialize IR receiver (for debugging)
  irrecv.enableIRIn();
  Serial.println(F("✓ IR Receiver initialized on GPIO14 (D5)"));

  // Initialize AC state with defaults
  acState.power = false;
  acState.temperature = 22.0;
  acState.mode = kBosch144Cool;
  acState.fanSpeed = kBosch144FanAuto;

  Serial.println();
  Serial.println(F("Ready. Send commands via serial:"));
  Serial.println(F("  POWER:ON|OFF  - Power control"));
  Serial.println(F("  TEMP:<16-30>  - Set temperature (0.5° increments)"));
  Serial.println(F("  MODE:<mode>   - Set mode (COOL/HEAT/DRY/FAN/AUTO)"));
  Serial.println(F("  FAN:<speed>   - Set fan (AUTO/20/40/60/80/100)"));
  Serial.println(F("  SWING         - Toggle swing"));
  Serial.println(F("  BOOST         - Activate boost/turbo"));
  Serial.println(F("  LED           - Toggle LED display"));
  Serial.println(F("  STATE         - Query current state"));
  Serial.println(F("  DEBUG:ON|OFF  - Enable/disable IR receive echo"));
  Serial.println();
  Serial.println(F("Debug commands:"));
  Serial.println(F("  PIN:<pin>:<HIGH|LOW>      - Manually set GPIO pin"));
  Serial.println(F("                              Example: PIN:4:HIGH"));
  Serial.println(F("  RAW:<protocol>:<hex_code> - Send raw IR code"));
  Serial.println(F("                              Example: RAW:COOLIX:B27BE0"));
  Serial.println();
}

void loop() {
  // Handle serial commands
  if (Serial.available() > 0) {
    handleSerialCommand();
  }

  // Handle IR receive (debug mode)
  if (debugMode) {
    decode_results results;
    if (irrecv.decode(&results)) {
      Serial.print(F("DEBUG: Received IR - "));
      Serial.println(resultToHumanReadableBasic(&results));
      irrecv.resume();
    }
  }

  delay(10);
}

void handleSerialCommand() {
  String command = Serial.readStringUntil('\n');
  command.trim();

  if (command.length() == 0) {
    return;
  }

  // Parse command and parameter
  int colonPos = command.indexOf(':');
  String cmd = (colonPos == -1) ? command : command.substring(0, colonPos);
  String param = (colonPos == -1) ? "" : command.substring(colonPos + 1);

  cmd.toUpperCase();
  param.toUpperCase();

  // Handle commands
  if (cmd == "POWER") {
    if (param == "ON") {
      acState.power = true;
      sendBosch144Command();
      Serial.println(F("OK:Power ON, sent BOSCH144 command"));
    } else if (param == "OFF") {
      acState.power = false;
      sendCoolixCommand(0xB27BE0);  // COOLIX Power OFF
      Serial.println(F("OK:Power OFF, sent COOLIX command"));
    } else {
      Serial.println(F("ERROR:Invalid parameter. Use POWER:ON or POWER:OFF"));
    }
  }
  else if (cmd == "TEMP") {
    float temp = param.toFloat();
    if (validateTemperature(temp)) {
      acState.temperature = temp;
      acState.power = true;  // Setting temp implies power on
      sendBosch144Command();
      Serial.print(F("OK:Temperature set to "));
      Serial.print(temp, 1);
      Serial.println(F("C"));
    } else {
      Serial.println(F("ERROR:Invalid temperature. Use 16.0-30.0 in 0.5° steps"));
    }
  }
  else if (cmd == "MODE") {
    uint8_t mode = parseMode(param);
    if (mode != 255) {
      acState.mode = mode;
      acState.power = true;  // Setting mode implies power on
      sendBosch144Command();
      Serial.print(F("OK:Mode set to "));
      Serial.println(param);
    } else {
      Serial.println(F("ERROR:Invalid mode. Use COOL/HEAT/DRY/FAN/AUTO"));
    }
  }
  else if (cmd == "FAN") {
    uint16_t fanSpeed = parseFanSpeed(param);
    if (fanSpeed != 0xFFFF) {
      acState.fanSpeed = fanSpeed;
      acState.power = true;  // Setting fan implies power on
      sendBosch144Command();
      Serial.print(F("OK:Fan set to "));
      Serial.println(param);
    } else {
      Serial.println(F("ERROR:Invalid fan speed. Use AUTO/20/40/60/80/100"));
    }
  }
  else if (cmd == "SWING") {
    // Toggle between two swing states (swapped codes)
    swingState = !swingState;
    uint32_t swingCode = swingState ? 0xB9F504 : 0xB9F505;
    sendCoolixCommand(swingCode);
    Serial.print(F("OK:Swing "));
    Serial.println(swingState ? "ON" : "OFF");
  }
  else if (cmd == "BOOST") {
    // Toggle boost state
    boostState = !boostState;
    uint32_t boostCode = boostState ? 0xB9F501 : 0xB9F502;
    sendCoolixCommand(boostCode);
    Serial.print(F("OK:Boost "));
    Serial.println(boostState ? "ON" : "OFF");
  }
  else if (cmd == "LED") {
    sendCoolixCommand(0xB9F509);  // COOLIX LED toggle
    Serial.println(F("OK:LED toggled"));
  }
  else if (cmd == "STATE") {
    printState();
  }
  else if (cmd == "DEBUG") {
    if (param == "ON") {
      debugMode = true;
      Serial.println(F("OK:Debug mode enabled"));
    } else if (param == "OFF") {
      debugMode = false;
      Serial.println(F("OK:Debug mode disabled"));
    } else {
      Serial.println(F("ERROR:Invalid parameter. Use DEBUG:ON or DEBUG:OFF"));
    }
  }
  else if (cmd == "PIN") {
    // PIN:<pin>:<HIGH|LOW> - Manually control GPIO pins for debugging
    // Example: PIN:4:HIGH or PIN:D2:HIGH
    int secondColon = param.indexOf(':');
    if (secondColon == -1) {
      Serial.println(F("ERROR:Invalid format. Use PIN:<pin>:<HIGH|LOW>"));
      return;
    }

    String pinStr = param.substring(0, secondColon);
    String stateStr = param.substring(secondColon + 1);
    stateStr.toUpperCase();

    // Parse pin number (support both "4" and "D2" notation)
    uint8_t pinNum;
    if (pinStr == "D2" || pinStr == "4") {
      pinNum = 4;
    } else if (pinStr == "D5" || pinStr == "14") {
      pinNum = 14;
    } else {
      pinNum = pinStr.toInt();
    }

    // Parse state
    if (stateStr == "HIGH" || stateStr == "1") {
      pinMode(pinNum, OUTPUT);
      digitalWrite(pinNum, HIGH);
      Serial.print(F("OK:Pin "));
      Serial.print(pinNum);
      Serial.println(F(" set HIGH"));
    } else if (stateStr == "LOW" || stateStr == "0") {
      pinMode(pinNum, OUTPUT);
      digitalWrite(pinNum, LOW);
      Serial.print(F("OK:Pin "));
      Serial.print(pinNum);
      Serial.println(F(" set LOW"));
    } else {
      Serial.println(F("ERROR:Invalid state. Use HIGH or LOW"));
    }
  }
  else if (cmd == "RAW") {
    // RAW:<protocol>:<hex_code> - Send raw IR codes
    // Example: RAW:COOLIX:B27BE0 or RAW:NEC:FF00FF00
    int secondColon = param.indexOf(':');
    if (secondColon == -1) {
      Serial.println(F("ERROR:Invalid format. Use RAW:<protocol>:<hex_code>"));
      return;
    }

    String protocol = param.substring(0, secondColon);
    String hexCode = param.substring(secondColon + 1);
    protocol.toUpperCase();

    // Convert hex string to number
    uint64_t code = 0;
    for (unsigned int i = 0; i < hexCode.length(); i++) {
      char c = hexCode.charAt(i);
      code <<= 4;
      if (c >= '0' && c <= '9') {
        code |= (c - '0');
      } else if (c >= 'A' && c <= 'F') {
        code |= (c - 'A' + 10);
      } else if (c >= 'a' && c <= 'f') {
        code |= (c - 'a' + 10);
      }
    }

    if (protocol == "COOLIX") {
      irsend.sendCOOLIX(code, kCoolixBits);
      Serial.print(F("OK:Sent COOLIX code 0x"));
      Serial.println((uint32_t)code, HEX);
    } else if (protocol == "NEC") {
      irsend.sendNEC(code);
      Serial.print(F("OK:Sent NEC code 0x"));
      Serial.println((uint32_t)code, HEX);
    } else if (protocol == "BOSCH144") {
      // For BOSCH144, expect 36 hex characters (18 bytes)
      if (hexCode.length() != 36) {
        Serial.println(F("ERROR:BOSCH144 requires 36 hex characters (18 bytes)"));
        return;
      }
      uint8_t rawData[kBosch144StateLength];
      for (uint16_t i = 0; i < kBosch144StateLength; i++) {
        String byteStr = hexCode.substring(i * 2, i * 2 + 2);
        rawData[i] = strtol(byteStr.c_str(), NULL, 16);
      }
      irsend.sendBosch144(rawData);
      Serial.println(F("OK:Sent BOSCH144 raw data"));
    } else {
      Serial.print(F("ERROR:Unsupported protocol: "));
      Serial.println(protocol);
      Serial.println(F("Supported: COOLIX, NEC, BOSCH144"));
    }
  }
  else {
    Serial.print(F("ERROR:Unknown command: "));
    Serial.println(cmd);
  }
}

void sendBosch144Command() {
  // Configure BOSCH144 AC with current state
  acBosch.setPower(acState.power);
  acBosch.setTemp(acState.temperature);
  acBosch.setMode(acState.mode);
  acBosch.setFan(acState.fanSpeed);

  // Send IR command
  acBosch.send();

  #ifdef DEBUG_IR
  // Print raw state for debugging
  uint8_t* raw = acBosch.getRaw();
  Serial.print(F("DEBUG: BOSCH144 sent - "));
  for (uint16_t i = 0; i < kBosch144StateLength; i++) {
    Serial.printf("%02X ", raw[i]);
  }
  Serial.println();
  #endif
}

void sendCoolixCommand(uint32_t code) {
  // Send COOLIX command
  acCoolix.setRaw(code);
  acCoolix.send();

  #ifdef DEBUG_IR
  Serial.printf("DEBUG: COOLIX sent - 0x%06X\n", code);
  #endif
}

void printState() {
  Serial.print(F("OK:Power="));
  Serial.print(acState.power ? "ON" : "OFF");
  Serial.print(F(",Temp="));
  Serial.print(acState.temperature, 1);
  Serial.print(F(",Mode="));
  Serial.print(getModeString(acState.mode));
  Serial.print(F(",Fan="));
  Serial.println(getFanString(acState.fanSpeed));
}

String getModeString(uint8_t mode) {
  switch (mode) {
    case kBosch144Cool: return F("COOL");
    case kBosch144Heat: return F("HEAT");
    case kBosch144Dry:  return F("DRY");
    case kBosch144Fan:  return F("FAN");
    case kBosch144Auto: return F("AUTO");
    default: return F("UNKNOWN");
  }
}

String getFanString(uint16_t fanSpeed) {
  if (fanSpeed == kBosch144FanAuto) return F("AUTO");
  if (fanSpeed == kBosch144Fan20) return F("20");
  if (fanSpeed == kBosch144Fan40) return F("40");
  if (fanSpeed == kBosch144Fan60) return F("60");
  if (fanSpeed == kBosch144Fan80) return F("80");
  if (fanSpeed == kBosch144Fan100) return F("100");
  return F("UNKNOWN");
}

uint8_t parseMode(const String& modeStr) {
  if (modeStr == "COOL") return kBosch144Cool;
  if (modeStr == "HEAT") return kBosch144Heat;
  if (modeStr == "DRY")  return kBosch144Dry;
  if (modeStr == "FAN")  return kBosch144Fan;
  if (modeStr == "AUTO") return kBosch144Auto;
  return 255;  // Invalid
}

uint16_t parseFanSpeed(const String& fanStr) {
  if (fanStr == "AUTO") return kBosch144FanAuto;
  if (fanStr == "20")   return kBosch144Fan20;
  if (fanStr == "40")   return kBosch144Fan40;
  if (fanStr == "60")   return kBosch144Fan60;
  if (fanStr == "80")   return kBosch144Fan80;
  if (fanStr == "100")  return kBosch144Fan100;
  return 0xFFFF;  // Invalid (uint16_t max)
}

bool validateTemperature(float temp) {
  // Check range: 16.0 to 30.0
  if (temp < 16.0 || temp > 30.0) {
    return false;
  }

  // Check 0.5° increments
  float remainder = fmod(temp, 0.5);
  return (remainder < 0.01 || remainder > 0.49);  // Allow small floating point errors
}
