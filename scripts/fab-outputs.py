#!/usr/bin/env python3
"""Regenerate the JLCPCB fab package in hardware/fab/ from the board sources.

Single source of truth for the ASSEMBLY SPLIT: which parts JLCPCB places
(SMT, top side) vs which go in the hand-solder kit. bring-up.md's solder
order and the BOM/CPL are all downstream of the HAND_SOLDER set below —
edit it here, rerun, commit the regenerated outputs.

Usage (host with kicad-cli, or the kicad/kibot container):
    python3 scripts/fab-outputs.py [--skip-renders]

Outputs (hardware/fab/):
    gerbers/ + esp32-ir-remote-gerbers.zip   copper/mask/silk/edge + drill
    esp32-ir-remote-cpl-raw.csv              kicad-cli pos export, all parts
    esp32-ir-remote-jlcpcb-bom.csv           assembled lines only
    esp32-ir-remote-jlcpcb-cpl.csv           assembled placements only
    esp32-ir-remote-hand-solder-kit.csv      the kit: order these loose
    final_top.png / final_bottom.png / final_iso.png
"""

import csv
import io
import os
import re
import shutil
import subprocess
import sys
import zipfile
from collections import OrderedDict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HW = os.path.join(ROOT, "hardware")
FAB = os.path.join(HW, "fab")
PCB = os.path.join(HW, "esp32-ir-remote.kicad_pcb")
NET = os.path.join(HW, "esp32-ir-remote.net")

# ---------------------------------------------------------------------------
# THE ASSEMBLY SPLIT.
#
# Hand-solder kit rationale (rev 1.3, 2026-06-11): everything through-hole
# (machine assembly can't bend the IR LEDs over the edge anyway, and THT
# lines all carry Extended loading + per-joint fees) plus the easy big
# two-terminal SMD Extended parts. What remains on the assembly BOM is
# all Basic except exactly three Extended lines: U1 (buck), U2 (CH340C),
# U3 (WROOM) — the placements where machine quality matters most.
HAND_SOLDER = {
    "D1":  "TVS SMBJ5.0A, SMB 2-pad. CATHODE BAND TOWARD F1.",
    "D2":  "TSAL6200 IR LED. Bend 90deg over north edge per silk fan guide.",
    "D3":  "TSAL6200 IR LED. Bend 90deg over north edge per silk fan guide.",
    "D4":  "TSAL6200 IR LED. Bend 90deg over north edge per silk fan guide.",
    "D5":  "TSAL6200 IR LED. Bend 90deg over north edge per silk fan guide.",
    "D6":  "Red 3mm, 5V power LED. Flat = cathode.",
    "D7":  "Green 3mm, 3V3 power LED. Flat = cathode.",
    "D8":  "Amber 3mm, serial TX LED. Flat = cathode.",
    "D9":  "Amber 3mm, serial RX LED. Flat = cathode.",
    "D10": "Red 3mm, IR-TX indicator. Flat = cathode.",
    "D11": "Blue 3mm, user LED 1. Flat = cathode.",
    "D12": "Blue 3mm, user LED 2. Flat = cathode.",
    "F1":  "Polyfuse 1812, 2-pad, non-polarized. Fit BEFORE first power.",
    "J2":  "USB-C GCT USB4085, through-hole. Fit BEFORE first power.",
    "J3":  "Qwiic JST-SH 1mm pitch. Fiddliest of the kit; flux + drag.",
    "L1":  "4.7uH 6x6mm, side-wrap terminations. Fit BEFORE first power.",
    "U4":  "TSOP38238 IR receiver, 3-pin THT.",
    "U5":  "AM2302/DHT22, 4-pin THT. NEAR STOCK-OUT AT LCSC - order early.",
}
# THT bits with no LCSC code (generic): listed on the kit for completeness.
KIT_EXTRA = [
    ("J4", "2x5 pin header 2.54mm", "", "1", "Spare GPIO header. Generic."),
    ("J5", "1x2 pin header 2.54mm", "", "1", "Ext-IR header (optional). Generic."),
]
# Not fitted at all: DNP parts (from schematic) and JP1 (bare solder jumper).
NEVER_PLACE = {"JP1"}

KICAD_CLI = os.environ.get("KICAD_CLI") or shutil.which("kicad-cli") or \
    "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"

GERBER_LAYERS = ("F.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,"
                 "F.Mask,B.Mask,Edge.Cuts")


def run(*args):
    print("  $", " ".join(args))
    subprocess.run(args, check=True, cwd=HW)


def parse_netlist():
    """ref -> dict(value, footprint, lcsc, dnp)"""
    net = open(NET).read()
    comps = {}
    for blk in re.split(r"\n    \(comp ", net)[1:]:
        ref = re.search(r'\(ref "([^"]+)"\)', blk).group(1)
        val = re.search(r'\(value "([^"]*)"\)', blk)
        fp = re.search(r'\(footprint "([^"]*)"\)', blk)
        lcsc = re.search(r'\(field \(name "LCSC"\) "([^"]*)"\)', blk)
        comps[ref] = {
            "value": val.group(1) if val else "",
            "footprint": (fp.group(1) if fp else "").split(":")[-1],
            "lcsc": lcsc.group(1) if lcsc else "",
            "dnp": '(property (name "dnp")' in blk,
        }
    return comps


