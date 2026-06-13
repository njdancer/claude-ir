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

sys.path.insert(0, os.path.join(ROOT, "scripts", "ci"))
from hardware_validate import netlist_fields, netlist_model  # noqa: E402

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
    "D1":  "TVS SMBJ5.0A, SMB 2-pad. Align cathode band with the on-board "
           "silk band marker (= the +5V pad; marking fixed 2026-06-13).",
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

# ---------------------------------------------------------------------------
# CPL ROTATION CORRECTIONS. JLCPCB's pick-and-place zero-orientation differs
# from KiCad's library convention per package; an uncorrected CPL is the
# classic dead-assembled-board cause. Offsets (degrees ADDED to the KiCad
# rotation, mod 360) follow the community-maintained JLCKicadTools database
# (matthewlai/JLCKicadTools cpl_rotations_db.csv).
#
# EVERY assembled footprint must be classified — either listed here or
# matching SYMMETRIC_RE — otherwise this script refuses to emit a CPL, so a
# new package can never reach JLC with an unreviewed rotation.
JLC_ROTATION = {
    "TSOT-23-6": 180,                   # U1 AP63203   (^TSOT-23 -> 180)
    "SOIC-16_3.9x9.9mm_P1.27mm": 270,   # U2 CH340C    (^SOIC-   -> 270)
    "ESP32-WROOM-32D": 270,             # U3 WROOM-32E (^ESP32-W -> 270)
    "SOT-23": 270,                      # Q1-Q5        (^SOT-23  -> -90)
    # Tact switch: pads are 180-symmetric and same-row pads are internally
    # common, so 0/180 are equivalent; a 90 error would miss the pads
    # entirely (visible in preview).
    "SW-SMD_TS-1187A-5.1x5.1": 0,
}
# Orientation-irrelevant chip passives (rectangular 2-pad).
SYMMETRIC_RE = re.compile(r"^[RC]_\d{4}_\d{4}Metric")

KICAD_CLI = os.environ.get("KICAD_CLI") or shutil.which("kicad-cli") or \
    "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"

GERBER_LAYERS = ("F.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,"
                 "F.Mask,B.Mask,Edge.Cuts")


def run(*args):
    print("  $", " ".join(args))
    subprocess.run(args, check=True, cwd=HW)


def parse_netlist():
    """ref -> dict(value, footprint, lcsc, dnp).

    Reuses the s-expression parser in scripts/ci/hardware_validate.py so this
    is whitespace-robust: it handles both the KiCad 9 compact netlist and the
    KiCad 10 expanded (multi-line, tab-nested, libparts) format. The old
    single-line regex silently parsed 0 components on a v10-exported netlist
    (which would have emitted an empty BOM/CPL).
    """
    fields = netlist_fields(NET)
    _, model_comps, _ = netlist_model(NET)
    comps = {}
    for ref, f in fields.items():
        fp = model_comps.get(ref, ("", ""))[1]
        comps[ref] = {
            "value": f["value"],
            "footprint": fp.split(":")[-1],
            "lcsc": f["fields"].get("LCSC", ""),
            "dnp": f["dnp"],
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

    # -- JLC CPL (assembled only, rotation-corrected) -----------------------
    def rotation_offset(ref):
        fp = comps[ref]["footprint"]
        if fp in JLC_ROTATION:
            return JLC_ROTATION[fp]
        if SYMMETRIC_RE.match(fp):
            return None  # symmetric: no correction, not orientation-critical
        raise SystemExit(
            f"UNCLASSIFIED footprint for CPL rotation: {ref} '{fp}'. Add it "
            "to JLC_ROTATION (verify against JLCKicadTools' "
            "cpl_rotations_db.csv + the JLC placement preview) or extend "
            "SYMMETRIC_RE if it is genuinely orientation-irrelevant.")

    keep = set(assembled)
    cpl = os.path.join(FAB, "esp32-ir-remote-jlcpcb-cpl.csv")
    orient = []  # orientation-critical rows for the report
    n = 0
    with open(raw) as fin, open(cpl, "w") as fout:
        fout.write("Designator,Mid X,Mid Y,Layer,Rotation\n")
        for row in csv.DictReader(fin):
            if row["Ref"] not in keep:
                continue
            off = rotation_offset(row["Ref"])
            rot = (float(row["Rot"]) + (off or 0)) % 360
            fout.write("%s,%f,%f,%s,%f\n" % (
                row["Ref"], float(row["PosX"]), float(row["PosY"]),
                row["Side"].capitalize(), rot))
            if off is not None:
                c = comps[row["Ref"]]
                orient.append([row["Ref"], c["value"], c["lcsc"],
                               c["footprint"], float(row["Rot"]), off, rot])
            n += 1
    assert n == len(assembled), (n, len(assembled))
    print("  CPL: %d placements (%d rotation-corrected/orientation-critical)"
          % (n, len(orient)))

    # -- orientation report: the JLC-preview checklist ------------------------
    # One row per orientation-critical assembled part. The preview check is
    # now mechanical: confirm each part's pin-1/polarity marker in JLC's
    # render matches the board renders (final_top.png) — the CPL rotations
    # were pre-corrected per the table above, so the preview SHOULD already
    # be correct; any mismatch means a JLC_ROTATION entry is wrong for that
    # package and must be fixed there (not by nudging the preview).
    orep = os.path.join(FAB, "esp32-ir-remote-orientation-report.csv")
    with open(orep, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Designator", "Value", "LCSC", "Footprint",
                    "KiCad rot", "JLC offset", "CPL rot",
                    "Verify in JLC placement preview"])
        for r in sorted(orient, key=lambda r: natkey(r[0])):
            w.writerow(r + ["pin-1/polarity marker matches final_top.png"])
    print("  orientation report: %d parts -> %s"
          % (len(orient), os.path.basename(orep)))

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
        # The leading space on the --rotate value is load-bearing: kicad-cli
        # 10's arg parser otherwise reads a value beginning with '-' as a flag
        # ("Unknown argument: -30,0,45") and aborts. Same trick as build-site.sh.
        run(KICAD_CLI, "pcb", "render", "--side", "top", "--perspective",
            "--rotate", " -30,0,45", "--zoom", "0.9", "--quality", "high",
            "--width", "1600", "--height", "1100",
            "-o", os.path.join(FAB, "final_iso.png"), PCB)


if __name__ == "__main__":
    main()
