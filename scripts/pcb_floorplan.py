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
HOLES = {"H1": (110.0, 74.0), "H2": (184.0, 74.0),
         "H3": (110.0, 105.0), "H4": (178.5, 104.5)}

# Zone anchors: ref -> (x, y, rot_deg). Firing/mouth directions verified by
# render then tuned. IR LED fan fires EAST (+x); rot ~0 = east, splay around it.
ANCHORS = {
    # --- WEST end: power + USB ---
    "J2":  (109.7, 92.0, 270),   # USB-C, mouth overhangs west edge ~0.5mm, pads on-board
    "U1":  (126.0, 86.0, 0),     # AMS1117 LDO
    "F1":  (122.0, 95.0, 90),    # fuse  (VBUS: J2 -> F1 -> D1 -> U1)
    "D1":  (130.0, 95.0, 90),    # TVS
    # --- CENTER: MCU, antenna keepout flush at NORTH edge (rot0) ---
    "U3":  (150.0, 88.5, 0),
    # --- EAST end (front): IR-TX fan firing east, Q3 just inboard ---
    "Q3":  (181.0, 96.0, 0),     # IR MOSFET driver
    "D2":  (191.0, 84.0, 68),    # TSAL6200 fan: N-most, tilt north
    "D3":  (191.0, 92.0, 23),
    "D4":  (191.0, 100.0, 337),  # -23
    "D5":  (191.0, 108.0, 292),  # -67.5
    # --- North edge (clear apart from the central antenna keepout x136-164) ---
    "J4":  (120.0, 75.5, 90),    # spare-GPIO 2x5 header, NW
    "J5":  (170.0, 74.0, 0),     # ext-IR header, NE (near the IR array)
    "U4":  (191.0, 74.0, 0),     # TSOP receiver, faces east (room), NE corner
    # --- South edge: power jumper, sensor, buttons, status LEDs ---
    "JP1": (112.0, 110.0, 0),    # LDO-disable jumper near U1
    "U5":  (123.0, 110.0, 0),    # AHT20 sensor (away from IR-LED heat at east)
    "SW1": (136.0, 109.0, 0),    # RESET
    "SW2": (147.0, 109.0, 0),    # BOOT
    "D6":  (156.0, 110.0, 90),   # status LEDs, S row
    "D7":  (163.0, 110.0, 90),
    "D10": (170.0, 110.0, 90),
    "D11": (177.0, 110.0, 90),
    "D12": (184.0, 110.0, 90),
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
    fps = {f.GetReference(): f for f in b.GetFootprints()}
    set_outline(b)
    moved = 0
    for ref, (x, y, rot) in {**HOLES_AS_ANCHORS(), **ANCHORS}.items():
        f = fps.get(ref)
        if not f:
            print(f"  ! {ref} not found")
            continue
        f.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
        if rot is not None:
            f.SetOrientationDegrees(rot)
        moved += 1
    pcbnew.SaveBoard(PCB, b)
    print(f"outline {BX1-BX0:.0f}x{BY1-BY0:.0f}mm, moved {moved} parts")


def HOLES_AS_ANCHORS():
    return {ref: (x, y, 0) for ref, (x, y) in HOLES.items()}


if __name__ == "__main__":
    main()
