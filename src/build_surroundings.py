"""Site context from NLSC 2023 orthophoto and June 2026 visual observations.
All neighbor dimensions/elevations are estimates, not survey geometry.
Pixel coordinates below refer only to the attributed NLSC source mosaic.
"""
from pathlib import Path
import sys,math,json,hashlib,struct,shutil
from collections import defaultdict
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'.deps'))
import numpy as np,trimesh as tm
from shapely.geometry import Polygon,LineString,Point,MultiPoint,mapping,shape
from shapely.affinity import translate
from shapely.ops import unary_union,nearest_points
from PIL import Image
from enhance_glb import run as texture_glb
from site_location import to_model,EN,MODEL,metadata as location_metadata
OUT=ROOT/'output';(OUT/'realism').mkdir(exist_ok=True)
M=.5489642909779521
# NLSC mosaic pixel location of the supplied GPS pin. Four corners set the frame.
ORIGIN=np.array([425.05491510778666,265.177157279104]); SQ=math.sqrt(2)
def xy(px,py):
 e=(px-ORIGIN[0])*M;n=(ORIGIN[1]-py)*M
 return to_model([e,n])
def points(p):return [xy(*v) for v in p]
PAL={'steel':[200,203,205],'wall':[217,211,197],'white':[225,225,219],'slab':[151,148,137],'brick':[135,69,47],'roof':[154,89,65],'roofdark':[88,87,75],'gold':[174,133,55],'metal':[61,68,67],'glass':[80,109,116],'wood':[102,80,57],'ground':[107,119,78],'road':[104,105,101],'porch':[174,169,155],'green':[72,93,44],'green2':[91,111,55],'green3':[58,80,40],'line':[224,222,196],'water':[64,98,104],'temple':[158,156,148]}
mats={k:tm.visual.material.PBRMaterial(name=k,baseColorFactor=v+[255],roughnessFactor=.35 if k=='steel' else .06 if k=='water' else .8,metallicFactor=.85 if k=='steel' else .5 if k in ['metal','gold'] else 0,doubleSided=k.startswith('green')) for k,v in PAL.items()}
parts=defaultdict(list);features=[];rng=np.random.default_rng(20260910)
site_protection=Polygon(MODEL).buffer(.35)          # permit lot 318 (site_location)
neighbor_envelopes=[]
base_scene=tm.load(OUT/'realism/architecture-baseline.glb',force='scene',process=False)
house_envelope=MultiPoint(np.concatenate([g.vertices[:,[0,2]] for n,g in base_scene.geometry.items() if n.startswith(('FLOOR_','ROOF_'))])).convex_hull
near_labels={'北側紅瓦平房','東側白色舊住宅','南側白色三層住宅'}
road_surfaces=[]
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
def roof_rect(center,u,v,w,d,base,rise,temple=False,rib=.34):
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
  for xx in np.arange(-w/2,w/2,rib):
   last=None
   for t in np.linspace(0,1,segments+1):
    p=origin+u*xx+v*(side*d/2*t);now=[p[0],h(t)+.04,p[1]]
    if last is not None:rod(last,now,.045,'roofdark',4)   # 4-sided ribs: same silhouette at viewing distance
    last=now
 if temple:
  for x in [-w/2,w/2]:
   last=None
   for t in np.linspace(-1,1,15):
    p=origin+u*x+v*(d/2*t);now=[p[0],base+rise*(1-abs(t))+.6*abs(t)**6+.15,p[1]]
    if last is not None:rod(last,now,.11,'gold',8)
    last=now
