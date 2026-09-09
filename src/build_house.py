"""Drawing-based concept model. Plan coordinates in metres; GLB uses Y up.
Source: PDF pp6-20. Fine profiles are user-approved approximations.
"""
from pathlib import Path
import sys, json, math, hashlib, struct
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.deps'))
import numpy as np
import trimesh
from shapely.geometry import Polygon, box as rect, LineString
from shapely.ops import unary_union
from audit_details import Audit, opening_detail, WALL_ZH
from audit_fixtures import add_fixtures
audit=Audit(ROOT)

OUT=ROOT/'output'; OUT.mkdir(exist_ok=True)
scene=trimesh.Scene(base_frame='WORLD')
materials={}
for name,color in {'wall':[224,223,215,255], 'slab':[197,194,181,255],
 'metal':[48,53,54,255], 'glass':[128,176,186,88], 'door':[159,136,111,255],
 'tile':[210,204,189,255], 'wet':[177,199,195,255], 'terrace':[173,178,170,255],
 'porch':[193,191,180,255], 'white':[240,239,228,255], 'grass':[124,145,112,255],
 'ground':[196,192,177,255], 'road':[105,113,117,255], 'ceramic':[244,245,242,255]}.items():
 materials[name]=trimesh.visual.material.PBRMaterial(name=name,baseColorFactor=color,
  metallicFactor=.35 if name=='metal' else 0,roughnessFactor=.28 if name=='glass' else .78,
  alphaMode='BLEND' if name=='glass' else 'OPAQUE',doubleSided=name=='glass')
T=np.array([[1,0,0,-7.18],[0,0,1,0],[0,1,0,-8.3],[0,0,0,1]],float)
manifest={'source':'王源東住宅新建工程(請照) (1).pdf','units':'metres',
 'date':'2026-09-09 UTC+8','purpose':'concept/display only', 'floors':{},'openings':[],
 'approximation':'Plan line tracing calibrated to dimension strings; no CAD or site survey. Fine profiles and colors approved by user.'}
serial=0
def group(name,parent='WORLD',extra=None,pos=None):
 m=np.eye(4)
 if pos is not None:m[:3,3]=[pos[0]-7.18,pos[2],pos[1]-8.3]
 scene.graph.update(frame_to=name,frame_from=parent,matrix=m,metadata=extra or {})
def mesh_add(mesh,name,parent,mat,kind):
 global serial
 if len(mesh.faces)==0:return
 serial+=1; mesh.apply_transform(T)
 audit.component(name,mesh)
 mesh.visual=trimesh.visual.TextureVisuals(material=materials[mat])
 scene.add_geometry(mesh,node_name=f'{name}_{serial}',geom_name=f'g{serial}',parent_node_name=parent,metadata={'kind':kind})
def extr(poly,z,h,name,parent,mat='wall',kind='wall'):
 if poly.is_empty:return
 if poly.geom_type!='Polygon':
  for part in poly.geoms:
   if part.geom_type in ('Polygon','MultiPolygon'):extr(part,z,h,name,parent,mat,kind)
  return
 if poly.area<1e-7 or h<=.0001:return
 m=trimesh.creation.extrude_polygon(poly,h,engine='earcut');m.apply_translation([0,0,z]);mesh_add(m,name,parent,mat,kind)
def box(x,y,z,w,d,h,name,parent,mat='wall',kind='wall'):
 extr(rect(x,y,x+w,y+d),z,h,name,parent,mat,kind)
def bar(a,b,z,h,t,name,parent,mat='wall',kind='wall'):
 extr(LineString([a,b]).buffer(t/2,cap_style=2,join_style=2),z,h,name,parent,mat,kind)
def arc(cx,cy,r,start,end,n=20):
 return [(cx+r*math.cos(t),cy+r*math.sin(t)) for t in np.linspace(math.radians(start),math.radians(end),n+1)]
def outline(poly,z,h,t,name,parent,mat='wall',kind='wall'):
 pts=list(poly.exterior.coords)
 for a,b in zip(pts,pts[1:]):bar(a,b,z,h,t,name,parent,mat,kind)

def rod3(a,b,r,name,parent,mat='metal',kind='railing'):
 a=np.asarray(a);b=np.asarray(b);m=trimesh.creation.cylinder(r,np.linalg.norm(b-a),sections=10)
 m.apply_transform(trimesh.geometry.align_vectors([0,0,1],b-a));m.apply_translation((a+b)/2);mesh_add(m,name,parent,mat,kind)

