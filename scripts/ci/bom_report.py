#!/usr/bin/env python3
"""BOM cost & stock report — CI telemetry, like coverage but for dollars.

Reads the committed netlist, groups fitted parts by LCSC code, queries
JLCPCB's public component endpoint for live price tiers / stock /
Basic-vs-Extended status, and emits:

  - a markdown table (stdout + $GITHUB_STEP_SUMMARY when set)
  - --json PATH   machine-readable report (archived as a CI artifact /
                  published on the Pages site, so cost history is one
                  `git log` + artifact walk away)
  - --html PATH   standalone HTML page for the Pages site

Non-gating by design: prices and stock move on their own; the report exits
0 unless every single lookup failed (exit 3 — usually means the endpoint
or network policy changed). Low-stock lines are WARNed, not failed —
they matter when ordering, not on every refactor PR.

Usage: python3 scripts/ci/bom_report.py [--boards N] [--json P] [--html P]
"""

import importlib.util
import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
NET = os.path.join(ROOT, "hardware", "esp32-ir-remote.net")

sys.path.insert(0, HERE)
from hardware_validate import netlist_fields  # noqa: E402

API = ("https://cart.jlcpcb.com/shoppingCart/smtGood/getComponentDetail"
       "?componentCode=%s")

# Loading fee JLCPCB charges per Extended line on the assembly BOM.
EXTENDED_FEE_USD = 3.0


