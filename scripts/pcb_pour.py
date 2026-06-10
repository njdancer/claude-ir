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
X0, Y0, X1, Y1 = 100.0, 60.0, 180.0, 115.0
ANTENNA_X = 104.6
ANTENNA_Y_MAX = 102.3   # WROOM courtyard wedge south extent
VIA_PITCH = 4.0         # stitching grid
VIA_D, VIA_DRILL = 0.6, 0.3
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

    # drop pre-existing zones (idempotent reruns)
    for z in list(board.Zones()):
        board.Remove(z)

    # --- antenna keepout rule areas (both layers) -----------------------
    ko = pcbnew.ZONE(board)
    ko.SetIsRuleArea(True)
    ko.SetDoNotAllowCopperPour(True)
    ko.SetDoNotAllowTracks(True)
    ko.SetDoNotAllowVias(True)
    ls = pcbnew.LSET()
    ls.AddLayer(pcbnew.F_Cu)
    ls.AddLayer(pcbnew.B_Cu)
    ko.SetLayerSet(ls)
    ko.AddPolygon(rect_chain(X0 - 1, Y0 - 1, ANTENNA_X, ANTENNA_Y_MAX))
    ko.SetZoneName("antenna_keepout")
    board.Add(ko)

    # --- GND pours on both layers ----------------------------------------
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        z = pcbnew.ZONE(board)
        z.SetLayer(layer)
        z.SetNetCode(gnd.GetNetCode())
        z.AddPolygon(rect_chain(X0 + 0.3, Y0 + 0.3, X1 - 0.3, Y1 - 0.3))
        z.SetLocalClearance(pcbnew.FromMM(0.3))
        z.SetMinThickness(pcbnew.FromMM(0.2))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        z.SetThermalReliefGap(pcbnew.FromMM(0.3))
        z.SetThermalReliefSpokeWidth(pcbnew.FromMM(0.5))
        z.SetAssignedPriority(0)
        z.SetZoneName(f"gnd_pour_{'F' if layer == pcbnew.F_Cu else 'B'}")
        board.Add(z)

    # --- stitching vias ---------------------------------------------------
    # occupancy check against pads/tracks/vias of non-GND nets
    pads_l = []   # (x, y, halfsize, netcode)
    segs_l = []   # (x0, y0, x1, y1, halfwidth, netcode)
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            bb = pad.GetBoundingBox()
            pads_l.append((pcbnew.ToMM(bb.GetCenter().x), pcbnew.ToMM(bb.GetCenter().y),
                           max(pcbnew.ToMM(bb.GetWidth()), pcbnew.ToMM(bb.GetHeight())) / 2,
                           pad.GetNetCode()))
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
            ok = not (x < ANTENNA_X + 1 and y < ANTENNA_Y_MAX + 1)
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
    pcbnew.SaveBoard(BOARD_PATH, board)
    print("zones filled, saved")
    return 0


if __name__ == "__main__":
    sys.exit(main())
