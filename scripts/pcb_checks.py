#!/usr/bin/env python3
"""Design-specific layout checks: decoupling distance, USB pair, antenna
keepout, mounting-hole clearance, LDO thermal copper, edge clearance."""
import sys, os, math
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "ci"))
from hardware_validate import sexp_parse, walk
from collections import defaultdict

PCB = os.path.join(os.path.dirname(__file__), "..", "hardware", "esp32-ir-remote.kicad_pcb")
root = sexp_parse(open(PCB).read())

def g(node, k):
    for c in node:
        if isinstance(c, list) and c and c[0] == k:
            return c
    return None

def rot(px, py, deg):
    r = math.radians(deg)
    return (px * math.cos(r) - py * math.sin(r), px * math.sin(r) + py * math.cos(r))

def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])

# Build pad table: ref -> list of (padname, (x,y), net)
fps = [x for x in root if isinstance(x, list) and x[0] == "footprint"]
pads = defaultdict(list)          # ref -> [(pad, (x,y), net)]
net_pads = defaultdict(list)      # net -> [(ref.pad, (x,y))]
fp_pos = {}
fp_courtyard = {}                 # ref -> list of courtyard polylines (abs)
for fp in fps:
    at = g(fp, "at")
    if not at: continue
    fx, fy = float(at[1]), float(at[2])
    fr = float(at[3]) if len(at) > 3 else 0.0
    ref = None
    for pr in walk(fp, "property"):
        if len(pr) > 1 and pr[1] == "Reference":
            ref = pr[2]
    if ref is None:
        for ft in walk(fp, "fp_text"):
            if ft[1] == "reference": ref = ft[2]
    fp_pos[ref] = (fx, fy, fr)
    for pad in walk(fp, "pad"):
        pat = g(pad, "at")
        if not pat: continue
        rx, ry = rot(float(pat[1]), float(pat[2]), fr)
        ax, ay = fx + rx, fy + ry
        netc = g(pad, "net")
        net = netc[2] if netc and len(netc) > 2 else (netc[1] if netc else None)
        pads[ref].append((pad[1], (ax, ay), net))
        if net:
            net_pads[net].append((f"{ref}.{pad[1]}", (ax, ay)))

def pad_xy(ref, padname):
    for p, xy, n in pads.get(ref, []):
        if p == padname: return xy
    return None

def pads_on_net_for(ref, net):
    return [(p, xy) for p, xy, n in pads.get(ref, []) if n == net]

# ---------- 1. Decoupling cap distance to served IC power pin ----------
print("=== DECOUPLING / BYPASS CAP DISTANCE ===")
# (cap, capnet, IC, ICnet) — distance from cap pad to nearest IC pad on same net
decoupling = [
    ("C7", "U3"), ("C5", "U3"), ("C8", "U3"), ("C10", "U3"),  # MCU bypass
    ("C1", "U1"), ("C2", "U1"), ("C3", "U1"),                  # LDO in/out
]
for cap, ic in decoupling:
    best = None
    for cp, cxy, cn in pads.get(cap, []):
        if cn in (None, "GND"):   # measure on the non-ground (power/signal) pad
            continue
        for ip, ixy, inn in pads.get(ic, []):
            if inn == cn:
                d = dist(cxy, ixy)
                if best is None or d < best[0]:
                    best = (d, cn, ip)
    if best:
        flag = "  <-- >3mm" if best[0] > 3.0 else ""
        print(f"  {cap} -> {ic}.{best[2]} ({best[1]}): {best[0]:.2f} mm{flag}")
    else:
        print(f"  {cap} -> {ic}: no shared power net found (check refs)")

# ---------- 2. USB differential pair ----------
print("\n=== USB D+/D- DIFFERENTIAL PAIR ===")
def net_track_len(netname):
    L = 0.0; layers=set()
    for x in root:
        if isinstance(x, list) and x[0] == "segment":
            nc = g(x, "net")
            n = nc[2] if nc and len(nc)>2 else (nc[1] if nc else None)
            if n == netname:
                s = g(x, "start"); e = g(x, "end")
                L += dist((float(s[1]),float(s[2])),(float(e[1]),float(e[2])))
                layers.add(g(x,"layer")[1])
    return L, layers
