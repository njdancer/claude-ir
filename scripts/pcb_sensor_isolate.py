#!/usr/bin/env python3
"""Thermal isolation for the U5 (AHT20) ambient sensor — TI SNOA967A demo.

Applies the SNOA967A air-temperature techniques to the CURRENT merged board so
we can SEE the result (Nick: "show me what it could look like given our current
layout"). Run AFTER the board is poured (it refills zones):

    /usr/bin/python3.12 scripts/pcb_sensor_isolate.py

What it does (all over the U5 cluster in the SE/south corner):
  1. COPPER MOAT (SNOA967A 2.1): a no-pour-fill keepout band on the N/E/upper-W
     sides of the U5 island so the main GND plane no longer bridges heat from
     U1 (LDO) / U3 (WiFi) into the sensor. Tracks are still ALLOWED through it
     (thin signal traces carry negligible heat) — only the poured copper plane,
     the real thermal highway, is removed. A SW pour NECK is left so the island
     GND stays tied to the plane (else island-removal would delete it).
  2. ISOLATION SLOT (SNOA967A 2.3): a south-edge milled notch on the EAST of the
     island (the only side clear of parts + routing) cutting the FR4 path.
  3. SOLDER-MASK CUT-OUT (SNOA967A 2.1): expose the island copper so it couples
     to air faster (mask k=0.245 insulates).

NOTE (the congestion finding): the heat-facing NORTH side can only get the
copper moat, NOT a physical slot — D12/R20 (status LEDs) and the I2C/3V3 routing
sit in the 1.3 mm gap directly north of R29. A true north slot/peninsula needs
those nudged ~2 mm north in the next floorplan pass. This is exactly the
tradeoff called out in temp-sensor.md.

Idempotent: removes any prior sensor-isolation artefacts before re-adding.
"""
import sys
import pcbnew

BOARD_PATH = "hardware/esp32-ir-remote.kicad_pcb"

# --- U5 island geometry (mm), derived from the cluster bbox -----------------
# Cluster: U5(165,110) + R28(161.5,109) R29(165.6,106.5) C5(170.5,109.8) C10(168.5,110)
ISL_X0, ISL_Y0, ISL_X1, ISL_Y1 = 159.0, 105.4, 172.0, 114.0   # island (kept) rect
MOAT = 0.7                                                      # moat band width
NMOAT_X0 = 162.0        # north moat starts EAST of D12 (status LED blocks the rest)
NECK_Y = 108.0          # west moat stops here; below = SW pour neck to main plane
SLOT_X0, SLOT_X1 = 173.4, 174.6     # east internal isolation slot
SLOT_Y0, SLOT_Y1 = 107.5, 113.5     # (kept off the south edge -> valid outline)
SOUTH_EDGE = 114.0

ISO_NAMES = {"sensor_moat_N", "sensor_moat_E", "sensor_moat_W"}


def rect_chain(x0, y0, x1, y1):
    ch = pcbnew.SHAPE_LINE_CHAIN()
    for x, y in [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]:
        ch.Append(pcbnew.FromMM(x), pcbnew.FromMM(y))
    ch.SetClosed(True)
    return ch


def add_moat(board, name, x0, y0, x1, y1):
    ko = pcbnew.ZONE(board)
    ko.SetIsRuleArea(True)
    ko.SetDoNotAllowZoneFills(True)   # remove the POUR (the thermal highway)
    ko.SetDoNotAllowTracks(False)     # thin signal traces may still cross
    ko.SetDoNotAllowVias(False)
    ls = pcbnew.LSET()
    ls.AddLayer(pcbnew.F_Cu)
    ls.AddLayer(pcbnew.B_Cu)
    ko.SetLayerSet(ls)
    ko.AddPolygon(rect_chain(x0, y0, x1, y1))
    ko.SetZoneName(name)
    board.Add(ko)


