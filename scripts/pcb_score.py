#!/usr/bin/env python3
"""Objective quality score for a *routed* board — the oracle for pcb_search.py.

Given a board that has been placed + routed (FreeRouting import done) + poured,
extract a vector of layout-quality metrics and fold them into a single scalar
(LOWER = better). This is the fitness function the generative floorplan search
ranks candidates by; FreeRouting (routability) + kicad-cli DRC (legality) are
the hard gates the *driver* applies before scoring — a board that doesn't route
0-unrouted or fails DRC never reaches here (or is scored with PENALTY).

Metrics (all from pcbnew on the live board, deterministic):
  usb_bcu_mm   B.Cu length of the USB pair      -> 0 wanted (F.Cu over GND)
  usb_vias     vias on the USB pair             -> 0 wanted (no layer hop)
  bcu_sig_mm   non-GND track length on B.Cu     -> low (B.Cu is the GND ref
                                                  plane; every signal there is
                                                  a slot the return must detour)
  track_mm     total routed track length        -> low (shorter = less coupling)
  vias         total via count                  -> low
  decap_mm     sum bypass/RC -> served-pin dist -> low (tight decoupling)
  sens_mm      U5 sensor dist to nearest heat   -> high, capped (thermal)
Weights are tunable; they exist to RANK candidates, not to be physical units.
"""
import math
import sys

import pcbnew

# bypass / RC / pull-up -> (anchor, pad) it serves (mirrors pcb_place_v2.ASSIGN).
DECAP = {
    "C1": ("U1", "3"), "C2": ("U1", "2"), "C3": ("U1", "2"),
    "C6": ("U3", "2"), "C7": ("U3", "1"), "C8": ("U3", "1"),
    "C5": ("U5", "2"), "C10": ("U5", "2"), "R28": ("U5", "4"), "R29": ("U5", "3"),
    "C9": ("U4", "3"), "R27": ("U4", "3"),
}
USB_NETS = {"/USB_D+", "/USB_D-"}

WEIGHTS = {
    "usb_bcu_mm": 2.0, "usb_vias": 8.0, "bcu_sig_mm": 1.0,
    "track_mm": 0.05, "vias": 1.0, "decap_mm": 0.5, "sens_mm": -0.5,
}
SENS_CAP = 40.0          # reward sensor->heat separation only up to here
PENALTY = 1e6            # for boards that fail the hard gates


def _mm(v):
    return pcbnew.ToMM(v)


def metrics(board_path):
    b = pcbnew.LoadBoard(board_path)
    fps = {f.GetReference(): f for f in b.GetFootprints()}

    def center(ref):
        p = fps[ref].GetPosition()
        return _mm(p.x), _mm(p.y)

    def pad_xy(ref, num):
        if ref not in fps:
            return None
        for pad in fps[ref].Pads():
            if pad.GetNumber() == num:
                p = pad.GetPosition()
                return _mm(p.x), _mm(p.y)
        return None

    m = dict(usb_bcu_mm=0.0, usb_vias=0, bcu_sig_mm=0.0, track_mm=0.0, vias=0)
    bcu = b.GetLayerID("B.Cu")
    for t in b.GetTracks():
        net = t.GetNetname()
        if t.GetClass() == "PCB_VIA":
            m["vias"] += 1
            if net in USB_NETS:
                m["usb_vias"] += 1
            continue
        ln = _mm(t.GetLength())
        m["track_mm"] += ln
        on_bcu = t.GetLayer() == bcu
        if net in USB_NETS and on_bcu:
            m["usb_bcu_mm"] += ln
        if on_bcu and net != "GND":
            m["bcu_sig_mm"] += ln

    decap = 0.0
    for ref, (ar, pn) in DECAP.items():
        if ref not in fps:
            continue
        cx, cy = center(ref)
        tp = pad_xy(ar, pn)
        if tp:
            decap += math.hypot(cx - tp[0], cy - tp[1])
    m["decap_mm"] = decap

    sens = SENS_CAP
    if "U5" in fps:
        ux, uy = center("U5")
        ds = [math.hypot(ux - center(h)[0], uy - center(h)[1])
              for h in ("U1", "U3") if h in fps]
        if ds:
            sens = min(min(ds), SENS_CAP)
    m["sens_mm"] = sens
    return m


def score(m):
    return sum(WEIGHTS[k] * m[k] for k in WEIGHTS)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else \
        "hardware/esp32-ir-remote.kicad_pcb"
    m = metrics(path)
    s = score(m)
    print(f"score {s:8.1f}  " + "  ".join(
        f"{k}={m[k]:.1f}" if isinstance(m[k], float) else f"{k}={m[k]}"
        for k in ("usb_bcu_mm", "usb_vias", "bcu_sig_mm", "track_mm", "vias",
                  "decap_mm", "sens_mm")))


if __name__ == "__main__":
    main()
