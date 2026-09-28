"""Geometry kit for the four interior schemes: primitives in plan metres (x, y,
z relative to the finished floor) plus wall-face and window lookup from the
house manifest, so wall-hung items sit on real wall faces and never seal openings.
"""
import sys, json, math
from pathlib import Path
from collections import defaultdict
from contextlib import contextmanager
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.deps'))
import numpy as np
import trimesh as tm
from shapely.geometry import Polygon, Point, LineString, box as rect
sys.path.insert(0, str(Path(__file__).resolve().parent))
import furniture_detail as fd

T = np.array([[1, 0, 0, -7.18], [0, 0, 1, 0], [0, 1, 0, -8.3], [0, 0, 0, 1]])
BASE = {1: .6, 2: 4.8, 3: 8.4, 4: 11.7}
HEIGHT = {1: 4.2, 2: 3.6, 3: 3.3, 4: 3.1}
FIN = .012  # finished floor thickness above structural level
PLAN = json.loads((ROOT / 'output/model-manifest.json').read_text(encoding='utf-8'))
WALLS = PLAN['walls']; ROOMS = PLAN['rooms']
RP = {(r['floor'], r['key']): Polygon(r['polygon']) for r in ROOMS}


def ceiling_z(f):
    return HEIGHT[f] - .20 - .012


def room_at(f, x, y):
    pt = Point(x, y)
    for (ff, k), p in RP.items():
        if ff == f and p.contains(pt):
            return k
    return None


class Face:
    def __init__(self, w, side, s0, s1):
        a = np.array(w['a'], float); b = np.array(w['b'], float)
        self.L = float(np.linalg.norm(b - a)); self.u = (b - a) / self.L
        self.n = np.array([-self.u[1], self.u[0]]) * side
        self.a = a; self.t = w['t']; self.s0 = s0; self.s1 = s1; self.wall = w; self.side = side

    def p(self, s, off=0.):
        return self.a + self.u * s + self.n * (self.t / 2 + off)

    @property
    def length(self):
        return self.s1 - self.s0

    @property
    def mid(self):
        return (self.s0 + self.s1) / 2


def _intervals(w, L, mode, sill_min=None):
    if mode == 'all':
        return [(0., L)]
    if sill_min is None:
        sill_min = .15 if mode == 'low' else 99
    cuts = sorted((lo, hi) for lo, hi, sill, oh, code in w['cuts'] if sill < sill_min)
    out = []; cur = 0.
    for lo, hi in cuts:
        if lo - cur > .02:
            out.append((cur, lo))
        cur = max(cur, hi)
    if L - cur > .02:
        out.append((cur, L))
    return out


def faces(f, key, mode='full', min_len=.2, sill_min=None):
    """Wall-face runs bounding room `key`. mode: full (no openings), low (windows
    with a sill count as wall), all (entire wall length)."""
    res = []
    for w in WALLS:
        if w['floor'] != f:
            continue
        a = np.array(w['a']); b = np.array(w['b']); L = float(np.linalg.norm(b - a)); u = (b - a) / L
        for side in (1, -1):
            n = np.array([-u[1], u[0]]) * side
            for s0, s1 in _intervals(w, L, mode, sill_min):
                run = None
                for s in np.arange(s0 + .05, s1, .1):
                    q = a + u * s + n * (w['t'] / 2 + .2)
                    hit = room_at(f, *q) == key
                    if hit and run is None:
                        run = [s, s]
                    elif hit:
                        run[1] = s
                    elif run is not None:
                        res.append(Face(w, side, max(s0, run[0] - .05), min(s1, run[1] + .05))); run = None
                if run is not None:
                    res.append(Face(w, side, max(s0, run[0] - .05), min(s1, run[1] + .05)))
    return [r for r in res if r.length >= min_len]


def windows(f, key, codes=('W', 'DW')):
    """Openings on walls that face into room `key`: (face, lo, hi, sill, oh, code)."""
    out = []
    for w in WALLS:
        if w['floor'] != f:
            continue
        for lo, hi, sill, oh, code in w['cuts']:
            if not code.startswith(codes):
                continue
            a = np.array(w['a']); b = np.array(w['b']); L = float(np.linalg.norm(b - a)); u = (b - a) / L
            for side in (1, -1):
                n = np.array([-u[1], u[0]]) * side
                q = a + u * (lo + hi) / 2 + n * (w['t'] / 2 + .3)
                if room_at(f, *q) == key:
                    out.append((Face(w, side, 0, L), lo, hi, sill, oh, code))
    return out


