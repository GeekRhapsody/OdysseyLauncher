"""Strips the texture maps the launcher doesn't draw yet from a GLB, for a theme's shipped models.

The item shader draws only each material's base colour (docs/ARCHITECTURE.md A7, Materials), so a model's normal,
metallic-roughness, occlusion and emissive maps are only read and thrown away every time it loads: the console
theme's Game Boy (gb.glb) was 13 MB, nearly all of it such maps. This removes those references from every material,
drops the textures, images, samplers and buffer views nothing uses any more, and repacks the binary chunk (each buffer
view 4-byte aligned). Everything else (meshes, nodes, animations, base colour textures, extras) is kept as it is.

Standard library only. Writes a new file (so a hardlinked source isn't changed); the output may be the input's path.
Run from the repo root:

    python tools/console-models/strip_maps.py <in.glb> <out.glb>

Then check it with `odyssey-scrape inspect-model --kind=system <out.glb>`.
"""

import json
import os
import struct
import sys
import tempfile

GLB_MAGIC = 0x46546C67  # 'glTF'
CHUNK_JSON = 0x4E4F534A
CHUNK_BIN = 0x004E4942
MATERIAL_MAPS = ("normalTexture", "occlusionTexture", "emissiveTexture")
PBR_MAPS = ("metallicRoughnessTexture",)


def read_glb(path):
    with open(path, "rb") as f:
        data = f.read()
    magic, version, length = struct.unpack_from("<III", data, 0)
    if magic != GLB_MAGIC or version != 2:
        raise SystemExit(f"{path}: not a glTF 2.0 binary")
    offset, gltf, binary = 12, None, b""
    while offset < length:
        chunk_length, chunk_type = struct.unpack_from("<II", data, offset)
        chunk = data[offset + 8:offset + 8 + chunk_length]
        if chunk_type == CHUNK_JSON:
            gltf = json.loads(chunk.decode("utf-8"))
        elif chunk_type == CHUNK_BIN:
            binary = chunk
        offset += 8 + chunk_length
    if gltf is None:
        raise SystemExit(f"{path}: no JSON chunk")
    return gltf, binary


def write_glb(path, gltf, binary):
    text = json.dumps(gltf, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    text += b" " * (-len(text) % 4)
    binary += b"\0" * (-len(binary) % 4)
    length = 12 + 8 + len(text) + (8 + len(binary) if binary else 0)
    out = struct.pack("<III", GLB_MAGIC, 2, length) + struct.pack("<II", len(text), CHUNK_JSON) + text
    if binary:
        out += struct.pack("<II", len(binary), CHUNK_BIN) + binary
    folder = os.path.dirname(os.path.abspath(path))
    handle, temporary = tempfile.mkstemp(dir=folder, suffix=".glb")
    with os.fdopen(handle, "wb") as f:
        f.write(out)
    os.replace(temporary, path)  # a new file: a hardlink to the old one keeps the old content


def texture_refs(node, found):
    """Every texture index the JSON under node refers to ({"index": n} under a key ending in "Texture")."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key.endswith("Texture") and isinstance(value, dict) and isinstance(value.get("index"), int):
                found.append(value)
            texture_refs(value, found)
    elif isinstance(node, list):
        for item in node:
            texture_refs(item, found)
    return found


def image_refs(texture):
    """The texture's image references: its source, and any extension's (EXT_texture_webp and the like)."""
    refs = [texture] if "source" in texture else []
    for extension in texture.get("extensions", {}).values():
        if isinstance(extension, dict) and "source" in extension:
            refs.append(extension)
    return refs


def strip(gltf, binary):
    removed = 0
    for material in gltf.get("materials", []):
        for key in MATERIAL_MAPS:
            removed += material.pop(key, None) is not None
        pbr = material.get("pbrMetallicRoughness", {})
        for key in PBR_MAPS:
            removed += pbr.pop(key, None) is not None

    # Textures still referred to (materials, and anything else that names one), renumbered in order.
    refs = texture_refs([gltf.get("materials", []), gltf.get("extensions", {}), gltf.get("meshes", [])], [])
    kept_textures = sorted({ref["index"] for ref in refs})
    texture_map = {old: new for new, old in enumerate(kept_textures)}
    for ref in refs:
        ref["index"] = texture_map[ref["index"]]
    textures = [gltf["textures"][i] for i in kept_textures]

    kept_images = sorted({ref["source"] for texture in textures for ref in image_refs(texture)})
    image_map = {old: new for new, old in enumerate(kept_images)}
    for texture in textures:
        for ref in image_refs(texture):
            ref["source"] = image_map[ref["source"]]
    images = [gltf["images"][i] for i in kept_images]

    kept_samplers = sorted({t["sampler"] for t in textures if "sampler" in t})
    sampler_map = {old: new for new, old in enumerate(kept_samplers)}
    for texture in textures:
        if "sampler" in texture:
            texture["sampler"] = sampler_map[texture["sampler"]]
    samplers = [gltf["samplers"][i] for i in kept_samplers]

    for key, items in (("textures", textures), ("images", images), ("samplers", samplers)):
        if items:
            gltf[key] = items
        else:
            gltf.pop(key, None)

    # Buffer views still used (accessors, sparse accessors, the kept images), repacked into the one binary buffer.
    users = []
    for accessor in gltf.get("accessors", []):
        if "bufferView" in accessor:
            users.append(accessor)
        sparse = accessor.get("sparse")
        if sparse:
            users.extend((sparse["indices"], sparse["values"]))
    users.extend(image for image in images if "bufferView" in image)
    views = gltf.get("bufferViews", [])
    if any(view.get("buffer", 0) != 0 for view in views) or len(gltf.get("buffers", [])) > 1 or any("uri" in b for b in gltf.get("buffers", [])):
        raise SystemExit("only a GLB with its one embedded buffer is supported")
    kept_views = sorted({user["bufferView"] for user in users})
    view_map = {old: new for new, old in enumerate(kept_views)}
    packed = bytearray()
    new_views = []
    for old in kept_views:
        view = dict(views[old])
        start = view.get("byteOffset", 0)
        packed += b"\0" * (-len(packed) % 4)
        chunk = binary[start:start + view["byteLength"]]
        view["byteOffset"] = len(packed)
        packed += chunk
        new_views.append(view)
    for user in users:
        user["bufferView"] = view_map[user["bufferView"]]
    gltf["bufferViews"] = new_views
    if gltf.get("buffers"):
        gltf["buffers"][0]["byteLength"] = len(packed)
    return removed, bytes(packed), len(views) - len(new_views)


def main():
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    source, target = sys.argv[1], sys.argv[2]
    gltf, binary = read_glb(source)
    before = os.path.getsize(source)
    removed, packed, dropped_views = strip(gltf, binary)
    write_glb(target, gltf, packed)
    print(f"{source}: removed {removed} map reference(s) and {dropped_views} buffer view(s); "
          f"{before:,} -> {os.path.getsize(target):,} bytes in {target}")


if __name__ == "__main__":
    main()
