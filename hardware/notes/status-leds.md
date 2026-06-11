# Status LEDs

Visual indicators for serial activity and user-programmable status.

## Serial activity LEDs (amber)

TX and RX LEDs hang off the UART lines themselves: anode via 470Ω from 3.3V,
cathode to GPIO1 (TXD) / GPIO3 (RXD). The LED lights when the line is LOW, so
UART traffic produces the blink pattern directly — activity indication with
zero extra GPIO.

Vf ≈ 2.0V; 470Ω gives ~3mA (the 5mA design target rounded to a dimmer
standard value, fine for an indicator).

## User LEDs (blue, MOSFET-driven)

Two blue LEDs on GPIO16/GPIO17 are driven through 2N7002 N-FETs from the 5V
rail rather than directly from GPIO, because:

- Blue Vf ≈ 3.2V leaves almost no headroom from 3.3V — the 5V rail gives
  consistent brightness.
- Gate current is ~nA, so the GPIO load is negligible.
- The FET isolates the GPIO from LED faults.

Series resistors (R20/R25): fitted 1kΩ → (5 − 3.4) / 1k ≈ 1.6mA. Dimmer
than the original 150Ω/~12mA plan, but the water-clear 800mcd blues are
clearly visible at this current and it keeps the 5V rail load trivial; bump
toward 360Ω (~5mA) at rework if they look faint. Each gate has a 100kΩ
pull-down (R23/R24) for a clean off-state while GPIOs float during boot.