def stair_waist(x,y,dx,dy,count,rise,zz,parent):
 # Vertical-thickness sloping prism beneath the treads; nominal 12 cm per p23.
 if dx:
  start=np.array([x,y,zz]);end=np.array([x-count*.24,y,zz+count*rise]);cross=np.array([0,1.13,0])
 else:
  start=np.array([x,y,zz]);end=np.array([x,y+dy*count*.24,zz+count*rise]);cross=np.array([1.13,0,0])
 corners=[start,end,end+cross,start+cross];verts=np.array(corners+[v+[0,0,-.12] for v in corners])
 faces=[[0,1,2],[0,2,3],[4,6,5],[4,7,6],[0,4,5],[0,5,1],[1,5,6],[1,6,2],[2,6,7],[2,7,3],[3,7,4],[3,4,0]]
 m=trimesh.Trimesh(vertices=verts,faces=faces,process=False)
 if m.volume<0:m.invert()
 mesh_add(m,'stair_waist',parent,'slab','stair')

BASE={1:.6,2:4.8,3:8.4,4:11.7}; HEIGHT={1:4.2,2:3.6,3:3.3,4:3.1}
WIN={
 'W1a':(.6,.5,2),'W1b':(.8,.6,1.7),'W1c':(.8,1,1.1),'W1d':(1,1.3,1.1),
 'W1e':(1,1.35,1.1),'W1f':(1.4,.5,3),'W1g':(1.4,1.4,1.1),'W1h':(1.45,1.4,1.1),'W1i':(1.2,.4,1.1),
 'W2':(3,1.65,1.1),'W3a':(2.1,1.4,1.1),'W3b':(3.2,1.85,1.1),'W3c':(2.1,1.35,1.1),
 'W4a':(.5,.9,1.9),'W4b':(.5,.9,2.5),'W4c':(.5,1.1,1.45),'W4d':(.4,1.2,.3),
 'W4e':(.8,1.4,1.1),'W4f':(.8,1.85,1.1),'W5':(4,2.4,.6),'W6a':(.6,1.4,1.1),'W6b':(.7,1.85,1.1),
 'D1':(1.65,2.1,0),'D2a':(1.3,2.5,0),'D2b':(1.2,2.4,0),'D3a':(.8,2.1,0),'D3b':(.9,2.1,0),
 'D3c':(.9,2.1,.1),'D3d':(1.1,2.1,0),'D4a':(1.1,2.1,0),'D4b':(1.1,2.3,0),'D4c':(1.1,2.35,0),
 'D5a':(.9,2.1,.1),'D5b':(1,2.1,.1),'D6':(.9,2.1,0),
 'DW1':(1.56,2.1,.1),'DW2':(2,2.1,.1),'DW3':(2.6,2.1,.1),'DW4':(3.6,2.1,.1),'SD1':(1.8,3.4,0),'LIFT':(.8,2,0)}
def wall(f,a,b,opens=(),t=.18,h=None,name='wall'):
 parent=f'FLOOR_{f}';z=BASE[f];h=h or HEIGHT[f]-.20
 a=np.array(a,float);b=np.array(b,float);L=np.linalg.norm(b-a);u=(b-a)/L
 def piece(s,e,zz,hh,mat='wall',kind='wall',tt=t,label=name):
  if e-s>.0001 and hh>.0001:bar(a+u*s,a+u*e,zz,hh,tt,label,parent,mat,kind)
 cuts=[]
 for center,code in opens:
  w,oh,sill=WIN[code]
  wet_offset={(2,'bed1_wc'):.10,(3,'wc_door'):.10}.get((f,name),0)
  if code.startswith('D3'):sill+=wet_offset
  lo=center-w/2;hi=center+w/2
  if lo<-.03 or hi>L+.03:raise ValueError((f,a,b,center,code,L))
  if sill+oh>h+.01:raise ValueError(('height',f,code))
  cuts.append((max(0,lo),min(L,hi),sill,oh,code))
 cuts.sort();cursor=0
 for lo,hi,sill,oh,code in cuts:
  if lo<cursor-.01:raise ValueError(('overlap',f,code))
  piece(cursor,lo,z,h);piece(lo,hi,z,sill);piece(lo,hi,z+sill+oh,h-sill-oh)
  center=(lo+hi)/2
  descriptions={'D1':('單片門','45+120 cm 子母雙扇門與雙扇把手'),
   'D2':('平板門','防爆鋼木門內框／面板與把手'), 'D3':('平板門','塑鋼門下部通風百葉與把手'),
   'D4':('無分格平板門','依圖重建上下兩分格、中橫框及把手；嵌板沿用木質示意'), 'D5':('木色平板門','卡控門金屬門扇與把手'),
   'D6':('實心門片','49×176 cm 百葉區與通風門把手'),
   'SD1':('無捲箱的平板','60 cm 捲箱與分段捲簾；保留半開姿態'),
   'LIFT':('衛浴门框80×210 cm及85×200 cm封板','電梯80×200 cm雙片滑門；移除重疊封板'),
   'W1':('單層連續玻璃與中梃','雙扇獨立框、玻璃、軌道與窗把手'),
   'W2':('等分三扇、連續玻璃','中央較寬三扇分格、獨立玻璃與軌道'),
   'W3':('等分三扇、連續玻璃','中央較寬三扇分格；W3b採10 mm玻璃'),
   'W4':('僅外框直接嵌玻璃','固定窗內側壓框與分型玻璃厚度'),
   'W5':('8 mm單片玻璃','8+8 mm膠合玻璃厚度與內側壓框'),
   'W6':('當作固定窗','單開推射窗獨立框、鉸鏈及把手'),
   'DW':('單片連續玻璃與等深中梃','分扇框／玻璃、錯層滑軌及把手；DW2/4採10 mm玻璃')}
  typ=next(k for k in ['LIFT','SD1','D1','D2','D3','D4','D5','D6','DW','W1','W2','W3','W4','W5','W6'] if code.startswith(k))
  before,after=descriptions[typ]
  if code.startswith('D3') and (f,name) in {(2,'bed1_wc'),(3,'wc_door')}:
   after+=f'；門底依衛浴完成面抬高{sill*100:.0f} cm，避免門片穿入地坪'
  before=audit.opening_before(f,name,code,a+u*center,before)
  row=audit.begin(f'opening_{f}_{name}_{center:.3f}','門窗／入口',f'{f}F {WALL_ZH.get(name,name)} {code}（沿牆{center:.2f}m）',[18] if code=='LIFT' else [6 if f==1 else 7,19],before,after)
  opening_detail(a,u,lo,hi,z+sill,oh,code,parent,piece,bar,box,mesh_add,materials)
  audit.end()
  manifest['openings'].append({'floor':f,'code':code,'wall':name,'width':round(hi-lo,4),'height':oh,'sill':sill,
    'center':[round(v,3) for v in (a+u*(lo+hi)/2)],'source_pages':[18] if code=='LIFT' else [6 if f==1 else 7,19],
    'position_basis':'calibrated plan tracing; see model notes','audit_id':row['id'],'construction':after})
  cursor=hi
 piece(cursor,L,z,h)

