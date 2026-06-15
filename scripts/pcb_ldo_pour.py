#!/usr/bin/env python3
"""Top-side F.Cu thermal pour for U1 (AMS1117 SOT-223) — owns the NW corner.

U1 was relocated into the open NW corner (floorplan: U1 @ (120,81,0), SOT-223
tab faces E at ~(123.2,81)) precisely so the thermal pour could be big and sit
in clear copper. The tab dissipates ~0.85 W at the rated load; a bare footprint
gives theta_JA ~135 C/W -> T_J ~140 C (> the 125 C limit). A large top-side
pour solidly bonded to the tab, over the unbroken B.Cu ground plane beneath,
brings theta_JA down to ~65 C/W -> T_J ~80 C at 25 C ambient.

Design choice (Nick): the pour RUNS TO THE N + W BOARD EDGES and *replaces* the
GND fill in that corner rather than carving a high-priority island out of it.
The earlier island approach left the GND fill chopped into thin slivers that the
stitching could not tie -> "isolated copper" / GND-island DRC errors. By taking
the whole corner out to the edges (priority 1, KiCad clips to the board outline
with edge clearance), the LDO pour simply owns it and GND ends cleanly at the
pour boundary, still a connected plane to the S/E. The SOT-223 tab is on F.Cu
only so this top pour is the dominant heat path; the solid B.Cu GND plane
underneath spreads further through the FR-4. (A tied B.Cu /LDO_OUT island +
thermal vias is a possible later add; deferred while the route is stabilised.)

The filler keeps 0.3 mm off foreign copper/pads (H1, J2, F1, D1, J4, U1's own
west pins) automatically; only same-net (/LDO_OUT) pads get the FULL spoke. The
zone is built INLINE in main() (not a helper): the SHAPE_POLY_SET outline must
stay referenced until after Fill() or it is GC'd and the filler reads freed
memory -> segfault. Run, then validate:

  /tmp/kv10/bin/python scripts/pcb_ldo_pour.py     # needs numpy+pcbnew bindings
  kicad-cli pcb drc hardware/esp32-ir-remote.kicad_pcb
"""
import sys
import pcbnew

PCB = "hardware/esp32-ir-remote.kicad_pcb"
NET = "/LDO_OUT"

# NW-corner pour. x0/y0 run PAST the W (106) and N (70) board edges so KiCad
# clips the fill flush to the outline (edge clearance only). East bound stops
# just W of J4 (left edge ~125.7); south bound clears the F1/D1 pocket. The
# whole rectangle is /LDO_OUT, displacing GND-F in the corner (no slivers).
TOP_RECT = (104.0, 68.0, 125.5, 87.0)


def mm(v):
    return pcbnew.ToMM(v)


def main():
    b = pcbnew.LoadBoard(PCB)
    nc = b.GetNetcodeFromNetname(NET)
    if nc <= 0:
        sys.exit(f"net {NET} not found")

    # drop any previous LDO pour (idempotent re-runs). NB: do NOT iterate
    # GetTracks() here — that corrupts this binding's SWIG state and segfaults
    # the ZONE_FILLER below. This pour adds no vias, and the pipeline's rip
    # stage clears stale vias anyway, so zone removal alone suffices.
    for z in list(b.Zones()):
        if not z.GetIsRuleArea() and z.GetNetname() == NET:
            b.Remove(z)

    # Build the pour zone INLINE (not in a helper): the SHAPE_POLY_SET outline
    # must stay referenced until after Fill(). If it is a helper-local it gets
    # GC'd on return and the filler reads a freed outline -> segfault.
    z = pcbnew.ZONE(b)
    z.SetLayer(pcbnew.F_Cu)
    z.SetNetCode(nc)
    z.SetAssignedPriority(1)            # win the local area over the GND pour
    z.SetLocalClearance(pcbnew.FromMM(0.3))
    z.SetMinThickness(pcbnew.FromMM(0.2))
    z.SetIsFilled(True)
    z.SetZoneName("LDO_OUT_thermal")
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)  # solid tab connection
    x0, y0, x1, y1 = TOP_RECT
    poly = pcbnew.SHAPE_POLY_SET()
    poly.NewOutline()
    for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        poly.Append(pcbnew.FromMM(x), pcbnew.FromMM(y))
    z.SetOutline(poly)
    b.Add(z)

    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    pcbnew.SaveBoard(PCB, b)
    # NB: don't query filled areas here — the ZONE_FILLER leaves this process's
    # SWIG objects untyped (even a re-LoadBoard). Run measure_pour_area() in a
    # fresh process (see __main__) to report the result.
    print("LDO thermal pour filled & saved")


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
