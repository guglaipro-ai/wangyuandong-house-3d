"""Real-world fit-out details added to the drawing-based house.

Values follow the PDF where it speaks (p8 註1 二丁掛外牆, 註2 背襯強化玻璃欄杆,
p20 W038/R022 構造, NE elevation roof ladder) and common Taiwan residential
practice otherwise (sources in output/realism/references.html):
- skirting 8 cm; switches centred 120 cm; outlets centred 30 cm
- split air-conditioner indoor unit 80x22x29 cm, top 15 cm below ceiling
- interior window sill board 2.5 cm; door architrave 6 cm
- rooftop stainless water tank (common practice; not drawn on the permit set)
All positions are concept placements derived from the traced plan, not MEP design.
"""
import math
import numpy as np
import shapely
from shapely.geometry import Polygon, Point, box as rect
from shapely.ops import unary_union

NOT_INTERIOR = {'TERRACE'}


def _polys(rooms, f, pred=lambda r: True):
    return [(r, Polygon(r['polygon'])) for r in rooms if r['floor'] == f and pred(r)]


def _slice_on_boundaries(m, areas, label):
    """Re-triangulate axis-aligned vertical faces so no triangle crosses a boundary
    line of `areas` (plan x or y). Each wall plane is merged into 2D polygons, cut into
    strips with shapely and triangulated again; the covered surface is unchanged."""
    import trimesh as tm
    from collections import defaultdict
    xs, ys = set(), set()
    for a in areas:
        for g in getattr(a, 'geoms', [a]):
            for ring in [g.exterior, *g.interiors]:
                for x, y in ring.coords:
                    xs.add(round(x - 7.18, 4)); ys.add(round(y - 8.3, 4))
    n = m.face_normals
    groups = defaultdict(list); keep = np.ones(len(m.faces), bool)
    for i in np.nonzero((np.abs(n[:, 1]) < 1e-6) & ((np.abs(n[:, 0]) > 1 - 1e-6) | (np.abs(n[:, 2]) > 1 - 1e-6)))[0]:
        ax = 0 if abs(n[i, 0]) > .5 else 2                 # normal axis
        d = round(float(m.vertices[m.faces[i][0], ax]), 4)
        groups[(ax, int(np.sign(n[i, ax])), d)].append(i); keep[i] = False
    out = [tm.Trimesh(m.vertices, m.faces[keep], process=False)]
    for (ax, sg, d), idx in groups.items():
        along = 2 if ax == 0 else 0                          # horizontal axis lying in the face
        cuts = sorted(ys if along == 2 else xs)
        tri = m.vertices[m.faces[idx]][:, :, [along, 1]]
        shape = unary_union([Polygon(t) for t in tri if Polygon(t).area > 1e-10])
        lo, _, hi, _ = shape.bounds
        edges = [lo - 1] + [c for c in cuts if lo + 1e-4 < c < hi - 1e-4] + [hi + 1]
        # finish of each strip (probe 0.3 m in front of the face, mid-height); merge runs
        normal = np.eye(3)[ax] * sg
        strips = []
        for e0, e1 in zip(edges, edges[1:]):
            mid = (max(e0, lo) + min(e1, hi)) / 2; q = np.zeros(3); q[along] = mid; q[ax] = d; q += normal * .3
            k = label(q[0] + 7.18, q[2] + 8.3)
            if strips and strips[-1][2] == k:
                strips[-1][1] = e1
            else:
                strips.append([e0, e1, k])
        if len(strips) == 1:
            out.append(tm.Trimesh(m.vertices, m.faces[idx], process=False)); continue
        for e0, e1, _ in strips:
            piece = shape.intersection(rect(e0, -1e3, e1, 1e3))
            for g in getattr(piece, 'geoms', [piece]):
                if g.geom_type != 'Polygon' or g.area < 1e-8:
                    continue
                v2, f2 = tm.creation.triangulate_polygon(g, engine='earcut')
                v3 = np.zeros((len(v2), 3)); v3[:, along] = v2[:, 0]; v3[:, 1] = v2[:, 1]; v3[:, ax] = d
                tri3 = v3[f2]; cr = np.cross(tri3[:, 1] - tri3[:, 0], tri3[:, 2] - tri3[:, 0])
                if np.dot(cr.sum(0), normal) < 0:
                    f2 = f2[:, ::-1]          # flip winding (Trimesh.invert keeps stale normals here)
                out.append(tm.Trimesh(v3, f2, process=False))
    return tm.util.concatenate(out)


