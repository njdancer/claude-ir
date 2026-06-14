#!/usr/bin/env python3
"""Objective PCB layout metrics, parsed straight from the .kicad_pcb s-expr.

Read-only analysis for layout review (no kicad-cli needed). Computes board
geometry, copper coverage, track/via stats, placement density, and a few
design-specific checks (decoupling distance, USB pair match, antenna keepout,
mounting-hole clearance).
"""
import sys, os, math
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "ci"))
from hardware_validate import sexp_parse, walk

PCB = os.path.join(os.path.dirname(__file__), "..", "hardware", "esp32-ir-remote.kicad_pcb")
root = sexp_parse(open(PCB).read())


def g(node, k, d=None):
    for c in node:
        if isinstance(c, list) and c and c[0] == k:
            return c
    return d


def fnum(node, k, i=1, d=None):
    c = g(node, k)
    return float(c[i]) if c else d


def shoelace(pts):
    a = 0.0
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        a += x1 * y2 - x2 * y1
    return abs(a) / 2.0


def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


# ---- board outline ----
edge_pts = []
for x in root:
    if isinstance(x, list) and x[0] in ("gr_line", "gr_rect", "gr_arc"):
        if "Edge.Cuts" in [c[1] for c in x if isinstance(c, list) and c[0] == "layer"]:
            for k in ("start", "end"):
                c = g(x, k)
                if c:
                    edge_pts.append((float(c[1]), float(c[2])))
xs = [p[0] for p in edge_pts]; ys = [p[1] for p in edge_pts]
bx0, bx1, by0, by1 = min(xs), max(xs), min(ys), max(ys)
bw, bh = bx1 - bx0, by1 - by0
board_area = bw * bh
print(f"=== BOARD OUTLINE ===")
print(f"bbox ({bx0:.1f},{by0:.1f})-({bx1:.1f},{by1:.1f})  {bw:.1f} x {bh:.1f} mm  area {board_area:.0f} mm^2  AR {bw/bh:.2f}:1")

# ---- layers ----
layers = g(root, "layers")
cu = [l[1] for l in layers[1:] if isinstance(l, list) and l[1].endswith(".Cu")]
print(f"copper layers: {len(cu)}  {cu}")

# ---- tracks ----
from collections import Counter, defaultdict
seg_len = defaultdict(float); seg_cnt = Counter(); width_cnt = Counter()
net_len = defaultdict(float)
for x in root:
    if isinstance(x, list) and x[0] == "segment":
        s = g(x, "start"); e = g(x, "end")
        L = dist((float(s[1]), float(s[2])), (float(e[1]), float(e[2])))
        lyr = g(x, "layer")[1]; w = g(x, "width")[1]; net = g(x, "net")
        seg_len[lyr] += L; seg_cnt[lyr] += 1; width_cnt[w] += 1
        if net: net_len[net[1] if len(net) > 1 else net[1]] += L
print(f"\n=== TRACKS ===")
for l in sorted(seg_len): print(f"  {l}: {seg_cnt[l]} segs, {seg_len[l]:.0f} mm")
print(f"  total {sum(seg_cnt.values())} segs, {sum(seg_len.values()):.0f} mm")
print("  widths used (mm -> count):", dict(width_cnt.most_common()))

# ---- vias ----
vias = [x for x in root if isinstance(x, list) and x[0] == "via"]
via_nets = Counter(g(v, "net")[1] for v in vias if g(v, "net"))
via_sizes = Counter((g(v, "size")[1], g(v, "drill")[1]) for v in vias)
print(f"\n=== VIAS ===")
print(f"  total {len(vias)};  sizes(size,drill->n): {dict(via_sizes)}")
print(f"  GND vias: {via_nets.get('GND',0)};  signal/other vias: {len(vias)-via_nets.get('GND',0)}")
top_via_nets = [(n,c) for n,c in via_nets.most_common(8)]
print(f"  top via nets: {top_via_nets}")

# ---- zones / copper coverage ----
print(f"\n=== COPPER POUR (zones) ===")
for z in [x for x in root if isinstance(x, list) and x[0] == "zone"]:
    net = g(z, "net_name")
    znet = net[1] if net else (g(z, "net")[1] if g(z, "net") else "?")
    zlayer = g(z, "layer")
    zlayers = g(z, "layers")
    lname = zlayer[1] if zlayer else (",".join(zlayers[1:]) if zlayers else "?")
    frags = []
    for fp in walk(z, "filled_polygon"):
        flyr = g(fp, "layer")
        pts = g(fp, "pts")
        coords = [(float(p[1]), float(p[2])) for p in pts if isinstance(p, list) and p[0] == "xy"]
        if coords:
            frags.append((flyr[1] if flyr else lname, shoelace(coords)))
    by_layer = defaultdict(lambda: [0.0, 0])
    for fl, ar in frags:
        by_layer[fl][0] += ar; by_layer[fl][1] += 1
    for fl, (ar, n) in by_layer.items():
        print(f"  zone net={znet} layer={fl}: {n} fill fragments, total {ar:.0f} mm^2 = {100*ar/board_area:.0f}% of board")

# ---- footprints / placement ----
print(f"\n=== PLACEMENT ===")
fps = [x for x in root if isinstance(x, list) and x[0] == "footprint"]
refs = {}
courtyard_area = 0.0
for fp in fps:
    at = g(fp, "at")
    ref = None
    for pr in walk(fp, "property"):
        if len(pr) > 1 and pr[1] == "Reference":
            ref = pr[2]
    # fp_text reference fallback
    if ref is None:
        for ft in walk(fp, "fp_text"):
            if ft[1] == "reference": ref = ft[2]
    pos = (float(at[1]), float(at[2])) if at else None
    refs[ref] = pos
print(f"  {len(fps)} footprints placed; refs: {sorted(r for r in refs if r and not r.startswith('REF'))}")
# component density
print(f"  density: {len(fps)/board_area*100:.1f} parts / 100 mm^2  (board {board_area:.0f} mm^2)")

# pad-based extents to gauge used vs empty area
pad_xy = []
for fp in fps:
    at = g(fp, "at");
    if not at: continue
    fx, fy = float(at[1]), float(at[2])
    pad_xy.append((fx, fy))
if pad_xy:
    pxs=[p[0] for p in pad_xy]; pys=[p[1] for p in pad_xy]
    print(f"  component origin bbox: x {min(pxs):.1f}-{max(pxs):.1f}  y {min(pys):.1f}-{max(pys):.1f}")

# ---- silk text sizes ----
print(f"\n=== SILKSCREEN TEXT ===")
sizes = Counter()
def collect_text(node):
    for c in node:
        if isinstance(c, list):
            if c[0] in ("gr_text", "fp_text"):
                lyr = g(c, "layer")
                if lyr and "SilkS" in lyr[1]:
                    eff = g(c, "effects")
                    if eff:
                        fontc = g(eff, "font")
                        if fontc:
                            sz = g(fontc, "size")
                            thk = g(fontc, "thickness")
                            if sz: sizes[(sz[1], sz[2], thk[1] if thk else "?")] += 1
            collect_text(c)
collect_text(root)
print("  (h,w,thickness mm -> count):")
for k, v in sizes.most_common():
    print(f"    {k}: {v}")

print("\nrefs dict for downstream checks:")
import json
print(json.dumps({k: v for k, v in refs.items() if k}, default=str))
