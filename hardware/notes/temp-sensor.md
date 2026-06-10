# Temperature Sensor

AM2302 (DHT22) provides temperature (±0.5°C, comfortably inside the spec's
±1°C requirement) and humidity sensing for the "Follow Me" feature, where the
AC adjusts output based on temperature at the remote's location.

- Single-wire bidirectional data line on ESP32 GPIO4.
- 10kΩ pull-up on the data line. Modules often include one onboard, but the
  board fits its own for reliability with bare sensors.
