#!/usr/bin/env python3
"""Connectivity finisher: route remaining split nets with bounded rip-up.

Finds nets whose copper (pads+tracks+vias) forms >1 connected component,
routes the gaps; when A* fails, retries with one candidate blocker net's
tracks ignored, rips the conflicting segments, and re-heals that net.

Run: tools/kicad-mcp-server/.venv/bin/python3 scripts/pcb_finish.py
"""
import heapq
import math
import sys
from collections import defaultdict, deque

import numpy as np
import pcbnew

BOARD_PATH = "hardware/esp32-ir-remote.kicad_pcb"
GRID = 0.1
X0, Y0, X1, Y1 = 100.0, 60.0, 180.0, 115.0
NX = int(round((X1 - X0) / GRID)) + 1
NY = int(round((Y1 - Y0) / GRID)) + 1
CLEAR = 0.131
EDGE_MARGIN = 0.45
ANTENNA_X, ANTENNA_Y = 104.6, 102.3
F, B = 0, 1
VIA_COST = 14.0
POWER = {"+5V", "+3.3V", "Net-(U1-SW)", "Net-(F1-Pad2)"}
IRN = {"IR_DRAIN", "EXT_IR_A", "Net-(D2-A)", "Net-(D3-A)", "Net-(D4-A)", "Net-(D5-A)"}

def widths(name):
    n = name.lstrip("/")
    if n in POWER: return 0.30, 0.8, 0.4
    if n in IRN: return 0.25, 0.8, 0.4
    return 0.125, 0.6, 0.3

def mm2c(x, y): return int(round((x - X0) / GRID)), int(round((y - Y0) / GRID))
def c2mm(i, j): return X0 + i * GRID, Y0 + j * GRID

def dilate(mask, r_mm):
    r = int(math.ceil(r_mm / GRID))
    if r <= 0: return mask.copy()
    out = mask.copy()
    for di in range(-r, r + 1):
        for dj in range(-r, r + 1):
            if di*di + dj*dj > r*r or (di == 0 and dj == 0): continue
            sh = np.zeros_like(mask)
            sh[max(di,0):NX+min(di,0), max(dj,0):NY+min(dj,0)] = \
                mask[max(-di,0):NX+min(-di,0), max(-dj,0):NY+min(-dj,0)]
            out |= sh
    return out

board = pcbnew.LoadBoard(BOARD_PATH)
assert isinstance(board, pcbnew.BOARD)

static = np.zeros((2, NX, NY), dtype=bool)
em = int(math.ceil(EDGE_MARGIN / GRID))
static[:, :em, :] = True; static[:, NX-em:, :] = True
static[:, :, :em] = True; static[:, :, NY-em:] = True
ax = int(math.ceil((ANTENNA_X - X0) / GRID)); ay = int(math.ceil((ANTENNA_Y - Y0) / GRID))
static[:, :ax, :ay] = True

def seg_cells(x0, y0, x1, y1, r):
    """cells covered by a segment of half-width r (proper sampling)."""
    length = math.hypot(x1-x0, y1-y0)
    steps = max(1, int(length / (GRID*0.5)))
    rc = int(math.ceil(r / GRID))
    out = set()
    for s in range(steps+1):
        x = x0 + (x1-x0)*s/steps; y = y0 + (y1-y0)*s/steps
        ci, cj = mm2c(x, y)
        for di in range(-rc, rc+1):
            for dj in range(-rc, rc+1):
                i, j = ci+di, cj+dj
                if 0 <= i < NX and 0 <= j < NY:
                    out.add((i, j))
    return out

