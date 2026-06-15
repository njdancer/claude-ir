#!/usr/bin/env python3
"""CI validation suite for the KiCad board design.

Checks (all gating unless marked):
  erc      ERC violations vs the committed baseline
  netlist  committed hardware/*.net is electrically fresh (partition check
           against a netlist exported from the schematic right now)
  drc      DRC violations vs baseline; unconnected items and schematic
           parity must match baseline exactly (expected: zero)
  bom      every fitted component carries an LCSC field (allowlist for
           generic pin headers / solder jumpers)
  models   every footprint 3D model path resolves (WARN-only: SW1/SW2
           STEP models are a known cosmetic debt)

Baseline (hardware/ci-baseline.json) stores (severity, type) violation counts.
ERROR-severity changes gate strictly (any change fails); unconnected and
schematic-parity counts gate exactly (both version-stable). WARNING-severity
count changes (lib_footprint_mismatch, silk_edge_clearance, lib_symbol_mismatch)
are INFORMATIONAL only — these are KiCad geometry/library heuristics that drift
between patch releases (10.0.2 vs 10.0.3), so gating their exact counts produced
spurious CI failures. KiBot owns the ERC/DRC error gate in CI; the real-error
and parity/unconnected gates here are version-stable.

Usage:
  python3 scripts/ci/hardware_validate.py                  # validate
  python3 scripts/ci/hardware_validate.py --update-baseline
  python3 scripts/ci/hardware_validate.py --json facts.json  # PR-comment rollup
  KICAD_CLI=/path/to/kicad-cli ...                         # override CLI

Exit codes: 0 ok, 1 violations/diffs found, 2 baseline missing (candidate
baseline printed between BEGIN/END markers for bootstrap).
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HW = os.path.join(ROOT, "hardware")
SCH = os.path.join(HW, "esp32-ir-remote.kicad_sch")
PCB = os.path.join(HW, "esp32-ir-remote.kicad_pcb")
NET = os.path.join(HW, "esp32-ir-remote.net")
BASELINE = os.path.join(HW, "ci-baseline.json")

# Fitted parts allowed to have no LCSC code: generic 2.54mm headers bought
# anywhere (J4/J5). (The JP1 LDO-disconnect jumper was removed in the
# single-supply simplification — see U1 in the polarity table below.)
NO_LCSC_OK = {"J4", "J5"}

# ---------------------------------------------------------------------------
# Polarity / orientation truth table — pin -> net for every polarized or
# orientation-critical part. Rebuilt for board v2 (ESP32-C3 redesign,
# 2026-06-14) and cross-checked against scripts/ci/golden_netlist_v2.py, which
# independently verifies the full intended connectivity. A value is either a
# net name (power rails — leading '/' ignored) or a list of partner nodes
# "REF.PIN" that must share the pin's net (signal nets, name-agnostic so it
# survives dual-label / KiCad-version net renames). ANY future edit that flips
# a diode, swaps a transistor pinout, or rewires a power pin fails CI loudly.
# Re-derive consciously, never blindly: each line encodes a datasheet fact.
POLARITY = {
    # TVS on +5V rail (SMB): pad 1 = cathode = silk band = +5V, anode = GND
    "D1": {"1": "+5V", "2": "GND"},
    # IR LEDs (TSAL6200): pad 1 = cathode -> Q3 drain (IR_DRAIN, shared with
    # the other three + J5.2); pad 2 = anode via its own 22R series resistor
    "D2": {"1": ["Q3.3", "D3.1"], "2": ["R9.1"]},
    "D3": {"1": ["Q3.3", "D2.1"], "2": ["R10.1"]},
    "D4": {"1": ["Q3.3", "D5.1"], "2": ["R11.1"]},
    "D5": {"1": ["Q3.3", "D4.1"], "2": ["R12.1"]},
    # System indicator LEDs (0805): pad 1 = cathode = GND, pad 2 = anode via R
    "D6": {"1": "GND", "2": ["R15.2"]},    # +5V power
    "D7": {"1": "GND", "2": ["R16.2"]},    # +3V3 power
    "D10": {"1": "GND", "2": ["R19.2"]},   # IR-TX activity
    # User LEDs (0805), DIRECT GPIO drive (no FET in v2): pad 1 = cathode =
    # GND, pad 2 = anode via R to the GPIO
    "D11": {"1": "GND", "2": ["R25.2"]},   # USER_LED1 (IO3 via R25)
    "D12": {"1": "GND", "2": ["R20.1"]},   # USER_LED2 (IO4 via R20)
    # IR driver AO3400A (SOT-23: 1=G 2=S 3=D): gate via R13 (+R14 pulldown),
    # source = GND, drain = IR_DRAIN (the IR-LED cathode bus)
    "Q3": {"1": ["R13.1", "R14.2"], "2": "GND", "3": ["D2.1", "D5.1"]},
    # AMS1117-3.3 LDO (SOT-223-3, TabPin2): 1=GND 2=VOUT=+3V3 3=VIN(+5V). Tab
    # (pin2 region) = VOUT, which now drives the +3.3V rail directly — the JP1
    # LDO-disconnect jumper was removed (single supply; desolder U1 to inject).
    "U1": {"1": "GND", "2": "+3.3V", "3": "+5V"},
    # TSOP38238 IR receiver (1=OUT 2=GND 3=Vs): OUT -> C3 IO6 (IR_RX),
    # Vs RC-filtered (IR_RX_VS = C9.1 + R27.2)
    "U4": {"1": ["U3.5"], "2": "GND", "3": ["C9.1", "R27.2"]},
    # AHT20 temp/humidity (DFN-6: 2=VDD 3=SCL 4=SDA 5=GND, 1/6 NC). SCL/SDA
    # confirmed by their pull-ups (R29=SCL, R28=SDA).
    "U5": {"2": "+3.3V", "3": ["R29.2"], "4": ["R28.2"], "5": "GND"},
    # Input fuse: pad 1 = +5V (post-fuse rail), pad 2 = VBUS from the USB-C
    "F1": {"1": "+5V", "2": ["J2.A4", "J2.A9"]},
    # USB-C receptacle (SMD XKB U262-16XN). Locks the new footprint's pinout:
    # VBUS A4/A9, CC1 A5->R1, CC2 B5->R2, D+ A6/B6 -> C3 IO19 (pin14),
    # D- A7/B7 -> C3 IO18 (pin13), GND on A1/A12/B1/B12/S1.
    "J2": {"A4": ["F1.2"], "A5": ["R1.1"], "B5": ["R2.2"],
           "A6": ["U3.14", "J2.B6"], "A7": ["U3.13", "J2.B7"],
           "A1": "GND", "A12": "GND", "S1": "GND"},
}

failures = []  # list of (check, message)
warnings = []
summary_rows = []  # (check, status, detail) for the GitHub step summary
facts = {}  # machine-readable rollup for the PR comment (--json)


def find_kicad_cli():
    if os.environ.get("KICAD_CLI"):
        return os.environ["KICAD_CLI"]
    mac = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
    if os.path.exists(mac):
        return mac
    return shutil.which("kicad-cli") or sys.exit("kicad-cli not found")


KCLI = None  # resolved lazily so the parser half is importable without KiCad


def run_cli(*args):
    global KCLI
    if KCLI is None:
        KCLI = find_kicad_cli()
    cmd = [KCLI] + list(args)
    print("  $", " ".join(cmd))
    # ERC/DRC exit nonzero on violations with --exit-code-violations; we
    # don't pass that flag, but be tolerant anyway and inspect the JSON.
    subprocess.run(cmd, check=False, cwd=HW,
                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


# --------------------------------------------------------------------------
# Tiny s-expression parser (for netlist partition comparison)
# --------------------------------------------------------------------------

def sexp_parse(text):
    toks = re.findall(r'"(?:[^"\\]|\\.)*"|[()]|[^\s()"]+', text)
    pos = 0

    def parse():
        nonlocal pos
        tok = toks[pos]
        pos += 1
        if tok == "(":
            out = []
            while toks[pos] != ")":
                out.append(parse())
            pos += 1
            return out
        if tok.startswith('"'):
            return tok[1:-1].replace('\\"', '"').replace("\\\\", "\\")
        return tok

    return parse()


def walk(node, name):
    """Yield child lists whose head is `name`."""
    for c in node:
        if isinstance(c, list) and c and c[0] == name:
            yield c


def netlist_model(path):
    """Return (partition, components) — partition is a set of frozensets of
    (ref, pin) nodes (net names deliberately ignored: dual labels / KiCad
    version differences rename nets without electrical meaning), components
    maps ref -> (value, footprint)."""
    root = sexp_parse(open(path).read())
    comps = {}
    for comp in walk(next(walk(root, "components")), "comp"):
        kv = {c[0]: (c[1] if len(c) > 1 else "") for c in comp if isinstance(c, list)}
        comps[kv["ref"]] = (kv.get("value", ""), kv.get("footprint", ""))
    partition = set()
    netnames = {}
    for net in walk(next(walk(root, "nets")), "net"):
        kv = {c[0]: c[1:] for c in net if isinstance(c, list)}
        nodes = frozenset(
            (n[1][1], next(x[1] for x in n if isinstance(x, list) and x[0] == "pin"))
            for n in walk(net, "node")
        )
        if nodes:
            partition.add(nodes)
            netnames[nodes] = kv.get("name", ["?"])[0]
    return partition, comps, netnames


def netlist_fields(path):
    """ref -> dict of fields (incl. LCSC) + dnp flag, from netlist sexp."""
    root = sexp_parse(open(path).read())
    out = {}
    for comp in walk(next(walk(root, "components")), "comp"):
        ref = next(walk(comp, "ref"))[1]
        fields = {}
        for fl in walk(comp, "fields"):
            for f in walk(fl, "field"):
                fname = next(walk(f, "name"))[1]
                fields[fname] = f[-1] if isinstance(f[-1], str) else ""
        dnp = any(
            next(walk(p, "name"))[1] == "dnp"
            for p in walk(comp, "property")
            if any(True for _ in walk(p, "name"))
        )
        val = next(walk(comp, "value"), [None, ""])[1]
        out[ref] = {"fields": fields, "dnp": dnp, "value": val}
    return out


# --------------------------------------------------------------------------
# Violation counting + baseline comparison
# --------------------------------------------------------------------------

def count_violations(violations):
    c = Counter()
    for v in violations:
        if v.get("excluded") or v.get("severity") == "exclusion":
            continue
        c[(v["severity"], v["type"])] += 1
    return c


def counts_to_json(counter):
    return {f"{sev}:{typ}": n for (sev, typ), n in sorted(counter.items())}


def json_to_counts(d):
    return Counter({tuple(k.split(":", 1)): v for k, v in d.items()})


def compare(check, actual, base):
    """Errors fail on any change. Warning-count changes are INFORMATIONAL only.

    Warning categories (lib_footprint_mismatch, silk_edge_clearance,
    lib_symbol_mismatch) are computed by KiCad geometry/library heuristics that
    drift between patch releases (10.0.2 vs 10.0.3), so gating on their exact
    counts caused spurious CI failures. KiBot now owns the ERC/DRC error gate
    (CI), and parity/unconnected (version-stable) are still gated below — so
    benign warning drift no longer needs to fail the build.
    """
    ok = True
    keys = set(actual) | set(base)
    for key in sorted(keys):
        sev, typ = key
        a, b = actual.get(key, 0), base.get(key, 0)
        if a == b:
            continue
        if sev == "error":
            failures.append((check, f"{sev}:{typ} count {b} -> {a}"))
            ok = False
        else:
            warnings.append((check, f"{sev}:{typ} {b} -> {a} (warning drift, "
                             "informational; refresh baseline if persistent)"))
    return ok


def details(violations, sev_type=None):
    for v in violations:
        if v.get("excluded") or v.get("severity") == "exclusion":
            continue
        if sev_type and (v["severity"], v["type"]) != sev_type:
            continue
        print(f"    [{v['severity']}] {v['type']}: {v.get('description','')[:140]}")


# --------------------------------------------------------------------------
# Checks
# --------------------------------------------------------------------------

def check_erc(tmp):
    print("\n== ERC ==")
    out = os.path.join(tmp, "erc.json")
    run_cli("sch", "erc", "--format", "json", "--severity-all", "-o", out, SCH)
    rep = json.load(open(out))
    viol = [v for sheet in rep.get("sheets", []) for v in sheet.get("violations", [])]
    counts = count_violations(viol)
    print("  counts:", dict(counts_to_json(counts)))
    details(viol)
    return {"erc": counts_to_json(counts)}, viol


def parity_is_noise(desc):
    """Parity classes with no electrical meaning:
    - empty-vs-'~' Datasheet field normalization (KiCad 10 reading v9)
    - root-sheet net-name prefix: PCB 'ESP_EN' vs schematic '/ESP_EN'
    - custom fields (LCSC etc.) not copied into footprints — cosmetic;
      BOM/fab outputs read fields from the netlist, and the BOM lint
      gates LCSC coverage there"""
    if re.fullmatch(r"Field 'Datasheet' differs \(PCB: '~', Schematic: ''\)",
                    desc):
        return True
    if re.fullmatch(r"Missing symbol field '[^']*' in footprint", desc):
        return True
    m = re.fullmatch(r"Pad net \(([^)]*)\) doesn't match net given by "
                     r"schematic \(([^)]*)\)", desc)
    if m and m.group(2).lstrip("/") == m.group(1).lstrip("/"):
        return True
    return False


def check_drc(tmp):
    print("\n== DRC (incl. schematic parity) ==")
    out = os.path.join(tmp, "drc.json")
    run_cli("pcb", "drc", "--format", "json", "--severity-all",
            "--schematic-parity", "-o", out, PCB)
    rep = json.load(open(out))
    viol = rep.get("violations", [])
    unconn = [v for v in rep.get("unconnected_items", [])
              if not v.get("excluded") and v.get("severity") != "exclusion"]
    parity_all = [v for v in rep.get("schematic_parity", [])
                  if not v.get("excluded") and v.get("severity") != "exclusion"]
    parity = [v for v in parity_all
              if not parity_is_noise(v.get("description", ""))]
    n_noise = len(parity_all) - len(parity)
    if n_noise:
        print(f"  parity noise filtered: {n_noise} "
              "(Datasheet ''/'~' + net-name '/'-prefix artifacts)")
    counts = count_violations(viol)
    print("  violation counts:", dict(counts_to_json(counts)))
    print(f"  unconnected items: {len(unconn)}   schematic parity: {len(parity)}")
    for v in unconn[:10]:
        print("    unconnected:", v.get("description", "")[:120])
    for v in parity[:10]:
        print("    parity:", v.get("description", "")[:120])
    return ({"drc": counts_to_json(counts),
             "drc_unconnected": len(unconn),
             "drc_parity": len(parity)}, viol, unconn, parity)


def check_netlist(tmp):
    """Regenerate the netlist and compare ELECTRICALLY with the committed
    one: same component set (value+footprint) and same pad partition."""
    print("\n== Netlist freshness (partition check) ==")
    fresh = os.path.join(tmp, "fresh.net")
    run_cli("sch", "export", "netlist", "--format", "kicadsexpr", "-o", fresh, SCH)
    ok = True
    fp, fc, fn = netlist_model(fresh)
    cp, cc, cn = netlist_model(NET)
    for ref in sorted(set(fc) | set(cc)):
        if fc.get(ref) != cc.get(ref):
            failures.append(("netlist", f"component {ref}: committed "
                             f"{cc.get(ref)} vs schematic {fc.get(ref)}"))
            ok = False
    only_fresh = fp - cp
    only_comm = cp - fp
    for nets, label in ((only_fresh, "in schematic, missing from committed"),
                        (only_comm, "in committed, missing from schematic")):
        for n in sorted(nets, key=lambda s: sorted(s)):
            name = (fn.get(n) or cn.get(n) or "?")
            failures.append(("netlist", f"net '{name}' {label}: "
                             + ",".join(f"{r}.{p}" for r, p in sorted(n))))
            ok = False
    if ok:
        print(f"  OK: {len(cc)} components, {len(cp)} nets — committed netlist"
              " is electrically identical to the schematic")
    facts["netlist"] = {"components": len(cc), "nets": len(cp), "fresh": ok}
    summary_rows.append(("netlist freshness", "PASS" if ok else "FAIL",
                         f"{len(fc)} comps / {len(fp)} nets"))
    return fresh


def check_bom(fresh_net):
    print("\n== BOM lint (LCSC coverage) ==")
    comps = netlist_fields(fresh_net)
    missing = []
    for ref, c in sorted(comps.items()):
        if c["dnp"] or ref in NO_LCSC_OK:
            continue
        if not c["fields"].get("LCSC"):
            missing.append(f"{ref} ({c['value']})")
    n_fitted = sum(1 for c in comps.values() if not c["dnp"])
    if missing:
        failures.append(("bom", "fitted parts without LCSC field: "
                         + ", ".join(missing)))
    else:
        print(f"  OK: all {n_fitted} fitted parts have LCSC codes"
              f" (allowlisted: {', '.join(sorted(NO_LCSC_OK))})")
    facts["bom"] = {"fitted": n_fitted, "missing": missing}
    summary_rows.append(("BOM LCSC coverage", "FAIL" if missing else "PASS",
                         f"{len(missing)} missing"))


def check_polarity(fresh_net):
    """Verify every POLARITY table entry against the freshly exported
    netlist: named nets by name (leading '/' ignored), auto-named nets by
    partner nodes sharing the net."""
    print("\n== Polarity / orientation truth table ==")
    root = sexp_parse(open(fresh_net).read())
    pin_net = {}   # (ref, pin) -> net name
    net_nodes = {}  # net name -> set of (ref, pin)
    for net in walk(next(walk(root, "nets")), "net"):
        name = next(c[1] for c in net if isinstance(c, list) and c[0] == "name")
        nodes = {(n[1][1], next(x[1] for x in n
                                if isinstance(x, list) and x[0] == "pin"))
                 for n in walk(net, "node")}
        net_nodes[name] = nodes
        for node in nodes:
            pin_net[node] = name
    bad = 0
    for ref, pinmap in POLARITY.items():
        for pin, expect in pinmap.items():
            actual = pin_net.get((ref, pin))
            if actual is None:
                failures.append(("polarity", f"{ref}.{pin}: pin missing from"
                                 " netlist"))
                bad += 1
                continue
            if isinstance(expect, str):
                if actual.lstrip("/") != expect.lstrip("/"):
                    failures.append(("polarity", f"{ref}.{pin}: on net "
                                     f"'{actual}', expected '{expect}'"))
                    bad += 1
            else:
                nodes = net_nodes[actual]
                missing = [p for p in expect
                           if tuple(p.split(".")) not in nodes]
                if missing:
                    failures.append(("polarity", f"{ref}.{pin}: net "
                                     f"'{actual}' lacks expected partner(s) "
                                     + ", ".join(missing)))
                    bad += 1
    n = sum(len(v) for v in POLARITY.values())
    if not bad:
        print(f"  OK: {n} pin->net invariants hold across "
              f"{len(POLARITY)} polarized parts")
    summary_rows.append(("polarity truth table", "FAIL" if bad else "PASS",
                         f"{n} invariants / {len(POLARITY)} parts"))


# KiCad page sizes (landscape mm). The schematic plotter crops to the sheet,
# so a symbol parked beyond these extents silently vanishes from the exported
# PDF/SVG while staying electrically valid (wired by net labels) — ERC has no
# rule for it. That's exactly how the v2 IC-swap scripts hid U3/U1/U5 off the
# A4 right edge (2026-06-14). This check is the missing gate.
PAGE_MM = {
    "A0": (1189, 841), "A1": (841, 594), "A2": (594, 420),
    "A3": (420, 297), "A4": (297, 210), "A5": (210, 148),
    "A": (279.4, 215.9), "B": (431.8, 279.4),
    "USLetter": (279.4, 215.9), "USLegal": (355.6, 215.9),
}


def check_page_extents():
    print("\n== schematic page extents ==")
    text = open(SCH).read()
    m = re.search(r'\(paper "([^"]+)"(\s+portrait)?\)', text)
    if not m:
        print("  SKIP: no (paper ...) directive found")
        return
    size, portrait = m.group(1), bool(m.group(2))
    if size not in PAGE_MM:
        print(f"  SKIP: unknown paper size {size!r}")
        return
    w, h = PAGE_MM[size]
    if portrait:
        w, h = h, w
    tol = 1.0  # mm: allow a hair of overhang for label/symbol body
    off = []
    for sm in re.finditer(r'\(symbol\s*\(lib_id "[^"]+"\)\s*\(at '
                          r'(-?[\d.]+) (-?[\d.]+)', text):
        x, y = float(sm.group(1)), float(sm.group(2))
        tail = text[sm.end():sm.end() + 1500]
        rm = re.search(r'\(property "Reference" "([^"]+)"', tail)
        ref = rm.group(1) if rm else "?"
        if ref.startswith("#"):   # power/flag pseudo-symbols
            continue
        if x < -tol or x > w + tol or y < -tol or y > h + tol:
            off.append((ref, x, y))
    if off:
        detail = ", ".join(f"{r}({x:.0f},{y:.0f})" for r, x, y in sorted(off))
        failures.append(("page", f"{len(off)} symbol(s) off the {size} sheet "
                         f"({w:.0f}x{h:.0f}mm) — cropped from the exported "
                         f"PDF/SVG: {detail}"))
        print(f"  FAIL: {len(off)} symbol(s) off-sheet: {detail}")
    else:
        print(f"  OK: all placed symbols within the {size} sheet "
              f"({w:.0f}x{h:.0f}mm)")
    summary_rows.append(("page extents", "FAIL" if off else "PASS",
                         f"{len(off)} off-sheet ({size})"))


def check_models():
    print("\n== 3D model paths (WARN-only) ==")
    text = open(PCB).read()
    missing = set()
    for m in re.finditer(r'\(model\s+"([^"]+)"', text):
        path = m.group(1).replace("${KIPRJMOD}", HW)
        if not os.path.isabs(path):
            path = os.path.join(HW, path)
        if not os.path.exists(path):
            missing.add(m.group(1))
    if missing:
        for p in sorted(missing):
            warnings.append(("models", f"3D model missing: {p} — Pages viewer"
                             " will render a bare footprint"))
    else:
        print("  OK: all footprint 3D model paths resolve")
    summary_rows.append(("3D models", "WARN" if missing else "PASS",
                         f"{len(missing)} missing"))


# --------------------------------------------------------------------------

def write_summary():
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not path:
        return
    with open(path, "a") as f:
        f.write("## Hardware validation\n\n| check | status | detail |\n|---|---|---|\n")
        for row in summary_rows:
            f.write("| %s | %s | %s |\n" % row)
        if failures:
            f.write("\n### Failures\n")
            for c, m in failures:
                f.write(f"- **{c}**: {m}\n")
        if warnings:
            f.write("\n### Warnings\n")
            for c, m in warnings:
                f.write(f"- {c}: {m}\n")


def main():
    global KCLI
    if KCLI is None:
        KCLI = find_kicad_cli()
    update = "--update-baseline" in sys.argv
    print(f"kicad-cli: {KCLI}")
    print("  version:", subprocess.run([KCLI, "version"], capture_output=True,
                                       text=True).stdout.strip())
    with tempfile.TemporaryDirectory() as tmp:
        erc_base, erc_viol = check_erc(tmp)
        drc_base, drc_viol, unconn, parity = check_drc(tmp)
        fresh = check_netlist(tmp)
        check_bom(fresh)
        check_polarity(fresh)
        check_page_extents()
        check_models()

        candidate = {**erc_base, **drc_base}
        if update:
            json.dump(candidate, open(BASELINE, "w"), indent=2)
            print(f"\nBaseline written to {BASELINE}")
            return 0

        if not os.path.exists(BASELINE):
            print("\nNo baseline found. Candidate baseline (review every entry"
                  " before committing as hardware/ci-baseline.json):")
            print("===BEGIN-CI-BASELINE===")
            print(json.dumps(candidate, indent=2))
            print("===END-CI-BASELINE===")
            write_summary()
            return 2

        base = json.load(open(BASELINE))
        erc_ok = compare("erc", json_to_counts(candidate["erc"]),
                         json_to_counts(base.get("erc", {})))
        summary_rows.insert(0, ("ERC vs baseline", "PASS" if erc_ok else "FAIL",
                                json.dumps(candidate["erc"])))
        drc_ok = compare("drc", json_to_counts(candidate["drc"]),
                         json_to_counts(base.get("drc", {})))
        for key, label in (("drc_unconnected", "unconnected items"),
                           ("drc_parity", "schematic parity issues")):
            if candidate[key] != base.get(key, 0):
                failures.append(("drc", f"{label}: baseline {base.get(key, 0)}"
                                 f" -> {candidate[key]}"))
                drc_ok = False
        summary_rows.insert(1, ("DRC vs baseline", "PASS" if drc_ok else "FAIL",
                                f"unconn={candidate['drc_unconnected']} "
                                f"parity={candidate['drc_parity']}"))
        if not erc_ok:
            details(erc_viol)
        if not drc_ok:
            details(drc_viol)

        facts["erc"] = {"pass": erc_ok, "counts": candidate["erc"]}
        facts["drc"] = {"pass": drc_ok, "counts": candidate["drc"],
                        "unconnected": candidate["drc_unconnected"],
                        "parity": candidate["drc_parity"]}

    json_out = None
    if "--json" in sys.argv:
        i = sys.argv.index("--json")
        json_out = sys.argv[i + 1] if i + 1 < len(sys.argv) else None
    if json_out:
        json.dump(facts, open(json_out, "w"), indent=1)
        print(f"Wrote PR-comment facts to {json_out}")

    write_summary()
    print()
    for c, m in warnings:
        print(f"WARN [{c}] {m}")
    if failures:
        for c, m in failures:
            print(f"FAIL [{c}] {m}")
        print("\nIf a change is intentional and reviewed, refresh with:"
              "\n  python3 scripts/ci/hardware_validate.py --update-baseline"
              "\n(run inside the CI container so counts match: "
              "kicad/kicad:10.0.2)")
        return 1
    print("All hardware checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
