#!/usr/bin/env python3
"""Update the PCB to match the v2 schematic netlist (headless ECO).

KiCad's "Update PCB from Schematic" isn't exposed to kicad-cli, so this does
it in pcbnew: remove footprints no longer in the netlist, swap the footprints
that changed (preserving position/orientation), and reassign every pad's net
from the committed netlist. Run:

  /tmp/kv10/bin/python scripts/pcb_sync.py

Avoids the cursed FPID string accessors (which corrupt SWIG state) by using a
hard-coded swap table — we know exactly which footprints changed for v2.
"""
import os
import sys

import pcbnew

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "ci"))
from hardware_validate import netlist_model  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PCB = os.path.join(ROOT, "hardware", "esp32-ir-remote.kicad_pcb")
NET = os.path.join(ROOT, "hardware", "esp32-ir-remote.net")
KFP = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"

SWAPS = {
    "U1": ("Package_TO_SOT_SMD", "SOT-223-3_TabPin2"),       # buck -> AMS1117
    "U3": ("RF_Module", "ESP32-C3-WROOM-02"),                # WROOM-32E -> C3
    "U5": ("JLC-MCP", "SENSOR-SMD_L3.0-W3.0-P1.00-BR"),      # AM2302 -> AHT20
    "D6": ("LED_SMD", "LED_0805_2012Metric"),                # 3mm THT -> 0805
    "D7": ("LED_SMD", "LED_0805_2012Metric"),
    "D10": ("LED_SMD", "LED_0805_2012Metric"),
    "D11": ("LED_SMD", "LED_0805_2012Metric"),
    "D12": ("LED_SMD", "LED_0805_2012Metric"),
}


def lib_path(nick):
    if nick == "JLC-MCP":
        return os.path.join(ROOT, "hardware", "libraries", "footprints",
                            "JLC-MCP.pretty")
    return os.path.join(KFP, nick + ".pretty")


def main():
    part, comps, names = netlist_model(NET)
    want_fp = set(comps)
    pad_net = {}
    for nodes in part:
        nm = names[nodes]
        for ref, pad in nodes:
            pad_net[(ref, pad)] = nm

    b = pcbnew.LoadBoard(PCB)
    on_board = {f.GetReference(): f for f in b.GetFootprints()}

    # 0) pre-load the swap footprints NOW — pcbnew's cached IO plugin goes
    #    untyped after a batch of Remove() calls, so FootprintLoad must run
    #    before any removal.
    loaded = {}
    for ref, (nick, name) in SWAPS.items():
        loaded[ref] = pcbnew.FootprintLoad(lib_path(nick), name)
        if loaded[ref] is None:
            print("  FAILED preload %s:%s for %s" % (nick, name, ref))

    # 1) remove footprints no longer in the netlist (keep mounting holes H*)
    removed = []
    for ref, f in list(on_board.items()):
        if ref.startswith("H") and ref[1:].isdigit():
            continue
        if ref not in want_fp:
            b.Remove(f)
            del on_board[ref]
            removed.append(ref)
    print("removed (%d):" % len(removed), " ".join(sorted(removed)))

    # 2) swap changed footprints, preserving placement
    swapped = []
    for ref, (nick, name) in SWAPS.items():
        f = on_board.get(ref)
        if f is None or loaded.get(ref) is None:
            continue
        newf = loaded[ref]
        newf.SetReference(ref)
        newf.SetValue(comps[ref][0])
        newf.SetPosition(f.GetPosition())
        newf.SetOrientation(f.GetOrientation())
        b.Remove(f)
        b.Add(newf)
        on_board[ref] = newf
        swapped.append("%s->%s" % (ref, name))
    print("swapped (%d):" % len(swapped), " ".join(swapped))

    # persist structural changes, then reload fresh — the footprint/pad SWIG
    # objects go untyped after the batch of Remove/Add, so net assignment must
    # run on a freshly-loaded board.
    pcbnew.SaveBoard(PCB, b)
    b = pcbnew.LoadBoard(PCB)

    # 3) reassign nets on every pad from the netlist
    netmap = {}

    def get_net(nm):
        if nm not in netmap:
            ni = b.FindNet(nm)
            if ni is None:
                ni = pcbnew.NETINFO_ITEM(b, nm)
                b.Add(ni)
            netmap[nm] = ni
        return netmap[nm]

    assigned = unassigned = 0
    for f in b.GetFootprints():
        ref = f.GetReference()
        for pad in f.Pads():
            nm = pad_net.get((ref, pad.GetPadName()))
            if nm:
                pad.SetNet(get_net(nm))
                assigned += 1
            else:
                pad.SetNetCode(0)
                unassigned += 1
    print("pads: %d assigned, %d unassigned" % (assigned, unassigned))

    b.BuildListOfNets()
    pcbnew.SaveBoard(PCB, b)
    print("saved", len(b.GetFootprints()), "footprints.")


if __name__ == "__main__":
    main()
