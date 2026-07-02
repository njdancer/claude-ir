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
# The LDO output is the +3.3V rail itself now: the JP1 LDO-disconnect jumper was
# removed and the old /LDO_OUT net collapsed into +3.3V (single-supply design;
# desolder U1 to bench-inject). The SOT-223 tab pad is +3.3V, so the thermal
# pour bonds to it on the +3.3V net and simply becomes rail copper in the NW
# corner — a better heat path than the old isolated /LDO_OUT island.
NET = "+3.3V"

# Board outline (mm) — pour rects run PAST the relevant edge so KiCad clips the
# fill flush to the outline (edge clearance only).
BX0, BY0, BX1, BY1 = 106.0, 70.0, 198.0, 114.0


def mm(v):
    return pcbnew.ToMM(v)


def ldo_rect(b):
    """Generous +3.3V thermal-pour rectangle around U1's tab, biased to the
    nearest board edge (heat sink) and reaching ~14mm inboard + ~11mm laterally
    into open copper. KiCad clips to the outline and carves 0.3mm around foreign
    parts, so the pour fills whatever open copper U1 actually has -- making
    'U1 needs spare space for a big pour' (Nick, 2026-06-16) a property the
    layout/score can optimise rather than a hardcoded corner. Tracks U1 wherever
    the floorplan/search puts it."""
    u1 = next((f for f in b.GetFootprints() if f.GetReference() == "U1"), None)
    if u1 is None:
        return (104.0, 68.0, 125.5, 87.0)        # legacy fallback
    tab = next((p for p in u1.Pads() if p.GetNumber() == "2"), None)  # VOUT tab
    p = (tab or u1).GetPosition()
    tx, ty = mm(p.x), mm(p.y)
    L, DEPTH = 19.0, 21.0    # lifted stepwise 11/14 -> 19/21 by the r2 ratchet
                             # loop (Nick 2026-07-02: "much larger pour"); the
                             # filler carves foreign parts, so the generous
                             # rect only claims whatever copper is open
    dN, dS, dW, dE = ty - BY0, BY1 - ty, tx - BX0, BX1 - tx
    m = min(dN, dS, dW, dE)
    # corner-aware: when the tab is also within L of a SECOND edge, run the
    # rect past that edge too, so the pour owns the whole corner
    if m in (dN, dS):
        x0 = BX0 - 2 if dW < L else tx - L
        x1 = BX1 + 2 if dE < L else tx + L
        if m == dN:                              # nearest the N edge
            return (x0, BY0 - 2, x1, ty + DEPTH)
        return (x0, ty - DEPTH, x1, BY1 + 2)
    y0 = BY0 - 2 if dN < L else ty - L
    y1 = BY1 + 2 if dS < L else ty + L
    if m == dW:
        return (BX0 - 2, y0, tx + DEPTH, y1)
    return (tx - DEPTH, y0, BX1 + 2, y1)         # nearest the E edge


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
    x0, y0, x1, y1 = ldo_rect(b)
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
        print(f"{NET} {ln} pour filled area = {areas[ln]:.1f} mm^2")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--measure":
        measure_pour_area()
    else:
        main()
