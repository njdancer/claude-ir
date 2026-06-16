#!/usr/bin/env python3
"""Generative floorplan search: sample layouts -> route -> score -> rank.

Bold approach to "find a better floorplan" (Nick, 2026-06-15): instead of
hand-nudging, generate many candidate placements, let FreeRouting route each,
and rank by pcb_score.py. FreeRouting is the routability ORACLE (~10 s/board,
deterministic) and pcb_score the fitness function. This orchestrates mature
tools (pcbnew place / FreeRouting route / kicad-cli DRC) — it does not reinvent
routing or DRC.

Search space (physics-constrained anchors stay FIXED — antenna at the N long
edge, USB-C at the W short edge, IR fan firing E, TSOP on the S edge):
  - status-LED row  (D6/D7/D10/D11/D12)  zone + orientation
  - buttons         (SW1/SW2)            zone
  - J4 spare header                      zone  (incl. "under the ESP")
  - LDO group       (U1/F1/D1)           zone
  - sensor          (U5)                 far-from-heat corner
plus small positional jitter. Two named candidates are always included:
  baseline      = the current merged floorplan (control)
  user_hyp      = Nick's idea: LEDs+buttons bottom-left, J4 under the ESP,
                  LDO alone top-left, clear USB lane.

Per candidate: copy pristine board -> apply anchors -> pcb_place_v2 support
re-seat -> courtyard-overlap gate -> rip -> FreeRouting -> import -> score.
Pour+DRC are skipped in the loop (FR unrouted==0 + 0 courtyard overlaps are the
gates); the driver re-runs the FULL pipeline (pour/DRC/validate) only on the
winner. Results -> hardware/fab/search_results.json; best board kept aside.

  JAVA25=... FREEROUTING_JAR=... /usr/bin/python3.12 scripts/pcb_search.py [N] [seed]
"""
import json
import os
import random
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable

PCB = "hardware/esp32-ir-remote.kicad_pcb"
PRISTINE = "/tmp/search_pristine.kicad_pcb"
BEST = "/tmp/search_best.kicad_pcb"
RESULTS = "hardware/fab/search_results.json"

# Anchors fixed by physics — never varied (values from the merged floorplan).
FIXED = {
    "J2": (110.0, 94.0, 270),                  # USB-C, W edge, meets U3's W USB pins
    "U3": (150.0, 96.0, 180),                  # MCU rotated 180, antenna overhangs S
    "Q3": (174.0, 98.0, 0),                    # IR driver MOSFET, W of LED fan
    "D2": (188.0, 80.0, 315), "D3": (188.0, 90.0, 285),
    "D4": (188.0, 100.0, 255), "D5": (188.0, 110.0, 225),  # IR fan firing E
    "J5": (192.0, 96.0, 0),                    # ext-IR header, E edge
    "F1": (127.0, 76.0, 0), "D1": (132.0, 76.0, 0),        # VBUS chain (NW)
}

# Discrete zones for the flexible groups (rotated-U3 layout: free space is the
# N band y70-86 + the W column x106-134). (x, y[, extra]) in mm.
LED_ZONES = {                          # 5-LED status row/col
    "N_row":   (142.0, 73.0, "h"),     # N edge row, centre
    "N_row_e": (150.0, 73.0, "h"),     # N edge, shifted E
    "W_col":   (126.0, 84.0, "v"),     # W column vertical
}
BTN_ZONES = {
    "W_edge":  (112.0, 104.0, "h"),    # W edge, horizontal pair
    "W_stack": (110.0, 103.0, "v"),    # W edge, vertical pair
}
J4_ZONES = {
    "N_ctr": (150.0, 82.0, 0),         # N of U3 (heaviest link)
    "N_e":   (162.0, 80.0, 0),
    "N_w":   (140.0, 81.0, 0),
}
LDO_ZONES = {
    "NW":       (118.0, 76.0, 90),
    "NW_tight": (115.0, 75.0, 90),
}
U5_ZONES = {
    "NE": (183.0, 75.0, 0),
    "E":  (185.0, 88.0, 0),
}
U4_ZONES = {                           # TSOP IR-RX (lens N, clear of the E fan)
    "N_ctr": (145.0, 74.0, 0),
    "N_w":   (135.0, 74.0, 0),
    "N_e":   (158.0, 74.0, 0),
}
LED_PITCH = 5.0
LED_REFS = ["D6", "D7", "D10", "D11", "D12"]


def led_row(x, y, orient, rot=90):
    out = {}
    for i, r in enumerate(LED_REFS):
        if orient == "h":
            out[r] = (round(x + i * LED_PITCH, 2), y, rot)
        else:
            out[r] = (x, round(y + i * LED_PITCH, 2), rot)
    return out


def buttons(x, y, orient):
    if orient == "h":
        return {"SW1": (x, y, 0), "SW2": (round(x + 11, 2), y, 0)}
    return {"SW1": (x, y, 0), "SW2": (x, round(y + 11, 2), 0)}