def split_wall_faces(m, par, kind, rooms):
    """Assign exterior faces to 二丁掛 facade tile, wet-room faces to wall tile,
    remaining interior faces to paint. Triangle positions are untouched."""
    n = m.face_normals
    c = m.triangles_center
    vertical = np.abs(n[:, 1]) < .5
    px = c[:, 0] + 7.18 + n[:, 0] * .3
    py = c[:, 2] + 8.3 + n[:, 2] * .3
    if kind == 'parapet' or not par.startswith('FLOOR_'):
        facade = vertical
        wet = np.zeros(len(n), bool)
    else:
        f = int(par.split('_')[1])
        # Enclosed but unnamed spaces (stair/lift core, 2F inner lobbies, 1F WC passage) are
        # interior too; a 0.3 m closing then fills wall thickness and column gaps between
        # adjacent rooms so only faces that look outdoors receive the 二丁掛 facade tile.
        enclosed = {1: [rect(6.6, 0, 11.95, 5.95), rect(6.53, 5.9, 8.62, 7.68)],
                    2: [rect(6.6, 0, 11.95, 5.95), rect(4.85, 4.2, 6.65, 5.9), rect(3.5, 5.9, 4.85, 8.2)],
                    3: [rect(6.6, 0, 11.95, 5.95)], 4: [rect(6.6, 0, 10.45, 5.95)]}.get(f, [])
        interior = unary_union([p for r, p in _polys(rooms, f, lambda r: r['key'] not in NOT_INTERIOR)] + enclosed)
        interior = interior.buffer(.3, join_style=2).buffer(-.3, join_style=2).buffer(.05)
        wets = [p for r, p in _polys(rooms, f, lambda r: r['wet'])]
        wet_area = unary_union(wets).buffer(.05) if wets else None
        # A long wall face can run past several spaces (e.g. a WC and the pipe void behind
        # it); classifying its two big triangles would leave a diagonal tile/brick seam.
        # Cut the mesh on every boundary line first so each triangle lies in one space.
        def label(x, y):
            return 0 if not interior.contains(Point(x, y)) else 2 if wet_area is not None and wet_area.contains(Point(x, y)) else 1
        m = _slice_on_boundaries(m, [interior] + ([wet_area] if wet_area else []), label)
        n = m.face_normals; c = m.triangles_center; vertical = np.abs(n[:, 1]) < .5
        px = c[:, 0] + 7.18 + n[:, 0] * .3; py = c[:, 2] + 8.3 + n[:, 2] * .3
        inside = shapely.contains_xy(interior, px, py)
        facade = vertical & ~inside
        wet = vertical & inside & (shapely.contains_xy(wet_area, px, py) if wets else False)
    paint = ~(facade | wet)
    out = {}
    for name, mask in [('facade', facade), ('wetwall', wet), ('paint', paint)]:
        idx = np.nonzero(mask)[0]
        if len(idx):
            out[name] = m.submesh([idx], append=True)
    return out


