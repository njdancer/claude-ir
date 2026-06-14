# ESP32 MCU

> ⚠️ **v2 (as-built): ESP32-C3-WROOM-02-N4** (LCSC C2934560), swapped in during
> the v2 cost-down redesign — see the v2 change set in
> [`ROADMAP.md`](../../ROADMAP.md). The C3 has a **native USB-Serial-JTAG**
> controller, so the CH340C bridge + auto-reset FETs were deleted (flash/monitor
> run straight over USB-C). The WROOM-32E rationale below is retained for v1
> history; where it disagrees with the schematic, the schematic wins.

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

## Expansion connectors

The original 2×19 DevKitC-style breakout header (J1) was removed in the v1.2
change set — it dominated routing for little benefit and exposed the module's
internal flash pins (GPIO6–11). Expansion is now:

- **J4 spare-GPIO header (2×5):** 3V3, 5V, GPIO23/32/33/34, 2× GND.
  GPIO25/26 were sacrificed to routing congestion during layout (pins NC'd at
  the module). Note **GPIO34 is input-only** (no output driver, no internal
  pulls) — don't try to drive it.
- **J3 Qwiic (JST-SH):** I2C on GPIO21 (SDA) / GPIO22 (SCL) with DNP 4.7k
  pull-up footprints (R28/R29) for non-Qwiic devices.
- **J6 JTAG (2×5, DNP):** ARM 10-pin layout, EN wired as nRESET.

The exposed power rails on J4 are the hook for v2 battery/power experiments
on an external board (with JP1 disabling the onboard buck).
