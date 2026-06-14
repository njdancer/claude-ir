#!/usr/bin/env python3
"""Rip all tracks + vias (and signal/GND pour zones) for a clean re-route.

Must run in its own process before scripts/pcb_router.py: removing tracks in
the same process that later iterates GetFootprints() corrupts the SWIG
iterator (returns untyped objects). Footprints, pads, the outline and the
silk/branding graphics are untouched.

  /tmp/kv10/bin/python scripts/pcb_rip.py
"""
import pcbnew

PCB = "hardware/esp32-ir-remote.kicad_pcb"


def main():
    b = pcbnew.LoadBoard(PCB)
    tracks = list(b.GetTracks())          # snapshot before Remove()
    zones = [z for z in b.Zones() if not z.GetIsRuleArea()]
    for t in tracks:
        b.Remove(t)
    for z in zones:
        b.Remove(z)
    pcbnew.SaveBoard(PCB, b)
    print(f"ripped {len(tracks)} tracks/vias, {len(zones)} pour zones")


if __name__ == "__main__":
    main()
