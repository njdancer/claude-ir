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

# Explicit decoupling / bypass / RC assignment — board knowledge the shared
# power+GND nets cannot encode. A +3.3V bypass cap pad sees the whole rail, so
# the net heuristic below can only seat it at the *nearest* rail pin; that piles
# every MCU/sensor bypass onto the LDO and starves the far ICs (U5/AHT20 ended
# up with NO local cap, both 10 uF stacked on U3). Pin each part to the specific
# (anchor, pad) it actually bypasses so every IC gets its own HF + bulk bank:
#   U3 (C3)   <- C7 100nF + C8 10uF  on 3V3 (pin 1); C6 1uF EN-POR RC on EN (2)
#   U5 (AHT20)<- C5 100nF + C10 10uF on VDD (pin 2); R28/R29 I2C pull-ups (4/3)
#   U1 (LDO)  <- C1 in-cap on VIN (3); C2/C3 out-caps on VOUT (2)
# Refs not listed fall back to the net heuristic (e.g. R27/C9 uniquely reach U4).
ASSIGN = {
    "C1":  ("U1", "3"),   # LDO input cap   -> VIN (+5V)
    "C2":  ("U1", "2"),   # LDO output cap  -> VOUT
    "C3":  ("U1", "2"),   # LDO output cap  -> VOUT
    "C6":  ("U3", "2"),   # EN power-on-reset RC -> C3 EN
    "C7":  ("U3", "1"),   # U3 bank: 100nF  -> C3 3V3
    "C8":  ("U3", "1"),   # U3 bank: 10uF   -> C3 3V3
    "C5":  ("U5", "2"),   # U5 bank: 100nF  -> AHT20 VDD
    "C10": ("U5", "2"),   # U5 bank: 10uF   -> AHT20 VDD
    "R28": ("U5", "4"),   # I2C SDA pull-up -> near sensor
    "R29": ("U5", "3"),   # I2C SCL pull-up -> near sensor
}


def overlaps(a, b):
    return not (a[2] <= b[0] or a[0] >= b[2] or a[3] <= b[1] or a[1] >= b[3])


def court_wh(f):
    sh = f.GetCourtyard(pcbnew.F_CrtYd)
    bb = sh.BBox()
    if bb.GetWidth() == 0:
        # text-free bbox: the default GetBoundingBox() includes the ref text,
        # so a courtyard-less part (mounting holes) grows by wherever the last
        # silk pass parked its ref — the legalizer then spiralled every hole
        # off-target nondeterministically (r2 loop find, 2026-07-02)
        bb = f.GetBoundingBox(False)
    return pcbnew.ToMM(bb.GetWidth()), pcbnew.ToMM(bb.GetHeight())


def court_bbox(f):
    sh = f.GetCourtyard(pcbnew.F_CrtYd)
    bb = sh.BBox()
    if bb.GetWidth() == 0:
        bb = f.GetBoundingBox(False)   # text-free: see court_wh
    return (pcbnew.ToMM(bb.GetLeft()) - MARGIN, pcbnew.ToMM(bb.GetTop()) - MARGIN,
            pcbnew.ToMM(bb.GetRight()) + MARGIN, pcbnew.ToMM(bb.GetBottom()) + MARGIN)


