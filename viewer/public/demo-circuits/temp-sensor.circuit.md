---
name: Temperature Sensor
description: |
  DHT22/AM2302 temperature and humidity sensor module.

  Exposed nets:
  - 3V3: 3.3V power supply
  - GND: Ground
  - TEMP_DATA: Single-wire data (to ESP32 GPIO4)
---

# Temperature Sensor

AM2302 (DHT22) provides temperature (±0.5°C) and humidity sensing
for "Follow Me" AC control functionality.

Single-wire proprietary protocol communicates with ESP32.

## Interface Nets

[3V3]: net
[GND]: net
[TEMP_DATA]: net

## Sensor Module

[U5]: dht22(AM2302)

### Power Connections

[3V3 --- U5.VDD]
[U5.GND --- GND]

### Data Line

Single-wire bidirectional data. 10kΩ pull-up required
(often included on module, but we add one for reliability).

[U5.DATA --- TEMP_DATA]
[3V3 --- 10kΩ --- TEMP_DATA]
