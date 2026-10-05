"""Walk-through circulation check on the exported GLBs (empty house + four schemes).

Mirrors walk_mode.js: body = three spheres r 0.22 m at feet+0.45/0.95/1.45 m, so any
non-decor triangle between feet+0.23 m and feet+1.67 m blocks; lower surfaces are steps.
Per floor, free cells (5 cm grid) are flood-filled from the stair hall. A room is
"comfortable" when most of its floor is reachable with a 0.40 m body radius
(80 cm clear aisle, the usual residential circulation width); the 0.22 m result is
what the walk engine physically allows. Writes output/circulation/*.json|png.
"""
from pathlib import Path
import sys, json, math
from collections import deque
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.deps'))
import numpy as np
import trimesh as tm
from PIL import Image
from shapely.geometry import Polygon

BASE = {1: .6, 2: 4.8, 3: 8.4, 4: 11.7}
CELL = .05
X0, Y0, NX, NY = -1.0, -1.0, 340, 380          # plan window -1..16 x -1..18 m
BAND = (.23, 1.67)
SKIP = {'decor', 'ceiling', 'room'}
RADII = {'engine': .22, 'aisle60': .30, 'aisle80': .40}
SEED = (9.2, 4.9)                              # stair hall in front of the lift, every floor
OUT = ROOT / 'output/circulation'


def kind_of(name):
    p = name.split('_')
    if p[0] == 'STYLE':
        return p[3], int(p[2])
    if p[0] == 'FLOOR':
        return p[2], int(p[1])
    return p[1] if len(p) > 1 else p[0], 0


def triangles(path):
    scene = tm.load(path, force='scene', process=False)
    out = {}
    for node in scene.graph.nodes_geometry:
        mat, g = scene.graph[node]
        kind, floor = kind_of(g)
        if kind in SKIP:
            continue
        m = scene.geometry[g]
        v = tm.transformations.transform_points(m.vertices, mat)
        t = v[m.faces][:, :, [0, 2, 1]] + [7.18, 8.3, 0]    # plan x, plan y, height
        out.setdefault(floor, []).append((kind, t))
    return out