def keepout_box(b):
    """Union bbox of ALL antenna rule areas. There are TWO: U3's footprint
    keepout (rotates with the module, y stops at the module edge) AND a
    board-level rule area that extends past the module to the S board edge.
    Reading only the footprint one stranded decoupling caps just below it
    (passed the placer, failed DRC items_not_allowed). Union both."""
    boxes = []
    for f in b.GetFootprints():
        for z in f.Zones():
            if z.GetIsRuleArea():
                boxes.append(z.GetBoundingBox())
    for z in b.Zones():
        if z.GetIsRuleArea():
            boxes.append(z.GetBoundingBox())
    if not boxes:
        return None
    return (min(pcbnew.ToMM(z.GetLeft()) for z in boxes),
            min(pcbnew.ToMM(z.GetTop()) for z in boxes),
            max(pcbnew.ToMM(z.GetRight()) for z in boxes),
            max(pcbnew.ToMM(z.GetBottom()) for z in boxes))


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

    # the back-silk logo (added by pcb_silk) is a fixed graphic, never re-seated
    movable = [f for r, f in fps.items()
               if r not in FIXED_REFS and "Claude_Spark" not in f.GetValue()]

    # anchor degree = how many distinct nets each anchor touches (hub vs leaf).
    # A series element bridging two single-anchor nets (e.g. an LED's current-
    # limit R, which sees the MCU pin on one net and the LED on the other)
    # should seat at the LEAF (the LED, low degree), not the hub (U3, high
    # degree). Only used to break ties among specificity-1 candidates.
    anchor_deg = {}
    for nc, lst in net_anchor.items():
        for ref, _, _ in lst:
            anchor_deg.setdefault(ref, set()).add(nc)
    anchor_deg = {r: len(s) for r, s in anchor_deg.items()}

    def pad_pos(anchor_ref, pad_num):
        f = fps.get(anchor_ref)
        if not f:
            return None
        for pad in f.Pads():
            if pad.GetNumber() == pad_num:
                p = pad.GetPosition()
                return (pcbnew.ToMM(p.x), pcbnew.ToMM(p.y))
        return None

    # choose a target pin for each movable part: explicit ASSIGN first (spec=-1
    # so these claim their pin slot before any net-heuristic part), else the
    # most-specific reachable net, ties broken toward the leaf anchor, then
    # nearest.
    def target_of(f):
        ref = f.GetReference()
        if ref in ASSIGN:
            pp = pad_pos(*ASSIGN[ref])
            if pp:
                fp = f.GetPosition()
                d = math.hypot(pp[0] - pcbnew.ToMM(fp.x), pp[1] - pcbnew.ToMM(fp.y))
                return (-1, 0, d, pp[0], pp[1])
        best = None  # (spec, leaf_pref, dist, x, y)
        fp = f.GetPosition()
        fx, fy = pcbnew.ToMM(fp.x), pcbnew.ToMM(fp.y)
        for pad in f.Pads():
            nc = pad.GetNetCode()
            if nc not in net_anchor:
                continue
            anchors = net_anchor[nc]
            spec = len(anchors)
            for ref, ax, ay in anchors:
                d = math.hypot(ax - fx, ay - fy)
                leaf = anchor_deg.get(ref, 99) if spec == 1 else 0
                cand = (spec, leaf, d, ax, ay)
                if best is None or cand < best:
                    best = cand
        return best

    targeted = []
    deferred = []
    for f in movable:
        t = target_of(f)
        (targeted if t else deferred).append((f, t))
    # most-specific + nearest first so signal parts claim the prime pin slots
    targeted.sort(key=lambda ft: (ft[1][0], ft[1][2]))

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
                    # tidiness bias (Nick 2026-07-02: board "looks thrown
                    # together"): prefer spots straight N/S/E/W of the target
                    # pad — clusters then read as rows/columns, not scatter.
                    # 0.35mm equivalent-distance bonus keeps it gentle.
                    aligned = abs(cx - tx) < 0.03 or abs(cy - ty) < 0.03
                    cands.append((math.hypot(cx - tx, cy - ty)
                                  + (0.0 if aligned else 0.35),
                                  cx, cy, rot, bb))
            if cands:
                cands.sort()
                _, cx, cy, rot, bb = cands[0]
                f.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(cx), pcbnew.FromMM(cy)))
                f.SetOrientationDegrees(rot)
                placed.append(bb)
                return (cx, cy)
        return None

    for f, t in targeted:
        _, _, _, tx, ty = t   # (spec, leaf, dist, x, y)
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