def room(f,key,label,poly,wet=False,raise_by=0):
 par=f'FLOOR_{f}';p=Polygon(poly) if isinstance(poly,list) else poly
 if raise_by:audit.begin(f'wet_level_{f}_{key}','標高',f'{f}F {label}地坪',[7],'與一般樓面齊平',f'依平面標高升高{raise_by*100:.0f} cm','明確標高')
 extr(p,BASE[f]+.003,.008+raise_by,key+'_floor',par,'wet' if wet else 'tile','floor_finish')
 if raise_by:audit.end()
 c=p.representative_point();group(f'ROOM_{f}_{key}',par,{'label':label,'floor':f,'kind':'room'},(c.x,c.y,BASE[f]+.05))
 manifest['floors'][str(f)]['rooms'].append(label)

# Calibrated outlines: p6 and p7 dimension strings. Positive plan Y points to front.
# Right facade recedes on 3F; front left wing and curved balconies remain distinct.
P1=Polygon([(0,.0),(11.88,0),(11.88,5.9),(12.45,5.9),(12.45,12.05),(6.53,12.05),(6.53,16.62),(0,16.62)])
P2=Polygon([(0,.52),(6.65,.52),(6.65,0),(14.36,0),(14.36,12.1),(12.45,12.1),(12.45,13.1),*arc(10.45,13.1,2,0,90)[1:],(6.53,15.1),(6.53,16.62),(0,16.62)])
P3=Polygon([(0,.52),(6.65,.52),(6.65,0),(14.36,0),(14.36,12.1),(12.45,12.1),(12.45,13.1),*arc(10.45,13.1,2,0,90)[1:],(6.9,15.1),(6.9,16.62),(0,16.62)])
P4=Polygon([(0,.3),(6.65,.3),(6.65,0),(12.45,0),(12.45,12.1),(6.53,12.1),(6.53,16.62),(0,16.62)])
corehole=rect(6.91,.25,11.85,4.05)
shaft=rect(8.28,1.65,10.13,3.50)
for f,p in enumerate([P1,P2,P3,P4],1):
 group(f'FLOOR_{f}',extra={'kind':'floor','floor':f,'base':BASE[f],'sourcePage':6 if f==1 else 7})
 manifest['floors'][str(f)]={'base':BASE[f],'height_to_next':HEIGHT[f],'rooms':[],'outline_area':p.area}
 thick=.18 if f==1 else .20
 extr(p.difference(shaft if f==1 else corehole),BASE[f]-thick,thick,'floor_slab',f'FLOOR_{f}','slab','slab')

