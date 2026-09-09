"""Site context from NLSC 2023 orthophoto and June 2026 visual observations.
All neighbor dimensions/elevations are estimates, not survey geometry.
Pixel coordinates below refer only to the attributed NLSC source mosaic.
"""
from pathlib import Path
import sys,math,json,hashlib,struct,shutil
from collections import defaultdict
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'.deps'))
import numpy as np,trimesh as tm
from shapely.geometry import Polygon,LineString,Point
from PIL import Image
from enhance_glb import run as texture_glb
from site_location import to_model,EN,metadata as location_metadata
OUT=ROOT/'output';(OUT/'realism').mkdir(exist_ok=True)
M=.5489642909779521
# NLSC mosaic pixel location of the supplied GPS pin. Four corners set the frame.
ORIGIN=np.array([425.05491510778666,265.177157279104]); SQ=math.sqrt(2)
def xy(px,py):
 e=(px-ORIGIN[0])*M;n=(ORIGIN[1]-py)*M
 return to_model([e,n])
def points(p):return [xy(*v) for v in p]
PAL={'wall':[217,211,197],'white':[225,225,219],'slab':[151,148,137],'brick':[135,69,47],'roof':[154,89,65],'roofdark':[88,87,75],'gold':[174,133,55],'metal':[61,68,67],'glass':[80,109,116],'wood':[102,80,57],'ground':[107,119,78],'road':[104,105,101],'porch':[174,169,155],'green':[72,93,44],'green2':[91,111,55],'green3':[58,80,40],'line':[224,222,196]}
mats={k:tm.visual.material.PBRMaterial(name=k,baseColorFactor=v+[255],roughnessFactor=.8,metallicFactor=.5 if k in ['metal','gold'] else 0,doubleSided=k.startswith('green')) for k,v in PAL.items()}
parts=defaultdict(list);features=[];rng=np.random.default_rng(20260910)
def add(m,mat):parts[mat].append(m)
def box(c,size,mat='wall'):
 m=tm.creation.box(size);m.apply_translation(c);add(m,mat)
def extr(p,h,y=0,mat='wall'):
 if p.is_empty:return
 if p.geom_type=='MultiPolygon':
  for q in p.geoms:extr(q,h,y,mat)
  return
 m=tm.creation.extrude_polygon(p,h,engine='earcut')
 m.apply_transform([[1,0,0,0],[0,0,1,y],[0,1,0,0],[0,0,0,1]]);add(m,mat)
def rod(a,b,r,mat='metal',sections=10):
 a=np.array(a);b=np.array(b);m=tm.creation.cylinder(r,np.linalg.norm(b-a),sections=sections)
 m.apply_transform(tm.geometry.align_vectors([0,0,1],b-a));m.apply_translation((a+b)/2);add(m,mat)
def localbox(origin,u,v,c,size,mat):
 x,z=origin+u*c[0]+v*c[2];m=tm.creation.box(size)
 t=np.array([[u[0],0,v[0],x],[0,1,0,c[1]],[u[1],0,v[1],z],[0,0,0,1]])
 m.apply_transform(t);add(m,mat)
def roof_rect(center,u,v,w,d,base,rise,temple=False):
 # Sloping ceramic roof with individual raised tile ribs and curved eaves.
 origin=np.array(center);segments=10 if temple else 2
 for side in [-1,1]:
  for i in range(segments):
   a=i/segments;b=(i+1)/segments
   def h(t):return base+rise*(1-t)+(0.6*t**6 if temple else 0)
   verts=[]
   for xx,t in [(-w/2,a),(w/2,a),(w/2,b),(-w/2,b)]:
    q=origin+u*xx+v*(side*d/2*t);verts.append([q[0],h(t),q[1]])
   m=tm.Trimesh(verts,[[0,1,2],[0,2,3]],process=False)
   if m.face_normals[0,1]<0:m.invert()
   add(m,'roof')
  for xx in np.arange(-w/2,w/2,.34):
   last=None
   for t in np.linspace(0,1,segments+1):
    p=origin+u*xx+v*(side*d/2*t);now=[p[0],h(t)+.04,p[1]]
    if last is not None:rod(last,now,.045,'roofdark',6)
    last=now
 if temple:
  for x in [-w/2,w/2]:
   last=None
   for t in np.linspace(-1,1,15):
    p=origin+u*x+v*(d/2*t);now=[p[0],base+rise*(1-abs(t))+.6*abs(t)**6+.15,p[1]]
    if last is not None:rod(last,now,.11,'gold',8)
    last=now