def build_model(skip_tracks_of=None):
    occ = np.zeros((2, NX, NY), dtype=bool)
    owner = np.full((2, NX, NY), -1, dtype=np.int32)
    net_cells = defaultdict(set)   # nc -> {(L,i,j)}
    hop_cells = defaultdict(set)   # nc -> {(i,j)} via/THT layer hops
    net_pads = defaultdict(list)
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            nc = pad.GetNetCode()
            bb = pad.GetBoundingBox()
            i0, j0 = mm2c(pcbnew.ToMM(bb.GetLeft()), pcbnew.ToMM(bb.GetTop()))
            i1, j1 = mm2c(pcbnew.ToMM(bb.GetRight()), pcbnew.ToMM(bb.GetBottom()))
            i0, j0 = max(i0,0), max(j0,0); i1, j1 = min(i1,NX-1), min(j1,NY-1)
            tht = pad.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH)
            Ls = (F, B) if tht else tuple(
                l for l, on in ((F, pad.IsOnLayer(pcbnew.F_Cu)), (B, pad.IsOnLayer(pcbnew.B_Cu))) if on)
            cells = []
            for L in Ls:
                occ[L, i0:i1+1, j0:j1+1] = True
                if nc > 0: owner[L, i0:i1+1, j0:j1+1] = nc
                for i in range(i0, i1+1):
                    for j in range(j0, j1+1):
                        cells.append((L, i, j))
                        if nc > 0: net_cells[nc].add((L, i, j))
            if nc > 0 and tht:
                for i in range(i0, i1+1):
                    for j in range(j0, j1+1):
                        hop_cells[nc].add((i, j))
            if nc > 0:
                net_pads[nc].append((fp.GetReference()+"/"+pad.GetNumber(), cells))
    for t in board.GetTracks():
        nc = t.GetNetCode()
        if nc <= 0: continue
        if skip_tracks_of and nc == skip_tracks_of and not isinstance(t, pcbnew.PCB_VIA):
            continue
        if isinstance(t, pcbnew.PCB_VIA):
            x, y = pcbnew.ToMM(t.GetPosition().x), pcbnew.ToMM(t.GetPosition().y)
            r = pcbnew.ToMM(t.GetWidth())/2
            cs = seg_cells(x, y, x, y, r)
            for (i, j) in cs:
                for L in (F, B):
                    occ[L, i, j] = True; owner[L, i, j] = nc
                    net_cells[nc].add((L, i, j))
                hop_cells[nc].add((i, j))
        else:
            s, e = t.GetStart(), t.GetEnd()
            r = pcbnew.ToMM(t.GetWidth())/2
            L = F if t.GetLayer() == pcbnew.F_Cu else B
            cs = seg_cells(pcbnew.ToMM(s.x), pcbnew.ToMM(s.y), pcbnew.ToMM(e.x), pcbnew.ToMM(e.y), r)
            for (i, j) in cs:
                occ[L, i, j] = True; owner[L, i, j] = nc
                net_cells[nc].add((L, i, j))
    return occ, owner, net_cells, hop_cells, net_pads

def components(nc, net_cells, hop_cells):
    cells = net_cells[nc]
    hops = hop_cells[nc]
    seen = set()
    comps = []
    for c in cells:
        if c in seen: continue
        comp = set([c]); dq = deque([c]); seen.add(c)
        while dq:
            L, i, j = dq.popleft()
            for di, dj in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)):
                n = (L, i+di, j+dj)
                if n in cells and n not in seen:
                    seen.add(n); comp.add(n); dq.append(n)
            if (i, j) in hops:
                n = (1-L, i, j)
                if n in cells and n not in seen:
                    seen.add(n); comp.add(n); dq.append(n)
        comps.append(comp)
    return comps

DIRS = [(1,0,1.0),(-1,0,1.0),(0,1,1.0),(0,-1,1.0),
        (1,1,1.41421),(1,-1,1.41421),(-1,1,1.41421),(-1,-1,1.41421)]

