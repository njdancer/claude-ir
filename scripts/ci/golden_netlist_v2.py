#!/usr/bin/env python3
"""Golden netlist for board v2 (ESP32-C3 redesign) — the machine-checkable
target for the schematic surgery.

Every intended electrical connection (≥2 pins) is listed below as a set of
"REF.PIN" tokens. The schematic surgery (delete CH340+auto-reset+buck etc.,
swap WROOM-32E→ESP32-C3 / AM2302→AHT20 / buck→AMS1117, rewire) is correct iff
the exported netlist's multi-pin partitions exactly match GOLDEN.

Comparison is name-agnostic (pin-set partitions, like hardware_validate) so it
verifies *electrical* correctness regardless of how KiCad names the nets.

Pin maps used:
  AMS1117 (U1):  1=GND  2=VO  3=VI
  ESP32-C3 (U3): 1=3V3 2=EN 3=IO4 4=IO5 5=IO6 6=IO7 7=IO8 8=IO9 9=GND 10=IO10
                 11=IO20 12=IO21 13=IO18 14=IO19 15=IO3 16=IO2 17=IO1 18=IO0 19=GND
  AHT20 (U5):    2=VDD 3=SCL 4=SDA 5=GND  (1,6 NC)

GPIO function map (C3): IO5=IR_TX IO6=IR_RX IO7=SDA IO10=SCL IO3=USER_LED1
  IO4=USER_LED2 IO9=BOOT IO18=USB_D- IO19=USB_D+ IO0/IO1/IO20/IO21=spares(J4)
  IO2/IO8=strapping pull-ups EN=reset.

Usage: python3 scripts/ci/golden_netlist_v2.py [path.kicad_sch]
       (exports the netlist via kicad-cli and diffs against GOLDEN)
"""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
from hardware_validate import netlist_model  # noqa: E402

