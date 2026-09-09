import sys,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.deps'))
import trimesh,numpy as np
original=trimesh.load(ROOT/'output/house.glb',force='scene',process=False)
report={}
for style in ['bohemian','industrial','eclectic','wabisabi']:
    file=ROOT/f'output/styles/{style}.glb'
    scene=trimesh.load(file,force='scene',process=False)
    mismatches=[]
    for name,geom in original.geometry.items():
        other=scene.geometry.get(name)
        if other is None or not np.array_equal(geom.vertices,other.vertices) or not np.array_equal(geom.faces,other.faces):
            mismatches.append(name)
    missing=[]
    for node in original.graph.nodes:
        if node not in scene.graph.nodes or not np.allclose(original.graph[node][0],scene.graph[node][0]): missing.append(node)
    report[style]={'originalGeometryUnchanged':not mismatches,'originalNodesUnchanged':not missing,'geometryMismatches':mismatches,'nodeMismatches':missing,'addedMeshBatches':len(scene.geometry)-len(original.geometry),'sha256':hashlib.sha256(file.read_bytes()).hexdigest()}
print(json.dumps(report,ensure_ascii=False))
(ROOT/'output/styles/geometry-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
assert all(r['originalGeometryUnchanged'] and r['originalNodesUnchanged'] and r['addedMeshBatches']>0 for r in report.values())
