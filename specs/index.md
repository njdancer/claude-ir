# Specifications Index

This directory contains technical specifications for the ActronAir IR Remote Control project.

## Hardware Specifications

- [Development Board v1.4](./hardware-dev-board-v1.md) - ESP32-WROOM-32E board for IR remote control: 4× IR emitter array, IR receiver, DHT22 temp/humidity, USB-C power (AP63203 buck), CH340C UART with cross-coupled auto-reset (2N7002 MOSFETs). Connection points: I2C Qwiic, spare-GPIO + power header, external IR-emitter header, unpopulated JTAG footprint (the large DevKitC breakout header was removed in v1.2). Targets JLCPCB SMT-only assembly (LCSC Basic parts, only 3 Extended lines machine-placed) plus a hand-solder kit for all THT and easy 2-terminal SMD parts.

The KiCad project in [`hardware/`](../hardware/) is the source of truth for the board design. Per-subsystem design rationale lives in [`hardware/notes/`](../hardware/notes/README.md), and `scripts/hardware-check.sh` runs ERC and regenerates the netlist after schematic changes.

## Protocol Documentation

See [re-findings.md](../re-findings.md) in the project root for comprehensive ActronAir IR protocol reverse engineering documentation including BOSCH144 and COOLIX protocol specifications.

---

**Last Updated**: 2026-06-11
