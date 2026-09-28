"""Embed real PBR maps in all GLBs. UV seams split vertices, never move triangles."""
from pathlib import Path
import sys,json,hashlib,struct
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'.deps'))
import trimesh as tm,numpy as np
from PIL import Image
from glb_tangents import add_tangents
from glb_util import dedupe_images
ASSETS=ROOT/'output/assets'; maps={}
PROCEDURAL=['facade','porcelain','wetfloor','wetwall','terracotta','subway','zellige','checker','herringbone','oakplank','rattan','boardform']
for kind in ['plaster','wood','linen','leather','concrete','asphalt','grass','brick']+PROCEDURAL:
 color=Image.open(ASSETS/f'{kind}-color.jpg')
 normal=Image.open(ASSETS/f'{kind}-normal.jpg')
 rough=Image.open(ASSETS/f'{kind}-roughness.jpg').convert('L').resize((256,256))
 orm=Image.merge('RGB',(Image.new('L',rough.size,255),rough,Image.new('L',rough.size,0)))
 maps[kind]=(color,normal,orm)
# Physical module sizes (metres per texture repeat, u then v) from procedural_textures.py.
MODULE={'facade':(.928,1.04),'porcelain':1.2,'wetfloor':1.2,'wetwall':1.2,'terracotta':1.2,'subway':.6,'zellige':.6,
 'checker':.6,'herringbone':.84,'oakplank':1.44,'rattan':.12,'boardform':1.2}
FABRIC={'fabric','accent','ochre','rose','cream','jute','macrame','sheer','linen','wool','hide','velvet','rosevelvet','mustvelvet','emervelvet','sand','charlinen','stripe','canvas2'}
RUGS={'rug','rugblue','rugred'}
WOODS={'wood','wood2','darkwood','walnut','oak','ash','bamboo'}
def select(name,style):
 styled=name.startswith(('bohemian_','industrial_','eclectic_','wabisabi_'))
 base=name.split('_',1)[1] if styled else name
 if styled:
  if base=='paint':return ('boardform',MODULE['boardform']) if style=='industrial' else ('plaster',2)
  if base=='ceilpaint':return 'plaster',2
  if base in MODULE:return base,MODULE[base]
  if base=='concrete':return 'concrete',2
  if base=='brick':return 'brick',1.2
  if base=='leather':return 'leather',.55
  if base in RUGS:return 'linen',.8
  if base in FABRIC:return 'linen',.35
  if base in WOODS:return 'wood',1
  if base in ('travertine','stone'):return 'concrete',.6
  if base=='gravel':return 'concrete',.3
  if base=='tatami':return 'rattan',.08
  return None
 if base in MODULE:return base,MODULE[base]
 if name=='facade':return 'facade',MODULE['facade']
 if name=='paint' or name=='ceiling':return 'plaster',2
 if name=='tile':return 'porcelain',1.2
 if name=='wet':return 'wetfloor',1.2
 if name=='wetwall':return 'wetwall',1.2
 if name=='ground' and style=='context':return 'grass',4
 if name=='grass':return 'grass',2
 if name=='brick':return 'brick',2
 if name=='wood':return 'wood',1
 if name in ['wall','white','slab']:return 'plaster',2
 if name=='door' or name.endswith('_wood'):return 'wood',1
 if name.endswith('_fabric') and style=='industrial':return 'leather',.55
 if name.endswith(('_fabric','_accent','_light','_rug')) or name=='canvas':return 'linen',.35 if not name.endswith('_rug') else .8
 if name.endswith('_floor'):return ('concrete',2) if style=='industrial' else ('wood',2)
 if name in ['tile','wet','terrace','porch','ground']:return 'concrete',2
 if name=='road':return 'asphalt',3
 return None
def autosmooth(m,angle=35):
 """Per-corner normals smoothed only across edges flatter than `angle` degrees:
 cushions and curved railings stay smooth, box edges and bevels stay crisp."""
 fn=m.face_normals;F=len(m.faces);cv=m.faces.ravel();cf=np.repeat(np.arange(F),3);ca=m.face_angles.ravel()
 order=np.argsort(cv,kind='stable');sv,sf,sa=cv[order],cf[order],ca[order]
 nv=len(m.vertices);starts=np.searchsorted(sv,np.arange(nv));deg=np.searchsorted(sv,np.arange(nv),side='right')-starts
 cdeg=deg[cv];rep_c=np.repeat(np.arange(3*F),cdeg)
 offs=np.arange(cdeg.sum())-np.repeat(np.cumsum(cdeg)-cdeg,cdeg)
 nb=starts[cv][rep_c]+offs;nf=sf[nb]
 w=np.where((fn[cf[rep_c]]*fn[nf]).sum(1)>np.cos(np.radians(angle)),sa[nb],0.)
 out=np.zeros((3*F,3));np.add.at(out,rep_c,fn[nf]*w[:,None])
 ln=np.linalg.norm(out,axis=1);bad=ln<1e-9;out[bad]=fn[cf[bad]]
 zero=np.linalg.norm(out,axis=1)<1e-9;out[zero]=[0,1,0]  # degenerate slivers
 ln=np.linalg.norm(out,axis=1)
 return out/ln[:,None]
def triangle_hash(m):
 return hashlib.sha256(np.asarray(m.triangles,dtype='<f4').tobytes()).hexdigest()
