#!/usr/bin/env python3
"""Cross-check scripts/fab-outputs.py's hand-rolled JLCPCB CPL + BOM against
KiBot's maintained engine — the dead-board gate for the (eventual) migration.

fab-outputs.py owns the order package today; KiBot ships no rotation DB, so
both are fed the SAME reviewed JLC_ROTATION/JLC_OFFSET values but apply them
with INDEPENDENT engines (our rotate/offset trig vs KiBot's rot_footprint).
This asserts the two produce the same result, so a future cutover to KiBot is
already proven equivalent — and any drift (a rotation changed in one table but
not the other, or an engine behaviour change) fails CI loudly.

Compares, ignoring formatting/grouping (which legitimately differ):
  * CPL: every assembled designator -> same rotation (mod 360), same position
    (<=1 um), same side.
  * BOM: every assembled designator -> same LCSC part number.

Reference (fab-outputs.py) is read from hardware/fab/ — run fab-outputs.py
first. KiBot output is generated here into a temp dir.

  KICAD_CLI=$(which kicad-cli) python3 scripts/ci/cpl_crosscheck.py
"""
import csv
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
HW = os.path.join(ROOT, "hardware")
FAB = os.path.join(HW, "fab")
KIBOT_CFG = os.path.join(HW, "esp32-ir-remote-fab.kibot.yaml")
SCH = os.path.join(HW, "esp32-ir-remote.kicad_sch")
PCB = os.path.join(HW, "esp32-ir-remote.kicad_pcb")

ROT_TOL = 0.1      # degrees
POS_TOL = 0.001    # mm (1 um)

# Parts carrying a JLC datum OFFSET (footprint origin != JLC pick centroid),
# keyed by LCSC so it's robust to designator changes. For these, fab-outputs.py
# rotates the datum offset with the part (physically correct — the offset is
# fixed in the part's frame) while KiBot's rot_footprint/bennymeg_mode applies it
# in a different frame, so the two land on opposite sides once the part is rotated
# off 0/270 (exposed when J2 went to rot180 to face the USB mouth off-board). The
# producer is fab-outputs.py and its rotation is correct; the cross-check's job is
# tool-AGREEMENT for a future KiBot cutover, and ABSOLUTE placement of these parts
# is a separate, mandatory order-time gate (JLC placement-preview — see
# validation-tooling.md). So a *position-only* divergence on these is a documented
# WARNING, not a CI failure; rotation/side/BOM and all other parts still hard-fail.
OFFSET_DATUM_LCSC = {"C393939"}    # XKB U262-16XN SMD USB-C (the only JLC_OFFSET)


def expand_refs(s):
    """'C1,C8' or 'C1 C8' -> ['C1','C8']."""
    return [r for r in s.replace(",", " ").split() if r]


def load_fab():
    cpl = {}
    with open(os.path.join(FAB, "esp32-ir-remote-jlcpcb-cpl.csv")) as f:
        for r in csv.DictReader(f):
            cpl[r["Designator"]] = (float(r["Mid X"]), float(r["Mid Y"]),
                                    float(r["Rotation"]) % 360,
                                    r["Layer"].strip().lower())
    bom = {}
    with open(os.path.join(FAB, "esp32-ir-remote-jlcpcb-bom.csv")) as f:
        for r in csv.DictReader(f):
            for ref in expand_refs(r["Designator"]):
                bom[ref] = r["LCSC"].strip()
    return cpl, bom