def house(label,p,floors=2,roof=False,color='wall',tower=False,source=''):
 """Building on its e-map footprint p (model x/z). No relocation: positions are surveyed-map
 outlines; the only edit is clipping a few cm off where a footprint touches the new house."""
 p=p.difference(house_envelope.buffer(.3)).buffer(0)
 if p.geom_type!='Polygon':p=max(getattr(p,'geoms',[p]),key=lambda g:g.area)
 if p.area<4:return
 p=Polygon(p.exterior.coords).simplify(.3,preserve_topology=True)
 rect_ratio=p.area/p.minimum_rotated_rectangle.area
 # irregular pitched-roof plans are split into rectangular roof parts below
 envelope=p.buffer(.2);neighbor_envelopes.append(envelope)
 starts={k:len(v) for k,v in parts.items()}
 extr(p,3.05*floors,mat=color)
 coords=np.array(p.exterior.coords)[:-1];height=3.05*floors
 # Generic openings represent the observed building type; their exact layout is unmeasured.
 # Typological Taiwanese village-house details (not individually observed): framed
 # aluminium windows with reflective glass, iron grilles (鐵窗) on the ground floor, an
 # entrance (roller shutter + side door on long road-facing walls), plinth and downpipes.
 # Everything stays within 0.17 m of the wall so the clearance envelope above still holds.
 poly=Polygon(coords)
 # Full typological detail only where it is seen from the site (within ~30 m); far houses
 # keep framed windows so the delivery archive stays under the 100 MiB hosting limit.
 dist=poly.distance(house_envelope);near=dist<35
 road_lines=list(road_edges)
 edges=[]
 for i in range(len(coords)):
  a=coords[i];b=coords[(i+1)%len(coords)];L=np.linalg.norm(b-a);u=(b-a)/L;v=np.array([-u[1],u[0]])
  out=-v if poly.contains(Point(*(a+u*L/2+v*.05))) else v      # outward wall normal
  edges.append((a,b,L,u,out,min((l.distance(Point(*(a+u*L/2))) for l in road_lines),default=99)))
 front=min(range(len(edges)),key=lambda i:edges[i][5]-edges[i][2]*.15)
 def face(a,u,out,s,y,w,h,d,off,mat):
  # local box on a wall face: s along wall, y up, off outward from the wall line
  q=a+u*s+out*(off);m=tm.creation.box([w,h,d]);x=u if u[0]*out[1]-out[0]*u[1]>0 else -u   # keep a proper rotation
  m.apply_transform(np.array([[x[0],0,out[0],q[0]],[0,1,0,y],[x[1],0,out[1],q[1]],[0,0,0,1]]));add(m,mat)
 for i,(a,b,L,u,out,_) in enumerate(edges):
  doors=[]
  if dist>80 or L<2.4:
   if near:
    for level in range(floors):face(a,u,out,L/2,level*3.05+2.95,L,.10,.13,0,'slab')
   continue
  if i==front:
   if L>5.5 and floors>=2:doors=[(L*.42,2.9,2.6,'shutter'),(L*.42+2.25,.95,2.15,'door')]
   else:doors=[(L/2,1.5,2.2,'door')]
  if near:face(a,u,out,L/2,.25,L,.5,.04,.02,'slab')              # plinth 50 cm
  for s0,w,h,typ in doors:
   face(a,u,out,s0,h/2,w+.16,h+.08,.06,.03,'metal')
   if typ=='shutter':
    face(a,u,out,s0,h/2,w,h,.02,.065,'white')
    for z in np.arange(.12,h,.24 if near else .6):face(a,u,out,s0,z,w,.018,.012,.08,'slab')
    face(a,u,out,s0,h+.22,w+.16,.36,.14,.07,'white')            # shutter box
   else:
    face(a,u,out,s0,h/2,w,h,.03,.06,'wood')
    face(a,u,out,s0+w*.3,1.0,.04,.25,.04,.09,'metal')
  for level in range(floors):
   n=max(1,int(L/3.2))
   for j in range(n):
    c=(j+.5)*L/n;z=level*3.05+1.7;ww=min(1.35,L*.4)
    if level==0 and any(abs(c-s0)<(w+ww)/2+.2 for s0,w,_,_ in doors):continue
    face(a,u,out,c,z,ww,1.3,.03,.015,'glass')
    if not near:
     face(a,u,out,c,z,.05,1.3,.06,.03,'metal');continue
    for dz in (-.625,.625):face(a,u,out,c,z+dz,ww,.05,.06,.03,'metal')
    for ds in (-ww/2+.025,0,ww/2-.025):face(a,u,out,c+ds,z,.05,1.3,.06,.03,'metal')
    face(a,u,out,c,z-.7,ww+.12,.06,.12,.06,'slab')                # sill
    if level==0 or (level==1 and floors>=3):
     # 鐵窗: box grille standing 12 cm proud of the facade
     for ds in np.arange(-ww/2,ww/2+.01,.15):face(a,u,out,c+ds,z,.02,1.4,.02,.13,'metal')
     for dz in (-.7,-.25,.25,.7):face(a,u,out,c,z+dz,ww+.04,.025,.025,.13,'metal')
     for side in (-1,1):face(a,u,out,c+side*(ww/2+.02),z,.02,1.4,.12,.075,'metal')
   if near:face(a,u,out,L/2,level*3.05+2.95,L,.10,.13,0,'slab')
 if not roof and near:
  # downpipes at two opposite corners, rooftop stainless tank on a steel stand
  for k in (0,2):
   a,b,L,u,out,_=edges[k%len(edges)];q=a+u*.25+out*.09
   rod([q[0],0,q[1]],[q[0],3.05*floors+.7,q[1]],.05,'white',8)
  if not tower:
   c=np.array(p.centroid.coords[0])+edges[1][3]*min(1.2,edges[1][2]*.2);h0=3.05*floors
   for dx,dz in ((-.45,-.45),(.45,-.45),(.45,.45),(-.45,.45)):rod([c[0]+dx,h0,c[1]+dz],[c[0]+dx,h0+.6,c[1]+dz],.03,'metal',6)
   box([c[0],h0+.62,c[1]],[1.1,.05,1.1],'metal')
   rod([c[0],h0+.65,c[1]],[c[0],h0+1.95,c[1]],.55,'steel',20)
   rod([c[0],h0+1.95,c[1]],[c[0],h0+2.05,c[1]],.3,'steel',16)
 if roof:
  # Irregular outlines (house + annexes) get one pitched roof per rectangular part: the plan
  # is rasterised (0.5 m) in its main axes and runs are merged into rectangles.
  r=np.array(p.minimum_rotated_rectangle.exterior.coords)[:4];e0=r[1]-r[0];e1=r[2]-r[1]
  u=e0/np.linalg.norm(e0) if np.linalg.norm(e0)>=np.linalg.norm(e1) else e1/np.linalg.norm(e1);v=np.array([-u[1],u[0]])
  o=np.array(p.centroid.coords[0]);loc=Polygon([((np.array(q)-o)@u,(np.array(q)-o)@v) for q in p.exterior.coords])
  x0,y0,x1,y1=loc.bounds;G=.5;xs=np.arange(x0+G/2,x1,G);ys=np.arange(y0+G/2,y1,G)
  from shapely import contains_xy
  gx,gy=np.meshgrid(xs,ys);M=contains_xy(loc,gx,gy)
  rects=[];openr={}
  for j in range(len(ys)+1):
   runs=set()
   if j<len(ys):
    d=np.diff(np.concatenate([[0],M[j].astype(np.int8),[0]]));runs={(a,b) for a,b in zip(np.nonzero(d==1)[0],np.nonzero(d==-1)[0]) if b-a>=6}
   for k in list(openr):
    if k not in runs:rects.append((k,openr.pop(k),j))
   for k in runs:openr.setdefault(k,j)
  for (a,b),j0,j1 in rects:
   w_,d_=(b-a)*G,(j1-j0)*G
   if w_*d_<9 or d_<2.5:continue
   c=o+u*(xs[a]-G/2+w_/2)+v*(ys[j0]-G/2+d_/2)
   uu,vv,ww,dd=(u,v,w_,d_) if w_>=d_ else (v,-u,d_,w_)
   roof_rect(c,uu,vv,ww+.4,dd+.4,height,min(1.3,dd*.18),rib=.34 if near else .9)
 else:
  extr(p.boundary.buffer(.10,join_style=2),.75,height,'white')
  if tower:
   c=np.array(p.centroid.coords[0]);box([c[0],height+.7,c[1]],[2.2,1.4,2.5],'white')
   rod([c[0],height+1.4,c[1]],[c[0],height+2.5,c[1]],.65,'metal',20)
 features.append(dict(label=label,type='neighbor',source=source,footprint_model_xz=mapping(p),built_envelope_xz=mapping(envelope),house_clearance_m=float(p.distance(house_envelope)),estimated_floors=floors,estimated_height_m=height,roof='pitched' if roof else 'flat',confidence='footprint from NLSC e-map (1/1000 base); storeys from Street View notes where available, otherwise estimated'))

