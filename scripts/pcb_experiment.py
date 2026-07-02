#!/usr/bin/env python3
"""One autoresearch experiment: apply a candidate spec -> route -> score -> log.

This is the *immutable evaluator* of the autoresearch loop (the "prepare.py" /
ruler — see hardware/notes/autoresearch.md). The agent edits the *artifact* (the
floorplan in pcb_floorplan.ANCHORS and/or a GPIO remap json), then runs this to
measure it. Pipeline, all on a fresh copy of the pristine (git HEAD) board:

  apply ANCHORS floorplan (+ optional GPIO remap) -> pcb_place_v2 (net-driven
  support re-seat) -> courtyard-overlap gate -> pcb_rip -> FreeRouting
  (export/route/import) -> pcb_pour -> kicad-cli DRC -> pcb_score

Logs one JSON line to hardware/fab/experiments.jsonl (the results.tsv analogue):
tag, score, drc errors, unrouted, USB metrics, and the spec. Keeps the best
board so far at /tmp/ar_best.kicad_pcb (the ratchet). The working tree is left
holding THIS candidate's routed board (so the agent can inspect/iterate); restore
the merged baseline with `git checkout hardware/esp32-ir-remote.kicad_pcb`.

  export JAVA25=...  FREEROUTING_JAR=...
  /usr/bin/python3.12 scripts/pcb_experiment.py --tag <name> [--gpio gpio.json]

Determinism: FreeRouting is single-threaded sequential; the same spec scores the
same. PENALTY-scores any candidate that fails a hard gate so it sorts below legal
ones in the log.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PY = "/usr/bin/python3.12"
PCB = "hardware/esp32-ir-remote.kicad_pcb"
PRISTINE = "/tmp/ar_pristine.kicad_pcb"
BEST = "/tmp/ar_best.kicad_pcb"
LOG = "hardware/fab/experiments.jsonl"
PENALTY = 1e6


def run(args, **kw):
    return subprocess.run(args, cwd=ROOT, capture_output=True, text=True, **kw)


def ensure_pristine():
    """Snapshot the committed (merged) board once as the per-experiment source."""
    if not os.path.exists(PRISTINE):
        r = run(["git", "show", "HEAD:hardware/esp32-ir-remote.kicad_pcb"])
        if r.returncode:
            sys.exit("cannot read HEAD board for pristine snapshot")
        open(PRISTINE, "w").write(r.stdout)


def _real_violations(d):
    """KiCad 10.0.4 added same-footprint NPTH hole checks that flag J2's
    vendored USB-C footprint against ITSELF (4x hole_clearance, NPTH posts vs
    its own GND pads). CI's pinned 10.0.2 reports 0 and the geometry is the
    part's own — filter them so they don't poison every candidate's score."""
    viol = []
    for v in d.get("violations", []):
        if (v.get("type") == "hole_clearance"
                and all("of J2" in it.get("description", "")
                        or it.get("description") == "NPTH pad of J2"
                        for it in v.get("items", []))):
            continue
        viol.append(v)
    return viol


def drc():
    out = "/tmp/ar_drc.json"
    run(["kicad-cli", "pcb", "drc", "--severity-error", "--exit-code-violations",
         "-o", out, "--format", "json", PCB])
    try:
        d = json.load(open(os.path.join(ROOT, out) if not os.path.isabs(out) else out))
        return len(_real_violations(d)), len(d.get("unconnected_items", []))
    except Exception:
        try:
            d = json.load(open(out))
            return len(_real_violations(d)), len(d.get("unconnected_items", []))
        except Exception:
            return 999, 999


# Parts that define zones and are positioned exactly by ANCHORS (treated as
# fixed obstacles during legalization). Everything else flexible is spiral-nudged
# off collisions toward its ANCHOR target (the open-centre peripherals + holes).
_FIXED_OBST = {"U3", "J2", "U1", "F1", "D1", "Q3", "D2", "D3", "D4", "D5", "J5"}
_FLEX = {"U4", "U5", "J4", "SW1", "SW2", "D6", "D7", "D10", "D11", "D12",
         "H1", "H2", "H3", "H4"}