def house(label,pixels,floors=2,roof=False,color='wall',tower=False):
 p=Polygon(points(pixels));extr(p,3.05*floors,mat=color)
 coords=np.array(p.exterior.coords)[:-1];height=3.05*floors
 # Generic openings represent the observed building type; their exact layout is unmeasured.
 for i in range(len(coords)):
  a=coords[i];b=coords[(i+1)%len(coords)];L=np.linalg.norm(b-a);u=(b-a)/L;v=np.array([-u[1],u[0]])
  for level in range(floors):
   for j in range(max(1,int(L/3.2))):
    c=(j+.5)*L/max(1,int(L/3.2))
    localbox(a,u,v,[c,level*3.05+1.7,0],[min(1.35,L*.4),1.3,.09],'metal')
    localbox(a,u,v,[c,level*3.05+1.7,-.07],[min(1.2,L*.36),1.15,.055],'glass')
    localbox(a,u,v,[c,level*3.05+1.7,-.11],[.05,1.18,.07],'metal')
   localbox(a,u,v,[L/2,level*3.05+2.95,0],[L,.10,.13],'slab')
 if roof:
  a=coords[0];u=(coords[1]-a);w=np.linalg.norm(u);u/=w;v=np.array([-u[1],u[0]]);d=p.area/w
  roof_rect(np.array(p.centroid.coords[0]),u,v,w+.6,d+.6,height,1.3)
 else:
  extr(p.boundary.buffer(.10,join_style=2),.75,height,'white')
  if tower:
   c=np.array(p.centroid.coords[0]);box([c[0],height+.7,c[1]],[2.2,1.4,2.5],'white')
   rod([c[0],height+1.4,c[1]],[c[0],height+2.5,c[1]],.65,'metal',20)
 features.append(dict(label=label,type='neighbor',source='NLSC PHOTO2 2023 footprint + Google Street View June 2026 appearance',footprint_source_pixels=pixels,estimated_floors=floors,estimated_height_m=height,confidence='approximate; openings and fine profiles schematic'))

# Continuous ground and the actual NW-SE village road / NE-SW lane pattern.
box([0,-.35,0],[430,.3,430],'ground')
roads=[([(272,251),(354,288),(396,315),(474,377),(620,490)],7.2), ([(402,316),(419,273),(433,232),(466,191),(508,160)],4.4), ([(455,344),(480,280),(516,242),(547,215)],4.2), ([(355,287),(332,233),(351,199),(385,164)],3.5)]
for coords,width in roads:
 p=LineString(points(coords)).buffer(width/2,join_style=2);extr(p,.06,-.14,'road')
 features.append(dict(label='道路／巷道',type='road',source='NLSC PHOTO2 2023; widths visually estimated',source_pixels=coords,estimated_width_m=width))
 # A narrow gutter follows each side of the lane.
 for side in [-1,1]:
  line=LineString(points(coords)).parallel_offset(width/2,side='left' if side==1 else 'right')
  extr(line.buffer(.13),.08,-.11,'slab')
# Front court; no invented street labels, people, signs or vehicles.
extr(Polygon(points([(355,252),(414,256),(397,307),(347,284)])),.15,-.11,'porch')

