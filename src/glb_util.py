"""Byte-level GLB passes that trimesh cannot express.

- dedupe_images: trimesh embeds one copy of a texture per material; phones then
  decode the same 1024 px image dozens of times (400+ MB GPU memory -> crash).
- lite: mobile variant with downscaled textures and no TANGENT attributes.
Triangle positions are never touched.
"""
import io, json, struct, hashlib, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '.deps'))
from PIL import Image


def read(blob):
    jl = struct.unpack_from('<I', blob, 12)[0]
    tree = json.loads(blob[20:20 + jl])
    bl = struct.unpack_from('<I', blob, 20 + jl)[0]
    return tree, bytearray(blob[28 + jl:28 + jl + bl])


def write(tree, binary):
    js = json.dumps(tree, ensure_ascii=False, separators=(',', ':')).encode(); js += b' ' * ((-len(js)) % 4)
    binary = bytes(binary) + b'\0' * ((-len(binary)) % 4)
    return (struct.pack('<III', 0x46546c67, 2, 28 + len(js) + len(binary)) + struct.pack('<II', len(js), 0x4e4f534a) + js
            + struct.pack('<II', len(binary), 0x004e4942) + binary)


def view_bytes(tree, binary, i):
    v = tree['bufferViews'][i]; o = v.get('byteOffset', 0)
    return bytes(binary[o:o + v['byteLength']])


def compact(tree, binary):
    """Drop unreferenced accessors/bufferViews/images and repack the binary chunk."""
    used_acc = set()
    for m in tree['meshes']:
        for p in m['primitives']:
            used_acc.update(p['attributes'].values())
            if 'indices' in p:
                used_acc.add(p['indices'])
    amap = {}; accs = []
    for i, a in enumerate(tree['accessors']):
        if i in used_acc:
            amap[i] = len(accs); accs.append(a)
    for m in tree['meshes']:
        for p in m['primitives']:
            p['attributes'] = {k: amap[v] for k, v in p['attributes'].items()}
            if 'indices' in p:
                p['indices'] = amap[p['indices']]
    tree['accessors'] = accs
    used_img = {t['source'] for t in tree.get('textures', [])}
    imap = {}; imgs = []
    for i, im in enumerate(tree.get('images', [])):
        if i in used_img:
            imap[i] = len(imgs); imgs.append(im)
    for t in tree.get('textures', []):
        t['source'] = imap[t['source']]
    if 'images' in tree:
        tree['images'] = imgs
    used_view = {a['bufferView'] for a in accs if 'bufferView' in a} | {im['bufferView'] for im in imgs if 'bufferView' in im}
    vmap = {}; views = []; out = bytearray()
    for i, v in enumerate(tree['bufferViews']):
        if i not in used_view:
            continue
        data = view_bytes(tree, binary, i)
        out += b'\0' * ((-len(out)) % 4)
        v = dict(v); v['byteOffset'] = len(out); v['byteLength'] = len(data); out += data
        vmap[i] = len(views); views.append(v)
    for a in accs:
        if 'bufferView' in a:
            a['bufferView'] = vmap[a['bufferView']]
    for im in imgs:
        im['bufferView'] = vmap[im['bufferView']]
    tree['bufferViews'] = views; tree['buffers'] = [{'byteLength': len(out) + ((-len(out)) % 4)}]
    return tree, out


def dedupe_images(blob):
    tree, binary = read(blob)
    if not tree.get('images'):
        return blob, 0
    first = {}; remap = {}
    for i, im in enumerate(tree['images']):
        h = hashlib.sha256(view_bytes(tree, binary, im['bufferView'])).hexdigest()
        remap[i] = first.setdefault(h, i)
    before = len(tree['images'])
    for t in tree['textures']:
        t['source'] = remap[t['source']]
    # identical (source, sampler) textures collapse too, so three.js shares one GPU upload
    tkey = {}; tmap = {}; texs = []
    for i, t in enumerate(tree['textures']):
        k = (t['source'], t.get('sampler'))
        if k not in tkey:
            tkey[k] = len(texs); texs.append(t)
        tmap[i] = tkey[k]

    def fix(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k.endswith('Texture') and isinstance(v, dict) and 'index' in v:
                    v['index'] = tmap[v['index']]
                else:
                    fix(v)
        elif isinstance(o, list):
            for v in o:
                fix(v)
    fix(tree['materials']); tree['textures'] = texs
    tree, binary = compact(tree, binary)
    return write(tree, binary), before - len(tree['images'])


def lite(blob, color_px=512, other_px=256, drop=('TANGENT',)):
    """Phone variant: smaller JPEG textures, no tangents (three.js derives them)."""
    tree, binary = read(blob)
    role = {}
    for m in tree.get('materials', []):
        pbr = m.get('pbrMetallicRoughness', {})
        if 'baseColorTexture' in pbr:
            role[tree['textures'][pbr['baseColorTexture']['index']]['source']] = 'color'
        for k in ('normalTexture', 'occlusionTexture'):
            if k in m:
                role.setdefault(tree['textures'][m[k]['index']]['source'], 'other')
        if 'metallicRoughnessTexture' in pbr:
            role.setdefault(tree['textures'][pbr['metallicRoughnessTexture']['index']]['source'], 'other')
    new_views = []
    for i, im in enumerate(tree.get('images', [])):
        img = Image.open(io.BytesIO(view_bytes(tree, binary, im['bufferView']))).convert('RGB')
        cap = color_px if role.get(i) == 'color' else other_px
        if max(img.size) > cap:
            img = img.resize((cap, max(1, round(img.height * cap / img.width))), Image.Resampling.LANCZOS)
        buf = io.BytesIO(); img.save(buf, 'JPEG', quality=82, optimize=True); data = buf.getvalue()
        binary += b'\0' * ((-len(binary)) % 4)
        tree['bufferViews'].append({'buffer': 0, 'byteOffset': len(binary), 'byteLength': len(data)}); binary += data
        im['bufferView'] = len(tree['bufferViews']) - 1; im['mimeType'] = 'image/jpeg'
    for m in tree['meshes']:
        for p in m['primitives']:
            for k in drop:
                p['attributes'].pop(k, None)
    tree, binary = compact(tree, binary)
    return write(tree, binary)
