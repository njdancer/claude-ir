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

Baseline (hardware/ci-baseline.json) stores (severity, type) violation
counts as produced by the CI KiCad container (kicad/kicad:10.0.2 — counts
can differ slightly under the bench's KiCad 9). Errors gate strictly: any
change, up or down, fails so the baseline never goes stale. Warnings gate
on increase only; a decrease prints a reminder to refresh.

Usage:
  python3 scripts/ci/hardware_validate.py                  # validate
  python3 scripts/ci/hardware_validate.py --update-baseline
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
# anywhere (J4/J5) and the bare solder jumper (JP1).
NO_LCSC_OK = {"J4", "J5", "JP1"}

failures = []  # list of (check, message)
warnings = []
summary_rows = []  # (check, status, detail) for the GitHub step summary


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
    """Errors strict (any change fails), warnings increase-only."""
    ok = True
    keys = set(actual) | set(base)
    for key in sorted(keys):
        sev, typ = key
        a, b = actual.get(key, 0), base.get(key, 0)
        if a == b:
            continue
        if sev == "error" or a > b:
            failures.append((check, f"{sev}:{typ} count {b} -> {a}"))
            ok = False
        else:
            warnings.append((check, f"{sev}:{typ} improved {b} -> {a} — "
                             "refresh baseline (--update-baseline)"))
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
    if missing:
        failures.append(("bom", "fitted parts without LCSC field: "
                         + ", ".join(missing)))
    else:
        n = sum(1 for c in comps.values() if not c["dnp"])
        print(f"  OK: all {n} fitted parts have LCSC codes"
              f" (allowlisted: {', '.join(sorted(NO_LCSC_OK))})")
    summary_rows.append(("BOM LCSC coverage", "FAIL" if missing else "PASS",
                         f"{len(missing)} missing"))


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