# Each entry: the complete set of pins on one electrical net (≥2 pins).
GOLDEN = [
    # --- power ---------------------------------------------------------------
    {"F1.1", "D1.1", "C1.1", "U1.3", "R15.1", "J4.2"},                 # +5V (VBUS post-fuse)
    # AMS1117 VO drives +3.3V directly — JP1 LDO-disconnect jumper removed
    # (single supply; desolder U1 to bench-inject/prototype battery). The old
    # /LDO_OUT net is collapsed into +3.3V; the redundant +3.3V PWR_FLAG (which
    # only existed because the open jumper left the rail undriven) is gone too.
    {"U1.2", "C2.1", "C3.1", "C5.2", "C7.1", "C8.1", "C10.1",          # +3.3V
     "R5.1", "R6.1", "R7.2", "R8.2", "R9.2", "R10.2", "R11.2", "R12.2",
     "R16.1", "R27.1", "R28.1", "R29.1", "R30.1", "U3.1", "U5.2", "J4.1"},
    {"C1.2", "C2.2", "C3.2", "C5.1", "C6.2", "C7.2", "C8.2", "C9.2",   # GND
     "C10.2", "D1.2", "D6.1", "D7.1", "D10.1", "D11.1", "D12.1",
     "J2.A1", "J2.A12", "J2.B1", "J2.B12", "J2.S1", "J4.9", "J4.10",
     "Q3.2", "R1.2", "R2.1", "R14.1", "SW1.2", "SW2.2",
     "U1.1", "U3.9", "U3.19", "U4.2", "U5.5"},
    # --- USB (native, to C3) -------------------------------------------------
    {"U3.14", "J2.A6", "J2.B6"},                                       # USB_D+ -> IO19
    {"U3.13", "J2.A7", "J2.B7"},                                       # USB_D- -> IO18
    {"F1.2", "J2.A4", "J2.A9", "J2.B4", "J2.B9"},                      # VBUS in
    {"J2.A5", "R1.1"},                                                 # CC1
    {"J2.B5", "R2.2"},                                                 # CC2
    # --- I2C bus (AHT20 + pullups + spare header) ----------------------------
    {"U3.6", "U5.4", "R28.2", "J4.3"},                                 # I2C_SDA  (IO7)
    {"U3.10", "U5.3", "R29.2", "J4.4"},                                # I2C_SCL  (IO10)
    # --- reset / boot / strapping --------------------------------------------
    {"U3.2", "C6.1", "R5.2", "SW1.1"},                                 # ESP_EN
    {"U3.8", "R6.2", "SW2.1"},                                         # ESP_BOOT (IO9)
    {"U3.7", "R7.1"},                                                  # IO8 strap pull-up
    {"U3.16", "R8.1"},                                                 # IO2 strap pull-up
    # --- IR transmit ---------------------------------------------------------
    {"U3.4", "R13.2", "R19.1"},                                        # IR_TX (IO5)
    {"Q3.1", "R13.1", "R14.2"},                                        # IR_GATE
    {"D2.1", "D3.1", "D4.1", "D5.1", "J5.2", "Q3.3"},                  # IR_DRAIN
    {"D2.2", "R9.1"}, {"D3.2", "R10.1"}, {"D4.2", "R11.1"}, {"D5.2", "R12.1"},
    {"D10.2", "R19.2"},                                                # IR-TX indicator
    {"J5.1", "R30.2"},                                                 # EXT_IR_A (DNP)
    # --- IR receive ----------------------------------------------------------
    {"U3.5", "U4.1"},                                                  # IR_RX (IO6)
    {"C9.1", "R27.2", "U4.3"},                                         # IR_RX_VS filter
    # --- power-rail LEDs -----------------------------------------------------
    {"D6.2", "R15.2"},                                                 # 5V power LED
    {"D7.2", "R16.2"},                                                 # 3V3 power LED
    # --- user LEDs (direct GPIO drive) ---------------------------------------
    {"U3.15", "R25.1"},                                                # USER_LED1 (IO3)
    {"R25.2", "D11.2"},                                                # D11 anode
    {"U3.3", "R20.2"},                                                 # USER_LED2 (IO4)
    {"R20.1", "D12.2"},                                                # D12 anode
    # --- spare header GPIO ---------------------------------------------------
    {"U3.18", "J4.5"},                                                 # SPARE IO0
    {"U3.17", "J4.6"},                                                 # SPARE IO1
    {"U3.11", "J4.7"},                                                 # SPARE IO20 (U0RX)
    {"U3.12", "J4.8"},                                                 # SPARE IO21 (U0TX)
]


def export_netlist(sch):
    cli = (os.environ.get("KICAD_CLI")
           or "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli")
    out = os.path.join(tempfile.mkdtemp(), "golden.net")
    subprocess.run([cli, "sch", "export", "netlist", "--format", "kicadsexpr",
                    "-o", out, sch], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return out


def check(sch):
    net = export_netlist(sch)
    partition, _, _ = netlist_model(net)
    actual = {frozenset(f"{r}.{p}" for r, p in nodes)
              for nodes in partition if len(nodes) >= 2}
    golden = {frozenset(s) for s in GOLDEN}
    missing = golden - actual            # intended nets not yet wired right
    extra = actual - golden              # nets present that shouldn't be
    for s in sorted(missing, key=lambda x: sorted(x)):
        print("  MISSING net:", " ".join(sorted(s)))
    for s in sorted(extra, key=lambda x: sorted(x)):
        print("  UNEXPECTED net:", " ".join(sorted(s)))
    if not missing and not extra:
        print(f"GOLDEN OK — all {len(golden)} multi-pin nets match.")
        return 0
    print(f"\n{len(missing)} missing, {len(extra)} unexpected "
          f"(of {len(golden)} golden nets).")
    return 1


if __name__ == "__main__":
    sch = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        ROOT, "hardware", "esp32-ir-remote.kicad_sch")
    sys.exit(check(sch))