# Temple volume / roof tiers. Ornamental sculpture is deliberately not invented.
temple=Polygon(points([(354,210),(399,206),(405,253),(354,258)]))
cx=np.array(temple.centroid.coords[0]);u=xy(399,206)-xy(354,210);u/=np.linalg.norm(u);v=np.array([-u[1],u[0]])
front=cx+v*13
front_opening=LineString([front-u*10,front+u*10]).buffer(3.0)
extr(temple.boundary.buffer(.35).difference(front_opening),5.1,mat='brick')
extr(temple,.3,.0,'slab')
localbox(front,u,v,[0,4.8,0],[24,.55,.6],'gold')
localbox(cx+v*7,u,v,[0,2.4,0],[18,3.7,.2],'wood')
for off,base,w,d,rise in [(-7,5.3,25,9,2.9),(0,6,25,10,3.7),(8,6.6,24,9,3.0)]:roof_rect(cx+v*off,u,v,w,d,base,rise,True)
for off in [-8,-4,0,4,8]:
 c=cx+u*off+v*13;rod([c[0],.4,c[1]],[c[0],5.0,c[1]],.22,'slab',18)
for i in range(5):
 c=cx+v*(14+i*.32);localbox(c,u,v,[0,.5-i*.10,0],[24,.18,.35],'slab')
features.append(dict(label='龍泉巖',type='temple',source='NLSC PHOTO2 2023; Google Street View June 2026',confidence='approximate massing, tiled roofs and front court; detailed dragons and stone sculptures not reproduced',estimated_height_m=10))

house('北側紅瓦平房',[(438,236),(460,255),(449,268),(426,247)],1,True,'brick')
house('東側白色舊住宅',[(459,276),(471,283),(461,300),(450,291)],2,False,'white',True)
house('南側白色三層住宅',[(418,283),(440,295),(425,317),(406,304)],3,False,'white',True)
house('北巷白色住宅',[(407,198),(421,209),(410,225),(398,213)],3,False,'white')
house('東南側低層住宅',[(478,295),(492,307),(481,324),(467,310)],2,True)
house('東南側住宅群一',[(465,327),(485,341),(470,361),(451,346)],2,True)
house('東南側住宅群二',[(481,351),(502,366),(489,383),(470,370)],2,True,'brick')
house('東側住宅',[(491,215),(504,225),(487,247),(474,237)],2,False,'white')
house('東北住宅一',[(478,174),(493,186),(473,210),(460,199)],2,True)
house('北側低層住宅',[(433,160),(449,173),(435,191),(420,179)],2,True)
house('東北住宅二',[(510,133),(529,148),(514,168),(495,152)],2,False,'white')
house('道路南側鐵皮農舍',[(346,316),(365,318),(365,342),(347,340)],1,True)
house('道路西側低層住宅',[(269,266),(285,267),(285,299),(267,299)],2,True)
house('路口南側建物',[(408,375),(431,386),(422,410),(402,399)],2,True,'white')
house('東南側中層住宅',[(570,392),(591,406),(575,430),(554,415)],4,False,'white',True)

# South neighbor's low block wall, visible from the vacant site.
extr(LineString(points([(414,281),(442,293),(429,317)])).buffer(.12),1.55,.05,'slab')
def tree(px,py,r=2.2,h=5,leafcount=110):
 c=xy(px,py);rod([c[0],0,c[1]],[c[0],h*.8,c[1]],.12 if h<7 else .38,'wood',10)
 for i in range(7):
  a=i*2.4;end=[c[0]+math.cos(a)*r*.55,h*.72+math.sin(i)*.35,c[1]+math.sin(a)*r*.55]
  rod([c[0],h*.38,c[1]],end,.045,'wood',7)
 verts=[];faces=[]
 for i in range(leafcount):
  angle=rng.uniform(0,2*np.pi);radius=rng.uniform(.2,1)**.5*r
  q=np.array([c[0]+math.cos(angle)*radius,h*.65+rng.uniform(-.45,.7)*r,c[1]+math.sin(angle)*radius])
  side=np.array([math.cos(angle),0,math.sin(angle)])*.28;direction=np.array([-math.sin(angle),rng.uniform(-.4,.5),math.cos(angle)])*.52
  start=len(verts);verts.extend([q-direction,q-side,q+[0,.09,0],q+side,q+direction])
  faces.extend([[start,start+1,start+2],[start,start+2,start+3],[start+1,start+4,start+2],[start+2,start+4,start+3]])
 m=tm.Trimesh(verts,faces,process=False);add(m,['green','green2','green3'][int(rng.integers(0,3))])
