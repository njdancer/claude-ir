#!/usr/bin/env python3
"""Swap J2 from the THT GCT USB-C to the SMD XKB U262-16XN (= JLCPCB C393939).

The THT receptacle's 0.85mm-pitch through-holes make the inner data/CC pins
(A5/A6/A7 + B-row) impossible to fan out — they stay unconnected. The SMD
part puts all 16 signal pads in one front-side row that can via straight down
to the B.Cu plane, so the escape is trivial. The BOM plan already calls for
this part (cheaper than the THT premium at the 5-board minimum).

The schematic symbol (USB_C_Receptacle_USB2.0_14P) names its shield pin "S1";
the stock XKB footprint names the 4 mounting posts "SH". We rename them to S1
on the instance so the shield still maps to GND (golden expects J2.S1).

  /tmp/kv10/bin/python scripts/pcb_swap_usbc.py
"""
import os
import sys
import pcbnew

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PCB = os.path.join(ROOT, "hardware", "esp32-ir-remote.kicad_pcb")
NET = os.path.join(ROOT, "hardware", "esp32-ir-remote.net")
KFP = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"
NEWLIB, NEWFP = "Connector_USB", "USB_C_Receptacle_XKB_U262-16XN-4BVC11"
NEW_CENTER = (135.0, 112.0)
NEW_ROT = 0.0

sys.path.insert(0, os.path.join(ROOT, "scripts", "ci"))
from hardware_validate import netlist_model  # noqa: E402


def main():
    part, comps, names = netlist_model(NET)
    pad_net = {}
    for nodes in part:
        nm = names[nodes]
        for ref, pad in nodes:
            if ref == "J2":
                pad_net[pad] = nm
    print("J2 netlist pads:", len(pad_net))

    b = pcbnew.LoadBoard(PCB)
    # preload new footprint before any Remove (SWIG IO-plugin curse)
    newf = pcbnew.FootprintLoad(os.path.join(KFP, NEWLIB + ".pretty"), NEWFP)
    assert newf is not None, "failed to load XKB footprint"

    old = {f.GetReference(): f for f in b.GetFootprints()}.get("J2")
    assert old is not None, "J2 not on board"
    oldval = old.GetValue()
    b.Remove(old)

    newf.SetReference("J2")
    newf.SetValue(oldval)
    newf.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(NEW_CENTER[0]),
                                     pcbnew.FromMM(NEW_CENTER[1])))
    newf.SetOrientationDegrees(NEW_ROT)
    # rename shield pads SH -> S1 so they match the symbol's shield pin
    for pad in newf.Pads():
        if pad.GetPadName() == "SH":
            pad.SetName("S1")
    b.Add(newf)

    pcbnew.SaveBoard(PCB, b)
    # reload fresh, assign nets (SWIG objects go untyped after Remove/Add)
    b = pcbnew.LoadBoard(PCB)
    netmap = {}

    def get_net(nm):
        if nm not in netmap:
            ni = b.FindNet(nm)
            if ni is None:
                ni = pcbnew.NETINFO_ITEM(b, nm); b.Add(ni)
            netmap[nm] = ni
        return netmap[nm]

    j2 = {f.GetReference(): f for f in b.GetFootprints()}["J2"]
    asg = 0
    for pad in j2.Pads():
        nm = pad_net.get(pad.GetPadName())
        if nm:
            pad.SetNet(get_net(nm)); asg += 1
        else:
            pad.SetNetCode(0)
    b.BuildListOfNets()
    pcbnew.SaveBoard(PCB, b)
    print(f"swapped J2 -> {NEWFP}, assigned {asg} pad nets")


if __name__ == "__main__":
    main()