# Continuous ground; roads, canal and building footprints from the NLSC e-map trace
# (src/site_trace.py -> output/realism/site-trace.json). Earlier hand-traced road bands
# ran 6-7 m east of the real lane and over the neighbours; they are no longer used.
box([0,-.35,0],[430,.3,430],'ground')
TRACE=json.loads((OUT/'realism/site-trace.json').read_text(encoding='utf-8'))
REACH=Point(0,0).buffer(205)
road_union=unary_union([shape(r['model_xz']) for r in TRACE['roads']]).intersection(REACH).difference(site_protection.buffer(-.35)).buffer(0).buffer(.8,join_style=1).buffer(-.8,join_style=1).simplify(.2)
road_edges=[LineString(r.coords) for g in getattr(road_union,'geoms',[road_union]) for r in [g.exterior,*g.interiors]]
road_reservation=road_union
LANE_AXIS_PX=[(402,316),(419,273),(433,232),(466,191),(508,160)]
water=unary_union([shape(w['model_xz']) for w in TRACE['water']]).intersection(REACH).buffer(0)
def render_roads():
 exclusion=unary_union([temple_built,*neighbor_envelopes])
 surface=road_union.difference(exclusion);extr(surface,.06,-.14,'road');road_surfaces.append(surface)
 features.append(dict(label='道路／巷道',type='road',source='NLSC e-map (2026-08) road surfaces, traced at zoom 19',built_footprint_xz=mapping(surface),area_m2=surface.area))
 # kerb / gutter line along every road edge, not across driveways into buildings
 extr(road_union.boundary.buffer(.12).intersection(Point(0,0).buffer(90)).difference(exclusion).difference(site_protection.buffer(-.4)),.08,-.11,'slab')
 if not water.is_empty:
  # irrigation canal: water surface 1.2 m below grade inside 25 cm concrete banks
  extr(water,.05,-1.25,'water');extr(water.boundary.buffer(.25).difference(road_union),1.35,-1.25,'slab')
  features.append(dict(label='排水溝渠',type='water',source='NLSC e-map water layer',built_footprint_xz=mapping(water)))
