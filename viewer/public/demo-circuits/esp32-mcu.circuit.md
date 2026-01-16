---
name: ESP32 MCU
description: |
  ESP32-WROOM-32E module with boot configuration and breakout header.

  Exposed nets:
  - 3V3: 3.3V power supply
  - GND: Ground
  - ESP_EN: Enable pin (directly to module)
  - ESP_GPIO0: Boot mode pin (directly to module)
  - ESP_GPIO1: UART TXD (directly to module)
  - ESP_GPIO3: UART RXD (directly to module)
  - ESP_GPIO2: Directly to module
  - ESP_GPIO4: Directly to module (used for temp sensor)
  - ESP_GPIO5-GPIO39: Directly to module
  - ESP_GPIO16: User LED 1 control
  - ESP_GPIO17: User LED 2 control
  - ESP_GPIO18: IR transmit control
  - ESP_GPIO19: IR receive input
---

# ESP32 MCU

ESP32-WROOM-32E-N4 module provides WiFi+BT connectivity with 4MB flash.
The module includes integrated antenna, crystal, and RF matching - we just
need power, boot configuration, and GPIO breakout.

## Power and Signal Nets

[3V3]: net
[GND]: net
[ESP_EN]: net
[ESP_GPIO0]: net
[ESP_GPIO1]: net
[ESP_GPIO2]: net
[ESP_GPIO3]: net
[ESP_GPIO4]: net
[ESP_GPIO5]: net
[ESP_GPIO6]: net
[ESP_GPIO7]: net
[ESP_GPIO8]: net
[ESP_GPIO9]: net
[ESP_GPIO10]: net
[ESP_GPIO11]: net
[ESP_GPIO12]: net
[ESP_GPIO13]: net
[ESP_GPIO14]: net
[ESP_GPIO15]: net
[ESP_GPIO16]: net
[ESP_GPIO17]: net
[ESP_GPIO18]: net
[ESP_GPIO19]: net
[ESP_GPIO21]: net
[ESP_GPIO22]: net
[ESP_GPIO23]: net
[ESP_GPIO25]: net
[ESP_GPIO26]: net
[ESP_GPIO27]: net
[ESP_GPIO32]: net
[ESP_GPIO33]: net
[ESP_GPIO34]: net
[ESP_GPIO35]: net
[ESP_SEN_VP]: net
[ESP_SEN_VN]: net

## ESP32 Module

[U3]: esp32_wroom_32e

### Power Connections

Module requires 3.3V with good decoupling. Multiple GND pins ensure
low impedance ground path.

[3V3 --- U3.VDD]
[U3.GND --- GND]

### Decoupling Capacitors

100nF close to VDD pin for high-frequency decoupling.
10µF for bulk capacitance and load transient support.

[3V3 --- 100nF --- GND]
[3V3 --- 10µF --- GND]

## Boot Configuration

### EN Pin (Chip Enable)

EN must be HIGH for normal operation. 10kΩ pull-up provides default HIGH.
1µF capacitor creates RC delay [t_delay ==> 10ms] for reliable power-on reset.
The auto-reset circuit (Q1) can pull EN LOW to reset the chip.

[3V3 --- 10kΩ --- ESP_EN]
[ESP_EN --- 1µF --- GND]
[ESP_EN --- U3.EN]

### GPIO0 (Boot Mode Selection)

GPIO0 must be HIGH for normal boot (flash execution).
LOW during reset enters download mode (serial programming).
10kΩ pull-up provides default HIGH. Auto-reset circuit (Q2) can pull LOW.

[3V3 --- 10kΩ --- ESP_GPIO0]
[ESP_GPIO0 --- U3.IO0]

### GPIO2 (Strapping Pin)

Must be LOW or floating during boot. 10kΩ pull-down ensures clean boot.
Also used for onboard status indication in some applications.

[ESP_GPIO2 --- 10kΩ --- GND]
[ESP_GPIO2 --- U3.IO2]

### GPIO15 (Strapping Pin)

Must be HIGH during boot (enables UART debug output).
10kΩ pull-down is used here to suppress boot messages.

[ESP_GPIO15 --- 10kΩ --- GND]
[ESP_GPIO15 --- U3.IO15]

## Manual Control Buttons

### RESET Button (SW1)

Momentary switch pulls EN LOW to reset the chip.
Useful for manual reset or recovery from crashed firmware.

[SW1]: switch_momentary

