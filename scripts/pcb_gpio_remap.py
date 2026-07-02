#!/usr/bin/env python3
"""GPIO remap as a search dimension: reassign nets among U3's permutable pads.

Nick (2026-06-16) unlocked GPIO remapping ("I don't care what pins we use"). On
a 2-layer board, routability is dominated by *which module pad each net attaches
to* — a signal whose pad faces away from its peripheral zone forces a crossing.
The ESP32-C3 GPIO matrix lets almost any peripheral function sit on almost any
GPIO, so we can permute net->pad so each signal exits the side facing its zone.

This tool applies a permutation to the live .kicad_pcb (a cheap routability
probe). The placement re-seat (pcb_place_v2) is net-driven, so support parts
re-cluster against the new pad automatically. See hardware/notes/autoresearch.md.

A *winning* remap is reflected into the sources of truth separately (firmware
build_flags + schematic net reattach + netlist regen); this only probes.

Pad classes on U3 (ESP32-C3-WROOM-02), from the netlist:
  free   3(IO4) 4(IO5) 5(IO6) 6(IO7) 10(IO10) 15(IO3)  -- permute freely
  spare  11(IO20) 12(IO21) 17(IO1) 18(IO0)             -- permute (->J4 breakout)
  strap  7(IO8) 16(IO2)                                -- left fixed (boot levels)
  fixed  1 2 8 9 13 14 19                              -- power/EN/BOOT/GND/USB

  pcb_gpio_remap.py show                 # print current U3 pad->net
  pcb_gpio_remap.py apply gpio.json      # gpio.json = {"<pad>": "<net>", ...}
  pcb_gpio_remap.py pins gpio.json       # print the implied firmware GPIO map
"""
import json
import sys

import pcbnew

PCB = "hardware/esp32-ir-remote.kicad_pcb"

# pad -> GPIO number (for the firmware-pin readout); from the WROOM-02 pinout.
PAD_GPIO = {
    "1": "3V3", "2": "EN", "3": 4, "4": 5, "5": 6, "6": 7, "7": 8, "8": 9,
    "9": "GND", "10": 10, "11": 20, "12": 21, "13": 18, "14": 19, "15": 3,
    "16": 2, "17": 1, "18": 0, "19": "GND",
}
FREE = {"3", "4", "5", "6", "10", "15"}
SPARE = {"11", "12", "17", "18"}
PERMUTABLE = FREE | SPARE
FIXED = {"1", "2", "7", "8", "9", "13", "14", "16", "19"}

# nets that must never be moved off their hardware pad (belt-and-braces; these
# pads are in FIXED anyway, but guard by net name too).
LOCKED_NETS = {"/USB_D+", "/USB_D-", "+3.3V", "GND", "/ESP_EN", "/ESP_BOOT"}


def u3_pad_nets(board):
    """ref pad-number -> net name for U3."""
    for f in board.GetFootprints():
        if f.GetReference() == "U3":
            return {p.GetNumber(): p.GetNetname() for p in f.Pads()
                    if p.GetNumber().isdigit()}
    sys.exit("U3 not found")


def show(board=None):
    b = board or pcbnew.LoadBoard(PCB)
    nets = u3_pad_nets(b)
    print(f"{'pad':>4} {'gpio':>5} {'class':<6} net")
    for pad in sorted(nets, key=lambda p: int(p)):
        cls = ("free" if pad in FREE else "spare" if pad in SPARE
               else "fixed" if pad in FIXED else "?")
        print(f"{pad:>4} {str(PAD_GPIO.get(pad,'?')):>5} {cls:<6} {nets[pad]}")


def validate(board, gmap):
    """gmap = {pad: net}. Must be a permutation within the mentioned permutable
    pads: every target pad is permutable + unlocked, and the multiset of
    requested nets equals the multiset currently on exactly those pads."""
    cur = u3_pad_nets(board)
    pads = set(gmap)
    bad = pads - PERMUTABLE
    if bad:
        sys.exit(f"refuse: pads {sorted(bad)} are not permutable")
    locked = {p for p in pads if cur.get(p) in LOCKED_NETS}
    if locked:
        sys.exit(f"refuse: pads {sorted(locked)} carry locked nets")
    want = sorted(gmap.values())
    have = sorted(cur[p] for p in pads)
    if want != have:
        sys.exit(f"refuse: not a permutation within {sorted(pads)}\n"
                 f"  have {have}\n  want {want}")
    return cur


def apply(gmap, board=None, save=True):
    """Apply pad->net reassignment to U3. Returns the board."""
    b = board or pcbnew.LoadBoard(PCB)
    cur = validate(b, gmap)
    u3 = next(f for f in b.GetFootprints() if f.GetReference() == "U3")
    # resolve net objects once (FindNet by name)
    for pad in u3.Pads():
        n = pad.GetNumber()
        if n in gmap and gmap[n] != cur[n]:
            ni = b.FindNet(gmap[n])
            if ni is None:
                sys.exit(f"net {gmap[n]} not found on board")
            pad.SetNet(ni)
    if save:
        pcbnew.SaveBoard(PCB, b)
        changed = {p: gmap[p] for p in gmap if gmap[p] != cur[p]}
        print(f"remapped {len(changed)} U3 pads: {changed}")
    return b


def pins(gmap):
    """Print the firmware GPIO assignment implied by a remap (net -> GPIO#)."""
    b = pcbnew.LoadBoard(PCB)
    validate(b, gmap)
    cur = u3_pad_nets(b)
    merged = {**cur, **gmap}
    net_gpio = {merged[p]: PAD_GPIO[p] for p in merged}
    fw = {"/IR_TX": "IR_LED_PIN", "/IR_RX": "IR_RECV_PIN",
          "/I2C_SDA": "I2C_SDA_PIN", "/I2C_SCL": "I2C_SCL_PIN",
          "/USER_LED1": "USER_LED1_PIN", "/USER_LED2": "USER_LED2_PIN"}
    print("implied firmware pins (platformio.ini build_flags):")
    for net, macro in fw.items():
        if net in net_gpio:
            print(f"  -D {macro}={net_gpio[net]}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "show"
    if cmd == "show":
        show()
    elif cmd == "apply":
        apply({str(k): v for k, v in json.load(open(sys.argv[2])).items()})
    elif cmd == "pins":
        pins({str(k): v for k, v in json.load(open(sys.argv[2])).items()})
    else:
        sys.exit(__doc__)