# Temple front court; no invented street labels, people, signs or vehicles.
extr(Polygon(points([(355,252),(414,256),(397,307),(347,284)])).difference(road_reservation).difference(site_protection),.15,-.11,'porch')

# Temple volume / roof tiers. Ornamental sculpture is deliberately not invented.
temple=Polygon(points([(354,210),(399,206),(405,253),(354,258)]))
temple_starts={k:len(v) for k,v in parts.items()}
cx=np.array(temple.centroid.coords[0]);u=xy(399,206)-xy(354,210);u/=np.linalg.norm(u);v=np.array([-u[1],u[0]])
front=cx+v*13
front_opening=LineString([front-u*10,front+u*10]).buffer(3.0)
# Side walls seen from the lane (Street View 2026-06): grey stone two-storey facade with
# window bays and an upper balcony band, not a plain brick enclosure.
ring=temple.boundary.buffer(.35).difference(front_opening)
extr(ring,5.1,mat='temple')
tc=np.array(temple.exterior.coords)[:-1]
for i in range(len(tc)):
 a,b=tc[i],tc[(i+1)%len(tc)];L=np.linalg.norm(b-a);uu=(b-a)/L;nn=np.array([-uu[1],uu[0]])
 if temple.contains(Point(*(a+uu*L/2+nn*.5))):nn=-nn
 for k in range(int(L/3.4)):
  c=a+uu*(1.7+k*3.4)
  if front_opening.contains(Point(*c)):continue
  for zc,hh in ((1.7,1.5),(4.1,1.1)):localbox(c+nn*.36,uu,nn,[0,zc,0],[1.5,hh,.06],'glass')
 band=LineString([a,b]).buffer(.75,cap_style=2).difference(temple.buffer(-.2)).difference(front_opening)
 extr(band,.15,3.2,'temple')