# 1F: two living rooms, central stair/elevator, two small sanitary spaces.
wall(1,(0,0),(6.65,0),[(4.7,'D5a')],name='back_left')
wall(1,(6.65,0),(11.88,0),[],name='back_core')
wall(1,(0,0),(0,16.62),[(2.2,'W1f'),(8.1,'W1f'),(10.3,'W1f'),(13.4,'W1f')],name='left')
wall(1,(0,16.62),(6.53,16.62),[(3.4,'W5')],name='front_feature_window')
wall(1,(6.53,12.05),(6.53,16.62),[(1.9,'D2a')],name='front_entry')
wall(1,(6.53,12.05),(12.45,12.05),[(3.5,'W2')],name='right_living_front')
wall(1,(12.45,5.9),(12.45,12.05),[(1.0,'W1b'),(2.6,'W1b'),(4.9,'D2b')],name='right_living_side')
wall(1,(11.88,0),(11.88,5.9),[(2,'W1f'),(4.65,'D1')],name='core_entry')
wall(1,(11.88,5.9),(12.45,5.9),name='step')
audit.begin('shutter_relocation','格局', '1F 捲門及兩客廳分隔',[6,20],'捲門設於兩客廳中段分隔牆','移至樓梯廳西側入口；原洞補回實牆','平面位置對照')
wall(1,(6.53,5.9),(6.53,12.05),[],name='living_partition')
wall(1,(8.18,5.9),(11.88,5.9),[],name='core_front')
audit.end()
wall(1,(8.18,3.60),(8.18,5.9),[(1.15,'SD1')],name='stair_lobby_west')
wall(1,(8.62,5.9),(8.62,7.55),[(.8,'D3a')],t=.15,name='wc_b_entry')
wall(1,(8.62,7.55),(12.45,7.55),[],t=.15,name='wc_b_front')
wall(1,(6.65,0),(6.65,3.55),[(2.5,'D3a')],t=.15,name='wc_a_side')
audit.begin('storage_space','格局','1F 樓梯下方儲藏室',[6,20],'誤標成客廳西北角廁所，並以兩面假隔牆佔用客廳','移除假隔牆；恢復客廳地坪；儲藏室標示移至樓梯下方','圖面明示「儲藏室」')
room(1,'LIVING_W','客廳（西側）',rect(.12,.15,6.4,16.45))
room(1,'STORAGE','儲藏室（樓梯下方）',rect(6.75,.15,8.08,3.45))
audit.end()
room(1,'LIVING_E','客廳（東側）',rect(6.65,7.68,12.32,11.92))
room(1,'WC_B','廁所 B',rect(8.72,6.0,12.3,7.43),True)
room(1,'LOBBY','樓梯間／電梯',rect(6.8,4.1,11.72,5.77))

# 2F exterior.
wall(2,(0,.52),(6.65,.52),[(2.25,'W3a'),(5.45,'W1b')],name='back_bed_wc')
wall(2,(6.65,0),(14.36,0),[(.65,'W4d'),(4.35,'W4a'),(6.2,'W6a')],name='back_stair_dining')
wall(2,(6.65,0),(6.65,.52),name='back_step')
wall(2,(0,.52),(0,16.62),[(6.6,'W1b'),(9.6,'W3a')],name='left')
wall(2,(0,16.62),(6.53,16.62),[(1.45,'W4f'),(4.3,'W3b')],name='bed3_front')
wall(2,(6.53,12.1),(6.53,16.62),[(.6,'D6')],name='bed3_balcony_entry')
wall(2,(6.53,12.1),(14.36,12.1),[(4,'DW4'),(7,'W6b')],name='living_balcony')
wall(2,(14.36,0),(14.36,12.1),[(2.55,'W1h'),(8.3,'W3a')],name='right_dining_living')
wall(2,(4.85,.52),(4.85,5.90),[(2.95,'D3b')],t=.15,name='bed1_wc')
wall(2,(4.85,1.65),(6.65,1.65),[],t=.15,name='wc_a_back')
wall(2,(4.85,4.20),(6.65,4.20),[],t=.15,name='wc_a_front')
wall(2,(6.65,.52),(6.65,5.90),[(4.65,'D2b')],name='stair_west')
wall(2,(0,5.9),(4.85,5.9),[(4.25,'D4a')],t=.15,name='bed1_front')
wall(2,(0,8.15),(3.5,8.15),[],t=.15,name='wc_b_front')
wall(2,(3.5,5.9),(3.5,8.15),[(.7,'D3d')],t=.15,name='wc_b_door')
wall(2,(4.85,5.9),(4.85,12.1),[(2.6,'D4a')],t=.15,name='bed2_east')
wall(2,(0,12.1),(4.85,12.1),[],t=.15,name='bed2_front')
wall(2,(6.53,5.9),(6.53,12.1),[(5.3,'D4a')],name='hall_living')
wall(2,(6.65,5.9),(11.88,5.9),[(.85,'W4e')],name='stair_front')
wall(2,(11.88,0),(11.88,5.9),[(3.9,'DW1')],name='dining_stair')
wall(2,(11.88,5.9),(14.36,5.9),[(1.25,'D4a')],name='dining_front')
room(2,'BED1','臥室一',rect(.12,.66,4.73,5.77));room(2,'BED2','臥室二',rect(.12,8.27,4.73,11.98))
room(2,'BED3','臥室三',rect(.12,12.23,6.4,16.49));room(2,'WC_A','廁所 A',rect(4.96,1.77,6.52,4.07),True,.10)
room(2,'WC_B','廁所 B',rect(.12,6.03,3.38,8.03),True)
room(2,'LIVING','客廳',rect(6.66,6.03,14.23,11.97));room(2,'DINING','餐廳',rect(12.01,.14,14.23,5.77))
room(2,'HALL','走道',rect(4.99,6.02,6.39,11.94));room(2,'STAIR','樓梯間',rect(6.83,4.1,11.72,5.76))

