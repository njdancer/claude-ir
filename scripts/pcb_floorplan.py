#!/usr/bin/env python3
"""Restructure pass: new long-thin outline + zone-anchor placement.

The v2 board was placed by dump-and-nudge: no zoning, spider-web traces, ~1/3
empty. This re-floorplans into functional zones along a long-thin board so
the noisy power/USB end is physically separated from the EMI-sensitive
IR-RX/sensor end (see hardware/notes/layout.md "v2 enclosure-driven
floorplan"):

    WEST end .............. CENTER ............... EAST end (front)
    power + USB-C         MCU (antenna N)        IR-TX fan + IR-RX + sensor

Only the zone ANCHORS are placed here (the big parts that define the zones).
Support parts (decoupling/pullups/RC) are re-seated against these anchors by
scripts/pcb_place_v2.py (Phase B). Mounting holes go wherever the zones leave
room (3D-printed enclosure adapts). Iterate: edit ANCHORS, rerun, render.

  /tmp/kv10/bin/python scripts/pcb_floorplan.py
"""
import pcbnew

PCB = "hardware/esp32-ir-remote.kicad_pcb"

# New board outline (mm). Long-thin: ~92 x 44.
BX0, BY0, BX1, BY1 = 106.0, 70.0, 198.0, 114.0

# 4x M3 mounting holes — placed in the clearest well-spread spots the dense
# layout leaves (3D-printed enclosure adapts to wherever they land). The east
# end is packed by the IR fan, so the E holes sit inboard of the corners.
HOLES = {"H1": (110.0, 74.0), "H2": (177.5, 80.5),
         "H3": (110.0, 105.0), "H4": (177.5, 109.5)}

# Zone anchors: ref -> (x, y, rot_deg). v3 "rotate-U3-180" floorplan (Nick,
# 2026-06-16): U3 spun 180 and dropped onto the SOUTH edge so the antenna
# overhangs S and its USB pins (were E) now face W toward the W USB-C, while the
# IR_TX/IR_RX pins (were W) now face E toward the E IR fan — killing the old
# USB cross-board run. The S peripherals move up into the freed N band.
ANCHORS = {
    # --- WEST column: power + USB-C + buttons ---
    "J2":  (110.0, 94.0, 270),   # USB-C, mouth overhangs W edge; y aligns to U3's W USB pins
    "U1":  (118.0, 76.0, 90),    # AMS1117 LDO, NW corner, tab N into the edge thermal pour
    "F1":  (124.0, 74.0, 0),     # fuse  (VBUS: J2 -> F1 -> D1 -> U1)
    "D1":  (132.0, 74.0, 0),     # TVS
    "SW1": (112.0, 104.0, 0),    # RESET button, W edge (reachable)
    "SW2": (123.0, 104.0, 0),    # BOOT button
    # --- CENTER-SOUTH: MCU rotated 180, antenna keepout overhangs the S edge ---
    "U3":  (150.0, 96.0, 180),
    # --- NORTH band (freed by U3 moving S): header hugs U3, status LEDs N edge.
    #     NOTE: routing not yet closed (~14 nets) — the rotation re-sides every
    #     non-USB/IR pin, so this peripheral set still needs re-optimisation
    #     (pcb_search on the fixed rotated U3). USB/IR alignment is proven. ---
    "J4":  (150.0, 82.0, 0),     # spare-GPIO header, just N of U3 (heaviest link)
    "U4":  (135.0, 75.0, 0),     # TSOP IR-RX, N edge, lens N, far from the E IR fan
    "D6":  (148.0, 73.0, 90),
    "D7":  (153.0, 73.0, 90),
    "D10": (158.0, 73.0, 90),
    "D11": (163.0, 73.0, 90),
    "D12": (168.0, 73.0, 90),
    # --- EAST column: IR-TX fan firing E, sensor, ext-IR ---
    "Q3":  (174.0, 98.0, 0),     # IR MOSFET driver, W of the LED row
    "D2":  (188.0, 80.0, 315),  # +45 NE
    "D3":  (188.0, 90.0, 285),  # +15
    "D4":  (188.0, 100.0, 255), # -15
    "D5":  (188.0, 110.0, 225), # -45 SE
    "U5":  (182.0, 76.0, 0),     # AHT20 sensor, NE corner, far from LDO heat
    "J5":  (195.0, 74.0, 0),     # ext-IR header, E edge
}


def set_outline(b):
    # drop existing Edge.Cuts graphics
    for d in list(b.GetDrawings()):
        if d.GetLayer() == pcbnew.Edge_Cuts:
            b.Remove(d)
    pts = [(BX0, BY0), (BX1, BY0), (BX1, BY1), (BX0, BY1)]
    for i in range(4):
        seg = pcbnew.PCB_SHAPE(b, pcbnew.SHAPE_T_SEGMENT)
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % 4]
        seg.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(x0), pcbnew.FromMM(y0)))
        seg.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(x1), pcbnew.FromMM(y1)))
        seg.SetLayer(pcbnew.Edge_Cuts)
        seg.SetWidth(pcbnew.FromMM(0.1))
        b.Add(seg)


def main():
    b = pcbnew.LoadBoard(PCB)
    apply_anchors(b, ANCHORS, HOLES)
    pcbnew.SaveBoard(PCB, b)


def apply_anchors(b, anchors, holes, draw_outline=True):
    """Place every anchor + mounting hole, fan the IR LEDs about their true
    centre, and (optionally) (re)draw the outline. Used by main() with the
    module ANCHORS and by pcb_search.py with generated candidate dicts.

    draw_outline=False skips set_outline() (whose b.Remove() curses later
    .Pads()/.GetCourtyard() iteration) so the caller can legalize placement
    first and draw the outline itself afterwards."""
    fps = {f.GetReference(): f for f in b.GetFootprints()}
    # NB: set_outline() does b.Remove() which curses later .Pads() iteration,
    # so it runs LAST (after the LED-centroid alignment below).
    moved = 0
    for ref, (x, y, rot) in {**{r: (hx, hy, 0) for r, (hx, hy) in holes.items()},
                             **anchors}.items():
        f = fps.get(ref)
        if not f:
            continue
        f.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
        if rot is not None:
            f.SetOrientationDegrees(rot)
        moved += 1

    # IR LEDs fan but must stay ALIGNED: rotate about the true LED centre, not
    # the footprint anchor (pad 1). After rotation, shift each so its pad
    # centroid lands on the target — equivalent to pivoting in place.
    for ref in ("D2", "D3", "D4", "D5"):
        f = fps.get(ref)
        if not f or ref not in anchors:
            continue
        tx, ty, _ = anchors[ref]
        xs, ys = [], []
        for p in f.Pads():
            pp = p.GetPosition()
            xs.append(pcbnew.ToMM(pp.x))
            ys.append(pcbnew.ToMM(pp.y))
        cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
        pos = f.GetPosition()
        f.SetPosition(pcbnew.VECTOR2I(pos.x + pcbnew.FromMM(tx - cx),
                                      pos.y + pcbnew.FromMM(ty - cy)))

    if draw_outline:
        set_outline(b)   # last: its b.Remove() curses .Pads() iteration above
    print(f"outline {BX1-BX0:.0f}x{BY1-BY0:.0f}mm, moved {moved} parts")
    return moved


if __name__ == "__main__":
    main()
