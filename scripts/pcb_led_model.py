#!/usr/bin/env python3
"""Assign the bent-flat 3D model to the IR LEDs (D2-D5).

The TSAL6200 IR LEDs are bent 90deg at assembly to fire horizontally over the
east edge. hardware/lib/3dshapes/LED_D5.0mm_bent.wrl is a bent-LED mesh that,
at footprint rot0, fires toward LOCAL +Y (perpendicular to the lead line) -
so the footprint rotation in pcb_floorplan aims the fold at each fan angle.
This swaps the straight 5mm-LED model for the bent one on D2-D5 only (status
LEDs are SMD, untouched). Run after pcb_floorplan.py.

  /tmp/kv10/bin/python scripts/pcb_led_model.py
"""
import pcbnew

PCB = "hardware/esp32-ir-remote.kicad_pcb"
BENT = "${KIPRJMOD}/lib/3dshapes/LED_D5.0mm_bent.wrl"
IR_LEDS = {"D2", "D3", "D4", "D5"}


def main():
    b = pcbnew.LoadBoard(PCB)
    n = 0
    for f in b.GetFootprints():
        if f.GetReference() not in IR_LEDS:
            continue
        models = f.Models()
        models.clear()
        m = pcbnew.FP_3DMODEL()
        m.m_Filename = BENT
        m.m_Scale = pcbnew.VECTOR3D(0.3937, 0.3937, 0.3937)
        m.m_Offset = pcbnew.VECTOR3D(0, 0, 0)
        m.m_Rotation = pcbnew.VECTOR3D(0, 0, 0)
        models.push_back(m)
        n += 1
    pcbnew.SaveBoard(PCB, b)
    print(f"assigned bent model to {n} IR LEDs")


if __name__ == "__main__":
    main()
