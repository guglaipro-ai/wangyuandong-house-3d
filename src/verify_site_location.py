from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'.deps'))
import numpy as np,trimesh as tm
from shapely.geometry import Polygon,MultiPoint
from site_location import EN,ROT,OFFSET,to_model,metadata
scene=tm.load(ROOT/'output/house.glb',force='scene',process=False)
site=Polygon(to_model(EN));floors={}
for i in range(1,5):
 verts=np.vstack([g.vertices for n,g in scene.geometry.items() if n.startswith(f'FLOOR_{i}_')]);outline=MultiPoint(verts[:,[0,2]]).convex_hull
 floors[str(i)]={'projected_outline_area_m2':float(outline.area),'outside_clicked_polygon_m2':float(outline.difference(site).area),'within_clicked_polygon':site.buffer(.001).covers(outline)}
report={'site_alignment':metadata(),'scale_unchanged':bool(np.allclose(ROT@ROT.T,np.eye(2))),'coordinate_round_trip':bool(np.allclose(to_model(EN)@ROT+OFFSET,EN)),'floors':floors,'clicked_polygon_area_m2':site.area,'not_surveyed':True}
report['passed']=report['scale_unchanged'] and report['coordinate_round_trip'] and all(f['within_clicked_polygon'] for f in floors.values())
(ROOT/'output/realism/site-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report));assert report['passed']
