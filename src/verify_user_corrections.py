"""User-requested room changes and independent exported geometry checks."""
from pathlib import Path
import sys,json,hashlib,html
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'.deps'))
import numpy as np,trimesh as tm
from shapely.geometry import Polygon,MultiPoint,shape
from shapely.ops import unary_union
OUT=ROOT/'output';dest=OUT/'corrections';dest.mkdir(exist_ok=True)
base=tm.load(OUT/'house.glb',force='scene',process=False)
ctx=tm.load(OUT/'surroundings.glb',force='scene',process=False)
context=json.loads((OUT/'realism/site-context.json').read_text(encoding='utf-8'))
neighbors=[f for f in context['features'] if f['type']=='neighbor']
buildings=[f for f in context['features'] if f['type'] in ('neighbor','temple')]
main=MultiPoint(np.concatenate([g.vertices[:,[0,2]] for n,g in base.geometry.items() if n.startswith(('FLOOR_','ROOF_'))])).convex_hull
road_triangles=[p for n,g in ctx.geometry.items() if n=='CONTEXT_road' for t in g.triangles if (p:=Polygon(t[:,[0,2]])).area>1e-8]
road=unary_union(road_triangles)
north=next(f for f in neighbors if f['label']=='北側紅瓦平房')
checks={'north_house_overlap_m2':main.intersection(shape(north['built_envelope_xz'])).area,
 'road_building_overlap_m2':sum(road.intersection(shape(f['built_envelope_xz'])).area for f in buildings)+road.intersection(main).area,
 'legacy_symbolic_road_removed':'SITE_site_road' not in base.geometry}
assert checks['north_house_overlap_m2']<1e-5 and checks['road_building_overlap_m2']<1e-4 and checks['legacy_symbolic_road_removed'],checks
labels={'ROOM_1_LIVING_W':'展覽空間／教室（西側）','ROOM_1_LIVING_E':'Lobby 大廳（東側）','ROOM_2_LIVING':'客廳兼餐廳','ROOM_2_DINING':'廚房','ROOM_3_BED3':'佛廳／祭祀空間','ROOM_4_BED':'儲藏間'}
audit=json.loads((OUT/'audit/corrections.json').read_text(encoding='utf-8'))
near=next(r for r in audit['rows'] if r['category']=='衛浴設備' and r['location']=='2F 廁所B 小便斗' and any(abs(c['world_bounds'][0][0]-(2.84-.18-7.18))<.03 for c in r['components']))
assert all('wc_' not in c['name'] for c in near['components']) and any(c['name']=='urinal_back' for c in near['components'])
checks['near_door_urinal_components']=[c['name'] for c in near['components']]
manifest=json.loads((OUT/'styles/furniture-manifest.json').read_text(encoding='utf-8'))
style_checks={}
for key,data in manifest['styles'].items():
 scene=tm.load(OUT/f'styles/{key}.glb',force='scene',process=False)
 for node,label in labels.items():
  par=scene.graph.transforms.parents[node]
  assert scene.graph.transforms.edge_data[(par,node)]['metadata']['label']==label,(key,node)
 items=data['items']
 # Reject residential beds in the newly designated exhibition, worship and storage rooms.
 beds=[i for i in items if i['name']=='床組']
 assert len(beds)==5 and all(i['floor'] in (2,3) for i in beds),(key,beds)
 assert not any(i['floor']==3 and i['footprint'][1]>11.75 for i in beds)
 def has(f,name):return any(i['floor']==f and name in i['name'] for i in items)
 assert all(has(f,n) for f,n in [(1,'展示台座'),(1,'教學桌'),(1,'接待櫃台'),(2,'餐桌'),(2,'廚房檯面'),(2,'水槽'),(2,'爐具'),(2,'冰箱'),(3,'神桌'),(3,'香爐'),(4,'層架')]),key
 # Physically rendered furniture exists inside the newly furnished room regions.
 for f,bounds in [(1,(.12,.15,6.4,16.45)),(1,(6.65,7.68,12.32,11.92)),(2,(12.01,.14,14.23,5.77)),(3,(.12,11.88,4.72,14.95)),(4,(10.54,.13,12.3,5.77))]:
  vv=np.concatenate([gg.vertices for n,gg in scene.geometry.items() if n.startswith(f'STYLE_{key}_{f}_furniture_')]);x,y,x2,y2=bounds
  assert np.count_nonzero((vv[:,0]>x-7.18)&(vv[:,0]<x2-7.18)&(vv[:,2]>y-8.3)&(vv[:,2]<y2-8.3))>100,(key,f,bounds)
 for f,head_y in [(2,5.65),(3,3.75)]:
  bed=next(i for i in beds if i['floor']==f and i['room']=='臥室一')
  x,y,x2,y2=bed['footprint']
  # Independent vertex test: tall headboard must be at positive Y end, not foot end.
  verts=np.concatenate([gg.vertices for n,gg in scene.geometry.items() if n.startswith(f'STYLE_{key}_{f}_')])
  z0={2:4.8,3:8.4}[f]
  mask=(verts[:,0]>x-7.18+.01)&(verts[:,0]<x2-7.18-.01)&(verts[:,1]>z0+.72)&(verts[:,1]<z0+.92)&(verts[:,2]>y-8.3-.01)&(verts[:,2]<y2-8.3+.01)
  tall=verts[mask,2]+8.3
  assert len(tall)>0 and tall.min()>y2-.15,(key,f,tall.min() if len(tall) else None,bed)
 style_checks[key]={'labels':True,'bed_count':len(beds),'two_bed_headboards_positive_plan_y':True,'furniture_count':data['furnitureCount']}