[ESP_EN --- SW1.1]
[SW1.2 --- GND]

### BOOT Button (SW2)

Momentary switch pulls GPIO0 LOW for manual bootloader entry.
Usage: Hold BOOT, press RESET, release both to enter programming mode.

[SW2]: switch_momentary

[ESP_GPIO0 --- SW2.1]
[SW2.2 --- GND]

## GPIO Connections

### UART0 (Programming/Debug)

GPIO1 (TXD) and GPIO3 (RXD) connect to USB-serial bridge.

[ESP_GPIO1 --- U3.IO1]
[ESP_GPIO3 --- U3.IO3]

### Peripheral GPIOs

All other GPIOs connect directly to module and breakout header.

[ESP_GPIO4 --- U3.IO4]
[ESP_GPIO5 --- U3.IO5]
[ESP_GPIO6 --- U3.IO6]
[ESP_GPIO7 --- U3.IO7]
[ESP_GPIO8 --- U3.IO8]
[ESP_GPIO9 --- U3.IO9]
[ESP_GPIO10 --- U3.IO10]
[ESP_GPIO11 --- U3.IO11]
[ESP_GPIO12 --- U3.IO12]
[ESP_GPIO13 --- U3.IO13]
[ESP_GPIO14 --- U3.IO14]
[ESP_GPIO16 --- U3.IO16]
[ESP_GPIO17 --- U3.IO17]
[ESP_GPIO18 --- U3.IO18]
[ESP_GPIO19 --- U3.IO19]
[ESP_GPIO21 --- U3.IO21]
[ESP_GPIO22 --- U3.IO22]
[ESP_GPIO23 --- U3.IO23]
[ESP_GPIO25 --- U3.IO25]
[ESP_GPIO26 --- U3.IO26]
[ESP_GPIO27 --- U3.IO27]
[ESP_GPIO32 --- U3.IO32]
[ESP_GPIO33 --- U3.IO33]
[ESP_GPIO34 --- U3.IO34]
[ESP_GPIO35 --- U3.IO35]
[ESP_SEN_VP --- U3.SENSOR_VP]
[ESP_SEN_VN --- U3.SENSOR_VN]

## Breakout Header

2x19 female header exposes all GPIO pins plus power rails.
Pinout matches ESP32-DevKitC V4 for jumper wire compatibility.

[J1]: esp32_breakout_header

### Power Pins

[3V3 --- J1.3V3]
[J1.5V --- 5V]: net
[5V]: net
[J1.GND --- GND]

### GPIO Pins (directly wired through)

All GPIO nets connect to corresponding header pins.
Pin assignments match DevKitC V4 layout (see reference design).

[ESP_EN --- J1.EN]
[ESP_GPIO0 --- J1.IO0]
[ESP_GPIO1 --- J1.TXD0]
[ESP_GPIO2 --- J1.IO2]
[ESP_GPIO3 --- J1.RXD0]
[ESP_GPIO4 --- J1.IO4]
[ESP_GPIO5 --- J1.IO5]
[ESP_GPIO6 --- J1.CLK]
[ESP_GPIO7 --- J1.SD0]
[ESP_GPIO8 --- J1.SD1]
[ESP_GPIO9 --- J1.SD2]
[ESP_GPIO10 --- J1.SD3]
[ESP_GPIO11 --- J1.CMD]
[ESP_GPIO12 --- J1.IO12]
[ESP_GPIO13 --- J1.IO13]
[ESP_GPIO14 --- J1.IO14]
[ESP_GPIO15 --- J1.IO15]
[ESP_GPIO16 --- J1.IO16]
[ESP_GPIO17 --- J1.IO17]
[ESP_GPIO18 --- J1.IO18]
[ESP_GPIO19 --- J1.IO19]
[ESP_GPIO21 --- J1.IO21]
[ESP_GPIO22 --- J1.IO22]
[ESP_GPIO23 --- J1.IO23]
[ESP_GPIO25 --- J1.IO25]
[ESP_GPIO26 --- J1.IO26]
[ESP_GPIO27 --- J1.IO27]
[ESP_GPIO32 --- J1.IO32]
[ESP_GPIO33 --- J1.IO33]
[ESP_GPIO34 --- J1.IO34]
[ESP_GPIO35 --- J1.IO35]
[ESP_SEN_VP --- J1.VP]
[ESP_SEN_VN --- J1.VN]
