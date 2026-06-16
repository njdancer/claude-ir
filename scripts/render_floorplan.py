#!/usr/bin/env python3
"""Floorplan mock-ups as coloured blocks on a to-scale board rectangle.

Cheap, pre-KiCad iteration: draw each functional ZONE as a coloured block on the
92x44 outline, with flight-lines for every signal net (from U3's real pad side
where the MCU is involved, so the picture respects the module pinout) and a
wirelength PROXY (sum of flight-line lengths, lower = easier to route). Lets us
compare floorplans before doing the real placement in KiCad.

  /usr/bin/python3.12 scripts/render_floorplan.py
"""
import json
import math
import os
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch

BX0, BY0, BX1, BY1 = 106.0, 70.0, 198.0, 114.0
PCB = "hardware/esp32-ir-remote.kicad_pcb"
NET = "hardware/esp32-ir-remote.net"
# functional-zone seeds (mm) used to classify every part by nearest seed
SEEDS = {"POWER/USB": (116, 88), "MCU": (150, 88.5), "IR-TX": (185, 92),
         "IR-RX": (149, 110), "SENSOR": (166, 110), "STATUS": (151, 104),
         "BUTTONS": (125, 109), "HEADER": (132, 84)}


def extract():
    """Pull part sizes, the zone classification + adjacency, and U3's pad sides
    straight from the board/netlist (self-contained, reproducible)."""
    import pcbnew
    b = pcbnew.LoadBoard(PCB)
    parts = {}
    for f in b.GetFootprints():
        sh = f.GetCourtyard(pcbnew.F_CrtYd); bb = sh.BBox()
        if bb.GetWidth() == 0:
            bb = f.GetBoundingBox()
        p = f.GetPosition()
        parts[f.GetReference()] = dict(
            ref=f.GetReference(), x=round(pcbnew.ToMM(p.x), 2),
            y=round(pcbnew.ToMM(p.y), 2), w=round(pcbnew.ToMM(bb.GetWidth()), 2),
            h=round(pcbnew.ToMM(bb.GetHeight()), 2))

    def zone_of(p):
        return min(SEEDS, key=lambda z: math.hypot(p["x"] - SEEDS[z][0],
                                                    p["y"] - SEEDS[z][1]))
    z2refs = {z: [] for z in SEEDS}
    for r, p in parts.items():
        z2refs[zone_of(p)].append(r)
    ref2zone = {r: zone_of(p) for r, p in parts.items()}

    u3 = next(f for f in b.GetFootprints() if f.GetReference() == "U3")
    u3pads = {}
    for pad in u3.Pads():
        nn = pad.GetNetname()
        if nn and nn != "GND":
            pp = pad.GetPosition()
            u3pads[nn] = (round(pcbnew.ToMM(pp.x), 1), round(pcbnew.ToMM(pp.y), 1))

    txt = open(NET).read()
    nets = re.findall(r'\(net\s+\(code "\d+"\)\s+\(name "([^"]*)"\)(.*?)'
                      r'(?=\n\t*\(net\s+\(code|\Z)', txt, re.S)
    netzones = {}
    for name, body in nets:
        if name in ("GND", "+3.3V", "+5V"):
            continue
        zs = sorted({ref2zone[m.group(1)] for m in
                     re.finditer(r'\(ref "([^"]+)"\)', body) if m.group(1) in ref2zone})
        if zs:
            netzones[name] = zs
    json.dump([parts[r] for r in parts], open("/tmp/parts.json", "w"))
    json.dump({"z2refs": z2refs}, open("/tmp/zones.json", "w"))
    json.dump({"u3pads": u3pads, "netzones": netzones}, open("/tmp/netgeo.json", "w"))


if not all(os.path.exists(f) for f in ("/tmp/parts.json", "/tmp/zones.json",
                                       "/tmp/netgeo.json")):
    extract()
parts = {p["ref"]: p for p in json.load(open("/tmp/parts.json"))}
zinfo = json.load(open("/tmp/zones.json"))
geo = json.load(open("/tmp/netgeo.json"))
U3PADS, NETZONES = geo["u3pads"], geo["netzones"]

ZCOLOR = {"POWER/USB": "#e74c3c", "MCU": "#3498db", "IR-TX": "#e67e22",
          "IR-RX": "#9b59b6", "SENSOR": "#1abc9c", "STATUS": "#f1c40f",
          "BUTTONS": "#95a5a6", "HEADER": "#34495e"}
# zone block sizes (mm): compact, from the total component AREA of the members
# (so a block ~ the silicon it must hold), aspect ~1.4.
ZSIZE = {}
for z, refs in zinfo["z2refs"].items():
    area = sum(parts[r]["w"] * parts[r]["h"] for r in refs if r in parts)
    area = max(area, 60)
    ZSIZE[z] = (math.sqrt(area * 1.4), math.sqrt(area / 1.4))
ZSIZE["MCU"] = (parts["U3"]["w"], parts["U3"]["h"])

