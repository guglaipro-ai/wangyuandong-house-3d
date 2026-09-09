"""PDF p19 opening constructions, and source-linked correction ledger."""
import json,hashlib,html
from pathlib import Path
import numpy as np
WALL_ZH={'back_left':'後側西段','back_core':'後側樓梯間','left':'左側外牆','front_feature_window':'前側造型窗','front_entry':'前側玄關','right_living_front':'右側客廳前牆','right_living_side':'右側客廳側牆','core_entry':'樓梯廳側入口','living_partition':'兩客廳隔牆','stair_lobby_west':'樓梯廳西側入口','wc_b_entry':'廁所B入口','wc_a_side':'梯下儲藏室側門','back_bed_wc':'後側臥室／衛浴','back_stair_dining':'後側樓梯／餐廳','bed3_front':'臥室三前牆','bed3_balcony_entry':'臥室三陽台入口','living_balcony':'客廳陽台入口','right_dining_living':'餐廳／客廳右外牆','bed1_wc':'臥室一衛浴入口','stair_west':'樓梯廳西側','bed1_front':'臥室一前牆','wc_b_door':'廁所B門','bed2_east':'臥室二側牆','hall_living':'走道／客廳隔牆','stair_front':'樓梯廳前牆','dining_stair':'餐廳／樓梯廳隔牆','dining_front':'餐廳前牆','back':'後側外牆','stair_back':'樓梯後牆','bed3_balcony':'臥室三陽台','stair_east':'樓梯廳東側','wc_door':'衛浴入口','bed2_back':'臥室二後牆','terrace_door':'露台側外牆','front':'前側外牆','bed_partition':'臥室隔牆','elevator_door':'電梯入口'}