def astar(blocked, viabad, sources, targets):
    tc = list(targets)[0]
    tcx = sum(c[1] for c in targets)/len(targets)
    tcy = sum(c[2] for c in targets)/len(targets)
    dist = {}; prev = {}; h = []
    for c in sources:
        dist[c] = 0.0
        heapq.heappush(h, (abs(c[1]-tcx)+abs(c[2]-tcy), 0.0, c))
    seen = set()
    while h:
        _, d, node = heapq.heappop(h)
        if node in seen: continue
        seen.add(node)
        if node in targets: return node, prev
        L, i, j = node
        for di, dj, c in DIRS:
            ni, nj = i+di, j+dj
            if not (0 <= ni < NX and 0 <= nj < NY): continue
            nn = (L, ni, nj)
            if nn in seen or blocked[L, ni, nj]: continue
            nd = d + c
            if nd < dist.get(nn, 1e18):
                dist[nn] = nd; prev[nn] = node
                heapq.heappush(h, (nd+abs(ni-tcx)+abs(nj-tcy), nd, nn))
        nn = (1-L, i, j)
        if nn not in seen and not viabad[i, j] and not blocked[1-L, i, j]:
            nd = d + VIA_COST
            if nd < dist.get(nn, 1e18):
                dist[nn] = nd; prev[nn] = node
                heapq.heappush(h, (nd+abs(i-tcx)+abs(j-tcy), nd, nn))
    return None, None

def masks_for(nc, name, occ, owner, net_pads, hw=None):
    hw_, via_d, _ = widths(name)
    if hw is not None: hw_ = hw
    foreign = occ & (owner != nc)
    blocked = np.zeros((2, NX, NY), dtype=bool)
    for L in (F, B):
        blocked[L] = dilate(foreign[L], hw_ + CLEAR) | static[L]
    viabad = dilate(foreign[F], via_d/2 + CLEAR) | dilate(foreign[B], via_d/2 + CLEAR) | static[F] | static[B]
    for _, cells in net_pads[nc]:
        for (L, i, j) in cells: blocked[L, i, j] = False
    return blocked, viabad, hw_

def emit_path(path, nc, hw, via_d, via_drill):
    new = []
    runs = []
    run = [path[0]]
    for a, b in zip(path, path[1:]):
        if a[0] != b[0]:
            x, y = c2mm(a[1], a[2])
            v = pcbnew.PCB_VIA(board)
            v.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
            v.SetWidth(pcbnew.FromMM(via_d)); v.SetDrill(pcbnew.FromMM(via_drill))
            v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); v.SetNetCode(nc)
            board.Add(v); new.append(v)
            runs.append(run); run = [b]
        else:
            run.append(b)
    runs.append(run)
    for r_ in runs:
        if len(r_) < 2: continue
        L = r_[0][0]
        corner = [r_[0]]
        for p0, p1, p2 in zip(r_, r_[1:], r_[2:]):
            if (p1[1]-p0[1], p1[2]-p0[2]) != (p2[1]-p1[1], p2[2]-p1[2]):
                corner.append(p1)
        corner.append(r_[-1])
        for a, b in zip(corner, corner[1:]):
            xa, ya = c2mm(a[1], a[2]); xb, yb = c2mm(b[1], b[2])
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(xa), pcbnew.FromMM(ya)))
            t.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(xb), pcbnew.FromMM(yb)))
            t.SetLayer(pcbnew.F_Cu if L == F else pcbnew.B_Cu)
            t.SetWidth(pcbnew.FromMM(hw*2)); t.SetNetCode(nc)
            board.Add(t); new.append(t)
    return new

names = {}
for n in board.GetNetsByNetcode().values() if hasattr(board, "GetNetsByNetcode") else []:
    pass
# build name map from pads
for fp in board.GetFootprints():
    for p in fp.Pads():
        if p.GetNetCode() > 0:
            names[p.GetNetCode()] = p.GetNetname()

