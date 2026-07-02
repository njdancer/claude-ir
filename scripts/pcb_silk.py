#!/usr/bin/env python3
"""Silkscreen pass: strip passive outlines + auto-place reference designators.

The board is dense. Most silk_overlap/silk_over_copper come from (a) the little
R/C passive silk outlines colliding when parts sit close, and (b) reference
text piled above courtyards. This:
  phase 1 - drops board-level silk texts (stale v1 labels) and the F.SilkS
            graphics of R* / C* passives (non-polarised, CPL-placed, the
            outline buys nothing), then saves;
  phase 2 - (fresh load, dodging the SWIG remove-then-iterate curse) sizes
            every reference small and drops it at the nearest spot clear of
            pads / courtyards / other refs, hiding it if nothing fits.
Diode/LED/IC/connector/switch outlines are kept (orientation matters).

Run: /tmp/kv10/bin/python scripts/pcb_silk.py
"""
import pcbnew

import subprocess

BOARD_PATH = "hardware/esp32-ir-remote.kicad_pcb"
REF_SIZE = 0.8          # silk text min (smaller trips the text_height rule)
EDGE = (106.3, 70.3, 197.7, 113.7)   # new long-thin board interior
STRIP_PREFIXES = ("R", "C")     # passives whose silk outline we remove
# Front labels: the board title is AUTO-PLACED (three hardcoded homes in a
# row went stale as the layout evolved — F1/D1's pads, then H2's new spot,
# then R5/R6's band). place_title() scans the pad/courtyard obstacle field
# for the widest clear band, preferring high on the board. Captions over the
# status-LED row are anchored to the LEDs as before.
TITLE = ("ESP32-C3 IR REMOTE", 1.0)
LABELS = []
# Per-LED function captions, abbreviated, placed just below each status LED so
# the cluster is self-documenting (a single "STATUS" word told you nothing).
# Anchored to the footprint position, not hardcoded x, so they track re-layout.
#   D6  +5V rail / USB power present      D11 user LED 1 (GPIO3)
#   D7  +3.3V rail present                D12 user LED 2 (GPIO4)
#   D10 IR-TX activity (GPIO5)  -> "TX": U4 (the IR *receiver*) now sits right
#       below this row, so "IR" would read as if it labelled the receiver.
STATUS_FN = {"D6": "5V", "D7": "3V3", "D10": "TX", "D11": "USR1", "D12": "USR2"}
# The captioned status LEDs get NO ref designator on silk: the cluster is too
# dense for 5 more texts, so the placer scatters them into wrong-reading spots
# (D10's ref lands nearer D11...). The function caption is the curated label;
# refs live in the iBOM/fab docs. SMD machine-placed, not hand-solder parts.
SUPPRESS_REF = set(STATUS_FN)
# Caption row offset candidates (mm below the LED centre; negative = above).
# The row is layout-dependent (Layout B seated R16 in the old fixed 4.0 row),
# so pick the first offset where EVERY caption clears pads/courtyards — one
# uniform row; falls back to per-LED offsets only if no uniform row exists.
STATUS_FN_DYS = [4.0, 3.2, 4.6, 5.2, 5.8, 6.4, 7.0, -2.8, -3.4, -4.0]
# Fallback per-LED sideways nudges (mm) when no uniform row clears: the
# caption tucks beside whatever part the placer stacked under that LED.
# Keep |dx| < half the LED pitch (2.5mm for the D6/D7 pair) wherever
# possible so a caption stays nearest ITS OWN LED — a caption that drifts
# under the neighbour actively mislabels it.
STATUS_FN_DXS = [0.0, -1.4, 1.4, -1.8, 1.8, -2.4, 2.4]
STATUS_FN_SIZE = 0.8     # min legible silk; <0.8 trips the text_height DRC rule
# Claude spark logo footprint (extracted to a B.SilkS logo, mirror-correct).
LOGO_LIB = "hardware/libraries/Branding.pretty"
LOGO_FP = "Claude_Spark_Logo"
LOGO_AT = (152.0, 84.3)   # header centred above the back-silk text block
# Old front-silk spark = a single top-level gr_poly on F.SilkS near here.
OLD_SPARK_BBOX = (126.0, 98.0, 132.0, 104.0)