extr(temple,.3,.0,'slab')
localbox(front,u,v,[0,4.8,0],[24,.55,.6],'gold')
localbox(cx+v*7,u,v,[0,2.4,0],[18,3.7,.2],'wood')
for off,base,w,d,rise in [(-7,5.3,25,9,2.9),(0,6,25,10,3.7),(8,6.6,24,9,3.0)]:roof_rect(cx+v*off,u,v,w,d,base,rise,True)
for off in [-8,-4,0,4,8]:
 c=cx+u*off+v*13;rod([c[0],.4,c[1]],[c[0],5.0,c[1]],.22,'slab',18)
for i in range(5):
 c=cx+v*(14+i*.32);localbox(c,u,v,[0,.5-i*.10,0],[24,.18,.35],'slab')
temple_built=MultiPoint(np.concatenate([m.vertices[:,[0,2]] for k,meshes in parts.items() for m in meshes[temple_starts.get(k,0):]])).convex_hull
features.append(dict(label='龍泉巖',type='temple',built_envelope_xz=mapping(temple_built),source='NLSC PHOTO2 2023; Google Street View June 2026',confidence='approximate massing, tiled roofs and front court; detailed dragons and stone sculptures not reproduced',estimated_height_m=10))

# Storey/roof notes per building from June 2026 Street View (earlier hand-traced
# footprints, used only to carry attributes to the matching e-map footprint).
HINTS=[('北側紅瓦平房',[(438,236),(460,255),(449,268),(426,247)],1,True,'brick',False),
 ('東側白色舊住宅',[(459,276),(471,283),(461,300),(450,291)],2,False,'white',True),
 ('南側白色三層住宅',[(418,283),(440,295),(425,317),(406,304)],3,False,'white',True),
 ('北巷白色住宅',[(407,198),(421,209),(410,225),(398,213)],3,False,'white',False),
 ('東南側低層住宅',[(478,295),(492,307),(481,324),(467,310)],2,True,'wall',False),
 ('東南側住宅群一',[(465,327),(485,341),(470,361),(451,346)],2,True,'wall',False),
 ('東南側住宅群二',[(481,351),(502,366),(489,383),(470,370)],2,True,'brick',False),
 ('東側住宅',[(491,215),(504,225),(487,247),(474,237)],2,False,'white',False),
 ('東北住宅一',[(478,174),(493,186),(473,210),(460,199)],2,True,'wall',False),
 ('北側低層住宅',[(433,160),(449,173),(435,191),(420,179)],2,True,'wall',False),
 ('東北住宅二',[(510,133),(529,148),(514,168),(495,152)],2,False,'white',False),
 ('道路南側鐵皮農舍',[(346,316),(365,318),(365,342),(347,340)],1,True,'wall',False),
 ('道路西側低層住宅',[(269,266),(285,267),(285,299),(267,299)],2,True,'wall',False),
 ('路口南側建物',[(408,375),(431,386),(422,410),(402,399)],2,True,'white',False),
 ('東南側中層住宅',[(570,392),(591,406),(575,430),(554,415)],4,False,'white',True)]