def edge_line(board, x0, y0, x1, y1):
    seg = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_SEGMENT)
    seg.SetLayer(pcbnew.Edge_Cuts)
    seg.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(x0), pcbnew.FromMM(y0)))
    seg.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(x1), pcbnew.FromMM(y1)))
    seg.SetWidth(pcbnew.FromMM(0.1))
    board.Add(seg)
    return seg


def mask_cutout(board, layer, x0, y0, x1, y1):
    sh = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_RECT)
    sh.SetLayer(layer)
    sh.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(x0), pcbnew.FromMM(y0)))
    sh.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(x1), pcbnew.FromMM(y1)))
    sh.SetFilled(True)
    sh.SetWidth(0)
    board.Add(sh)


def clean_prior(board):
    for z in list(board.Zones()):
        if z.GetZoneName() in ISO_NAMES:
            board.Remove(z)
    for d in list(board.GetDrawings()):
        # our slot is a closed loop on Edge.Cuts in a tight x/y band by H4
        if d.GetLayer() == pcbnew.Edge_Cuts:
            bb = d.GetBoundingBox()
            cx, cy = pcbnew.ToMM(bb.GetCenter().x), pcbnew.ToMM(bb.GetCenter().y)
            if SLOT_X0 - 0.5 < cx < SLOT_X1 + 0.5 and SLOT_Y0 - 0.5 < cy < SLOT_Y1 + 0.5:
                board.Remove(d)


def del_gnd_vias_in_island(board):
    """Drop GND stitching vias inside the island/slot region. The island GND
    pour stays grounded through the SW neck (both layers), so local F-B ties are
    redundant and would otherwise read unconnected or clash with the slot."""
    gnd = board.FindNet("GND").GetNetCode()
    n = 0
    for t in list(board.GetTracks()):
        if isinstance(t, pcbnew.PCB_VIA) and t.GetNetCode() == gnd:
            x, y = pcbnew.ToMM(t.GetPosition().x), pcbnew.ToMM(t.GetPosition().y)
            if ISL_X0 - MOAT - 0.5 < x < SLOT_X1 + 0.5 and ISL_Y0 - MOAT - 0.5 < y < SOUTH_EDGE:
                board.Remove(t)
                n += 1
    return n


def main():
    board = pcbnew.LoadBoard(BOARD_PATH)
    clean_prior(board)

    # 1. copper moat: N band (east of D12), E band, W band (upper; SW = pour neck)
    add_moat(board, "sensor_moat_N", NMOAT_X0, ISL_Y0 - MOAT, ISL_X1 + MOAT, ISL_Y0)
    add_moat(board, "sensor_moat_E", ISL_X1, ISL_Y0 - MOAT, ISL_X1 + MOAT, SOUTH_EDGE)
    add_moat(board, "sensor_moat_W", ISL_X0 - MOAT, ISL_Y0 - MOAT, ISL_X0, NECK_Y)

    # 2. east internal isolation slot (closed Edge.Cuts loop, off the board edge)
    edge_line(board, SLOT_X0, SLOT_Y0, SLOT_X1, SLOT_Y0)
    edge_line(board, SLOT_X1, SLOT_Y0, SLOT_X1, SLOT_Y1)
    edge_line(board, SLOT_X1, SLOT_Y1, SLOT_X0, SLOT_Y1)
    edge_line(board, SLOT_X0, SLOT_Y1, SLOT_X0, SLOT_Y0)

    # (technique 3 — solder-mask cut-out — deliberately omitted: the island is
    #  too densely populated to expose bare GND without bridging adjacent-net
    #  pads; it only applies to a bare-plane sensor, see temp-sensor.md.)

    del_gnd_vias_in_island(board)

    # refill GND zones so the moat shows as copper-free + island stays via neck
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(BOARD_PATH, board)
    print("sensor isolation applied: 3 moat bands + east slot; refilled")
    return 0


if __name__ == "__main__":
    sys.exit(main())