# 3F: smaller enclosed living space and a long eastern balcony.
wall(3,(0,.52),(6.65,.52),[(2.25,'W3a'),(5.45,'W1b')],name='back')
wall(3,(6.65,0),(11.88,0),[(.65,'W4d'),(4.35,'W4c')],name='stair_back')
wall(3,(6.65,0),(6.65,.52),name='back_step')
wall(3,(0,.52),(0,15.08),[(6.9,'W1b'),(9.65,'W3a')],name='left')
wall(3,(0,15.08),(4.85,15.08),[(3.2,'W1g')],name='bed3_front')
wall(3,(4.85,11.75),(4.85,15.08),[(1.65,'DW2')],name='bed3_balcony')
wall(3,(4.85,9.82),(12.45,9.82),[(4.6,'DW3')],name='living_balcony')
wall(3,(12.45,5.9),(12.45,9.82),[],name='living_east')
wall(3,(11.88,0),(11.88,5.9),[(2.4,'W3a'),(4.85,'DW1')],name='stair_east')
wall(3,(11.88,5.9),(12.45,5.9),name='east_step')
wall(3,(0,4.0),(4.85,4.0),[(4.2,'D4a')],t=.15,name='bed1_front')
wall(3,(4.85,.52),(4.85,4.0),[],t=.15,name='bed1_wc')
wall(3,(4.85,1.65),(6.65,1.65),[],t=.15,name='wc_back')
wall(3,(4.85,4.0),(6.65,4.0),[(.88,'D3b')],t=.15,name='wc_door')
wall(3,(6.65,.52),(6.65,5.9),[(4.68,'D4a')],name='stair_west')
audit.begin('remove_false_stair_front_door','格局','3F 樓梯廳南側牆',[7,20],'虛設一樘DW1通往起居室','依平面恢復實牆；保留西側D4a及東側DW1出入口','平面開口對照')
wall(3,(6.65,5.9),(11.88,5.9),[],name='stair_front')
audit.end()
wall(3,(0,7.90),(4.85,7.90),[(4.2,'D4a')],t=.15,name='bed2_back')
wall(3,(4.85,7.90),(4.85,11.75),[(2.6,'D6')],t=.15,name='bed2_east')
wall(3,(0,11.75),(4.85,11.75),[],t=.15,name='bed2_front')
room(3,'BED1','臥室一',rect(.12,.66,4.72,3.88));room(3,'BED2','臥室二',rect(.12,8.02,4.72,11.62))
room(3,'BED3','臥室三',rect(.12,11.88,4.72,14.95));room(3,'WC','廁所',rect(4.99,1.78,6.52,3.87),True,.10)
room(3,'LIVING','起居室',Polygon([(.12,4.13),(6.5,4.13),(6.5,6.02),(12.3,6.02),(12.3,9.69),(4.99,9.69),(4.99,7.77),(.12,7.77)]))
room(3,'STAIR','樓梯間',rect(6.82,4.12,11.74,5.78))

# 4F enclosed rectangle and terrace parapets.
wall(4,(6.65,0),(12.45,0),[(.8,'W4d'),(4.6,'W1e')],name='back')
wall(4,(6.65,0),(6.65,5.9),[(2.7,'W1c'),(5.15,'D5b')],name='terrace_door')
wall(4,(12.45,0),(12.45,5.9),[],name='bed_east')
wall(4,(6.65,5.9),(12.45,5.9),[(1.8,'W3c')],name='front')
wall(4,(10.40,0),(10.40,5.9),[(5.0,'D4a')],name='bed_partition')
room(4,'BED','臥室',rect(10.54,.13,12.3,5.77));room(4,'STAIR','樓梯間',rect(6.8,4.08,10.25,5.76))

