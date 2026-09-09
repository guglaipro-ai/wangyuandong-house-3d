"""Independent GLB and source-ledger checks for the PDF correction release."""
import sys,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'.deps'))
import numpy as np,trimesh
r=json.loads((ROOT/'output/audit/corrections.json').read_text(encoding='utf-8'))
m=json.loads((ROOT/'output/model-manifest.json').read_text(encoding='utf-8'))
scene=trimesh.load(ROOT/'output/house.glb',force='scene',process=False)
checks={}
checks['atLeast100ActualComponentRows']=r['count']>=100 and len(r['rows'])==r['count']
checks['uniqueIds']=len({x['id'] for x in r['rows']})==r['count']
checks['everyRowHasBuiltGeometry']=all(x['components'] and all(c['triangles']>0 for c in x['components']) for x in r['rows'])
current_hash=hashlib.sha256((ROOT/'output/house.glb').read_bytes()).hexdigest()
checks['modelHashMatches']=current_hash==r['model_sha256']==m['sha256']
baseline_path=ROOT/'output/realism/architecture-baseline.glb'
if not checks['modelHashMatches'] and baseline_path.exists():
 baseline=trimesh.load(baseline_path,force='scene',process=False)
 same_triangles=set(baseline.geometry)==set(scene.geometry) and all(np.array_equal(np.asarray(g.triangles,dtype=np.float32),np.asarray(scene.geometry[n].triangles,dtype=np.float32)) for n,g in baseline.geometry.items())
 same_nodes=set(baseline.graph.nodes)==set(scene.graph.nodes) and all(np.array_equal(baseline.graph[n][0],scene.graph[n][0]) for n in baseline.graph.nodes)
 checks['modelHashMatches']=current_hash==m['sha256'] and hashlib.sha256(baseline_path.read_bytes()).hexdigest()==r['model_sha256'] and same_triangles and same_nodes
 checks['materialOnlyArchitectureBridge']=same_triangles and same_nodes
checks['fourCorrectElevatorEntrances']=sum(o['code']=='LIFT' and o['width']==.8 and o['height']==2 for o in m['openings'])==4
checks['missingWindowsAdded']=any(o['floor']==2 and o['wall']=='stair_front' and o['code']=='W4e' for o in m['openings']) and sum(o['floor']==1 and o['wall']=='right_living_side' and o['code']=='W1b' for o in m['openings'])==2
checks['storageCorrected']=any('儲藏室' in s for s in m['floors']['1']['rooms']) and '廁所 A' not in m['floors']['1']['rooms']
checks['falseThirdFloorDoorRemoved']=not any(o['floor']==3 and o['wall']=='stair_front' for o in m['openings'])
checks['wetThresholdsMatchDrawing']=all(any(o['floor']==f and o['wall']==wall and abs(o['sill']-h)<1e-6 for o in m['openings']) for f,wall,h in [(2,'bed1_wc',.1),(2,'wc_b_door',0),(3,'wc_door',.1)])
checks['finiteGeometry']=all(np.isfinite(g.vertices).all() and len(g.faces)>0 for g in scene.geometry.values())
checks['nineHandrailsAndWaists']=sum(x['category']=='樓梯扶手' for x in r['rows'])==9 and sum(x['category']=='樓梯斜板' for x in r['rows'])==9
checks['elevenSanitaryFixtures']=sum(x['category']=='衛浴設備' for x in r['rows'])==11
checks['W5LaminatedGlass16mm']=all(abs(min(np.diff(np.array(c['world_bounds']),axis=0)[0])-.016)<1e-5 for x in r['rows'] if ' W5' in x['location'] for c in x['components'] if c['name']=='W5_pane1')
# Vertical ray through shaft centre: the first roof surface must be 15.77m,
# proving the GLB itself has no former solid 14.60m roof obstruction.
px,pz=9.205-7.18,2.575-8.3;hits=[]
def cross2(a,b):return a[0]*b[1]-a[1]*b[0]
for name,g in scene.geometry.items():
 if not name.startswith('ROOF_'):continue
 for tri in g.triangles:
  a,b,c=tri[:,[0,2]];den=cross2(b-a,c-a)
  if abs(den)<1e-10:continue
  q=np.array([px,pz])-a;u=cross2(q,c-a)/den;v=cross2(b-a,q)/den
  if u>=-1e-6 and v>=-1e-6 and u+v<=1+1e-6:hits.append(float(tri[0,1]+u*(tri[1,1]-tri[0,1])+v*(tri[2,1]-tri[0,1])))
checks['shaftOverhead4070mm']=bool(hits) and abs(min(hits)-15.77)<1e-4
report={'checks':checks,'passed':all(checks.values()),'roofShaftSurfaceHeights':sorted(set(round(h,3) for h in hits)),'physicalAndroidTested':False,'notCadOrConstructionCertification':True}
(ROOT/'output/audit/validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=True));assert report['passed']
