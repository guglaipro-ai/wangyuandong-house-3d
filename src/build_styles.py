"""Four procedural furnished concept variants; original house stays immutable."""
import sys,json,math,struct,hashlib
from pathlib import Path
from collections import defaultdict
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.deps'))
import numpy as np
import trimesh as tm
from shapely.geometry import box as rect, Polygon
sys.path.insert(0,str(Path(__file__).resolve().parent))
import furniture_detail as fd
OUT=ROOT/'output/styles';OUT.mkdir(exist_ok=True)
T=np.array([[1,0,0,-7.18],[0,0,1,0],[0,1,0,-8.3],[0,0,0,1]])
BASE={1:.6,2:4.8,3:8.4,4:11.7}
PALETTES={
 'bohemian':dict(label='波西米亞',fabric='#b85134',accent='#287f7c',light='#e1bb6c',wood='#926b40',metal='#6b563d',rug='#c18148',floor='#c9b797'),
 'industrial':dict(label='工業 Loft',fabric='#9c633f',accent='#555b59',light='#b8ab93',wood='#796044',metal='#262b2b',rug='#8b8e89',floor='#aaa9a3'),
 'eclectic':dict(label='折衷混搭',fabric='#3358b6',accent='#b34e70',light='#e8d8b9',wood='#66503b',metal='#b79a56',rug='#e0b985',floor='#cdbda1'),
 'wabisabi':dict(label='侘寂',fabric='#d6cdbb',accent='#aaa08b',light='#e9dfce',wood='#aa916d',metal='#69665c',rug='#c5baa3',floor='#cfc5b2')}

def material(name,color,rough=.85,metal=0):
 c=[int(color[i:i+2],16) for i in (1,3,5)]+[255]
 return tm.visual.material.PBRMaterial(name=name,baseColorFactor=c,roughnessFactor=rough,metallicFactor=metal,doubleSided=True)

