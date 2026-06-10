# ESP32 MCU

ESP32-WROOM-32E-N4 module (WiFi+BT, 4MB flash) used directly rather than as a
dev board — the module integrates antenna, crystal, and RF matching, so the
board only needs to supply power, boot configuration, and GPIO breakout.

## Power and decoupling

3.3V supply with 100nF close to the VDD pin (high-frequency decoupling) plus
10µF bulk for load transients. WiFi TX bursts are the demanding case; the
spec budget allows ≤100mV droop at the module pins.

## Boot configuration (strapping pins)

| Pin | Requirement at boot | Provision |
|-----|--------------------|-----------|
| EN | HIGH for normal operation | 10kΩ pull-up + 1µF to GND (RC ≈ 10ms power-on reset delay); auto-reset Q1 can pull LOW |
| GPIO0 | HIGH = flash boot, LOW = download mode | 10kΩ pull-up; auto-reset Q2 / BOOT button pull LOW |
| GPIO2 | LOW or floating | 10kΩ pull-down |
| GPIO15 | sets UART debug output | 10kΩ pull-down — deliberately suppresses boot ROM messages |

## Manual buttons

- **RESET (SW1):** pulls EN low. Recovery from crashed firmware.
- **BOOT (SW2):** pulls GPIO0 low. Hold BOOT, press RESET, release both to
  force download mode if auto-reset fails.

## Breakout header

2×19 female header exposes all GPIO plus 3.3V, 5V, and GND rails. The pinout
deliberately matches the ESP32-DevKitC V4 so jumper-wire setups and pin
references from the DevKitC ecosystem transfer directly. The exposed power
rails are also the hook for v2 battery/power experiments on an external board
(with JP1 disabling the onboard buck).

Note: GPIO6–11 (CLK/SD0–SD3/CMD on the header) are connected to the module's
internal SPI flash. They're broken out for completeness but must not be used
as general I/O.
