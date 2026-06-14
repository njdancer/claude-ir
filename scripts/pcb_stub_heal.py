#!/usr/bin/env python3
"""Close the autorouter's THT-pad shortfalls — targeted, vertex-anchored, safe.

The grid router targets each pad's bounding BOX. For round/oval THT pads the
bbox corners sit outside the actual copper, so a leg can stop ~1mm shy at a
corner cell, leaving the pad unconnected. This reads a DRC report, and for
each short track<->pad (or track<->track) gap it adds ONE short bridge from
the pad anchor (or other vertex) to the nearest existing same-net track
*vertex* — never to a mid-segment point (which would dangle) and never across
foreign copper (a clearance guard rejects anything that would short).

Skips pad<->pad and zone gaps (structural — handled by placement/pour).

  /tmp/kv10/bin/python scripts/pcb_stub_heal.py [drc.json]
"""
import json
import sys

import pcbnew

PCB = "hardware/esp32-ir-remote.kicad_pcb"
MAXLEN = 2.4      # mm — longest shortfall we'll bridge
CLR = 0.18        # mm — reject a bridge that comes within this of foreign copper


def mm(v):
    return v / 1e6


def seg_pt_dist(ax, ay, bx, by, px, py):
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    if L2 == 0:
        return ((px - ax) ** 2 + (py - ay) ** 2) ** 0.5
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
    cx, cy = ax + t * dx, ay + t * dy
    return ((px - cx) ** 2 + (py - cy) ** 2) ** 0.5


def main():
    rep = sys.argv[1] if len(sys.argv) > 1 else "/tmp/drc.json"
    d = json.load(open(rep))
    b = pcbnew.LoadBoard(PCB)

    tracks = [t for t in b.GetTracks() if not isinstance(t, pcbnew.PCB_VIA)]
    # same-net vertices: net -> [(x,y)]
    verts = {}
    for t in tracks:
        nc = t.GetNetCode()
        for e in (t.GetStart(), t.GetEnd()):
            verts.setdefault(nc, []).append((mm(e.x), mm(e.y)))
    # foreign copper for the clearance guard: list of (net, x0,y0,x1,y1) track
    # segs + (net, x,y,r) pads
    fseg = [(t.GetNetCode(), mm(t.GetStart().x), mm(t.GetStart().y),
             mm(t.GetEnd().x), mm(t.GetEnd().y), mm(t.GetWidth()) / 2)
            for t in b.GetTracks() if not isinstance(t, pcbnew.PCB_VIA)]
    fpad = []
    netname = {}
    for f in b.GetFootprints():
        for p in f.Pads():
            pos = p.GetPosition()
            r = mm(p.GetBoundingBox().GetWidth()) / 2
            fpad.append((p.GetNetCode(), mm(pos.x), mm(pos.y), r))
    for i in range(1, b.GetNetInfo().GetNetCount()):
        ni = b.GetNetInfo().GetNetItem(i)
        if ni:
            netname[ni.GetNetname()] = i

    def crosses_foreign(nc, x0, y0, x1, y1):
        for fn, fx0, fy0, fx1, fy1, fr in fseg:
            if fn == nc:
                continue
            # distance between the two segments (sample endpoints of bridge)
            for px, py in ((x0, y0), (x1, y1), ((x0 + x1) / 2, (y0 + y1) / 2)):
                if seg_pt_dist(fx0, fy0, fx1, fy1, px, py) < CLR + fr:
                    return True
        for fn, fx, fy, fr in fpad:
            if fn == nc:
                continue
            if seg_pt_dist(x0, y0, x1, y1, fx, fy) < CLR + fr:
                return True
        return False

    added = skipped = 0
    for u in d.get("unconnected_items", []):
        its = u.get("items", [])
        if len(its) != 2:
            continue
        kinds = [it["description"].split(" ")[0] for it in its]
        if "Zone" in kinds:
            skipped += 1; continue
        if kinds.count("Pad") + kinds.count("PTH") + kinds.count("SMD") == 2:
            skipped += 1; continue            # pad<->pad: structural
        # net code
        import re
        m = re.search(r"\[([^\]]+)\]", its[0]["description"])
        nc = netname.get(m.group(1)) if m else None
        if nc is None:
            skipped += 1; continue
        ax, ay = its[0]["pos"]["x"], its[0]["pos"]["y"]
        bx, by = its[1]["pos"]["x"], its[1]["pos"]["y"]
        # anchor each end to the nearest same-net track vertex (so we bridge
        # vertex->vertex, never to a mid-segment point)
        vs = verts.get(nc, [])

        def nearest_vertex(x, y):
            best = None
            for vx, vy in vs:
                dd = (vx - x) ** 2 + (vy - y) ** 2
                if best is None or dd < best[0]:
                    best = (dd, vx, vy)
            return (best[1], best[2]) if best else (x, y)

        # if an end is a pad, keep the pad anchor; if it's a track, snap to its
        # nearest vertex
        p0 = (ax, ay) if its[0]["description"].startswith(("Pad", "PTH", "SMD")) \
            else nearest_vertex(ax, ay)
        p1 = (bx, by) if its[1]["description"].startswith(("Pad", "PTH", "SMD")) \
            else nearest_vertex(bx, by)
        L = ((p0[0] - p1[0]) ** 2 + (p0[1] - p1[1]) ** 2) ** 0.5
        if L > MAXLEN or L < 1e-3:
            skipped += 1; continue
        if crosses_foreign(nc, p0[0], p0[1], p1[0], p1[1]):
            print(f"  SKIP {m.group(1):14} {round(L,2)}mm — would short")
            skipped += 1; continue
        lyr = (pcbnew.B_Cu if "B.Cu" in its[0]["description"] + its[1]["description"]
               else pcbnew.F_Cu)
        t = pcbnew.PCB_TRACK(b)
        t.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(p0[0]), pcbnew.FromMM(p0[1])))
        t.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(p1[0]), pcbnew.FromMM(p1[1])))
        t.SetLayer(lyr)
        t.SetWidth(pcbnew.FromMM(0.25))
        t.SetNetCode(nc)
        b.Add(t)
        added += 1
        print(f"  bridged {m.group(1):14} {round(L,2)}mm on "
              f"{'B' if lyr==pcbnew.B_Cu else 'F'}.Cu")

    pcbnew.SaveBoard(PCB, b)
    print(f"added {added} bridges, skipped {skipped}")


if __name__ == "__main__":
    main()
