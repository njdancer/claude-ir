---
name: ESP32 IR Remote Control Development Board
description: |
  Development board for ESP32-based smart AC remote control with IR transmission.
  Designed for hand assembly with through-hole and large SMD components.

  Features:
  - USB-C power with overcurrent/overvoltage protection
  - Efficient 3.3V buck regulation (AP63203)
  - CH340C USB-to-UART bridge with auto-reset
  - ESP32-WROOM-32E WiFi+BT module
  - 4x omnidirectional IR LEDs (940nm)
  - IR receiver for development
  - DHT22 temperature/humidity sensor
  - Status LEDs for power, serial, IR, and user indication
  - DevKitC-compatible breakout header

  Board version: v1.1
---

# ESP32 IR Remote Control Development Board

A development platform for testing and developing an ESP32-based smart AC
remote control system. The board prioritizes ease of assembly and debugging
over miniaturization, with comprehensive status indicators and GPIO access.

## Global Power Nets

[VBUS]: net
[5V]: net
[3V3]: net
[GND]: net

## Subcircuits

### Power Supply

USB-C power entry with protection and 3.3V buck regulation.

[PSU]: @./power-supply.circuit.md

[PSU.VBUS --- 5V]
[PSU.3V3 --- 3V3]
[PSU.GND --- GND]

### USB-to-Serial Bridge

CH340C provides programming and serial console interface.

[SERIAL]: @./usb-serial.circuit.md

[PSU.USB_DP --- SERIAL.USB_DP]
[PSU.USB_DM --- SERIAL.USB_DM]
[SERIAL.3V3 --- 3V3]
[SERIAL.GND --- GND]

### ESP32 Microcontroller

ESP32-WROOM-32E module with boot configuration and breakout.

[MCU]: @./esp32-mcu.circuit.md

[MCU.3V3 --- 3V3]
[MCU.5V --- 5V]
[MCU.GND --- GND]

Connect auto-reset signals from USB-serial bridge to ESP32.

[SERIAL.ESP_EN --- MCU.ESP_EN]
[SERIAL.ESP_GPIO0 --- MCU.ESP_GPIO0]

Connect UART between CH340C and ESP32.

[SERIAL.TXD --- MCU.ESP_GPIO3]
[SERIAL.RXD --- MCU.ESP_GPIO1]

### IR Transmitter

Four omnidirectional IR LEDs with MOSFET driver.

[IR_TX_CIRCUIT]: @./ir-transmitter.circuit.md

[IR_TX_CIRCUIT.3V3 --- 3V3]
[IR_TX_CIRCUIT.GND --- GND]
[MCU.ESP_GPIO18 --- IR_TX_CIRCUIT.IR_TX]

### IR Receiver

38kHz IR receiver for development and signal verification.

[IR_RX_CIRCUIT]: @./ir-receiver.circuit.md

[IR_RX_CIRCUIT.3V3 --- 3V3]
[IR_RX_CIRCUIT.GND --- GND]
[IR_RX_CIRCUIT.IR_RX --- MCU.ESP_GPIO19]

### Temperature Sensor

DHT22 for "Follow Me" temperature-based AC control.

[TEMP]: @./temp-sensor.circuit.md

[TEMP.3V3 --- 3V3]
[TEMP.GND --- GND]
[TEMP.TEMP_DATA --- MCU.ESP_GPIO4]

### Status LEDs

Serial activity and user-programmable indicators.

[STATUS]: @./status-leds.circuit.md

[STATUS.3V3 --- 3V3]
[STATUS.5V --- 5V]
[STATUS.GND --- GND]
[STATUS.SERIAL_TXD --- MCU.ESP_GPIO1]
[STATUS.SERIAL_RXD --- MCU.ESP_GPIO3]
[STATUS.USER_LED1 --- MCU.ESP_GPIO16]
[STATUS.USER_LED2 --- MCU.ESP_GPIO17]

## GPIO Pin Assignments

Summary of dedicated GPIO usage:

| GPIO | Function          | Direction | Notes                    |
|------|-------------------|-----------|--------------------------|
| 0    | Boot mode         | Input     | Strapping pin, pull-up   |
| 1    | UART TXD          | Output    | Also drives TX LED       |
| 2    | (Available)       | I/O       | Strapping pin, pull-down |
| 3    | UART RXD          | Input     | Also drives RX LED       |
| 4    | Temp sensor data  | I/O       | DHT22 single-wire        |
| 15   | (Available)       | I/O       | Strapping pin, pull-down |
| 16   | User LED 1        | Output    | Blue LED via MOSFET      |
| 17   | User LED 2        | Output    | Blue LED via MOSFET      |
| 18   | IR transmit       | Output    | 38kHz modulated signal   |
| 19   | IR receive        | Input     | Demodulated signal       |

All other GPIOs available via breakout header for expansion.

## Design Rationale

### Power Architecture

Synchronous buck converter (AP63203) chosen over LDO for efficiency:
- LDO would dissipate ~0.6W as heat at typical load
- Buck converter dissipates ~0.09W, enabling smaller package
- 2A rating provides headroom for WiFi TX + IR emission peaks

### IR LED Drive

Single MOSFET drives all four LEDs for simplicity:
- All LEDs emit simultaneously for maximum coverage
- 100mA per LED provides good range with reasonable power
- 3.3V supply (not 5V) reduces resistor power dissipation

### Serial LEDs

Active-low LED drive (cathode to GPIO) provides activity indication
without consuming additional GPIO pins - the UART signals themselves
create the blinking pattern during serial communication.

### Boot Configuration

Multiple strapping pins (GPIO0, GPIO2, GPIO15) have pull resistors to
ensure reliable boot into flash execution mode. Auto-reset circuit
allows seamless programming without manual button presses.