# Elevator: shaft opening follows 1850 mm clear size, with a door at the front.
for f in range(1,5):
 par=f'FLOOR_{f}';z=BASE[f];h=HEIGHT[f]-.20
 for a,b in [((8.18,1.55),(10.23,1.55)),((8.18,1.55),(8.18,3.60)),((10.23,1.55),(10.23,3.60))]:bar(a,b,z,h,.20,'elevator_shaft',par,kind='wall')
 wall(f,(8.18,3.60),(10.23,3.60),[(1.025,'LIFT')],t=.20,name='elevator_door')
 group(f'ROOM_{f}_ELEVATOR',par,{'label':'電梯','kind':'room','floor':f},(9.205,2.6,z+.05))

# Staircase around the central shaft. Each riser closes exactly at the next FL.
# 27/23/21 risers derived from 4.20/3.60/3.30m and the rounded p20 table.
for f,counts in [(1,(8,8,11)),(2,(7,7,9)),(3,(6,7,8))]:
 par=f'FLOOR_{f}';base=BASE[f];rise=HEIGHT[f]/sum(counts);n=0
 # right run climbs toward back, back run crosses left, left run descends in plan to upper landing.
 flights=[((10.37,1.25+counts[0]*.24),(0,-1),counts[0]),((10.37,.12),(-1,0),counts[1]),((6.88,1.25),(0,1),counts[2])]
 for k,((x,y),(dx,dy),count) in enumerate(flights):
  start_n=n
  for j in range(count):
   n+=1;top=base+n*rise
   if dx:xx=x+dx*j*.24-.24;yy=y;w=.24;d=1.13
   else:xx=x;yy=y+dy*j*.24-(.24 if dy<0 else 0);w=1.13;d=.24
   box(xx,yy,top-rise,w,d,rise,'stair_tread',par,'tile','stair')
  # flight handrail follows approximate stair profile; posts at tread edges.
  for j in range(0,count,2):
   top=base+(n-count+j+1)*rise
   px=x+dx*j*.24+(0 if dx else .04);py=y+dy*j*.24+(1.09 if dx else 0)
   box(px,py,top,.035,.035,.9,'stair_baluster',par,'metal','railing')
  audit.begin(f'stair_rail_{f}_{k}','樓梯扶手',f'{f}→{f+1}F 第{k+1}梯段扶手',[13,15,20],'僅孤立立柱，沒有連續握持橫桿','補建沿梯段坡度連續扶手','剖面與梯段圖示；細部截面為概念假設')
  def rail_point(j):return [x+dx*j*.24+(0 if dx else .0575),y+dy*j*.24+(1.1075 if dx else .0175),base+(start_n+j+1)*rise+.9]
  rod3(rail_point(0),rail_point(count-1),.025,'stair_continuous_handrail',par)
  audit.end()
  audit.begin(f'stair_waist_{f}_{k}','樓梯斜板',f'{f}→{f+1}F 第{k+1}梯段底板',[13,15,23],'只有逐階塊體、未建斜底板','補建連續斜向梯板底面','剖面構造；斜板厚度12 cm概念採用，未含配筋')
  stair_waist(x,y,dx,dy,count,rise,base+start_n*rise,par)
  audit.end()
 # clear turning landings and upper access, assigned to this stair group.
 box(10.37,.12,base+counts[0]*rise-.14,1.13,1.13,.14,'stair_landing',par,'tile','stair')
 box(6.88,.12,base+sum(counts[:2])*rise-.14,10.37-counts[1]*.24-6.88,1.13,.14,'stair_landing',par,'tile','stair')
 endy=1.25+counts[2]*.24
 box(6.88,endy,base+HEIGHT[f]-.20,1.30,4.36-endy,.20,'stair_top_landing',par,'tile','stair')
 box(10.37,1.25+counts[0]*.24,base-.14,1.13,4.10-(1.25+counts[0]*.24),.14,'stair_bottom_landing',par,'tile','stair')

# Visible columns at grid intersections; no hidden reinforcement.
add_fixtures(globals())
for f in range(1,5):
 z=BASE[f];par=f'FLOOR_{f}'
 points=[(.12,.65),(6.65,.12),(11.88,.12),(.12,5.90),(6.65,5.90),(12.20,5.90),(.12,12.0),(6.65,12.0),(.12,15.95),(6.65,15.95)]
 for x,y in points:
  hh=HEIGHT[f]-.20 if f<4 or (x>6 and y<6) else 1.2
  # columns shown as 50x70 in structural legend; placed by architectural trace.
  box(x-.25,y-.35,z,.50,.70,hh,'column',par,'wall','column')