hint_polys=[(h,Polygon(points(h[1]))) for h in HINTS]
used=set();footprints=[]
for k,b in enumerate(sorted(TRACE['buildings'],key=lambda b:Point(b['centroid_xz']).distance(house_envelope))):
 p=shape(b['model_xz'])
 if p.distance(house_envelope)>140 or p.intersection(temple_built).area>.4*p.area:continue
 match=max(((h,p.intersection(q).area/min(p.area,q.area)) for h,q in hint_polys if h[0] not in used),key=lambda t:t[1],default=(None,0))
 r,g,bl=b['roof_rgb']
 if match[1]>.25:
  h=match[0];used.add(h[0]);label,floors,roof,color,tower=h[0],h[2],h[3],h[4],h[5];src='NLSC e-map footprint; storeys/roof from June 2026 Street View notes'
 else:
  tin=bl>r+4 and bl>120;red=r-g>22 and r-bl>28
  label=f'鄰房{k+1:03d}';floors=1 if (tin or p.area<32) else 2;roof=red or tin;color='white' if (r+g+bl)/3>165 else 'wall';tower=False
  src='NLSC e-map footprint; roof type from 2023 orthophoto colour, storeys estimated'
 house(label,p,floors,roof,color,tower,src);footprints.append(p)
render_roads()
built_area=unary_union(footprints+[temple_built])

def tree(px,py,r=2.2,h=5,leafcount=110,observed=False):
 c=xy(px,py)
 if observed:
  # observed trees stay, but the trunk is pushed off the asphalt to the nearest verge
  if Point(c).buffer(.5).intersects(road_union):
   q=nearest_points(Point(c),road_union.buffer(.8).boundary)[1];c=np.array(q.coords[0])
 elif Point(c).buffer(.5).intersects(unary_union([built_area,road_union,water,site_protection])):return
 rod([c[0],0,c[1]],[c[0],h*.8,c[1]],.12 if h<7 else .38,'wood',10)
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
tree(408,254,4.1,9,750,True) # Large temple-side banyan, observed in June 2026.
for px,py in [(410,317),(442,302),(450,302),(453,288),(431,313),(490,269),(498,276),(358,262),(343,248)]:tree(px,py,1.8,4.4,140)
# Orchard blocks recorded in the official orthophoto; canopy placement approximate.
for xmin,ymin,xmax,ymax in [(285,322,335,410),(296,386,372,477),(268,101,354,173),(482,258,535,288),(304,42,440,106),(432,418,521,480),(322,499,455,555)]:
 for x in range(xmin,xmax,16):
  for y in range(ymin,ymax,17):tree(x+rng.uniform(-2,2),y+rng.uniform(-2,2),2,4.4,65)
features.append(dict(label='果園與道路樹木',type='vegetation',source='NLSC PHOTO2 2023 and June 2026 Street View',confidence='approximate canopy distribution; species and individual tree positions not surveyed'))
# Street lights and utility poles observed in Google Street View (June 2026), positions
# triangulated from three panoramas (lane at the site, junction, 28 m north); about
# 1-2 m uncertainty. Each base is snapped just outside the e-map asphalt edge.
OBS_POLES=[('B','streetlight',(-9.05,-3.96),'lane east edge at the lot SW corner, beside the block wall'),
 ('L2','streetlight',(-14.05,-21.8),'lane east edge, about 18 m south of B'),
 ('A','utility_lamp',(-14.6,-28.9),'yellow/black striped pole at the lane / main-road corner'),
 ('C','utility',(-1.21,22.2),'striped pole on the lane east edge by the red-brick yard wall'),
 ('D','utility_lamp',(-5.45,25.1),'striped pole with LED head at the temple north-east corner')]
poles=[];pole_records=[]
road_union_all=unary_union(road_surfaces)
pole_forbidden=unary_union([house_envelope.buffer(.3),temple_built.buffer(.15),built_area.buffer(.1)])
def stripe_pole(c,h):
 rod([c[0],0,c[1]],[c[0],h,c[1]],.13 if h>8 else .10,'slab',14)
 for k in range(8):   # Taipower yellow/black safety stripes on the lowest 2 m
  rod([c[0],.25*k,c[1]],[c[0],.25*k+.25,c[1]],.135,'gold' if k%2==0 else 'metal',14)