class Scheme:
 def __init__(self,key):
  self.key=key;self.p=PALETTES[key];self.batches=defaultdict(list);self.items=[];self.floor=1;self.room='';self.serial=0
  self.mats={n:material(key+'_'+n,c,.4 if n=='metal' else .9,.7 if n=='metal' else 0) for n,c in self.p.items() if n!='label'}
  self.mats.update(green=material('leaf','#597955'),clay=material('terracotta','#ae785a'),ink=material('ink','#3b403a'),white=material('canvas','#efe7d6'),brick=material('brick','#97533e'))
 def mesh(self,m,mat='wood',kind='furniture'):
  m.apply_transform(T);self.batches[(self.floor,mat,kind)].append(m)
 def box(self,x,y,z,w,d,h,mat='wood',kind='furniture',rounded=0):
  if rounded:
   r=min(rounded,w/3,d/3);p=rect(x+r,y+r,x+w-r,y+d-r).buffer(r,quad_segs=3)
   m=tm.creation.extrude_polygon(p,h,engine='earcut');m.apply_translation([0,0,z])
  else:
   m=tm.creation.box([w,d,h]);m.apply_translation([x+w/2,y+d/2,z+h/2])
  self.mesh(m,mat,kind)
 def cyl(self,x,y,z,r,h,mat='wood',kind='furniture'):
  m=tm.creation.cylinder(r,h,sections=24);m.apply_translation([x,y,z+h/2]);self.mesh(m,mat,kind)
 def soft(self,x,y,z,w,d,h,mat='fabric',kind='furniture',rounding=.4):
  m=fd.cushion((w,d,h),rounding=rounding);m.apply_translation([x+w/2,y+d/2,z+h/2]);self.mesh(m,mat,kind)
 def drape(self,x,y,z,w,d,h,mat='fabric',kind='furniture',folds=3):
  m=fd.puffy_slab(w,d,h,folds=folds);m.apply_translation([x+w/2,y+d/2,z]);self.mesh(m,mat,kind)
 def rod(self,a,b,r=.015,mat='metal',kind='furniture'):
  a=np.array(a);b=np.array(b);m=tm.creation.cylinder(r,np.linalg.norm(b-a),sections=12)
  m.apply_transform(tm.geometry.align_vectors([0,0,1],b-a));m.apply_translation((a+b)/2);self.mesh(m,mat,kind)
 def item(self,name,x,y,w,d,major=True,**meta):
  self.items.append(dict(name=name,floor=self.floor,room=self.room,footprint=[x,y,x+w,y+d],size_m=[w,d],major=major,approximate=True,**meta))
 def legs(self,x,y,z,w,d,h,mat='wood'):
  for xx in [x+.07,x+w-.07]:
   for yy in [y+.07,y+d-.07]:self.rod([xx,yy,z],[xx,yy,z+h],.027,mat)
 def sofa(self,x,y,w=2.4,d=.9):
  z=BASE[self.floor]+.03;low=self.key=='wabisabi';seat=.31 if low else .39
  self.item('低座沙發' if low else '三人沙發',x,y,w,d)
  self.legs(x,y,z,w,d,.18,'metal' if self.key=='industrial' else 'wood')
  self.box(x,y,z+.14,w,d,.19,'wood',rounded=.06)
  self.soft(x+.02,y,z+seat,w-.04,.2,.44,'fabric',rounding=.42)
  for i in range(3):self.soft(x+.14+i*(w-.28)/3,y+.17,z+seat-.05,(w-.34)/3,d-.22,.17,'fabric',rounding=.55)
  for xx in [x,x+w-.13]:self.soft(xx,y+.12,z+.24,.15,d-.16,.34,'fabric',rounding=.45)
  n=1 if low else 3
  for i in range(n):self.soft(x+.26+i*(w-.7)/max(n,1),y+.19,z+seat+.08,.32,.2,.3,'light' if i%2 else 'accent',rounding=.6)
 def chair(self,x,y,turn=False):
  z=BASE[self.floor]+.03;w=.65;d=.68;self.item('休閒單椅',x,y,w,d)
  self.legs(x,y,z,w,d,.42,'metal' if self.key=='industrial' else 'wood')
  self.soft(x,y,z+.4,w,d,.13,'accent',rounding=.4)
  by=y+d-.13 if turn else y
  self.soft(x,by,z+.46,w,.14,.44,'accent',rounding=.4)
  for xx in [x+.025,x+w-.065]:self.box(xx,y+.05,z+.64,.04,d-.1,.045,'wood')
  if self.key=='bohemian':
   for i in range(8):self.rod([x+.06+i*.074,by+.075,z+.51],[x+.06+i*.074,by+.075,z+.85],.014,'light')
 def table(self,x,y,w,d,h=.42,roundtop=False,name='茶几'):
  z=BASE[self.floor]+.03;self.item(name,x,y,w,d)
  metal=self.key in ['industrial','eclectic']
  if roundtop:
   self.cyl(x+w/2,y+d/2,z+h-.055,min(w,d)/2,.055,'light' if self.key=='eclectic' else 'wood')
   self.cyl(x+w/2,y+d/2,z,.055,h-.055,'metal' if metal else 'wood')
   self.cyl(x+w/2,y+d/2,z,.22,.035,'metal' if metal else 'wood')
  elif self.key=='wabisabi' and h<.5:
   pts=[(x,y+.12*d),(x+.6*w,y),(x+w,y+.3*d),(x+.84*w,y+d),(x+.15*w,y+.86*d)]
   m=tm.creation.extrude_polygon(Polygon(pts),.065,engine='earcut');m.apply_translation([0,0,z+h-.065]);self.mesh(m)
   self.legs(x+.08,y+.05,z,w-.16,d-.1,h-.065)
  else:
   self.box(x,y,z+h-.06,w,d,.06,'wood',rounded=.035)
   self.legs(x,y,z,w,d,h-.06,'metal' if metal else 'wood')
   if self.key=='industrial':
    for xx in [x+.08,x+w-.08]:self.rod([xx,y+.07,z+.08],[xx,y+d-.07,z+h-.08],.022,'metal')
 def rug(self,x,y,w,d):
  z=BASE[self.floor]+.018;self.item('地毯',x,y,w,d,False)
  self.box(x,y,z,w,d,.008,'rug','decor',rounded=.05)
  if self.key in ['bohemian','eclectic']:
   for i in range(7):
    xx=x+.16+i*(w-.4)/7;self.box(xx,y+.12,z+.009,.09,d-.24,.004,'accent' if i%2 else 'light','decor')
   if self.key=='bohemian':
    for yy in [y+.25,y+d-.5]:
     for i in range(5):self.box(x+.18+i*w/5,yy,z+.013,.22,.22,.004,'fabric','decor',rounded=.06)
 def plant(self,x,y,dry=False):
  z=BASE[self.floor]+.03;self.item('枯枝陶器' if dry else '盆栽',x-.2,y-.2,.4,.4,False)
  self.cyl(x,y,z,.15,.28,'clay','decor')
  for i in range(5 if dry else 9):
   a=i*2.4;end=[x+math.cos(a)*.24,y+math.sin(a)*.24,z+.6+(i%3)*.14]
   self.rod([x,y,z+.2],end,.009,'wood','decor')
   if not dry:
    for k in range(3):
     lf=fd.leaf(length=.15,width=.05,droop=.55)
     lf.apply_transform(tm.transformations.rotation_matrix(.5,[0,1,0]))
     lf.apply_transform(tm.transformations.rotation_matrix(a+k*2.1,[0,0,1]))
     lf.apply_translation(end);self.mesh(lf,'green','decor')
 def art(self,x,y,w=1,h=.7):
  z=BASE[self.floor]+1.25;self.item('原創幾何畫作',x,y,w,.08,False)
  self.box(x,y,z,w,.065,h,'metal' if self.key=='eclectic' else 'wood','decor')
  self.box(x+.035,y+.066,z+.035,w-.07,.008,h-.07,'white','decor')
  n=2 if self.key=='wabisabi' else 5
  for i in range(n):
   self.box(x+.09+i*(w-.18)/n,y+.075,z+.09+(i%2)*h*.25,(w-.2)/n*.7,.006,h*(.35 if i%2 else .55),'ink' if self.key=='wabisabi' else ['fabric','accent','light'][i%3],'decor')
 def track(self,x,y,w=2.2):
  z=BASE[self.floor]+2.65;self.item('展示軌道燈',x,y,w,.16,False)
  self.box(x,y,z,w,.035,.035,'metal','fixture')
  for i in range(3):
   xx=x+.2+i*(w-.4)/2
   self.cyl(xx,y+.02,z-.15,.055,.15,'metal','fixture')
   self.cyl(xx,y+.02,z-.155,.05,.008,'light','fixture')
 def bed(self,x,y,w=1.5,d=2,head_high=False,head_dir=None,head_target=None):
  z=BASE[self.floor]+.03
  meta=dict(head_side=('+y' if head_high else '-y'),headboard_y=(y+d-.09 if head_high else y))
  if head_dir:meta['head_direction']=head_dir
  if head_target:meta['head_target']=head_target
  self.item('床組',x,y,w,d,**meta)
  self.box(x,y,z,w,d,.23,'wood',rounded=.04)
  self.soft(x+.02,y+.03,z+.23,w-.04,d-.05,.22,'light',rounding=.24)
  # Headboard, pillows and duvet flip to whichever short edge is the head.
  hb=y+d-.09 if head_high else y
  self.box(x,hb,z+.12,w,.09,.75,'wood',rounded=.025)
  if head_high:
   self.drape(x+.02,y+.03,z+.4,w-.04,d-.55,.11,'fabric')
   for i in range(1 if w<1.1 else 2):self.soft(x+.1+i*w/2,y+d-.49,z+.45,w*.38,.34,.14,'white',rounding=.58)
   if w>1.1:self.table(x+w+.12,y+d-.52,.38,.4,.4,name='床邊桌')
  else:
   self.drape(x+.02,y+.5,z+.4,w-.04,d-.55,.11,'fabric')
   for i in range(1 if w<1.1 else 2):self.soft(x+.1+i*w/2,y+.15,z+.45,w*.38,.34,.14,'white',rounding=.58)
   if w>1.1:self.table(x+w+.12,y+.12,.38,.4,.4,name='床邊桌')
 def desk(self,x,y,w=1.4,d=.65):
  self.table(x,y,w,d,.75,name='創作／書寫桌');self.chair(x+(w-.65)/2,y+d+.15,True)
  z=BASE[self.floor]+.8;self.box(x+.12,y+.1,z,.38,.3,.025,'white','decor')
 def vase(self,x,y,z):
  self.cyl(x,y,z,.09,.2,'clay','decor')
  self.cyl(x,y,z+.2,.045,.1,'clay','decor')
 def lounge(self,floor,x,y,compact=False):
  self.floor=floor;self.room='客廳兼餐廳' if floor==2 else '起居室'
  w=2.1 if compact else 2.4
  self.rug(x-.1,y+.3,w+1.4,2.0 if compact else 2.9)
  self.sofa(x,y,w,.85 if compact else .9)
  self.table(x+.45,y+1.3,.95,.6,.34 if self.key=='wabisabi' else .42,self.key=='eclectic')
  if not compact:self.chair(x+3.15,y+1.3,True)
  self.art(x+.2,y-.24,1.6 if self.key!='wabisabi' else 1.05,.7);self.track(x,y+.22,w)
  if self.key!='wabisabi':self.plant(x+w+.45,y+.35)
  self.vase(x+.9,y+1.58,BASE[floor]+(.405 if self.key=='wabisabi' else .475))
 def populate(self):
  # ===================== 1F =====================
  # West room -> exhibition gallery + classroom (residential lounge removed).
  self.floor=1;self.room='展覽空間／教室（西側）'
  z1=BASE[1]+.03
  for i,py in enumerate([1.35,3.55,5.75]):
   self.box(.45,py,z1,.55,.55,1.02,'metal' if i%2 else 'wood','furniture',rounded=.03)
   self.vase(.725,py+.275,z1+1.02)
   self.item('展示台座',.45,py,.55,.55)
  self.art(.35,.2,1.6,.9);self.art(2.3,.2,1.6,.9);self.art(.35,15.9,1.6,.9)
  self.track(.6,.45,2.4);self.track(3.2,.45,2.4)
  # Teaching tables + chairs, two rows, central aisle x~2.3 kept clear (>1 m).
  for ty in [9.4,12.0]:
   for c in range(2):
    tx=.4+c*3.05
    self.table(tx,ty,1.5,.7,.74,name='教學桌')
    self.chair(tx+.42,ty-.75);self.chair(tx+.42,ty+.78,True)
  self.plant(5.7,15.4)
  # East room -> lobby: reception counter + compact waiting seating.
  self.floor=1;self.room='Lobby 大廳（東側）'
  self.box(8.3,11.2,z1,2.6,.6,1.05,'wood','furniture',rounded=.04)
  self.item('接待櫃台',8.3,11.2,2.6,.6)
  self.cyl(9.6,10.85,z1,.19,.44,'metal');self.item('櫃台高椅',9.41,10.66,.38,.38,False)
  self.sofa(7.0,8.0,2.0,.82)
  self.table(7.55,8.95,.8,.55,.4,name='候客茶几')
  # ===================== 2F =====================
  self.lounge(2,8.6,6.4,True)
  self.floor=2;self.room='客廳兼餐廳／創作角';self.desk(6.95,7.4,1.35,.6)
  # Combined living/dining: dining set on the east side, passage y10.3..11.9 kept clear.
  self.room='客廳兼餐廳／用餐區';self.table(12.0,8.05,1.5,.9,.74,name='餐桌')
  for xx in [12.15,13.0]:self.chair(xx,7.25);self.chair(xx,9.1,True)
  # Narrow 2F dining -> kitchen (real counter / sink / hob / fridge).
  self.floor=2;self.room='廚房';zk=BASE[2]+.03
  self.box(12.05,.18,zk,2.1,.6,.70,'wood','furniture',rounded=.02)
  # Countertop opening and recessed basin are visible, not a sink buried in a solid box.
  top=rect(12.05,.18,14.15,.78).difference(rect(12.40,.34,12.80,.62))
  slab=tm.creation.extrude_polygon(top,.04,engine='earcut');slab.apply_translation([0,0,zk+.86]);self.mesh(slab,'light')
  self.box(13.63,.18,zk,.6,4.3,.9,'wood','furniture',rounded=.02)   # east counter run
  self.item('廚房檯面（L形）',12.05,.18,2.18,4.5)
  self.box(12.05,.18,zk+1.5,2.0,.32,.7,'wood','furniture',rounded=.02);self.item('吊櫃',12.05,.18,2.0,.32,False)
  rim=rect(12.32,.30,12.84,.66).difference(rect(12.40,.34,12.80,.62))
  basin=tm.creation.extrude_polygon(rim,.18,engine='earcut');basin.apply_translation([0,0,zk+.73]);self.mesh(basin,'metal')
  self.box(12.40,.34,zk+.72,.4,.28,.02,'metal','furniture');self.item('水槽',12.32,.30,.52,.36,False)
  self.rod([12.62,.30,zk+.9],[12.62,.30,zk+1.06],.015,'metal');self.rod([12.62,.30,zk+1.06],[12.74,.30,zk+1.02],.015,'metal')
  for gx,gy in [(13.8,1.05),(14.05,1.05),(13.8,1.5),(14.05,1.5)]:self.cyl(gx,gy,zk+.9,.07,.02,'metal','furniture')
  self.item('爐具（四口爐）',13.68,.9,.55,.75,False)
  self.box(13.66,.66,zk+1.7,.55,.55,.28,'metal','fixture');self.item('抽油煙機',13.66,.66,.55,.55,False)
  self.box(12.05,1.08,zk,.72,.7,1.85,'metal','furniture',rounded=.03);self.item('冰箱',12.05,1.08,.72,.7)
  # west door x11.88 y3.12..4.68 and front door y5.9 left clear.
  # ---- 2F bedrooms ----
  self.floor=2
  self.room='臥室一';self.bed(1,3.65,1.6,2,head_high=True,head_dir='+plan_y (toward 廁所 B)',head_target='廁所 B 隔牆 y≈5.9');self.art(1,.9,1,.55)
  self.room='臥室二';self.bed(1,8.6,1.5,2);self.art(1,8.48,1,.55)
  self.room='臥室三';self.bed(1.2,12.6,1.8,2);self.art(1.2,12.48,1,.55)
  # ===================== 3F =====================
  self.lounge(3,8.2,6.35,True)
  self.floor=3
  self.room='臥室一';self.bed(1,1.75,1.5,2,head_high=True,head_dir='+plan_y (toward 臥室二)',head_target='臥室二 側，床頭近 y≈3.88');self.art(1,.8,1,.55)
  self.room='臥室二';self.bed(1,8.3);self.art(1,8.18,1,.55)
  # 臥室三 -> worship hall (no bed; no invented deity).
  self.room='佛廳／祭祀空間';za=BASE[3]+.03
  self.box(.6,14.15,za,2.9,.7,.9,'wood','furniture',rounded=.03);self.item('神桌／供奉檯',.6,14.15,2.9,.7)
  self.box(1.05,14.4,za+.9,2.0,.35,.55,'wood','furniture',rounded=.03);self.item('佛龕（無造像）',1.05,14.4,2.0,.35,False)
  self.table(1.2,13.15,1.7,.6,.5,name='供桌')
  self.cyl(2.0,13.45,za+.5,.12,.14,'metal','decor');self.cyl(2.0,13.45,za+.64,.09,.05,'metal','decor');self.item('香爐',1.85,13.3,.3,.3,False)
  for vx in [1.45,2.6]:self.vase(vx,13.45,za+.5)
  self.item('供品（水果／花）',1.3,13.2,1.5,.5,False)
  for i in range(2):
   self.soft(1.05+i*1.15,12.25,za,.6,.55,.12,'fabric',rounding=.5);self.item('拜墊',1.05+i*1.15,12.25,.6,.55,False)
  # ===================== 4F =====================
  # Bedroom -> storage room (shelving + boxes; entry strip from y=4.4 kept clear).
  self.floor=4;self.room='儲藏間';zs=BASE[4]+.03
  for wx in [10.58,11.88]:
   for px in [wx,wx+.39]:
    for py in [.2,4.17]:self.box(px,py,zs,.03,.03,1.7,'metal','furniture')
   self.box(wx,.2,zs,.42,4.0,.05,'metal','furniture')
   for lv in range(4):self.box(wx,.2,zs+.05+lv*.5,.42,4.0,.03,'metal','furniture')
   for r in range(4):
    for cc in range(3):
     self.box(wx+.05,.35+r*.92,zs+.09+cc*.5,.32,.8,.4,'wood' if (r+cc)%2 else 'clay','decor')
   self.item('層架',wx,.2,.42,4.0)
  self.item('收納紙箱',10.58,.2,1.72,4.0,False)
  self.room='露台';self.table(1.8,7.5,.9,.9,.65,True,name='露台圓桌');self.chair(1.9,6.5);self.chair(1.9,8.6,True)
  self.plant(.9,7,self.key=='wabisabi')
  if self.key!='wabisabi':
   self.plant(4.6,9.5)
 def export(self):
  scene=tm.load(ROOT/'output/house.glb',force='scene',process=False)
  for name,g in scene.geometry.items():
   if name.endswith('_floor_finish_tile'):g.visual=tm.visual.TextureVisuals(material=self.mats['floor'])
  for (floor,mat,kind),parts in self.batches.items():
   m=tm.util.concatenate(parts);m.visual=tm.visual.TextureVisuals(material=self.mats[mat])
   name=f'STYLE_{self.key}_{floor}_{kind}_{mat}'
   scene.add_geometry(m,node_name=name,geom_name=name,parent_node_name=f'FLOOR_{floor}',metadata={'kind':kind,'style':self.key})
  blob=scene.export(file_type='glb');jl=struct.unpack_from('<I',blob,12)[0];tree=json.loads(blob[20:20+jl]);binary=blob[20+jl:]
  for m in tree['meshes']:
   for p in m['primitives']:
    for idx in p['attributes'].values():tree['bufferViews'][tree['accessors'][idx]['bufferView']]['target']=34962
    if 'indices' in p:tree['bufferViews'][tree['accessors'][p['indices']]['bufferView']]['target']=34963
  js=json.dumps(tree,ensure_ascii=False,separators=(',',':')).encode();js+=b' '*((-len(js))%4)
  blob=struct.pack('<III',0x46546c67,2,20+len(js)+len(binary))+struct.pack('<II',len(js),0x4e4f534a)+js+binary
  target=OUT/f'{self.key}.glb';temporary=target.with_suffix('.glb.tmp')
  temporary.write_bytes(blob);temporary.replace(target)
  return dict(label=self.p['label'],bytes=len(blob),sha256=hashlib.sha256(blob).hexdigest(),furnitureCount=sum(i['major'] for i in self.items),itemCount=len(self.items),items=self.items)

if __name__=='__main__':
 report={}
 for key in PALETTES:
  scheme=Scheme(key);scheme.populate();report[key]=scheme.export();print(key,report[key]['bytes'],report[key]['itemCount'])
 (OUT/'furniture-manifest.json').write_text(json.dumps({'units':'metres; plan x/y coordinates','purpose':'approximate furniture proposals; not construction or clearance certification','styles':report},ensure_ascii=False,indent=2),encoding='utf-8')
