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
    chunks[0] = (b"JSON", json.dumps(gltf, separators=(",", ":")).encode())
    write_glb(path, chunks)
    # validate round-trip
    check = json.loads(read_glb(path)[0][1])
    assert all(
        "metallicFactor" in m.get("pbrMetallicRoughness", {})
        for m in check.get("materials", [])
    ), "validation failed: material missing explicit factors"
    print(f"fixed {path}: {n_diel} dielectric, {n_metal} metallic materials")


if __name__ == "__main__":
    main(sys.argv[1])