class Audit:
 def __init__(self,root):
  self.root=root;self.rows=[];self.active=None
  self.before=json.loads((root/'output/audit/before-model-manifest.json').read_text(encoding='utf-8'))['openings'];self.used=set()
 def opening_before(self,f,wall,code,center,detail):
  candidates=[(i,o) for i,o in enumerate(self.before) if i not in self.used and o['floor']==f and (o['code']==code or code=='LIFT' and o['wall']=='elevator_door')]
  same=[(i,o) for i,o in candidates if o['wall']==wall]
  if same:candidates=same
  if not candidates:return '圖面有此開口，原模型未建立'
  i,o=min(candidates,key=lambda io:np.linalg.norm(np.array(io[1]['center'])-center));self.used.add(i)
  moved=np.linalg.norm(np.array(o['center'])-center)>.025
  return detail+(f"；原中心{xstr(o['center'])}，本次移至{xstr(center)}" if moved else '')
 def begin(self,key,category,where,pages,before,after,basis='圖示構造；細框截面沿用已確認的概念假設'):
  if any(r['key']==key for r in self.rows):raise ValueError('duplicate audit key '+key)
  row=dict(id=f'A{len(self.rows)+1:03}',key=key,category=category,location=where,pdf_pages=pages,before=before,after=after,basis=basis,components=[])
  self.rows.append(row);self.active=row;return row
 def end(self):self.active=None
 def component(self,name,mesh):
  if self.active is not None:
   self.active['components'].append(dict(name=name,triangles=len(mesh.faces),world_bounds=mesh.bounds.tolist(),geometry_sha256=hashlib.sha256(mesh.vertices.tobytes()+mesh.faces.tobytes()).hexdigest()))
 def export(self,manifest):
  out=self.root/'output/audit';out.mkdir(exist_ok=True)
  report=dict(count=len(self.rows),counting_rule='依實際位置與構件逐處計數；相同門窗型號在不同位置分別列一項。含原模型省略的圖示細節，不代表100種互不重複的設計錯誤。',rows=self.rows,source='王源東住宅新建工程(請照) (1).pdf',model_sha256=manifest['sha256'])
  if (out/'source.json').exists():report['source_evidence']=json.loads((out/'source.json').read_text(encoding='utf-8'))
  (out/'corrections.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
  lines=['# 圖面比對與修正清單','',f'已執行 {len(self.rows)} 處修正。逐處按實際構件位置計數；同型號多樘門窗分開列項。包含省略的細節補建，並非同一項拆成每根框料來計數。','',
   '基準：baf81f8 版建築模型。家具是另外授權的配置提案，不列作圖面錯誤。PDF 本身未修改。','',
   '頁碼是 PDF 檔案頁序。明確標註的尺寸依圖採用；未標細框、五金、衛浴產品外形與局部定位仍採概念比例，不宣稱 CAD／施工精度。','',
   '|編號|位置／構件|PDF頁|修正前|已執行修正|','|---|---|---|---|---|']
  for r in self.rows:lines.append('|'+ '|'.join([r['id'],r['location'],','.join(map(str,r['pdf_pages'])),r['before'],r['after']])+'|')
  lines+=['','## 留待確認','', '- 二、三樓梯段分配及少數未清楚標註的門扇開向仍屬示意；總踢面數與樓高已保留，連通幾何已改善。','- 未取得 CAD／測量坐標，不能將圖面比例定位視為現地精密尺寸。','- 地界、地形、隱藏機電與鋼筋不納入本次100處可見模型修正，也不據此提供施工或結構認證。','- Android 實機流暢度仍須由手機補驗。']
  (out/'圖面差異與修正清單.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
  escape=html.escape
  body=''.join('<tr>'+''.join('<td>'+escape(str(v))+'</td>' for v in [r['id'],r['location'],','.join(map(str,r['pdf_pages'])),r['before'],r['after']])+'</tr>' for r in self.rows)
  page='''<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>圖面修正清單</title><style>body{font:16px/1.7 system-ui,sans-serif;background:#f7f4ec;color:#263d36;margin:0}main{max-width:1280px;margin:auto;padding:24px}h1{font-size:26px}a{color:#22644e}input{font:inherit;padding:12px;width:100%;box-sizing:border-box;border:1px solid #b8c7bd;border-radius:8px}.table{overflow:auto;margin-top:20px}table{border-collapse:collapse;width:100%;background:white}th,td{padding:12px;border-bottom:1px solid #ddd;text-align:left;vertical-align:top;min-width:95px}td:nth-child(4),td:nth-child(5){min-width:210px}thead{background:#e2ece2}small{color:#61756a}.count{font-size:36px;font-weight:bold}details{padding:12px 0}</style><main><a href="../">← 返回可旋轉的住宅模型</a><h1>圖面比對與修正清單</h1><div class="count">COUNT 處已修正</div><p>按實際構件位置逐處計數，含原模型省略的圖示細節；同型號多樘門窗分別列项。家具是另外授權的提案，不列作圖面錯誤。</p><details><summary>比對範圍與精度</summary><p>比對來源：王源東住宅新建工程(請照) (1).pdf。頁碼採 PDF 頁序。明示尺寸依圖採用；門窗細框、五金、衛浴產品及未完整標註的定位仍是概念近似。101處修正不代表整份模型達到CAD、施工或結構認證精度。原PDF未修改。</p></details><label for="q">搜尋樓層、構件或編號</label><input id="q" placeholder="例如：2F、電梯、百葉、A001"><div class="table"><table><thead><tr><th>編號</th><th>位置／構件</th><th>PDF頁</th><th>修正前</th><th>已執行修正</th></tr></thead><tbody>ROWS</tbody></table></div><p><a href="corrections.json">下載完整驗證資料</a></p><small>本頁隨建築模型更新；四套家具版共用此次修正。</small></main><script>document.querySelector('#q').oninput=e=>{const q=e.target.value.toLowerCase();document.querySelectorAll('tbody tr').forEach(r=>r.hidden=!r.textContent.toLowerCase().includes(q))}</script></html>'''.replace('COUNT',str(len(self.rows))).replace('ROWS',body)
  page=page.replace('<div class="table">','<p><small>手機可左右滑動表格，查看修正前後內容。</small></p><div class="table">')
  (out/'index.html').write_text(page,encoding='utf-8')

def xstr(a):return '('+','.join(f'{v:.3f}' for v in a)+')m'

def opening_detail(a,u,lo,hi,z,oh,code,parent,piece,bar,box,mesh_add,materials):
 """Draw real individual leaves/sashes in plan coordinates; no symbolic arrows."""
 w=hi-lo;fw=.05;kind='door' if code.startswith(('D','S','LIFT')) else 'window'
 normal=np.array([-u[1],u[0]])
 def p(s,offset=0):return a+u*s+normal*offset
 def strip(s,e,zz,hh,mat='metal',depth=.06,offset=0,label='profile'):
  bar(p(s,offset),p(e,offset),zz,hh,depth,code+'_'+label,parent,mat,kind)
 def frame(s,e,zz,hh,offset=0,depth=.04,b=.027,mat='metal',label='sash'):
  strip(s,e,zz,b,mat,depth,offset,label+'_bottom');strip(s,e,zz+hh-b,b,mat,depth,offset,label+'_top')
  strip(s,s+b,zz,hh,mat,depth,offset,label+'_left');strip(e-b,e,zz,hh,mat,depth,offset,label+'_right')
 # Original external frame remains nominal 5 cm, inner members model the schedule.
 frame(lo,hi,z,oh,0,.06,fw,label='outer')
 if code.startswith(('W','DW')):
  if code.startswith(('W1','DW1','DW2')):fractions=[0,.5,1]
  elif code.startswith(('W2','W3')):fractions=[0,.25,.75,1]
  elif code in ('DW3','DW4'):fractions=[0,.25,.5,.75,1]
  else:fractions=[0,1]
  depth=.010 if code in ('W3b','DW2','DW4') else .016 if code=='W5' else .008 if code.startswith(('W2','W3','W6')) or code in ('W4c','W4f','DW1','DW3') else .006
  for i,(l,r) in enumerate(zip(fractions,fractions[1:])):
   s=lo+fw+(w-2*fw)*l;e=lo+fw+(w-2*fw)*r;off=(i%2-.5)*.027 if len(fractions)>2 else 0
   frame(s,e,z+fw,oh-2*fw,off,label=f'sash{i+1}')
   strip(s+.027,e-.027,z+fw+.027,oh-2*fw-.054,'glass',depth,off,f'pane{i+1}')
   if len(fractions)>2 or code.startswith('W6'):
    hs=s+.045 if i%2 else e-.07
    strip(hs,hs+.025,z+oh*.43,.13,'metal',.025,off+.035,f'handle{i+1}')
   if code.startswith('W6'):
    for h in [.2,oh-.3]:strip(s,s+.035,z+h,.06,'metal',.06,off,'hinge')
  if len(fractions)>2:
   for off in [-.035,.035]:strip(lo+fw,hi-fw,z+.025,.015,'metal',.012,off,'track')
 elif code=='SD1':
  # p19: 340 cm curtain + 60 cm housing; retain previously approved half-open pose.
  strip(lo,hi,z+oh,.6,'metal',.36,0,'housing_60cm')
  for zz in np.arange(z+1.9,z+oh-.025,.08):strip(lo+fw,hi-fw,zz,min(.07,z+oh-zz),'metal',.025,0,'shutter_slat')
 elif code.startswith('LIFT'):
  # p18 usable 800 x 2000 entrance with two telescopic panels and jamb surrounds.
  for i in range(2):strip(lo+fw+i*(w-2*fw)/2,lo+fw+(i+1)*(w-2*fw)/2-.004,z+.02,oh-.04,'metal',.035,i*.018,'telescopic_panel')
 else:
  # Door leaf local axis follows the existing 55-degree display pose.
  ang=np.deg2rad(55);rot=np.array([[np.cos(ang),-np.sin(ang)],[np.sin(ang),np.cos(ang)]])
  def leaf(start,width,reverse=False):
   hinge=p(start);v=rot@u*(-1 if reverse else 1);nv=np.array([-v[1],v[0]])
   def lstrip(s,e,zz,hh,mat='door',th=.04,offset=0,label='leaf'):
    bar(hinge+v*s+nv*offset,hinge+v*e+nv*offset,zz,hh,th,code+'_'+label,parent,mat,kind)
   if code.startswith('D4') or code=='D6':
    for s,e in [(0,.07),(width-.07,width)]:lstrip(s,e,z+.02,oh-.04)
    lstrip(0,width,z+.02,.10);lstrip(0,width,z+oh-.10,.08)
    if code.startswith('D4'):
     lstrip(0,width,z+oh*.48,.10)
     # p19 names D4 a timber door; do not infer unspecified infill glass.
     for zz,hh in [(z+.12,oh*.48-.13),(z+oh*.48+.10,oh*.52-.21)]:lstrip(.07,width-.07,zz,hh,'door',.022,label='inset_panel')
    else:
     # p19 inset louvre field 49 x 176 cm.
     lw=min(.49,width-.14);s=(width-lw)/2
     lstrip(.07,s,z+.12,oh-.24);lstrip(s+lw,width-.07,z+.12,oh-.24)
     for zz in np.arange(z+.20,z+1.94,.09):lstrip(s,s+lw,zz,.055,'metal',.035,label='louvre')
   else:
    lstrip(0,width,z+.02,oh-.04,'metal' if code.startswith('D5') else 'door')
    if code.startswith('D2'):
     for off in [-.023,.023]:
      for s,e in [(.10,.13),(width-.13,width-.10)]:lstrip(s,e,z+.18,oh-.36,'door',.015,off,'panel_border')
      for zz in [z+.18,z+oh-.21]:lstrip(.10,width-.10,zz,.03,'door',.015,off,'panel_border')
    if code.startswith('D3'):
     for zz in np.arange(z+.24,z+.47,.045):lstrip(width*.25,width*.75,zz,.024,'metal',.01,.026,'vent_louvre')
   for off in [-.035,.035]:lstrip(width-.13,width-.025,z+.98,.025,'metal',.025,off,'handle')
  if code=='D1':
   # p19 nominal leaves 45 + 120 cm; frame clearance apportioned to each leaf.
   leaf(lo+fw,.45-fw);leaf(hi-fw,1.20-fw,True)
  else:leaf(lo+fw,w-2*fw)
