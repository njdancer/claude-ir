#!/usr/bin/env python3
"""Phase B: net-driven re-seat of support parts against the zone anchors.

scripts/pcb_floorplan.py (Phase A) places the zone ANCHORS (the big parts
that define the functional zones) + the new outline + mounting holes. This
pass seats every *other* footprint (decoupling, pullups, RC filters, CC
resistors, ...) next to the anchor pin it actually connects to:

  - For each movable part, look at the nets on its pads. Pick the MOST
    SPECIFIC net (fewest anchor pins on it) that still reaches an anchor — a
    signal net touching exactly one anchor pin (e.g. a pullup on IO8 -> the
    C3's pin) targets that pin uniquely; power nets (many anchor pins) are
    used only as a fallback so decoupling clusters at the nearest IC rail.
  - Spiral-search the nearest collision-free slot to that target pin.
  - GND is excluded as a target (it touches everything and is poured, not
    routed). Parts with no non-GND anchor net are deferred to a second pass
    that seats them at the centroid of their now-placed net-mates.

Anchors + mounting holes are fixed obstacles. Antenna keepout is read live
from U3's rule-area so it tracks the floorplan. Run:

  /tmp/kv10/bin/python scripts/pcb_place_v2.py
"""
import math
import pcbnew
from pcb_floorplan import ANCHORS, HOLES, BX0, BY0, BX1, BY1

PCB = "hardware/esp32-ir-remote.kicad_pcb"
MARGIN = 0.2
EDGE = 0.4                       # keep courtyards off the board edge
X0, Y0, X1, Y1 = BX0 + EDGE, BY0 + EDGE, BX1 - EDGE, BY1 - EDGE
FIXED_REFS = set(ANCHORS) | set(HOLES)
GND_NAMES = {"GND", "GNDA", "GNDPWR"}


def overlaps(a, b):
    return not (a[2] <= b[0] or a[0] >= b[2] or a[3] <= b[1] or a[1] >= b[3])


def court_wh(f):
    sh = f.GetCourtyard(pcbnew.F_CrtYd)
    bb = sh.BBox()
    if bb.GetWidth() == 0:
        bb = f.GetBoundingBox()
    return pcbnew.ToMM(bb.GetWidth()), pcbnew.ToMM(bb.GetHeight())


def court_bbox(f):
    sh = f.GetCourtyard(pcbnew.F_CrtYd)
    bb = sh.BBox()
    if bb.GetWidth() == 0:
        bb = f.GetBoundingBox()
    return (pcbnew.ToMM(bb.GetLeft()) - MARGIN, pcbnew.ToMM(bb.GetTop()) - MARGIN,
            pcbnew.ToMM(bb.GetRight()) + MARGIN, pcbnew.ToMM(bb.GetBottom()) + MARGIN)


def keepout_box(b):
    for f in b.GetFootprints():
        if f.GetReference() != "U3":
            continue
        for z in f.Zones():
            if z.GetIsRuleArea():
                zb = z.GetBoundingBox()
                return (pcbnew.ToMM(zb.GetLeft()), pcbnew.ToMM(zb.GetTop()),
                        pcbnew.ToMM(zb.GetRight()), pcbnew.ToMM(zb.GetBottom()))
    return None


def main():
    b = pcbnew.LoadBoard(PCB)
    fps = {f.GetReference(): f for f in b.GetFootprints()}

    # net -> list of (anchor_ref, x, y) for every pad of every anchor part
    net_anchor = {}
    for ref in FIXED_REFS:
        f = fps.get(ref)
        if not f:
            continue
        for pad in f.Pads():
            nn = pad.GetNetname().split("/")[-1].upper()
            if nn in GND_NAMES or not pad.GetNetname():
                continue
            p = pad.GetPosition()
            net_anchor.setdefault(pad.GetNetCode(), []).append(
                (ref, pcbnew.ToMM(p.x), pcbnew.ToMM(p.y)))

    movable = [f for r, f in fps.items() if r not in FIXED_REFS]

    # choose a target pin for each movable part: most-specific reachable net
    def target_of(f):
        best = None  # (specificity, dist, x, y)
        fp = f.GetPosition()
        fx, fy = pcbnew.ToMM(fp.x), pcbnew.ToMM(fp.y)
        for pad in f.Pads():
            nc = pad.GetNetCode()
            if nc not in net_anchor:
                continue
            anchors = net_anchor[nc]
            spec = len(anchors)
            for _, ax, ay in anchors:
                d = math.hypot(ax - fx, ay - fy)
                cand = (spec, d, ax, ay)
                if best is None or cand < best:
                    best = cand
        return best

    targeted = []
    deferred = []
    for f in movable:
        t = target_of(f)
        (targeted if t else deferred).append((f, t))
    # most-specific first so signal parts claim the prime pin-side slots
    targeted.sort(key=lambda ft: (ft[1][0], ft[1][1]))

    placed = [court_bbox(fps[r]) for r in FIXED_REFS if r in fps]
    ko = keepout_box(b)
    results = {}

    def seat(f, tx, ty):
        w0, h0 = court_wh(f)
        cur = round(f.GetOrientation().AsDegrees()) % 180
        for R in [x * 0.25 for x in range(0, 120)]:
            steps = max(8, int(2 * math.pi * R / 0.25)) if R > 0 else 1
            cands = []
            for s in range(steps):
                th = 2 * math.pi * s / steps
                cx = round(tx + R * math.cos(th), 2)
                cy = round(ty + R * math.sin(th), 2)
                for rot in (cur, (cur + 90) % 180):
                    w, h = (w0, h0) if rot == cur else (h0, w0)
                    bb = (cx - w / 2 - MARGIN, cy - h / 2 - MARGIN,
                          cx + w / 2 + MARGIN, cy + h / 2 + MARGIN)
                    if bb[0] < X0 or bb[1] < Y0 or bb[2] > X1 or bb[3] > Y1:
                        continue
                    if ko and overlaps(bb, ko):
                        continue
                    if any(overlaps(bb, p) for p in placed):
                        continue
                    cands.append((math.hypot(cx - tx, cy - ty), cx, cy, rot, bb))
            if cands:
                cands.sort()
                _, cx, cy, rot, bb = cands[0]
                f.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(cx), pcbnew.FromMM(cy)))
                f.SetOrientationDegrees(rot)
                placed.append(bb)
                return (cx, cy)
        return None

    for f, t in targeted:
        _, _, tx, ty = t
        r = seat(f, tx, ty)
        results[f.GetReference()] = r

    # deferred: seat at centroid of placed net-mates (now that targets are down)
    for f, _ in deferred:
        pts = []
        for pad in f.Pads():
            nn = pad.GetNetname().split("/")[-1].upper()
            if nn in GND_NAMES:
                continue
            for f2 in movable:
                if f2 is f or results.get(f2.GetReference()) is None:
                    continue
                if any(p2.GetNetCode() == pad.GetNetCode() for p2 in f2.Pads()):
                    pts.append(results[f2.GetReference()])
        if pts:
            tx = sum(p[0] for p in pts) / len(pts)
            ty = sum(p[1] for p in pts) / len(pts)
        else:
            tx, ty = (X0 + X1) / 2, (Y0 + Y1) / 2
        results[f.GetReference()] = seat(f, tx, ty)

    pcbnew.SaveBoard(PCB, b)
    ok = sum(1 for v in results.values() if v)
    miss = [r for r, v in results.items() if v is None]
    print(f"seated {ok}/{len(results)} support parts" + (f"; NO SLOT: {miss}" if miss else ""))


if __name__ == "__main__":
    main()
