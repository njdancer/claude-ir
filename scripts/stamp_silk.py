#!/usr/bin/env python3
"""Re-stamp the back-silk metadata git line from the CURRENT commit.

The silk metadata block carries one line: "<date>  git <hash>[-dirty]".
`pcb_silk.py` bakes that line when it regenerates the silk, which normally
happens on a *dirty* working tree (you're mid-edit), so it records "-dirty"
and the *parent* commit's hash. Every asset CI then renders from the committed
board therefore reads "dirty", which is misleading: the published board was
built from a clean, specific commit.

Fix: run this in CI on the clean checkout, right before rendering / fab
generation. The checkout is clean and at the build commit, so the stamp
becomes the exact build SHA with no "-dirty". It is a text-only edit of that
one line (no pcbnew needed), idempotent, and a no-op if the line is already
correct. Failures are non-fatal — a wrong cosmetic stamp must not break a
render or fab build.

Usage:
    python3 scripts/stamp_silk.py [path/to/board.kicad_pcb]
"""
import re
import subprocess
import sys

DEFAULT_PCB = "hardware/esp32-ir-remote.kicad_pcb"
# matches the gr_text the metadata block writes: "YYYY-MM-DD  git <hash>[-dirty]"
LINE_RE = re.compile(
    r'(\(gr_text ")\d{4}-\d{2}-\d{2}\s+git [0-9a-f]+(?:-dirty)?(")')


def _git(*args):
    # safe.directory=* dodges CI's "dubious ownership" guard (checkout user vs
    # the root-running KiCad container).
    return subprocess.check_output(
        ["git", "-c", "safe.directory=*", *args], text=True).strip()


def current_stamp():
    h = _git("rev-parse", "--short", "HEAD")
    date = _git("show", "-s", "--format=%cs", "HEAD")
    dirty = subprocess.call(
        ["git", "-c", "safe.directory=*", "diff", "--quiet"]) != 0
    return f"{date}  git {h}" + ("-dirty" if dirty else "")


def main():
    pcb = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PCB
    try:
        stamp = current_stamp()
    except Exception as e:  # noqa: BLE001 - never fail a build over the stamp
        print(f"stamp_silk: skipped (git unavailable: {e})", file=sys.stderr)
        return 0
    src = open(pcb, encoding="utf-8").read()
    new, n = LINE_RE.subn(lambda m: m.group(1) + stamp + m.group(2), src)
    if n == 0:
        print("stamp_silk: metadata git line not found — nothing stamped",
              file=sys.stderr)
        return 0
    if new != src:
        open(pcb, "w", encoding="utf-8").write(new)
    print(f"stamp_silk: {n} line -> {stamp}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