def git_stamp():
    try:
        h = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"],
                                    text=True).strip()
        dirty = subprocess.call(["git", "diff", "--quiet"]) != 0
        return h + ("-dirty" if dirty else "")
    except Exception:
        return "unknown"


def mm(v):
    return v / 1e6


def is_passive(ref):
    return (ref[:1] in STRIP_PREFIXES and ref[1:2].isdigit())


def overlaps(a, b):
    return not (a[2] <= b[0] or a[0] >= b[2] or a[3] <= b[1] or a[1] >= b[3])


def text_wh(text, size):
    """Real KiCad stroke-font extents (measured @0.8mm: 'R16' 2.46x1.29,
    'C1' 1.70x1.29, 'SW1' 2.58x1.29 -> ~1.07*len*size wide, 1.61*size tall).
    The old len*size*0.75 estimate under-read the true bbox by ~35% and let
    refs land on silk lines that DRC then flagged."""
    return len(text) * size * 1.1, size * 1.62


def phase1():
    b = pcbnew.LoadBoard(BOARD_PATH)
    texts = [d for d in b.GetDrawings()
             if isinstance(d, pcbnew.PCB_TEXT)
             and d.GetLayer() in (pcbnew.F_SilkS, pcbnew.B_SilkS)]
    # old front-silk Claude spark (a top-level gr_poly) -> relocated to B.SilkS
    # as a logo footprint in phase2; remove the stray front poly here.
    spark = [d for d in b.GetDrawings()
             if isinstance(d, pcbnew.PCB_SHAPE) and d.GetLayer() == pcbnew.F_SilkS
             and OLD_SPARK_BBOX[0] - 2 < pcbnew.ToMM(d.GetBoundingBox().GetCenter().x) < OLD_SPARK_BBOX[2] + 2
             and OLD_SPARK_BBOX[1] - 2 < pcbnew.ToMM(d.GetBoundingBox().GetCenter().y) < OLD_SPARK_BBOX[3] + 2]
    # collect passive silk graphics to remove (collect THEN remove)
    rm = []
    for fp in b.GetFootprints():
        if not is_passive(fp.GetReference()):
            continue
        for g in fp.GraphicalItems():
            if isinstance(g, pcbnew.PCB_SHAPE) and g.GetLayer() == pcbnew.F_SilkS:
                rm.append((fp, g))
    # existing logo footprint(s) — remove so phase2 re-adds exactly one
    # (idempotent; otherwise re-runs duplicate it and the placer drifts a copy)
    old_logos = [fp for fp in b.GetFootprints()
                 if "Claude_Spark" in fp.GetValue()]
    for t in texts:
        b.Remove(t)
    for d in spark:
        b.Remove(d)
    for fp in old_logos:
        b.Remove(fp)
    for fp, g in rm:
        fp.Remove(g)
    pcbnew.SaveBoard(BOARD_PATH, b)
    print(f"phase1: removed {len(texts)} texts, {len(spark)} spark polys, "
          f"{len(old_logos)} old logos, {len(rm)} passive outlines")


