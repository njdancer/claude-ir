#!/usr/bin/env python3
"""Thermal copper for U1 (AMS1117 SOT-223): top F.Cu pour + bottom island + vias.

The SOT-223 tab (U1 pad 2 = /LDO_OUT) dissipates ~0.85 W at the rated load; a
bare footprint gives theta_JA ~135 C/W -> T_J ~140 C (> the 125 C limit). This
script builds the standard SOT-223 cooling stack, additively and idempotently:

  1. A top-side F.Cu /LDO_OUT pour NE of the tab (the original measure).
  2. A small bottom-side B.Cu /LDO_OUT island hugging the tab. The west power
     zone is the least-bad place to slot the B.Cu ground (far from the IR_RX
     and USB returns), and it gives the thermal vias same-net copper to land on
     and a second convecting surface.
  3. A 2x3 array of thermal vias on the tab, tying the top tab/pour to the
     bottom island so heat conducts straight through the FR-4 instead of only
     leaking sideways.

The filler maintains clearance to foreign copper/pads/vias automatically, so the
island and pour shrink to fit the congested power zone (report prints the actual
filled areas). Run, then validate:

  python3.12 scripts/pcb_ldo_pour.py            # needs the pcbnew bindings
  kicad-cli pcb drc hardware/esp32-ir-remote.kicad_pcb
"""
import sys
import pcbnew

PCB = "hardware/esp32-ir-remote.kicad_pcb"
NET = "/LDO_OUT"

# Top F.Cu pour. The filler carves the U3 antenna keepout (x>=135.8, y<=81.4)
# and keeps 0.3 mm from foreign copper/pads automatically.
TOP_RECT = (123.0, 72.0, 140.0, 90.5)

# Bottom B.Cu island, bounded tight to the tab (centre ~129.15,86.0). Kept small
# on purpose: the surrounding B.Cu carries +3.3V / I2C_SCL / SPARE_TX and GND
# stitching, so a wide island would shred the ground plane. The filler clears
# 0.5 mm around all of that, so the island fills whatever clean copper remains.
BOT_RECT = (126.5, 82.0, 133.0, 89.5)

# Thermal vias on the tab (2 cols x 3 rows, 1.0 mm pitch). Placed in the south
# 2/3 of the tab to keep >0.8 mm off the /I2C_SCL via at (129.2,83.6).
VIA_XS = (128.65, 129.65)
VIA_YS = (85.0, 86.0, 87.0)
VIA_DRILL = 0.3
VIA_DIA = 0.6


def mm(v):
    return pcbnew.ToMM(v)


def add_zone(b, nc, layer, rect, name):
    z = pcbnew.ZONE(b)
    z.SetLayer(layer)
    z.SetNetCode(nc)
    z.SetAssignedPriority(1)            # win the local area over the GND pour
    z.SetLocalClearance(pcbnew.FromMM(0.3))
    z.SetMinThickness(pcbnew.FromMM(0.2))
    z.SetIsFilled(True)
    z.SetZoneName(name)
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)  # solid tab connection
    x0, y0, x1, y1 = rect
    poly = pcbnew.SHAPE_POLY_SET()
    poly.NewOutline()
    for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        poly.Append(pcbnew.FromMM(x), pcbnew.FromMM(y))
    z.SetOutline(poly)
    b.Add(z)
    return z


def main():
    b = pcbnew.LoadBoard(PCB)
    nc = b.GetNetcodeFromNetname(NET)
    if nc <= 0:
        sys.exit(f"net {NET} not found")

    # drop any previous thermal vias we placed on the tab footprint, then any
    # previous LDO pours/island (idempotent re-runs). Tracks first: removing
    # zones first leaves GetTracks() unable to iterate in this binding.
    old_vias = []
    for t in b.GetTracks():
        if t.GetClass() == "PCB_VIA" and t.GetNetname() == NET:
            x, y = mm(t.GetPosition().x), mm(t.GetPosition().y)
            if 127.5 <= x <= 131.0 and 83.5 <= y <= 88.5:
                old_vias.append(t)
    for t in old_vias:
        b.Remove(t)
    for z in list(b.Zones()):
        if not z.GetIsRuleArea() and z.GetNetname() == NET:
            b.Remove(z)

    add_zone(b, nc, pcbnew.F_Cu, TOP_RECT, "LDO_OUT_thermal")
    add_zone(b, nc, pcbnew.B_Cu, BOT_RECT, "LDO_OUT_thermal_btm")

    # thermal vias tying the tab/top pour down to the bottom island
    nvias = 0
    for x in VIA_XS:
        for y in VIA_YS:
            v = pcbnew.PCB_VIA(b)
            v.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
            v.SetDrill(pcbnew.FromMM(VIA_DRILL))
            v.SetWidth(pcbnew.FromMM(VIA_DIA))
            v.SetNetCode(nc)
            v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
            b.Add(v)
            nvias += 1

    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    pcbnew.SaveBoard(PCB, b)
    # NB: don't query filled areas here — the ZONE_FILLER leaves this process's
    # SWIG objects untyped (even a re-LoadBoard). Run measure_pour_area() in a
    # fresh process (see __main__) to report the result.
    print(f"thermal vias placed = {nvias}; board saved")


def measure_pour_area():
    """Report /LDO_OUT filled copper per layer from a freshly loaded board."""
    b = pcbnew.LoadBoard(PCB)
    areas = {}
    for i in range(b.GetAreaCount()):
        zz = b.GetArea(i)
        if zz.GetNetname() == NET:
            for lid in zz.GetLayerSet().CuStack():
                a = mm(mm(zz.GetFilledPolysList(lid).Area()))
                if a > 0.01:
                    ln = b.GetLayerName(lid)
                    areas[ln] = areas.get(ln, 0.0) + a
    for ln in sorted(areas):
        print(f"/LDO_OUT {ln} pour filled area = {areas[ln]:.1f} mm^2")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--measure":
        measure_pour_area()
    else:
        main()
