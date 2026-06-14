#!/usr/bin/env python3
"""Fix PBR factors in a kicad-cli GLB export.

kicad-cli omits metallicFactor/roughnessFactor on component materials, and
the glTF spec defaults both to 1.0 — every part renders as rough bare metal
and washes out to white under model-viewer's neutral lighting. Classify each
material by colour (gold/copper and silver/grey -> metal, everything else
dielectric) and write explicit factors.

Translucent board materials (silkscreen, board body) render milky in
model-viewer; force them opaque. The soldermask is the deliberate exception:
kicad-cli exports it as a flat sheet sitting just above the copper, so making
it opaque hides every trace/pad/via. Keep it semi-transparent (BLEND), deepen
its green so it reads as mask rather than mint, and gloss it up a touch so
copper traces read through as the familiar darker-green outlines.

KiCad 9 Linux builds additionally fail to read STEP colours entirely:
component primitives arrive with NO material (renderer default = white).
KiCad 10 (the CI image) reads them fine, so the recolor-by-mesh-name table
below is only a fallback for older exports (e.g. a local KiCad 9 build).

Usage: python3 scripts/fix_glb_materials.py <file.glb>
Validates by re-parsing the output and asserting every material has
explicit factors and in-range colours.
"""
import json
import struct
import sys


def read_glb(path):
    with open(path, "rb") as f:
        data = f.read()
    magic, version, _total = struct.unpack_from("<4sII", data, 0)
    assert magic == b"glTF" and version == 2, "not a glTF 2.0 GLB"
    chunks = []
    off = 12
    while off < len(data):
        ln, typ = struct.unpack_from("<I4s", data, off)
        chunks.append((typ, data[off + 8:off + 8 + ln]))
        off += 8 + ln
    return chunks


def write_glb(path, chunks):
    blobs = []
    for typ, payload in chunks:
        pad = b" " if typ == b"JSON" else b"\x00"
        payload += pad * (-len(payload) % 4)
        blobs.append(struct.pack("<I4s", len(payload), typ) + payload)
    body = b"".join(blobs)
    with open(path, "wb") as f:
        f.write(struct.pack("<4sII", b"glTF", 2, 12 + len(body)) + body)


def classify(color):
    """(metallicFactor, roughnessFactor) for a base colour."""
    r, g, b = color[:3]
    mx, mn = max(r, g, b), min(r, g, b)
    if r > 0.5 and g > 0.3 and b < 0.55 and r - b > 0.1:
        return 0.9, 0.35  # gold / copper / brass (pads, pins, contacts)
    if 0.5 <= mx < 0.9 and mx - mn < 0.12:
        return 0.9, 0.35  # silver / grey (end caps, shields, leads)
    return 0.05, 0.65  # dielectric (plastic, ceramic, FR4, mask, silk)


# Fallback for KiCad 9 Linux exports, which drop STEP colours: component
# primitives arrive with NO material. Recolor them by mesh name (= the 3D
# model filename). (color RGB, metallic, roughness)
COMPONENT_COLORS = {
    "LED_D3.0mm": ((0.55, 0.03, 0.03), 0.0, 0.4),
    "LED_D5.0mm": ((0.55, 0.03, 0.03), 0.0, 0.4),
    "R_0603_1608Metric": ((0.12, 0.12, 0.12), 0.0, 0.6),
    "R_0805_2012Metric": ((0.12, 0.12, 0.12), 0.0, 0.6),
    "R_1206_3216Metric": ((0.12, 0.12, 0.12), 0.0, 0.6),
    "C_0603_1608Metric": ((0.55, 0.45, 0.33), 0.0, 0.6),
    "C_0805_2012Metric": ((0.55, 0.45, 0.33), 0.0, 0.6),
    "C_1812_4532Metric": ((0.78, 0.73, 0.6), 0.0, 0.6),
    "D_SMB": ((0.08, 0.08, 0.08), 0.0, 0.6),
    "SOT-23": ((0.08, 0.08, 0.08), 0.0, 0.55),
    "TSOT-23-6": ((0.08, 0.08, 0.08), 0.0, 0.55),
    "SOIC-16_3.9x9.9mm_P1.27mm": ((0.08, 0.08, 0.08), 0.0, 0.55),
    "Vishay_MINICAST-3Pin": ((0.05, 0.05, 0.05), 0.0, 0.45),
    "TS-1088R-02026": ((0.55, 0.55, 0.58), 0.4, 0.5),
    "IND-SMD_L6.7-W6.7": ((0.25, 0.25, 0.25), 0.0, 0.7),
    "PinHeader_1x02_P2.54mm_Vertical": ((0.1, 0.1, 0.1), 0.0, 0.6),
    "PinHeader_2x05_P2.54mm_Vertical": ((0.1, 0.1, 0.1), 0.0, 0.6),
    "SM04B-SRSS-TB__LF__SN_": ((0.88, 0.85, 0.78), 0.0, 0.6),
    "ESP32-WROOM-32": ((0.72, 0.74, 0.76), 0.8, 0.4),
    "AM2302": ((0.92, 0.92, 0.9), 0.0, 0.6),
    "USB_C_Receptacle_GCT_USB4085": ((0.75, 0.76, 0.78), 0.85, 0.35),
}
DEFAULT_COMPONENT = ((0.4, 0.4, 0.4), 0.0, 0.6)


