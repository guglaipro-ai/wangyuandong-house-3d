"""Check exported road geometry, close neighbors and physical pole-base vertices."""
from pathlib import Path
import sys,json,hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'.deps'),str(ROOT/'src')]
import numpy as np,trimesh as tm
from shapely.geometry import Polygon,MultiPoint,Point,shape,LineString
from shapely.ops import unary_union,nearest_points
from site_location import ROT,OFFSET
OUT=ROOT/'output';DEST=OUT/'corrections'
house=tm.load(OUT/'house.glb',force='scene',process=False)
context=tm.load(OUT/'surroundings.glb',force='scene',process=False)
meta=json.loads((OUT/'realism/site-context.json').read_text(encoding='utf-8'))
main=MultiPoint(np.concatenate([g.vertices[:,[0,2]] for n,g in house.geometry.items() if n.startswith(('FLOOR_','ROOF_'))])).convex_hull
def projected_mesh(g):return unary_union([p for t in g.triangles if (p:=Polygon(t[:,[0,2]])).area>1e-8])
road=projected_mesh(context.geometry['CONTEXT_road'])
apron=projected_mesh(house.geometry['SITE_site_ground'])
neighbors={f['label']:shape(f['built_envelope_xz']) for f in meta['features'] if f.get('close_neighbor')}
assert len(neighbors)==3
checks={};main_center=np.array(main.centroid.coords[0])@ROT+OFFSET
for label,p in neighbors.items():
 distance=main.distance(p);a,b=nearest_points(main,p)
 direction=np.array(p.centroid.coords[0])@ROT+OFFSET-main_center
 relationship=direction[1]>0 if label.startswith('北') else direction[0]>0 if label.startswith('東') else direction[1]<0
 checks[label]={'gap_m':distance,'correct_geographic_side':bool(relationship),'road_between_neighbors_m':LineString([a,b]).intersection(road).length}
 assert .8<=distance<=1.6 and relationship and checks[label]['road_between_neighbors_m']<1e-5,checks[label]
checks['house_on_road_m2']=main.intersection(road).area
checks['private_apron_on_road_m2']=apron.intersection(road).area
assert checks['house_on_road_m2']<1e-5 and checks['private_apron_on_road_m2']<1e-5
vertices=np.unique(context.geometry['CONTEXT_slab'].vertices,axis=0)
pole_checks=[]
for pole in next(f for f in meta['features'] if f['type']=='utilities')['poles']:
 center=np.array(pole['center_model_xz']);p=Point(center)
 ring=vertices[(np.abs(vertices[:,1])<1e-5)&(np.linalg.norm(vertices[:,[0,2]]-center,axis=1)<.101)]
 assert len(ring)>=14
 radius=float(np.linalg.norm(ring[:,[0,2]]-center,axis=1).max())
 distance=p.distance(road)
 check={'center_model_xz':center.tolist(),'edge_distance_m':distance,'actual_base_radius_m':radius,'base_in_asphalt_m2':p.buffer(radius).intersection(road).area}
 assert .15<=distance<=.4 and check['base_in_asphalt_m2']<1e-6 and radius>.095,check
 pole_checks.append(check)
report={'passed':True,'date':'2026-09-10 UTC+8','checks':checks,'poles':pole_checks,'assumption':'Three-sided adjacency confirmed by user; roughly 1 m conceptual separation, not surveyed distance. Pole centers lie just outside actual road edge.', 'sha256':{name:hashlib.sha256((OUT/name).read_bytes()).hexdigest() for name in ['house.glb','surroundings.glb']}}
(DEST/'adjacency-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
svg=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="-29 -29 58 58"><rect x="-29" y="-29" width="58" height="58" fill="#f0f1e8"/>']
for geom,color in [(road,'#727b7e'),(apron,'#eadbc0'),(main,'#287c66'),*[(p,'#bb8a65') for p in neighbors.values()]]:
 for p in getattr(geom,'geoms',[geom]):
  if p.geom_type!='Polygon':continue
  d=' '.join('M'+' L'.join(f'{x:.3f},{y:.3f}' for x,y in ring.coords)+' Z' for ring in [p.exterior,*p.interiors])
  svg.append(f'<path d="{d}" fill="{color}" fill-rule="evenodd" stroke="white" stroke-width=".06"/>')
for label,p in neighbors.items():
 x,y=p.centroid.coords[0];svg.append(f'<text x="{x}" y="{y}" font-size="1.35" text-anchor="middle">{label}</text>')
for pole in pole_checks:
 x,y=pole['center_model_xz'];svg.append(f'<circle cx="{x}" cy="{y}" r=".28" fill="#dc4e28" stroke="white" stroke-width=".07"/>')
nx,ny=np.array([0,5])@ROT.T
svg.append(f'<path d="M-24,-22 l{nx},{ny}" stroke="#27342f" stroke-width=".25"/><text x="{-24+nx}" y="{-22+ny-.8}" font-size="1.7">北</text>')
svg.append('<text x="-27" y="26" font-size="1.3">綠：住宅　棕：鄰房　深灰：道路　紅點：路緣電桿</text></svg>')
(DEST/'adjacency.svg').write_text(''.join(svg),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