def run(file,style):
 input_sha256=hashlib.sha256(file.read_bytes()).hexdigest()
 scene=tm.load(file,force='scene',process=False);changed=0;proof=[];materials={};converted=set()
 def linear_color(mat):
  if id(mat) in converted:return
  converted.add(id(mat));c=np.array(mat.baseColorFactor,dtype=float)/255
  c[:3]=np.where(c[:3]<=.04045,c[:3]/12.92,((c[:3]+.055)/1.055)**2.4)
  mat.baseColorFactor=np.round(c*255).astype(np.uint8)
 for name,m in scene.geometry.items():
  before=triangle_hash(m);old=m.visual.material;selection=select(old.name or '',style)
  corner_normals=autosmooth(m);verts=m.vertices[m.faces].reshape(-1,3)
  if selection:
   kind,scale=selection;key=(old.name,kind)
   if key not in materials:
    mat=old.copy();mat.baseColorTexture,mat.normalTexture,mat.metallicRoughnessTexture=maps[kind]
    mat.roughnessFactor=.7 if kind=='wood' else 1.0 if kind in PROCEDURAL else .9;mat.metallicFactor=0;linear_color(mat);materials[key]=mat
   normals=corner_normals
   axis=np.argmax(np.abs(m.face_normals),axis=1);uv=np.empty((len(m.faces),3,2))
   tri=m.triangles
   sc=np.array(scale if isinstance(scale,tuple) else (scale,scale),float)
   for a,indices in [(0,[2,1]),(1,[0,2]),(2,[0,1])]:uv[axis==a]=tri[axis==a][:,:,indices]/sc
   uv=uv.reshape(-1,2)
   # Lossless attribute welding: reduce phone memory without quantizing geometry.
   _,indices,inverse=np.unique(np.column_stack([verts,normals,uv]),axis=0,return_index=True,return_inverse=True)
   new=tm.Trimesh(vertices=verts[indices],faces=inverse.reshape(-1,3),vertex_normals=normals[indices],process=False,metadata=m.metadata)
   new.visual=tm.visual.TextureVisuals(uv=uv[indices],material=materials[key])
   assert triangle_hash(new)==before
   scene.geometry[name]=new;changed+=1
  else:
   linear_color(old)
   if old.name=='ceramic':old.roughnessFactor=.22
   elif old.name=='glass':old.baseColorFactor=[171,208,208,60];old.roughnessFactor=.1
   _,indices,inverse=np.unique(np.column_stack([verts,corner_normals]),axis=0,return_index=True,return_inverse=True)
   new=tm.Trimesh(vertices=verts[indices],faces=inverse.reshape(-1,3),vertex_normals=corner_normals[indices],process=False,metadata=m.metadata)
   new.visual=tm.visual.TextureVisuals(material=old)
   assert triangle_hash(new)==before
   scene.geometry[name]=new
  proof.append(dict(mesh=name,triangle_sha256=before))
 blob=scene.export(file_type='glb');jl=struct.unpack_from('<I',blob,12)[0];tree=json.loads(blob[20:20+jl]);binary=blob[20+jl:]
 # Trimesh shares UV sets for occlusion with index 0; explicitly tag GPU buffers.
 for mesh in tree['meshes']:
  for p in mesh['primitives']:
   for idx in p['attributes'].values():tree['bufferViews'][tree['accessors'][idx]['bufferView']]['target']=34962
   if 'indices' in p:tree['bufferViews'][tree['accessors'][p['indices']]['bufferView']]['target']=34963
 js=json.dumps(tree,ensure_ascii=False,separators=(',',':')).encode();js+=b' '*((-len(js))%4)
 blob=struct.pack('<III',0x46546c67,2,20+len(js)+len(binary))+struct.pack('<II',len(js),0x4e4f534a)+js+binary
 blob,tangent_count=add_tangents(blob)
 blob,duplicate_images=dedupe_images(blob)
 tmp=file.with_suffix('.tmp');tmp.write_bytes(blob);tmp.replace(file)
 check=tm.load(file,force='scene',process=False)
 assert all(triangle_hash(check.geometry[p['mesh']])==p['triangle_sha256'] for p in proof)
 return dict(file=file.relative_to(ROOT/'output').as_posix(),input_sha256=input_sha256,sha256=hashlib.sha256(blob).hexdigest(),bytes=len(blob),texturedMeshBatches=changed,duplicateImagesRemoved=duplicate_images,tangentMeshBatches=tangent_count,trianglePositionsUnchanged=True,proof=proof)
if __name__=='__main__':
 report={'date':'2026-09-10 UTC+8','material_source':'https://polyhaven.com/license','files':[]}
 report['files'].append(run(ROOT/'output/house.glb','original'))
 for style in ['bohemian','industrial','eclectic','wabisabi']:report['files'].append(run(ROOT/f'output/styles/{style}.glb',style))
 (ROOT/'output/realism').mkdir(exist_ok=True)
 (ROOT/'output/realism/material-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 p=ROOT/'output/model-manifest.json';m=json.loads(p.read_text(encoding='utf-8'));m['sha256']=report['files'][0]['sha256'];m['glb_bytes']=m['bytes']=report['files'][0]['bytes'];m['render_revision']='2026-09-10-pbr';p.write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf-8')
 p=ROOT/'output/styles/furniture-manifest.json';m=json.loads(p.read_text(encoding='utf-8'))
 for style,r in zip(['bohemian','industrial','eclectic','wabisabi'],report['files'][1:]):m['styles'][style].update(sha256=r['sha256'],bytes=r['bytes'])
 p.write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps([{k:v for k,v in r.items() if k!='proof'} for r in report['files']]))