for key,typ,en,note in OBS_POLES:
 q=Point(to_model(en))
 edge=road_union_all.buffer(.28).boundary;near=nearest_points(q,edge)[1]
 c=np.array(near.coords[0])
 if Point(c).buffer(.12).intersects(pole_forbidden):c=np.array(q.coords[0])
 inward=np.array(nearest_points(Point(c),road_union_all)[1].coords[0])-c;inward/=max(np.linalg.norm(inward),1e-6)
 if typ=='streetlight':
  # galvanised steel pole, 8 m, curved outreach arm 1.8 m and LED head
  rod([c[0],0,c[1]],[c[0],7.2,c[1]],.075,'steel',14)
  last=[c[0],7.2,c[1]]
  for t in np.linspace(0,1,7)[1:]:
   pnt=c+inward*1.8*t;now=[pnt[0],7.2+.75*math.sin(t*math.pi/2),pnt[1]];rod(last,now,.04,'steel',8);last=now
  head=c+inward*1.95;box([head[0],7.9,head[1]],[.62,.09,.26],'steel')
 else:
  stripe_pole(c,9.5);poles.append(c)
  across=np.array([-inward[1],inward[0]]);box([c[0],8.7,c[1]],[1.6*abs(across[0])+.1,.1,1.6*abs(across[1])+.1],'wood')  # cross-arm
  if typ=='utility_lamp':
   arm=c+inward*1.2;rod([c[0],6.6,c[1]],[arm[0],7.0,arm[1]],.04,'steel',8);box([arm[0],6.95,arm[1]],[.5,.08,.22],'steel')
 pole_records.append(dict(id=key,type=typ,observed_east_north=list(en),center_model_xz=c.tolist(),radius_m=.13 if typ!='streetlight' else .075,
                          road_edge_distance_m=Point(c).distance(road_union_all),note=note))
# Overhead lines between the observed utility poles, in lane order.
lane_axis=LineString(points(LANE_AXIS_PX))
poles.sort(key=lambda c:lane_axis.project(Point(c)))
for a,b in zip(poles,poles[1:]):
 for offset in [-.5,0,.5]:
  last=None
  for t in np.linspace(0,1,14):
   c=a*(1-t)+b*t;now=[c[0]+offset*.6,8.6-.6*math.sin(t*math.pi),c[1]+offset*.6]
   if last is not None:rod(last,now,.012,'metal',5)
   last=now
features.append(dict(label='路燈電桿與架空線',type='utilities',poles=pole_records,source='Google Street View June 2026 panoramas ql_QZTnMdwUm36kTXeddWg, osS7BUzyUgwC_IYvavd0qA, RJICdZ330YwCkiFck9NJhg (viewed, not copied); bearings and ground-contact angles triangulated',confidence='about 1-2 m; heights and arm lengths typical, not measured'))
# Observed boundary walls (Street View): concrete-block wall of the SW neighbour along the
# lane and along lot 318's SW line; low red-brick yard wall of No.21 along the lane.
from site_location import PARCEL_MODEL
par=Polygon(PARCEL_MODEL)
P=list(par.exterior.coords)
sw_line=LineString([P[0],P[1],P[2]])            # lane frontage corner -> 界7 (shared with the 3-storey SW house)
extr(sw_line.buffer(.1,cap_style=2).difference(house_envelope.buffer(.2)),1.7,0,'slab')
lane_dir=np.subtract(P[0],P[9]);lane_dir/=np.linalg.norm(lane_dir)       # 界5 -> 界6, along the lane edge
in_lot=np.array(par.centroid.coords[0])-np.array(P[0]);side=np.sign(in_lot@np.array([-lane_dir[1],lane_dir[0]]))
off=np.array([-lane_dir[1],lane_dir[0]])*side*.12                        # keep walls just inside the private side
walls=[('西南鄰房空心磚圍牆',LineString([P[2],P[1],P[0],np.add(P[0],lane_dir*11)]),1.7,'slab'),
       ('北側紅磚矮牆',LineString([np.add(P[9],off),np.add(np.add(P[9],off),-lane_dir*12)]),1.2,'brick')]
for label,line,h,mat in walls:
 g=line.buffer(.1,cap_style=2).difference(house_envelope.buffer(.2)).difference(road_union_all)
 extr(g,h,0,mat);features.append(dict(label=label,type='wall',height_m=h,source='Street View June 2026 (observed type and run; height estimated)',built_footprint_xz=mapping(g)))
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