def sample(tris, step=.025):
    """Barycentric point samples covering each triangle at ~step spacing."""
    pts = []
    edge = np.max(np.linalg.norm(tris - np.roll(tris, 1, axis=1), axis=2), axis=1)
    n_all = np.clip(np.ceil(edge / step).astype(int), 1, 400)
    for n in np.unique(n_all):
        sel = tris[n_all == n]
        i, j = np.meshgrid(np.arange(n + 1), np.arange(n + 1), indexing='ij'); k = i + j <= n
        a = (i[k] / n)[:, None]; b = (j[k] / n)[:, None]
        for c in range(0, len(sel), max(1, 400000 // len(a))):
            s = sel[c:c + max(1, 400000 // len(a))]
            p = s[:, None, 0] + a[None] * (s[:, None, 1] - s[:, None, 0]) + b[None] * (s[:, None, 2] - s[:, None, 0])
            pts.append(p.reshape(-1, 3))
    return np.concatenate(pts) if pts else np.zeros((0, 3))


def cells(pts):
    ix = np.floor((pts[:, 0] - X0) / CELL).astype(int); iy = np.floor((pts[:, 1] - Y0) / CELL).astype(int)
    ok = (ix >= 0) & (ix < NX) & (iy >= 0) & (iy < NY)
    g = np.zeros((NX, NY), bool); g[ix[ok], iy[ok]] = True
    return g


def dilate(g, r):
    rr = int(math.ceil(r / CELL)); out = g.copy()
    for dx in range(-rr, rr + 1):
        for dy in range(-rr, rr + 1):
            if dx * dx + dy * dy <= (r / CELL) ** 2 and (dx or dy):
                out |= np.roll(np.roll(g, dx, 0), dy, 1)
    return out


def flood(free, seed):
    sx, sy = int((seed[0] - X0) / CELL), int((seed[1] - Y0) / CELL)
    seen = np.zeros_like(free)
    if not free[sx, sy]:
        # nearest free cell to the seed
        idx = np.argwhere(free)
        if not len(idx):
            return seen
        sx, sy = idx[np.argmin((idx[:, 0] - sx) ** 2 + (idx[:, 1] - sy) ** 2)]
    q = deque([(sx, sy)]); seen[sx, sy] = True
    while q:
        x, y = q.popleft()
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < NX and 0 <= ny < NY and free[nx, ny] and not seen[nx, ny]:
                seen[nx, ny] = True; q.append((nx, ny))
    return seen


def route(free, wide, seed, target_mask):
    """Shortest 8-connected path seed -> deepest reachable cell of target; returns plan waypoints."""
    sx, sy = int((seed[0] - X0) / CELL), int((seed[1] - Y0) / CELL)
    if not free[sx, sy]:
        idx = np.argwhere(free); sx, sy = idx[np.argmin((idx[:, 0] - sx) ** 2 + (idx[:, 1] - sy) ** 2)]
    goal_cells = target_mask & wide
    if not goal_cells.any():
        goal_cells = target_mask & free
    if not goal_cells.any():
        return None
    # prefer the goal cell farthest from obstacles: erode until it would vanish
    g = goal_cells.copy()
    for _ in range(12):
        e = g & np.roll(g, 1, 0) & np.roll(g, -1, 0) & np.roll(g, 1, 1) & np.roll(g, -1, 1)
        if not e.any():
            break
        g = e
    par = -np.ones((NX, NY, 2), int); dist = np.full((NX, NY), np.inf); dist[sx, sy] = 0
    import heapq
    h = [(0., sx, sy)]; end = None
    while h:
        d, x, y = heapq.heappop(h)
        if d > dist[x, y]:
            continue
        if g[x, y]:
            end = (x, y); break
        for dx, dy, c in ((1, 0, 1), (-1, 0, 1), (0, 1, 1), (0, -1, 1), (1, 1, 1.414), (1, -1, 1.414), (-1, 1, 1.414), (-1, -1, 1.414)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < NX and 0 <= ny < NY and free[nx, ny]:
                nd = d + c * (1 if wide[nx, ny] else 3)   # stay in the comfortable aisle when possible
                if nd < dist[nx, ny]:
                    dist[nx, ny] = nd; par[nx, ny] = (x, y); heapq.heappush(h, (nd, nx, ny))
    if end is None:
        return None
    path = [end]
    while path[-1] != (sx, sy):
        path.append(tuple(par[path[-1]]))
    path = path[::-1]
    def clear(a, b):
        n = int(max(abs(b[0] - a[0]), abs(b[1] - a[1]))) + 1
        for t in np.linspace(0, 1, n + 1):
            if not wide[int(round(a[0] + (b[0] - a[0]) * t)), int(round(a[1] + (b[1] - a[1]) * t))]:
                return False
        return True
    pts = [path[0]]; i = 0
    while i < len(path) - 1:
        j = len(path) - 1
        while j > i + 1 and not clear(path[i], path[j]):
            j -= 1
        pts.append(path[j]); i = j
    return [[round(X0 + (x + .5) * CELL, 3), round(Y0 + (y + .5) * CELL, 3)] for x, y in pts]


def room_mask(poly):
    p = Polygon(poly) if isinstance(poly, list) else poly; xs = X0 + (np.arange(NX) + .5) * CELL; ys = Y0 + (np.arange(NY) + .5) * CELL
    gx, gy = np.meshgrid(xs, ys, indexing='ij')
    from shapely import contains_xy
    return contains_xy(p, gx, gy)


def door_mask(f):
    """Door openings (plus 45 cm each side) where only the engine radius is required."""
    man = json.loads((ROOT / 'output/model-manifest.json').read_text(encoding='utf-8'))
    walls = {(w['floor'], w['name']): w for w in man['walls']}
    from shapely.geometry import box as rect
    from shapely.ops import unary_union
    polys = []
    for o in man['openings']:
        if o['floor'] != f or not o['code'].startswith(('D', 'SD', 'LIFT')):
            continue
        w = walls[f, o['wall']]; a = np.array(w['a']); b = np.array(w['b']); u = (b - a) / np.linalg.norm(b - a); n = np.array([-u[1], u[0]])
        c = np.array(o['center']); hw = o['width'] / 2; d = w['t'] / 2 + .45
        polys.append(Polygon([c - u * hw - n * d, c + u * hw - n * d, c + u * hw + n * d, c - u * hw + n * d]))
    return room_mask(unary_union(polys)) if polys else np.zeros((NX, NY), bool)


def analyse(label, path, rooms):
    data = triangles(path); report = {}; maps = {}
    for f, base in BASE.items():
        tris = np.concatenate([t for _, t in data.get(f, [])])
        z = tris[:, :, 2] - base
        # Standable floor: near-horizontal faces whose top is within one step of this level.
        nrm = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0]); nz = np.abs(nrm[:, 2]) / (np.linalg.norm(nrm, axis=1) + 1e-12)
        floor = (nz > .95) & (z.max(1) > -.05) & (z.max(1) < BAND[0])
        ground = cells(sample(tris[floor], .04))
        # A floor patch hidden under an obstacle is still not standable; that is handled by obstacles.
        band = (z.max(1) > BAND[0]) & (z.min(1) < BAND[1])
        pts = sample(tris[band]); zz = pts[:, 2] - base
        block = cells(pts[(zz > BAND[0]) & (zz < BAND[1])])
        # Close small floor seams (tile joints, sampling gaps) so they are not read as holes.
        ground = dilate(ground, .06) & ~block
        res = {}
        doors = door_mask(f); engine_free = ground & ~dilate(block, RADII['engine'])
        for key, r in RADII.items():
            free = (ground & ~dilate(block, r)) | (doors & engine_free)
            res[key] = flood(free, SEED)
        maps[f] = (ground, block, res)
        wide = ground & ~dilate(block, RADII['engine'] + .06)
        rr = []
        for room in rooms:
            if room['floor'] != f:
                continue
            m = room_mask(room['polygon']) & ground & ~block
            area = m.sum() * CELL * CELL
            if area < .3:
                continue
            row = {'room': room['label'], 'key': room['key'], 'floor_m2': round(float(area), 2)}
            for key in RADII:
                row[key] = round(float((res[key] & m).sum() * CELL * CELL), 2)
            # Reachable centre-line area relative to what a free-standing person could occupy.
            row['reachable_engine'] = bool((res['engine'] & m).sum() > 0)
            row['reachable_aisle80'] = bool((res['aisle80'] & m).sum() > 0)
            row['route'] = route(engine_free, wide | (doors & engine_free), SEED, m & res['engine'])
            rr.append(row)
        report[f] = rr
    return report, maps


def draw(maps, path):
    tiles = []
    for f in BASE:
        ground, block, res = maps[f]
        img = np.full((NX, NY, 3), 255, np.uint8)
        img[ground] = (225, 225, 225)
        img[res['engine']] = (250, 200, 120)     # walkable only by squeezing (44-60 cm)
        img[res['aisle60']] = (170, 210, 240)    # 60-80 cm
        img[res['aisle80']] = (130, 200, 140)    # >= 80 cm comfortable
        img[block] = (40, 40, 40)
        for k in range(0, NX, int(1 / CELL)): img[k, :] = img[k, :] * .8 + np.array([255, 0, 0]) * .2   # 1 m grid (plan x = k*CELL-1)
        for k in range(0, NY, int(1 / CELL)): img[:, k] = img[:, k] * .8 + np.array([255, 0, 0]) * .2
        Image.fromarray(np.transpose(img, (1, 0, 2))).resize((NX * 3, NY * 3), Image.NEAREST).save(str(path).replace('.png', f'-{f}F.png'))
        tiles.append(np.transpose(img, (1, 0, 2)))   # rows = plan y (back at top), cols = plan x
        tiles.append(np.full((NY, 6, 3), 255, np.uint8))
    im = np.concatenate(tiles, axis=1)
    Image.fromarray(im).resize((im.shape[1] * 2, im.shape[0] * 2), Image.NEAREST).save(path)


if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    rooms = json.loads((ROOT / 'output/model-manifest.json').read_text(encoding='utf-8'))['rooms']
    targets = {'empty': ROOT / 'output/house.glb'} | {s: ROOT / f'output/styles/{s}.glb' for s in ('bohemian', 'industrial', 'eclectic', 'wabisabi')}
    only = [a for a in sys.argv[1:] if not a.startswith('-')]
    full = {}
    for label, path in targets.items():
        if only and label not in only:
            continue
        rep, maps = analyse(label, path, rooms)
        draw(maps, OUT / f'{label}.png'); full[label] = rep
        # Wet rooms, bedrooms, galley kitchen and store rooms need a 60 cm path; living/gallery/hall/terrace 80 cm.
        wet = {(r['floor'], r['key']) for r in rooms if r['wet'] or r['key'].startswith(('BED', 'STORAGE', 'DINING')) and r['label'] != '佛廳／祭祀空間'}
        bad = [(f, r['room'], r['floor_m2'], r['engine'], r['aisle60'], r['aisle80']) for f, rr in rep.items() for r in rr
               if not r['reachable_engine'] or ((f, r['key']) in wet and r['aisle60'] < .28 * r['floor_m2'])
               or ((f, r['key']) not in wet and r['aisle80'] < .4 * r['floor_m2'])]
        print(label, 'issues:', bad, flush=True)
    (OUT / ('circulation.json' if not only else f'circulation-{"-".join(only)}.json')).write_text(
        json.dumps({'method': __doc__, 'cell_m': CELL, 'radii_m': RADII, 'results': full}, ensure_ascii=False, indent=1), encoding='utf-8')
