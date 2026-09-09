"""Add glTF tangent spaces without touching positions, normals, faces or UVs."""
import json,struct,numpy as np
def add_tangents(blob):
 length=struct.unpack_from('<I',blob,12)[0];tree=json.loads(blob[20:20+length]);binary=bytearray(blob[28+length:]);added=0
 def read(index):
  a=tree['accessors'][index];v=tree['bufferViews'][a['bufferView']];count={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[a['type']]
  dtype=np.dtype({5126:'<f4',5125:'<u4',5123:'<u2',5121:'u1'}[a['componentType']]);offset=v.get('byteOffset',0)+a.get('byteOffset',0)
  return np.ndarray((a['count'],count),dtype,buffer=binary,offset=offset,strides=(v.get('byteStride',dtype.itemsize*count),dtype.itemsize)).copy()
 for mesh in tree['meshes']:
  for p in mesh['primitives']:
   attrs=p['attributes'];mat=tree.get('materials',[])[p.get('material',0)]
   if 'normalTexture' not in mat or 'TANGENT' in attrs or 'TEXCOORD_0' not in attrs:continue
   xyz=read(attrs['POSITION']).astype(float);n=read(attrs['NORMAL']).astype(float);uv=read(attrs['TEXCOORD_0']).astype(float)
   faces=read(p['indices']).reshape(-1,3) if 'indices' in p else np.arange(len(xyz)).reshape(-1,3)
   e1=xyz[faces[:,1]]-xyz[faces[:,0]];e2=xyz[faces[:,2]]-xyz[faces[:,0]]
   d1=uv[faces[:,1]]-uv[faces[:,0]];d2=uv[faces[:,2]]-uv[faces[:,0]];den=d1[:,0]*d2[:,1]-d1[:,1]*d2[:,0]
   r=np.divide(1.,den,out=np.zeros_like(den),where=np.abs(den)>1e-12)
   t=(e1*d2[:,1,None]-e2*d1[:,1,None])*r[:,None];b=(e2*d1[:,0,None]-e1*d2[:,0,None])*r[:,None]
   tan=np.zeros_like(xyz);bit=np.zeros_like(xyz)
   for i in range(3):np.add.at(tan,faces[:,i],t);np.add.at(bit,faces[:,i],b)
   tan-=n*np.sum(n*tan,axis=1)[:,None];norm=np.linalg.norm(tan,axis=1);bad=norm<1e-10
   axis=np.eye(3)[np.argmin(abs(n[bad]),axis=1)];tan[bad]=np.cross(n[bad],axis);norm=np.linalg.norm(tan,axis=1)
   assert np.all(norm>0) and np.isfinite(norm).all()
   tan/=norm[:,None];w=np.where(np.sum(np.cross(n,tan)*bit,axis=1)<0,-1.,1.)
   data=np.column_stack([tan,w]).astype('<f4').tobytes();binary+=b'\0'*((-len(binary))%4)
   view=len(tree['bufferViews']);tree['bufferViews'].append({'buffer':0,'byteOffset':len(binary),'byteLength':len(data),'target':34962});binary+=data
   accessor=len(tree['accessors']);tree['accessors'].append({'bufferView':view,'componentType':5126,'count':len(xyz),'type':'VEC4'});attrs['TANGENT']=accessor;added+=1
 tree['buffers'][0]['byteLength']=len(binary);binary+=b'\0'*((-len(binary))%4)
 js=json.dumps(tree,ensure_ascii=False,separators=(',',':')).encode();js+=b' '*((-len(js))%4)
 return struct.pack('<III',0x46546c67,2,28+len(js)+len(binary))+struct.pack('<II',len(js),0x4e4f534a)+js+struct.pack('<II',len(binary),0x004e4942)+binary,added
