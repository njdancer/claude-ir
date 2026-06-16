#!/usr/bin/env python3
"""Add a B.Cu keepout under the J2->U3 USB lane so the re-route is forced to
keep the D+/D- pair on F.Cu (brief item 2 — closes the "USB not a matched pair"
review item). FreeRouting can't express "this net F.Cu-only," but it DOES honour
a layer keepout that round-trips through the Specctra DSN; with B.Cu forbidden
along the lane the pair has to run on F.Cu over the solid B.Cu GND reference.

The keepout forbids TRACKS + VIAS only — the GND pour still fills it, so the
reference plane stays intact. Run BEFORE pcb_rip + pcb_route_fr:

  /usr/bin/python3.12 scripts/pcb_usb_keepout.py [x0 y0 x1 y1]
default rect = the board waist between J2 (W) and the module's USB pins (E).
"""
import sys

import pcbnew

PCB = "hardware/esp32-ir-remote.kicad_pcb"
DEFAULT = (112.0, 85.5, 160.0, 94.5)   # mm; J2 east -> U3 USB pins, USB y-band
NAME = "USB_FCu_only"


def main():
    rect = tuple(float(a) for a in sys.argv[1:5]) if len(sys.argv) >= 5 else DEFAULT
    x0, y0, x1, y1 = rect
    b = pcbnew.LoadBoard(PCB)
    # drop a previous instance so this is idempotent
    for z in list(b.Zones()):
        if z.GetIsRuleArea() and z.GetZoneName() == NAME:
            b.Remove(z)
    z = pcbnew.ZONE(b)
    z.SetIsRuleArea(True)
    z.SetZoneName(NAME)
    ls = pcbnew.LSET()
    ls.AddLayer(pcbnew.B_Cu)
    z.SetLayerSet(ls)
    z.SetDoNotAllowTracks(True)
    z.SetDoNotAllowVias(True)
    z.SetDoNotAllowCopperPour(False)      # keep the GND pour -> plane intact
    z.SetDoNotAllowPads(False)
    z.SetDoNotAllowFootprints(False)
    pts = pcbnew.VECTOR_VECTOR2I()
    for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        pts.append(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
    z.AddPolygon(pts)
    b.Add(z)
    pcbnew.SaveBoard(PCB, b)
    print(f"added B.Cu keepout {NAME} {rect}")


if __name__ == "__main__":
    main()