import os
ONLY = set(os.environ.get("NETS", "").split(",")) - {""}
ALLOW_RIP = os.environ.get("RIPUP", "1") == "1"
MAX_ROUNDS = int(os.environ.get("ROUNDS", "40"))
rip_history = set()
for rnd in range(MAX_ROUNDS):
    occ, owner, net_cells, hop_cells, net_pads = build_model()
    track_snapshot = [t for t in board.GetTracks()]
    removed_ids = set()
    gnd = board.FindNet("GND").GetNetCode()
    split = []
    for nc in net_pads:
        if nc == gnd: continue
        if ONLY and names.get(nc, "").lstrip("/") not in ONLY: continue
        comps = components(nc, net_cells, hop_cells)
        if len(comps) > 1:
            comps.sort(key=len, reverse=True)
            split.append((nc, comps))
    if not split:
        print(f"round {rnd}: ALL NETS CONNECTED")
        break
    print(f"round {rnd}: {len(split)} split nets: {[names[nc] for nc, _ in split]}")
    progress = False
    restart = False
    for nc, comps in split:
        if restart: break
        name = names[nc]
        hwd, via_d, via_drill = widths(name)
        blocked, viabad, hw = masks_for(nc, name, occ, owner, net_pads)
        main_c = comps[0]
        for other in comps[1:]:
            goal, prev = astar(blocked, viabad, main_c, other)
            used_hw = hw
            if goal is None and hw > 0.13:
                b2, v2, _ = masks_for(nc, name, occ, owner, net_pads, hw=0.125)
                goal, prev = astar(b2, v2, other, main_c)
                used_hw = 0.125
            if goal is None and not ALLOW_RIP:
                print(f"  [{name}] SPLIT REMAINS (rip-up disabled)")
                continue
            if goal is None:
                # bounded rip-up: try ignoring one candidate net's tracks
                bbx = [c[1] for c in main_c | other]; bby = [c[2] for c in main_c | other]
                cand = set()
                m = int(4.0 / GRID)
                for L in (F, B):
                    sub = owner[L, max(min(bbx)-m,0):min(max(bbx)+m,NX), max(min(bby)-m,0):min(max(bby)+m,NY)]
                    cand |= set(np.unique(sub).tolist())
                cand -= {-1, nc, gnd}
                done = False
                for x in sorted(cand, key=lambda c: len(net_cells.get(c, ()))):
                    if (nc, x) in rip_history or (x, nc) in rip_history:
                        continue
                    occ2, owner2, ncl2, hc2, npd2 = build_model(skip_tracks_of=x)
                    b3 = np.zeros((2, NX, NY), dtype=bool)
                    foreign = occ2 & (owner2 != nc)
                    for L in (F, B):
                        b3[L] = dilate(foreign[L], 0.125 + CLEAR) | static[L]
                    v3 = dilate(foreign[F], via_d/2+CLEAR) | dilate(foreign[B], via_d/2+CLEAR) | static[F] | static[B]
                    for _, cells in npd2[nc]:
                        for (L, i, j) in cells: b3[L, i, j] = False
                    goal, prev = astar(b3, v3, main_c, other)
                    if goal is None: continue
                    # rip conflicting segments of net x along path
                    path = [goal]
                    while path[-1] in prev: path.append(prev[path[-1]])
                    path.reverse()
                    pc = {(i, j) for L, i, j in path}
                    ripped = []
                    for t in track_snapshot:
                        if id(t) in removed_ids: continue
                        if t.GetNetCode() != x or isinstance(t, pcbnew.PCB_VIA): continue
                        s, e = t.GetStart(), t.GetEnd()
                        cells = seg_cells(pcbnew.ToMM(s.x), pcbnew.ToMM(s.y),
                                          pcbnew.ToMM(e.x), pcbnew.ToMM(e.y),
                                          pcbnew.ToMM(t.GetWidth())/2 + 0.125 + CLEAR)
                        if cells & pc:
                            board.Remove(t); removed_ids.add(id(t)); ripped.append(t)
                    emit_path(path, nc, 0.125, via_d, via_drill)
                    rip_history.add((nc, x))
                    print(f"  [{name}] healed via rip of {names.get(x,'?')} ({len(ripped)} segs)")
                    progress = True; done = True
                    restart = True
                    break
                if not done:
                    print(f"  [{name}] STILL SPLIT (no single-net rip works)")
                continue
            path = [goal]
            while path[-1] in prev: path.append(prev[path[-1]])
            path.reverse()
            emit_path(path, nc, used_hw, via_d, via_drill)
            print(f"  [{name}] joined ({len(path)} cells, hw {used_hw})")
            progress = True
            restart = True
            break
    pcbnew.SaveBoard(BOARD_PATH, board)
    print(f"  (round {rnd} state saved)")
    if not progress:
        print("no progress; stopping")
        break

pcbnew.SaveBoard(BOARD_PATH, board)
print("saved")