checks['styles']=style_checks
report={'date':'2026-09-10 UTC+8','passed':True,'checks':checks,'neighbor_adjustments':[{'label':f['label'],'distance_m':f['placement_shift_distance_m']} for f in neighbors if f['placement_shift_distance_m']>0],
 'basis':'Eleven explicit user changes take precedence over old PDF room names and the former near-door toilet. Context adjustments are approximate, not newly measured positions.',
 'sha256':{p.relative_to(OUT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in [OUT/'house.glb',OUT/'surroundings.glb',*[OUT/f'styles/{k}.glb' for k in manifest['styles']]]}}
(dest/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
rows=[('北側鄰房','含屋簷量體移至基地外；與住宅投影重疊面積為 0。'),('道路與鄰房','移除舊示意路面；道路、巷道與鄰房／寺廟投影重疊面積為 0。'),('1F 西側','改為展覽空間／教室：展示台、畫作、四張教學桌與座椅；移除住宅沙發組。'),('1F 東側','改為 Lobby：接待櫃台、候客座位及茶几。'),('2F 臥室一','床頭及枕頭改朝廁所 B 方向，床頭近相鄰隔牆。'),('2F 廁所 B','靠門原坐式便器改為壁掛小便斗，原有其他設備保留。'),('2F 客廳','改為客廳兼餐廳：保留起居座位並加入四人餐桌。'),('2F 原餐廳','改為廚房：L 形工作檯、水槽、爐具、抽油煙機、吊櫃與冰箱。'),('3F 臥室一','床頭及枕頭改朝臥室二方向。'),('3F 原臥室三','改為佛廳／祭祀空間：供奉檯、供桌、香爐與拜墊；移除床。神像另待使用者選定。'),('4F 原臥室','改為儲藏間：兩側層架及收納箱；移除床與書桌，入口保留。')]
rows[0]=('北側鄰房','依最新指示恢復近接關係，含屋簷仍未與住宅交疊；細節見最新位置檢查頁。')
lines=['# 本次 11 項修正與模型檢查清單','', '2026-09-10（台灣時間）。四套家具風格均已套用；建築原版同步更新房間名稱及衛浴。','', '用途及設備依使用者最新指示；PDF 本身未修改。鄰房位置依確認的近接關係作概念調整，不是新的測量成果。最新位置、電桿及門口檢查見 access.html。','', '|項次|位置|已執行修正|','|---|---|---|']
for i,(where,change) in enumerate(rows,1):lines.append(f'|{i}|{where}|{change}|')
lines+=['','檢查：北側鄰房／住宅零投影重疊、道路／建物零投影重疊；六處用途標示一致；四套各保留五張床；兩張指定床的床頭以匯出模型頂點確認；新設備及家具均為三維幾何。','', '另驗證 GLB、四風格切換、樓層／屋頂開關與觸控模擬；未在實體安卓手機驗收。']
(dest/'模型檢查清單.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
body=''.join(f'<tr><td>{i}</td><td>{html.escape(w)}</td><td>{html.escape(c)}</td></tr>' for i,(w,c) in enumerate(rows,1))
page='''<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>11 項用途與配置修正</title><style>body{font:16px/1.7 system-ui;margin:auto;max-width:1000px;padding:22px;background:#f5f3ec;color:#263d36}table{border-collapse:collapse;width:100%}td,th{border-bottom:1px solid #ccd2ca;padding:10px;text-align:left}a{color:#245943}img{max-width:100%}</style><a href="../">← 返回住宅模型</a><h1>11 項用途與配置修正</h1><p>四套家具風格均已更新；原版建築同步更新名稱及衛浴。請選取家具風格查看配置。</p><p>依使用者最新指示優先於 PDF 舊用途；建築尺寸保留。鄰房避讓調整仍屬近似位置，不是測量成果。</p><table><tr><th>項次</th><th>位置</th><th>修正</th></tr>'''+body+'''</table><h2>模型檢查</h2><p>北側鄰房／住宅、道路／建物投影重疊均為零。床头方向以匯出模型頂點檢查；四套風格各有五張床。另檢查模型格式、樓層與屋頂切換及手機觸控模擬；實體安卓驗收尚未進行。</p><p><a href="validation.json">幾何檢查結果及鄰房移位紀錄</a> · <a href="模型檢查清單.md" download>下載檢查清單</a> · <a href="../realism/index.html">實景來源與限制</a></p><img src="site-layout.svg" alt="住宅、鄰房與道路投影檢查"></html>'''
page=page.replace('<h2>模型檢查</h2>','<p><a href="access.html">最新：鄰近配置、路緣電桿與門口淨空修正</a></p><h2>四樓層配置預覽</h2><p>以下為波西米亞版的實際模型截圖；其餘三套採相同用途與家具位置。</p>'+''.join(f'<details><summary>{i} 樓配置</summary><a href="floor-{i}.png"><img loading="lazy" src="floor-{i}.png" alt="{i} 樓配置"></a></details>' for i in range(1,5))+'<h2>模型檢查</h2>')
(dest/'index.html').write_text(page,encoding='utf-8')
# Inspectable plan view made from the actual exported road and generated envelopes.
shapes=[(road,'#bfc5c3'),(main,'#287c66')]+[(shape(f['built_envelope_xz']),'#b78765') for f in buildings]
svg=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="-65 -65 130 130"><rect x="-65" y="-65" width="130" height="130" fill="#f0f1e8"/>']
for geom,color in shapes:
 for p in (geom.geoms if geom.geom_type=='MultiPolygon' else [geom]):
  if p.geom_type!='Polygon':continue
  rings=[p.exterior,*p.interiors]
  d=' '.join('M'+' L'.join(f'{x:.3f},{y:.3f}' for x,y in ring.coords)+' Z' for ring in rings)
  svg.append(f'<path d="{d}" fill="{color}" fill-rule="evenodd" stroke="#ffffff" stroke-width=".08"/>')
svg.append('<text x="-61" y="-57" font-size="3.3">綠色：王源東宅　棕色：周邊建物　灰色：道路</text></svg>')
(dest/'site-layout.svg').write_text(''.join(svg),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
