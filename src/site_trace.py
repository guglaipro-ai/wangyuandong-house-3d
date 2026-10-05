"""Vectorise NLSC e-map tiles (Taiwan e-Map, 2026-08 edition) into building footprints
and road surfaces in model coordinates. The e-map is drawn from 1/1000 topographic and
cadastral sources, so its building and road outlines are far more accurate than hand
tracing on the orthophoto. Roof colour is sampled from the NLSC 2023 orthophoto.

Input tiles (zoom 19, 8x8 around the site) are fetched by tmp/geo/fetch19.py into tmp/geo/.
Output: output/realism/site-trace.json (committed; build_surroundings.py reads only that).
"""
from pathlib import Path
import sys, json, math
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.deps')); sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
from PIL import Image, ImageDraw
from shapely.geometry import box, Polygon, mapping
from shapely.ops import unary_union
from site_location import to_model, LAT0, LON0

Z = 19; X0, Y0 = 437277, 227424; N = 2 ** Z
K = 111319.49079327358


def px_lonlat(px, py):
    x = X0 + px / 256; y = Y0 + py / 256
    lon = x / N * 360 - 180
    lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / N))))
    return lon, lat


def px_model(px, py):
    lon, lat = px_lonlat(px, py)
    en = [(lon - LON0) * K * math.cos(math.radians(LAT0)), (lat - LAT0) * K]
    return to_model(en)


def mask_polygons(mask, min_px=20):
    """Row runs -> rectangles -> union. Pixel coordinates."""
    rects = []
    for y in range(mask.shape[0]):
        row = mask[y]
        if not row.any():
            continue
        d = np.diff(np.concatenate([[0], row.astype(np.int8), [0]]))
        for a, b in zip(np.nonzero(d == 1)[0], np.nonzero(d == -1)[0]):
            rects.append(box(a, y, b, y + 1))
    u = unary_union(rects)
    return [g for g in getattr(u, 'geoms', [u]) if g.area >= min_px]


def to_model_poly(p, tol_px=.9):
    p = p.simplify(tol_px, preserve_topology=True)
    ext = [px_model(x, y) for x, y in p.exterior.coords]
    holes = [[px_model(x, y) for x, y in r.coords] for r in p.interiors if Polygon(r).area > 40]
    return Polygon(ext, holes).buffer(0)


if __name__ == '__main__':
    G = ROOT / 'tmp/geo'
    emap9 = np.array(Image.open(G / 'EMAP9-19.png').convert('RGB')).astype(int)
    emap01 = np.array(Image.open(G / 'EMAP01-19.png').convert('RGB')).astype(int)
    photo = np.array(Image.open(G / 'PHOTO2-19.png').convert('RGB')).astype(int)
    # building fill (233,226,233); tolerance covers anti-aliased edges, text is absent in EMAP9
    b = (np.abs(emap9 - [233, 226, 233]).sum(2) <= 12)
    # road surface: white in EMAP01 (background is 247 grey, buildings 230, canal 218)
    r = (emap01.min(2) >= 252)
    water = (np.abs(emap9 - [149, 213, 251]).sum(2) <= 30)
    out = {'source': 'NLSC WMTS EMAP9/EMAP01 (Taiwan e-Map, NLSC 2026-08) zoom 19; roof colour NLSC PHOTO2 (2023)',
           'license': 'https://maps.nlsc.gov.tw/pro/use_clause.jsp', 'tile_origin_z19': [X0, Y0],
           'metres_per_pixel': 156543.03392 * math.cos(math.radians(LAT0)) / N,
           'buildings': [], 'roads': [], 'water': []}
    for p in mask_polygons(b, 25):
        q = p.buffer(.6).buffer(-.6)   # close 1 px seams between adjoining fills
        if q.area < 25:
            continue
        mp = to_model_poly(q)
        if mp.is_empty or mp.area < 4:
            continue
        x0, y0, x1, y1 = [int(v) for v in q.bounds]; x1 += 1; y1 += 1
        m = Image.new('L', (x1 - x0, y1 - y0), 0); ImageDraw.Draw(m).polygon([(x - x0, y - y0) for x, y in q.exterior.coords], fill=1)
        sl = photo[y0:y1, x0:x1]; cols = sl[np.array(m, bool)[:sl.shape[0], :sl.shape[1]]]
        mean = cols.mean(0) if len(cols) else np.array([180, 180, 180])
        out['buildings'].append({'model_xz': mapping(mp), 'area_m2': round(mp.area, 1),
                                 'roof_rgb': [int(v) for v in mean], 'centroid_xz': [round(v, 2) for v in mp.centroid.coords[0]]})
    for p in mask_polygons(r, 60):
        q = p.buffer(1.5).buffer(-1.5)   # fill label holes inside road bands
        mp = to_model_poly(q, .7)
        if mp.area > 6:
            out['roads'].append({'model_xz': mapping(mp), 'area_m2': round(mp.area, 1)})
    for p in mask_polygons(water, 60):
        mp = to_model_poly(p.buffer(1).buffer(-1))
        if mp.area > 10:
            out['water'].append({'model_xz': mapping(mp), 'area_m2': round(mp.area, 1)})
    (ROOT / 'output/realism/site-trace.json').write_text(json.dumps(out, ensure_ascii=False), encoding='utf-8')
    print(len(out['buildings']), 'buildings', len(out['roads']), 'road parts', len(out['water']), 'water')
