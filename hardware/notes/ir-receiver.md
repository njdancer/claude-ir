# IR Receiver

TSOP38238 receiver module for development and signal verification — loopback
testing of our own transmissions and capturing the physical remote, exactly as
the ESP8266 breadboard did. Production boards may omit it.

The module integrates the 38kHz bandpass filter, AGC, and demodulator. Output
is active-low: it pulls LOW while 38kHz-modulated IR is detected, preserving
the mark/space timing of the original transmission.

- Output goes to ESP32 GPIO19, which supports external interrupts for
  timing-accurate edge capture.
- 100nF decoupling close to VCC — the TSOP parts are sensitive to supply
  noise, which shows up as false detections.
