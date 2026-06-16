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
HOLES = {"H1": (135.0, 73.0), "H2": (185.0, 73.0),
         "H3": (135.0, 112.0), "H4": (185.0, 112.0)}

# Zone anchors: ref -> (x, y, rot_deg). v4 "U3-at-west-end" floorplan (Nick,
# 2026-06-16): U3 rotated 90 at the WEST end so the antenna overhangs the W
# short edge (clean corner, away from everything), its USB pins face NORTH (so
# the USB-C sits on the N long edge right next to them) and its IR pins face
# SOUTH/centre. The IR fan stays at the opposite (E) end and the whole open
# CENTRE holds the now-distributed peripherals — no more thin-strip cram.
ANCHORS = {
    # --- WEST end: MCU rot90, antenna overhangs W edge; USB-C on N edge ---
    "U3":  (126.0, 95.5, 90),    # nudged S so the USB-C posts clear the N edge
    "J2":  (130.0, 72.5, 180),   # USB-C: rot180 -> mouth faces N off the board
                                 # edge (rot90/270 face sideways - unusable); at
                                 # rot180 it's only 4.7mm deep so pads sit
                                 # on-board with the mouth overhanging N + posts
                                 # clearing the edge
    # --- power: U1 LDO in the OPEN NE for a big thermal pour (Nick 2026-06-16);
    #     VBUS J2 -> F1 -> D1 -> U1 spread along the N edge so none crams ---
    "U1":  (176.0, 81.0, 90),    # AMS1117 LDO, open NE -> ~433mm2 +3.3V tab pour
    "F1":  (144.0, 73.5, 0),     # fuse
    "D1":  (160.0, 73.5, 0),     # TVS
    # --- EAST end: IR-TX fan firing E ---
    "Q3":  (176.0, 92.0, 0),
    "D2":  (188.0, 80.0, 315),
    "D3":  (188.0, 90.0, 285),
    "D4":  (188.0, 100.0, 255),
    "D5":  (188.0, 110.0, 225),
    "J5":  (195.0, 73.0, 0),     # ext-IR header, NE corner (clear of D2 fan)
    # --- open CENTRE/S: peripherals (flexible; legalizer fine-tunes) ---
    # Deliberate non-cramming arrangement: LED row along the upper-centre band,
    # J4 below it, buttons + TSOP along the S edge, sensor E-centre away from the
    # W LDO heat. (Targets chosen so courtyards don't fundamentally collide.)
    "D6":  (140.0, 89.0, 90),    # status LED row, upper-centre
    "D7":  (145.5, 89.0, 90),
    "D10": (151.0, 89.0, 90),
    "D11": (156.5, 89.0, 90),
    "D12": (162.0, 89.0, 90),
    "U5":  (140.0, 84.0, 0),     # AHT20 sensor: kept FAR from the NE LDO heat
                                 # (~38mm to U1); limited only by ~18mm to U3
    "J4":  (142.0, 101.0, 90),   # GPIO header, horizontal, centre
    "SW1": (140.0, 110.0, 0),    # RESET button, S edge
    "SW2": (149.0, 110.0, 0),    # BOOT button, S edge
    "U4":  (160.0, 110.0, 0),    # TSOP IR-RX, S edge, lens S, far from E fan
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
