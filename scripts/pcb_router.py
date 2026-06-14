#!/usr/bin/env python3
"""Grid autorouter for esp32-ir-remote.kicad_pcb.

Deterministic A* router over a 0.2mm grid, 2 layers (F.Cu / B.Cu).
GND is NOT routed here - it is handled by dual-layer pours + stitching
(scripts/pcb_pour.py). Validation is `kicad-cli pcb drc` afterwards;
this script only proposes copper.

Run with the kicad-mcp-server venv python (numpy + pcbnew):
  tools/kicad-mcp-server/.venv/bin/python3 scripts/pcb_router.py
"""
import heapq
import math
import sys

import numpy as np
import pcbnew

BOARD_PATH = "hardware/esp32-ir-remote.kicad_pcb"
GRID = 0.1  # mm
X0, Y0, X1, Y1 = 100.0, 60.0, 180.0, 115.0
NX = int(round((X1 - X0) / GRID)) + 1
NY = int(round((Y1 - Y0) / GRID)) + 1
CLEAR = 0.128        # working clearance, just above JLCPCB 0.127 floor
EDGE_MARGIN = 0.45   # copper-to-edge (board rule 0.3 + margin)
ANTENNA_X = 104.6    # no copper west of this (WROOM antenna strip)
F, B = 0, 1

POWER_NETS = {"+5V", "+3.3V", "Net-(U1-SW)", "Net-(F1-Pad2)"}
IR_NETS = {"IR_DRAIN", "EXT_IR_A", "/EXT_IR_A", "Net-(D2-A)", "Net-(D3-A)",
           "Net-(D4-A)", "Net-(D5-A)"}

def net_widths(name):
    """(track half-width, via diameter, via drill) in mm."""
    if name in POWER_NETS:
        return 0.30, 0.6, 0.3
    if name in IR_NETS or name.lstrip("/") in {n.lstrip("/") for n in IR_NETS}:
        return 0.25, 0.6, 0.3
    return 0.125, 0.5, 0.3

# short, position-locked local families first; long flexible transit last
ROUTE_ORDER_HEAD = [
    "Net-(U1-SW)", "Net-(U1-BST)",
    "Net-(Q1-B)", "Net-(Q2-B)", "Net-(Q1-E)", "Net-(Q2-E)",
    "Net-(U2-~{DTR})", "Net-(U2-~{RTS})",
    "Net-(Q3-G)", "Net-(D10-A)",
    "Net-(D11-K)", "Net-(D11-A)", "Net-(D12-K)", "Net-(D12-A)",
    "Net-(D6-A)", "Net-(D7-A)", "Net-(D8-A)", "Net-(D9-A)",
    "Net-(J2-CC1)", "Net-(J2-CC2)", "Net-(JP1-B)", "IR_RX_VS",
    "Net-(D2-A)", "Net-(D3-A)", "Net-(D4-A)", "Net-(D5-A)", "EXT_IR_A",
    "USB_D-", "USB_D+", "Net-(F1-Pad2)", "+5V", "IR_DRAIN",
    "ESP_EN",
]
ROUTE_ORDER_TAIL = ["+3.3V"]

def mm2c(x, y):
    return int(round((x - X0) / GRID)), int(round((y - Y0) / GRID))

def c2mm(i, j):
    return X0 + i * GRID, Y0 + j * GRID

def cells_dilate(mask, r_mm):
    r = int(math.ceil(r_mm / GRID))
    if r <= 0:
        return mask.copy()
    out = mask.copy()
    for di in range(-r, r + 1):
        for dj in range(-r, r + 1):
            if di * di + dj * dj > r * r or (di == 0 and dj == 0):
                continue
            sh = np.zeros_like(mask)
            si = slice(max(di, 0), NX + min(di, 0))
            sj = slice(max(dj, 0), NY + min(dj, 0))
            ti = slice(max(-di, 0), NX + min(-di, 0))
            tj = slice(max(-dj, 0), NY + min(-dj, 0))
            sh[si, sj] = mask[ti, tj]
            out |= sh
    return out


