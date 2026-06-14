#!/usr/bin/env python3
"""Relocate C3-support parts adjacent to their pins (v2 placement fix).

The v1.4->v2 swap left the C3's pullups/caps at the old WROOM locations,
45mm from the new C3 pins, so the autorouter can't reach pins 6/7/8 or the
USB-C CC pad. This greedily re-seats each listed part at the nearest
collision-free slot to its anchor pin, highest-priority parts first so the
pin-pullups win the prime escape lane and decoupling fills what's left.

Collision = courtyard-bbox overlap (+MARGIN) with any fixed/already-placed
part, off-board, or inside the WROOM antenna keepout. Run:

  /tmp/kv10/bin/python scripts/pcb_place_v2.py
"""
import math
import pcbnew

PCB = "hardware/esp32-ir-remote.kicad_pcb"
MARGIN = 0.2          # extra courtyard gap, mm
X0, Y0, X1, Y1 = 100.3, 60.3, 179.7, 114.7   # placeable board interior
KEEPOUT = (95.0, 60.0, 104.6, 102.3)         # antenna: no part center/box here

# (ref, anchor_x, anchor_y, [allowed rotations]) — order = priority
# anchors are the C3 pin (or J2 pad) the part must sit beside.
PLACE = [
    ("R7",  116.5, 86.75, [90, 0]),   # IO8 pullup  -> pin7
    ("R6",  118.0, 86.75, [90, 0]),   # BOOT pullup -> pin8
    ("R28", 115.0, 86.75, [90, 0]),   # SDA pullup  -> pin6
    ("R5",  109.0, 86.75, [90, 0]),   # EN pullup   -> pin2
    ("C6",  109.0, 86.75, [90, 0]),   # EN cap      -> pin2
    ("R29", 119.5, 69.25, [90, 0]),   # SCL pullup  -> pin10 (north)
    ("R8",  110.5, 69.25, [90, 0]),   # IO2 pullup  -> pin16 (north)
    ("R1",  133.3, 113.9, [0, 90]),   # CC1 res     -> J2.A5
    # decoupling — lower priority, fill remaining south channel
    ("C5",  107.5, 86.75, [90, 0]),   # 3V3 decoup near pin1
    ("C7",  112.0, 86.75, [90, 0]),
    ("C10", 113.5, 86.75, [90, 0]),
]
MOVING = {p[0] for p in PLACE}


def bbox_at(w, h, cx, cy):
    return (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)


def overlaps(a, b):
    return not (a[2] <= b[0] or a[0] >= b[2] or a[3] <= b[1] or a[1] >= b[3])


def main():
    b = pcbnew.LoadBoard(PCB)
    fps = {f.GetReference(): f for f in b.GetFootprints()}

    def court_wh(f):
        sh = f.GetCourtyard(pcbnew.F_CrtYd)
        bb = sh.BBox()
        if bb.GetWidth() == 0:
            bb = f.GetBoundingBox()
        return pcbnew.ToMM(bb.GetWidth()), pcbnew.ToMM(bb.GetHeight())

    # fixed obstacles = every part not being moved (inflated)
    fixed = []
    for ref, f in fps.items():
        if ref in MOVING:
            continue
        sh = f.GetCourtyard(pcbnew.F_CrtYd)
        bb = sh.BBox()
        if bb.GetWidth() == 0:
            bb = f.GetBoundingBox()
        fixed.append((pcbnew.ToMM(bb.GetLeft()) - MARGIN,
                      pcbnew.ToMM(bb.GetTop()) - MARGIN,
                      pcbnew.ToMM(bb.GetRight()) + MARGIN,
                      pcbnew.ToMM(bb.GetBottom()) + MARGIN))

    placed = list(fixed)
    results = []
    for ref, ax, ay, rots in PLACE:
        f = fps[ref]
        w0, h0 = court_wh(f)
        best = None
        # spiral search: increasing radius, fine grid
        for R in [x * 0.25 for x in range(0, 80)]:
            cand = []
            steps = max(8, int(2 * math.pi * R / 0.25)) if R > 0 else 1
            for s in range(steps):
                th = 2 * math.pi * s / steps
                cx = round(ax + R * math.cos(th), 2)
                cy = round(ay + R * math.sin(th), 2)
                for rot in rots:
                    w, h = (w0, h0) if rot % 180 == (round(f.GetOrientation().AsDegrees()) % 180) else (h0, w0)
                    # account that court_wh already reflects current rot; if we
                    # change parity, swap w/h
                    cur = round(f.GetOrientation().AsDegrees()) % 180
                    w, h = (w0, h0) if (rot % 180) == cur else (h0, w0)
                    bb = bbox_at(w + 2 * MARGIN, h + 2 * MARGIN, cx, cy)
                    if bb[0] < X0 or bb[1] < Y0 or bb[2] > X1 or bb[3] > Y1:
                        continue
                    ko = (KEEPOUT[0], KEEPOUT[1], KEEPOUT[2], KEEPOUT[3])
                    if overlaps(bb, ko):
                        continue
                    if any(overlaps(bb, p) for p in placed):
                        continue
                    d = math.hypot(cx - ax, cy - ay)
                    cand.append((d, cx, cy, rot, w, h))
            if cand:
                cand.sort()
                best = cand[0]
                break
        if best is None:
            results.append((ref, None))
            print(f"  {ref}: NO FREE SLOT near ({ax},{ay})")
            continue
        d, cx, cy, rot, w, h = best
        f.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(cx), pcbnew.FromMM(cy)))
        f.SetOrientationDegrees(rot)
        placed.append((cx - w / 2 - MARGIN, cy - h / 2 - MARGIN,
                       cx + w / 2 + MARGIN, cy + h / 2 + MARGIN))
        results.append((ref, (cx, cy, rot)))
        print(f"  {ref}: -> ({cx},{cy}) rot{rot}  d={round(d,2)}mm")

    pcbnew.SaveBoard(PCB, b)
    ok = sum(1 for _, r in results if r)
    print(f"placed {ok}/{len(PLACE)}")


if __name__ == "__main__":
    main()
