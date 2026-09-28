"""Seamless procedural finish textures sized from real product modules.

Every texture maps a known physical size so UV scale in enhance_glb equals the
module dimensions below (metres). Sources are listed in output/realism/references.html.
- facade: 二丁掛 227x60 mm, 5 mm joint (PDF p8 註1 / p20 W038 牆面：磁磚(丁掛磚) 10 mm)
- porcelain: 60x60 cm 拋光石英磚, 2 mm joint (common Taiwan residential floor)
- wetfloor: 30x30 cm anti-slip, 3 mm joint; wetwall: 30x60 cm glazed wall tile
- terracotta 20x20, herringbone 7x42 cm, oak plank 18 cm wide, subway 7.5x15,
  zellige 10x10, checker 10x10, rattan weave. No external images are used.
"""
from pathlib import Path
import sys,json,hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'.deps'))
import numpy as np
from PIL import Image,ImageFilter
OUT=ROOT/'output/assets'
RNG=np.random.default_rng(20260928)

def noise(h,w,scale,octaves=3,seed=0):
 """Tileable value noise via wrapped low-res grids."""
 r=np.random.default_rng(seed);acc=np.zeros((h,w))
 for o in range(octaves):
  gh=max(2,int(h/scale*2**o));gw=max(2,int(w/scale*2**o))
  g=r.random((gh,gw))
  img=Image.fromarray((g*255).astype(np.uint8)).resize((w,h),Image.Resampling.BICUBIC)
  # wrap smoothing so edges match
  a=np.asarray(img,float)/255;a=(a+np.roll(a,1,0)+np.roll(a,1,1))/3
  acc+=a/2**o
 acc-=acc.min();return acc/max(acc.max(),1e-6)

def normal_from_height(hmap,strength=2.0):
 gx=(np.roll(hmap,-1,1)-np.roll(hmap,1,1))*strength
 gy=(np.roll(hmap,-1,0)-np.roll(hmap,1,0))*strength
 n=np.dstack([-gx,gy,np.ones_like(hmap)]);n/=np.linalg.norm(n,axis=2,keepdims=True)
 return Image.fromarray(((n*.5+.5)*255).astype(np.uint8))

def save(name,color,height,rough,strength=2.0):
 OUT.mkdir(exist_ok=True)
 Image.fromarray(np.clip(color,0,255).astype(np.uint8)).save(OUT/f'{name}-color.jpg',quality=86,optimize=True)
 normal_from_height(height,strength).save(OUT/f'{name}-normal.jpg',quality=84,optimize=True)
 Image.fromarray((np.clip(rough,0,1)*255).astype(np.uint8)).resize((256,256)).save(OUT/f'{name}-roughness.jpg',quality=84)

def grid_tiles(px,py,W,H,tw,th,joint,offset_rows=False):
 """Return tile index arrays and joint mask for pixel grid covering W x H metres."""
 y,x=np.mgrid[0:py,0:px];xm=x/px*W;ym=y/py*H
 row=np.floor(ym/th).astype(int)
 xs=xm+(row%2)*(tw/2 if offset_rows else 0)
 col=np.floor(xs/tw).astype(int)
 fx=xs-col*tw;fy=ym-row*th
 joint_mask=(fx<joint/2)|(fx>tw-joint/2)|(fy<joint/2)|(fy>th-joint/2)
 ncol=int(round(W/tw));col=col%max(ncol,1)
 return row,col,joint_mask,fx,fy

def tile_texture(name,W,H,tw,th,joint,base,var,grout,rough_tile,rough_grout,offset=False,px=1024,glaze=0.0,seed=1):
 py=int(round(px*H/W));row,col,jm,fx,fy=grid_tiles(px,py,W,H,tw,th,joint,offset)
 ids=(row*977+col*131)%4093;rng=np.random.default_rng(seed)
 lut=rng.normal(0,1,(4096,3))
 c=np.array(base,float)[None,None,:]*(1+var*lut[ids][:,:,:1])+lut[ids]*var*18
 n=noise(py,px,90,3,seed)
 c=c*(0.95+0.1*n[:,:,None])
 c[jm]=grout
 # slightly bevelled edge (glazed tile softness)
 edge=np.minimum(np.minimum(fx,tw-fx),np.minimum(fy,th-fy))
 h=np.clip((edge-joint/2)/max(joint,0.002),0,1)*0.6+n*0.05*(1-glaze)
 h[jm]=0
 r=np.full(jm.shape,rough_tile)+n*0.08;r[jm]=rough_grout
 save(name,c,h,r,2.2)

def herringbone(name='herringbone',L=.42,w=.07,px=1024):
 n=int(round(L/w));S=2*L;y,x=np.mgrid[0:px,0:px]/px*S
 a=np.floor(x/w).astype(int);b=np.floor(y/w).astype(int);d=b-a
 c=np.floor((d+n-1)/(2*n)).astype(int);r=(d+n-1)-2*n*c
 horiz=r<n;bp=b-2*n*c
 pid=np.where(horiz,(bp%(2*n)),(a%(2*n))+2*n)
 rng=np.random.default_rng(7);tone=rng.normal(0,1,4*n+1)
 base=np.array([112,78,52],float)
 grain_coord=np.where(horiz,y*140+np.sin(x*9+pid)*1.5,x*140+np.sin(y*9+pid)*1.5)
 grain=(np.sin(grain_coord+pid*3.1)*.5+.5)**3
 col=base[None,None,:]*(1+.10*tone[pid][:,:,None])*(0.88+0.2*grain[:,:,None])
 edge=(pid!=np.roll(pid,1,0))|(pid!=np.roll(pid,1,1))
 col[edge]=col[edge]*.55
 h=1-edge.astype(float)*.9+grain*.05
 rough=.42+.12*grain;rough[edge]=.8
 save(name,col,h,rough,2.4)