def main():
    board = pcbnew.LoadBoard(BOARD_PATH)
    assert isinstance(board, pcbnew.BOARD), "LoadBoard failed"

    # --- static blocks -------------------------------------------------
    static = np.zeros((2, NX, NY), dtype=bool)
    em = int(math.ceil(EDGE_MARGIN / GRID))
    static[:, :em, :] = True
    static[:, NX - em:, :] = True
    static[:, :, :em] = True
    static[:, :, NY - em:] = True
    ax = int(math.ceil((ANTENNA_X - X0) / GRID))
    ay = int(math.ceil((102.3 - Y0) / GRID))
    static[:, :ax, :ay] = True

    # --- copper model from pads ----------------------------------------
    occ = np.zeros((2, NX, NY), dtype=bool)
    owner = np.full((2, NX, NY), -1, dtype=np.int32)
    pad_cells = {}   # (netcode) -> list of (layer, i, j) per pad: pads[netcode] = [ [cells...] , ...]
    net_pads = {}    # netcode -> list of pad cell-lists
    net_names = {}

    for fp in board.GetFootprints():
        for pad in fp.Pads():
            nc = pad.GetNetCode()
            bb = pad.GetBoundingBox()
            x0p, y0p = pcbnew.ToMM(bb.GetLeft()), pcbnew.ToMM(bb.GetTop())
            x1p, y1p = pcbnew.ToMM(bb.GetRight()), pcbnew.ToMM(bb.GetBottom())
            i0, j0 = mm2c(x0p, y0p)
            i1, j1 = mm2c(x1p, y1p)
            i0, j0 = max(i0, 0), max(j0, 0)
            i1, j1 = min(i1, NX - 1), min(j1, NY - 1)
            tht = pad.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH)
            on_f = tht or pad.IsOnLayer(pcbnew.F_Cu)
            on_b = tht or pad.IsOnLayer(pcbnew.B_Cu)
            layers = [l for l, on in ((F, on_f), (B, on_b)) if on]
            cells = []        # full bbox cells (occupancy / clearance)
            hit_cells = []    # cells whose centre is actually inside the pad
            for L in layers:
                occ[L, i0:i1 + 1, j0:j1 + 1] = True
                if nc > 0:
                    owner[L, i0:i1 + 1, j0:j1 + 1] = nc
                for i in range(i0, i1 + 1):
                    for j in range(j0, j1 + 1):
                        cells.append((L, i, j))
                        cx, cy = c2mm(i, j)
                        if pad.HitTest(pcbnew.VECTOR2I(pcbnew.FromMM(cx),
                                                       pcbnew.FromMM(cy))):
                            hit_cells.append((L, i, j))
            if nc > 0:
                # route TO cells genuinely inside the pad shape, not bbox
                # corners (which sit outside round/oval pads -> the path lands a
                # cell shy and the pad reads unconnected). Fall back to bbox for
                # pads smaller than the grid.
                tcells = hit_cells if hit_cells else cells
                net_pads.setdefault(nc, []).append(
                    (fp.GetReference() + "/" + pad.GetNumber(), tcells))
                net_names[nc] = pad.GetNetname()

    gnd_code = board.FindNet("GND").GetNetCode()

    # existing copper (seed stubs, previous routing) joins the model
    net_seed_cells = {}
    for t in board.GetTracks():
        nc = t.GetNetCode()
        if nc <= 0:
            continue
        if isinstance(t, pcbnew.PCB_VIA):
            x, y = pcbnew.ToMM(t.GetPosition().x), pcbnew.ToMM(t.GetPosition().y)
            r = pcbnew.ToMM(t.GetWidth()) / 2
            i0, j0 = mm2c(x - r, y - r); i1, j1 = mm2c(x + r, y + r)
            layers = (F, B)
        else:
            xs, ys = t.GetStart(), t.GetEnd()
            r = pcbnew.ToMM(t.GetWidth()) / 2
            x0t, x1t = sorted((pcbnew.ToMM(xs.x), pcbnew.ToMM(ys.x)))
            y0t, y1t = sorted((pcbnew.ToMM(xs.y), pcbnew.ToMM(ys.y)))
            i0, j0 = mm2c(x0t - r, y0t - r); i1, j1 = mm2c(x1t + r, y1t + r)
            layers = (F,) if t.GetLayer() == pcbnew.F_Cu else (B,)
            # NB: diagonal segments rasterized as bbox - conservative obstacle,
            # generous own-net seed; acceptable for short seeds
        i0, j0 = max(i0, 0), max(j0, 0); i1, j1 = min(i1, NX - 1), min(j1, NY - 1)
        for L in layers:
            occ[L, i0:i1 + 1, j0:j1 + 1] = True
            owner[L, i0:i1 + 1, j0:j1 + 1] = nc
        # seeds (connectivity) must be EXACT, not bbox: sample along segment
        if isinstance(t, pcbnew.PCB_VIA):
            for L in layers:
                for i in range(i0, i1 + 1):
                    for j in range(j0, j1 + 1):
                        net_seed_cells.setdefault(nc, set()).add((L, i, j))
        else:
            sx, sy = pcbnew.ToMM(xs.x), pcbnew.ToMM(xs.y)
            ex2, ey2 = pcbnew.ToMM(ys.x), pcbnew.ToMM(ys.y)
            length = math.hypot(ex2 - sx, ey2 - sy)
            steps = max(1, int(length / (GRID * 0.5)))
            rc = int(math.ceil(r / GRID))
            for sN in range(steps + 1):
                cx = sx + (ex2 - sx) * sN / steps
                cy = sy + (ey2 - sy) * sN / steps
                ci, cj = mm2c(cx, cy)
                for di in range(-rc, rc + 1):
                    for dj in range(-rc, rc + 1):
                        ii, jj = ci + di, cj + dj
                        if 0 <= ii < NX and 0 <= jj < NY:
                            for L in layers:
                                net_seed_cells.setdefault(nc, set()).add((L, ii, jj))

    # --- route order ----------------------------------------------------
    code_by_name = {v: k for k, v in net_names.items()}
    ordered = []
    for nm in ROUTE_ORDER_HEAD:
        for cand in (nm, "/" + nm):
            if cand in code_by_name:
                ordered.append(code_by_name[cand])
                break
    tail = []
    for nm in ROUTE_ORDER_TAIL:
        for cand in (nm, "/" + nm):
            if cand in code_by_name:
                tail.append(code_by_name[cand])
                break
    en_code = code_by_name.get("ESP_EN") or code_by_name.get("/ESP_EN")
    if en_code: tail.append(en_code)
    u3_nets, rest = [], []
    for nc, pads in net_pads.items():
        if nc == gnd_code or nc in ordered or nc in tail or len(pads) < 2:
            continue
        u3p = [p for ref, p in pads if ref.startswith("U3/")]
        if u3p:
            cx = sum(c[1] for c in u3p[0]) / len(u3p[0])
            cy = sum(c[2] for c in u3p[0]) / len(u3p[0])
            u3_nets.append(((cy, cx), nc))   # north row (small y) first, then west->east
        else:
            xs = [c[1] for _, p in pads for c in p]
            ys = [c[2] for _, p in pads for c in p]
            rest.append(((max(xs) - min(xs)) + (max(ys) - min(ys)), nc))
    u3_nets.sort(); rest.sort()
    ordered += [nc for _, nc in u3_nets] + [nc for _, nc in rest] + tail

    tracks_out = []   # (netcode, layer, x0,y0,x1,y1, width)
    vias_out = []     # (netcode, x, y, dia, drill)
    unrouted = []

    # F.Cu penalty regions: [x0,y0,x1,y1,penalty] - corridors stay clear for
    # perpendicular escapes; east-west bus traffic prefers B.Cu there
    REGION = np.zeros((2, NX, NY), dtype=np.float32)
    for rx0, ry0, rx1, ry1, pen in ((105, 60.5, 162, 71.5, 1.2),
                                    (123.5, 71.5, 137, 96.0, 0.5),
                                    (125, 83, 145, 90, 0.9)):
        i0, j0 = mm2c(rx0, ry0); i1, j1 = mm2c(rx1, ry1)
        REGION[F, max(i0,0):min(i1,NX), max(j0,0):min(j1,NY)] = pen

    SQRT2 = math.sqrt(2)
    DIRS = [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
            (1, 1, SQRT2), (1, -1, SQRT2), (-1, 1, SQRT2), (-1, -1, SQRT2)]
    VIA_COST = 8.0

    for nc in ordered:
        name = net_names[nc]
        pads = net_pads[nc]
        hw, via_d, via_drill = net_widths(name)
        if name in POWER_NETS:
            LAYER_PENALTY = {F: 0.30, B: 0.0}   # power distributes on B
        else:
            LAYER_PENALTY = {F: 0.0, B: 0.0}   # signals may use B freely

        def build_masks(hw_):
            foreign = occ & (owner != nc)
            blocked = np.zeros((2, NX, NY), dtype=bool)
            viabad = np.zeros((NX, NY), dtype=bool)
            for L in (F, B):
                blocked[L] = cells_dilate(foreign[L], hw_ + CLEAR) | static[L]
            vb = cells_dilate(foreign[F], via_d / 2 + CLEAR) | \
                 cells_dilate(foreign[B], via_d / 2 + CLEAR) | static[F] | static[B]
            # own pads always enterable
            for _, cells in pads:
                for (L, i, j) in cells:
                    blocked[L, i, j] = False
            return blocked, vb

        blocked, viabad = build_masks(hw)

        # connect pads greedily: blob starts at pad 0
        blob = set(net_pads[nc][0][1]) | net_seed_cells.get(nc, set())
        remaining = list(range(1, len(pads)))
        # order remaining by distance to pad0 centroid
        def centroid(cells):
            return (sum(c[1] for c in cells) / len(cells),
                    sum(c[2] for c in cells) / len(cells))
        c0 = centroid(pads[0][1])
        remaining.sort(key=lambda k: abs(centroid(pads[k][1])[0] - c0[0]) +
                                     abs(centroid(pads[k][1])[1] - c0[1]))

        for k in remaining:
            padref = pads[k][0]
            target = set(pads[k][1])
            if target & blob:
                blob |= target
                continue
            tcx = sum(c[1] for c in target) / len(target)
            tcy = sum(c[2] for c in target) / len(target)

            def astar(blocked_, viabad_):
                dist = {}
                prev = {}
                h = []
                for (L, i, j) in blob:
                    dist[(L, i, j)] = 0.0
                    heapq.heappush(h, (abs(i - tcx) + abs(j - tcy), 0.0, (L, i, j)))
                seen = set()
                while h:
                    _, d, node = heapq.heappop(h)
                    if node in seen:
                        continue
                    seen.add(node)
                    if node in target:
                        return node, prev
                    L, i, j = node
                    for di, dj, c in DIRS:
                        ni, nj = i + di, j + dj
                        if not (0 <= ni < NX and 0 <= nj < NY):
                            continue
                        nn = (L, ni, nj)
                        if nn in seen or blocked_[L, ni, nj]:
                            continue
                        ncost = d + c + LAYER_PENALTY[L] * c + REGION[L, ni, nj] * c
                        if ncost < dist.get(nn, 1e18):
                            dist[nn] = ncost
                            prev[nn] = node
                            heapq.heappush(h, (ncost + abs(ni - tcx) + abs(nj - tcy), ncost, nn))
                    # layer change
                    oL = 1 - L
                    nn = (oL, i, j)
                    if nn not in seen and not viabad_[i, j] and not blocked_[oL, i, j]:
                        ncost = d + VIA_COST
                        if ncost < dist.get(nn, 1e18):
                            dist[nn] = ncost
                            prev[nn] = node
                            heapq.heappush(h, (ncost + abs(i - tcx) + abs(j - tcy), ncost, nn))
                return None, None

            goal, prev = astar(blocked, viabad)
            used_hw = hw
            if goal is None and hw > 0.26:
                nb, nv = build_masks(0.25)
                goal, prev = astar(nb, nv)
                used_hw = 0.25
                if goal is not None:
                    print(f"  [{name}] leg to {padref}: neckdown 0.5mm")
            if goal is None and hw > 0.13:
                nb, nv = build_masks(0.125)
                goal, prev = astar(nb, nv)
                used_hw = 0.125
                if goal is not None:
                    print(f"  [{name}] leg to {padref}: neckdown 0.25mm")
            if goal is None:
                unrouted.append((name, padref))
                print(f"  [{name}] leg to {padref}: UNROUTED")
                continue

            # reconstruct
            path = [goal]
            while path[-1] in prev:
                path.append(prev[path[-1]])
            path.reverse()

            # emit segments + vias; mark copper
            def emit(path_, hw_):
                segs = []
                s = path_[0]
                for a, b in zip(path_, path_[1:]):
                    if a[0] != b[0]:
                        if s != a:
                            segs.append((s, a))
                        x, y = c2mm(a[1], a[2])
                        vias_out.append((nc, x, y, via_d, via_drill))
                        s = b
                    else:
                        # direction change?
                        pass
                # collapse collinear runs per layer
                out = []
                run = [path_[0]]
                for a, b in zip(path_, path_[1:]):
                    if a[0] != b[0]:
                        out.append(run)
                        run = [b]
                    else:
                        run.append(b)
                out.append(run)
                for run_ in out:
                    if len(run_) < 2:
                        continue
                    L = run_[0][0]
                    corner = [run_[0]]
                    for p0, p1, p2 in zip(run_, run_[1:], run_[2:]):
                        d1 = (p1[1] - p0[1], p1[2] - p0[2])
                        d2 = (p2[1] - p1[1], p2[2] - p1[2])
                        if d1 != d2:
                            corner.append(p1)
                    corner.append(run_[-1])
                    for a, b in zip(corner, corner[1:]):
                        xa, ya = c2mm(a[1], a[2])
                        xb, yb = c2mm(b[1], b[2])
                        tracks_out.append((nc, L, xa, ya, xb, yb, used_hw * 2))
                # mark copper cells
                r = int(math.ceil(hw_ / GRID))
                for (L, i, j) in path_:
                    i0m, i1m = max(i - r, 0), min(i + r, NX - 1)
                    j0m, j1m = max(j - r, 0), min(j + r, NY - 1)
                    occ[L, i0m:i1m + 1, j0m:j1m + 1] = True
                    owner[L, i0m:i1m + 1, j0m:j1m + 1] = nc

            emit(path, used_hw)
            blob |= set(path)
            blob |= target
            # masks must absorb new copper of own net (it's owner==nc: not foreign) - no rebuild needed

        print(f"routed {name}: {len(pads)} pads")

    # --- write to board --------------------------------------------------
    for nc, L, xa, ya, xb, yb, w in tracks_out:
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(xa), pcbnew.FromMM(ya)))
        t.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(xb), pcbnew.FromMM(yb)))
        t.SetLayer(pcbnew.F_Cu if L == F else pcbnew.B_Cu)
        t.SetWidth(pcbnew.FromMM(w))
        t.SetNetCode(nc)
        board.Add(t)
    for nc, x, y, dia, drill in vias_out:
        v = pcbnew.PCB_VIA(board)
        v.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
        v.SetWidth(pcbnew.FromMM(dia))
        v.SetDrill(pcbnew.FromMM(drill))
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        v.SetNetCode(nc)
        board.Add(v)

    print(f"\ntracks: {len(tracks_out)}, vias: {len(vias_out)}, unrouted legs: {len(unrouted)}")
    for u in unrouted:
        print("  UNROUTED:", u)
    pcbnew.SaveBoard(BOARD_PATH, board)
    print("saved")
    return 0 if not unrouted else 1


if __name__ == "__main__":
    sys.exit(main())
