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

# J2's USB-C reversibility tie: the two VBUS pad stacks {A4,B9}@(132.4,y) and
# {A9,B4}@(127.6,y) are the same net (Net-(F1-Pad2)) and must be bridged with
# a detour around the D+/D-/CC pads between them. KiCad 10.0.4's DSN export
# makes FreeRouting drop exactly this stacked-same-net-pad tie (10.0.3 routed
# it), so the known-good detour is SPARED from the rip and seeds the DSN as an
# existing wire. J2 is an anchor-fixed part — the tie is identical in every
# candidate, so seeding it adds no ranking noise to the search.
TIE_NET = "Net-(F1-Pad2)"


def _j2_court(b):
    j2 = next((f for f in b.GetFootprints() if f.GetReference() == "J2"), None)
    if not j2:
        return None
    bb = j2.GetCourtyard(pcbnew.F_CrtYd).BBox()
    if bb.GetWidth() == 0:
        bb = j2.GetBoundingBox()
    return bb


def main():
    b = pcbnew.LoadBoard(PCB)
    court = _j2_court(b)
    tracks = list(b.GetTracks())          # snapshot before Remove()
    zones = [z for z in b.Zones() if not z.GetIsRuleArea()]
    spared = 0
    for t in tracks:
        if (court and t.GetClass() != "PCB_VIA" and t.GetNetname() == TIE_NET
                and court.Contains(t.GetStart()) and court.Contains(t.GetEnd())):
            spared += 1
            continue                      # footprint-internal VBUS tie: keep
        b.Remove(t)
    for z in zones:
        b.Remove(z)
    pcbnew.SaveBoard(PCB, b)
    print(f"ripped {len(tracks) - spared} tracks/vias (spared {spared} "
          f"J2 VBUS-tie segs), {len(zones)} pour zones")


if __name__ == "__main__":
    main()