NETCOLOR = {"USB": "#c0392b", "I2C": "#16a085", "IR": "#d35400"}
def netcol(n):
    if "USB" in n: return NETCOLOR["USB"], 2.2
    if "I2C" in n: return NETCOLOR["I2C"], 1.6
    if "IR" in n: return NETCOLOR["IR"], 1.4
    return "#7f8c8d", 0.7

# U3 pad offsets relative to its current centre, so a layout can rotate the
# module and the flight-lines follow the pins. Antenna keepout is a fixed
# offset from the centre too (it moves/rotates with the module).
U3C = (150.0, 88.5)
U3REL = {n: (x - U3C[0], y - U3C[1]) for n, (x, y) in U3PADS.items()}
ANT_REL = (0.0, -14.5)            # keepout centre rel to U3 centre; 28x8 mm


def xform(rel, cx, cy, rot):
    rx, ry = rel
    if rot == 180:
        return (cx - rx, cy - ry)
    return (cx + rx, cy + ry)      # rot 0 (only 0/180 used here)


def u3pad(net, mcu):
    return xform(U3REL[net], *mcu)


# --- layouts: zone -> (cx, cy); MCU -> (cx, cy, rot). --------------------------
CUR = {}
for z, refs in zinfo["z2refs"].items():
    xs = [parts[r]["x"] for r in refs if r in parts]
    ys = [parts[r]["y"] for r in refs if r in parts]
    CUR[z] = (sum(xs) / len(xs), sum(ys) / len(ys))
CUR["MCU"] = (150.0, 88.5, 0)

# P_user (Nick): rotate U3 180 + push to the S edge -> antenna overhangs S, USB
# pins flip to the W (toward the W USB-C), IR pins flip to the E (toward the E
# fan). The S peripherals move up into the now-free N band.
USER = {"MCU": (150.0, 98.0, 180), "POWER/USB": (116, 90), "IR-TX": (185, 90),
        "IR-RX": (120, 75), "SENSOR": (168, 78), "STATUS": (150, 76),
        "BUTTONS": (124, 80), "HEADER": (138, 88)}
# P1 flip-zones: keep U3/antenna N, instead move IR->W and power/USB->E.
FLIP = {"MCU": (150.0, 88.5, 0), "IR-TX": (118, 90), "IR-RX": (120, 107),
        "POWER/USB": (184, 90), "HEADER": (170, 104), "SENSOR": (150, 108),
        "STATUS": (135, 107), "BUTTONS": (121, 100)}
# P3 tightened-current: keep ends, pull HEADER+STATUS onto U3, USB-C as far E as
# the W power zone allows.
TIGHT = dict(CUR)
TIGHT.update({"HEADER": (138, 80), "STATUS": (150, 102), "POWER/USB": (124, 92),
              "BUTTONS": (122, 108), "SENSOR": (168, 108), "IR-RX": (150, 110)})

LAYOUTS = [("Current", CUR),
           ("P-Nick: rotate U3 180 + push to S edge", USER),
           ("P1: flip zones (IR<->power), U3 stays N", FLIP),
           ("P3: tightened current", TIGHT)]


def antenna_box(mcu):
    cx, cy = xform(ANT_REL, *mcu)
    return (cx - 14, cy - 4, cx + 14, cy + 4)


def proxy(L):
    """Flight-line lengths (mm): (total, usb, ir). MCU endpoint uses the real
    U3 pad side so module rotation is reflected."""
    mcu = L["MCU"]
    tot = usb = ir = 0.0
    for net, zones in NETZONES.items():
        pts = []
        for z in zones:
            if z == "MCU" and net in U3REL:
                pts.append(u3pad(net, mcu))
            elif z in L and z != "MCU":
                pts.append(L[z][:2])
        d = 0.0
        for i in range(len(pts)):
            for j in range(i + 1, len(pts)):
                d += math.hypot(pts[i][0] - pts[j][0], pts[i][1] - pts[j][1])
        tot += d
        if "USB" in net:
            usb += d
        if "IR_" in net:
            ir += d
    return tot, usb, ir


