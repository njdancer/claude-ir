#!/usr/bin/env python3
"""Assemble the sticky PR comment from CI facts + renders.

Inputs are all OPTIONAL — every section degrades to a "—" row if its facts
file is missing, so the comment job posts something useful even when an
upstream job failed. Reuses the sexp parser + netlist helpers from
hardware_validate so there is one source of truth for board parsing.

  hardware-facts.json   {erc, drc, netlist, bom}  (hardware_validate --json)
  bom-report.json       {totals, lines}           (bom_report.py --json)
  firmware-facts.json   {envs: {env: {flash_*, ram_*}}}
  app-facts.json        {tests, client_bytes}
  the .kicad_pcb         board outline (Edge.Cuts bbox) + copper layer count

Usage:
  python3 scripts/ci/pr_report.py \
      --pcb hardware/esp32-ir-remote.kicad_pcb \
      --hardware hw.json --bom bom.json --firmware fw.json --app app.json \
      --renders-url https://raw.../pr-12 --sha abc123 --run-url https://...
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hardware_validate import sexp_parse, walk  # noqa: E402

HEADER = "pr-board-report"  # sticky-comment key; keep in sync with the workflow


def load(path):
    if path and os.path.exists(path):
        try:
            return json.load(open(path))
        except (json.JSONDecodeError, OSError):
            return None
    return None


def ok(flag):
    return "✅" if flag else "❌"


def human_bytes(n):
    if n is None:
        return "—"
    if n < 1024:
        return f"{n} B"
    if n < 1024 ** 2:
        return f"{n / 1024:.1f} KB"
    return f"{n / 1024 ** 2:.1f} MB"


def kb(n):
    return "—" if n is None else f"{n / 1024:.0f} KB"


# --------------------------------------------------------------------------
# Board geometry straight from the PCB (Edge.Cuts bbox + copper layer count)
# --------------------------------------------------------------------------

def _coords_on_edge_cuts(node, out):
    """Recursively collect (x, y) points from graphics on Edge.Cuts."""
    if not isinstance(node, list):
        return
    is_graphic = node and node[0] in (
        "gr_line", "gr_rect", "gr_arc", "gr_circle", "gr_poly", "gr_curve")
    on_edge = any(
        isinstance(c, list) and c[0] == "layer" and "Edge.Cuts" in c[1:]
        for c in node)
    if is_graphic and on_edge:
        for c in node:
            if isinstance(c, list) and c[0] in (
                    "start", "end", "center", "mid", "xy"):
                try:
                    out.append((float(c[1]), float(c[2])))
                except (ValueError, IndexError):
                    pass
    for c in node:
        _coords_on_edge_cuts(c, out)


def board_geometry(pcb_path):
    if not pcb_path or not os.path.exists(pcb_path):
        return None
    root = sexp_parse(open(pcb_path).read())
    pts = []
    _coords_on_edge_cuts(root, pts)
    copper = 0
    for ls in walk(root, "layers"):
        for layer in ls:
            if isinstance(layer, list) and len(layer) > 1 and \
                    isinstance(layer[1], str) and layer[1].endswith(".Cu"):
                copper += 1
        break
    if not pts:
        return {"copper_layers": copper or None}
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    w = max(xs) - min(xs)
    h = max(ys) - min(ys)
    return {"width_mm": round(w, 1), "height_mm": round(h, 1),
            "area_cm2": round(w * h / 100, 1), "copper_layers": copper or None}


# --------------------------------------------------------------------------
# Section builders
# --------------------------------------------------------------------------

def section_renders(url, sha):
    if not url:
        return ["### 🛰️ Board preview",
                "_Renders unavailable for this run "
                "(see the `fab-package` workflow artifact)._", ""]
    bust = f"?{sha[:12]}" if sha else ""
    cells = " | ".join(
        f"![{name}]({url}/{name}.png{bust})" for name in ("top", "bottom", "iso"))
    return ["### 🛰️ Board preview",
            "| top | bottom | iso (3D) |",
            "|---|---|---|",
            f"| {cells} |", ""]


def section_hardware(hw, geo):
    out = ["### 🔌 Hardware"]
    if not hw and not geo:
        out += ["_No hardware facts (the `hardware` job did not produce them)._", ""]
        return out
    rows = ["| check | result | detail |", "|---|---|---|"]
    if hw and "erc" in hw:
        c = ", ".join(f"{k}={v}" for k, v in (hw["erc"]["counts"] or {}).items())
        rows.append(f"| ERC vs baseline | {ok(hw['erc']['pass'])} | "
                    f"`{c or 'clean'}` |")
    if hw and "drc" in hw:
        d = hw["drc"]
        c = ", ".join(f"{k}={v}" for k, v in (d["counts"] or {}).items())
        rows.append(f"| DRC vs baseline | {ok(d['pass'])} | "
                    f"`{c or 'clean'}`, unconnected={d['unconnected']}, "
                    f"parity={d['parity']} |")
    if geo and geo.get("width_mm"):
        rows.append(f"| Board outline | 📐 | {geo['width_mm']} × "
                    f"{geo['height_mm']} mm ({geo['area_cm2']} cm²), "
                    f"{geo.get('copper_layers', '?')} copper layers |")
    if hw and "netlist" in hw:
        n = hw["netlist"]
        rows.append(f"| Netlist | {ok(n['fresh'])} | {n['components']} "
                    f"components, {n['nets']} nets, "
                    f"{'fresh' if n['fresh'] else 'STALE'} |")
    if hw and "bom" in hw:
        b = hw["bom"]
        miss = b["missing"]
        rows.append(f"| BOM LCSC coverage | {ok(not miss)} | {b['fitted']} "
                    f"fitted parts, {len(miss)} missing |")
    out += rows + [""]
    return out


def section_bom(bom):
    out = ["### 💸 BOM cost & stock"]
    if not bom or "totals" not in bom:
        out += ["_No BOM telemetry (non-gating `bom-report` job; may be "
                "rate-limited)._", ""]
        return out
    t = bom["totals"]
    low = t.get("low_stock_lines", 0)
    boards = bom.get("boards", "?")
    out += [
        f"- **${t.get('parts_usd_per_board', '?')}/board** "
        f"(${t.get('parts_usd', '?')} for {boards} boards)",
        f"- {t.get('extended_smt_lines', '?')} Extended SMT lines "
        f"(~${t.get('extended_fees_usd', 0):.0f} loading fees)",
        f"- low-stock lines: {low} {'⚠️' if low else '✅'}",
        ""]
    return out


def section_firmware(fw):
    out = ["### 📟 Firmware size"]
    envs = (fw or {}).get("envs") or {}
    if not envs:
        out += ["_No firmware size facts (the `firmware` job did not produce "
                "them)._", ""]
        return out
    rows = ["| env | flash | ram |", "|---|---|---|"]
    for env, m in envs.items():
        flash = (f"{m['flash_pct']:.1f}% ({kb(m['flash_used'])})"
                 if "flash_pct" in m else "—")
        ram = (f"{m['ram_pct']:.1f}% ({kb(m['ram_used'])})"
               if "ram_pct" in m else "—")
        rows.append(f"| `{env}` | {flash} | {ram} |")
    out += rows + [""]
    return out


def section_app(app):
    out = ["### 🖥️ App"]
    if not app:
        out += ["_No app facts (the `app` job did not produce them)._", ""]
        return out
    t = app.get("tests") or {}
    passed, failed = t.get("passed"), t.get("failed")
    if passed is None:
        tline = "unit tests: —"
    else:
        tline = (f"unit tests: {passed} passed"
                 + (f", {failed} failed ❌" if failed else " ✅"))
    out += [f"- {tline}",
            f"- client bundle: {human_bytes(app.get('client_bytes'))}", ""]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pcb")
    ap.add_argument("--hardware")
    ap.add_argument("--bom")
    ap.add_argument("--firmware")
    ap.add_argument("--app")
    ap.add_argument("--renders-url")
    ap.add_argument("--sha", default="")
    ap.add_argument("--run-url")
    a = ap.parse_args()

    hw = load(a.hardware)
    bom = load(a.bom)
    fw = load(a.firmware)
    app = load(a.app)
    geo = board_geometry(a.pcb)

    md = [f"<!-- {HEADER} -->",
          "## 📋 Board PR report", ""]
    md += section_renders(a.renders_url, a.sha)
    md += section_hardware(hw, geo)
    md += section_bom(bom)
    md += section_firmware(fw)
    md += section_app(app)

    foot = "<sub>Auto-generated by CI"
    if a.sha:
        foot += f" · commit `{a.sha[:12]}`"
    if a.run_url:
        foot += f" · [run log]({a.run_url})"
    foot += ". The full fab package is the `fab-package` workflow artifact.</sub>"
    md += ["---", foot]

    sys.stdout.write("\n".join(md) + "\n")


if __name__ == "__main__":
    main()