def rail_path(points,z,parent,solid=.4,total=1.2):
 for a,b in zip(points,points[1:]):
  if solid:bar(a,b,z,solid,.15,'balcony_upstand',parent,'wall','parapet')
  bar(a,b,z+total-.05,.05,.05,'handrail',parent,'metal','railing')
  L=math.dist(a,b);count=max(1,math.ceil(L/.115))
  for j in range(count):
   k=(j+.5)/count;x=a[0]+(b[0]-a[0])*k;y=a[1]+(b[1]-a[1])*k
   box(x-.015,y-.015,z+solid,.03,.03,total-solid-.05,'baluster',parent,'metal','railing')

curve=[(6.53,15.1),(10.45,15.1),*arc(10.45,13.1,2,90,0)[1:],(12.45,12.1)]
for f in (2,3):
 par=f'FLOOR_{f}';z=BASE[f]
 balcony=Polygon([(6.53,12.1),(12.45,12.1),(12.45,13.1),*arc(10.45,13.1,2,0,90)[1:],(6.53,15.1)])
 extr(balcony,z+.003,.012,'curved_balcony_finish',par,'terrace','floor_finish')
 rail_path(curve,z,par,solid=.6 if f==2 else .4)
 # facade cornice follows curved perimeter just below deck.
 for a,b in zip(curve,curve[1:]):bar(a,b,z-.12,.12,.24,'curved_fascia',par,'wall','trim')
 if f==3:
  rail_path([(12.45,12.1),(14.36,12.1),(14.36,0),(12,0)],z,par,solid=1.2)
  rail_path([(0,15.1),(0,16.62),(6.9,16.62),(6.9,15.1)],z,par,solid=.35)
  extr(rect(4.95,9.96,12.32,12.1),z+.005,.01,'front_terrace_finish',par,'terrace','floor_finish')
 # Vertical facade privacy screens on the front, sized from the elevation silhouette.
 for x in np.arange(5.25,6.48,.115):box(x,15.95,z,.035,.10,2.55,'front_privacy_screen',par,'metal','railing')

terr=P4.difference(rect(6.56,-.2,12.7,6.02));extr(terr,11.703,.012,'terrace_finish','FLOOR_4','terrace','floor_finish')
outline(P4,11.7,1.2,.15,'terrace_parapet','FLOOR_4',kind='parapet')
# Do not leave a parapet crossing the roof room; remove overlapping segments later.
room(4,'TERRACE','露台',rect(.20,6.15,12.25,11.9))

group('ROOF',extra={'kind':'roof','base':14.8})
roof=rect(6.55,-.10,12.55,6.0)
audit.begin('roof_shaft_hole','電梯頂部', 'RF 電梯井穿越屋頂板',[17,18],'14.60m屋頂板封住井道，淨高不足','屋頂板及面層留出1.85×1.85m井道開口','第18頁頂層井道1850 mm與OH4070 mm')
extr(roof.difference(shaft),14.6,.2,'roof_slab','ROOF','slab','slab')
extr(roof.buffer(-.16).difference(shaft),14.8,.012,'roof_finish','ROOF','terrace','floor_finish')
audit.end()
outline(roof,14.8,1.2,.15,'roof_parapet','ROOF',kind='parapet')
audit.begin('overrun_hollow','電梯頂部','RF 電梯突出井道',[17,18],'2.15m實心方塊，內部完全填實','改為1.85m淨空、20cm井壁的中空井道；頂板下緣15.77m','11.70m+4.070m=15.770m；井道1850+2×200mm')
extr(rect(8.08,1.45,10.33,3.70).difference(shaft),14.8,.97,'elevator_overrun_wall','ROOF','wall','wall')
box(8.08,1.45,15.77,2.25,2.25,.20,'elevator_overrun_cap','ROOF','slab','slab')
audit.end()

# Horizontal elevation bands and modest window hoods. Shapes retained, fine trim inferred.
for f in (2,3,4):
 par=f'FLOOR_{f}';z=BASE[f]
 for a,b in [((-.20,5.9),(-.20,12.0)),((-.20,12),(-.20,16.65)),((0,16.7),(6.6,16.7))]:
  bar(a,b,z-.18,.18,.48,'horizontal_band',par,'wall','trim')
for op in manifest['openings']:
 if op['wall'] in ('left','back','back_bed_wc','right_dining_living') and op['code'].startswith('W'):
  x,y=op['center'];w=op['width'];z=BASE[op['floor']]+op['sill']+op['height']+.12;par=f"FLOOR_{op['floor']}"
  if op['wall']=='left':box(-.35,y-w/2-.12,z,.48,w+.24,.10,'window_hood',par,'wall','trim')
  elif op['wall']=='right_dining_living':box(x-.1,y-w/2-.12,z,.45,w+.24,.10,'window_hood',par,'wall','trim')
  else:box(x-w/2-.12,y-.32,z,w+.24,.45,.10,'window_hood',par,'wall','trim')