def _legalize_flex(b, anchors=None):
    """Spiral-nudge each FLEX part to the nearest collision-free slot near its
    ANCHOR target, treating fixed parts + already-placed flex as obstacles.
    Reuses pcb_place_v2's courtyard/keepout helpers. `anchors` lets the caller
    pass overridden targets (else falls back to pcb_floorplan.ANCHORS) -- without
    this, an --anchors override of a FLEX part was placed then legalized straight
    back to its original target."""
    import math
    import pcbnew
    import pcb_floorplan as fp
    import pcb_place_v2 as pv
    base = anchors if anchors is not None else fp.ANCHORS
    targets = {**base, **{h: (x, y, 0) for h, (x, y) in fp.HOLES.items()}}
    fps = {f.GetReference(): f for f in b.GetFootprints()}
    placed = [pv.court_bbox(fps[r]) for r in _FIXED_OBST if r in fps]
    ko = pv.keepout_box(b)
    # big/structural first so they claim room before small LEDs
    order = ["U1", "U4", "U5", "J4", "SW1", "SW2", "H1", "H2", "H3", "H4",
             "D6", "D7", "D10", "D11", "D12"]
    for ref in [r for r in order if r in _FLEX and r in fps and r in targets]:
        f = fps[ref]
        tx, ty, _ = targets[ref]
        w, h = pv.court_wh(f)
        # holes report a tiny courtyard; give them an M3 head + extra clearance
        marg = pv.MARGIN + (0.8 if ref.startswith("H") else 0.0)
        best = None
        for R in [x * 0.25 for x in range(0, 200)]:
            steps = max(8, int(2 * math.pi * R / 0.25)) if R > 0 else 1
            for s in range(steps):
                th = 2 * math.pi * s / steps
                cx = round(tx + R * math.cos(th), 2)
                cy = round(ty + R * math.sin(th), 2)
                bb = (cx - w / 2 - marg, cy - h / 2 - marg,
                      cx + w / 2 + marg, cy + h / 2 + marg)
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


def _apply_floorplan(gpio_path, anchors_path="-"):
    """Subprocess stage: fresh pristine -> ANCHORS floorplan + legalize +
    outline (+ optional gpio remap). anchors_path overrides individual anchors
    (json {ref:[x,y,rot]}) so the search can sweep positions without editing
    pcb_floorplan."""
    import pcbnew
    sys.path.insert(0, HERE)
    import pcb_floorplan as fp
    anchors = dict(fp.ANCHORS)
    if anchors_path and anchors_path != "-":
        for ref, v in json.load(open(anchors_path)).items():
            anchors[ref] = tuple(v)
    shutil.copy(os.path.join(ROOT, PRISTINE) if not os.path.isabs(PRISTINE)
                else PRISTINE, os.path.join(ROOT, PCB))
    b = pcbnew.LoadBoard(PCB)
    fp.apply_anchors(b, anchors, fp.HOLES, draw_outline=False)
    # Drop the STALE board-level antenna keepout. It was drawn for the rot0
    # merged layout (x136-164, y69-81) and does NOT track U3 when the floorplan
    # moves the module -- in Layout B it strands on the N power chain (F1/U1/D1),
    # blocking power routing. U3's *footprint* keepout rotates+moves with the
    # module and already protects the antenna, so the board-level one is
    # redundant. (b.Zones() excludes footprint zones in KiCad 10.)
    removed = [z for z in b.Zones() if z.GetIsRuleArea()]
    for z in removed:
        b.Remove(z)
    pcbnew.SaveBoard(PCB, b)            # commit the removal, then reload clean
    b = pcbnew.LoadBoard(PCB)           # (b.Remove curses later .Pads() iteration)
    _legalize_flex(b, anchors)
    fp.set_outline(b)   # last: its b.Remove() curses .Pads()/.GetCourtyard()
    pcbnew.SaveBoard(PCB, b)
    # NB: GPIO remap runs as its OWN subprocess (see experiment()) -- doing it
    # in-process here corrupts the SWIG state after the repeated Load/Save above.


def _overlaps():
    """Subprocess stage: emit courtyard-overlap count as JSON."""
    import pcbnew
    b = pcbnew.LoadBoard(PCB)
    boxes = []
    for f in b.GetFootprints():
        if "Claude_Spark" in f.GetValue():   # back-silk logo graphic, not a part
            continue
        bb = f.GetCourtyard(pcbnew.F_CrtYd).BBox()
        if bb.GetWidth() == 0:
            bb = f.GetBoundingBox(False)   # text-free (see pcb_place_v2.court_wh)
        boxes.append((pcbnew.ToMM(bb.GetLeft()), pcbnew.ToMM(bb.GetTop()),
                      pcbnew.ToMM(bb.GetRight()), pcbnew.ToMM(bb.GetBottom())))
    n = 0
    for i in range(len(boxes)):
        a = boxes[i]
        for j in range(i + 1, len(boxes)):
            c = boxes[j]
            if not (a[2] <= c[0] or a[0] >= c[2] or a[3] <= c[1] or a[1] >= c[3]):
                n += 1
    print(json.dumps({"overlaps": n}))