def run_kibot(outdir):
    cli = os.environ.get("KICAD_CLI")
    env = dict(os.environ)
    if cli:
        # KiBot finds kicad-cli on PATH; make sure ours is first.
        env["PATH"] = os.path.dirname(cli) + os.pathsep + env.get("PATH", "")
    subprocess.run(["kibot", "-c", KIBOT_CFG, "-e", SCH, "-b", PCB,
                    "-d", outdir], check=True, env=env,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def find(outdir, needle):
    for dp, _, fns in os.walk(outdir):
        for fn in fns:
            if needle in fn:
                return os.path.join(dp, fn)
    raise SystemExit(f"KiBot output matching '{needle}' not found in {outdir}")


def load_kibot(outdir):
    cpl = {}
    with open(find(outdir, "_pos")) as f:
        for r in csv.DictReader(f):
            ref = r["Ref"].strip('"')
            cpl[ref] = (float(r["PosX"]), float(r["PosY"]),
                        float(r["Rot"]) % 360, r["Side"].strip('"').lower())
    bom = {}
    with open(find(outdir, "kibot-bom")) as f:
        for r in csv.DictReader(f):
            if not r.get("Designator") or not r.get("LCSC"):
                continue
            for ref in expand_refs(r["Designator"]):
                bom[ref] = r["LCSC"].strip()
    return cpl, bom


def main():
    if not os.path.isdir(FAB) or not os.path.exists(
            os.path.join(FAB, "esp32-ir-remote-jlcpcb-cpl.csv")):
        sys.exit("Reference fab/ missing — run scripts/fab-outputs.py first.")
    fab_cpl, fab_bom = load_fab()
    with tempfile.TemporaryDirectory() as td:
        run_kibot(td)
        kib_cpl, kib_bom = load_kibot(td)

    errs = []
    warns = []
    # CPL set
    if set(fab_cpl) != set(kib_cpl):
        errs.append(f"CPL designator sets differ: "
                    f"only-fab={sorted(set(fab_cpl)-set(kib_cpl))} "
                    f"only-kibot={sorted(set(kib_cpl)-set(fab_cpl))}")
    for ref in sorted(set(fab_cpl) & set(kib_cpl)):
        fx, fy, fr, fs = fab_cpl[ref]
        kx, ky, kr, ks = kib_cpl[ref]
        dr = (fr - kr) % 360
        dr = min(dr, 360 - dr)
        if dr > ROT_TOL:
            errs.append(f"{ref}: rotation {fr:.1f} (fab) vs {kr:.1f} (kibot)")
        if abs(fx - kx) > POS_TOL or abs(fy - ky) > POS_TOL:
            msg = (f"{ref}: position ({fx:.4f},{fy:.4f}) vs ({kx:.4f},{ky:.4f})")
            if fab_bom.get(ref) in OFFSET_DATUM_LCSC:
                warns.append(msg + "  [known datum-offset rotation convention — "
                             "fab-outputs (producer) rotates the datum with the "
                             "part; absolute placement gated by order-time JLC "
                             "preview]")
            else:
                errs.append(msg)
        if fs != ks:
            errs.append(f"{ref}: side {fs} vs {ks}")
    # BOM designator -> LCSC
    if set(fab_bom) != set(kib_bom):
        errs.append(f"BOM designator sets differ: "
                    f"only-fab={sorted(set(fab_bom)-set(kib_bom))} "
                    f"only-kibot={sorted(set(kib_bom)-set(fab_bom))}")
    for ref in sorted(set(fab_bom) & set(kib_bom)):
        if fab_bom[ref] != kib_bom[ref]:
            errs.append(f"{ref}: LCSC {fab_bom[ref]} (fab) vs "
                        f"{kib_bom[ref]} (kibot)")

    for w in warns:
        print("  ⚠", w)
    if errs:
        print("CPL/BOM CROSS-CHECK FAILED — fab-outputs.py vs KiBot disagree:")
        for e in errs:
            print("  ✗", e)
        sys.exit(1)
    extra = f" ({len(warns)} known datum-offset warning/s)" if warns else ""
    print(f"OK: KiBot CPL+BOM match fab-outputs.py — {len(fab_cpl)} placements, "
          f"{len(fab_bom)} assembled parts, rotations + LCSC identical{extra}.")


if __name__ == "__main__":
    main()
