#!/usr/bin/env python3
"""GND pours + antenna keepout + stitching vias for esp32-ir-remote.

Run AFTER scripts/pcb_router.py:
  tools/kicad-mcp-server/.venv/bin/python3 scripts/pcb_pour.py
Validation: kicad-cli pcb drc (unconnected items + clearance).
"""
import math
import sys

import pcbnew

BOARD_PATH = "hardware/esp32-ir-remote.kicad_pcb"
# new long-thin outline
X0, Y0, X1, Y1 = 106.0, 70.0, 198.0, 114.0
VIA_PITCH = 4.0         # stitching grid
VIA_D, VIA_DRILL = 0.6, 0.3
TIE_VIA_D, TIE_DRILL = 0.5, 0.3    # smaller body for island ties in tight spots
                                   # (0.5/0.3 = the router's signal via, annular-OK)
CLEAR = 0.35            # via-to-foreign-copper margin for stitching


def rect_chain(x0, y0, x1, y1):
    pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    ch = pcbnew.SHAPE_LINE_CHAIN()
    for x, y in pts:
        ch.Append(pcbnew.FromMM(x), pcbnew.FromMM(y))
    ch.SetClosed(True)
    return ch


def main():
    board = pcbnew.LoadBoard(BOARD_PATH)
    assert isinstance(board, pcbnew.BOARD)
    gnd = board.FindNet("GND")
    assert gnd, "GND net missing"

    # antenna keepout rect from U3's footprint rule-area, extended to the
    # NEAREST board edge (the module may be rotated to ANY edge: N/S long edge
    # OR W/E short edge for the rot90 west-end floorplan). Extend only toward
    # the edge the antenna overhangs; keep the other three sides at the module's
    # antenna span (extending the wrong way strands decoupling caps -- the
    # Layout-B power-routing bug).
    kx0, ky0, kx1, ky1 = 136.0, Y0 - 1, 164.0, 81.5   # fallback (north)
    for fp in board.GetFootprints():
        if fp.GetReference() == "U3":
            for z in fp.Zones():
                if z.GetIsRuleArea():
                    zb = z.GetBoundingBox()
                    kx0, kx1 = pcbnew.ToMM(zb.GetLeft()), pcbnew.ToMM(zb.GetRight())
                    ky0, ky1 = pcbnew.ToMM(zb.GetTop()), pcbnew.ToMM(zb.GetBottom())
                    dN, dS = ky0 - Y0, Y1 - ky1       # gap to each board edge
                    dW, dE = kx0 - X0, X1 - kx1
                    m = min(dN, dS, dW, dE)
                    if m == dN:                       # antenna on the N edge
                        ky0 = Y0 - 1
                    elif m == dS:                     # antenna on the S edge
                        ky1 = Y1 + 1
                    elif m == dW:                     # antenna on the W edge
                        kx0 = X0 - 1
                    else:                             # antenna on the E edge
                        kx1 = X1 + 1

    # drop pre-existing zones AND prior GND stitching vias (idempotent reruns —
    # GND is never routed, only poured + stitched, so every GND via is ours;
    # leaving them means each rerun double-stitches and the headless filler
    # eventually segfaults).
    gnd_code0 = gnd.GetNetCode()
    # snapshot BOTH lists before any Remove() — removing a zone corrupts the
    # SWIG iterator so a later board.GetTracks() returns an untyped object.
    old_zones = list(board.Zones())
    old_gnd_vias = [t for t in board.GetTracks()
                    if isinstance(t, pcbnew.PCB_VIA) and t.GetNetCode() == gnd_code0]
    for z in old_zones:
        board.Remove(z)
    for v in old_gnd_vias:
        board.Remove(v)

    # SOLID GND-pad connection (per-pad — the board is reflow-assembled, so
    # thermal relief only buys starved spokes on the C3 centre pad + USB-C
    # shield that read as unconnected). Pad-level FULL is filler-safe headless;
    # zone-level FULL crashes it.
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNetCode() == gnd_code0:
                pad.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)

    # --- antenna keepout rule areas (both layers) -----------------------
    ko = pcbnew.ZONE(board)
    ko.SetIsRuleArea(True)
    ko.SetDoNotAllowZoneFills(True)
    ko.SetDoNotAllowTracks(True)
    ko.SetDoNotAllowVias(True)
    ls = pcbnew.LSET()
    ls.AddLayer(pcbnew.F_Cu)
    ls.AddLayer(pcbnew.B_Cu)
    ko.SetLayerSet(ls)
    ko.AddPolygon(rect_chain(kx0, ky0, kx1, ky1))
    ko.SetZoneName("antenna_keepout")
    board.Add(ko)

    # --- GND pours on both layers ----------------------------------------
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        z = pcbnew.ZONE(board)
        z.SetLayer(layer)
        z.SetNetCode(gnd.GetNetCode())
        z.AddPolygon(rect_chain(X0 + 0.4, Y0 + 0.4, X1 - 0.4, Y1 - 0.4))
        z.SetLocalClearance(pcbnew.FromMM(0.3))
        z.SetMinThickness(pcbnew.FromMM(0.2))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        z.SetThermalReliefGap(pcbnew.FromMM(0.3))
        z.SetThermalReliefSpokeWidth(pcbnew.FromMM(0.5))
        # remove ALL unconnected fill islands (they otherwise read as
        # unconnected-zone DRC items). With FreeRouting routing the signals,
        # every GND pad is already tied by a routed trace, so the pour only
        # needs to be the plane — any island it can't stitch is redundant and
        # should go rather than be rescued by the tie pass.
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        z.SetAssignedPriority(0)
        z.SetZoneName(f"gnd_pour_{'F' if layer == pcbnew.F_Cu else 'B'}")
        board.Add(z)

    # --- stitching vias ---------------------------------------------------
    # occupancy check against pads/tracks/vias of non-GND nets
    pads_l = []   # (x, y, halfsize, netcode)
    segs_l = []   # (x0, y0, x1, y1, halfwidth, netcode)
    drills = []   # (x, y, drill_radius) for EVERY drilled hole (any net) —
                  # hole-to-hole spacing applies regardless of net, incl. GND
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            bb = pad.GetBoundingBox()
            pads_l.append((pcbnew.ToMM(bb.GetCenter().x), pcbnew.ToMM(bb.GetCenter().y),
                           max(pcbnew.ToMM(bb.GetWidth()), pcbnew.ToMM(bb.GetHeight())) / 2,
                           pad.GetNetCode()))
            if pad.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH):
                pp = pad.GetPosition()
                drills.append((pcbnew.ToMM(pp.x), pcbnew.ToMM(pp.y),
                               pcbnew.ToMM(pad.GetDrillSizeX()) / 2))
    for t in board.GetTracks():
        if isinstance(t, pcbnew.PCB_VIA):
            pads_l.append((pcbnew.ToMM(t.GetPosition().x), pcbnew.ToMM(t.GetPosition().y),
                           pcbnew.ToMM(t.GetWidth()) / 2, t.GetNetCode()))
        else:
            s, e = t.GetStart(), t.GetEnd()
            segs_l.append((pcbnew.ToMM(s.x), pcbnew.ToMM(s.y), pcbnew.ToMM(e.x), pcbnew.ToMM(e.y),
                           pcbnew.ToMM(t.GetWidth()) / 2, t.GetNetCode()))

    def seg_dist(px, py, x0, y0, x1, y1):
        dx, dy = x1 - x0, y1 - y0
        L2 = dx*dx + dy*dy
        t_ = 0 if L2 == 0 else max(0, min(1, ((px-x0)*dx + (py-y0)*dy) / L2))
        return math.hypot(x0 + t_*dx - px, y0 + t_*dy - py)

    gnd_code = gnd.GetNetCode()
    placed = 0
    y = Y0 + 3.0
    while y < Y1 - 2.0:
        x = X0 + 3.0
        while x < X1 - 2.0:
            ok = not (kx0 - 1 < x < kx1 + 1 and y < ky1 + 1)
            if ok:
                r = VIA_D / 2 + CLEAR
                for (ix, iy, ihs, inc) in pads_l:
                    if inc == gnd_code:
                        continue
                    if abs(ix - x) < ihs + r and abs(iy - y) < ihs + r:
                        ok = False
                        break
                if ok:
                    for (x0s, y0s, x1s, y1s, hw, inc) in segs_l:
                        if inc == gnd_code:
                            continue
                        if seg_dist(x, y, x0s, y0s, x1s, y1s) < hw + r:
                            ok = False
                            break
                if ok:
                    # hole-to-hole spacing vs EVERY drilled hole (incl. GND THT
                    # pads — net doesn't matter for drill spacing). board min
                    # 0.25mm; keep margin.
                    for (hx, hy, hr) in drills:
                        if math.hypot(hx - x, hy - y) < VIA_D / 2 + hr + 0.3:
                            ok = False
                            break
            if ok:
                v = pcbnew.PCB_VIA(board)
                v.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
                v.SetWidth(pcbnew.FromMM(VIA_D))
                v.SetDrill(pcbnew.FromMM(VIA_DRILL))
                v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
                v.SetNetCode(gnd_code)
                board.Add(v)
                placed += 1
            x += VIA_PITCH
        y += VIA_PITCH
    print(f"stitching vias placed: {placed}")

    # --- fill ------------------------------------------------------------
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())

    # --- tie orphan fill islands -----------------------------------------
    # A small GND fill that touches only a pad (not the main plane) reads as an
    # unconnected zone. Drop a GND via where the island overlaps the OTHER
    # layer's pour, stitching it into the plane, then re-fill. Iterate so a
    # chain (F-island -> B-island -> F-main) resolves over a few passes.
    ties = 0
    for _ in range(4):
        n = tie_islands(board, gnd_code)
        if not n:
            break
        ties += n
        filler.Fill(board.Zones())
    print(f"island ties: {ties}")

    pcbnew.SaveBoard(BOARD_PATH, board)
    print("zones filled, saved")
    return 0


