#!/usr/bin/env python3
"""Fix PBR factors in a kicad-cli GLB export.

kicad-cli omits metallicFactor/roughnessFactor, and the glTF spec defaults
both to 1.0 — every part renders as rough bare metal and washes out to
white under model-viewer's neutral lighting. Set sane dielectric defaults,
keeping gold/copper-coloured materials metallic so pads and pins still
look like metal.

Usage: python3 scripts/fix_glb_materials.py <file.glb>
Validates by re-parsing the output and asserting every material has
explicit factors.
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


def looks_metallic(color):
    r, g, b = color[:3]
    return r > 0.5 and g > 0.3 and b < 0.5 and r > b  # gold / copper tones


# Linux KiCad builds fail to read STEP colors: component primitives arrive
# with NO material (renderer default = white). Recolor them by mesh name
# (= the 3D model filename). (color RGB, metallic, roughness)
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


def main(path):
    chunks = read_glb(path)
    gltf = json.loads(chunks[0][1])
    n_metal = n_diel = 0
    for m in gltf.get("materials", []):
        pbr = m.setdefault("pbrMetallicRoughness", {})
        color = pbr.get("baseColorFactor", [1, 1, 1, 1])
        if looks_metallic(color):
            pbr["metallicFactor"] = 0.9
            pbr["roughnessFactor"] = 0.35
            n_metal += 1
        else:
            pbr["metallicFactor"] = 0.05
            pbr["roughnessFactor"] = 0.65
            n_diel += 1
        # translucent soldermask renders milky in model-viewer; make it a
        # solid, slightly deeper green
        if len(color) > 3 and color[3] < 0.99:
            pbr["baseColorFactor"] = [color[0] * 0.7, color[1] * 1.1,
                                      color[2] * 0.7, 1.0]
            m["alphaMode"] = "OPAQUE"
    n_recolored = recolor_missing(gltf)
    chunks[0] = (b"JSON", json.dumps(gltf, separators=(",", ":")).encode())
    write_glb(path, chunks)
    # validate round-trip
    check = json.loads(read_glb(path)[0][1])
    assert all(
        "metallicFactor" in m.get("pbrMetallicRoughness", {})
        for m in check.get("materials", [])
    ), "validation failed: material missing explicit factors"
    assert not any(
        "material" not in p
        for mesh in check.get("meshes", [])
        for p in mesh.get("primitives", [])
        if not mesh.get("name", "").startswith("esp32-ir-remote")
    ), "validation failed: component primitive without material"
    print(f"fixed {path}: {n_diel} dielectric, {n_metal} metallic, "
          f"{n_recolored} primitives recolored by name")


if __name__ == "__main__":
    main(sys.argv[1])