tree(408,254,4.1,9,750) # Large temple-side tree, observed in June 2026.
for px,py in [(410,317),(442,302),(450,302),(453,288),(431,313),(490,269),(498,276),(358,262),(343,248)]:tree(px,py,1.8,4.4,140)
# Orchard blocks recorded in the official orthophoto; canopy placement approximate.
for xmin,ymin,xmax,ymax in [(285,322,335,410),(296,386,372,477),(268,101,354,173),(482,258,535,288),(304,42,440,106),(432,418,521,480),(322,499,455,555)]:
 for x in range(xmin,xmax,16):
  for y in range(ymin,ymax,17):tree(x+rng.uniform(-2,2),y+rng.uniform(-2,2),2,4.4,65)
features.append(dict(label='果園與道路樹木',type='vegetation',source='NLSC PHOTO2 2023 and June 2026 Street View',confidence='approximate canopy distribution; species and individual tree positions not surveyed'))
# Poles and sagging utility cables observed on the lane.
poles=[]
for px,py in [(411,277),(402,307),(427,243),(444,218)]:
 c=xy(px,py);poles.append(c);rod([c[0],0,c[1]],[c[0],7.5,c[1]],.10,'slab',14)
 rod([c[0],6,c[1]],[c[0]+1.4,6.65,c[1]],.045,'metal')
 box([c[0]+1.5,6.6,c[1]],[.6,.08,.25],'metal')
for a,b in zip(poles,poles[1:]):
 for offset in [-.16,.16,.35]:
  last=None
  for t in np.linspace(0,1,12):
   c=a*(1-t)+b*t;now=[c[0]+offset,7.1-.5*math.sin(t*math.pi),c[1]]
   if last is not None:rod(last,now,.012,'metal',5)
   last=now
features.append(dict(label='路燈電桿與架空線',type='utilities',source='June 2026 Street View',confidence='approximate; not utility survey'))
scene=tm.Scene(base_frame='CONTEXT_WORLD');scene.graph.update(frame_to='SURROUNDINGS',frame_from='CONTEXT_WORLD',metadata={'kind':'context','approximate':True})
for mat,meshes in parts.items():
 m=tm.util.concatenate(meshes);m.visual=tm.visual.TextureVisuals(material=mats[mat]);scene.add_geometry(m,node_name='CONTEXT_'+mat,geom_name='CONTEXT_'+mat,parent_node_name='SURROUNDINGS',metadata={'kind':'context','approximate':True})
file=OUT/'surroundings.glb';temp=file.with_suffix('.tmp');temp.write_bytes(scene.export(file_type='glb'));temp.replace(file)
result=texture_glb(file,'context')
shutil.copyfile(ROOT/'tmp/nlsc-context.jpg',OUT/'realism/nlsc-reference.jpg')
metadata={'site_pin':[23.178193459074407,120.25725453748464],'date':'2026-09-10 UTC+8','north_reference':'PDF window schedule: plan left=NE, rear=SE, right=SW, front=NW; rotation fitted to four user map-click corners','alignment':location_metadata(),'source_imagery':'NLSC PHOTO2 mosaic carries NLSC 2023 mark; Google Street View observed June 2026, imagery not copied into the model','reference_license':'https://maps.nlsc.gov.tw/pro/use_clause.jsp','street_view':'https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=23.1782064,120.257168','map':'https://maps.nlsc.gov.tw/','features':features,'model':{k:v for k,v in result.items() if k!='proof'}}
(OUT/'realism/site-location.json').write_text(json.dumps(location_metadata(),ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'realism/site-context.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(metadata['model']))