def hand_solder_refs():
    """The assembly split lives in scripts/fab-outputs.py — import it."""
    spec = importlib.util.spec_from_file_location(
        "fab_outputs", os.path.join(ROOT, "scripts", "fab-outputs.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return set(mod.HAND_SOLDER), set(mod.NEVER_PLACE)


def fetch(code):
    req = urllib.request.Request(API % code, headers={
        "User-Agent": "claude-ir-ci/1.0 (+https://github.com/njdancer/claude-ir)"})
    for attempt in (1, 2):
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                data = json.load(r)
            return data.get("data") or {}
        except Exception as e:  # noqa: BLE001 — best-effort telemetry
            if attempt == 2:
                print(f"  WARN: {code}: {e}", file=sys.stderr)
                return None
            time.sleep(2)


def price_at(tiers, qty):
    best = None
    for t in tiers or []:
        lo = t.get("startNumber") or 1
        hi = t.get("endNumber") or 10**9
        if hi < 0:
            hi = 10**9
        if lo <= qty <= hi:
            return t.get("productPrice")
        if best is None or lo < (best.get("startNumber") or 1):
            best = t
    return best.get("productPrice") if best else None


def main():
    args = sys.argv[1:]

    def opt(name, default=None):
        return args[args.index(name) + 1] if name in args else default

    boards = int(opt("--boards", "5"))
    hand, never = hand_solder_refs()
    comps = netlist_fields(NET)

    groups = {}  # lcsc -> {refs, value, kit}
    skipped = []
    for ref, c in sorted(comps.items()):
        if c["dnp"] or ref in never:
            continue
        code = c["fields"].get("LCSC")
        if not code:
            skipped.append(ref)
            continue
        g = groups.setdefault(code, {"refs": [], "value": c["value"]})
        g["refs"].append(ref)

    def assembly(refs):
        in_kit = sum(1 for r in refs if r in hand)
        return "kit" if in_kit == len(refs) else ("smt" if not in_kit else "mixed")

    print(f"BOM report: {len(groups)} LCSC lines, {boards} board(s); "
          f"no-code parts skipped: {', '.join(skipped) or 'none'}\n")

    lines, failed = [], []
    for code, g in sorted(groups.items(), key=lambda kv: kv[1]["refs"][0]):
        d = fetch(code)
        time.sleep(0.4)
        if d is None:
            failed.append(code)
            lines.append({"lcsc": code, "value": g["value"], "refs": g["refs"],
                          "qty_per_board": len(g["refs"]), "error": "lookup failed"})
            continue
        qty = len(g["refs"]) * boards
        unit = price_at(d.get("prices"), max(qty, 1))
        stock = d.get("stockCount") or 0
        lines.append({
            "lcsc": code,
            "value": g["value"],
            "mfr": d.get("componentModelEn") or "",
            "refs": g["refs"],
            "qty_per_board": len(g["refs"]),
            "assembly": assembly(g["refs"]),
            "library": d.get("componentLibraryType") or "?",  # base|expand
            "unit_usd": unit,
            "line_usd": round(unit * qty, 4) if unit is not None else None,
            "stock": stock,
            "low_stock": stock < max(100, 10 * qty),
        })

    if failed and len(failed) == len(groups):
        print("ERROR: every JLCPCB lookup failed — endpoint or network issue",
              file=sys.stderr)
        return 3

    parts_total = sum(l["line_usd"] or 0 for l in lines)
    ext_smt = [l for l in lines
               if l.get("library") == "expand" and l.get("assembly") == "smt"]
    low = [l for l in lines if l.get("low_stock")]
    report = {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "commit": os.environ.get("GITHUB_SHA", ""),
        "boards": boards,
        "lines": lines,
        "lookup_failures": failed,
        "totals": {
            "parts_usd": round(parts_total, 2),
            "parts_usd_per_board": round(parts_total / boards, 2),
            "extended_smt_lines": len(ext_smt),
            "extended_fees_usd": len(ext_smt) * EXTENDED_FEE_USD,
            "low_stock_lines": len(low),
        },
    }

    md = [f"## BOM cost & stock ({boards} boards)",
          "",
          f"**Parts: ${report['totals']['parts_usd']}** "
          f"(${report['totals']['parts_usd_per_board']}/board) — "
          f"{len(ext_smt)} Extended SMT lines "
          f"(~${report['totals']['extended_fees_usd']:.0f} loading fees)"
          + (f" — **{len(low)} LOW-STOCK lines**" if low else ""),
          "",
          "| LCSC | part | refs | asm | lib | unit $ | line $ | stock |",
          "|---|---|---|---|---|---|---|---|"]
    for l in lines:
        if "error" in l:
            md.append(f"| {l['lcsc']} | {l['value']} | {len(l['refs'])} |  |  "
                      f"| — | — | lookup failed |")
            continue
        stock = f"**{l['stock']} ⚠️**" if l["low_stock"] else str(l["stock"])
        md.append(f"| {l['lcsc']} | {l['value']} | {l['qty_per_board']} "
                  f"| {l['assembly']} | {l['library']} "
                  f"| {l['unit_usd']} | {l['line_usd']} | {stock} |")
    md_text = "\n".join(md) + "\n"
    print(md_text)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as f:
            f.write(md_text)

    if opt("--json"):
        with open(opt("--json"), "w") as f:
            json.dump(report, f, indent=1)
    if opt("--html"):
        rows = md_text.split("\n")
        body = "\n".join(f"<tr>{''.join(f'<td>{c.strip()}</td>' for c in r.strip('|').split('|'))}</tr>"
                         for r in rows if r.startswith("|") and "---" not in r)
        with open(opt("--html"), "w") as f:
            f.write(f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>BOM cost &amp; stock — claude-ir</title>
<style>body{{font-family:system-ui,sans-serif;max-width:60rem;margin:2rem auto;padding:0 1rem}}
table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #ccc;padding:.3em .5em;font-size:.9rem}}
tr:first-child{{font-weight:bold;background:#f4f4f4}}</style></head><body>
<h1>BOM cost &amp; stock</h1>
<p>Parts <b>${report['totals']['parts_usd']}</b> for {boards} boards
(${report['totals']['parts_usd_per_board']}/board) ·
{len(ext_smt)} Extended SMT lines (~${report['totals']['extended_fees_usd']:.0f} fees) ·
{len(low)} low-stock lines · generated {report['generated']}
from commit <code>{report['commit'][:9]}</code> ·
<a href="bom-report.json">JSON</a></p>
<table>{body}</table></body></html>""")

    for l in low:
        print(f"WARN low stock: {l['lcsc']} {l['value']} — {l['stock']} left "
              f"(need {l['qty_per_board'] * boards})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