def make_anchors(choices, rng=None, jit=0.0):
    """Build a full anchor dict from a dict of zone keys, with optional jitter."""
    def J(v):
        return round(v + rng.uniform(-jit, jit), 2) if (rng and jit) else v
    a = {r: (J(x), J(y), rot) for r, (x, y, rot) in FIXED.items()}
    lx, ly, lo = LED_ZONES[choices["led"]]
    a.update({r: (J(px), J(py), rot)
              for r, (px, py, rot) in led_row(lx, ly, lo).items()})
    bx, by, bo = BTN_ZONES[choices["btn"]]
    a.update({r: (J(px), J(py), rot)
              for r, (px, py, rot) in buttons(bx, by, bo).items()})
    for grp, table in (("j4", J4_ZONES), ("ldo", LDO_ZONES), ("u5", U5_ZONES),
                       ("u4", U4_ZONES)):
        key = choices[grp]
        x, y, rot = table[key]
        ref = {"j4": "J4", "ldo": "U1", "u5": "U5", "u4": "U4"}[grp]
        a[ref] = (J(x), J(y), rot)
    return a


PENALTY = 1e6


def _run(args):
    """Run a pipeline stage in its own process (the codebase's SWIG-safe
    pattern); stderr is swallowed (pcbnew assert noise)."""
    return subprocess.run([PY] + args, cwd=os.path.dirname(HERE) or ".",
                          capture_output=True, text=True)


def _drc():
    """Authoritative legality gate: (errors, unconnected) from kicad-cli."""
    out = "/tmp/cand_drc.json"
    subprocess.run(["kicad-cli", "pcb", "drc", "--severity-error",
                    "--exit-code-violations", "-o", out, "--format", "json", PCB],
                   capture_output=True, text=True, cwd=os.path.dirname(HERE) or ".")
    try:
        d = json.load(open(out))
        return len(d.get("violations", [])), len(d.get("unconnected_items", []))
    except Exception:
        return 999, 999


def evaluate(choices, rng, jit, tag):
    """Run one candidate end-to-end via per-stage subprocesses. Hard gates:
    0 DRC errors + 0 unconnected (FreeRouting + KiCad DRC); else PENALTY."""
    shutil.copy(PRISTINE, PCB)
    anchors = make_anchors(choices, rng, jit)
    aj = "/tmp/cand_anchors.json"
    json.dump(anchors, open(aj, "w"))
    if _run([__file__, "_apply", aj]).returncode:
        return None, PENALTY, f"{tag}: ERROR apply"
    if _run([os.path.join(HERE, "pcb_place_v2.py")]).returncode:
        return None, PENALTY, f"{tag}: ERROR place"
    _run([os.path.join(HERE, "pcb_rip.py")])
    for stage in ("export", "route", "import"):
        _run([os.path.join(HERE, "pcb_route_fr.py"), stage])
    _run([os.path.join(HERE, "pcb_pour.py")])        # GND pour so DRC unconn is real
    errs, unconn = _drc()
    ev = _run([__file__, "_eval", "routed"])
    try:
        res = json.loads(ev.stdout.strip().splitlines()[-1])
    except Exception:
        return None, PENALTY, f"{tag}: ERROR eval ({ev.stdout[-200:]})"
    m, s = res["metrics"], res["score"]
    m.update(drc_err=errs, unconn=unconn)
    if errs or unconn:
        s += PENALTY * 0.001 * (errs + unconn) + 5000.0   # keep illegal below legal
    return m, s, f"{tag}: score {s:8.1f}  drc_err {errs} unconn {unconn}  {fmt(m)}"


def fmt(m):
    return (f"usb_bcu {m['usb_bcu_mm']:.0f} v{m['usb_vias']} "
            f"bcu_sig {m['bcu_sig_mm']:.0f} trk {m['track_mm']:.0f} "
            f"via {m['vias']} dec {m['decap_mm']:.0f}")


def candidates(n, rng):
    """Named controls first, then random combos (dedup)."""
    named = [
        ("v3_hand", dict(led="N_row", btn="W_edge", j4="N_ctr", ldo="NW",
                         u5="NE", u4="N_w")),
    ]
    seen = {tuple(sorted(c.items())) for _, c in named}
    out = list(named)
    tries = 0
    while len(out) < n and tries < n * 20:
        tries += 1
        c = dict(led=rng.choice(list(LED_ZONES)), btn=rng.choice(list(BTN_ZONES)),
                 j4=rng.choice(list(J4_ZONES)), ldo=rng.choice(list(LDO_ZONES)),
                 u5=rng.choice(list(U5_ZONES)), u4=rng.choice(list(U4_ZONES)))
        key = tuple(sorted(c.items()))
        if key in seen:
            continue
        seen.add(key)
        out.append((f"rand{len(out)-1:02d}", c))
    return out


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    rng = random.Random(seed)
    shutil.copy(PCB, PRISTINE)
    os.makedirs(os.path.dirname(RESULTS), exist_ok=True)
    rows = []
    best = None
    for tag, choices in candidates(n, rng):
        jit = 0.0 if tag == "v3_hand" else 0.6
        try:
            m, s, line = evaluate(choices, rng, jit=jit, tag=tag)
        except Exception as e:                # a bad candidate must not kill the run
            m, s, line = None, PENALTY, f"{tag}: ERROR {e}"
        print(line, flush=True)
        rows.append(dict(tag=tag, choices=choices, score=s, metrics=m))
        if best is None or s < best["score"]:
            best = dict(tag=tag, choices=choices, score=s, metrics=m)
            shutil.copy(PCB, BEST)
    rows.sort(key=lambda r: r["score"])
    json.dump({"best": best, "rows": rows}, open(RESULTS, "w"), indent=2)
    shutil.copy(PRISTINE, PCB)                # leave working tree pristine
    print("\n=== TOP 5 ===")
    for r in rows[:5]:
        print(f"  {r['tag']:10} {r['score']:8.1f}  {r['choices']}")
    print(f"\nbest = {best['tag']} ({best['score']:.1f}); board -> {BEST}")