def recolor_missing(gltf):
    """Give a named material to every primitive that has none."""
    cache = {}
    fixed = 0
    mats = gltf.setdefault("materials", [])
    for mesh in gltf.get("meshes", []):
        name = mesh.get("name", "")
        if name.startswith("esp32-ir-remote"):
            continue  # board geometry keeps KiCad's own materials
        spec = COMPONENT_COLORS.get(name, DEFAULT_COMPONENT)
        for prim in mesh.get("primitives", []):
            if "material" in prim:
                continue
            if spec not in cache:
                (r, g, b), metal, rough = spec
                mats.append({
                    "name": f"cc_{name}",
                    "pbrMetallicRoughness": {
                        "baseColorFactor": [r, g, b, 1.0],
                        "metallicFactor": metal,
                        "roughnessFactor": rough,
                    },
                })
                cache[spec] = len(mats) - 1
            prim["material"] = cache[spec]
            fixed += 1
    return fixed


# Soldermask transparency in the final viewer. Lower = more see-through
# (traces read more clearly) but milkier; higher = solider green but the
# copper starts to disappear again. 0.75 keeps the green reading as mask
# while letting trace/pad/via outlines show through.
SOLDERMASK_ALPHA = 0.75
SOLDERMASK_ROUGHNESS = 0.5  # glossier than generic dielectric -> less haze


def main(path):
    chunks = read_glb(path)
    gltf = json.loads(chunks[0][1])
    n_metal = n_diel = n_mask = 0
    for m in gltf.get("materials", []):
        pbr = m.setdefault("pbrMetallicRoughness", {})
        color = pbr.get("baseColorFactor", [1, 1, 1, 1])
        metal, rough = classify(color)
        pbr["metallicFactor"] = metal
        pbr["roughnessFactor"] = rough
        if metal > 0.5:
            n_metal += 1
        else:
            n_diel += 1
        # Translucent board materials render milky in model-viewer, so force
        # them opaque — EXCEPT the soldermask. It's a flat sheet just above
        # the copper, so opaque mask hides every trace/pad/via. Identify it
        # as the strongly-translucent green material, deepen its green (clamp
        # — the old unclamped 1.1 multiplier pushed white silk out of spec),
        # and keep it BLEND so copper reads through as darker-green outlines.
        if len(color) > 3 and color[3] < 0.99:
            r, g, b = color[:3]
            is_soldermask = color[3] < 0.9 and g > r and g > b
            if is_soldermask:
                r, g, b = r * 0.7, min(g * 1.1, 1.0), b * 0.7
                pbr["baseColorFactor"] = [r, g, b, SOLDERMASK_ALPHA]
                pbr["roughnessFactor"] = SOLDERMASK_ROUGHNESS
                m["alphaMode"] = "BLEND"
                n_mask += 1
            else:
                pbr["baseColorFactor"] = [r, g, b, 1.0]
                m["alphaMode"] = "OPAQUE"
    n_recolored = recolor_missing(gltf)
    chunks[0] = (b"JSON", json.dumps(gltf, separators=(",", ":")).encode())
    write_glb(path, chunks)
    # validate round-trip
    check = json.loads(read_glb(path)[0][1])
    for m in check.get("materials", []):
        pbr = m.get("pbrMetallicRoughness", {})
        assert "metallicFactor" in pbr and "roughnessFactor" in pbr, \
            "validation failed: material missing explicit factors"
        assert all(0.0 <= c <= 1.0
                   for c in pbr.get("baseColorFactor", [0, 0, 0, 0])), \
            "validation failed: baseColorFactor out of [0,1]"
    assert not any(
        "material" not in p
        for mesh in check.get("meshes", [])
        for p in mesh.get("primitives", [])
        if not mesh.get("name", "").startswith("esp32-ir-remote")
    ), "validation failed: component primitive without material"
    # The soldermask MUST stay translucent — an opaque mask buries every
    # copper trace. Guard against a regression silently re-hiding them.
    assert n_mask > 0 and any(m.get("alphaMode") == "BLEND"
                              for m in check.get("materials", [])), \
        "validation failed: no translucent soldermask (traces would be hidden)"
    print(f"fixed {path}: {n_diel} dielectric, {n_metal} metallic, "
          f"{n_mask} translucent soldermask, "
          f"{n_recolored} primitives recolored by name")


if __name__ == "__main__":
    main(sys.argv[1])