def phase2():
    board = pcbnew.LoadBoard(BOARD_PATH)
    M = 0.12
    obst = []
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            bb = pad.GetBoundingBox()
            obst.append((mm(bb.GetLeft()) - M, mm(bb.GetTop()) - M,
                         mm(bb.GetRight()) + M, mm(bb.GetBottom()) + M))
        fp.BuildCourtyardCaches()
        c = fp.GetCourtyard(pcbnew.F_CrtYd)
        if c.OutlineCount():
            bb = c.BBox()
            obst.append((mm(bb.GetLeft()), mm(bb.GetTop()),
                         mm(bb.GetRight()), mm(bb.GetBottom())))
        # kept footprint silk outlines (diodes/ICs/connectors) can poke past
        # the courtyard (e.g. LED_0805 bar) — refs/captions must dodge them too
        for g in fp.GraphicalItems():
            if isinstance(g, pcbnew.PCB_SHAPE) and g.GetLayer() == pcbnew.F_SilkS:
                gb = g.GetBoundingBox()
                obst.append((mm(gb.GetLeft()), mm(gb.GetTop()),
                             mm(gb.GetRight()), mm(gb.GetBottom())))

    # Reserve the per-LED caption boxes as obstacles so the designator placer
    # dodges them, then emit the captions after placement.
    def caption_box(fp, t, dy, dx=0.0, ang=0, margin=0.12):
        p = fp.GetPosition()
        lx, ly = mm(p.x) + dx, mm(p.y) + dy
        lw, lh = text_wh(t, STATUS_FN_SIZE)
        if ang:
            lw, lh = lh, lw
        return (lx, ly, ang, (lx - lw / 2 - margin, ly - lh / 2 - margin,
                              lx + lw / 2 + margin, ly + lh / 2 + margin))

    leds = [(fp, STATUS_FN[fp.GetReference()]) for fp in board.GetFootprints()
            if fp.GetReference() in STATUS_FN]
    fn_labels = []
    for dy in STATUS_FN_DYS:            # prefer one uniform horizontal row
        boxes = [caption_box(fp, t, dy) for fp, t in leds]
        if all(not any(overlaps(rb, o) for o in obst) for _, _, _, rb in boxes):
            break
    else:                               # ragged fallback: nudge each caption
        boxes = []                      # sideways/down (vertical as a last
        for fp, t in leds:              # resort) until it clears
            cands = [(dy, dx, ang) for ang in (0, 90)
                     for dy in STATUS_FN_DYS for dx in STATUS_FN_DXS]
            for dy, dx, ang in sorted(
                    cands, key=lambda c: (c[2], abs(c[1]),
                                          STATUS_FN_DYS.index(c[0]))):
                lx, ly, a, rb = caption_box(fp, t, dy, dx, ang)
                if not any(overlaps(rb, o)
                           for o in obst + [b[3] for b in boxes]):
                    boxes.append((lx, ly, a, rb))
                    break
            else:
                boxes.append(caption_box(fp, t, STATUS_FN_DYS[0]))
    for (fp, t), (lx, ly, ang, rb) in zip(leds, boxes):
        obst.append(rb)
        fn_labels.append((t, lx, ly, STATUS_FN_SIZE, ang))

    placed = []
    hidden = 0
    order = sorted(board.GetFootprints(),
                   key=lambda f: -f.GetCourtyard(pcbnew.F_CrtYd).BBox().GetWidth())
    for fp in order:
        ref = fp.Reference()
        if fp.GetReference() in SUPPRESS_REF:
            ref.SetVisible(False)
            for f in fp.GetFields():
                if f.GetName() != "Reference":
                    f.SetVisible(False)
            continue
        ref.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(REF_SIZE), pcbnew.FromMM(REF_SIZE)))
        ref.SetTextThickness(pcbnew.FromMM(0.1))
        ref.SetTextAngle(pcbnew.EDA_ANGLE(0))
        # Hide every footprint field except the reference. The BOM workflow
        # left the LCSC part-number field (and others) visible on F.SilkS at
        # full 1.27mm, so 25 part codes piled on top of the designators ->
        # illegible. Silk should carry only the curated ref + our labels.
        for f in fp.GetFields():
            if f.GetName() != "Reference":
                f.SetVisible(False)
        txt = ref.GetText()
        w, h = text_wh(txt, REF_SIZE)
        c = fp.GetCourtyard(pcbnew.F_CrtYd)
        bb = c.BBox() if c.OutlineCount() else fp.GetBoundingBox()
        cx, cy = mm(bb.GetCenter().x), mm(bb.GetCenter().y)
        hw, hh = mm(bb.GetWidth()) / 2, mm(bb.GetHeight()) / 2
        best = None
        # gap sweep to 6mm: with real-size text boxes the dense zones need a
        # longer leash before a ref gives up and hides
        for gap in [x * 0.25 for x in range(1, 25)]:
            for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0),
                           (-1, -1), (1, -1), (-1, 1), (1, 1)):
                px = cx + (dx * (hw + gap + w / 2) if dx else 0)
                py = cy + (dy * (hh + gap + h / 2) if dy else 0)
                rb = (px - w / 2, py - h / 2, px + w / 2, py + h / 2)
                if (rb[0] < EDGE[0] or rb[1] < EDGE[1]
                        or rb[2] > EDGE[2] or rb[3] > EDGE[3]):
                    continue
                if any(overlaps(rb, o) for o in obst):
                    continue
                # keep a small gap between adjacent refs so they can't pack
                # edge-to-edge (which reads as a collision and trips DRC).
                if any(overlaps(rb, (o[0] - 0.2, o[1] - 0.2,
                                     o[2] + 0.2, o[3] + 0.2)) for o in placed):
                    continue
                best = (px, py, rb)
                break
            if best:
                break
        if best is None:
            ref.SetVisible(False)
            hidden += 1
            continue
        px, py, rb = best
        ref.SetVisible(True)
        ref.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(px), pcbnew.FromMM(py)))
        placed.append(rb)

    # auto-place the board title: scan a 0.5mm grid for a clear box, top-first
    title_entries = []
    t_text, t_size = TITLE
    tw, th = text_wh(t_text, t_size)
    tw += 0.4
    th += 0.4
    ty = EDGE[1] + th / 2
    found = None
    while ty < EDGE[3] - th / 2 and not found:
        tx = EDGE[0] + tw / 2
        while tx < EDGE[2] - tw / 2:
            rb = (tx - tw / 2, ty - th / 2, tx + tw / 2, ty + th / 2)
            if (not any(overlaps(rb, o) for o in obst)
                    and not any(overlaps(rb, p) for p in placed)):
                found = (tx, ty, rb)
                break
            tx += 0.5
        ty += 0.5
    if found:
        tx, ty, rb = found
        obst.append(rb)
        placed.append(rb)
        title_entries.append((t_text, tx, ty, t_size))
        print(f"  title auto-placed at ({tx:.2f},{ty:.2f})")
    else:
        print("  WARNING: no clear spot for the board title — omitted")

    for entry in title_entries + LABELS + fn_labels:
        text, x, y, size = entry[:4]
        ang = entry[4] if len(entry) > 4 else 0
        t = pcbnew.PCB_TEXT(board)
        t.SetText(text)
        t.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
        t.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(size), pcbnew.FromMM(size)))
        t.SetTextThickness(pcbnew.FromMM(max(0.1, size / 6)))
        if ang:
            t.SetTextAngle(pcbnew.EDA_ANGLE(float(ang)))
        t.SetLayer(pcbnew.F_SilkS)
        board.Add(t)

    # --- underside metadata block (B.SilkS, mirror-correct) ---------------
    try:
        date = subprocess.check_output(
            ["git", "show", "-s", "--format=%cs", "HEAD"], text=True).strip()
    except Exception:
        date = ""
    meta = [
        ("Designed by Claude", 0.95),
        ("ESP32-C3 IR Remote  rev v2", 0.8),
        (f"{date}  git {git_stamp()}", 0.8),
        ("njdancer.github.io/claude-ir", 0.8),
        ("Non-commercial hobby project", 0.8),
    ]
    mx, my = 152.0, 88.0
    for i, (text, size) in enumerate(meta):
        t = pcbnew.PCB_TEXT(board)
        t.SetText(text)
        t.SetLayer(pcbnew.B_SilkS)
        t.SetMirrored(True)
        t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER)
        t.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(mx), pcbnew.FromMM(my + i * 1.7)))
        t.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(size), pcbnew.FromMM(size)))
        t.SetTextThickness(pcbnew.FromMM(max(0.1, size / 6)))
        board.Add(t)
    # Claude spark logo footprint on the back, left of the text block
    n_logo = 0
    try:
        logo = pcbnew.FootprintLoad(LOGO_LIB, LOGO_FP)
        if logo:
            logo.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(LOGO_AT[0]),
                                             pcbnew.FromMM(LOGO_AT[1])))
            board.Add(logo)
            n_logo = 1
    except Exception as e:
        print("  logo place failed:", e)

    pcbnew.SaveBoard(BOARD_PATH, board)
    print(f"phase2: refs placed, {hidden} hidden, "
          f"{len(LABELS) + len(fn_labels)} front labels "
          f"({len(fn_labels)} per-LED), {len(meta)} back-meta lines, "
          f"{n_logo} logo")


if __name__ == "__main__":
    import sys
    # phases run in SEPARATE processes: a second LoadBoard after Remove() in
    # one process returns an untyped (cursed) board. Default runs both via a
    # re-exec of phase2.
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("all", "1"):
        phase1()
    if which == "2":
        phase2()
    if which == "all":
        import subprocess
        subprocess.run([sys.executable, __file__, "2"], check=True)
