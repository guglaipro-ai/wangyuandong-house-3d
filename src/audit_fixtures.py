"""Visible sanitary fixtures shown on PDF floor plans; product shape approximate."""
import math
from shapely.geometry import Polygon,box as rect
from shapely.affinity import rotate

def add_fixtures(ns):
 audit=ns['audit'];extr=ns['extr'];box=ns['box'];BASE=ns['BASE'];rod=ns['rod3']
 def ellipse(x,y,rx,ry):return Polygon([(x+rx*math.cos(i*math.tau/24),y+ry*math.sin(i*math.tau/24)) for i in range(24)])
 items=[
  (1,'廁所B','洗手盆',9.12,6.16,0,0),(1,'廁所B','小便斗',10.30,6.16,0,0),(1,'廁所B','坐式便器',11.35,6.16,0,0),
  (2,'廁所A','坐式便器',6.32,2.38,.1,90),(2,'廁所A','洗手盆',6.32,3.65,.1,90),
  (2,'廁所B','洗手盆',1.84,7.88,0,180),(2,'廁所B','小便斗',.83,7.88,0,180),(2,'廁所B','小便斗',2.84,7.88,0,180),
  (3,'廁所','坐式便器',6.32,2.30,.1,90),(3,'廁所','洗手盆',6.30,3.45,.1,90),(3,'廁所','小便斗',5.11,3.28,.1,-90)]
 for f,room,typ,x,y,up,angle in items:
  par=f'FLOOR_{f}';z=BASE[f]+up+.012
  override=f==2 and room=='廁所B' and x==2.84
  audit.begin(f'fixture_{f}_{room}_{typ}_{x}','衛浴設備',f'{f}F {room} {typ}',[6 if f==1 else 7,20],'靠門設備原為坐式便器' if override else '原模型缺少圖示衛浴設備',f'補建{typ}可見三維外形，位於約({x:.2f},{y:.2f})m', '2026-09-10 使用者明確指定靠門處改為小便斗；優先於原圖示' if override else '平面符號及配置；產品尺寸／曲面為概念近似')
  def ex(p,zz,h,name):extr(rotate(p,angle,origin=(x,y)),zz,h,name,par,'ceramic','fixture')
  def rotate_point(p):
   a=math.radians(angle);dx,dy=p[0]-x,p[1]-y
   return [x+dx*math.cos(a)-dy*math.sin(a),y+dx*math.sin(a)+dy*math.cos(a),p[2]]
  if typ=='坐式便器':
   ex(ellipse(x,y+.30,.16,.24),z,.24,'wc_pedestal')
   ex(ellipse(x,y+.32,.23,.31).difference(ellipse(x,y+.33,.16,.23)),z+.24,.15,'wc_bowl_rim')
   ex(ellipse(x,y+.32,.22,.30).difference(ellipse(x,y+.33,.16,.23)),z+.39,.025,'wc_seat')
   ex(rect(x-.22,y-.04,x+.22,y+.14),z+.28,.41,'wc_tank')
  elif typ=='洗手盆':
   ex(rect(x-.065,y+.10,x+.065,y+.25),z,.67,'basin_pedestal')
   outer=rect(x-.26,y-.06,x+.26,y+.39).buffer(.035,quad_segs=3)
   inner=ellipse(x,y+.16,.205,.155)
   ex(outer,z+.69,.025,'basin_bottom');ex(outer.difference(inner),z+.715,.105,'basin_rim')
   rod(rotate_point([x,y+.01,z+.82]),rotate_point([x,y+.01,z+.97]),.012,'tap_stem',par,'metal','fixture')
   rod(rotate_point([x,y+.01,z+.97]),rotate_point([x,y+.16,z+.97]),.012,'tap_spout',par,'metal','fixture')
  else:
   ex(rect(x-.18,y-.04,x+.18,y+.08),z+.35,.56,'urinal_back')
   ex(ellipse(x,y+.15,.19,.23).difference(ellipse(x,y+.15,.14,.17)),z+.38,.22,'urinal_bowl')
   ex(ellipse(x,y+.15,.19,.23),z+.36,.03,'urinal_base')
  audit.end()
