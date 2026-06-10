#!/usr/bin/env python3
"""Silkscreen pass: tidy reference designators + functional labels.

Run: tools/kicad-mcp-server/.venv/bin/python3 scripts/pcb_silk.py
"""
import pcbnew

BOARD_PATH = "hardware/esp32-ir-remote.kicad_pcb"

# functional labels: (text, x, y, size, layer)
LABELS = [
    ("ESP32 IR REMOTE v1.2", 113.5, 58.6, 1.2, pcbnew.F_SilkS),
    ("IR ARRAY ->AC", 145, 61.5, 0.9, pcbnew.F_SilkS),
    ("EXT IR", 121.3, 64.5, 0.6, pcbnew.F_SilkS),
    ("TSOP RX", 171.5, 67.5, 0.7, pcbnew.F_SilkS),
    ("DHT22", 166, 80.8, 0.7, pcbnew.F_SilkS),
    ("QWIIC I2C", 173.5, 92.7, 0.7, pcbnew.F_SilkS),
    ("G 3V3 SDA21 SCL22", 172.5, 103.5, 0.55, pcbnew.F_SilkS),
    ("JTAG", 152, 79, 0.7, pcbnew.F_SilkS),
    ("GPIO HDR", 165, 98.7, 0.7, pcbnew.F_SilkS),
    ("3V3|23|26|33|G", 165, 107.3, 0.55, pcbnew.F_SilkS),
    ("5V|25|32|34|G", 165, 108.8, 0.55, pcbnew.F_SilkS),
    ("RESET", 150.5, 104.2, 0.7, pcbnew.F_SilkS),
    ("BOOT", 160.5, 104.2, 0.7, pcbnew.F_SilkS),
    ("5V", 110.5, 110.3, 0.6, pcbnew.F_SilkS),
    ("3V3", 115.1, 110.3, 0.6, pcbnew.F_SilkS),
    ("TX", 119.75, 110.3, 0.6, pcbnew.F_SilkS),
    ("RX", 124.4, 110.3, 0.6, pcbnew.F_SilkS),
    ("IR TX", 146.5, 73, 0.6, pcbnew.F_SilkS),
    ("USR1", 144, 101.2, 0.55, pcbnew.F_SilkS),
    ("USR2", 153.5, 101.2, 0.55, pcbnew.F_SilkS),
    ("JP1 cut=5V->3V3 off", 110.5, 113.5, 0.55, pcbnew.F_SilkS),
    ("R21/R26: auto-rst 0R", 145, 86.5, 0.55, pcbnew.F_SilkS),
    ("njdancer.github.io/claude-ir", 140, 58.6, 0.8, pcbnew.F_SilkS),
]


def main():
    board = pcbnew.LoadBoard(BOARD_PATH)
    assert isinstance(board, pcbnew.BOARD)

    # 1. tidy reference designators: small, above the footprint
    for fp in board.GetFootprints():
        ref = fp.Reference()
        ref.SetVisible(True)
        ref.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(0.6), pcbnew.FromMM(0.6)))
        ref.SetTextThickness(pcbnew.FromMM(0.1))
        fp.BuildCourtyardCaches()
        c = fp.GetCourtyard(pcbnew.F_CrtYd)
        pos = fp.GetPosition()
        if c.OutlineCount():
            bb = c.BBox()
            y = bb.GetTop() - pcbnew.FromMM(0.45)
            x = bb.GetCenter().x
        else:
            y = pos.y - pcbnew.FromMM(2)
            x = pos.x
        ref.SetPosition(pcbnew.VECTOR2I(x, y))
        ref.SetTextAngle(pcbnew.EDA_ANGLE(0))
        # values invisible on silk (fab notes live in BOM)
        fp.Value().SetVisible(False)

    # 2. functional labels
    for text, x, y, size, layer in LABELS:
        t = pcbnew.PCB_TEXT(board)
        t.SetText(text)
        t.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y)))
        t.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(size), pcbnew.FromMM(size)))
        t.SetTextThickness(pcbnew.FromMM(max(0.1, size / 6)))
        t.SetLayer(layer)
        board.Add(t)

    pcbnew.SaveBoard(BOARD_PATH, board)
    print(f"refs tidied, {len(LABELS)} labels added, saved")


if __name__ == "__main__":
    main()
