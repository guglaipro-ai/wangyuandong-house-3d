"""Four independent interior schemes. Each class owns its finishes, lighting,
window dressing, furniture forms and room layouts; nothing is a recolour.
Room uses follow the user's 2026-09-10 corrections (1F gallery/classroom + lobby,
2F living-dining + kitchen, 3F worship hall, 4F storage + terrace).
Furniture modules use Taiwan market sizes (5尺 152x188, 6尺 182x188, 3.5尺 105x188
mattresses; dining 75 cm; seat 42-45 cm; worktop 85 cm).
"""
import math
import numpy as np
import trimesh as tm
from shapely.geometry import Polygon, Point, box as rect
from style_kit import Kit, faces, windows, ceiling_z, RP, BASE

MATTRESS = {'5': (1.52, 1.88), '6': (1.82, 1.88), '3.5': (1.05, 1.88)}


def _cz(k):
    return ceiling_z(k.floor)


# =====================================================================
# 1. 波西米亞：旅人收藏的溫暖手作
# =====================================================================
class Bohemian(Kit):
    key = 'bohemian'; label = '波西米亞'
    brief = dict(concept='旅人收藏的溫暖手作：陶磚地、石灰漆牆、木梁與藤編，低座與層疊織品',
                 floor='手工陶磚 20×20 cm（8 mm 灰縫）', walls='暖杏色石灰漆', ceiling='客廳外露木梁＋藤編天花板',
                 lighting='藤編吊燈、串燈、摩洛哥風燈', windows='竹捲簾（窗）＋番紅花色紗簾（落地門）',
                 signature='低座沙發、孔雀藤椅、吊掛蛋椅、黃銅托盤桌、流蘇編織掛毯、大量植栽、帳幔床')
    FLOOR = 'terracotta'
    MATS = {'terracotta': ('#ffffff', .8, 0), 'paint': ('#ecd7bd', .95, 0), 'ceilpaint': ('#f3e7d6', .95, 0),
            'wood': ('#8b5e3c', .75, 0), 'darkwood': ('#5a3a24', .7, 0), 'rattan': ('#e0b57a', .8, 0),
            'fabric': ('#b85134', .95, 0), 'accent': ('#2a7f7c', .95, 0), 'ochre': ('#d39a3b', .95, 0),
            'rose': ('#c46f73', .95, 0), 'cream': ('#efe3cb', .95, 0), 'rug': ('#b8683b', .95, 0), 'jute': ('#c7a574', .95, 0),
            'brass': ('#b08a3e', .35, .8), 'clay': ('#b0714f', .9, 0), 'zellige': ('#ffffff', .25, 0), 'macrame': ('#efe6d2', .95, 0),
            'sheer': ('#f2d9a8', .9, 0, None, 120), 'copper': ('#b86f45', .3, .85), 'stainless': ('#c9ccce', .3, .85), 'wood2': ('#a8784e', .7, 0)}

    # ---- signature pieces (local frame: back at y=0, facing +y) ----
    def sofa(self, w=2.4, d=.92):
        self.item('低座沙發（木座＋坐墊）', -w / 2, 0, w, d)
        for x in (-w / 2 + .08, w / 2 - .08):
            for y in (.08, d - .08):
                self.cyl(x, y, 0, .03, .07, 'darkwood', sec=10)
        self.box(-w / 2, 0, .07, w, d, .12, 'darkwood', r=.03)
        n = 3
        for i in range(n):
            self.soft(-w / 2 + .14 + i * (w - .28) / n, .2, .19, (w - .28) / n - .01, d - .22, .17, 'fabric', rounding=.35)
            self.osoft(-w / 2 + .14 + (i + .5) * (w - .28) / n, .14, .3, (w - .28) / n - .02, .2, .46, 0, 'fabric', rounding=.55, tilt=-.18)
        for x in (-w / 2, w / 2 - .17):
            self.soft(x, .02, .19, .17, d - .06, .34, 'fabric', rounding=.75)
        for i, c in enumerate(['accent', 'ochre', 'rose', 'cream', 'accent', 'ochre']):
            self.osoft(-w / 2 + .32 + i * (w - .64) / 5, .3, .42, .36, .13, .36, (i % 3 - 1) * .12, c, rounding=.6, tilt=-.35)
        self.drape(w / 2 - .62, .06, .36, .5, d - .1, .05, 'ochre', folds=4)

    def peacock(self):
        self.item('孔雀藤椅', -.4, 0, .8, .75)
        self.lathe(0, .42, 0, [(0, 0), (.26, 0), (.14, .2), (.27, .38), (0, .38)], 'rattan', 'furniture', 20)
        self.lathe(0, .42, .38, [(0, 0), (.36, 0), (.37, .07), (0, .07)], 'rattan', 'furniture', 24)
        self.soft(-.3, .14, .44, .6, .56, .09, 'cream', rounding=.9)
        for i in range(17):
            a = math.radians(8 + i * 10.25); end = [math.cos(a) * .58, .05, .5 + math.sin(a) * .95]
            self.rod([0, .28, .46], end, .011, 'rattan')
        for i in range(24):
            a0 = math.radians(8 + i * 6.9); a1 = math.radians(8 + (i + 1) * 6.9)
            self.rod([math.cos(a0) * .58, .05, .5 + math.sin(a0) * .95], [math.cos(a1) * .58, .05, .5 + math.sin(a1) * .95], .016, 'rattan')

    def egg(self, hang_top):
        self.item('吊掛藤編蛋椅', -.5, -.45, 1.0, .9)
        m = tm.creation.icosphere(subdivisions=3, radius=.48); m.apply_scale([1, .92, 1.3])
        keep = m.triangles_center[:, 1] < .12 - .35 * np.clip(m.triangles_center[:, 2], -1, 1)
        m.update_faces(keep); m.remove_unreferenced_vertices(); m.apply_translation([0, 0, self.Z(.95)]); self.add(m, 'rattan')
        self.soft(-.33, -.3, .55, .66, .58, .14, 'accent', rounding=.8)
        self.osoft(0, -.22, .78, .5, .14, .38, 0, 'ochre', rounding=.6, tilt=-.3)
        self.rod([0, 0, 1.55], [0, 0, hang_top], .012, 'brass', 'ceiling')

    def pouf(self, x, y, c='fabric'):
        self.soft(x - .25, y - .25, 0, .5, .5, .36, c, rounding=.9); self.item('皮革坐墩', x - .25, y - .25, .5, .5, False)

    def tray_table(self, x, y, r=.45):
        self.item('黃銅托盤桌', x - r, y - r, 2 * r, 2 * r)
        for a in (math.pi / 4, 3 * math.pi / 4):
            self.rod([x + math.cos(a) * .3, y + math.sin(a) * .3, 0], [x - math.cos(a) * .3, y - math.sin(a) * .3, .36], .014, 'darkwood')
            self.rod([x - math.cos(a) * .3, y - math.sin(a) * .3, 0], [x + math.cos(a) * .3, y + math.sin(a) * .3, .36], .014, 'darkwood')
        self.lathe(x, y, .36, [(0, 0), (r, 0), (r + .01, .045), (r - .02, .045), (0, .012)], 'brass', 'furniture', 32)

    def kilim(self, x, y, w, d):
        self.item('幾何紋基里姆地毯', x, y, w, d, False)
        self.box(x, y, 0, w, d, .008, 'rug', 'decor')
        for m in (0, 1):
            self.box(x + .08, y + .08 + m * (d - .24), .008, w - .16, .08, .003, 'cream', 'decor')
        nx = max(2, int(w / .45)); ny = max(2, int(d / .5))
        for i in range(nx):
            for j in range(ny):
                cx = x + (i + .5) * w / nx; cy = y + .2 + (j + .5) * (d - .4) / ny
                self.obox(cx, cy, .008, .22, .22, .003, math.pi / 4, ['accent', 'ochre', 'cream'][(i + j) % 3], 'decor')
                self.obox(cx, cy, .011, .1, .1, .003, math.pi / 4, 'fabric', 'decor')

    def jute(self, x, y, r):
        self.cyl(x, y, 0, r, .007, 'jute', 'decor', 48); self.cyl(x, y, .007, r * .8, .002, 'cream', 'decor', 48)
        self.item('圓形黃麻地毯', x - r, y - r, 2 * r, 2 * r, False)

    def pendant(self, x, y, drop=1.0, r=.26):
        cz = _cz(self); z = cz - drop
        self.rod([x, y, z + .28], [x, y, cz], .006, 'black', 'ceiling')
        self.lathe(x, y, z, [(r, 0), (r * .98, .1), (r * .8, .2), (r * .45, .27), (.03, .3), (0, .3)], 'rattan', 'ceiling', 28)
        self.sphere(x, y, z + .12, .05, 'bulb', 'ceiling')

    def macrame(self, F, s, zr=1.4, w=.8, h=1.0):
        self.face_box(F, s - w / 2 - .06, s + w / 2 + .06, zr + h, .03, .03, 'wood', off=.02)
        n = 22
        for i in range(n):
            t = i / (n - 1); a = s - w / 2 + w * t; ln = h * (.55 + .45 * (1 - abs(t - .5) * 2))
            self.face_box(F, a - .006, a + .006, zr + h - ln, ln, .01, 'macrame', off=.03)
        for j in range(3):
            self.face_box(F, s - w / 2 + .1 + j * .05, s + w / 2 - .1 - j * .05, zr + h - .25 - j * .12, .025, .016, 'macrame', off=.03)

    def tapestry(self, F, s, zr, w, h):
        self.face_box(F, s - w / 2 - .05, s + w / 2 + .05, zr + h, .025, .025, 'wood', off=.02)
        cols = ['fabric', 'ochre', 'accent', 'cream', 'rose']
        for i in range(8):
            self.face_box(F, s - w / 2, s + w / 2, zr + h - (i + 1) * h / 8, h / 8, .008, cols[i % 5], off=.02)
        for i in range(12):
            a = s - w / 2 + (i + .5) * w / 12; self.face_box(F, a - .005, a + .005, zr - .14, .14, .006, 'macrame', off=.022)

    def hanging_plant(self, x, y, drop=.8):
        cz = _cz(self); z = cz - drop
        for a in (0, 2.1, 4.2):
            self.rod([x + math.cos(a) * .12, y + math.sin(a) * .12, z + .12], [x, y, cz], .004, 'macrame', 'ceiling')
        self.lathe(x, y, z, [(0, 0), (.1, 0), (.13, .14), (0, .14)], 'clay', 'ceiling', 16)
        for i in range(7):
            a = i * .9; L = .3 + (i % 3) * .2
            for k in range(4):
                self.sphere(x + math.cos(a) * (.12 + k * .02), y + math.sin(a) * (.12 + k * .02), z + .1 - k * L / 4, .035, 'leaf', 'ceiling', 1, (1, .6, .3))

    def bed(self, W, L=1.88):
        Wf = W + .1; Lf = L + .1
        self.item('帳幔床（低平台）', -Wf / 2, 0, Wf, Lf)
        self.box(-Wf / 2, 0, 0, Wf, Lf, .22, 'darkwood', r=.02)
        self.box(-Wf / 2 + .04, 0, .22, Wf - .08, .06, .78, 'darkwood')
        for i in range(7):
            self.box(-Wf / 2 + .14 + i * (Wf - .28) / 6 - .03, .06, .34, .06, .012, .55, 'wood2', 'decor')
        self.soft(-W / 2, .07, .22, W, L - .02, .2, 'cream', rounding=.2)
        self.drape(-W / 2 - .02, .55, .38, W + .04, L - .5, .08, 'accent', folds=5)
        self.drape(-W / 2 - .02, L - .45, .44, W + .04, .4, .05, 'rug', folds=3)
        for i, c in enumerate(['cream', 'cream', 'ochre', 'fabric', 'rose']):
            xx = -W / 2 + .15 + i * (W - .45) / 4
            self.osoft(xx + .15, .22 if i < 2 else .32, .44, .42 if i < 2 else .32, .15, .3, 0, c, rounding=.6, tilt=-.3)
        for x in (-Wf / 2 + .03, Wf / 2 - .03):
            for y in (.03, Lf - .03):
                self.rod([x, y, 0], [x, y, 2.1], .02, 'darkwood')
        for a, b in (((-Wf / 2, .03), (Wf / 2, .03)), ((-Wf / 2, Lf - .03), (Wf / 2, Lf - .03)), ((-Wf / 2 + .03, 0), (-Wf / 2 + .03, Lf)), ((Wf / 2 - .03, 0), (Wf / 2 - .03, Lf))):
            self.rod([a[0], a[1], 2.1], [b[0], b[1], 2.1], .015, 'darkwood')
        for x in (-Wf / 2 + .02, Wf / 2 - .1):
            for y in (.06, Lf - .3):
                self.box(x, y, .25, .015, .24, 1.84, 'sheer', 'furniture')
        for side in (-1, 1):
            x = side * (Wf / 2 + .28)
            self.lathe(x, .3, 0, [(0, 0), (.19, 0), (.21, .25), (.19, .5), (0, .5)], 'rattan', 'furniture', 18)
            self.lathe(x, .3, .5, [(0, 0), (.07, 0), (.08, .14), (.03, .2), (0, .2)], 'brass', 'decor', 12)
            self.item('藤編床邊几', x - .21, .09, .42, .42, False)

    def finishes(self):
        for f, key in ((2, 'LIVING'), (3, 'LIVING')):
            self.at(f, key); p = RP[(f, key)]
            self.beams(p.intersection(rect(6.6, 6.0, 14.3, 12)), 'y', 4, .14, .2, 'wood2')
            self.poly(p.intersection(rect(7.9, 6.3, 11.2, 9.6)).buffer(-.02), _cz(self) - .03, .018, 'rattan', 'ceiling')
        for f, rooms in {1: ['LIVING_W', 'LIVING_E'], 2: ['LIVING', 'BED1', 'BED2', 'BED3'], 3: ['LIVING', 'BED1', 'BED2', 'BED3']}.items():
            for k in rooms:
                self.at(f, k); self.dress_windows(k, 'blind', 'rattan', 'wood', codes=('W',)); self.dress_windows(k, 'sheer', 'sheer', 'brass', codes=('DW',))

    def gallery1(self):
        self.at(1, '展覽空間／教室（西側）：手作工作坊')
        self.kilim(1.0, 8.2, 3.2, 2.4); self.kilim(1.0, 11.2, 3.2, 2.4)
        for cx, cy in ((2.6, 9.4), (2.6, 12.4)):
            self.lathe(cx, cy, 0, [(0, 0), (.22, 0), (.12, .38), (.62, .38), (.62, .44), (0, .44)], 'wood', 'furniture', 32)
            self.item('低圓工作桌', cx - .62, cy - .62, 1.24, 1.24)
            for i in range(6):
                a = i * math.pi / 3 + .3
                self.soft(cx + math.cos(a) * 1.0 - .27, cy + math.sin(a) * 1.0 - .27, 0, .54, .54, .12, ['fabric', 'accent', 'ochre'][i % 3], rounding=.6)
            self.pendant(cx, cy, 1.9, .34)
        self.lathe(4.9, 10.9, 0, [(0, 0), (.25, 0), (.25, .5), (.2, .55), (0, .55)], 'darkwood', 'furniture', 20)
        self.cyl(4.9, 10.9, .55, .18, .04, 'clay', 'decor'); self.lathe(4.9, 10.9, .59, [(0, 0), (.08, 0), (.11, .12), (.05, .2), (0, .2)], 'clay')
        self.item('拉坯機', 4.65, 10.65, .5, .5)
        for y in (3.3, 4.8, 6.3):
            self.lathe(.55, y, 0, [(0, 0), (.24, 0), (.22, .88), (.26, .9), (0, .9)], 'rattan', 'furniture', 18)
            self.lathe(.55, y, .9, [(0, 0), (.1, 0), (.14, .16), (.06, .28), (.07, .32), (0, .32)], ['clay', 'accent', 'ochre'][int(y) % 3])
            self.item('藤編展示台＋手作陶器', .31, y - .24, .48, .48, False)
        left = [F for F in faces(1, 'LIVING_W', 'low') if abs(F.u[1]) > .9 and F.wall['name'] == 'left']
        for F in left:
            for s, w in ((3.9, 1.1), (6.0, .9)):
                if F.s0 + w / 2 < s < F.s1 - w / 2:
                    self.tapestry(F, s, 1.1, w, 1.4)
        part = [F for F in faces(1, 'LIVING_W', 'full') if F.wall['name'] == 'living_partition']
        for F in part:
            for z in (1.1, 1.5, 1.9):
                self.face_box(F, 1.2, 4.0, z, .03, .24, 'wood')
                for k in range(6):
                    q = F.p(1.35 + k * .45, .12); self.lathe(q[0], q[1], z + .03, [(0, 0), (.06, 0), (.08, .1), (.04, .17), (0, .17)], ['clay', 'accent', 'cream', 'ochre'][k % 4])
            self.item('壁掛陶器層板', 6.2, 7.1, .24, 2.8, False)
        back = [F for F in faces(1, 'LIVING_W', 'full') if F.wall['name'] == 'back_left']
        for F in back:
            self.macrame(F, 2.2, 1.2, 1.0, 1.2)
        self.fiddle(5.7, 15.8, 1.7, seed=4); self.fiddle(.6, 15.8, 1.5, seed=5); self.snake(.55, .7)
        self.box(5.9, 4.6, 0, .45, 1.8, .38, 'wood', r=.03); self.item('靠牆長凳', 5.9, 4.6, .45, 1.8)
        for i in range(3):
            self.soft(5.92, 4.65 + i * .58, .38, .42, .55, .1, ['accent', 'fabric', 'ochre'][i], rounding=.6)

    def lobby1(self):
        self.at(1, 'Lobby 大廳（東側）')
        self.box(8.3, 10.95, 0, 2.4, .6, 1.02, 'wood', r=.03)
        for i in range(8):
            self.box(8.36 + i * .29, 10.93, .08, .26, .02, .86, 'rattan', 'furniture')
        self.box(8.25, 10.9, 1.02, 2.5, .7, .04, 'darkwood'); self.item('藤編接待櫃台', 8.25, 10.9, 2.5, .7)
        self.box(6.7, 8.4, 0, .5, 1.9, .42, 'rattan', r=.05); self.item('藤編長椅', 6.7, 8.4, .5, 1.9)
        for i in range(3):
            self.soft(6.72, 8.45 + i * .62, .42, .46, .58, .1, ['fabric', 'accent', 'ochre'][i], rounding=.6)
        self.jute(8.2, 9.3, .8); self.fiddle(11.9, 9.5, 1.6, seed=7)
        self.pendant(9.5, 11.25, 1.6, .3); self.pendant(7.0, 9.35, 1.8, .22)

    def living2(self):
        self.at(2, '客廳兼餐廳')
        self.kilim(7.9, 6.9, 3.2, 2.7); self.jute(10.8, 9.2, .8)
        with self.xf(9.3, 6.1, '+y'):
            self.sofa()
        with self.xf(11.8, 7.8, '-x'):
            self.peacock()
        self.tray_table(9.3, 8.1); self.pouf(8.3, 9.3, 'rose'); self.pouf(9.3, 9.5, 'accent')
        with self.xf(7.45, 8.9, '+x'):
            self.egg(_cz(self))
        self.fiddle(7.05, 6.45, 1.7, seed=2); self.snake(10.85, 6.35); self.hanging_plant(11.6, 6.5)
        for F in faces(2, 'LIVING', 'full'):
            if F.wall['name'] == 'stair_front' and F.s0 < 2.65 < F.s1:
                self.macrame(F, 2.65, 1.45, .9, 1.0)
        # dining: rustic table + mismatched chairs
        for x in (12.14, 13.62):
            for y in (8.18, 8.87):
                self.lathe(x + .02, y + .02, 0, [(0, 0), (.035, 0), (.045, .2), (.03, .36), (.045, .55), (.035, .72), (0, .72)], 'wood', 'furniture', 12)
        self.box(12.12, 8.16, .6, 1.56, .75, .12, 'wood')
        self.box(12.05, 8.1, .72, 1.7, .95, .04, 'wood2', r=.03); self.item('手作實木餐桌（車旋腳）', 12.05, 8.1, 1.7, .95)
        for x, y, f in ((12.5, 9.2, '-y'), (13.3, 9.2, '-y'), (12.5, 7.65, '+y'), (13.3, 7.65, '+y')):
            with self.xf(x, y if f == '+y' else y + .5, f):
                self.item('藤編餐椅', -.25, 0, .5, .5)
                self.lathe(0, .25, .0, [(0, 0), (.2, 0), (.18, .44), (0, .44)], 'rattan', 'furniture', 16)
                self.soft(-.21, .06, .44, .42, .4, .06, 'cream', rounding=.8)
                self.box(-.22, .0, .44, .44, .05, .42, 'rattan', r=.02)
        for x in (12.5, 13.3):
            self.pendant(x, 8.6, 1.45, .2)
        self.pendant(9.3, 7.9, 1.1, .34)

    def kitchen2(self):
        self.kitchen('L', 'accent', 'wood2', 'zellige', 'brass', 'cream', 'copper', 'open', cab_upper='wood2')
        for i in range(6):
            x = 13.25 + i * .16; self.lathe(x, .22, .85 + .68, [(0, 0), (.05, 0), (.06, .12), (.03, .16), (0, .16)], ['clay', 'accent', 'cream'][i % 3], 'wallmount', 12)
        self.rod([12.3, .55, 2.2], [12.3 + .9, .55, 2.2], .012, 'copper', 'wallmount')
        for i in range(4):
            x = 12.4 + i * .22; self.rod([x, .55, 2.2], [x, .55, 2.05], .004, 'copper', 'wallmount')
            self.lathe(x, .55, 1.9, [(0, 0), (.08, 0), (.09, .1), (0, .1)], 'copper', 'wallmount', 12)
        self.pendant(12.9, 2.2, 1.0, .24); self.hanging_plant(12.3, .9, .9)

    def bedrooms(self):
        for f, room, x, y, facing, size in ((2, 'BED1', 1.5, 5.82, '-y', '5'), (2, 'BED2', 1.72, 8.3, '+y', '5'), (2, 'BED3', 2.16, 12.28, '+y', '6'),
                                            (3, 'BED1', 1.5, 3.9, '-y', '5'), (3, 'BED2', 1.72, 8.05, '+y', '5')):
            self.at(f, {'BED1': '臥室一', 'BED2': '臥室二', 'BED3': '臥室三'}[room])
            n0 = len(self.items)
            with self.xf(x, y, facing):
                self.bed(*MATTRESS[size])
            self.items[n0].update(category='bed', head_side={'-y': '+y', '+y': '-y', '+x': '-x', '-x': '+x'}[facing], mattress_cm=[round(v * 100) for v in MATTRESS[size]])
            p = RP[(f, room)]; c = p.centroid
            if room == 'BED1':
                self.pouf(3.0, 1.2, 'accent')
            else:
                self.kilim(c.x - .9, c.y - .6, 1.8, 1.2); self.snake(p.bounds[2] - .35, p.bounds[3] - .35)
            for F in faces(f, room, 'low'):
                if F.length > 2.0 and F.wall['name'] in ('bed2_front', 'bed1_front', 'bed2_back', 'bed3_front') and room != 'BED3':
                    self.tapestry(F, F.mid, 1.1, .8, 1.0); break

    def living3(self):
        self.at(3, '起居室：閱讀與音樂角')
        self.box(7.0, 6.05, 0, 2.2, .95, .22, 'darkwood', r=.03); self.soft(7.02, 6.08, .22, 2.16, .9, .16, 'fabric', rounding=.3)
        for i, c in enumerate(['accent', 'ochre', 'rose', 'cream', 'accent']):
            self.osoft(7.25 + i * .43, 6.2, .5, .4, .14, .4, 0, c, rounding=.6, tilt=-.3)
        self.item('地舖臥榻', 7.0, 6.05, 2.2, .95)
        self.jute(8.3, 7.7, 1.05); self.tray_table(8.3, 7.7, .38); self.pouf(9.4, 7.5, 'ochre')
        self.box(10.1, 6.05, 0, 1.3, .32, .9, 'wood', r=.02); self.item('矮書櫃', 10.1, 6.05, 1.3, .32)
        for i in range(10):
            self.box(10.15 + i * .06, 6.08, .05, .045, .22, .28 + (i % 3) * .04, ['fabric', 'accent', 'ochre', 'cream'][i % 4], 'decor')
        self.pot(11.1, 6.2, .1, .2); self.hanging_plant(11.9, 6.4); self.pendant(8.3, 7.7, 1.2, .3)
        self.at(3, '起居室走廊')
        self.box(.15, 4.5, 0, .45, 2.0, .4, 'wood', r=.03); self.item('走廊長凳', .15, 4.5, .45, 2.0)
        for i in range(3):
            self.soft(.17, 4.55 + i * .65, .4, .41, .6, .1, ['rose', 'accent', 'ochre'][i], rounding=.6)

    def worship3(self):
        self.at(3, '佛廳／祭祀空間')
        self.box(.15, 12.35, 0, .7, 2.2, .88, 'darkwood', r=.02)
        for i in range(4):
            self.box(.85, 12.42 + i * .54, .1, .02, .5, .66, 'wood2')
        self.box(.18, 12.75, .88, .5, 1.4, .6, 'darkwood', 'furniture'); self.item('神桌＋佛龕（無造像）', .15, 12.35, .7, 2.2)
        self.box(1.05, 12.95, 0, .55, 1.0, .62, 'darkwood'); self.item('供桌', 1.05, 12.95, .55, 1.0)
        self.lathe(1.32, 13.45, .62, [(0, 0), (.1, 0), (.12, .08), (.09, .1), (0, .1)], 'brass'); self.item('黃銅香爐', 1.2, 13.33, .24, .24, False)
        for y in (13.05, 13.85):
            self.lathe(1.32, y, .62, [(0, 0), (.04, 0), (.02, .05), (.02, .25), (.03, .27), (0, .27)], 'brass')
        for y in (13.0, 13.75):
            self.box(2.0, y, 0, .55, .5, .08, 'rattan', r=.08); self.item('藤編拜墊', 2.0, y, .55, .5, False)

    def terrace4(self):
        self.at(4, '露台')
        self.box(1.2, 7.2, 0, 3.2, 2.8, .01, 'jute', 'decor'); self.item('戶外編織地毯', 1.2, 7.2, 3.2, 2.8, False)
        self.lathe(2.8, 8.6, 0, [(0, 0), (.45, 0), (.45, .32), (.5, .36), (0, .36)], 'wood', 'furniture', 28); self.item('低圓桌', 2.3, 8.1, 1.0, 1.0)
        for i in range(6):
            a = i * math.pi / 3
            self.soft(2.8 + math.cos(a) * 1.05 - .3, 8.6 + math.sin(a) * 1.05 - .3, 0, .6, .6, .16, ['fabric', 'accent', 'ochre'][i % 3], rounding=.7)
        poles = [(1.0, 7.0), (4.7, 7.0), (4.7, 10.3), (1.0, 10.3)]
        for x, y in poles:
            self.cyl(x, y, 0, .12, .25, 'clay'); self.rod([x, y, .2], [x, y, 2.45], .025, 'wood')
        for (a, b) in zip(poles, poles[1:] + poles[:1]):
            for i in range(11):
                t = i / 10; sag = .35 * math.sin(math.pi * t)
                p = [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, 2.4 - sag]
                self.sphere(p[0], p[1], p[2], .03, 'bulb', 'decor', 1)
            for i in range(10):
                t0, t1 = i / 10, (i + 1) / 10
                self.rod([a[0] + (b[0] - a[0]) * t0, a[1] + (b[1] - a[1]) * t0, 2.4 - .35 * math.sin(math.pi * t0)], [a[0] + (b[0] - a[0]) * t1, a[1] + (b[1] - a[1]) * t1, 2.4 - .35 * math.sin(math.pi * t1)], .004, 'black', 'decor')
        self.item('串燈木柱', 1.0, 7.0, 3.7, 3.3, False)
        for i, (x, y) in enumerate(((5.6, 7.2), (5.6, 8.4), (5.6, 9.6), (1.2, 11.2), (3.0, 11.2), (4.6, 11.2))):
            self.fiddle(x, y, 1.3 + .1 * (i % 3), seed=10 + i) if i % 2 == 0 else self.snake(x, y)
        for x, y in ((1.8, 7.3), (4.0, 10.0)):
            self.lathe(x, y, 0, [(0, 0), (.12, 0), (.12, .3), (.06, .38), (.02, .42), (0, .42)], 'brass', 'decor', 12)

    def storage4(self):
        self.at(4, '儲藏間'); self.storage_shelves('darkwood', 'wood', ['rattan', 'jute', 'clay'], box_kind='basket')

    def populate(self):
        self.finishes(); self.gallery1(); self.lobby1(); self.living2(); self.kitchen2(); self.bedrooms()
        self.living3(); self.worship3(); self.storage4(); self.terrace4()