def _poly_areas(ps):
    out = []
    for i in range(ps.OutlineCount()):
        ol = ps.Outline(i)
        a = 0
        n = ol.PointCount()
        for k in range(n):
            p1, p2 = ol.CPoint(k), ol.CPoint((k + 1) % n)
            a += p1.x * p2.y - p2.x * p1.y
        out.append(abs(a) / 2)
    return out


def tie_islands(board, gnd_code):
    zones = {z.GetLayer(): z for z in board.Zones()
             if z.GetNetCode() == gnd_code and not z.GetIsRuleArea()}
    if pcbnew.F_Cu not in zones or pcbnew.B_Cu not in zones:
        return 0
    polys = {L: zones[L].GetFilledPolysList(L) for L in (pcbnew.F_Cu, pcbnew.B_Cu)}
    areas = {L: _poly_areas(polys[L]) for L in polys}
    main = {L: (areas[L].index(max(areas[L])) if areas[L] else -1) for L in polys}

    # obstacles for a safety check: non-GND pads/tracks (clearance) + ALL vias
    # (hole-to-hole). A tie via must clear every one.
    fpads = []   # (x, y, halfsize) of non-GND pads
    fsegs = []   # (x0, y0, x1, y1, halfwidth) of non-GND track segments
    allvias = []  # (x, y) of every existing via
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNetCode() == gnd_code:
                continue
            bb = pad.GetBoundingBox()
            fpads.append((pcbnew.ToMM(bb.GetCenter().x), pcbnew.ToMM(bb.GetCenter().y),
                          max(pcbnew.ToMM(bb.GetWidth()), pcbnew.ToMM(bb.GetHeight())) / 2))
    for t in board.GetTracks():
        if isinstance(t, pcbnew.PCB_VIA):
            allvias.append((pcbnew.ToMM(t.GetPosition().x), pcbnew.ToMM(t.GetPosition().y)))
        elif t.GetNetCode() != gnd_code:
            s, e = t.GetStart(), t.GetEnd()
            fsegs.append((pcbnew.ToMM(s.x), pcbnew.ToMM(s.y),
                          pcbnew.ToMM(e.x), pcbnew.ToMM(e.y), pcbnew.ToMM(t.GetWidth()) / 2))

    def seg_d(px, py, x0, y0, x1, y1):
        dx, dy = x1 - x0, y1 - y0
        L2 = dx * dx + dy * dy
        u = 0 if L2 == 0 else max(0, min(1, ((px - x0) * dx + (py - y0) * dy) / L2))
        return math.hypot(x0 + u * dx - px, y0 + u * dy - py)

    def clear_of_foreign(xmm, ymm):
        # tie vias use a smaller body + DRC-min clearance so they fit the tight
        # congested spots (USB-C / C3 pins) where islands form
        r = TIE_VIA_D / 2 + 0.16
        if any(abs(fx - xmm) < fr + r and abs(fy - ymm) < fr + r for fx, fy, fr in fpads):
            return False
        if any(seg_d(xmm, ymm, *s[:4]) < s[4] + r for s in fsegs):
            return False
        if any(math.hypot(vx - xmm, vy - ymm) < (TIE_VIA_D + VIA_D) / 2 + 0.5
               for vx, vy in allvias):
            return False  # hole-to-hole
        return True

    gnd_via_pts = [t.GetPosition() for t in board.GetTracks()
                   if isinstance(t, pcbnew.PCB_VIA) and t.GetNetCode() == gnd_code]

    added = 0
    for L in (pcbnew.F_Cu, pcbnew.B_Cu):
        opp = pcbnew.B_Cu if L == pcbnew.F_Cu else pcbnew.F_Cu
        if main[opp] < 0:
            continue
        for i in range(polys[L].OutlineCount()):
            if i == main[L]:
                continue
            # already stitched into the plane? (a GND via inside it) -> skip
            if any(polys[L].Contains(p, i) for p in gnd_via_pts):
                continue
            ol = polys[L].Outline(i)
            n = ol.PointCount()
            xs = [ol.CPoint(k).x for k in range(n)]
            ys = [ol.CPoint(k).y for k in range(n)]
            # dense grid scan: first interior point that also sits over the
            # opposite main pour and clears foreign copper gets a tie via
            step = int(0.2 * 1e6)
            done = False
            yy = min(ys)
            while yy < max(ys) and not done:
                xx = min(xs)
                while xx < max(xs):
                    pt = pcbnew.VECTOR2I(int(xx), int(yy))
                    if (polys[L].Contains(pt, i)
                            and polys[opp].Contains(pt, main[opp])
                            and clear_of_foreign(pcbnew.ToMM(int(xx)), pcbnew.ToMM(int(yy)))):
                        v = pcbnew.PCB_VIA(board)
                        v.SetPosition(pt)
                        v.SetWidth(pcbnew.FromMM(TIE_VIA_D))
                        v.SetDrill(pcbnew.FromMM(TIE_DRILL))
                        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
                        v.SetNetCode(gnd_code)
                        board.Add(v)
                        added += 1
                        done = True
                        break
                    xx += step
                yy += step
    return added


if __name__ == "__main__":
    sys.exit(main())