def chamfer_box(w, d, h, c):
    """Box with 45-degree chamfered edges and corners (real furniture is never
    knife-edged; the bevel catches light). Centred on the origin."""
    hx, hy, hz = w / 2, d / 2, h / 2; c = min(c, hx * .45, hy * .45, hz * .45)
    V = {}
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                V[(sx, sy, sz, 0)] = (sx * hx, sy * (hy - c), sz * (hz - c))
                V[(sx, sy, sz, 1)] = (sx * (hx - c), sy * hy, sz * (hz - c))
                V[(sx, sy, sz, 2)] = (sx * (hx - c), sy * (hy - c), sz * hz)
    keys = list(V); idx = {k: i for i, k in enumerate(keys)}; verts = np.array([V[k] for k in keys])
    quads = []
    for ax in range(3):  # six main faces
        for s in (-1, 1):
            corners = [k for k in keys if k[3] == ax and k[ax] == s]
            ctr = np.mean([V[k] for k in corners], axis=0); o = [i for i in range(3) if i != ax]
            corners.sort(key=lambda k: math.atan2(V[k][o[1]] - ctr[o[1]], V[k][o[0]] - ctr[o[0]]))
            quads.append([idx[k] for k in corners])
    for a, b in ((0, 1), (0, 2), (1, 2)):  # twelve edge bevels
        free = 3 - a - b
        for sa in (-1, 1):
            for sb in (-1, 1):
                q = []
                for sf in (-1, 1):
                    sgn = [0, 0, 0]; sgn[a] = sa; sgn[b] = sb; sgn[free] = sf
                    q += [idx[(*sgn, a)], idx[(*sgn, b)]]
                quads.append([q[0], q[1], q[3], q[2]])
    faces = []
    for q in quads:
        faces += [[q[0], q[1], q[2]], [q[0], q[2], q[3]]]
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                faces.append([idx[(sx, sy, sz, 0)], idx[(sx, sy, sz, 1)], idx[(sx, sy, sz, 2)]])
    faces = np.array(faces); tri = verts[faces]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]); flip = (n * tri.mean(axis=1)).sum(1) < 0
    faces[flip] = faces[flip][:, ::-1]
    return tm.Trimesh(verts, faces, process=False)


def material(name, color, rough=.85, metal=0., emissive=None, alpha=None):
    c = [int(color[i:i + 2], 16) for i in (1, 3, 5)] + [alpha or 255]
    return tm.visual.material.PBRMaterial(name=name, baseColorFactor=c, roughnessFactor=rough, metallicFactor=metal,
                                          doubleSided=True, emissiveFactor=emissive,
                                          alphaMode='BLEND' if alpha else 'OPAQUE')


COMMON = {
    'leaf': ('#4f7447', .7, 0), 'leaf2': ('#6f9156', .7, 0), 'soil': ('#4a3a2c', .95, 0), 'canvas': ('#f1ebdd', .9, 0),
    'glass': ('#bcd3d6', .08, .1, None, 70), 'bulb': ('#fff3d6', .3, 0, [1., .86, .6]), 'black': ('#1d1f1f', .5, .3),
    'white': ('#f2f0ea', .6, 0), 'ceramic': ('#eeebe4', .25, 0),
}