# =====================================================================
# 2. 工業 Loft：舊廠房改造
# =====================================================================
class Industrial(Kit):
    key = 'industrial'; label = '工業 Loft'
    brief = dict(concept='舊廠房改造：清水模、外露管線與黑鐵，焦糖皮革與回收木',
                 floor='拋光混凝土（清水地坪）', walls='清水模板牆（12 cm 模板紋＋螺栓孔）', ceiling='不做天花：外露樓板、明管線、黑色螺旋風管',
                 lighting='鐵籠愛迪生燈泡吊燈、黑色軌道投射燈、搪瓷工作吊燈', windows='黑色金屬百葉',
                 signature='焦糖皮革沙發＋俱樂部椅、管件書架牆、黑鐵玻璃隔屏、紅磚展示牆、實木厚板長桌＋長凳、畫架與工作台')
    FLOOR = 'concrete'; EXPOSED = True
    MATS = {'concrete': ('#c0bcb4', .5, 0), 'paint': ('#ffffff', .9, 0), 'leather': ('#9a5a34', .55, 0), 'steel': ('#2b2e2f', .45, .6),
            'wood': ('#6f5238', .8, 0), 'darkwood': ('#3f2e21', .8, 0), 'linen': ('#c9c1ae', .95, 0), 'wool': ('#6d7270', .95, 0),
            'rug': ('#8a8c87', .95, 0), 'hide': ('#d9cfbf', .9, 0), 'brick': ('#ffffff', .9, 0), 'subway': ('#ffffff', .2, 0),
            'stainless': ('#c4c7c9', .3, .85), 'copper': ('#b0643a', .35, .85), 'rust': ('#7a4a30', .85, .2),
            'amber': ('#ffc27a', .3, 0, [1., .68, .32]), 'duct': ('#2f3233', .5, .5), 'conduit': ('#a3a8a9', .4, .7),
            'screen': ('#101214', .15, .3), 'clay': ('#8b5a3e', .9, 0), 'canvas2': ('#f3efe6', .9, 0), 'red': ('#a8332a', .6, 0),
            'cream': ('#e9e2d2', .9, 0)}

    def sofa(self, w=2.3, d=.95):
        self.item('焦糖皮革三人沙發', -w / 2, 0, w, d)
        for x in (-w / 2 + .05, w / 2 - .05):
            self.rod([x, .08, 0], [x, d - .08, 0], .015, 'steel'); self.rod([x, .08, 0], [x, .08, .14], .015, 'steel'); self.rod([x, d - .08, 0], [x, d - .08, .14], .015, 'steel')
        self.box(-w / 2, 0, .14, w, d, .2, 'leather', r=.04)
        for i in range(3):
            self.soft(-w / 2 + .16 + i * (w - .32) / 3, .24, .32, (w - .32) / 3 - .01, d - .26, .14, 'leather', rounding=.25)
            self.soft(-w / 2 + .16 + i * (w - .32) / 3, .02, .34, (w - .32) / 3 - .01, .24, .45, 'leather', rounding=.28)
        for x in (-w / 2, w / 2 - .16):
            self.box(x, 0, .14, .16, d, .5, 'leather', r=.05)
        self.drape(-w / 2 + .2, .3, .47, .6, d - .35, .04, 'wool', folds=3)

    def club(self):
        self.item('皮革俱樂部椅', -.43, 0, .86, .86)
        self.soft(-.43, 0, .08, .86, .86, .3, 'leather', rounding=.3)
        self.soft(-.43, 0, .3, .86, .24, .5, 'leather', rounding=.35)
        for x in (-.43, .27):
            self.soft(x, .05, .3, .16, .78, .32, 'leather', rounding=.5)
        self.soft(-.28, .22, .38, .56, .58, .1, 'leather', rounding=.4)
        for x in (-.35, .35):
            for y in (.08, .78):
                self.cyl(x, y, 0, .025, .08, 'steel', sec=8)

    def cage(self, x, y, drop=1.0):
        cz = _cz(self); z = cz - drop
        self.rod([x, y, z + .3], [x, y, cz], .005, 'black', 'ceiling'); self.cyl(x, y, z + .26, .04, .06, 'steel', 'ceiling', 12)
        self.sphere(x, y, z + .14, .06, 'amber', 'ceiling', 2, (1, 1, 1.3))
        for i in range(6):
            a = i * math.pi / 3; self.rod([x + math.cos(a) * .1, y + math.sin(a) * .1, z], [x + math.cos(a) * .1, y + math.sin(a) * .1, z + .26], .004, 'steel', 'ceiling')
        for zz in (z, z + .13, z + .26):
            for i in range(6):
                a0, a1 = i * math.pi / 3, (i + 1) * math.pi / 3
                self.rod([x + math.cos(a0) * .1, y + math.sin(a0) * .1, zz], [x + math.cos(a1) * .1, y + math.sin(a1) * .1, zz], .004, 'steel', 'ceiling')

    def enamel(self, x, y, drop=1.2):
        cz = _cz(self); z = cz - drop
        self.rod([x, y, z + .25], [x, y, cz], .005, 'black', 'ceiling')
        self.lathe(x, y, z, [(.22, 0), (.2, .04), (.12, .14), (.05, .22), (0, .25)], 'steel', 'ceiling', 24)
        self.sphere(x, y, z + .06, .05, 'amber', 'ceiling')

    def conduits(self, f, key, runs):
        self.at(f, key); cz = _cz(self) + .012
        for (a, b) in runs:
            self.rod([a[0], a[1], cz - .05], [b[0], b[1], cz - .05], .012, 'conduit', 'ceiling', 8)
            for t in (.25, .5, .75):
                self.box(a[0] + (b[0] - a[0]) * t - .05, a[1] + (b[1] - a[1]) * t - .05, cz - .1, .1, .1, .06, 'conduit', 'ceiling')

    def duct(self, a, b, r=.16):
        cz = _cz(self) + .012; z = cz - .22
        self.rod([a[0], a[1], z], [b[0], b[1], z], r, 'duct', 'ceiling', 20)
        L = math.dist(a, b)
        for i in range(int(L / .6)):
            t = (i + .5) * .6 / L; p = [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t]
            d = np.subtract(b, a) / L * .012
            self.rod([p[0] - d[0], p[1] - d[1], z], [p[0] + d[0], p[1] + d[1], z], r + .008, 'duct', 'ceiling', 20)
        for t in (.2, .8):
            p = [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t]; self.rod([p[0], p[1], z + r], [p[0], p[1], cz], .008, 'steel', 'ceiling')

    def track(self, a, b, n=4):
        cz = _cz(self)
        self.rod([a[0], a[1], cz - .04], [b[0], b[1], cz - .04], .02, 'black', 'ceiling', 8)
        for i in range(n):
            t = (i + .5) / n; x = a[0] + (b[0] - a[0]) * t; y = a[1] + (b[1] - a[1]) * t
            self.rod([x, y, cz - .06], [x, y, cz - .14], .008, 'black', 'ceiling')
            self.rod([x, y - .03, cz - .2], [x, y + .08, cz - .26], .045, 'black', 'ceiling', 16)

    def pipe_shelf(self, x, y, w, d, h, levels=5, books=True):
        self.item('黑鐵管件書架', x, y, w, d)
        for xx in (x + .03, x + w - .03):
            for yy in (y + .03, y + d - .03):
                self.rod([xx, yy, 0], [xx, yy, h], .017, 'steel')
                self.cyl(xx, yy, 0, .04, .012, 'steel', sec=10)
        for i in range(levels):
            z = .12 + i * (h - .15) / (levels - 1)
            self.box(x, y, z, w, d, .04, 'wood')
            if books and 0 < i < levels - 1:
                for k in range(int(w / .09)):
                    if k % 5 == 4:
                        continue
                    self.box(x + .05 + k * .085, y + .04, z + .04, .07, d - .1, .2 + (k % 3) * .04, ['red', 'cream', 'wool', 'darkwood'][k % 4], 'decor')

    def glass_screen(self, x, y0, y1, h=2.1):
        self.item('黑鐵玻璃隔屏', x - .05, y0, .1, y1 - y0)
        self.box(x - .2, y0, 0, .4, .05, .03, 'steel'); self.box(x - .2, y1 - .05, 0, .4, .05, .03, 'steel')
        nx = 4
        for i in range(nx + 1):
            yy = y0 + (y1 - y0) * i / nx; self.box(x - .02, yy - .02, 0, .04, .04, h, 'steel')
        for z in (0, .9, 1.5, h - .04):
            self.box(x - .02, y0, z, .04, y1 - y0, .04, 'steel')
        self.box(x - .005, y0, .04, .01, y1 - y0, h - .08, 'glass', 'furniture')

    def brick_panel(self, x, y, w, d, h):
        self.item('獨立紅磚展示牆', x, y, w, d)
        self.box(x, y, 0, w, d, h, 'brick'); self.box(x - .01, y - .01, h, w + .02, d + .02, .04, 'steel')

    def easel(self, x, y, facing, canvas_c):
        with self.xf(x, y, facing):
            self.item('黑鐵畫架', -.35, 0, .7, .6)
            self.rod([-.3, .45, 0], [0, .1, 1.8], .014, 'steel'); self.rod([.3, .45, 0], [0, .1, 1.8], .014, 'steel'); self.rod([0, -.25, 0], [0, .1, 1.6], .014, 'steel')
            self.box(-.35, .25, .75, .7, .06, .03, 'steel')
            self.box(-.32, .22, .78, .64, .025, .82, 'canvas2', 'decor')
            for i, c in enumerate(canvas_c):
                self.box(-.25 + i * .18, .245, .9 + (i % 2) * .2, .15, .004, .35, c, 'decor')

    def bed(self, W, L=1.88):
        Wf = W + .1; Lf = L + .1
        self.item('黑鐵管床', -Wf / 2, 0, Wf, Lf)
        for x in (-Wf / 2 + .03, Wf / 2 - .03):
            self.rod([x, .03, 0], [x, .03, 1.0], .025, 'steel'); self.rod([x, Lf - .03, 0], [x, Lf - .03, .55], .025, 'steel')
            self.rod([x, .03, .3], [x, Lf - .03, .3], .02, 'steel')
        for z in (.55, .8, 1.0):
            self.rod([-Wf / 2, .03, z], [Wf / 2, .03, z], .018, 'steel')
        self.rod([-Wf / 2, Lf - .03, .55], [Wf / 2, Lf - .03, .55], .018, 'steel')
        self.box(-Wf / 2 + .03, .05, .28, Wf - .06, Lf - .1, .04, 'wood')
        self.soft(-W / 2, .06, .32, W, L, .22, 'cream', rounding=.18)
        self.drape(-W / 2 - .02, .6, .5, W + .04, L - .55, .07, 'wool', folds=3)
        for i in range(2 if W > 1.2 else 1):
            self.soft(-W / 2 + .12 + i * W / 2, .12, .54, W * .38, .36, .14, 'linen', rounding=.55)
        for side in (-1, 1):
            x = side * (Wf / 2 + .27)
            self.box(x - .22, .06, 0, .44, .38, .02, 'wood'); self.box(x - .22, .06, .44, .44, .38, .02, 'wood')
            for xx in (x - .22, x + .2):
                self.box(xx, .06, 0, .02, .38, .46, 'wood')
            self.item('木箱床邊櫃', x - .22, .06, .44, .38, False)

    def finishes(self):
        for f, key, runs in ((1, 'LIVING_W', [((.6, 1.0), (.6, 15.8)), ((5.8, 1.0), (5.8, 15.8)), ((.6, 8.0), (5.8, 8.0))]),
                             (1, 'LIVING_E', [((7.0, 9.8), (12.0, 9.8))]),
                             (2, 'LIVING', [((6.9, 7.0), (14.0, 7.0)), ((6.9, 10.3), (14.0, 10.3)), ((9.4, 7.0), (9.4, 10.3))]),
                             (3, 'LIVING', [((6.9, 6.6), (12.1, 6.6)), ((1.0, 5.8), (6.9, 6.6))])):
            self.conduits(f, key, runs)
        self.at(2, '客廳兼餐廳'); self.duct((6.9, 8.4), (14.0, 8.4)); self.track((7.6, 6.4), (11.0, 6.4), 5)
        self.at(3, '起居室'); self.duct((6.9, 7.8), (12.1, 7.8), .13)
        for f, rooms in {1: ['LIVING_W', 'LIVING_E'], 2: ['LIVING', 'BED1', 'BED2', 'BED3', 'DINING'], 3: ['LIVING', 'BED1', 'BED2', 'BED3']}.items():
            for k in rooms:
                self.at(f, k); self.dress_windows(k, 'venetian', 'steel', 'steel', codes=('W',))

    def gallery1(self):
        self.at(1, '展覽空間／教室（西側）：創作工坊')
        self.box(.4, .45, 0, 3.0, .8, .05, 'steel'); self.legs(.4, .45, .05, 3.0, .8, .82, 'steel', .025)
        self.box(.35, .4, .87, 3.1, .9, .07, 'wood'); self.item('厚木工作台', .35, .4, 3.1, .9)
        self.box(2.9, 1.18, .94, .18, .12, .1, 'steel', 'furniture')
        for F in faces(1, 'LIVING_W', 'full'):
            if F.wall['name'] == 'back_left':
                self.face_box(F, .3, 3.5, 1.05, 1.1, .02, 'darkwood')
                for i in range(14):
                    q = F.p(.45 + i * .22, .04); self.rod([q[0], q[1], 1.3 + (i % 3) * .25], [q[0], q[1] + .01, 1.55 + (i % 3) * .25], .008, ['steel', 'red', 'wood'][i % 3], 'wallmount')
        for x in (1.0, 2.0, 3.0):
            self.enamel(x, .85, 2.6)
        for x, y, c in ((1.5, 4.4, ['red', 'wool']), (3.0, 4.1, ['cream', 'rust', 'darkwood']), (4.5, 4.5, ['wool', 'red'])):
            self.easel(x, y, '-y', c)
        self.box(3.8, 2.5, 0, .5, .4, .8, 'red', r=.02); self.item('工具推車', 3.8, 2.5, .5, .4)
        for i in range(4):
            self.box(5.98, 6.3 + i * .46, 0, .45, .44, 1.8, 'wool'); self.item('鐵製置物櫃', 5.98, 6.3 + i * .46, .45, .44)
            for z in (1.45, 1.52, 1.59):
                self.box(5.975, 6.36 + i * .46, z, .005, .3, .02, 'steel', 'decor')
        self.brick_panel(6.2, 8.5, .22, 2.4, 2.4)
        # Classroom: >= 1.1 m between table groups and >= 0.9 m to the brick wall / lockers.
        for ty in (9.3, 12.3):
            for tx in (.45, 3.25):
                self.box(tx, ty, .72, 2.0, .8, .05, 'wood'); self.legs(tx, ty, 0, 2.0, .8, .72, 'steel', .02); self.item('教學長桌', tx, ty, 2.0, .8)
                for k in range(3):
                    for yy, dy in ((ty - .45, 0), (ty + .95, 0)):
                        self.lathe(tx + .35 + k * .65, yy + .15, 0, [(0, 0), (.18, 0), (.12, .6), (.17, .62), (.17, .66), (0, .66)], 'steel', 'furniture', 12)
        for F in faces(1, 'LIVING_W', 'low'):
            if F.wall['name'] == 'left':
                self.face_box(F, F.s0 + .5, F.s1 - .5, 2.75, .03, .03, 'steel')
                for s, w, h in ((4.2, 1.2, .9), (6.0, .8, 1.1), (11.8, 1.3, .9)):
                    self.rod(list(F.p(s, .03)) + [2.75], list(F.p(s, .03)) + [1.2 + h], .002, 'steel', 'wallmount')
                    self.frame_art(F, s, 1.2, w, h, 'black', ['red', 'wool', 'cream'], seed=int(s))
        self.track((1.5, 3.0), (1.5, 14.0), 8); self.track((4.8, 3.0), (4.8, 14.0), 8)

    def lobby1(self):
        self.at(1, 'Lobby 大廳（東側）')
        self.box(8.3, 10.95, 0, 2.4, .6, 1.0, 'concrete'); self.box(8.25, 10.9, 1.0, 2.5, .7, .04, 'steel'); self.item('清水混凝土接待櫃台', 8.25, 10.9, 2.5, .7)
        self.box(6.7, 8.4, .42, .5, 1.9, .06, 'wood'); self.legs(6.7, 8.4, 0, .5, 1.9, .42, 'steel', .02); self.item('鐵木長凳', 6.7, 8.4, .5, 1.9)
        self.box(11.7, 8.9, 0, .5, .5, .3, 'rust'); self.pot(11.95, 9.15, .2, .1, 'rust')
        self.cage(9.0, 11.25, 1.3); self.cage(10.0, 11.25, 1.3)

    def living2(self):
        self.at(2, '客廳兼餐廳')
        self.pipe_shelf(8.0, 6.0, 2.8, .36, 1.95)
        self.box(8.8, 6.06, .98, 1.3, .03, .75, 'screen', 'decor'); self.item('電視', 8.8, 6.0, 1.3, .1, False)
        hide = Polygon([(8.1, 7.3), (9.2, 7.1), (10.5, 7.2), (10.9, 7.9), (10.6, 8.8), (9.4, 9.0), (8.2, 8.8), (7.9, 8.0)])
        self.poly(hide, 0, .008, 'hide', 'decor'); self.item('皮革地毯', 7.9, 7.1, 3.0, 1.9, False)
        with self.xf(9.4, 9.6, '-y'):
            self.sofa()
        with self.xf(7.2, 7.85, '+x'):
            self.club()
        with self.xf(11.65, 7.85, '-x'):
            self.club()
        self.box(8.8, 7.55, .36, 1.2, .65, .06, 'wood'); self.box(8.82, 7.57, .08, 1.16, .61, .03, 'steel')
        for x in (8.82, 9.98):
            for y in (7.57, 8.18):
                self.box(x, y, .06, .02, .02, .3, 'steel'); self.cyl(x + .01, y + .01, 0, .035, .06, 'black', sec=10)
        self.item('回收木鐵件茶几（附輪）', 8.8, 7.55, 1.2, .65)
        for a in (0, 2.1, 4.2):
            self.rod([10.95 + math.cos(a) * .25, 9.4 + math.sin(a) * .25, 0], [10.95, 9.4, 1.5], .012, 'steel')
        self.lathe(10.95, 9.4, 1.45, [(.2, 0), (.18, .05), (.08, .2), (0, .22)], 'steel', 'furniture', 20); self.item('三腳落地燈', 10.7, 9.15, .5, .5, False)
        # Screen starts 1.4 m in front of the kitchen door so the kitchen-to-living route stays open.
        self.glass_screen(11.8, 7.35, 9.3)
        self.brick_panel(6.62, 6.3, .18, 2.3, 2.3)
        self.box(6.7, 9.0, .9, .7, 1.2, .04, 'wood'); self.legs(6.7, 9.0, 0, .7, 1.2, .9, 'steel', .018); self.item('製圖工作桌', 6.7, 9.0, .7, 1.2)
        self.lathe(7.35, 9.6, 0, [(0, 0), (.18, 0), (.12, .6), (.17, .62), (.17, .66), (0, .66)], 'steel', 'furniture', 12)
        # dining: slab table, bench, metal chairs, cage pendants
        self.box(12.05, 8.15, .7, 1.9, .9, .08, 'wood')
        for x in (12.25, 13.75):
            self.rod([x, 8.25, 0], [x, 8.95, .7], .02, 'steel'); self.rod([x, 8.95, 0], [x, 8.25, .7], .02, 'steel'); self.rod([x, 8.25, 0], [x, 8.95, 0], .02, 'steel')
        self.item('厚木板長餐桌', 12.05, 8.15, 1.9, .9)
        self.box(12.25, 7.5, .42, 1.5, .35, .05, 'wood'); self.legs(12.25, 7.5, 0, 1.5, .35, .42, 'steel', .018); self.item('長凳', 12.25, 7.5, 1.5, .35)
        for x in (12.6, 13.4):
            with self.xf(x, 9.6, '-y'):
                self.item('金屬餐椅', -.22, 0, .44, .46)
                self.box(-.2, .04, .44, .4, .4, .025, 'red', r=.03); self.legs(-.2, .04, 0, .4, .4, .44, 'red', .012, .03)
                self.box(-.2, 0, .47, .4, .025, .38, 'red', r=.01)
        for x in (12.4, 13.0, 13.6):
            self.cage(x, 8.6, 1.35)

    def kitchen2(self):
        self.kitchen('galley', 'stainless', 'stainless', 'subway', 'steel', 'stainless', 'chimney', 'open', cab_upper='steel')
        self.rod([12.1, .12, 1.45], [13.1, .12, 1.45], .01, 'steel', 'wallmount')
        for i in range(5):
            x = 12.2 + i * .2; self.box(x - .01, .1, 1.18, .02, .02, .25, ['steel', 'wood', 'steel'][i % 3], 'wallmount')
        self.cage(12.9, 1.6, 1.0); self.cage(12.9, 2.6, 1.0)

    def bedrooms(self):
        for f, room, x, y, facing, size in ((2, 'BED1', 1.81, 5.76, '-y', '5'), (2, 'BED2', 1.81, 11.9, '-y', '5'), (2, 'BED3', .15, 14.16, '+x', '6'),
                                            (3, 'BED1', 1.81, 3.8, '-y', '5'), (3, 'BED2', 1.81, 11.55, '-y', '5')):
            self.at(f, {'BED1': '臥室一', 'BED2': '臥室二', 'BED3': '臥室三'}[room])
            n0 = len(self.items)
            with self.xf(x, y, facing):
                self.bed(*MATTRESS[size])
                self.items[n0].update(category='bed', head_side={'-y': '+y', '+y': '-y', '+x': '-x', '-x': '+x'}[facing], mattress_cm=[round(v * 100) for v in MATTRESS[size]])
                for side in (-1, 1):
                    self.rod([side * (MATTRESS[size][0] / 2 + .32), .25, 1.35], [side * (MATTRESS[size][0] / 2 + .32), .25, _cz(self)], .004, 'black', 'ceiling')
                    self.sphere(side * (MATTRESS[size][0] / 2 + .32), .25, 1.3, .06, 'amber', 'ceiling', 2, (1, 1, 1.3))
            p = RP[(f, room)]
            if room == 'BED3':
                for xx in (4.0, 4.9):
                    self.rod([xx, 15.9, 0], [xx, 15.9, 1.7], .016, 'steel')
                self.rod([4.0, 15.9, 1.7], [4.9, 15.9, 1.7], .016, 'steel'); self.item('管件吊衣架', 3.95, 15.75, 1.0, .3)
            else:
                # 2F bedroom 2 is entered from its back-right corner; keep that corner clear.
                cy = p.bounds[3] - .6 if (f, room) == (2, 'BED2') else p.bounds[1] + .1
                self.box(3.2, cy, 0, .45, .5, 1.3, 'wool'); self.item('鐵製收納櫃', 3.2, cy, .45, .5)

    def living3(self):
        self.at(3, '起居室：唱片與閱讀')
        with self.xf(8.0, 6.05, '+y'):
            self.sofa(1.8, .9)
        self.poly(Polygon([(7.3, 7.1), (8.8, 7.0), (9.3, 7.7), (8.6, 8.3), (7.4, 8.1)]), 0, .008, 'hide', 'decor')
        self.box(7.5, 7.3, .36, 1.0, .55, .05, 'wood'); self.legs(7.5, 7.3, 0, 1.0, .55, .36, 'steel', .018); self.item('鐵木茶几', 7.5, 7.3, 1.0, .55)
        self.box(9.6, 6.05, 0, 1.3, .42, .62, 'darkwood'); self.item('唱片機邊櫃', 9.6, 6.05, 1.3, .42)
        self.cyl(9.95, 6.26, .62, .15, .02, 'black', 'decor'); self.box(9.75, 6.1, .62, .42, .34, .04, 'wood', 'decor')
        self.pipe_shelf(12.0, 6.3, .34, 2.1, 1.9)
        with self.xf(11.3, 7.4, '-x'):
            self.club()
        self.cage(8.0, 7.6, 1.1)
        self.at(3, '起居室走廊'); self.box(.15, 4.5, .42, .45, 2.0, .06, 'wood'); self.legs(.15, 4.5, 0, .45, 2.0, .42, 'steel', .02); self.item('鐵木長凳', .15, 4.5, .45, 2.0)

    def worship3(self):
        self.at(3, '佛廳／祭祀空間')
        self.box(.15, 12.35, .82, .7, 2.2, .06, 'darkwood'); self.legs(.15, 12.35, 0, .7, 2.2, .82, 'steel', .025)
        self.box(.2, 12.4, .15, .6, 2.1, .03, 'darkwood'); self.box(.18, 12.75, .88, .5, 1.4, .6, 'darkwood')
        self.item('神桌＋佛龕（無造像）', .15, 12.35, .7, 2.2)
        self.box(1.05, 12.95, .6, .55, 1.0, .04, 'darkwood'); self.legs(1.05, 12.95, 0, .55, 1.0, .6, 'steel', .018); self.item('供桌', 1.05, 12.95, .55, 1.0)
        self.lathe(1.32, 13.45, .64, [(0, 0), (.1, 0), (.12, .09), (0, .09)], 'steel'); self.item('鑄鐵香爐', 1.2, 13.33, .24, .24, False)
        for y in (13.0, 13.75):
            self.soft(2.0, y, 0, .55, .5, .09, 'wool', rounding=.5); self.item('拜墊', 2.0, y, .55, .5, False)

    def terrace4(self):
        self.at(4, '露台')
        self.lathe(2.5, 8.4, 0, [(0, 0), (.25, 0), (.03, .05), (.03, .7), (.35, .7), (.35, .74), (0, .74)], 'steel', 'furniture', 24); self.item('鐵製小圓桌', 2.15, 8.05, .7, .7)
        for x, y, f in ((2.5, 7.5, '+y'), (2.5, 9.3, '-y')):
            with self.xf(x, y, f):
                self.item('金屬戶外椅', -.22, 0, .44, .46)
                self.box(-.2, .04, .44, .4, .4, .025, 'steel', r=.03); self.legs(-.2, .04, 0, .4, .4, .44, 'steel', .012, .03); self.box(-.2, 0, .47, .4, .025, .38, 'steel')
        self.cyl(4.3, 9.6, 0, .45, .06, 'wood'); self.cyl(4.3, 9.6, .06, .18, .44, 'wood'); self.cyl(4.3, 9.6, .5, .45, .06, 'wood'); self.item('電纜捲軸桌', 3.85, 9.15, .9, .9)
        for x in (1.0, 2.6, 4.2):
            self.box(x, 11.0, 0, 1.3, .45, .5, 'rust'); self.item('耐候鋼花槽', x, 11.0, 1.3, .45)
            self.leaves(x + .65, 11.22, .45, 18, .45, .45, .03, .1, 'leaf2', seed=int(x * 10))
        self.box(5.5, 6.6, .42, .45, 2.0, .06, 'wood'); self.legs(5.5, 6.6, 0, .45, 2.0, .42, 'steel', .02); self.item('鐵木長凳', 5.5, 6.6, .45, 2.0)

    def storage4(self):
        self.at(4, '儲藏間'); self.storage_shelves('steel', 'steel', ['wool', 'stainless', 'red'])

    def populate(self):
        self.finishes(); self.gallery1(); self.lobby1(); self.living2(); self.kitchen2(); self.bedrooms()
        self.living3(); self.worship3(); self.storage4(); self.terrace4()


