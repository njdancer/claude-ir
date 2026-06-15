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

# Zone anchors: ref -> (x, y, rot_deg). Firing/mouth directions verified by
# render then tuned. IR LED fan fires EAST (+x); rot ~0 = east, splay around it.
ANCHORS = {
    # --- WEST end: power + USB ---
    "J2":  (109.7, 92.0, 270),   # USB-C, mouth overhangs west edge ~0.5mm, pads on-board
    "U1":  (120.0, 80.5, 90),    # AMS1117 LDO in the open NW corner, rot90 so the
                                 # SOT-223 tab faces NORTH into the to-the-edge
                                 # thermal pour (max heat spread); pins face S to
                                 # the VBUS chain. 2-sided pour+vias in pcb_ldo_pour
    "F1":  (119.0, 88.0, 0),     # fuse  (VBUS: J2 -> F1 -> D1 -> U1), pocket S of U1
    "D1":  (119.0, 93.0, 0),     # TVS, stacked below F1
    # --- CENTER: MCU, antenna keepout flush at NORTH edge (rot0) ---
    "U3":  (150.0, 88.5, 0),
    # --- EAST end (front): IR-TX fan firing east. base east = rot270; fan is
    #     ±15/±45° around it. (x,y) here is the desired pad-CENTROID; main()
    #     shifts each LED so it pivots about its true centre and the row stays
    #     aligned while the beams fan. ---
    "Q3":  (178.0, 92.0, 0),     # IR MOSFET driver, W of the LED row
    "D2":  (186.0, 79.0, 315),  # +45 NE
    "D3":  (186.0, 88.0, 285),  # +15
    "D4":  (186.0, 97.0, 255),  # -15
    "D5":  (186.0, 106.0, 225), # -45 SE
    # --- North edge (clear apart from the central antenna keepout x136-164) ---
    "J4":  (130.0, 84.0, 180),   # spare-GPIO 2x5 header — rotated 90 deg CCW
                                 # (vertical), sat E of U1 but NOT hugging the
                                 # module: leaves the module-W channel open for
                                 # the ESP boot/strap routing that jammed before
    "J5":  (168.0, 74.0, 0),     # ext-IR header, E of the module
    # --- TSOP receiver: SOUTH long edge (relocated off the TX corner, 1fc1f68);
    #     lens fires south/room, isolated from the 38kHz drive loop ---
    "U4":  (153.0, 110.5, 180),
    # --- South / west: buttons, sensor ---
    "SW1": (120.0, 109.0, 0),    # RESET
    "SW2": (131.0, 109.0, 0),    # BOOT
    "U5":  (165.0, 110.0, 0),    # AHT20 sensor, S edge, far from LDO heat (W)
    # --- Status-LED cluster: tight labelled block, top face, S of the MCU ---
    "D6":  (141.0, 104.0, 90),
    "D7":  (146.0, 104.0, 90),
    "D10": (151.0, 104.0, 90),
    "D11": (156.0, 104.0, 90),
    "D12": (161.0, 104.0, 90),
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