def add_real_details(ns):
    WALLS = ns['WALLS']; ROOMS = ns['ROOMS']; BASE = ns['BASE']; HEIGHT = ns['HEIGHT']
    box = ns['box']; bar = ns['bar']; extr = ns['extr']; rod = ns['rod3']
    count = {}

    def tally(k, v=1):
        count[k] = count.get(k, 0) + v

    polys = {f: _polys(ROOMS, f) for f in BASE}

    def room_at(f, x, y):
        pt = Point(x, y)
        for r, p in polys[f]:
            if p.contains(pt):
                return r
        return None

    def top(f):
        return BASE[f] + HEIGHT[f] - .20

    def wall_frames(w):
        a = np.array(w['a'], float); b = np.array(w['b'], float)
        L = float(np.linalg.norm(b - a)); u = (b - a) / L
        n = np.array([-u[1], u[0]])
        return a, u, n, L

    def solid(w, L, floor_level=False):
        """Intervals without openings. With floor_level, windows count as solid."""
        cuts = sorted((lo, hi) for lo, hi, sill, oh, code in w['cuts'] if not (floor_level and sill > .15))
        out = []; cur = 0.
        for lo, hi in cuts:
            if lo - cur > .02:
                out.append((cur, lo))
            cur = max(cur, hi)
        if L - cur > .02:
            out.append((cur, L))
        return out

    def runs(w, side, intervals, ok, step=.1):
        """Split intervals into runs whose room (probed 20 cm off the face) passes ok()."""
        a, u, n, L = wall_frames(w); nn = n * side; res = []
        for s0, s1 in intervals:
            cur = None
            for s in np.arange(s0 + step / 2, s1, step):
                p = a + u * s + nn * (w['t'] / 2 + .2)
                r = room_at(w['floor'], *p)
                key = r['key'] if r is not None and ok(r) else None
                if cur and cur[2] == key:
                    cur[1] = s
                else:
                    if cur and cur[2]:
                        res.append(cur)
                    cur = [s, s, key, r]
            if cur and cur[2]:
                res.append(cur)
        return [(max(s0, lo - step / 2), min(s1, hi + step / 2), room) for lo, hi, key, room in res
                for s0, s1 in intervals if s0 <= lo <= s1]

    dry = lambda r: not r['wet'] and r['key'] not in NOT_INTERIOR | {'ELEVATOR'}

    def face_bar(w, side, s0, s1, z, h, depth, name, mat, kind, gap=0.):
        a, u, n, L = wall_frames(w); off = n * side * (w['t'] / 2 + gap + depth / 2)
        bar(a + u * s0 + off, a + u * s1 + off, z, h, depth, name, f"FLOOR_{w['floor']}", mat, kind)

    # 1) Skirting 8 cm on every dry interior wall face (doors interrupt it).
    for w in WALLS:
        a, u, n, L = wall_frames(w)
        for side in (1, -1):
            for s0, s1, r in runs(w, side, solid(w, L, True), dry):
                if s1 - s0 > .08:
                    face_bar(w, side, s0, s1, BASE[w['floor']] + r['raise_by'], .08, .012, 'skirting', 'skirting', 'trim')
                    tally('skirting_m', round(s1 - s0, 2))

    # 2) Painted ceilings with recessed downlights (hidden by the viewer in cutaway).
    stair_void = rect(6.70, -1, 12.0, 4.45)
    for r in ROOMS:
        f = r['floor']; key = r['key']
        if key in ('TERRACE', 'STORAGE'):
            continue
        p = Polygon(r['polygon']).buffer(.04, join_style=2)
        if key in ('STAIR', 'LOBBY'):
            p = p.difference(stair_void)
        if p.is_empty or p.area < .3:
            continue
        z = top(f) - .012
        extr(p, z, .01, 'ceiling_' + key, f'FLOOR_{f}', 'ceiling', 'ceiling')
        tally('ceiling_m2', round(p.area, 2))
        inner = p.buffer(-.55)
        pts = []
        if not inner.is_empty:
            x0, y0, x1, y1 = inner.bounds
            nx = max(1, round((x1 - x0) / 1.8) + 1); ny = max(1, round((y1 - y0) / 1.8) + 1)
            for x in np.linspace(x0, x1, nx) if nx > 1 else [(x0 + x1) / 2]:
                for y in np.linspace(y0, y1, ny) if ny > 1 else [(y0 + y1) / 2]:
                    if inner.contains(Point(x, y)):
                        pts.append((x, y))
        if not pts:
            c = p.representative_point(); pts = [(c.x, c.y)]
        for x, y in pts:
            ring = Point(x, y).buffer(.07, quad_segs=6)
            extr(ring, z - .004, .004, 'downlight_trim', f'FLOOR_{f}', 'plate', 'ceiling')
            extr(Point(x, y).buffer(.05, quad_segs=6), z - .006, .002, 'downlight_lens', f'FLOOR_{f}', 'lamp', 'ceiling')
            tally('downlights')

    # 3) Door architraves, switches beside the latch jamb, interior window sills.
    for w in WALLS:
        a, u, n, L = wall_frames(w); f = w['floor']; z = w['z']
        for lo, hi, sill, oh, code in w['cuts']:
            if code.startswith('D') and not code.startswith('DW'):
                zz = z + sill
                for side in (1, -1):
                    if lo - .06 > 0:
                        face_bar(w, side, lo - .06, lo, zz, oh + .06, .012, 'architrave', 'skirting', 'door')
                    if hi + .06 < L:
                        face_bar(w, side, hi, hi + .06, zz, oh + .06, .012, 'architrave', 'skirting', 'door')
                    if zz + oh + .06 < z + w['h']:
                        face_bar(w, side, max(0, lo - .06), min(L, hi + .06), zz + oh, .06, .012, 'architrave', 'skirting', 'door')
                    tally('architraves')
                    s = hi + .16 if hi + .25 < L else lo - .16
                    blocked = any(l2 - .05 < s < h2 + .05 for l2, h2, *_ in w['cuts'])
                    probe = a + u * s + n * side * (w['t'] / 2 + .2)
                    r = room_at(f, *probe)
                    if not blocked and 0 < s < L and r is not None and r['key'] not in NOT_INTERIOR:
                        face_bar(w, side, s - .035, s + .035, z + 1.14, .12, .01, 'switch_plate', 'plate', 'wallmount')
                        face_bar(w, side, s - .012, s + .012, z + 1.17, .05, .016, 'switch_rocker', 'plate', 'wallmount')
                        tally('switches')
            elif code.startswith('W') and sill >= .3:
                bar(a + u * max(0, lo - .04), a + u * min(L, hi + .04), z + sill - .025, .025, w['t'] + .07,
                    'window_sill_board', f'FLOOR_{f}', 'stone', 'window')
                tally('window_sills')

    # 4) Duplex outlets at 30 cm, roughly every 2.8 m of dry wall.
    for w in WALLS:
        a, u, n, L = wall_frames(w)
        for side in (1, -1):
            for s0, s1, r in runs(w, side, solid(w, L), lambda r: dry(r) and r['key'] not in ('STAIR', 'LOBBY')):
                s = s0 + .45
                while s < s1 - .35:
                    face_bar(w, side, s - .035, s + .035, w['z'] + r['raise_by'] + .24, .12, .01, 'outlet_plate', 'plate', 'wallmount')
                    tally('outlets'); s += 2.8

    # 5) Split air-conditioner indoor units on the longest clear wall of each room.
    ac_rooms = {1: {'LIVING_W', 'LIVING_E'}, 2: {'BED1', 'BED2', 'BED3', 'LIVING'}, 3: {'BED1', 'BED2', 'BED3', 'LIVING'}}
    for f, keys in ac_rooms.items():
        for key in keys:
            best = None
            for w in (w for w in WALLS if w['floor'] == f):
                a, u, n, L = wall_frames(w)
                for side in (1, -1):
                    for s0, s1, r in runs(w, side, solid(w, L), lambda r: r['key'] == key):
                        if best is None or s1 - s0 > best[3] - best[2]:
                            best = (w, side, s0, s1)
            if best and best[3] - best[2] > 1.0:
                w, side, s0, s1 = best; s = (s0 + s1) / 2; zb = top(f) - .15 - .29
                face_bar(w, side, s - .40, s + .40, zb, .29, .22, 'ac_indoor_body', 'plate', 'wallmount', .002)
                face_bar(w, side, s - .36, s + .36, zb + .025, .035, .012, 'ac_indoor_louvre', 'metal', 'wallmount', .222)
                face_bar(w, side, s - .38, s + .38, zb + .22, .012, .01, 'ac_indoor_intake', 'metal', 'wallmount', .222)
                tally('ac_indoor')

    # Outdoor condensers on the 4F terrace and roof, on concrete pads.
    for x, y, z, facing in [(.10, 7.0, 11.7, 'x'), (.10, 8.05, 11.7, 'x'), (.10, 9.1, 11.7, 'x'), (6.9, 5.3, 14.8, 'y'), (7.9, 5.3, 14.8, 'y')]:
        w, d = (.30, .80) if facing == 'x' else (.80, .30)
        box(x, y, z + .012, w + .06, d + .06, .10, 'ac_pad', 'FLOOR_4' if z < 14 else 'ROOF', 'slab', 'fixture')
        par = 'FLOOR_4' if z < 14 else 'ROOF'
        box(x + .03, y + .03, z + .112, w, d, .55, 'ac_outdoor_body', par, 'plate', 'fixture')
        cx, cy = (x + .03 + w + .004, y + .03 + d / 2) if facing == 'x' else (x + .03 + w / 2, y + .03 - .004)
        a = np.array([cx, cy, z + .112 + .30]); dirv = np.array([1, 0, 0]) if facing == 'x' else np.array([0, -1, 0])
        rod(a - dirv * .004, a + dirv * .006, .19, 'ac_fan_grille', par, 'metal', 'fixture')
        tally('ac_outdoor')

    # 6) Mirrors above the drawn wash basins (ray to the nearest wall face).
    def face_hit(f, p, d):
        best = None
        for w in (w for w in WALLS if w['floor'] == f):
            a, u, n, L = wall_frames(w)
            for side in (1, -1):
                q = a + n * side * w['t'] / 2
                den = d[0] * u[1] - d[1] * u[0]
                if abs(den) < 1e-9:
                    continue
                diff = q - p
                s = (diff[0] * u[1] - diff[1] * u[0]) / den
                r = (diff[0] * d[1] - diff[1] * d[0]) / den
                if s > 0 and -.01 <= r <= L + .01 and (best is None or s < best):
                    best = s
        return best
    for f, x, y, up, ang in [(1, 9.12, 6.16, 0, 0), (2, 6.32, 3.65, .1, 90), (2, 1.84, 7.88, 0, 180), (3, 6.30, 3.45, .1, 90)]:
        t = math.radians(ang); d = np.array([math.sin(t), -math.cos(t)]); p = np.array([x, y])
        dist = face_hit(f, p, d)
        if dist is None or dist > .7:
            continue
        hit = p + d * (dist - .006); side = np.array([-d[1], d[0]])
        bar(hit - side * .26, hit + side * .26, BASE[f] + up + 1.05, .72, .01, 'basin_mirror', f'FLOOR_{f}', 'mirror', 'wallmount')
        tally('mirrors')

    # 7) Entrance: wall lamps beside D2a, meter box, mailbox, porch downlights.
    for w in WALLS:
        if w['floor'] == 1 and w['name'] == 'front_entry':
            a, u, n, L = wall_frames(w)
            lo, hi = next((lo, hi) for lo, hi, s, oh, code in w['cuts'] if code == 'D2a')
            for s in (lo - .30, hi + .30):
                face_bar(w, -1, s - .06, s + .06, w['z'] + 2.25, .22, .10, 'entry_wall_lamp', 'metal', 'fixture')
                face_bar(w, -1, s - .045, s + .045, w['z'] + 2.28, .16, .012, 'entry_wall_lamp_glow', 'lamp', 'fixture', .10)
                tally('entry_lamps')
            face_bar(w, -1, L - 1.25, L - .80, w['z'] + .85, .60, .18, 'electric_meter_box', 'pvc', 'fixture')
            face_bar(w, -1, lo - 1.10, lo - .75, w['z'] + .75, .40, .12, 'mailbox', 'metal', 'fixture')
            tally('meter_box'); tally('mailbox')
    for x, y in [(8.3, 13.3), (10.3, 13.3), (9.3, 14.4)]:
        extr(Point(x, y).buffer(.07, quad_segs=6), BASE[2] - .20 - .006, .006, 'porch_downlight', 'FLOOR_2', 'lamp', 'fixture')
        tally('porch_downlights')

    # 8) Roof: stainless water tank on steel stand, overrun ladder (NE elevation), drains.
    tx, ty, z = 11.35, 4.75, 14.812
    for dx in (-.42, .42):
        for dy in (-.42, .42):
            rod([tx + dx, ty + dy, z], [tx + dx, ty + dy, z + .5], .025, 'water_tank_stand', 'ROOF', 'metal', 'fixture')
    box(tx - .5, ty - .5, z + .46, 1.0, 1.0, .05, 'water_tank_frame', 'ROOF', 'metal', 'fixture')
    rod([tx, ty, z + .51], [tx, ty, z + 1.76], .55, 'water_tank_1ton', 'ROOF', 'stainless', 'fixture')
    for zz in (z + .85, z + 1.2, z + 1.55):
        rod([tx, ty, zz], [tx, ty, zz + .025], .557, 'water_tank_band', 'ROOF', 'stainless', 'fixture')
    rod([tx, ty, z + 1.76], [tx, ty, z + 1.84], .42, 'water_tank_cap', 'ROOF', 'stainless', 'fixture')
    rod([tx, ty, z + 1.84], [tx, ty, z + 1.93], .16, 'water_tank_lid', 'ROOF', 'stainless', 'fixture')
    rod([tx - .55, ty, z + .6], [10.55, ty, z + .6], .025, 'water_supply_pipe', 'ROOF', 'pvc', 'fixture')
    rod([10.55, ty, z + .6], [10.55, ty, z], .025, 'water_supply_pipe', 'ROOF', 'pvc', 'fixture')
    tally('water_tank')
    lx = 10.33 + .16
    for yy in (2.38, 2.82):
        rod([lx, yy, z], [lx, yy, 16.1], .02, 'roof_ladder_rail', 'ROOF', 'metal', 'railing')
        for zz in (15.0, 15.9):
            rod([10.33, yy, zz], [lx, yy, zz], .012, 'roof_ladder_bracket', 'ROOF', 'metal', 'railing')
    for zz in np.arange(z + .30, 16.0, .30):
        rod([lx, 2.38, zz], [lx, 2.82, zz], .014, 'roof_ladder_rung', 'ROOF', 'metal', 'railing')
    tally('roof_ladder')
    for x, y in [(6.85, .20), (12.25, .20), (6.85, 5.72), (12.25, 5.72)]:
        box(x - .1, y - .1, z, .2, .2, .012, 'roof_drain', 'ROOF', 'metal', 'fixture'); tally('roof_drains')
    # Rain-water downspouts (PVC 10 cm) with wall clips.
    for (x, y), z0, z1, wall_x in [((-.18, .62), .02, 12.8, .0), ((12.72, .18), 8.41, 14.95, 12.55)]:
        rod([x, y, z0], [x, y, z1], .05, 'downspout', 'FLOOR_4', 'pvc', 'fixture')
        rod([x, y, z1], [wall_x, y, z1], .05, 'downspout_elbow', 'FLOOR_4', 'pvc', 'fixture')
        for zz in np.arange(z0 + 1.2, z1, 1.5):
            box(min(x, wall_x) - .02, y - .02, zz, abs(x - wall_x) + .04, .04, .03, 'downspout_clip', 'FLOOR_4', 'metal', 'fixture')
        tally('downspouts')
    return count
