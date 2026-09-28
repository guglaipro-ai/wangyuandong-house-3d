"""Four independently designed furnished variants; the house GLB stays immutable.

Each scheme (style_schemes.py) supplies its own floor, wall and ceiling finish,
lighting, window dressing, furniture forms and layouts. Run after build_house.py
and before enhance_glb.py (textures are embedded there).
"""
import sys, json, struct, hashlib
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.deps')); sys.path.insert(0, str(Path(__file__).resolve().parent))
import trimesh as tm
from style_schemes import SCHEMES

OUT = ROOT / 'output/styles'; OUT.mkdir(exist_ok=True)


def export(s):
    scene = tm.load(ROOT / 'output/house.glb', force='scene', process=False)
    removed = []
    for name, g in list(scene.geometry.items()):
        if name.endswith('_floor_finish_tile'):
            g.visual = tm.visual.TextureVisuals(material=s.mats[s.FLOOR])
        elif name.endswith(('_wall_paint', '_column_paint')):
            g.visual = tm.visual.TextureVisuals(material=s.mats['paint'])
        elif '_ceiling_' in name:
            if getattr(s, 'EXPOSED', False):
                scene.delete_geometry(name); removed.append(name)
            elif name.endswith('_ceiling_ceiling'):
                g.visual = tm.visual.TextureVisuals(material=s.mats['ceilpaint'])
    triangles = 0
    for (floor, mat, kind), parts in s.batches.items():
        m = tm.util.concatenate(parts); m.visual = tm.visual.TextureVisuals(material=s.mats[mat]); triangles += len(m.faces)
        name = f'STYLE_{s.key}_{floor}_{kind}_{mat}'
        scene.add_geometry(m, node_name=name, geom_name=name, parent_node_name=f'FLOOR_{floor}', metadata={'kind': kind, 'style': s.key})
    blob = scene.export(file_type='glb'); jl = struct.unpack_from('<I', blob, 12)[0]; tree = json.loads(blob[20:20 + jl]); binary = blob[20 + jl:]
    for m in tree['meshes']:
        for p in m['primitives']:
            for idx in p['attributes'].values():
                tree['bufferViews'][tree['accessors'][idx]['bufferView']]['target'] = 34962
            if 'indices' in p:
                tree['bufferViews'][tree['accessors'][p['indices']]['bufferView']]['target'] = 34963
    js = json.dumps(tree, ensure_ascii=False, separators=(',', ':')).encode(); js += b' ' * ((-len(js)) % 4)
    blob = struct.pack('<III', 0x46546c67, 2, 20 + len(js) + len(binary)) + struct.pack('<II', len(js), 0x4e4f534a) + js + binary
    target = OUT / f'{s.key}.glb'; tmp = target.with_suffix('.glb.tmp'); tmp.write_bytes(blob); tmp.replace(target)
    return dict(label=s.label, design=s.brief, bytes=len(blob), sha256=hashlib.sha256(blob).hexdigest(), addedTriangles=triangles,
                removedBaseGeometry=removed, furnitureCount=sum(i['major'] for i in s.items), itemCount=len(s.items), items=s.items)


if __name__ == '__main__':
    report = {}
    for cls in SCHEMES:
        s = cls(); s.populate(); report[s.key] = export(s)
        print(s.key, report[s.key]['bytes'], report[s.key]['itemCount'], report[s.key]['addedTriangles'], flush=True)
    names = {k: {i['name'] for i in v['items']} for k, v in report.items()}
    shared = set.intersection(*names.values())
    (OUT / 'furniture-manifest.json').write_text(json.dumps({
        'units': 'metres; plan x/y coordinates', 'purpose': 'approximate furniture proposals; not construction or clearance certification',
        'distinctness': {'item_names_shared_by_all_four': sorted(shared), 'unique_item_names': {k: len(v - set.union(*(names[o] for o in names if o != k))) for k, v in names.items()}},
        'styles': report}, ensure_ascii=False, indent=2), encoding='utf-8')