def natkey(ref):
    m = re.match(r"([A-Za-z]+)(\d+)", ref)
    return (m.group(1), int(m.group(2))) if m else (ref, 0)


def main():
    skip_renders = "--skip-renders" in sys.argv
    comps = parse_netlist()

    # -- gerbers + drill ----------------------------------------------------
    gdir = os.path.join(FAB, "gerbers")
    shutil.rmtree(gdir, ignore_errors=True)
    os.makedirs(gdir)
    run(KICAD_CLI, "pcb", "export", "gerbers", "--layers", GERBER_LAYERS,
        "-o", gdir + "/", PCB)
    run(KICAD_CLI, "pcb", "export", "drill", "--format", "excellon",
        "--excellon-units", "mm", "-o", gdir + "/", PCB)
    zpath = os.path.join(FAB, "esp32-ir-remote-gerbers.zip")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(os.listdir(gdir)):
            z.write(os.path.join(gdir, f), f)
    print("  gerbers zipped:", os.path.basename(zpath))

    # -- raw positions ------------------------------------------------------
    raw = os.path.join(FAB, "esp32-ir-remote-cpl-raw.csv")
    run(KICAD_CLI, "pcb", "export", "pos", "--format", "csv", "--units", "mm",
        "-o", raw, PCB)

    # -- classify -----------------------------------------------------------
    assembled, kit, dnp = [], [], []
    for ref in sorted(comps, key=natkey):
        c = comps[ref]
        if c["dnp"]:
            dnp.append(ref)
        elif ref in HAND_SOLDER:
            kit.append(ref)
        elif ref in NEVER_PLACE or not c["lcsc"]:
            dnp.append(ref)
        else:
            assembled.append(ref)

    # -- JLC BOM (assembled only, grouped) ----------------------------------
    groups = OrderedDict()
    for ref in assembled:
        c = comps[ref]
        groups.setdefault((c["value"], c["footprint"], c["lcsc"]), []).append(ref)
    bom = os.path.join(FAB, "esp32-ir-remote-jlcpcb-bom.csv")
    with open(bom, "w") as f:
        f.write("Comment,Designator,Footprint,LCSC\n")
        for (val, fp, lcsc), refs in groups.items():
            refs = sorted(refs, key=natkey)
            des = ",".join(refs)
            if len(refs) > 1:
                des = '"%s"' % des
            f.write("%s,%s,%s,%s\n" % (val, des, fp, lcsc))
    print("  BOM: %d assembled lines" % len(groups))

    # -- JLC CPL (assembled only) -------------------------------------------
    keep = set(assembled)
    cpl = os.path.join(FAB, "esp32-ir-remote-jlcpcb-cpl.csv")
    n = 0
    with open(raw) as fin, open(cpl, "w") as fout:
        fout.write("Designator,Mid X,Mid Y,Layer,Rotation\n")
        for row in csv.DictReader(fin):
            if row["Ref"] in keep:
                fout.write("%s,%f,%f,%s,%f\n" % (
                    row["Ref"], float(row["PosX"]), float(row["PosY"]),
                    row["Side"].capitalize(), float(row["Rot"])))
                n += 1
    assert n == len(assembled), (n, len(assembled))
    print("  CPL: %d placements" % n)

    # -- hand-solder kit ----------------------------------------------------
    kitcsv = os.path.join(FAB, "esp32-ir-remote-hand-solder-kit.csv")
    kit_groups = OrderedDict()
    for ref in kit:
        c = comps[ref]
        kit_groups.setdefault((c["value"], c["lcsc"]), []).append(ref)
    with open(kitcsv, "w", newline="") as f:
        w = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        w.writerow(["Designator", "Value", "LCSC", "Qty per board", "Notes"])
        for (val, lcsc), refs in kit_groups.items():
            refs = sorted(refs, key=natkey)
            w.writerow([",".join(refs), val, lcsc, len(refs),
                        HAND_SOLDER[refs[0]]])
        for row in KIT_EXTRA:
            w.writerow(list(row))
    print("  kit: %d lines (+%d generic)" % (len(kit_groups), len(KIT_EXTRA)))
    print("  not fitted (DNP/jumper/no-code):", ",".join(sorted(dnp, key=natkey)))

    # -- renders ------------------------------------------------------------
    if not skip_renders:
        run(KICAD_CLI, "pcb", "render", "--side", "top", "--quality", "high",
            "--width", "1600", "--height", "1100",
            "-o", os.path.join(FAB, "final_top.png"), PCB)
        run(KICAD_CLI, "pcb", "render", "--side", "bottom", "--quality", "high",
            "--width", "1600", "--height", "1100",
            "-o", os.path.join(FAB, "final_bottom.png"), PCB)
        run(KICAD_CLI, "pcb", "render", "--side", "top", "--perspective",
            "--rotate=-30,0,45", "--zoom", "0.9", "--quality", "high",
            "--width", "1600", "--height", "1100",
            "-o", os.path.join(FAB, "final_iso.png"), PCB)


if __name__ == "__main__":
    main()