for net in ("/USB_D+", "/USB_D-"):
    L, ly = net_track_len(net)
    nv = sum(1 for v in root if isinstance(v,list) and v[0]=="via" and g(v,"net") and (g(v,"net")[2] if len(g(v,"net"))>2 else g(v,"net")[1])==net)
    print(f"  {net}: {L:.2f} mm on {sorted(ly)}, {nv} vias")
lp,_ = net_track_len("/USB_D+"); lm,_ = net_track_len("/USB_D-")
print(f"  length mismatch: {abs(lp-lm):.2f} mm")

# ---------- 3. ESP32-C3 antenna keepout: copper under antenna region ----------
print("\n=== ANTENNA KEEPOUT (U3 ESP32-C3) ===")
ux, uy, ur = fp_pos["U3"]
print(f"  U3 at ({ux:.1f},{uy:.1f}) rot {ur}")
# ESP32-C3-WROOM-02 ~ 18x20mm, antenna is the ~6mm end. Approx antenna keepout
# as a band at the module end. Report nearest copper feature to U3 origin end.
# Find the module's pad extent to locate the antenna (opposite the pad cluster).
u3pads = [xy for _, xy, _ in pads["U3"]]
if u3pads:
    pxs=[p[0] for p in u3pads]; pys=[p[1] for p in u3pads]
    print(f"  U3 pad bbox: x {min(pxs):.1f}-{max(pxs):.1f}  y {min(pys):.1f}-{max(pys):.1f}")
    print(f"  board bbox y 70-114; U3 pad y-extent vs board edges -> top gap {min(pys)-70:.1f}mm bottom gap {114-max(pys):.1f}mm")
# count tracks/vias within a bbox guess for the antenna (need manual edge align)

# ---------- 4. Mounting hole clearance ----------
print("\n=== MOUNTING HOLES ===")
# collect all copper feature points (track endpoints + via centers + pads not on the hole)
copper_pts = []
for x in root:
    if isinstance(x, list) and x[0]=="segment":
        s=g(x,"start"); e=g(x,"end"); copper_pts.append((float(s[1]),float(s[2]))); copper_pts.append((float(e[1]),float(e[2])))
    if isinstance(x, list) and x[0]=="via":
        a=g(x,"at"); copper_pts.append((float(a[1]),float(a[2])))
for ref in ("H1","H2","H3","H4"):
    if ref not in fp_pos: continue
    hx,hy,_ = fp_pos[ref]
    # nearest copper track/via
    nearest = min((dist((hx,hy),p) for p in copper_pts), default=None)
    # nearest other-footprint pad
    npad = min((dist((hx,hy),xy) for r,plist in pads.items() if r!=ref for _,xy,_ in plist), default=None)
    edge = min(hx-106, 198-hx, hy-70, 114-hy)
    print(f"  {ref} at ({hx:.1f},{hy:.1f}): nearest track/via {nearest:.1f}mm, nearest pad {npad:.1f}mm, edge {edge:.1f}mm")

# ---------- 5. Component-to-edge clearance ----------
print("\n=== COMPONENT-TO-EDGE (pad nearest each board edge) ===")
allpads = [(r,p,xy) for r,plist in pads.items() for p,xy,_ in plist]
for name, fn in [("west x=106", lambda xy: xy[0]-106),("east x=198", lambda xy:198-xy[0]),
                 ("north y=70", lambda xy: xy[1]-70),("south y=114", lambda xy:114-xy[1])]:
    r,p,xy = min(allpads, key=lambda t: fn(t[2]))
    print(f"  {name}: closest pad {r}.{p} at {fn(xy):.2f} mm")

# ---------- 6. LDO thermal copper (U1 SOT-223 tab) ----------
print("\n=== LDO U1 THERMAL ===")
# tab pad is the large one (pad '2'/'4' on SOT-223 is the tab = VOUT typ). report GND/VOUT copper near U1
print(f"  U1 at {fp_pos['U1'][:2]}")
for p, xy, n in pads.get("U1", []):
    print(f"    pad {p} net={n} at ({xy[0]:.1f},{xy[1]:.1f})")