# =====================================================================
# 3. 折衷混搭：古典線板 × 大膽色彩
# =====================================================================
class Eclectic(Kit):
    key = 'eclectic'; label = '折衷混搭'
    brief = dict(concept='古典線板 × 大膽色彩：胡桃木人字拼、腰牆板與天花線板，天鵝絨、黃銅與大理石混搭',
                 floor='胡桃木人字拼（7×42 cm）', walls='奶油色牆＋白色腰牆板（90 cm）＋掛畫線（235 cm）', ceiling='天花線板＋圓形燈座飾盤',
                 lighting='黃銅放射吊燈（Sputnik 式）、乳白球燈群、百褶燈罩檯燈', windows='祖母綠天鵝絨落地簾＋黃銅簾桿與綁帶',
                 signature='鈷藍弧形天鵝絨沙發、莓紅殼形單椅、胡桃木溫莎椅、洞石圓几、沙龍式掛畫牆、大理石台座雕塑、軟包高床頭')
    FLOOR = 'herringbone'
    MATS = {'herringbone': ('#ffffff', .5, 0), 'paint': ('#ddd3bd', .95, 0), 'ceilpaint': ('#f6f2ea', .9, 0), 'trim': ('#f4f0e6', .5, 0),
            'velvet': ('#2f4fae', .9, 0), 'rosevelvet': ('#b3405f', .9, 0), 'mustvelvet': ('#d4a236', .9, 0), 'emervelvet': ('#1f6b55', .9, 0),
            'walnut': ('#5d3f2a', .55, 0), 'brass': ('#c09a4e', .3, .85), 'travertine': ('#dbcbb0', .55, 0), 'marble': ('#ede9e2', .2, 0),
            'rug': ('#e0b985', .95, 0), 'rugblue': ('#2f4fae', .95, 0), 'rugred': ('#b3405f', .95, 0), 'cobalt': ('#27418f', .45, 0),
            'checker': ('#ffffff', .2, 0), 'opal': ('#fbf6ec', .3, 0, [.95, .88, .75]), 'lacquer': ('#8e2a22', .3, 0), 'shade': ('#efe4cc', .8, 0, [.35, .3, .22]),
            'stainless': ('#c4c7c9', .3, .85), 'iron': ('#26282a', .5, .5), 'wood': ('#6b4a30', .8, 0), 'mosaic': ('#3b8fa6', .3, 0), 'clay': ('#c65f3c', .5, 0), 'stripe': ('#e8d7a8', .8, 0)}

    def curved_sofa(self, cx, cy, r0=1.0, r1=1.9, a0=200, a1=340):
        def sector(ra, rb, h0, h1):
            pts = [(cx + ra * math.cos(math.radians(a)), cy + ra * math.sin(math.radians(a))) for a in np.linspace(a0, a1, 30)]
            pts += [(cx + rb * math.cos(math.radians(a)), cy + rb * math.sin(math.radians(a))) for a in np.linspace(a1, a0, 30)]
            return Polygon(pts).buffer(-.03).buffer(.03)
        self.poly(sector(r0 + .05, r1, 0, 0), .04, .16, 'brass')
        self.poly(sector(r0, r1, 0, 0).buffer(-.02), .12, .28, 'velvet')
        self.poly(sector(r1 - .24, r1, 0, 0), .4, .42, 'velvet')
        for a in np.linspace(a0 + 12, a1 - 12, 5):
            x = cx + (r0 + r1) / 2 * math.cos(math.radians(a)); y = cy + (r0 + r1) / 2 * math.sin(math.radians(a))
            self.osoft(x, y, .38, .5, .5, .12, math.radians(a) + math.pi / 2, 'velvet', rounding=.35)
        for i, a in enumerate(np.linspace(a0 + 20, a1 - 20, 4)):
            x = cx + (r1 - .32) * math.cos(math.radians(a)); y = cy + (r1 - .32) * math.sin(math.radians(a))
            self.osoft(x, y, .5, .38, .13, .36, math.radians(a) + math.pi / 2, ['mustvelvet', 'rosevelvet', 'emervelvet', 'mustvelvet'][i], rounding=.6, tilt=-.3)
        b = sector(r0, r1, 0, 0).bounds; self.item('鈷藍弧形天鵝絨沙發', b[0], b[1], b[2] - b[0], b[3] - b[1])

    def shell_chair(self):
        self.item('莓紅殼形單椅', -.4, 0, .8, .8)
        self.cyl(0, .4, 0, .26, .02, 'brass'); self.cyl(0, .4, 0, .03, .3, 'brass', sec=12)
        m = tm.creation.icosphere(subdivisions=3, radius=.42); m.apply_scale([1, 1, .9])
        keep = (m.triangles_center[:, 2] < .1 + .45 * (m.triangles_center[:, 1] < 0)) & ~((m.triangles_center[:, 1] > .1) & (m.triangles_center[:, 2] > .05))
        m.update_faces(keep); m.remove_unreferenced_vertices(); m.apply_translation([0, .4, self.Z(.62)]); self.add(m, 'rosevelvet')
        self.soft(-.3, .15, .3, .6, .55, .12, 'rosevelvet', rounding=.7)

    def spindle_chair(self):
        self.item('胡桃木溫莎椅', -.25, 0, .5, .5)
        self.box(-.23, .04, .43, .46, .44, .04, 'walnut', r=.08)
        for x in (-.18, .18):
            for y in (.1, .42):
                self.rod([x * 1.15, y + (.04 if y > .2 else -.04), 0], [x, y, .43], .016, 'walnut')
        for i in range(7):
            x = -.18 + i * .06; self.rod([x, .08, .47], [x * 1.1, .02, .95], .008, 'walnut')
        self.box(-.24, -.01, .93, .48, .06, .05, 'walnut', r=.02)

    def lamp(self, x, y, zr):
        self.lathe(x, y, zr, [(0, 0), (.08, 0), (.03, .05), (.02, .3), (0, .3)], 'brass', 'decor', 16)
        self.lathe(x, y, zr + .28, [(.17, 0), (.1, .22), (0, .22)], 'shade', 'decor', 24)

    def sputnik(self, x, y, drop=1.1):
        cz = _cz(self); z = cz - drop
        self.cyl(x, y, cz - .03, .35, .03, 'trim', 'ceiling', 40); self.cyl(x, y, cz - .045, .22, .015, 'trim', 'ceiling', 40)
        self.rod([x, y, z], [x, y, cz - .03], .01, 'brass', 'ceiling'); self.sphere(x, y, z, .07, 'brass', 'ceiling')
        rng = np.random.default_rng(3)
        for i in range(16):
            v = rng.normal(0, 1, 3); v[2] *= .6; v /= np.linalg.norm(v); e = [x + v[0] * .45, y + v[1] * .45, z + v[2] * .45]
            self.rod([x, y, z], e, .006, 'brass', 'ceiling'); self.sphere(*e, .035, 'bulb', 'ceiling', 1)

    def globe(self, x, y, drop, r=.14):
        cz = _cz(self); self.rod([x, y, cz - drop + r], [x, y, cz], .005, 'brass', 'ceiling'); self.sphere(x, y, cz - drop, r, 'opal', 'ceiling', 2)

    def plinth(self, x, y, h=1.0, kind=0):
        self.box(x - .2, y - .2, 0, .4, .4, h, 'marble'); self.item('大理石台座＋抽象雕塑', x - .2, y - .2, .4, .4, False)
        if kind == 0:
            self.sphere(x, y, h + .16, .16, 'brass', 'decor')
        elif kind == 1:
            m = tm.creation.torus(.16, .035); m.apply_transform(tm.transformations.rotation_matrix(math.pi / 2, [1, 0, 0])); m.apply_translation([x, y, self.Z(h + .2)]); self.add(m, 'brass', 'decor')
        else:
            self.lathe(x, y, h, [(0, 0), (.12, 0), (.04, .2), (.1, .38), (0, .42)], 'rosevelvet', 'decor')

    def gallery(self, F, s0, s1, z0=1.0, z1=2.25, seed=0):
        rng = np.random.default_rng(seed); s = s0
        palette = [['velvet', 'mustvelvet', 'cream' if False else 'trim'], ['rosevelvet', 'emervelvet'], ['mustvelvet', 'rugblue', 'clay']]
        while s < s1 - .35:
            w = .35 + rng.random() * .55; col = []
            z = z0
            while z < z1 - .25:
                h = .3 + rng.random() * .5
                if z + h > z1:
                    break
                self.frame_art(F, s + w / 2, z, w, h, 'brass' if rng.random() < .5 else 'walnut', palette[int(rng.random() * 3)], seed=int(rng.random() * 1000))
                z += h + .08
            s += w + .1

    def bed(self, W, L=1.88, stands=(-1, 1)):
        Wf = W + .14; Lf = L + .12
        self.item('軟包高床頭床組', -Wf / 2, 0, Wf, Lf)
        self.box(-Wf / 2, .12, 0, Wf, Lf - .12, .3, 'mustvelvet', r=.03)
        self.soft(-Wf / 2, 0, .1, Wf, .14, 1.35, 'mustvelvet', rounding=.25)
        for i in range(6):
            for j in range(4):
                self.sphere(-Wf / 2 + .15 + i * (Wf - .3) / 5, .145, .45 + j * .25, .012, 'brass', 'decor', 1)
        self.soft(-W / 2, .16, .3, W, L - .06, .22, 'trim', rounding=.18)
        self.drape(-W / 2 - .03, .7, .48, W + .06, L - .66, .07, 'rugblue', folds=4)
        self.drape(-W / 2 - .03, L - .35, .54, W + .06, .3, .04, 'rosevelvet', folds=2)
        for i in range(2 if W > 1.2 else 1):
            self.soft(-W / 2 + .12 + i * W / 2, .2, .52, W * .38, .34, .16, 'trim', rounding=.55)
        self.osoft(0, .5, .56, .45, .14, .3, 0, 'emervelvet', rounding=.6, tilt=-.35)
        self.soft(-W / 2 + .1, Lf + .05, .0, W - .2, .42, .45, 'rosevelvet', rounding=.35); self.item('床尾凳', -W / 2 + .1, Lf + .05, W - .2, .42, False)
        for side in stands:
            x = side * (Wf / 2 + .27)
            self.box(x - .23, .08, .12, .46, .4, .5, 'walnut', r=.02); self.legs(x - .23, .08, 0, .46, .4, .12, 'brass', .012, .04)
            self.lamp(x, .28, .62); self.item('胡桃木床邊櫃＋檯燈', x - .23, .08, .46, .4, False)

    def rug_round(self, x, y, r):
        self.cyl(x, y, 0, r, .008, 'rug', 'decor', 64)
        for k, c in enumerate(['rugblue', 'rugred', 'rug', 'rugblue']):
            self.cyl(x, y, .008 + k * .001, r * (.85 - k * .2), .001, c, 'decor', 64)
        self.item('幾何圓毯', x - r, y - r, 2 * r, 2 * r, False)

    def rug_rect(self, x, y, w, d):
        self.box(x, y, 0, w, d, .008, 'rugred', 'decor'); self.box(x + .1, y + .1, .008, w - .2, d - .2, .002, 'rug', 'decor')
        for i in range(int(w / .5)):
            self.cyl(x + .35 + i * .5, y + d / 2, .01, .16, .002, ['rugblue', 'rugred'][i % 2], 'decor', 24)
        self.item('圖騰地毯', x, y, w, d, False)

    def finishes(self):
        for f, rooms in {1: ['LIVING_W', 'LIVING_E'], 2: ['LIVING', 'BED1', 'BED2', 'BED3'], 3: ['LIVING', 'BED1', 'BED2']}.items():
            for k in rooms:
                self.at(f, k); self.crown(k, 'trim'); self.wainscot(k, 'trim'); self.picture_rail(k, 'trim')
                self.dress_windows(k, 'drape', 'emervelvet', 'brass')

    def gallery1(self):
        self.at(1, '展覽空間／教室（西側）：沙龍展廳')
        for F in faces(1, 'LIVING_W', 'low'):
            if F.wall['name'] == 'left':
                self.gallery(F, 2.6, 7.2, 1.05, 2.25, 1); self.gallery(F, 9.0, 12.2, 1.05, 2.25, 2)
            if F.wall['name'] == 'living_partition':
                self.gallery(F, .6, 5.6, 1.05, 2.25, 3)
        for x, y, k in ((2.4, 3.4, 0), (3.6, 4.7, 1), (2.4, 6.0, 2), (3.6, 7.3, 0)):
            self.plinth(x, y, 1.0, k)
        for y in (2.9, 4.4, 5.9, 7.4):
            self.cyl(1.05, y, 0, .15, .03, 'brass'); self.cyl(1.05, y, 0, .025, .95, 'brass', sec=10); self.sphere(1.05, y, .97, .04, 'brass', 'furniture', 1)
        for y0, y1 in ((2.9, 4.4), (4.4, 5.9), (5.9, 7.4)):
            for i in range(8):
                t0, t1 = i / 8, (i + 1) / 8; s = lambda t: .9 - .18 * math.sin(math.pi * t)
                self.rod([1.05, y0 + (y1 - y0) * t0, s(t0)], [1.05, y0 + (y1 - y0) * t1, s(t1)], .016, 'rosevelvet', 'furniture')
        self.item('黃銅紅絨欄柱', .9, 2.75, .3, 4.8, False)
        self.soft(2.4, 8.6, 0, 1.3, 1.3, .42, 'emervelvet', rounding=.85); self.item('圓形軟墊凳', 2.4, 8.6, 1.3, 1.3)
        self.rug_rect(1.8, 2.2, 2.5, 5.8)
        for cx, cy in ((1.9, 11.6), (4.3, 11.6)):
            self.cyl(cx, cy, .72, .55, .04, 'walnut', 'furniture', 40); self.cyl(cx, cy, 0, .06, .72, 'walnut', 'furniture', 12); self.cyl(cx, cy, 0, .3, .03, 'brass', 'furniture', 32)
            self.item('胡桃木圓桌', cx - .55, cy - .55, 1.1, 1.1)
            for a, f in ((0, '-x'), (math.pi / 2, '-y'), (math.pi, '+x'), (1.5 * math.pi, '+y')):
                px, py = cx + math.cos(a) * .95, cy + math.sin(a) * .95
                with self.xf(px, py, f):
                    self.spindle_chair()
        self.sputnik(3.0, 8.3, 1.4); self.globe(1.9, 11.6, 1.5); self.globe(4.3, 11.6, 1.5)
        self.fiddle(5.8, 15.8, 1.8, 'clay', seed=9)

    def lobby1(self):
        self.at(1, 'Lobby 大廳（東側）')
        self.box(8.3, 10.95, 0, 2.4, .6, 1.0, 'walnut', r=.02); self.box(8.25, 10.9, 1.0, 2.5, .7, .04, 'marble')
        for i in range(4):
            self.box(8.4 + i * .6, 10.93, .15, .5, .02, .7, 'walnut')
        self.item('胡桃木大理石接待台', 8.25, 10.9, 2.5, .7)
        for y, f in ((8.4, '+x'), (9.9, '+x')):
            with self.xf(6.72, y, f):
                self.item('天鵝絨扶手椅', -.38, 0, .76, .75)
                self.soft(-.38, 0, .05, .76, .75, .38, 'velvet', rounding=.35); self.soft(-.38, 0, .38, .76, .2, .48, 'velvet', rounding=.4)
        self.cyl(7.1, 9.15, 0, .3, .5, 'travertine', 'furniture', 32); self.item('洞石小圓几', 6.8, 8.85, .6, .6)
        self.rug_round(7.5, 9.15, .9); self.globe(9.4, 11.25, 1.6, .18); self.globe(10.2, 11.25, 1.4, .12)
        self.fiddle(11.9, 9.3, 1.9, 'clay', seed=11)

    def living2(self):
        self.at(2, '客廳兼餐廳')
        self.rug_round(9.4, 8.0, 1.55)
        self.curved_sofa(9.4, 8.0)
        self.cyl(9.4, 8.0, 0, .5, .38, 'travertine', 'furniture', 48); self.cyl(9.4, 8.0, .38, .52, .012, 'brass', 'furniture', 48); self.item('洞石圓几', 8.9, 7.5, 1.0, 1.0)
        self.lathe(9.25, 7.95, .39, [(0, 0), (.07, 0), (.1, .15), (.05, .28), (0, .28)], 'clay')
        with self.xf(8.5, 9.95, '-y'):
            self.shell_chair()
        with self.xf(10.4, 9.95, '-y'):
            self.spindle_chair()
        self.sputnik(9.4, 8.0, 1.0)
        for F in faces(2, 'LIVING', 'full'):
            if F.wall['name'] == 'stair_front':
                self.gallery(F, 1.4, 5.1, 1.2, 2.25, 5)
        self.box(6.62, 7.2, .15, .45, 2.0, .7, 'walnut', r=.02); self.legs(6.62, 7.2, 0, .45, 2.0, .15, 'brass', .015, .05)
        for i in range(3):
            self.box(7.07, 7.26 + i * .66, .22, .012, .62, .56, 'walnut')
        self.lamp(6.85, 7.5, .85); self.lamp(6.85, 8.9, .85); self.item('復古胡桃木餐邊櫃', 6.62, 7.2, .45, 2.0)
        for z in (.1, .5, .85):
            self.box(7.05, 9.45, z, .6, .38, .015, 'glass')
        for x in (7.07, 7.63):
            for y in (9.47, 9.81):
                self.rod([x, y, 0], [x, y, .9], .01, 'brass')
        self.item('黃銅酒車', 7.05, 9.45, .6, .38)
        for k in range(4):
            self.lathe(7.15 + k * .12, 9.62, .52, [(0, 0), (.035, 0), (.035, .2), (.012, .26), (0, .3)], ['emervelvet', 'glass', 'rosevelvet', 'glass'][k], 'decor', 10)
        self.plinth(11.6, 6.45, .9, 1)
        # dining: marble pedestal table, four different chairs, globe pendant cluster
        self.cyl(13.0, 8.7, .72, .6, .03, 'marble', 'furniture', 48); self.lathe(13.0, 8.7, 0, [(0, 0), (.32, 0), (.06, .12), (.06, .6), (.2, .72), (0, .72)], 'trim', 'furniture', 32)
        self.item('大理石圓餐桌', 12.4, 8.1, 1.2, 1.2)
        with self.xf(13.0, 7.55, '+y'):
            self.spindle_chair()
        with self.xf(13.0, 9.85, '-y'):
            self.item('天鵝絨餐椅', -.24, 0, .48, .5); self.soft(-.24, .05, .42, .48, .45, .1, 'emervelvet', rounding=.5); self.soft(-.24, 0, .5, .48, .12, .45, 'emervelvet', rounding=.5); self.legs(-.22, .07, 0, .44, .4, .42, 'brass', .012)
        with self.xf(11.85, 8.7, '+x'):
            self.item('鈷藍漆餐椅', -.23, 0, .46, .46); self.box(-.21, .04, .43, .42, .42, .04, 'cobalt', r=.03); self.legs(-.21, .04, 0, .42, .42, .43, 'cobalt', .015); self.box(-.21, 0, .47, .42, .04, .45, 'cobalt', r=.02)
        with self.xf(14.15, 8.7, '-x'):
            self.spindle_chair()
        for dx, dy, dr in ((-.2, -.15, 1.2), (.15, .1, 1.0), (.05, -.25, .85), (-.1, .22, 1.35)):
            self.globe(13.0 + dx, 8.7 + dy, dr, .1 + .02 * (dr > 1))

    def kitchen2(self):
        self.kitchen('L', 'cobalt', 'marble', 'checker', 'brass', 'stainless', 'canopy', 'cab', cab_upper='trim')
        self.box(13.18, .1, 1.5 + .72, 1.08, .37, .06, 'trim', 'wallmount')
        self.globe(12.9, 2.2, 1.1, .16)
        for i in range(3):
            self.lathe(12.2 + i * .14, .3, .85, [(0, 0), (.05, 0), (.05, .22), (.02, .26), (0, .28)], ['clay', 'mosaic', 'marble'][i], 'decor', 12)

    def bedrooms(self):
        for f, room, x, y, facing, size, st in ((2, 'BED1', 2.0, 5.82, '-y', '5', (-1, 1)), (2, 'BED2', 2.3, 11.98, '-y', '5', (-1, 1)), (2, 'BED3', 2.96, 12.28, '+y', '6', (-1, 1)),
                                                (3, 'BED1', 2.0, 3.9, '-y', '3.5', (-1, 1)), (3, 'BED2', 2.3, 8.05, '+y', '5', (-1, 1))):
            self.at(f, {'BED1': '臥室一', 'BED2': '臥室二', 'BED3': '臥室三'}[room])
            n0 = len(self.items)
            with self.xf(x, y, facing):
                self.bed(*MATTRESS[size], stands=st)
            self.items[n0].update(category='bed', head_side={'-y': '+y', '+y': '-y', '+x': '-x', '-x': '+x'}[facing], mattress_cm=[round(v * 100) for v in MATTRESS[size]])
            p = RP[(f, room)]
            self.globe(p.centroid.x, p.centroid.y, .7, .2)
            for F in faces(f, room, 'full'):
                if F.length > 1.6 and F.wall['name'] in ('bed2_front', 'bed1_front', 'bed2_back', 'bed3_front'):
                    self.gallery(F, F.mid - .7, F.mid + .7, 1.6, 2.35, len(room) * 7 + f); break

    def living3(self):
        self.at(3, '起居室：私人書房')
        self.rug_round(8.3, 7.6, 1.1)
        with self.xf(8.2, 6.05, '+y'):
            w = 2.0; self.item('祖母綠捲手沙發', -w / 2, 0, w, .9)
            self.box(-w / 2, 0, .1, w, .9, .3, 'emervelvet', r=.05); self.legs(-w / 2, 0, 0, w, .9, .1, 'walnut', .02)
            self.soft(-w / 2 + .12, .22, .38, w - .24, .64, .14, 'emervelvet', rounding=.3); self.soft(-w / 2, 0, .38, w, .25, .48, 'emervelvet', rounding=.35)
            for x in (-w / 2 - .02, w / 2 - .16):
                self.soft(x, .02, .3, .18, .86, .34, 'emervelvet', rounding=.85)
            self.osoft(-.5, .35, .52, .4, .14, .36, 0, 'mustvelvet', rounding=.6, tilt=-.3); self.osoft(.5, .35, .52, .4, .14, .36, 0, 'rosevelvet', rounding=.6, tilt=-.3)
        self.cyl(8.3, 7.5, 0, .38, .42, 'travertine', 'furniture', 40); self.item('洞石茶几', 7.92, 7.12, .76, .76)
        with self.xf(10.3, 7.6, '-x'):
            self.item('芥末黃高背單椅', -.4, 0, .8, .8)
            self.soft(-.4, 0, .05, .8, .8, .4, 'mustvelvet', rounding=.35); self.soft(-.4, 0, .4, .8, .22, .75, 'mustvelvet', rounding=.35)
            for x in (-.42, .27):
                self.soft(x, 0, .3, .15, .8, .35, 'mustvelvet', rounding=.6)
        self.box(11.95, 6.2, 0, .36, 3.2, 2.3, 'walnut'); self.item('胡桃木書牆', 11.95, 6.2, .36, 3.2)
        for lv in range(6):
            z = .1 + lv * .37; self.box(11.95, 6.2, z, .36, 3.2, .025, 'walnut')
            for k in range(30):
                if k % 7 == 6:
                    continue
                self.box(11.99, 6.26 + k * .1, z + .025, .28, .07, .22 + (k * 7 % 5) * .025, ['velvet', 'rosevelvet', 'mustvelvet', 'emervelvet', 'trim'][k % 5], 'decor')
        self.lathe(11.1, 6.4, 0, [(0, 0), (.15, 0), (.02, .05), (.02, 1.5), (0, 1.5)], 'brass', 'furniture', 16); self.sphere(11.1, 6.4, 1.6, .18, 'opal', 'furniture', 2)
        self.sputnik(8.3, 7.6, .9)
        self.at(3, '起居室走廊')
        self.box(.15, 4.6, .7, .38, 1.4, .04, 'marble'); self.legs(.15, 4.6, 0, .38, 1.4, .7, 'brass', .015); self.item('大理石玄關桌', .15, 4.6, .38, 1.4)
        self.lamp(.34, 4.9, .74)

    def worship3(self):
        self.at(3, '佛廳／祭祀空間')
        self.box(.15, 12.35, 0, .7, 2.2, .9, 'lacquer', r=.02)
        for y in (12.4, 14.5):
            self.box(.82, y, .1, .04, .04, .7, 'brass')
        self.box(.18, 12.75, .9, .5, 1.4, .62, 'lacquer'); self.box(.16, 12.73, 1.52, .54, 1.44, .05, 'brass'); self.item('朱漆神桌＋佛龕（無造像）', .15, 12.35, .7, 2.2)
        self.box(1.05, 12.95, 0, .55, 1.0, .62, 'lacquer'); self.item('供桌', 1.05, 12.95, .55, 1.0)
        self.lathe(1.32, 13.45, .62, [(0, 0), (.11, 0), (.13, .1), (.1, .12), (0, .12)], 'brass'); self.item('黃銅香爐＋燭台', 1.2, 13.0, .24, 1.0, False)
        for y in (13.05, 13.85):
            self.lathe(1.32, y, .62, [(0, 0), (.05, 0), (.02, .06), (.02, .3), (.04, .32), (0, .32)], 'brass')
        for y in (13.0, 13.75):
            self.soft(2.0, y, 0, .55, .5, .12, 'rosevelvet', rounding=.5); self.item('天鵝絨拜墊', 2.0, y, .55, .5, False)

    def terrace4(self):
        self.at(4, '露台')
        self.cyl(3.0, 8.6, .72, .45, .03, 'mosaic', 'furniture', 40); self.lathe(3.0, 8.6, 0, [(0, 0), (.25, 0), (.03, .1), (.03, .72), (0, .72)], 'iron', 'furniture', 24)
        self.item('馬賽克小圓桌', 2.55, 8.15, .9, .9)
        for a in (0, 2.1, 4.2):
            px, py = 3.0 + math.cos(a) * .8, 8.6 + math.sin(a) * .8
            with self.xf(px, py, math.atan2(-(3.0 - px), 8.6 - py)):
                self.item('鑄鐵椅', -.22, 0, .44, .46); self.box(-.2, .04, .44, .4, .4, .02, 'iron', r=.1)
                self.legs(-.2, .04, 0, .4, .4, .44, 'iron', .01, .03)
                for i in range(5):
                    self.rod([-.18 + i * .09, .02, .46], [-.18 + i * .09, .0, .9], .006, 'iron')
                self.soft(-.18, .06, .46, .36, .36, .06, 'rosevelvet', rounding=.6)
        self.rod([4.3, 8.0, 0], [4.3, 8.0, 2.3], .02, 'brass'); self.cyl(4.3, 8.0, 0, .25, .08, 'iron')
        for i in range(12):
            a0, a1 = i * math.pi / 6, (i + 1) * math.pi / 6
            tri = Polygon([(4.3, 8.0), (4.3 + 1.2 * math.cos(a0), 8.0 + 1.2 * math.sin(a0)), (4.3 + 1.2 * math.cos(a1), 8.0 + 1.2 * math.sin(a1))])
            self.poly(tri, 2.15, .02, 'stripe' if i % 2 else 'rosevelvet', 'decor')
        self.item('條紋遮陽傘', 3.1, 6.8, 2.4, 2.4, False)
        for x, c in ((1.0, 'mosaic'), (2.4, 'clay'), (4.4, 'cobalt'), (5.6, 'mustvelvet')):
            self.lathe(x, 11.2, 0, [(0, 0), (.2, 0), (.25, .45), (.27, .5), (0, .5)], c, 'furniture', 20); self.item('彩釉花盆＋球形灌木', x - .27, 10.93, .54, .54, False)
            self.sphere(x, 11.2, .85, .33, 'leaf', 'decor', 2)
        self.box(1.2, 7.0, 0, 3.4, 3.2, .008, 'stripe', 'decor')

    def storage4(self):
        self.at(4, '儲藏間'); self.storage_shelves('walnut', 'trim', ['mustvelvet', 'rosevelvet', 'velvet'])

    def populate(self):
        self.finishes(); self.gallery1(); self.lobby1(); self.living2(); self.kitchen2(); self.bedrooms()
        self.living3(); self.worship3(); self.storage4(); self.terrace4()


