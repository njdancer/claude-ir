#!/usr/bin/env python3
"""FreeRouting-based ROUTE stage (replaces pcb_router.py + pcb_finish.py).

WHY: the home-grown A* router + pcb_finish.py rip-up post-pass is greedy and
fixed-order, so on a congested 2-layer board one net always loses a contested
escape lane and the finisher mangles the route healing it (dangling stubs,
co-located vias, ripped neighbours). FreeRouting implements negotiated
congestion (PathFinder-style) rip-up-and-reroute as its core loop, so nets
negotiate shared resources instead of one being frozen out.

PROVEN (2026-06-15, this board, KiCad 10.0.3 + FreeRouting 2.2.4 / Java 25):
  export DSN -> FreeRouting -> import SES routes ALL 127 nets to 0 unrouted in
  ~11 s (pass1 12 unrouted -> pass2 4 -> pass3 0). No keepout intrusion, no
  dangling, no duplicate vias. The +3.3V/U3.1 escape that the old router could
  never place clean just routes.

WORKFLOW (this script orchestrates it; run AFTER place, the board having been
ripped clean of tracks/pours by pcb_rip.py — DSN must be pads+outline+nets+
keepouts only, NO pours, since KiCad exports pours as (plane ...) which would
constrain the router):

  1. pcbnew.ExportSpecctraDSN(board, board.dsn)         # headless BOARD* overload
  2. java -jar freerouting.jar --gui.enabled=false \\
       -de board.dsn -do board.ses -mp <N> -mt 1 -is sequential -us greedy
  3. validate board.ses is non-empty (FR emits 0-byte SES on failure)
  4. pcbnew.ImportSpecctraSES(board, board.ses)         # deletes+re-adds tracks
  5. SaveBoard, then pcb_pour.py (pour GND AFTER routing), ldo_pour, silk

DETERMINISM: FreeRouting v2.2.0+ made maze tie-breaking deterministic (no seed
needed for the routing pass). Pin the jar version, run single-threaded (-mt 1)
with -is sequential to kill optimizer randomness. VERIFY end-to-end by routing
twice and diffing the .ses; if not bit-identical, commit the .ses as a checked-
in artifact and have CI re-import+DRC instead of re-routing.

OPEN ITEMS before this fully replaces the old stage (see
hardware/notes/autorouting-freerouting.md):
  - USB pair lands on B.Cu (FR doesn't honour "F.Cu only"). Must constrain via
    a B.Cu keepout under the J2->module USB corridor, or per-net layer rules.
    Until then the USB SI regresses vs the old HARD_F router.
  - GND: we route signals then drop GND traces and pour GND. FR's signal layout
    can strand a GND pad whose pour patch has no B-via (seen: R1.2). Either keep
    FR's GND routing (but fix edge-clearance traces) or harden pcb_pour island
    tying. Don't blindly drop all GND traces.
  - Wire into CI: Java 25 + the pinned FreeRouting jar/Docker
    (ghcr.io/freerouting/freerouting:2.2.4) in the hardware job.

Env (this container): Java 25 at /tmp/fr/jdk-25*/bin/java, jar at
/tmp/fr/freerouting-2.2.4.jar. Run pcbnew bits with /tmp/kv10/bin/python.
"""
import os
import subprocess
import sys

PCB = "hardware/esp32-ir-remote.kicad_pcb"
DSN = "hardware/fab/board.dsn"
SES = "hardware/fab/board.ses"
FR_JAR = os.environ.get("FREEROUTING_JAR", "/tmp/fr/freerouting-2.2.4.jar")
JAVA = os.environ.get("JAVA25", "/tmp/fr/jdk-25.0.3+9-jre/bin/java")
MAX_PASSES = int(os.environ.get("FR_MAX_PASSES", "100"))


def export_dsn():
    import pcbnew
    b = pcbnew.LoadBoard(PCB)
    os.makedirs(os.path.dirname(DSN), exist_ok=True)
    if not pcbnew.ExportSpecctraDSN(b, DSN):
        sys.exit("DSN export failed")
    print(f"exported {DSN} ({os.path.getsize(DSN)} bytes)")


def run_freerouting():
    cmd = [JAVA, "-jar", FR_JAR, "--gui.enabled=false",
           "-de", DSN, "-do", SES,
           "-mp", str(MAX_PASSES), "-mt", "1", "-is", "sequential", "-us", "greedy", "-dl"]
    print("+ " + " ".join(cmd))
    subprocess.run(cmd, check=False)          # FR exit code is unreliable; gate on SES
    if not os.path.exists(SES) or os.path.getsize(SES) == 0:
        sys.exit("FreeRouting produced no/empty SES")
    print(f"routed -> {SES} ({os.path.getsize(SES)} bytes)")


def import_ses():
    import pcbnew
    if os.path.getsize(SES) == 0:
        sys.exit("empty SES")
    b = pcbnew.LoadBoard(PCB)
    if not pcbnew.ImportSpecctraSES(b, SES):
        sys.exit("SES import failed")
    # FreeRouting routes GND too (we keep it — dropping all GND traces strands
    # pads the pour can't reach where USB sits on B.Cu, e.g. R1.2). But it also
    # routes some GND right up to the board edge (copper_edge_clearance). Those
    # edge GND traces are redundant with the pour, so drop any GND track with an
    # endpoint within 0.55 mm of an edge; the pour grounds those pads.
    import pcbnew as _p
    X0, Y0, X1, Y1 = 106.0, 70.0, 198.0, 114.0
    drop = []
    for t in b.GetTracks():
        if t.GetClass() == "PCB_VIA" or t.GetNetname() != "GND":
            continue
        for p in (t.GetStart(), t.GetEnd()):
            x, y = _p.ToMM(p.x), _p.ToMM(p.y)
            if min(x - X0, X1 - x, y - Y0, Y1 - y) < 0.55:
                drop.append(t)
                break
    for t in drop:
        b.Remove(t)
    pcbnew.SaveBoard(PCB, b)
    print(f"imported SES into board (dropped {len(drop)} edge-hugging GND traces)")


if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else "all"
    if stage in ("export", "all"):
        export_dsn()
    if stage in ("route", "all"):
        run_freerouting()
    if stage in ("import", "all"):
        import_ses()
