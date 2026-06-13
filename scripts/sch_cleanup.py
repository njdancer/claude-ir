#!/usr/bin/env python3
"""One-pass sweep of dangling schematic graphics left by the v2 surgery.

Deleting symbols via the MCP leaves their wires / net labels / no-connect
markers behind as orphans, and re-serialises the file onto one line. This
parses the s-expression into a tree (quote-preserving), computes every pin's
world coordinate from the symbol transforms, removes top-level nodes that are
dangling wires / floating labels / stale no-connects, and re-emits.

No args = DRY RUN (counts; dangling wires must match find_orphaned_wires=94).
--apply rewrites the file.
"""
import re
import sys

SCH = "hardware/esp32-ir-remote.kicad_sch"
TOK = re.compile(r'"(?:[^"\\]|\\.)*"|[()]|[^\s()"]+')


def parse(text):
    toks = TOK.findall(text)
    pos = 0

    def rd():
        nonlocal pos
        t = toks[pos]; pos += 1
        if t == "(":
            lst = []
            while toks[pos] != ")":
                lst.append(rd())
            pos += 1
            return lst
        return t
    return rd()


def emit(node):
    if isinstance(node, str):
        return node
    return "(" + " ".join(emit(c) for c in node) + ")"


def head(node):
    return node[0] if isinstance(node, list) and node and isinstance(node[0], str) else None


def child(node, name):
    for c in node:
        if head(c) == name:
            return c
    return None


def children(node, name):
    return [c for c in node if head(c) == name]


def num(t):
    return float(t)


def k(x, y):
    return (round(float(x), 2), round(float(y), 2))


def transform(rot, mx, my, lx, ly):
    r = int(round(rot)) % 360
    if r == 0:      nx, ny = lx, -ly
    elif r == 90:   nx, ny = ly, lx
    elif r == 180:  nx, ny = -lx, ly
    else:           nx, ny = -ly, -lx
    if mx: ny = -ny
    if my: nx = -nx
    return nx, ny


def main():
    text = open(SCH).read()
    root = parse(text)

    # --- lib_symbols: libid -> {pin#: (lx, ly)} ---
    libs = {}
    ls = child(root, "lib_symbols")
    for sym in children(ls, "symbol"):
        libid = sym[1].strip('"')
        pins = {}

        def collect(s):
            for p in children(s, "pin"):
                at = child(p, "at")
                nm = child(p, "number")
                if at and nm:
                    pins[nm[1].strip('"')] = (num(at[1]), num(at[2]))
            for sub in children(s, "symbol"):
                collect(sub)
        collect(sym)
        if pins:
            libs[libid] = pins

    # --- instances -> pin world points ---
    pin_pts = set()
    for sym in children(root, "symbol"):       # top-level instances
        lib = child(sym, "lib_id")
        at = child(sym, "at")
        if not lib or not at:
            continue
        libid = lib[1].strip('"')
        x, y, rot = num(at[1]), num(at[2]), num(at[3])
        mir = child(sym, "mirror")
        mx = mir is not None and "x" in mir
        my = mir is not None and "y" in mir
        for n, (lx, ly) in libs.get(libid, {}).items():
            dx, dy = transform(rot, mx, my, lx, ly)
            pin_pts.add(k(x + dx, y + dy))

    # --- wires / labels / junctions / no_connects (node refs kept) ---
    wires, labels, ncs = [], [], []
    junctions = set()
    for c in root:
        h = head(c)
        if h == "wire":
            pts = child(c, "pts")
            xs = children(pts, "xy")
            wires.append([k(xs[0][1], xs[0][2]), k(xs[1][1], xs[1][2]), c])
        elif h == "label":
            at = child(c, "at")
            labels.append([k(at[1], at[2]), c[1].strip('"'), c])
        elif h == "junction":
            at = child(c, "at")
            junctions.add(k(at[1], at[2]))
        elif h == "no_connect":
            at = child(c, "at")
            ncs.append([k(at[1], at[2]), c])

    print(f"pins={len(pin_pts)} wires={len(wires)} labels={len(labels)} "
          f"junctions={len(junctions)} no_connects={len(ncs)}")

    # iteratively drop wires with a dangling endpoint
    from collections import Counter
    alive = list(wires)
    removed = []
    label_pts = {lp for lp, _, _ in labels}
    while True:
        ec = Counter()
        for a, b, _ in alive:
            ec[a] += 1; ec[b] += 1
        anchored = pin_pts | junctions | label_pts
        drop = [w for w in alive
                if not ((w[0] in anchored or ec[w[0]] > 1) and
                        (w[1] in anchored or ec[w[1]] > 1))]
        if not drop:
            break
        ids = {id(w) for w in drop}
        alive = [w for w in alive if id(w) not in ids]
        removed += drop

    wire_pts = set()
    for a, b, _ in alive:
        wire_pts.add(a); wire_pts.add(b)
    floating = [l for l in labels if l[0] not in pin_pts and l[0] not in wire_pts]
    stale = [n for n in ncs if n[0] not in pin_pts]

    print(f"DANGLING wires={len(removed)} floating_labels={len(floating)} "
          f"stale_no_connects={len(stale)}")

    if "--apply" in sys.argv:
        remove_ids = {id(c) for _, _, c in removed} | \
                     {id(c) for _, _, c in floating} | {id(c) for _, c in stale}
        root[:] = [c for c in root if id(c) not in remove_ids]
        open(SCH, "w").write(emit(root) + "\n")
        print(f"APPLIED — removed {len(remove_ids)} nodes.")


if __name__ == "__main__":
    main()
