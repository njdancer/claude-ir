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

## I²C pull-ups

The bus pull-ups are **R28/R29 (4.7 kΩ to +3.3V, LCSC C17936)** on SDA/SCL, and
they **are populated** (verified: schematic `dnp` clear / `in_bom yes`, PCB
footprint attr `smd`). A bare AHT20 has no internal pull-ups, so the on-board
sensor needs these; 4.7 kΩ is the standard value for a short 3.3 V bus. (The
old `esp32-mcu.md` line that called these "DNP for Qwiic" was a v1 leftover —
there is no Qwiic connector in v2; the bus serves the on-board AHT20 plus the
J4 breakout.)

## Placement

Keep the sensor the maximum practical distance from U1 (LDO) and U3 (WiFi
self-heating) so it samples room air, not board air — see `layout.md`
constraint 5.