class Kit:
    key = ''; label = ''; MATS = {}

    def __init__(self):
        self.batches = defaultdict(list); self.items = []; self.floor = 1; self.room = ''; self._xf = []
        spec = {**COMMON, **self.MATS}; self.mats = {}
        for n, v in spec.items():
            color, rough, metal = v[:3]
            self.mats[n] = material(f'{self.key}_{n}', color, rough, metal, v[3] if len(v) > 3 else None, v[4] if len(v) > 4 else None)

    # ---- low level ----
    FACING = {'+y': 0., '-y': math.pi, '+x': -math.pi / 2, '-x': math.pi / 2}

    @contextmanager
    def xf(self, x, y, facing):
        """Local frame: origin = back centre of a piece, local +y = the way it faces."""
        M = tm.transformations.rotation_matrix(self.FACING.get(facing, facing), [0, 0, 1]); M[:3, 3] = [x, y, 0]
        self._xf.append(M)
        try:
            yield
        finally:
            self._xf.pop()

    def add(self, m, mat, kind='furniture'):
        if mat not in self.mats:
            raise KeyError(mat)
        if self._xf:
            m.apply_transform(self._xf[-1])
        m.apply_transform(T); self.batches[(self.floor, mat, kind)].append(m)

    def Z(self, zr):
        return BASE[self.floor] + FIN + zr

    def item(self, name, x, y, w, d, major=True, **meta):
        if self._xf:
            pts = np.array([[x, y, 0, 1], [x + w, y, 0, 1], [x, y + d, 0, 1], [x + w, y + d, 0, 1]]) @ self._xf[-1].T
            x, y = pts[:, 0].min(), pts[:, 1].min(); w, d = pts[:, 0].max() - x, pts[:, 1].max() - y
        self.items.append(dict(name=name, floor=self.floor, room=self.room, footprint=[round(x, 3), round(y, 3), round(x + w, 3), round(y + d, 3)],
                               size_m=[round(w, 3), round(d, 3)], major=major, approximate=True, **meta))

    def at(self, floor, room):
        self.floor = floor; self.room = room; return self

    # ---- primitives (plan x,y; zr above finished floor) ----
    def box(self, x, y, zr, w, d, h, mat, kind='furniture', r=0.):
        if r:
            r = min(r, w / 2.2, d / 2.2)
            m = tm.creation.extrude_polygon(rect(x + r, y + r, x + w - r, y + d - r).buffer(r, quad_segs=3), h, engine='earcut')
            m.apply_translation([0, 0, self.Z(zr)])
        elif min(w, d, h) >= .025 and kind in ('furniture', 'wallmount', 'fixture'):
            m = chamfer_box(w, d, h, min(.007, min(w, d, h) / 5)); m.apply_translation([x + w / 2, y + d / 2, self.Z(zr) + h / 2])
        else:
            m = tm.creation.box([w, d, h]); m.apply_translation([x + w / 2, y + d / 2, self.Z(zr) + h / 2])
        self.add(m, mat, kind)

    def obox(self, cx, cy, zr, w, d, h, ang, mat, kind='furniture'):
        m = chamfer_box(w, d, h, min(.007, min(w, d, h) / 5)) if min(w, d, h) >= .025 and kind != 'decor' else tm.creation.box([w, d, h])
        m.apply_transform(tm.transformations.rotation_matrix(ang, [0, 0, 1]))
        m.apply_translation([cx, cy, self.Z(zr) + h / 2]); self.add(m, mat, kind)

    def poly(self, polygon, zr, h, mat, kind='furniture'):
        if polygon.is_empty:
            return
        for p in getattr(polygon, 'geoms', [polygon]):
            m = tm.creation.extrude_polygon(p, h, engine='earcut'); m.apply_translation([0, 0, self.Z(zr)]); self.add(m, mat, kind)

    def cyl(self, x, y, zr, r, h, mat, kind='furniture', sec=24):
        m = tm.creation.cylinder(r, h, sections=sec); m.apply_translation([x, y, self.Z(zr) + h / 2]); self.add(m, mat, kind)

    def lathe(self, x, y, zr, profile, mat, kind='decor', sec=24):
        m = tm.creation.revolve(np.array(profile, float), sections=sec); m.apply_translation([x, y, self.Z(zr)]); self.add(m, mat, kind)

    def sphere(self, x, y, zr, r, mat, kind='decor', sub=2, scale=(1, 1, 1)):
        m = tm.creation.icosphere(subdivisions=sub, radius=r); m.apply_scale(scale); m.apply_translation([x, y, self.Z(zr)]); self.add(m, mat, kind)

    def rod(self, a, b, r, mat, kind='furniture', sec=10):
        a = np.array([a[0], a[1], self.Z(a[2])], float); b = np.array([b[0], b[1], self.Z(b[2])], float)
        L = np.linalg.norm(b - a)
        if L < 1e-4:
            return
        m = tm.creation.cylinder(r, L, sections=sec); m.apply_transform(tm.geometry.align_vectors([0, 0, 1], b - a)); m.apply_translation((a + b) / 2)
        self.add(m, mat, kind)

    def soft(self, x, y, zr, w, d, h, mat, kind='furniture', rounding=.4, sections=14):
        m = fd.cushion((w, d, h), rounding=rounding, sections=sections); m.apply_translation([x + w / 2, y + d / 2, self.Z(zr) + h / 2]); self.add(m, mat, kind)

    def osoft(self, cx, cy, zr, w, d, h, ang, mat, kind='furniture', rounding=.4, tilt=0.):
        m = fd.cushion((w, d, h), rounding=rounding, sections=12)
        if tilt:
            m.apply_transform(tm.transformations.rotation_matrix(tilt, [1, 0, 0]))
        m.apply_transform(tm.transformations.rotation_matrix(ang, [0, 0, 1])); m.apply_translation([cx, cy, self.Z(zr) + h / 2]); self.add(m, mat, kind)

    def drape(self, x, y, zr, w, d, h, mat, folds=3, kind='furniture'):
        m = fd.puffy_slab(w, d, h, folds=folds); m.apply_translation([x + w / 2, y + d / 2, self.Z(zr)]); self.add(m, mat, kind)

    def bar(self, p, q, zr, h, t, mat, kind='furniture'):
        if np.linalg.norm(np.subtract(q, p)) < 1e-4:
            return
        self.poly(LineString([tuple(p), tuple(q)]).buffer(t / 2, cap_style=2, join_style=2), zr, h, mat, kind)

    def legs(self, x, y, zr, w, d, h, mat, r=.022, inset=.06):
        for xx in (x + inset, x + w - inset):
            for yy in (y + inset, y + d - inset):
                self.rod([xx, yy, zr], [xx, yy, zr + h], r, mat)

    # ---- wall-referenced helpers ----
    def face_box(self, F, s0, s1, zr, h, depth, mat, kind='wallmount', off=0.):
        s0 = max(F.s0 if F.s1 > F.s0 else 0, s0); s1 = min(F.s1, s1)
        if s1 - s0 < .005:
            return
        self.bar(F.p(s0, off + depth / 2), F.p(s1, off + depth / 2), zr, h, depth, mat, kind)

    def pleats(self, F, s0, s1, zr, h, mat, depth=.06, kind='wallmount', off=.08, waves=None):
        """Open curtain stack: pleated sheet parallel to the wall face."""
        L = s1 - s0
        if L < .05:
            return
        n = waves or max(3, int(L / .07))
        pts = [F.p(s0 + L * i / (n * 6), off + depth / 2 + depth / 2 * math.sin(i / 6 * 2 * math.pi)) for i in range(n * 6 + 1)]
        self.poly(LineString([tuple(p) for p in pts]).buffer(.004, cap_style=2), zr, h, mat, kind)

    # ---- repeated decor ----
    def pot(self, x, y, r=.16, h=.3, mat='clay'):
        self.lathe(x, y, 0, [(0, 0), (r * .78, 0), (r, h * .85), (r * 1.04, h), (r * .92, h), (0, h - .02)], mat, 'decor')
        self.cyl(x, y, h - .03, r * .9, .02, 'soil', 'decor', 16)

    def leaves(self, x, y, zr, count, spread, length, width, droop, mat='leaf', seed=0):
        rng = np.random.default_rng(seed)
        for i in range(count):
            a = i * 2.39996 + rng.random() * .3; up = .2 + rng.random() * .7
            lf = fd.leaf(length=length * (.75 + .5 * rng.random()), width=width, droop=droop)
            lf.apply_transform(tm.transformations.rotation_matrix(-up, [0, 1, 0]))
            lf.apply_transform(tm.transformations.rotation_matrix(a, [0, 0, 1]))
            r = spread * rng.random()
            lf.apply_translation([x + math.cos(a) * r, y + math.sin(a) * r, self.Z(zr + rng.random() * spread * .8)])
            self.add(lf, mat, 'decor')

    def fiddle(self, x, y, h=1.6, pot='clay', seed=1):
        self.item('大型盆栽（琴葉榕）', x - .22, y - .22, .44, .44, False)
        self.pot(x, y, .2, .38, pot); self.rod([x, y, .3], [x + .03, y, h * .75], .018, 'wood', 'decor')
        self.leaves(x, y, h * .45, 26, .28, .24, .15, .25, seed=seed)

    def snake(self, x, y, pot='clay'):
        self.pot(x, y, .13, .26, pot)
        for i in range(9):
            a = i * 2.2; hgt = .45 + (i % 4) * .12
            b = Polygon([(-.03, 0), (.03, 0), (.005, hgt), (-.005, hgt)])
            m = tm.creation.extrude_polygon(b, .008, engine='earcut'); m.apply_transform(tm.transformations.rotation_matrix(math.pi / 2, [1, 0, 0]))
            m.apply_transform(tm.transformations.rotation_matrix(a, [0, 0, 1])); m.apply_translation([x + math.cos(a) * .05, y + math.sin(a) * .05, self.Z(.24)])
            self.add(m, 'leaf2', 'decor')

    def branches(self, x, y, zr, h=.7, mat='wood', seed=3):
        rng = np.random.default_rng(seed)
        for i in range(5):
            a = rng.random() * 6.28; end = [x + math.cos(a) * .22, y + math.sin(a) * .22, zr + h * (.7 + .3 * rng.random())]
            mid = [x + math.cos(a) * .08, y + math.sin(a) * .08, zr + h * .45]
            self.rod([x, y, zr], mid, .008, mat, 'decor'); self.rod(mid, end, .006, mat, 'decor')
            tw = [end[0] + math.cos(a + 1) * .08, end[1] + math.sin(a + 1) * .08, end[2] + .06]; self.rod(mid, tw, .004, mat, 'decor')

    def frame_art(self, F, s, zr, w, h, frame, colors, canvas='canvas', depth=.035, seed=0, mode='blocks'):
        """Framed original artwork on a wall face; painting is geometric blocks."""
        self.face_box(F, s - w / 2, s + w / 2, zr, h, depth, frame)
        self.face_box(F, s - w / 2 + .04, s + w / 2 - .04, zr + .04, h - .08, .006, canvas, off=depth)
        rng = np.random.default_rng(seed)
        if mode == 'ink':
            for i in range(3):
                x0 = s - w / 2 + .12 + rng.random() * (w - .5); self.face_box(F, x0, x0 + .06 + rng.random() * .25, zr + .15 + rng.random() * (h - .5), .03 + rng.random() * .2, .003, colors[0], off=depth + .006)
            return
        n = len(colors)
        for i in range(n + 2):
            bw = (w - .16) * (.18 + .3 * rng.random()); x0 = s - w / 2 + .08 + rng.random() * (w - .16 - bw)
            bh = (h - .16) * (.2 + .45 * rng.random()); z0 = zr + .08 + rng.random() * (h - .16 - bh)
            self.face_box(F, x0, x0 + bw, z0, bh, .003 + .001 * i, colors[i % n], off=depth + .006)

    # ---- room-scale treatments shared by the schemes (each passes its own design) ----
    def dress_windows(self, key, treat, mat, rod='black', codes=('W', 'DW'), panel=.30):
        """Window dressing on every opening facing into room `key`."""
        cz = ceiling_z(self.floor); n = 0
        for F, lo, hi, sill, oh, code in windows(self.floor, key, codes):
            top = sill + oh; W = hi - lo
            if treat in ('drape', 'sheer'):
                rz = min(top + .16, cz - .06)
                others = [(l2, h2) for l2, h2, *_ in F.wall['cuts'] if (l2, h2) != (lo, hi)]
                a0 = max(0.02, lo - panel - .06); b1 = min(F.L - .02, hi + panel + .06)
                self.face_box(F, a0, b1, rz, .03, .03, rod, off=.07)
                for s0, s1 in ((max(.02, lo - panel), lo - .02), (hi + .02, min(F.L - .02, hi + panel))):
                    if s1 - s0 > .08 and not any(l2 < s1 and h2 > s0 for l2, h2 in others):
                        self.pleats(F, s0, s1, .015, rz - .03, mat, off=.1 if treat == 'drape' else .08, depth=.07 if treat == 'drape' else .045)
                        if treat == 'drape':
                            self.face_box(F, s0, s1, .95, .045, .02, rod, off=.17)
                n += 1
            elif code.startswith('W') and W > .45:
                if treat == 'blind':
                    self.face_box(F, lo - .02, hi + .02, top + .03, .07, .07, rod, off=.0)
                    drop = oh * .38
                    self.face_box(F, lo + .02, hi - .02, top - drop, drop + .03, .006, mat, off=.035)
                    self.face_box(F, lo + .02, hi - .02, top - drop - .02, .025, .02, rod, off=.03)
                elif treat == 'venetian':
                    self.face_box(F, lo - .02, hi + .02, top + .03, .05, .06, rod, off=.0)
                    for z in np.arange(top - .05, top - oh * .55, -.055):
                        self.face_box(F, lo + .01, hi - .01, z, .004, .05, mat, off=.01)
                    self.face_box(F, lo + .01, hi - .01, top - oh * .55 - .03, .025, .05, rod, off=.01)
                elif treat == 'shoji':
                    half = W / 2 + .04
                    for i, (s0, off) in enumerate(((lo - .02, .02), (lo + W / 2 - .06, .055))):
                        s1 = s0 + half
                        self.face_box(F, s0, s1, sill - .02, oh + .04, .012, mat, off=off + .012)
                        for a, b in ((s0, s0 + .03), (s1 - .03, s1)):
                            self.face_box(F, a, b, sill - .03, oh + .06, .03, rod, off=off)
                        for z in (sill - .03, sill + oh):
                            self.face_box(F, s0, s1, z, .03, .03, rod, off=off)
                        for k in range(1, 3):
                            a = s0 + (s1 - s0) * k / 3; self.face_box(F, a - .006, a + .006, sill, oh, .014, rod, off=off + .016)
                        for k in range(1, 5):
                            z = sill + oh * k / 5; self.face_box(F, s0, s1, z - .006, .012, .014, rod, off=off + .016)
                n += 1
        return n

    def beams(self, poly, axis, count, w, h, mat, pad=.35):
        """Exposed timber beams under the ceiling across a room polygon."""
        x0, y0, x1, y1 = poly.bounds; cz = ceiling_z(self.floor)
        for i in range(count):
            t = (i + 1) / (count + 1)
            if axis == 'y':
                x = x0 + (x1 - x0) * t; seg = poly.intersection(rect(x - w / 2, y0, x + w / 2, y1))
            else:
                y = y0 + (y1 - y0) * t; seg = poly.intersection(rect(x0, y - w / 2, x1, y + w / 2))
            self.poly(seg, cz - h, h, mat, 'ceiling')

    def crown(self, key, mat, h=.11, d=.05):
        cz = ceiling_z(self.floor)
        for F in faces(self.floor, key, 'all'):
            self.face_box(F, F.s0, F.s1, cz - h, h, d * .45, mat, off=0)
            self.face_box(F, F.s0, F.s1, cz - h * .55, h * .55, d, mat, off=0)
            self.face_box(F, F.s0, F.s1, cz - h - .02, .02, d * .25, mat, off=0)

    def door_zones(self):
        """1.2 m approach rectangles in front of every door on this floor."""
        zones = []
        for w in WALLS:
            if w['floor'] != self.floor:
                continue
            a = np.array(w['a']); b = np.array(w['b']); u = (b - a) / np.linalg.norm(b - a); n = np.array([-u[1], u[0]])
            for lo, hi, sill, oh, code in w['cuts']:
                if code.startswith(('D', 'SD', 'LIFT')):
                    c = a + u * (lo + hi) / 2; hw = (hi - lo) / 2 + .03
                    zones.append(Polygon([tuple(c + u * sx * hw + n * sy * 1.25) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]))
        return zones

    def clear_runs(self, F, off=.02):
        zones = self.door_zones(); runs = []; cur = None
        for s in np.arange(F.s0, F.s1 + 1e-6, .05):
            ok = not any(z.contains(Point(*F.p(s, off))) for z in zones)
            if ok and cur is None:
                cur = [s, s]
            elif ok:
                cur[1] = s
            elif cur is not None:
                runs.append(cur); cur = None
        if cur is not None:
            runs.append(cur)
        return [(a, b) for a, b in runs if b - a > .2]

    def wainscot(self, key, mat, h=.9, bay=.62):
        import copy
        for F0 in faces(self.floor, key, 'low', sill_min=h + .05, min_len=.3):
            for a0, b0 in self.clear_runs(F0):
                F = copy.copy(F0); F.s0, F.s1 = a0, b0
                self.face_box(F, F.s0, F.s1, .09, h - .09, .012, mat)
                self.face_box(F, F.s0, F.s1, h - .01, .04, .035, mat)
                n = max(1, int(F.length / bay)); step = F.length / n
                for i in range(n):
                    a = F.s0 + i * step + .07; b = F.s0 + (i + 1) * step - .07
                    if b - a < .15:
                        continue
                    for s0, s1, z, hh in ((a, b, .2, .02), (a, b, h - .13, .02), (a, a + .02, .2, h - .31), (b - .02, b, .2, h - .31)):
                        self.face_box(F, s0, s1, z, hh, .012, mat, off=.012)

    def picture_rail(self, key, mat, z=2.35):
        for F in faces(self.floor, key, 'low', sill_min=z + .05, min_len=.3):
            self.face_box(F, F.s0, F.s1, z, .035, .025, mat)

    def storage_shelves(self, frame_mat, shelf_mat, box_mats, levels=4, box_kind='lathe'):
        """4F storage room: two shelving runs, entry strip y 4.4..5.8 left clear."""
        for wx in (10.58, 11.86):
            for px in (wx, wx + .40):
                for py in (.2, 4.15):
                    self.box(px, py, 0, .035, .035, 1.95, frame_mat)
            for lv in range(levels):
                self.box(wx, .2, .08 + lv * .5, .435, 3.985, .03, shelf_mat)
                for r in range(4):
                    m = box_mats[(lv + r) % len(box_mats)]
                    if box_kind == 'basket':
                        self.lathe(wx + .22, .7 + r * .95, .11 + lv * .5, [(0, 0), (.15, 0), (.18, .28), (0, .28)], m, 'decor', 14)
                    else:
                        self.box(wx + .05, .32 + r * .95, .11 + lv * .5, .34, .75, .34, m, 'decor', r=.02)
            self.item('收納層架', wx, .2, .435, 3.985)

    def frustum(self, x0, y0, x1, y1, zr, h, shrink, mat, kind='fixture'):
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2; hw, hd = (x1 - x0) / 2, (y1 - y0) / 2
        ring = ((-1, -1), (1, -1), (1, 1), (-1, 1))
        pts = [[cx + sx * hw, cy + sy * hd, 0] for sx, sy in ring] + [[cx + sx * hw * shrink, cy + sy * hd * shrink, h] for sx, sy in ring]
        fcs = [[0, 2, 1], [0, 3, 2], [4, 5, 6], [4, 6, 7]]
        for i in range(4):
            j = (i + 1) % 4; fcs += [[i, j, 4 + j], [i, 4 + j, 4 + i]]
        m = tm.Trimesh(pts, fcs, process=False); m.apply_translation([0, 0, self.Z(zr)]); self.add(m, mat, kind)

    def kitchen(self, layout, cab, top, splash, handle, fridge, hood, uppers, cab_upper=None, handles='bar'):
        """2F kitchen. Real module sizes: worktop 85 cm, depth 60 cm, uppers 60-65 cm
        above worktop, hood 70 cm above hob. Door DW1 (y 3.12-4.68) and D4a stay clear."""
        self.at(2, '廚房'); H = .85; cz = ceiling_z(2); cab_upper = cab_upper or cab
        runs = {'L': [('back', 12.03, .10, 2.23, .60), ('east', 13.66, .70, .60, 2.35)],
                'galley': [('back', 12.03, .10, 2.23, .60), ('east', 13.66, .70, .60, 2.35), ('west', 11.98, .70, .60, 1.30)],
                'I': [('east', 13.66, .10, .60, 2.95)]}[layout]
        for name, x, y, w, d in runs:
            self.box(x + (.05 if name == 'west' else 0), y + (.0 if name != 'back' else 0), 0, w - (.05 if name in ('east', 'west') else 0), d - (.05 if name == 'back' else 0), .1, 'black')
            self.box(x, y, .1, w, d, H - .13, cab)
            front, along = {'back': ('y', (x, x + w)), 'east': ('x', (y, y + d)), 'west': ('x2', (y, y + d))}[name]
            n = max(1, round((along[1] - along[0]) / .6)); step = (along[1] - along[0]) / n
            for i in range(n):
                a = along[0] + i * step + .004; b = a + step - .008
                if front == 'y':
                    self.box(a, y + d, .12, b - a, .018, H - .17, cab)
                    if handles == 'bar':
                        self.box((a + b) / 2 - .08, y + d + .018, H - .16, .16, .02, .012, handle)
                elif front == 'x':
                    self.box(x - .018, a, .12, .018, b - a, H - .17, cab)
                    if handles == 'bar':
                        self.box(x - .038, (a + b) / 2 - .08, H - .16, .02, .16, .012, handle)
                else:
                    self.box(x + w, a, .12, .018, b - a, H - .17, cab)
                    if handles == 'bar':
                        self.box(x + w + .018, (a + b) / 2 - .08, H - .16, .02, .16, .012, handle)
            worktop = rect(x - (.02 if name == 'east' else 0), y, x + w + (.02 if name == 'west' else 0), y + d + (.02 if name == 'back' else 0))
            if name == 'back' and layout != 'I':
                worktop = worktop.difference(rect(12.62, .22, 13.08, .58))
            if name == 'east' and layout == 'I':
                worktop = worktop.difference(rect(13.78, 2.22, 14.14, 2.72))
            self.poly(worktop, H - .03, .03, top)
            self.item({'back': '後側廚櫃', 'east': '東側廚櫃', 'west': '西側廚櫃'}[name], x, y, w, d)
        # sink bowl, tap
        sx, sy, sw, sd = (12.62, .22, .46, .36) if layout != 'I' else (13.78, 2.22, .36, .50)
        self.poly(rect(sx - .02, sy - .02, sx + sw + .02, sy + sd + .02).difference(rect(sx, sy, sx + sw, sy + sd)), H - .21, .18, 'stainless', 'fixture')
        self.box(sx, sy, H - .22, sw, sd, .012, 'stainless', 'fixture')
        tx, ty = (sx + sw / 2, sy - .01) if layout != 'I' else (sx + sw + .05, sy + sd / 2)
        self.rod([tx, ty, H], [tx, ty, H + .3], .014, 'stainless', 'fixture')
        tip = [tx, ty + .2, H + .3] if layout != 'I' else [tx - .2, ty, H + .3]
        self.rod([tx, ty, H + .3], tip, .012, 'stainless', 'fixture')
        self.item('水槽', sx, sy, sw, sd, False)
        # induction/gas hob and hood (70 cm above hob)
        hy = 1.0 if layout != 'I' else .45
        self.box(13.70, hy, H, .52, .56, .008, 'black', 'fixture')
        for dx in (.13, .38):
            for dy in (.14, .41):
                self.cyl(13.70 + dx, hy + dy, H + .008, .075, .008, 'stainless', 'fixture', 18)
        self.item('爐具', 13.70, hy, .52, .56, False)
        hz = H + .70
        if hood == 'chimney':
            self.box(13.66, hy - .04, hz, .60, .64, .08, 'stainless', 'fixture')
            self.frustum(13.70, hy, 14.22, hy + .56, hz + .08, .30, .45, 'stainless')
            self.box(13.86, hy + .16, hz + .38, .26, .26, cz - hz - .38, 'stainless', 'fixture')
        elif hood == 'copper':
            self.frustum(13.66, hy - .04, 14.26, hy + .60, hz, .55, .4, 'copper')
            self.box(13.84, hy + .14, hz + .55, .24, .24, cz - hz - .55, 'copper', 'fixture')
        elif hood == 'canopy':
            self.frustum(13.62, hy - .08, 14.26, hy + .64, hz, .5, .55, 'white')
            self.box(13.62, hy - .08, hz, .64, .72, .05, 'brass', 'fixture')
            self.box(13.78, hy + .08, hz + .5, .36, .40, cz - hz - .5, 'white', 'fixture')
        else:
            self.box(13.66, hy - .05, hz, .61, .66, cz - hz, 'paint', 'fixture')
        self.item('抽油煙機', 13.66, hy - .04, .6, .64, False)
        # backsplash on the wall faces (window openings keep only the low strip)
        for a, b, hgt in ((12.03, 12.55, .65), (12.55, 13.15, .23), (13.15, 14.26, .65)):
            if layout != 'I':
                self.box(a, .092, H, b - a, .008, hgt, splash, 'wallmount')
        for a, b, hgt in (((.10 if layout == 'I' else .70), 1.83, .65), (1.83, 3.05, .23)):
            self.box(14.262, a, H, .008, b - a, hgt, splash, 'wallmount')
        # fridge / tall units
        if layout in ('L', 'galley'):
            fy = 1.0 if layout == 'L' else 2.06
            self.box(11.99, fy, 0, .72, .70, 1.80, fridge, 'furniture', r=.03); self.item('冰箱（約 500 L）', 11.99, fy, .72, .70)
            self.box(12.71, fy + .02, 1.18, .006, .66, .006, 'black', 'fixture')
            for z0, z1 in ((.3, 1.05), (1.3, 1.7)):
                self.box(12.715, fy + .6, z0, .03, .025, z1 - z0, handle, 'fixture')
        else:
            self.box(11.99, .18, 0, .62, 2.8, 2.3, cab, 'furniture'); self.item('高櫃（內嵌冰箱）', 11.99, .18, .62, 2.8)
            for i in range(4):
                self.box(12.61, .2 + i * .69, .05, .015, .67, 2.2, cab)
        # upper cabinets / open shelves (bottom 65 cm above worktop)
        if layout != 'I':
            if uppers == 'cab':
                self.box(13.18, .10, H + .65, 1.08, .35, .72, cab_upper, 'wallmount')
                for i in range(2):
                    self.box(13.19 + i * .54, .45, H + .67, .52, .015, .68, cab_upper, 'wallmount')
            elif uppers == 'open':
                for z in (H + .65, H + 1.05):
                    self.box(13.18, .10, z, 1.08, .26, .035, cab_upper, 'wallmount')
                for z in (H + .65, H + 1.05):
                    self.box(12.03, .10, z, .50, .26, .035, cab_upper, 'wallmount')