# =====================================================================
# 4. 侘寂：留白、自然材質、不完美
# =====================================================================
class WabiSabi(Kit):
    key = 'wabisabi'; label = '侘寂'
    brief = dict(concept='留白與不完美：寬版橡木、珪藻土、和紙與石材，低矮家具與少量器物',
                 floor='寬版橡木實木地板（18 cm 寬）', walls='暖灰珪藻土', ceiling='客廳木格柵天花＋一道原木梁',
                 lighting='和紙球燈、和紙落地燈（間接低照度）', windows='障子紙門（窗）＋亞麻紗簾（落地門）',
                 signature='低平台亞麻沙發、不規則原木茶几、床之間（壁龕）、榻榻米平台床、低書法桌與座布團、枯山水碎石庭')
    FLOOR = 'oakplank'
    MATS = {'oakplank': ('#ffffff', .6, 0), 'paint': ('#dccfbb', .98, 0), 'ceilpaint': ('#ece4d6', .95, 0), 'oak': ('#bfa27a', .7, 0),
            'ash': ('#d2bf9c', .75, 0), 'linen': ('#e7ddcb', .97, 0), 'sand': ('#cdbfa2', .97, 0), 'charlinen': ('#58544c', .97, 0),
            'clay': ('#a88a6c', .85, 0), 'stone': ('#9e988c', .85, 0), 'paper': ('#f5efe2', .9, 0, [.62, .56, .45]),
            'washi': ('#f3eee3', .9, 0, None, 230), 'tatami': ('#cfc28f', .9, 0), 'ink': ('#2b2b28', .9, 0), 'moss': ('#6f7d52', .95, 0),
            'gravel': ('#bab3a5', .95, 0), 'bamboo': ('#b9a86a', .6, 0), 'glaze': ('#7d6f5d', .35, 0), 'stainless': ('#c4c7c9', .3, .85),
            'wood': ('#8a6a48', .8, 0)}

    def sofa(self, w=2.3, d=.9):
        self.item('低平台亞麻沙發', -w / 2, 0, w, d)
        self.box(-w / 2, 0, 0, w, d, .16, 'oak'); self.box(-w / 2, 0, .16, .06, d, .26, 'oak'); self.box(w / 2 - .06, 0, .16, .06, d, .26, 'oak')
        self.box(-w / 2, 0, .16, w, .06, .38, 'oak')
        self.soft(-w / 2 + .07, .08, .16, w - .14, d - .1, .16, 'linen', rounding=.3)
        for i in range(2):
            self.soft(-w / 2 + .08 + i * (w - .16) / 2, .06, .3, (w - .16) / 2 - .01, .2, .36, 'linen', rounding=.45)
        self.osoft(w / 2 - .4, .3, .34, .38, .12, .34, 0, 'charlinen', rounding=.6, tilt=-.3)

    def lantern(self, x, y, drop=.9, r=.28):
        cz = _cz(self); self.rod([x, y, cz - drop + r], [x, y, cz], .004, 'ink', 'ceiling'); self.sphere(x, y, cz - drop, r, 'paper', 'ceiling', 2, (1, 1, .92))

    def floor_lamp(self, x, y, h=.9):
        self.cyl(x, y, 0, .14, .02, 'oak'); self.cyl(x, y, .02, .12, h, 'paper', 'furniture', 16); self.item('和紙落地燈', x - .14, y - .14, .28, .28, False)

    def vessel(self, x, y, zr, h=.3, mat='glaze', branch=True):
        self.lathe(x, y, zr, [(0, 0), (h * .28, 0), (h * .38, h * .45), (h * .22, h * .85), (h * .14, h), (0, h)], mat, 'decor', 20)
        if branch:
            self.branches(x, y, zr + h * .9, .75, 'wood', seed=int(x * 7))

    def zabuton(self, x, y, c='linen'):
        self.soft(x - .27, y - .27, 0, .54, .54, .08, c, rounding=.45)

    def platform_bed(self, W, L=1.88):
        Wf = W + .3; Lf = L + .3
        self.item('榻榻米平台床＋床墊', -Wf / 2, 0, Wf, Lf)
        self.box(-Wf / 2, 0, 0, Wf, Lf, .16, 'oak')
        self.box(-Wf / 2 + .03, .03, .16, Wf - .06, Lf - .06, .03, 'tatami')
        self.box(-Wf / 2, 0, .16, Wf, .05, .62, 'oak'); self.box(-Wf / 2, 0, .78, Wf, .16, .03, 'oak')
        for x in (-Wf / 2 + .03, 0, Wf / 2 - .06):
            self.box(x, .03, .185, .03, Lf - .06, .006, 'charlinen', 'decor')
        self.soft(-W / 2, .15, .19, W, L, .12, 'linen', rounding=.2)
        self.drape(-W / 2, .6, .31, W, L - .5, .06, 'sand', folds=2)
        for i in range(2 if W > 1.2 else 1):
            self.soft(-W / 2 + .1 + i * W / 2, .2, .31, W * .4, .32, .1, 'linen', rounding=.5)

    def tokonoma(self, F, s, w=1.5, d=.5):
        a = F.p(s - w / 2, 0); b = F.p(s + w / 2, 0); c = F.p(s + w / 2, d); e = F.p(s - w / 2, d)
        self.poly(Polygon([tuple(a), tuple(b), tuple(c), tuple(e)]), 0, .12, 'oak'); q = F.p(s, .12)
        self.item('床之間（壁龕平台）', min(a[0], c[0]), min(a[1], c[1]), abs(c[0] - a[0]), abs(c[1] - a[1]))
        self.face_box(F, s - .28, s + .28, .55, 1.25, .01, 'washi', off=.005); self.face_box(F, s - .3, s + .3, 1.8, .03, .025, 'oak', off=.0)
        self.face_box(F, s - .3, s + .3, .52, .03, .025, 'oak', off=.0)
        for i in range(3):
            self.face_box(F, s - .03 - i * .06, s - i * .06, .9 + i * .2, .12 + i * .1, .003, 'ink', off=.016)
        self.vessel(q[0], q[1], .12, .28)

    def finishes(self):
        for f, key, box_ in ((2, 'LIVING', (7.9, 6.3, 11.2, 9.7)), (3, 'LIVING', (7.0, 6.2, 9.8, 8.5))):
            self.at(f, key); cz = _cz(self); x0, y0, x1, y1 = box_
            for x in np.arange(x0, x1, .09):
                self.box(x, y0, cz - .05, .035, y1 - y0, .05, 'ash', 'ceiling')
            self.beams(RP[(f, key)].intersection(rect(6.6, 6.0, 14.3, 12)), 'x', 1, .18, .22, 'oak')
        for f, rooms in {1: ['LIVING_W', 'LIVING_E'], 2: ['LIVING', 'BED1', 'BED2', 'BED3', 'DINING'], 3: ['LIVING', 'BED1', 'BED2', 'BED3']}.items():
            for k in rooms:
                self.at(f, k); self.dress_windows(k, 'shoji', 'washi', 'oak', codes=('W',)); self.dress_windows(k, 'sheer', 'linen', 'oak', codes=('DW',))

    def gallery1(self):
        self.at(1, '展覽空間／教室（西側）：書法與水墨')
        for F in faces(1, 'LIVING_W', 'low'):
            if F.wall['name'] == 'left':
                for s in (4.2, 6.3):
                    self.frame_art(F, s, 1.0, 1.2, 1.6, 'oak', ['ink'], mode='ink', seed=int(s * 3))
            if F.wall['name'] == 'living_partition':
                self.frame_art(F, 3.0, 1.1, 1.8, 1.2, 'oak', ['ink'], mode='ink', seed=5)
        self.box(2.6, 7.55, .38, 2.4, .42, .07, 'oak'); self.box(2.75, 7.6, 0, .1, .32, .38, 'oak'); self.box(4.75, 7.6, 0, .1, .32, .38, 'oak'); self.item('原木長凳', 2.6, 7.55, 2.4, .42)
        for y in (3.8, 5.4):
            self.box(4.6, y, 0, .45, .45, .75, 'stone'); self.vessel(4.825, y + .225, .75, .32, 'glaze', y > 4); self.item('石台座＋陶器', 4.6, y, .45, .45, False)
        self.box(1.6, 15.35, 0, 3.6, .95, .08, 'oak'); self.box(1.65, 15.4, .02, 3.5, .85, .05, 'gravel', 'decor'); self.item('碎石展示床', 1.6, 15.35, 3.6, .95)
        for x, r in ((2.3, .18), (3.4, .12), (4.5, .22)):
            self.sphere(x, 15.8, .1, r, 'stone', 'decor', 1, (1.3, 1, .7))
        for ty in (9.6, 11.8):
            for tx in (.6, 3.3):
                self.box(tx, ty, .3, 1.8, .6, .04, 'oak'); self.box(tx + .1, ty + .05, 0, .06, .5, .3, 'oak'); self.box(tx + 1.64, ty + .05, 0, .06, .5, .3, 'oak')
                self.item('書法矮桌', tx, ty, 1.8, .6)
                for k in range(3):
                    self.zabuton(tx + .3 + k * .6, ty + .95, ['linen', 'charlinen', 'linen'][k])
                self.box(tx + .2, ty + .15, .34, .5, .3, .003, 'washi', 'decor'); self.box(tx + .8, ty + .2, .34, .12, .06, .02, 'ink', 'decor')
        for x, y in ((.5, 15.9), (5.9, 8.6)):
            self.floor_lamp(x, y, 1.1)
        self.lantern(3.0, 8.2, 1.6, .4); self.lantern(3.0, 12.0, 1.6, .4)

    def lobby1(self):
        self.at(1, 'Lobby 大廳（東側）')
        self.box(8.3, 10.95, 0, 2.4, .6, 1.0, 'paint', r=.1); self.box(8.25, 10.9, 1.0, 2.5, .7, .05, 'oak', r=.05); self.item('珪藻土接待台', 8.25, 10.9, 2.5, .7)
        self.box(6.7, 8.4, 0, .5, 2.0, .42, 'stone'); self.item('石材長凳', 6.7, 8.4, .5, 2.0)
        self.vessel(9.4, 11.2, 1.05, .3); self.lantern(9.4, 10.0, 1.4, .35)

    def living2(self):
        self.at(2, '客廳兼餐廳')
        self.box(8.1, 7.15, 0, 2.7, 2.2, .008, 'sand', 'decor'); self.item('沙色手織地毯', 8.1, 7.15, 2.7, 2.2, False)
        with self.xf(9.4, 6.1, '+y'):
            self.sofa()
        pts = [(8.8, 7.72), (9.62, 7.6), (10.05, 7.84), (9.9, 8.3), (9.05, 8.36), (8.72, 8.08)]
        self.poly(Polygon(pts), .26, .08, 'oak')
        for x, y in ((8.95, 7.8), (9.8, 7.8), (9.7, 8.2), (8.9, 8.18)):
            self.cyl(x, y, 0, .035, .26, 'oak', sec=10)
        self.item('不規則原木茶几', 8.72, 7.6, 1.33, .76)
        self.vessel(9.4, 8.0, .34, .18, 'glaze', False)
        self.zabuton(8.6, 9.0, 'charlinen'); self.zabuton(10.2, 9.0)
        self.floor_lamp(7.65, 6.4)
        for F in faces(2, 'LIVING', 'full'):
            if F.wall['name'] == 'hall_living' and F.s0 < 2.4 < F.s1:
                self.tokonoma(F, 2.4)
        self.vessel(11.55, 6.45, 0, .55, 'clay')
        self.box(12.1, 8.2, .7, 1.8, .85, .05, 'oak'); self.box(12.2, 8.3, 0, .08, .65, .7, 'oak'); self.box(13.72, 8.3, 0, .08, .65, .7, 'oak'); self.item('橡木餐桌', 12.1, 8.2, 1.8, .85)
        for y in (7.6, 9.25):
            self.box(12.3, y, .42, 1.4, .34, .05, 'oak'); self.box(12.4, y + .04, 0, .06, .26, .42, 'oak'); self.box(13.54, y + .04, 0, .06, .26, .42, 'oak'); self.item('橡木長凳', 12.3, y, 1.4, .34)
        self.lantern(13.0, 8.62, 1.35, .3); self.lantern(9.4, 7.9, 1.1, .45)

    def kitchen2(self):
        self.kitchen('I', 'ash', 'stone', 'paint', 'ash', 'ash', 'box', 'none', handles='groove')
        for i, h in enumerate((.18, .24, .14)):
            self.lathe(13.85 + i * .01, 1.9 + i * .13, .85, [(0, 0), (.05, 0), (.06, h * .6), (.03, h), (0, h)], ['glaze', 'clay', 'linen'][i], 'decor', 14)
        self.lantern(12.9, 2.2, .9, .25)

    def bedrooms(self):
        for f, room, x, y, facing, size in ((2, 'BED1', 1.6, 5.82, '-y', '5'), (2, 'BED2', .15, 10.0, '+x', '5'), (2, 'BED3', 1.21, 16.44, '-y', '6'),
                                            (3, 'BED1', 1.6, 3.9, '-y', '5'), (3, 'BED2', .15, 10.0, '+x', '5')):
            self.at(f, {'BED1': '臥室一', 'BED2': '臥室二', 'BED3': '臥室三'}[room])
            n0 = len(self.items)
            with self.xf(x, y, facing):
                self.platform_bed(*MATTRESS[size])
                self.items[n0].update(category='bed', head_side={'-y': '+y', '+y': '-y', '+x': '-x', '-x': '+x'}[facing], mattress_cm=[round(v * 100) for v in MATTRESS[size]])
                self.floor_lamp(-(MATTRESS[size][0] + .3) / 2 - .3, .3, .55)
            if room == 'BED3':
                self.vessel(5.9, 15.9, 0, .45, 'clay')

    def living3(self):
        self.at(3, '起居室：榻榻米茶室')
        self.box(7.0, 6.1, 0, 2.7, 2.2, .15, 'oak'); self.item('榻榻米平台', 7.0, 6.1, 2.7, 2.2)
        for i in range(3):
            self.box(7.05 + i * .88, 6.15, .15, .86, 2.1, .02, 'tatami')
        self.box(8.0, 7.0, .17, .06, .5, .29, 'oak'); self.box(8.79, 7.0, .17, .06, .5, .29, 'oak'); self.box(7.95, 6.95, .46, .9, .6, .04, 'oak'); self.item('茶几（矮桌）', 7.95, 6.95, .9, .6)
        for x, y in ((8.4, 6.55), (8.4, 7.95), (7.55, 7.25), (9.25, 7.25)):
            self.soft(x - .27, y - .27, .17, .54, .54, .08, 'linen', rounding=.45)
        self.lathe(8.3, 7.25, .5, [(0, 0), (.06, 0), (.07, .06), (.05, .1), (0, .1)], 'glaze', 'decor', 14)
        self.lantern(8.35, 7.25, 1.2, .4); self.vessel(11.8, 6.45, 0, .5, 'clay')

    def worship3(self):
        self.at(3, '佛廳／祭祀空間')
        self.box(.15, 12.35, 0, .7, 2.2, .85, 'oak'); self.box(.18, 12.75, .85, .5, 1.4, .55, 'oak'); self.item('原木神桌＋佛龕（無造像）', .15, 12.35, .7, 2.2)
        self.box(1.05, 12.95, 0, .55, 1.0, .55, 'oak'); self.item('供桌', 1.05, 12.95, .55, 1.0)
        self.lathe(1.32, 13.45, .55, [(0, 0), (.11, 0), (.13, .1), (0, .1)], 'stone'); self.item('石香爐', 1.2, 13.33, .24, .24, False)
        self.zabuton(2.3, 13.45, 'charlinen')

    def terrace4(self):
        self.at(4, '露台')
        self.box(1.0, 8.6, 0, 4.2, 2.7, .1, 'oak'); self.box(1.05, 8.65, .02, 4.1, 2.6, .06, 'gravel', 'decor'); self.item('碎石庭', 1.0, 8.6, 4.2, 2.7, False)
        for x, y in ((1.6, 8.2), (2.3, 8.0), (3.0, 8.25), (3.7, 8.0)):
            self.cyl(x, y, 0, .22, .05, 'stone', 'decor', 12)
        for x, y, r in ((2.0, 9.6, .3), (2.5, 9.9, .18), (4.2, 10.3, .25)):
            self.sphere(x, y, .12, r, 'stone', 'decor', 1, (1.3, 1, .75))
        self.box(4.45, 10.6, .08, .3, .3, .5, 'stone'); self.box(4.35, 10.5, .58, .5, .5, .1, 'stone'); self.box(4.45, 10.6, .68, .3, .3, .25, 'paper'); self.lathe(4.6, 10.75, .93, [(.35, 0), (.02, .22), (0, .24)], 'stone', 'decor', 4)
        self.item('石燈籠', 4.35, 10.5, .5, .5, False)
        self.rod([1.8, 10.3, .1], [1.85, 10.3, 1.4], .05, 'wood', 'decor'); self.rod([1.85, 10.3, 1.2], [1.4, 10.1, 1.8], .03, 'wood', 'decor'); self.rod([1.85, 10.3, 1.3], [2.3, 10.5, 1.9], .03, 'wood', 'decor')
        for cx, cy, cz in ((1.4, 10.1, 1.9), (2.3, 10.5, 2.0), (1.9, 10.3, 2.2), (1.6, 10.6, 1.8)):
            self.sphere(cx, cy, cz, .38, 'moss' if cz > 2 else 'leaf', 'decor', 1, (1.2, 1, .7))
        self.item('楓樹', 1.2, 9.9, 1.3, .9, False)
        self.box(1.2, 7.1, .42, 2.0, .4, .06, 'oak'); self.box(1.3, 7.15, 0, .08, .3, .42, 'oak'); self.box(3.02, 7.15, 0, .08, .3, .42, 'oak'); self.item('杉木長凳', 1.2, 7.1, 2.0, .4)
        self.box(5.4, 6.6, 0, .45, 3.5, .45, 'oak'); self.item('竹子花槽', 5.4, 6.6, .45, 3.5)
        for i in range(12):
            y = 6.8 + i * .28; h = 1.8 + (i % 3) * .3
            self.rod([5.62, y, .4], [5.62 + ((i % 2) - .5) * .1, y, h], .018, 'bamboo', 'decor', 8)
            self.leaves(5.62, y, h - .3, 5, .2, .18, .03, .5, 'leaf2', seed=i)

    def storage4(self):
        self.at(4, '儲藏間'); self.storage_shelves('oak', 'ash', ['linen', 'sand', 'washi'])

    def populate(self):
        self.finishes(); self.gallery1(); self.lobby1(); self.living2(); self.kitchen2(); self.bedrooms()
        self.living3(); self.worship3(); self.storage4(); self.terrace4()


SCHEMES = [Bohemian, Industrial, Eclectic, WabiSabi]
