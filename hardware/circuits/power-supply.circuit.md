---
name: Power Supply
description: |
  USB-C power input with protection and 3.3V buck regulation.

  Exposed nets:
  - VBUS: 5V input from USB-C (after fuse)
  - 3V3: Regulated 3.3V output
  - GND: Ground reference
  - USB_DP: USB D+ data line
  - USB_DM: USB D- data line
---

# Power Supply

USB-C power entry with overcurrent and overvoltage protection, followed by
a synchronous buck converter for efficient 3.3V regulation.

## Power Nets

[VBUS]: net
[3V3]: net
[GND]: net
[USB_DP]: net
[USB_DM]: net

## USB-C Connector

[J2]: usb_c_receptacle_14p

The USB-C receptacle provides 5V power and USB 2.0 data lines.
Shield connects to ground for EMI shielding.

[J2.VBUS --- VBUS_RAW]: net
[VBUS_RAW]: net
[J2.GND --- GND]
[J2.SHIELD --- GND]
[J2.DP --- USB_DP]
[J2.DM --- USB_DM]

USB-C requires 5.1kΩ pull-downs on CC lines to advertise as a
5V sink device (default USB power).

[J2.CC1 --- 5.1kΩ --- GND]
[J2.CC2 --- 5.1kΩ --- GND]

## Input Protection

### Overcurrent Protection

PTC resettable fuse trips at ~2A to protect against shorts.
Hold current [i_hold ==> 1.1A], trip current [i_trip ==> 2.2A].

[F1]: polyfuse(1.1A)

[VBUS_RAW --- F1.1]
[F1.2 --- VBUS_FUSED]: net
[VBUS_FUSED]: net

### Overvoltage Protection

TVS diode clamps voltage spikes below [v_clamp ==> 6.5V] to protect
the buck converter (max input ~32V but we want fast clamping).

[D1]: tvs_diode

[VBUS_FUSED --- D1.A]
[D1.K --- GND]
[VBUS_FUSED --- VBUS]

## Buck Converter

AP63203WU synchronous buck converter provides efficient 3.3V regulation.
Fixed output voltage, no feedback resistors needed.
Switching frequency [f_sw ==> 1.1MHz] enables small passives.

[U1]: ap63203

[VBUS --- U1.VIN]
[U1.GND --- GND]
[U1.FB --- 3V3]

### Enable Control

Jumper JP1 allows disabling the buck converter for external power testing.
EN pin has internal pull-up to VIN, so open = enabled (normal operation).

[JP1]: jumper_2_open

[U1.EN --- JP1.B]
[JP1.A --- GND]

### Bootstrap Capacitor

100nF bootstrap cap between BST and SW for high-side gate drive.

[BST_NET]: net
[SW_NET]: net

[U1.BST --- BST_NET]
[U1.SW --- SW_NET]
[BST_NET --- 100nF --- SW_NET]

### Output Inductor

3.9µH inductor with [i_sat ==> 2.7A] saturation current.
Low DCR minimizes power loss.

[L1]: inductor(3.9µH)

[SW_NET --- L1.1]
[L1.2 --- 3V3]

### Input Capacitor

10µF ceramic on input for stability during load transients.

[VBUS --- 10µF --- GND]

### Output Capacitors

Two 22µF ceramics in parallel for low ESR and ripple.

[3V3 --- 22µF --- GND]
[3V3 --- 22µF --- GND]

## Power Indicators

### 5V Rail Indicator

Red LED indicates USB power present (before buck converter).
Vf ≈ 1.9V, target [i_led_5v ==> 5mA], R = (5 - 1.9) / 0.005 = 620Ω, use 150Ω for brighter indication.

[D6]: led(red)

[VBUS --- 150Ω --- D6.A]
[D6.K --- GND]

### 3.3V Rail Indicator

Green LED indicates regulated 3.3V present (after buck converter).
Vf ≈ 2.0V, target [i_led_3v3 ==> 3mA], R = (3.3 - 2.0) / 0.003 = 433Ω, use 150Ω.

[D7]: led(green)

[3V3 --- 150Ω --- D7.A]
[D7.K --- GND]
