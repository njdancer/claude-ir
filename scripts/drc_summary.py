#!/usr/bin/env python3
"""Run DRC via kicad-cli and summarize violations by type.

Usage: python3 scripts/drc_summary.py [--full]
"""
import json
import subprocess
import sys
from collections import Counter

KCLI = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
BOARD = "hardware/esp32-ir-remote.kicad_pcb"
OUT = "/tmp/drc.json"

subprocess.run([KCLI, "pcb", "drc", "--format", "json", "--severity-all",
                "-o", OUT, BOARD], check=True, capture_output=True)
rep = json.load(open(OUT))
viol = rep.get("violations", [])
unconn = rep.get("unconnected_items", [])
parity = rep.get("schematic_parity", [])

by_type = Counter(v["type"] for v in viol)
by_sev = Counter(v["severity"] for v in viol)
print(f"violations: {len(viol)}  (by severity: {dict(by_sev)})")
for t, n in by_type.most_common():
    print(f"  {n:4d}  {t}")
print(f"unconnected items: {len(unconn)}")
for u in unconn[:15]:
    d = u.get("description", "")
    print("   ", d[:110])
if len(unconn) > 15:
    print(f"    ... +{len(unconn)-15} more")
print(f"schematic parity issues: {len(parity)}")

if "--full" in sys.argv:
    for v in viol:
        print(v["severity"], v["type"], v.get("description", "")[:120])
        for it in v.get("items", []):
            print("     @", it.get("description", "")[:100])
