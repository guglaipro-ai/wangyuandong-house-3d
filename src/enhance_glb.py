"""Embed real PBR maps in all GLBs. UV seams split vertices, never move triangles."""
from pathlib import Path
import sys,json,hashlib,struct
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'.deps'))
import trimesh as tm,numpy as np
from PIL import Image
from glb_tangents import add_tangents
ASSETS=ROOT/'output/assets'; maps={}
for kind in ['plaster','wood','linen','leather','concrete','asphalt','grass','brick']:
 color=Image.open(ASSETS/f'{kind}-color.jpg')
 normal=Image.open(ASSETS/f'{kind}-normal.jpg')
 rough=Image.open(ASSETS/f'{kind}-roughness.jpg').convert('L').resize((256,256))
 orm=Image.merge('RGB',(Image.new('L',rough.size,255),rough,Image.new('L',rough.size,0)))
 maps[kind]=(color,normal,orm)
def select(name,style):
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
  smooth=np.zeros_like(m.vertices)
  for corner in range(3):np.add.at(smooth,m.faces[:,corner],m.face_normals*m.face_angles[:,corner,None])
  smooth/=np.maximum(np.linalg.norm(smooth,axis=1)[:,None],1e-10)
  m.vertex_normals=smooth
  if selection:
   kind,scale=selection;key=(old.name,kind)
   if key not in materials:
    mat=old.copy();mat.baseColorTexture,mat.normalTexture,mat.metallicRoughnessTexture=maps[kind]
    mat.roughnessFactor=.7 if kind=='wood' else .9;mat.metallicFactor=0;linear_color(mat);materials[key]=mat
   # Preserve smooth normals on upholstery; architectural surfaces retain their
   # original vertex normals. Three vertices per triangle make UV seams exact.
   verts=m.vertices[m.faces].reshape(-1,3)
   if name.startswith('STYLE_'):
    normals=smooth[m.faces].reshape(-1,3)
   else: normals=np.repeat(m.face_normals,3,axis=0)
   axis=np.argmax(np.abs(m.face_normals),axis=1);uv=np.empty((len(m.faces),3,2))
   tri=m.triangles
   for a,indices in [(0,[2,1]),(1,[0,2]),(2,[0,1])]:uv[axis==a]=tri[axis==a][:,:,indices]/scale
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
 tmp=file.with_suffix('.tmp');tmp.write_bytes(blob);tmp.replace(file)
 check=tm.load(file,force='scene',process=False)
 assert all(triangle_hash(check.geometry[p['mesh']])==p['triangle_sha256'] for p in proof)
 return dict(file=file.relative_to(ROOT/'output').as_posix(),input_sha256=input_sha256,sha256=hashlib.sha256(blob).hexdigest(),bytes=len(blob),texturedMeshBatches=changed,tangentMeshBatches=tangent_count,trianglePositionsUnchanged=True,proof=proof)
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
