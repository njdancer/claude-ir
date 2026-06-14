#!/usr/bin/env python3
"""Add a top-side /LDO_OUT thermal copper pour around U1 (AMS1117 SOT-223).

Additive + idempotent: removes any prior /LDO_OUT zone, adds one F.Cu zone
bounded to the free space NE of U1's tab (clear of the U3 antenna keepout and
neighbours — the filler maintains clearance automatically), then refills all
zones. The SOT-223 tab (U1 pad 2 = /LDO_OUT) dissipates ~0.85 W at the rated
load; a bare footprint gives theta_JA ~135 C/W -> T_J ~140 C (> 125 C limit).
This pour drops theta_JA toward the area where T_J clears the limit with
margin, and the solid GND pour on B.Cu beneath spreads further through the FR-4.

  python3 scripts/pcb_ldo_pour.py
Validate: kicad-cli pcb drc hardware/esp32-ir-remote.kicad_pcb
"""
import sys
import pcbnew

PCB = "hardware/esp32-ir-remote.kicad_pcb"
NET = "/LDO_OUT"
# Bounding rectangle (mm). The filler carves the antenna keepout (x>=135.8,
# y<=81.4) and keeps 0.3 mm from foreign copper/pads automatically.
RECT = (123.0, 72.0, 140.0, 90.5)


def mm(v):
    return pcbnew.ToMM(v)


def main():
    b = pcbnew.LoadBoard(PCB)
    nc = b.GetNetcodeFromNetname(NET)
    if nc <= 0:
        sys.exit(f"net {NET} not found")

    # drop any previous LDO pour (idempotent re-runs)
    for z in list(b.Zones()):
        if not z.GetIsRuleArea() and z.GetNetname() == NET:
            b.Remove(z)

    z = pcbnew.ZONE(b)
    z.SetLayer(pcbnew.F_Cu)
    z.SetNetCode(nc)
    z.SetAssignedPriority(1)            # win the local area over the GND pour
    z.SetLocalClearance(pcbnew.FromMM(0.3))
    z.SetMinThickness(pcbnew.FromMM(0.2))
    z.SetIsFilled(True)
    z.SetZoneName("LDO_OUT_thermal")
    # solid (full) tab connection for maximum heat transfer into the pour
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)

    x0, y0, x1, y1 = RECT
    poly = pcbnew.SHAPE_POLY_SET()
    poly.NewOutline()
    for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        poly.Append(pcbnew.FromMM(x), pcbnew.FromMM(y))
    z.SetOutline(poly)
    b.Add(z)

    filler = pcbnew.ZONE_FILLER(b)
    filler.Fill(b.Zones())

    # report filled area of the new zone
    area = 0.0
    for zz in b.Zones():
        if zz.GetNetname() == NET and zz.GetLayer() == pcbnew.F_Cu:
            fp = zz.GetFilledPolysList(pcbnew.F_Cu)
            area += mm(mm(fp.Area()))
    print(f"/LDO_OUT F.Cu pour filled area = {area:.0f} mm^2")
    pcbnew.SaveBoard(PCB, b)


if __name__ == "__main__":
    main()