def _score():
    """Subprocess stage: emit metrics + score as JSON."""
    sys.path.insert(0, HERE)
    import pcb_score
    m = pcb_score.metrics(PCB)
    print(json.dumps({"metrics": m, "score": pcb_score.score(m)}))


def experiment(tag, gpio_path, note, anchors_path=None):
    ensure_pristine()
    # 1. placement -- own process
    r = run([PY, __file__, "_apply", gpio_path or "-", anchors_path or "-"])
    if r.returncode:
        return _log(tag, PENALTY, dict(stage="apply", err=r.stderr[-300:]), gpio_path, note)
    # 1b. GPIO remap -- its own clean process (SWIG state, see _apply_floorplan)
    if gpio_path and gpio_path != "-":
        r = run([PY, os.path.join(HERE, "pcb_gpio_remap.py"), "apply", gpio_path])
        if r.returncode:
            return _log(tag, PENALTY, dict(stage="gpio", err=r.stderr[-300:]),
                        gpio_path, note)
    # 2. support re-seat
    r = run([PY, os.path.join(HERE, "pcb_place_v2.py")])
    if r.returncode:
        return _log(tag, PENALTY, dict(stage="place", err=r.stderr[-300:]), gpio_path, note)
    # 3. courtyard-overlap gate
    ov = run([PY, __file__, "_overlaps"])
    try:
        overlaps = json.loads(ov.stdout.strip().splitlines()[-1])["overlaps"]
    except Exception:
        overlaps = 999
    if overlaps:
        return _log(tag, PENALTY, dict(stage="overlap", overlaps=overlaps),
                    gpio_path, note)
    # 4. rip + route + pour
    run([PY, os.path.join(HERE, "pcb_rip.py")])
    for st in ("export", "route", "import"):
        run([PY, os.path.join(HERE, "pcb_route_fr.py"), st])
    run([PY, os.path.join(HERE, "pcb_pour.py")])
    run([PY, os.path.join(HERE, "pcb_ldo_pour.py")])   # U1 thermal pour (scored)
    # 5. DRC + score
    errs, unconn = drc()
    sc = run([PY, __file__, "_score"])
    try:
        res = json.loads(sc.stdout.strip().splitlines()[-1])
        m, score = res["metrics"], res["score"]
    except Exception:
        return _log(tag, PENALTY, dict(stage="score", err=sc.stdout[-300:]),
                    gpio_path, note)
    m.update(drc_err=errs, unrouted=unconn, overlaps=overlaps)
    if errs or unconn:
        score += PENALTY * 0.001 * (errs + unconn) + 5000.0
    return _log(tag, score, m, gpio_path, note)


def _log(tag, score, metrics, gpio_path, note):
    gpio = None
    if gpio_path and gpio_path != "-" and os.path.exists(gpio_path):
        gpio = json.load(open(gpio_path))
    row = dict(tag=tag, score=round(score, 1), metrics=metrics, gpio=gpio, note=note)
    os.makedirs(os.path.join(ROOT, "hardware/fab"), exist_ok=True)
    # ratchet: best-so-far must be read BEFORE appending this row — scanning
    # after the append includes the current score, so new_best could never fire
    legal = metrics.get("drc_err") == 0 and metrics.get("unrouted") == 0
    best_score = _best_score()
    with open(os.path.join(ROOT, LOG), "a") as f:
        f.write(json.dumps(row) + "\n")
    if legal and score < best_score:
        shutil.copy(os.path.join(ROOT, PCB), BEST)
        row["new_best"] = True
    print(json.dumps(row, indent=2))
    return row


def _best_score():
    if not os.path.exists(LOG):
        return PENALTY
    best = PENALTY
    for line in open(os.path.join(ROOT, LOG)):
        try:
            r = json.loads(line)
        except Exception:
            continue
        m = r.get("metrics", {})
        if m.get("drc_err") == 0 and m.get("unrouted") == 0:
            best = min(best, r["score"])
    return best


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "_apply":
        _apply_floorplan(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "-")
    elif len(sys.argv) > 1 and sys.argv[1] == "_overlaps":
        _overlaps()
    elif len(sys.argv) > 1 and sys.argv[1] == "_score":
        _score()
    else:
        ap = argparse.ArgumentParser()
        ap.add_argument("--tag", required=True)
        ap.add_argument("--gpio", default=None)
        ap.add_argument("--anchors", default=None)
        ap.add_argument("--note", default="")
        a = ap.parse_args()
        experiment(a.tag, a.gpio, a.note, a.anchors)