# flexible anchors the search moves (others — antenna/USB/IR-fan/TSOP — are
# physics-fixed and never legalized, only treated as obstacles).
FLEX = set(LED_REFS) | {"SW1", "SW2", "J4", "U1", "U5", "U4"}


def _legalize(b, anchors):
    """Spiral-nudge each FLEX anchor to the nearest collision-free slot near its
    target, treating fixed anchors + holes (and already-placed FLEX) as
    obstacles. Reuses pcb_place_v2's courtyard/overlap/keepout helpers. Keeps
    each part's orientation (anchors carry meaningful rotation)."""
    import math
    import pcbnew
    import pcb_place_v2 as pv
    fps = {f.GetReference(): f for f in b.GetFootprints()}
    anchor_refs = (set(anchors) | set(__import__("pcb_floorplan").HOLES)) & set(fps)
    placed = [pv.court_bbox(fps[r]) for r in anchor_refs if r not in FLEX]
    ko = pv.keepout_box(b)
    order = ["U1", "J4", "U5", "SW1", "SW2"] + LED_REFS   # big/structural first
    for ref in [r for r in order if r in anchors and r in fps]:
        f = fps[ref]
        tx, ty, _ = anchors[ref]
        w, h = pv.court_wh(f)
        best = None
        for R in [x * 0.25 for x in range(0, 160)]:
            steps = max(8, int(2 * math.pi * R / 0.25)) if R > 0 else 1
            for s in range(steps):
                th = 2 * math.pi * s / steps
                cx, cy = round(tx + R * math.cos(th), 2), round(ty + R * math.sin(th), 2)
                bb = (cx - w / 2 - pv.MARGIN, cy - h / 2 - pv.MARGIN,
                      cx + w / 2 + pv.MARGIN, cy + h / 2 + pv.MARGIN)
                if bb[0] < pv.X0 or bb[1] < pv.Y0 or bb[2] > pv.X1 or bb[3] > pv.Y1:
                    continue
                if ko and pv.overlaps(bb, ko):
                    continue
                if any(pv.overlaps(bb, p) for p in placed):
                    continue
                best = (cx, cy, bb)
                break
            if best:
                break
        if best:
            cx, cy, bb = best
            f.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(cx), pcbnew.FromMM(cy)))
            placed.append(bb)


def _apply(aj):
    """Subprocess stage: apply a generated anchor dict, then legalize the
    flexible anchors off any collisions, then draw the outline + save."""
    import pcbnew
    sys.path.insert(0, HERE)
    import pcb_floorplan as fp
    anchors = {k: tuple(v) for k, v in json.load(open(aj)).items()}
    b = pcbnew.LoadBoard(PCB)
    fp.apply_anchors(b, anchors, fp.HOLES, draw_outline=False)
    _legalize(b, anchors)
    fp.set_outline(b)
    pcbnew.SaveBoard(PCB, b)


def _eval(mode):
    """Subprocess stage: emit a JSON line. mode=placement -> courtyard overlap
    count; mode=routed -> metrics + score + unrouted."""
    import pcbnew
    sys.path.insert(0, HERE)
    import pcb_score
    if mode == "placement":
        b = pcbnew.LoadBoard(PCB)
        boxes = []
        for f in b.GetFootprints():
            sh = f.GetCourtyard(pcbnew.F_CrtYd)
            bb = sh.BBox()
            if bb.GetWidth() == 0:
                bb = f.GetBoundingBox()
            boxes.append((pcbnew.ToMM(bb.GetLeft()), pcbnew.ToMM(bb.GetTop()),
                          pcbnew.ToMM(bb.GetRight()), pcbnew.ToMM(bb.GetBottom())))
        n = 0
        for i in range(len(boxes)):
            ax0, ay0, ax1, ay1 = boxes[i]
            for j in range(i + 1, len(boxes)):
                bx0, by0, bx1, by1 = boxes[j]
                if not (ax1 <= bx0 or ax0 >= bx1 or ay1 <= by0 or ay0 >= by1):
                    n += 1
        print(json.dumps({"overlaps": n}))
    else:
        m = pcb_score.metrics(PCB)
        print(json.dumps({"metrics": m, "score": pcb_score.score(m)}))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "_apply":
        _apply(sys.argv[2])
    elif len(sys.argv) > 1 and sys.argv[1] == "_eval":
        _eval(sys.argv[2])
    else:
        main()
