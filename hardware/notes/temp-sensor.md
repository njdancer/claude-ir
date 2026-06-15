# Temperature / Humidity Sensor

> **v2 (as-built): AHT20** (U5), an **I²C** temperature + humidity sensor,
> swapped in during the v2 redesign. It replaced the v1 AM2302/DHT22 single-wire
> part. Where this note disagrees with the schematic, the schematic wins.

The AHT20 provides temperature (±0.3 °C, inside the spec's ±1 °C requirement)
and relative humidity for the "Follow Me" feature, where the AC adjusts output
based on the temperature at the remote's location.

## Interface

- **I²C bus** (not single-wire): SCL on C3 **IO10** (U3 pin 10), SDA on C3
  **IO7** (U3 pin 6). The bus is also broken out on the spare header **J4**
  (SCL = pin 4, SDA = pin 3) for external I²C devices.
- **VDD** on +3.3V (pin 2), **GND** on pin 5; pins 1 and 6 are NC.
- **Decoupling:** 100 nF at VDD, placed with the sensor (see `layout.md`
  constraint 10 — U5 gets one 100 nF + 10 µF bank).

## I²C pull-ups — ⚠️ currently DNP

The bus pull-ups are **R28/R29 (4.7 kΩ to +3.3V)** on SDA/SCL, but they are
marked **DNP (do-not-populate)**. That is a leftover from v1, when the I²C bus
only fed an off-board **Qwiic** connector (J3, now removed) and Qwiic modules
bring their own pull-ups, so the on-board footprints were optional.

In v2 the AHT20 is soldered **on-board** and a bare AHT20 has **no internal
pull-ups**, so the bus needs pull-ups to work. The ESP32-C3's internal
pull-ups (~45 kΩ) are too weak to be relied on for a clean I²C bus. **R28/R29
should be populated (4.7 kΩ) in v2** unless a deliberate decision says
otherwise — flagged for the next schematic pass.

## Placement

Keep the sensor the maximum practical distance from U1 (LDO) and U3 (WiFi
self-heating) so it samples room air, not board air — see `layout.md`
constraint 5.
