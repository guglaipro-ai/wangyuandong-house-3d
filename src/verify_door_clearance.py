"""Independent actual GLB furniture vs door approach / 0..90 degree swing test."""
from pathlib import Path
import sys,json,ast,math
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'.deps'))
import numpy as np,trimesh as tm
from shapely.geometry import Polygon,box,MultiPoint,mapping
from shapely.ops import unary_union
BASE={1:.6,2:4.8,3:8.4,4:11.7}
def door_zones():
 walls={}
 for node in ast.walk(ast.parse((ROOT/'src/build_house.py').read_text(encoding='utf-8'))):
  if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='wall':
   try:
    f,a,b=[ast.literal_eval(v) for v in node.args[:3]]
    name=next(ast.literal_eval(k.value) for k in node.keywords if k.arg=='name')
    if isinstance(f,int):walls[f,name]=(np.array(a,float),np.array(b,float))
   except (ValueError,TypeError,StopIteration):pass
 openings=json.loads((ROOT/'output/model-manifest.json').read_text(encoding='utf-8'))['openings'];result=[]
 for o in openings:
  code=o['code'];f=o['floor']
  if not code.startswith(('D','SD','LIFT')):continue
  if code=='LIFT':u=np.array([1.,0.])
  else:
   a,b=walls[f,o['wall']];u=(b-a)/np.linalg.norm(b-a)
  center=np.array(o['center']);w=o['width'];normal=np.array([-u[1],u[0]])
  approach=Polygon([center+u*s+normal*t for s,t in [(-w/2+.025,-1.2),(w/2-.025,-1.2),(w/2-.025,1.2),(-w/2+.025,1.2)]])
  zones=[approach]
  if code.startswith('D') and not code.startswith('DW'):
   leaves=[(center-u*(w/2-.05),w-.10,u)]
   if code=='D1':leaves=[(center-u*(w/2-.05),.4,u),(center+u*(w/2-.05),1.15,-u)]
   for hinge,r,axis in leaves:
    side=np.array([-axis[1],axis[0]])
    zones.append(Polygon([hinge,*[hinge+r*(axis*math.cos(t)+side*math.sin(t)) for t in np.linspace(0,math.pi/2,37)],hinge]))
  result.append(dict(floor=f,code=code,wall=o['wall'],center=center.tolist(),zone=unary_union(zones)))
 return result
def check_style(style,zones):
 scene=tm.load(ROOT/f'output/styles/{style}.glb',force='scene',process=False)
 triangles={}
 for f in BASE:
  ts=np.concatenate([g.triangles for n,g in scene.geometry.items() if n.startswith(f'STYLE_{style}_{f}_')])
  # Disregard flat rugs under 6cm and overhead lighting above 2.05m.
  ts=ts[(ts[:,:,1].max(axis=1)>BASE[f]+.06)&(ts[:,:,1].min(axis=1)<BASE[f]+2.05)]
  ts=ts[:,:,[0,2]]+[7.18,8.3];triangles[f]=(ts,ts.min(axis=1),ts.max(axis=1))
 reports=[]
 for door in zones:
  f=door['floor'];region=door['zone'];x,y,x2,y2=region.bounds
  ts,lo,hi=triangles[f];mask=(hi[:,0]>x)&(lo[:,0]<x2)&(hi[:,1]>y)&(lo[:,1]<y2)
  hits=[]
  for t in ts[mask]:
   p=Polygon(t)
   if p.area>1e-8 and p.intersects(region):hits.append(p.intersection(region))
  collision=unary_union(hits)
  reports.append({k:v for k,v in door.items() if k!='zone'}|{'overlap_m2':collision.area,'collision_bounds_plan':list(collision.bounds) if not collision.is_empty else None})
 return reports
if __name__=='__main__':
 zones=door_zones();styles=['bohemian','industrial','eclectic','wabisabi'] if '--all' in sys.argv else ['bohemian']
 report={'scope':'Actual exported furniture triangles, door frontage 1.2 m on both sides and hinged 0..90 degree sweep; flat rugs under 6 cm and fixtures above 2.05 m excluded. Concept clearance, not code compliance.','door_count':len(zones),'styles':{s:check_style(s,zones) for s in styles}}
 report['passed']=all(d['overlap_m2']<1e-5 for ds in report['styles'].values() for d in ds)
 (ROOT/'output/corrections/door-clearance.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({'passed':report['passed'],'door_count':len(zones),'conflicts':{s:[d for d in ds if d['overlap_m2']>=1e-5] for s,ds in report['styles'].items()}},ensure_ascii=False))
 if not report['passed']:sys.exit(1)
