from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'.deps'))
import numpy as np,trimesh as tm
from shapely.geometry import Polygon,MultiPoint
from site_location import EN,ROT,OFFSET,to_model,metadata,PARCEL_MODEL,REG
scene=tm.load(ROOT/'output/house.glb',force='scene',process=False)
lot=Polygon(PARCEL_MODEL);clicked=Polygon(to_model(EN));floors={}
for i in range(1,5):
 verts=np.vstack([g.vertices for n,g in scene.geometry.items() if n.startswith(f'FLOOR_{i}_')]);outline=MultiPoint(verts[:,[0,2]]).convex_hull
 floors[str(i)]={'projected_outline_area_m2':float(outline.area),'outside_lot_318_m2':float(outline.difference(lot).area),'within_lot_318':lot.buffer(.001).covers(outline),
                 'outside_user_clicked_quad_m2':float(outline.difference(clicked).area)}
report={'site_alignment':metadata(),'scale_unchanged':bool(np.allclose(np.abs(np.linalg.det(ROT)),1) and np.allclose(ROT@ROT.T,np.eye(2))),
 'coordinate_round_trip':bool(np.allclose(to_model(EN)@ROT+OFFSET,EN)),'floors':floors,'lot_area_m2':lot.area,'lot_area_permit_m2':REG['parcel_area_m2_permit'],
 'permit_lot_line_distance_rms_m':REG['house_plan_to_en']['permit_lot_line_distance_rms_m'],'not_surveyed':True}
report['passed']=report['scale_unchanged'] and report['coordinate_round_trip'] and all(f['within_lot_318'] for f in floors.values()) and abs(lot.area-REG['parcel_area_m2_permit'])<5 and report['permit_lot_line_distance_rms_m']<.2
(ROOT/'output/realism/site-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report,ensure_ascii=False));assert report['passed']