def draw(ax, title, L):
    mcu = L["MCU"]
    ax.add_patch(Rectangle((BX0, BY0), BX1 - BX0, BY1 - BY0, fill=False, lw=2,
                           ec="black"))
    ax0, ay0, ax1, ay1 = antenna_box(mcu)
    ax.add_patch(Rectangle((ax0, ay0), ax1 - ax0, ay1 - ay0, facecolor="none",
                 ec="black", hatch="////", lw=0.5))
    ax.text((ax0 + ax1) / 2, (ay0 + ay1) / 2, "antenna", ha="center",
            va="center", fontsize=5)
    for net, zones in NETZONES.items():
        pts = []
        for z in zones:
            if z == "MCU" and net in U3REL:
                pts.append(u3pad(net, mcu))
            elif z in L and z != "MCU":
                pts.append(L[z][:2])
        col, lw = netcol(net)
        for i in range(len(pts)):
            for j in range(i + 1, len(pts)):
                ax.plot([pts[i][0], pts[j][0]], [pts[i][1], pts[j][1]],
                        color=col, lw=lw, alpha=0.55, zorder=1)
    for z, c in L.items():
        cx, cy = c[:2]
        w, h = ZSIZE.get(z, (12, 8))
        ax.add_patch(FancyBboxPatch((cx - w / 2, cy - h / 2), w, h,
                     boxstyle="round,pad=0.2,rounding_size=1.5",
                     facecolor=ZCOLOR[z], ec="black", lw=1, alpha=0.85, zorder=3))
        n = len(zinfo["z2refs"].get(z, [])) if z != "MCU" else 1
        lbl = z + (f"\n({n})" if z != "MCU" else f"\nU3 r{mcu[2]}")
        ax.text(cx, cy, lbl, ha="center", va="center", fontsize=6,
                weight="bold", zorder=4)
    ax.set_xlim(BX0 - 3, BX1 + 3)
    ax.set_ylim(BY1 + 3, BY0 - 3)
    ax.set_aspect("equal")
    tot, usb, ir = proxy(L)
    ax.set_title(f"{title}\nwire proxy: total {tot:.0f}  |  USB {usb:.0f}  |  "
                 f"IR {ir:.0f} mm", fontsize=8.5)
    ax.axis("off")


REF2ZONE = {r: z for z, refs in zinfo["z2refs"].items() for r in refs}


def draw_components(ax):
    """Faithful reproduction of the CURRENT board: every part as a to-scale
    block at its real position, coloured by zone."""
    ax.add_patch(Rectangle((BX0, BY0), BX1 - BX0, BY1 - BY0, fill=False, lw=2,
                           ec="black"))
    a = antenna_box((150.0, 88.5, 0))
    ax.add_patch(Rectangle((a[0], a[1]), a[2] - a[0], a[3] - a[1],
                 facecolor="none", ec="black", hatch="////", lw=0.5))
    for net, zones in NETZONES.items():
        pts = [u3pad(net, (150.0, 88.5, 0)) if (z == "MCU" and net in U3REL)
               else CUR[z][:2] for z in zones if z == "MCU" or z in CUR]
        col, lw = netcol(net)
        for i in range(len(pts)):
            for j in range(i + 1, len(pts)):
                ax.plot([pts[i][0], pts[j][0]], [pts[i][1], pts[j][1]],
                        color=col, lw=lw, alpha=0.5, zorder=1)
    for r, p in parts.items():
        if r not in REF2ZONE:
            continue
        ax.add_patch(Rectangle((p["x"] - p["w"] / 2, p["y"] - p["h"] / 2),
                     p["w"], p["h"], facecolor=ZCOLOR[REF2ZONE[r]], ec="black",
                     lw=0.4, alpha=0.85, zorder=3))
        if p["w"] * p["h"] > 12:
            ax.text(p["x"], p["y"], r, ha="center", va="center", fontsize=4,
                    zorder=4)
    ax.set_xlim(BX0 - 3, BX1 + 3)
    ax.set_ylim(BY1 + 3, BY0 - 3)
    ax.set_aspect("equal")
    ax.set_title("CURRENT board — actual components (coloured by zone)",
                 fontsize=9)
    ax.axis("off")


figc, axc = plt.subplots(figsize=(13, 7))
draw_components(axc)
from matplotlib.lines import Line2D as _L
zleg = [_L([0], [0], marker="s", color="w", markerfacecolor=c, markersize=9,
           label=z) for z, c in ZCOLOR.items()]
figc.legend(handles=zleg, loc="lower center", ncol=8, fontsize=7)
figc.tight_layout(rect=(0, 0.04, 1, 1))
figc.savefig("/tmp/current_components.png", dpi=130)

fig, axes = plt.subplots(2, 2, figsize=(16, 9))
for ax, (title, L) in zip(axes.flat, LAYOUTS):
    draw(ax, title, L)
# legend
from matplotlib.lines import Line2D
leg = [Line2D([0], [0], color=NETCOLOR["USB"], lw=2.2, label="USB pair"),
       Line2D([0], [0], color=NETCOLOR["I2C"], lw=1.6, label="I2C"),
       Line2D([0], [0], color=NETCOLOR["IR"], lw=1.4, label="IR"),
       Line2D([0], [0], color="#7f8c8d", lw=0.7, label="other signal")]
fig.legend(handles=leg, loc="lower center", ncol=4, fontsize=8)
fig.suptitle("ESP32-C3 IR remote — 2-layer floorplan options (92x44mm). "
             "Flight lines from U3's real pad sides; lower proxy = easier route.",
             fontsize=11)
fig.tight_layout(rect=(0, 0.03, 1, 0.97))
fig.savefig("/tmp/floorplans.png", dpi=120)
print("wrote /tmp/floorplans.png + /tmp/current_components.png")
for title, L in LAYOUTS:
    t, u, i = proxy(L)
    print(f"  {title:40} total {t:5.0f}  USB {u:4.0f}  IR {i:4.0f} mm")
