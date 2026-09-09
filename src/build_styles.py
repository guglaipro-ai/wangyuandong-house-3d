"""Four procedural furnished concept variants; original house stays immutable."""
import sys,json,math,struct,hashlib
from pathlib import Path
from collections import defaultdict
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.deps'))
import numpy as np
import trimesh as tm
from shapely.geometry import box as rect, Polygon
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
  m=tm.creation.cylinder(r,h,sections=12);m.apply_translation([x,y,z+h/2]);self.mesh(m,mat,kind)
 def rod(self,a,b,r=.015,mat='metal',kind='furniture'):
  a=np.array(a);b=np.array(b);m=tm.creation.cylinder(r,np.linalg.norm(b-a),sections=8)
  m.apply_transform(tm.geometry.align_vectors([0,0,1],b-a));m.apply_translation((a+b)/2);self.mesh(m,mat,kind)
 def item(self,name,x,y,w,d,major=True):
  self.items.append(dict(name=name,floor=self.floor,room=self.room,footprint=[x,y,x+w,y+d],size_m=[w,d],major=major,approximate=True))
 def legs(self,x,y,z,w,d,h,mat='wood'):
  for xx in [x+.07,x+w-.07]:
   for yy in [y+.07,y+d-.07]:self.rod([xx,yy,z],[xx,yy,z+h],.027,mat)
 def sofa(self,x,y,w=2.4,d=.9):
  z=BASE[self.floor]+.03;low=self.key=='wabisabi';seat=.31 if low else .39
  self.item('低座沙發' if low else '三人沙發',x,y,w,d)
  self.legs(x,y,z,w,d,.18,'metal' if self.key=='industrial' else 'wood')
  self.box(x,y,z+.14,w,d,.19,'wood',rounded=.06)
  self.box(x+.02,y,z+seat,w-.04,.17,.42,'fabric',rounded=.06)
  for i in range(3):self.box(x+.14+i*(w-.28)/3,y+.18,z+seat-.05,(w-.34)/3,d-.23,.15,'fabric',rounded=.08)
  for xx in [x,x+w-.13]:self.box(xx,y+.12,z+.28,.13,d-.16,.3,'fabric',rounded=.04)
  n=1 if low else 3
  for i in range(n):self.box(x+.26+i*(w-.7)/max(n,1),y+.19,z+seat+.08,.32,.18,.29,'light' if i%2 else 'accent',rounded=.07)
 def chair(self,x,y,turn=False):
  z=BASE[self.floor]+.03;w=.65;d=.68;self.item('休閒單椅',x,y,w,d)
  self.legs(x,y,z,w,d,.42,'metal' if self.key=='industrial' else 'wood')
  self.box(x,y,z+.4,w,d,.12,'accent',rounded=.11 if self.key=='eclectic' else .05)
  by=y+d-.13 if turn else y
  self.box(x,by,z+.46,w,.13,.42,'accent',rounded=.06)
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
    m=tm.creation.icosphere(subdivisions=1,radius=1);m.apply_scale([.14,.065,.055]);m.apply_translation(end);self.mesh(m,'green','decor')
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
 def bed(self,x,y,w=1.5,d=2):
  z=BASE[self.floor]+.03;self.item('床組',x,y,w,d)
  self.box(x,y,z,w,d,.23,'wood',rounded=.04)
  self.box(x+.02,y+.03,z+.23,w-.04,d-.05,.2,'light',rounded=.06)
  self.box(x,y,z+.12,w,.09,.75,'wood',rounded=.025)
  self.box(x+.025,y+.62,z+.431,w-.05,d-.68,.035,'fabric',rounded=.04)
  for i in range(1 if w<1.1 else 2):self.box(x+.1+i*w/2,y+.15,z+.44,w*.38,.34,.1,'white',rounded=.09)
  if w>1.1:self.table(x+w+.12,y+.12,.38,.4,.4,name='床邊桌')
 def desk(self,x,y,w=1.4,d=.65):
  self.table(x,y,w,d,.75,name='創作／書寫桌');self.chair(x+(w-.65)/2,y+d+.15,True)
  z=BASE[self.floor]+.8;self.box(x+.12,y+.1,z,.38,.3,.025,'white','decor')
 def vase(self,x,y,z):
  self.cyl(x,y,z,.09,.2,'clay','decor')
  self.cyl(x,y,z+.2,.045,.1,'clay','decor')
 def lounge(self,floor,x,y,compact=False):
  self.floor=floor;self.room='客廳／起居室'
  w=2.1 if compact else 2.4
  self.rug(x-.1,y+.3,w+1.4,2.0 if compact else 2.9)
  self.sofa(x,y,w,.85 if compact else .9)
  self.table(x+.45,y+1.3,.95,.6,.34 if self.key=='wabisabi' else .42,self.key=='eclectic')
  if not compact:self.chair(x+3.15,y+1.3,True)
  self.art(x+.2,y-.24,1.6 if self.key!='wabisabi' else 1.05,.7);self.track(x,y+.22,w)
  if self.key!='wabisabi':self.plant(x+w+.45,y+.35)
  self.vase(x+.9,y+1.58,BASE[floor]+(.405 if self.key=='wabisabi' else .475))
 def populate(self):
  self.lounge(1,1.0,12.65)
  self.floor=1;self.room='創作區';self.desk(.8,2.0,1.9,.75);self.art(.8,1.78,1.5,.9);self.track(.8,2.3)
  if self.key=='industrial':
   z=BASE[1]+.03
   for a,b in [([3.7,3,z],[3.95,3.15,z+1.65]),([4.2,3,z],[3.95,3.15,z+1.65]),([3.95,3.8,z],[3.95,3.15,z+1.65])]:self.rod(a,b,.028,'wood')
   self.box(3.6,3.18,z+.75,.7,.045,.8,'white','decor');self.item('畫架',3.6,3,.7,.8)
   for row in range(7):
    for col in range(5):self.box(.6+col*.22+(row%2)*.1,7.1,BASE[1]+.06+row*.1,.21,.1,.09,'brick','decor')
   self.item('低矮磚色展示台',.6,7.1,1.2,.1,False)
  self.room='展覽區';self.art(.7,7.3,1.4,.9)
  self.floor=1;self.room='東側會客區';self.table(8.0,8.4,2.1,.9,.74,name='會客桌')
  for xx in [8.05,9.3]:self.chair(xx,7.55);self.chair(xx,9.48,True)
  self.lounge(2,8.6,6.4)
  self.floor=2;self.room='客廳創作角';self.desk(6.95,7.4,1.35,.6)
  self.room='餐廳';self.table(12.725,1.7,.75,1.4,.74,name='二人餐桌');self.chair(12.775,.85);self.chair(12.775,3.3,True)
  for x,y,w,room in [(1,1.5,1.6,'臥室一'),(1,8.6,1.5,'臥室二'),(1.2,12.6,1.8,'臥室三')]:
   self.room=room;self.bed(x,y,w);self.art(x,y-.12,1,.55)
  self.lounge(3,8.2,6.35,True)
  self.floor=3
  for y,room in [(1.0,'臥室一'),(8.3,'臥室二'),(12.1,'臥室三')]:self.room=room;self.bed(1,y);self.art(1,y-.12,1,.55)
  self.floor=4;self.room='臥室';self.bed(10.7,1.2,.95);self.table(10.65,4.25,1.2,.55,.75,name='書桌')
  # Small stool fits behind desk, entry strip from y=5 remains clear.
  self.cyl(11.25,3.85,BASE[4]+.03,.19,.42,'wood');self.item('書桌凳',11.06,3.66,.38,.38)
  self.room='露台';self.table(1.8,7.5,.9,.9,.65,True,name='露台圓桌');self.chair(1.9,6.5);self.chair(1.9,8.6,True)
  self.plant(.9,7,self.key=='wabisabi')
  if self.key!='wabisabi':
   self.plant(4.6,9.5);self.floor=2;self.room='客廳';self.plant(13.6,9.5)
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