# Ground/porch only; no survey-grade terrain or neighboring buildings.
group('SITE',extra={'kind':'site'})
site=Polygon([(-1.7,-1),(17,-2.2),(17.2,17.3),(-1.9,20)])
extr(site,-.18,.18,'site_ground','SITE','ground','site')
extr(Polygon([(-2,20),(18,17),(18,20),(-2,23)]),-.05,.05,'road_context','SITE','road','site')
extr(rect(-1.4,.5,-.55,16.5),0,.02,'planting_strip','SITE','grass','site')
porch=Polygon([(6.53,12.05),(12.45,12.05),(12.45,13.1),*arc(10.45,13.1,2,0,90)[1:],(6.53,15.1)])
extr(porch,0,.55,'curved_entrance_porch','SITE','porch','site')
for j in range(3):box(7.05,15.1+j*.32,0,2.6,.32,.55-(j+1)*.14,'entrance_step','SITE','porch','site')

# Remove the symbolic open leaf at the elevator and parapet segments through 4F room.
for node in list(scene.graph.nodes_geometry):
 if node.startswith('D3a_open_leaf'):
  # Only doors near shaft front qualify; keep sanitary doors.
  _,g=scene.graph[node];c=scene.geometry[g].centroid
  if 1.0<c[0]<3.1 and -5.1<c[2]<-3.5:scene.delete_geometry(g)
 if node.startswith('terrace_parapet'):
  _,g=scene.graph[node];c=scene.geometry[g].centroid
  if c[0]>.65 and c[2]<-2.3:scene.delete_geometry(g)

# Merge render primitives per floor/material/kind for Android draw-call efficiency.
# Logical room nodes stay separate and retain labels. Openings stay in the manifest.
batches={}
for node in list(scene.graph.nodes_geometry):
 _,g=scene.graph[node];m=scene.geometry[g]
 par=scene.graph.transforms.parents[node]
 meta=scene.graph.transforms.edge_data[(par,node)].get('metadata',{})
 kind=meta.get('kind','geometry');mat=m.visual.material.name
 batches.setdefault((par,mat,kind),[]).append(m.copy())
 scene.delete_geometry(g)
# Rebuild a minimal graph instead of exporting empty nodes left by batched parts.
clean=trimesh.Scene(base_frame='WORLD')
keep=[n for n in scene.graph.nodes if n in ['SITE','ROOF','FLOOR_1','FLOOR_2','FLOOR_3','FLOOR_4'] or n.startswith('ROOM_')]
for n in sorted(keep,key=lambda n:n.startswith('ROOM_')):
 par=scene.graph.transforms.parents[n];matrix=scene.graph[n][0]
 meta=scene.graph.transforms.edge_data[(par,n)].get('metadata',{})
 clean.graph.update(frame_to=n,frame_from=par,matrix=matrix,metadata=meta)
scene=clean
for (par,mat,kind),parts in batches.items():
 m=trimesh.util.concatenate(parts);m.visual=trimesh.visual.TextureVisuals(material=materials[mat])
 scene.add_geometry(m,node_name=f'{par}_{kind}_{mat}',geom_name=f'{par}_{kind}_{mat}',parent_node_name=par,metadata={'kind':kind})
manifest['nodes']=len(scene.graph.nodes);manifest['meshes']=len(scene.geometry)
manifest['triangles']=sum(len(m.faces) for m in scene.geometry.values())
manifest['bounds']=scene.bounds.tolist()
blob=scene.export(file_type='glb')
# Supply optional GPU buffer targets so independent validator also has no hints.
jl=struct.unpack_from('<I',blob,12)[0];tree=json.loads(blob[20:20+jl]);binary=blob[20+jl:]
for mesh in tree['meshes']:
 for prim in mesh['primitives']:
  for idx in prim['attributes'].values():tree['bufferViews'][tree['accessors'][idx]['bufferView']]['target']=34962
  if 'indices' in prim:tree['bufferViews'][tree['accessors'][prim['indices']]['bufferView']]['target']=34963
js=json.dumps(tree,ensure_ascii=False,separators=(',',':')).encode('utf8');js+=b' '*((-len(js))%4)
blob=struct.pack('<III',0x46546c67,2,20+len(js)+len(binary))+struct.pack('<II',len(js),0x4e4f534a)+js+binary
(OUT/'house.glb').write_bytes(blob)
manifest['glb_bytes']=len(blob);manifest['sha256']=hashlib.sha256(blob).hexdigest()
(OUT/'model-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
audit.export(manifest)
print(json.dumps({k:manifest[k] for k in ['nodes','meshes','triangles','bounds','glb_bytes','sha256']}))
