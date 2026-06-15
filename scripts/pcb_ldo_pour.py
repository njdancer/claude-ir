#!/usr/bin/env python3
"""Top-side F.Cu thermal pour for U1 (AMS1117 SOT-223).

U1 was relocated into the open NW corner (floorplan: U1 @ (120,81,0), SOT-223
tab faces E at ~(123.2,81)) precisely so the thermal pour could be big and sit
in clear copper instead of the old cramped scraps. The tab dissipates ~0.85 W
at the rated load; a bare footprint gives theta_JA ~135 C/W -> T_J ~140 C
(> the 125 C limit). A large top-side pour solidly bonded to the tab, over the
unbroken B.Cu ground plane beneath, brings theta_JA down to ~70 C/W
-> T_J ~85 C at 25 C ambient.

The SOT-223 tab is on F.Cu (top) only, so the F.Cu pour is the dominant heat
path; the bottom is the solid GND plane, coupling through the FR-4. A *second*
/LDO_OUT zone on B.Cu (a tied bottom island + thermal vias) would add a parallel
path, but the KiCad 10.0.3 zone filler segfaults whenever two overlapping
same-net F.Cu+B.Cu /LDO_OUT zones are filled together on this routed board
(the /LDO_OUT net also lands on JP1's all-layer through-hole pad). Each zone
fills fine alone; the pair does not. The bottom island is therefore deferred —
it can be added in the KiCad GUI / on CI's 10.0.2 image where the bug may not
bite. The big top pour already clears the thermal target on its own.

The filler keeps 0.3 mm off foreign copper/pads (H1, J2, F1, D1, J4, U1's own
west pins) automatically. Bounds are pulled just clear of the H1 mounting hole
(right edge ~113.5), the J2 USB pads (right ~114.5) and the N board edge: a
FULL-connection pour reaching those makes the filler degenerate its spokes and
segfault. Run, then validate:

  /tmp/kv10/bin/python scripts/pcb_ldo_pour.py     # needs numpy+pcbnew bindings
  kicad-cli pcb drc hardware/esp32-ir-remote.kicad_pcb
"""
import sys
import pcbnew

PCB = "hardware/esp32-ir-remote.kicad_pcb"
NET = "/LDO_OUT"

# Top-side pour over the whole open NW zone around U1's tab. Largest bound that
# fills cleanly (see segfault note above): ~158 mm^2 of solid copper.
TOP_RECT = (114.5, 71.5, 130.0, 87.0)


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
