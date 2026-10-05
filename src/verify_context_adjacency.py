"""Check the exported site context against the registered real-world layout:
house and lot off the road, no neighbour inside the house, neighbours on the NE / rear / SW
sides at plausible gaps, poles outside the asphalt, and the permit lot-line distances."""
from pathlib import Path
import sys, json, hashlib
ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT / '.deps'), str(ROOT / 'src')]
import numpy as np, trimesh as tm
from shapely.geometry import Polygon, MultiPoint, Point, shape
from shapely.ops import unary_union
from site_location import ROT, OFFSET, PARCEL_MODEL, REG
OUT = ROOT / 'output'; DEST = OUT / 'corrections'
house = tm.load(OUT / 'house.glb', force='scene', process=False)
context = tm.load(OUT / 'surroundings.glb', force='scene', process=False)
meta = json.loads((OUT / 'realism/site-context.json').read_text(encoding='utf-8'))
main = MultiPoint(np.concatenate([g.vertices[:, [0, 2]] for n, g in house.geometry.items() if n.startswith(('FLOOR_', 'ROOF_'))])).convex_hull
def projected_mesh(g): return unary_union([p for t in g.triangles if (p := Polygon(t[:, [0, 2]])).area > 1e-8])
road = projected_mesh(context.geometry['CONTEXT_road'])
lot = Polygon(PARCEL_MODEL)
neighbors = [(f['label'], shape(f['footprint_model_xz']), f) for f in meta['features'] if f['type'] == 'neighbor']
checks = {}
checks['house_on_road_m2'] = main.intersection(road).area
checks['lot_on_road_m2'] = lot.intersection(road).area
checks['neighbour_inside_house_m2'] = sum(p.intersection(main).area for _, p, _ in neighbors)
# side classification in plan axes: plan x = model x + 7.18 (NE -> SW), plan y = model z + 8.3 (rear -> front)
sides = {'NE (plan left)': lambda c: c[0] + 7.18 < 0, 'rear SE': lambda c: c[1] + 8.3 < 0, 'SW (plan right)': lambda c: c[0] + 7.18 > 14.36}
nearest = {}
for side, test in sides.items():
    cand = [(p.distance(main), lab) for lab, p, _ in neighbors if test(np.array(p.representative_point().coords[0])) and p.distance(main) < 15]
    nearest[side] = min(cand) if cand else None
checks['nearest_neighbour_by_side'] = {k: (None if v is None else {'label': v[1], 'gap_m': round(v[0], 2)}) for k, v in nearest.items()}
checks['permit_lot_line_distance_rms_m'] = REG['house_plan_to_en']['permit_lot_line_distance_rms_m']
checks['site_plan_registration_rms_m'] = REG['site_plan_to_en']['residual_rms_m']
assert checks['house_on_road_m2'] < 1e-5, checks
assert checks['lot_on_road_m2'] < .5, checks
assert checks['neighbour_inside_house_m2'] < 1e-5, checks
assert all(v is not None and .3 <= v[0] <= 6 for v in nearest.values()), checks['nearest_neighbour_by_side']
assert checks['permit_lot_line_distance_rms_m'] < .2
poles = next(f for f in meta['features'] if f['type'] == 'utilities')['poles']
pole_checks = []
for pole in poles:
    p = Point(pole['center_model_xz']); r = pole['radius_m']
    c = {'id': pole['id'], 'type': pole['type'], 'edge_distance_m': round(p.distance(road), 3), 'base_in_asphalt_m2': p.buffer(r).intersection(road).area,
         'shift_from_street_view_estimate_m': round(float(np.linalg.norm(np.array(pole['center_model_xz']) - (np.array(pole['observed_east_north']) - OFFSET) @ ROT.T)), 2)}
    assert c['base_in_asphalt_m2'] < 1e-6 and c['edge_distance_m'] < .8 and c['shift_from_street_view_estimate_m'] < 3, c
    pole_checks.append(c)
assert len(pole_checks) == 5
report = {'passed': True, 'date': '2026-10-05 UTC+8', 'checks': checks, 'poles': pole_checks,
          'basis': 'Lot 318 and house placement from the permit site plan registered to the NLSC e-map; neighbours and roads are e-map outlines; poles from Street View June 2026.',
          'sha256': {name: hashlib.sha256((OUT / name).read_bytes()).hexdigest() for name in ['house.glb', 'surroundings.glb']}}
(DEST / 'adjacency-validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
svg = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="-40 -40 80 80"><rect x="-40" y="-40" width="80" height="80" fill="#f0f1e8"/>']
for geom, color in [(road, '#727b7e'), (lot, '#cfe8c4'), (main, '#287c66'), *[(p, '#bb8a65') for _, p, _ in neighbors]]:
    for p in getattr(geom, 'geoms', [geom]):
        if p.geom_type != 'Polygon': continue
        d = ' '.join('M' + ' L'.join(f'{x:.3f},{y:.3f}' for x, y in ring.coords) + ' Z' for ring in [p.exterior, *p.interiors])
        svg.append(f'<path d="{d}" fill="{color}" fill-rule="evenodd" stroke="white" stroke-width=".06"/>')
for pole in poles:
    x, y = pole['center_model_xz']; svg.append(f'<circle cx="{x}" cy="{y}" r=".35" fill="{"#f2b705" if pole["type"] == "streetlight" else "#dc4e28"}" stroke="white" stroke-width=".07"/>')
nx, ny = np.array([0, 5]) @ ROT.T
svg.append(f'<path d="M-34,-32 l{nx},{ny}" stroke="#27342f" stroke-width=".25"/><text x="{-34 + nx}" y="{-32 + ny - .8}" font-size="1.7">北</text>')
svg.append('<text x="-38" y="37" font-size="1.4">綠：地號318　深綠：住宅　棕：鄰房（電子地圖）　灰：道路　黃：路燈　紅：電桿</text></svg>')
(DEST / 'adjacency.svg').write_text(''.join(svg), encoding='utf-8')
print(json.dumps(report, ensure_ascii=False))
