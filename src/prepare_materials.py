"""Fetch a bounded set of CC0 scanned materials; preserve source hashes and licenses."""
from pathlib import Path
import urllib.request,json,hashlib,io
from PIL import Image,ImageOps,ImageEnhance
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'output/assets'; OUT.mkdir(exist_ok=True)
RAW=ROOT/'tmp/materials'; RAW.mkdir(exist_ok=True)
ASSETS={'plaster':'white_plaster_02','wood':'oak_veneer_01','linen':'denim_fabric','leather':'leather_white','concrete':'concrete_floor','asphalt':'asphalt_02','grass':'sparse_grass','brick':'red_brick'}
def get(url):
 return urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'WangHouseConcept/1.0 personal-visualization'}),timeout=45).read()
records=[]
for label,asset in ASSETS.items():
 catalog=ROOT/'tmp'/f'{asset}.json'
 if not catalog.exists():catalog.write_bytes(get('https://api.polyhaven.com/files/'+asset))
 files=json.loads(catalog.read_text())
 for channel,key in [('color','Diffuse'),('normal','nor_gl'),('roughness','Rough')]:
  info=files[key]['1k']['jpg']; raw=RAW/f'{asset}-{channel}.jpg'
  if not raw.exists():raw.write_bytes(get(info['url']))
  data=raw.read_bytes();assert hashlib.md5(data).hexdigest()==info['md5']
  im=Image.open(io.BytesIO(data)).convert('RGB'); im.thumbnail((1024,1024) if channel=='color' else (512,512),Image.Resampling.LANCZOS)
  if channel=='color':
   # Neutral surface detail is tinted with each approved scheme's palette in glTF.
   im=ImageOps.grayscale(im).convert('RGB')
   avg=sum(ImageOps.grayscale(im).getdata())/(im.width*im.height)
   im=ImageEnhance.Brightness(im).enhance((214 if label=='wood' else 235)/max(1,avg))
   if label=='plaster':im=Image.blend(Image.new('RGB',im.size,(238,238,238)),im,.12)
  if channel=='normal':
   # Keep micro detail subtle; scanned brick-sized bumps must not read as damage.
   im=Image.blend(Image.new('RGB',im.size,(128,128,255)),im,.42 if label in ['plaster','linen','leather'] else .65)
  target=OUT/f'{label}-{channel}.jpg'; im.save(target,quality=87 if channel=='color' else 82,optimize=True)
  records.append(dict(asset=asset,channel=channel,source=info['url'],source_md5=info['md5'],file='assets/'+target.name,sha256=hashlib.sha256(target.read_bytes()).hexdigest(),license='CC0',processing='resized; albedo neutralized for palette tint; normal strength reduced'))
 print(label,flush=True)
sky='kloofendal_48d_partly_cloudy_puresky'; catalog=ROOT/'tmp'/f'{sky}.json'
if not catalog.exists():catalog.write_bytes(get('https://api.polyhaven.com/files/'+sky))
info=json.loads(catalog.read_text())['hdri']['1k']['hdr']; target=OUT/'daylight.hdr'
if not target.exists():target.write_bytes(get(info['url']))
assert hashlib.md5(target.read_bytes()).hexdigest()==info['md5']
records.append(dict(asset=sky,file='assets/daylight.hdr',source=info['url'],license='CC0',sha256=hashlib.sha256(target.read_bytes()).hexdigest(),note='Generic sky for illumination only; NOT a photograph at the Taiwan site'))
(OUT/'sources.json').write_text(json.dumps({'credit':'Powered by Poly Haven','license_url':'https://polyhaven.com/license','date':'2026-09-10 UTC+8','assets':records},ensure_ascii=False,indent=2),encoding='utf-8')