def planks(name='oakplank',W=1.44,H=1.44,pw=.18,px=1024):
 y,x=np.mgrid[0:px,0:px]/px*W;row=np.floor(y/pw).astype(int);rows=int(round(H/pw))
 rng=np.random.default_rng(11);offs=rng.random(rows)*W;split=rng.random(rows)<.5
 xs=(x+offs[row%rows])%W;seg=np.where(split[row%rows],np.floor(xs/(W/2)),0).astype(int)
 pid=row*3+seg;tone=rng.normal(0,1,rows*3+3)
 base=np.array([196,168,128],float)
 knot=noise(px,px,60,2,4)
 grain=(np.sin(y*520+np.sin(xs*2.1+pid)*1.1+knot*2.5+pid*1.7)*.5+.5)**3
 col=base[None,None,:]*(1+.06*tone[pid][:,:,None])*(0.9+0.14*grain[:,:,None])
 edge=(pid!=np.roll(pid,1,0))|(pid!=np.roll(pid,1,1))
 col[edge]*=.62
 h=1-edge*.8+grain*.06;rough=.62+.1*grain;rough[edge]=.85
 save(name,col,h,rough,2.0)

def rattan(name='rattan',px=512,S=.12):
 y,x=np.mgrid[0:px,0:px]/px;k=8
 u=np.sin(x*np.pi*2*k);v=np.sin(y*np.pi*2*k)
 over=((np.floor(x*k*2)+np.floor(y*k*2))%2==0)
 h=np.where(over,np.abs(np.sin(y*np.pi*k*2)),np.abs(np.sin(x*np.pi*k*2)))
 base=np.array([190,150,96],float)
 col=base[None,None,:]*(0.7+0.4*h[:,:,None])
 gap=h<.18;col[gap]=[70,52,32]
 rough=np.full(h.shape,.7);save(name,col,h,rough,3)

def concrete_board(name='boardform',W=1.2,px=1024):
 # 清水模 board-formed concrete: 12 cm boards, 60x120 form-tie pattern
 y,x=np.mgrid[0:px,0:px]/px*W
 n=noise(px,px,40,4,21);board=np.floor(y/.12).astype(int)
 col=np.array([168,166,160],float)[None,None,:]*(0.88+0.18*n[:,:,None])
 col*=1+0.03*np.sin(board*2.3)[:,:,None]
 line=(y%.12)<.002;col[line]*=.9
 tie=((x%.6-.15)**2+(y%.6-.3)**2)<.013**2;col[tie]*=.6
 h=n*.4-line*.3-tie*.8;rough=.8+n*.1
 save(name,col,h,rough,1.6)

def build():
 tile_texture('facade',.928,1.04,.232,.065,.005,[238,235,228],.03,[186,183,176],.5,.95,offset=True,glaze=.3,seed=3)
 tile_texture('porcelain',1.2,1.2,.6,.6,.002,[222,214,199],.02,[196,190,178],.2,.7,glaze=1,seed=5)
 tile_texture('wetfloor',1.2,1.2,.3,.3,.003,[176,178,172],.04,[140,140,134],.72,.9,seed=6)
 tile_texture('wetwall',1.2,1.2,.6,.3,.002,[233,234,230],.015,[200,200,195],.18,.7,offset=True,glaze=1,seed=8)
 tile_texture('terracotta',1.2,1.2,.2,.2,.008,[178,98,62],.10,[206,190,166],.7,.92,seed=9)
 tile_texture('subway',.6,.6,.15,.075,.003,[238,237,232],.02,[62,62,60],.14,.8,offset=True,glaze=1,seed=10)
 tile_texture('zellige',.6,.6,.1,.1,.003,[38,120,118],.16,[214,206,190],.18,.8,glaze=1,seed=12)
 # checkerboard: two tones 10x10
 row,col,jm,fx,fy=grid_tiles(512,512,.6,.6,.1,.1,.002)
 c=np.where(((row+col)%2==0)[:,:,None],np.array([236,232,222.]),np.array([30,40,70.]));c[jm]=[180,176,168]
 h=np.ones(jm.shape);h[jm]=0;r=np.full(jm.shape,.2);r[jm]=.7;save('checker',c,h,r,2)
 herringbone();planks();rattan();concrete_board()
 rec={k:hashlib.sha256((OUT/f'{k}-color.jpg').read_bytes()).hexdigest()[:16] for k in ['facade','porcelain','wetfloor','wetwall','terracotta','subway','zellige','checker','herringbone','oakplank','rattan','boardform']}
 print(json.dumps(rec))

if __name__=='__main__':build()
