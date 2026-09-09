"""Local procedural geometry helpers for softer furniture forms.

Pure geometry only: no material, texture, lighting or placement logic (the
main controller owns those). Everything returns a trimesh.Trimesh centred on
the origin so callers can translate it exactly like a primitive box.
"""
import numpy as np
import trimesh as tm


def _surface(X, Y, Z):
    rows, cols = X.shape
    V = np.column_stack([X.ravel(), Y.ravel(), Z.ravel()])
    F = []
    for i in range(rows - 1):
        for j in range(cols - 1):
            a = i * cols + j
            b = i * cols + j + 1
            c = (i + 1) * cols + j
            dd = (i + 1) * cols + j + 1
            F.append([a, b, dd])
            F.append([a, dd, c])
    m = tm.Trimesh(V, np.array(F), process=True)
    m.update_faces(m.nondegenerate_faces())
    if m.volume < 0: m.invert()
    return m


def _pw(a, m):
    """Signed power used by the superellipsoid parameterisation."""
    return np.sign(a) * (np.abs(a) ** m)


def cushion(size, rounding=0.45, sections=18, seam=True):
    """Soft parametric superellipsoid cushion with an optional edge seam.

    ``rounding`` in ~(0.2 boxy .. 1.0 ellipsoid); ``size`` is full w,d,h.
    """
    w, d, h = size
    e = float(np.clip(rounding, 0.12, 1.0))
    u = np.linspace(-np.pi / 2, np.pi / 2, sections)
    v = np.linspace(-np.pi, np.pi, 2 * sections)
    U, Vv = np.meshgrid(u, v)
    cu, su = _pw(np.cos(U), e), _pw(np.sin(U), e)
    cv, sv = _pw(np.cos(Vv), e), _pw(np.sin(Vv), e)
    X = (w / 2.0) * cu * cv
    Y = (d / 2.0) * cu * sv
    Z = (h / 2.0) * su
    mesh = _surface(X, Y, Z)
    if seam:
        # Two-millimetre piping follows the same cushion outline; a scaled
        # circular torus would protrude beyond the approved furniture footprint.
        theta=np.linspace(-np.pi,np.pi,2*sections+1)
        phi=np.linspace(0,2*np.pi,7)
        cx=(w/2-.003)*_pw(np.cos(theta),e)
        cy=(d/2-.003)*_pw(np.sin(theta),e)
        radial=np.column_stack([cx,cy]);radial/=np.linalg.norm(radial,axis=1)[:,None]
        X=cx[:,None]+.002*radial[:,0,None]*np.cos(phi)
        Y=cy[:,None]+.002*radial[:,1,None]*np.cos(phi)
        Z=np.broadcast_to(.002*np.sin(phi),X.shape)
        mesh=tm.util.concatenate([mesh,_surface(X,Y,Z)])
    return mesh


def rounded_box(size, radius=0.05, steps=2):
    """Box with smoothly rounded edges (convex hull of corner spheres)."""
    w, d, h = size
    r = max(1e-3, min(radius, w / 2 - 1e-3, d / 2 - 1e-3, h / 2 - 1e-3))
    sph = tm.creation.icosphere(subdivisions=steps, radius=r)
    parts = []
    for x in (-w / 2 + r, w / 2 - r):
        for y in (-d / 2 + r, d / 2 - r):
            for z in (-h / 2 + r, h / 2 - r):
                s = sph.copy()
                s.apply_translation([x, y, z])
                parts.append(s)
    return tm.util.concatenate(parts).convex_hull


def puffy_slab(w, d, h, nx=22, ny=16, folds=3):
    """A duvet/throw-like solid: domed top with soft folds, flat underside."""
    xs = np.linspace(0, w, nx)
    ys = np.linspace(0, d, ny)
    X, Y = np.meshgrid(xs, ys)
    edge = np.sin(np.pi * np.clip(X / max(w, 1e-6), 0, 1)) * np.sin(np.pi * np.clip(Y / max(d, 1e-6), 0, 1))
    ripple = 0.16 * h * np.sin(folds * np.pi * X / max(w, 1e-6)) * np.cos(1.3 * np.pi * Y / max(d, 1e-6))
    Z = h * (0.32 + 0.68 * edge) + ripple * edge
    top = np.column_stack([X.ravel(), Y.ravel(), Z.ravel()])
    bot = np.column_stack([X.ravel(), Y.ravel(), np.zeros(X.size)])
    V = np.vstack([top, bot])
    N = X.size
    idx = lambda i, j: i * nx + j
    F = []
    for i in range(ny - 1):
        for j in range(nx - 1):
            a, b, c, dd = idx(i, j), idx(i, j + 1), idx(i + 1, j), idx(i + 1, j + 1)
            F += [[a, b, dd], [a, dd, c]]
            F += [[N + a, N + dd, N + b], [N + a, N + c, N + dd]]
    for j in range(nx - 1):
        a, b = idx(0, j), idx(0, j + 1)
        F += [[a, N + a, b], [b, N + a, N + b]]
        a, b = idx(ny - 1, j), idx(ny - 1, j + 1)
        F += [[a, b, N + a], [b, N + b, N + a]]
    for i in range(ny - 1):
        a, b = idx(i, 0), idx(i + 1, 0)
        F += [[a, b, N + a], [b, N + b, N + a]]
        a, b = idx(i, nx - 1), idx(i + 1, nx - 1)
        F += [[a, N + a, b], [b, N + a, N + b]]
    m = tm.Trimesh(V, np.array(F), process=True)
    m.apply_translation([-w / 2.0, -d / 2.0, 0.0])
    return m


def leaf(length=0.15, width=0.05, droop=0.5, fold=0.16, sections=9):
    """Curved tapered leaf blade along +X, drooping in -Z, with a mid-rib fold."""
    t = np.linspace(0.0, 1.0, sections)
    hw = np.sin(np.pi * np.clip(t, 0, 1) ** 0.7) * (width / 2.0)
    xs = length * t
    zc = -droop * length * t ** 2
    L = np.column_stack([xs, -hw, zc + fold * hw])
    R = np.column_stack([xs, hw, zc + fold * hw])
    C = np.column_stack([xs, np.zeros(sections), zc])
    V = np.vstack([L, R, C])
    n = sections
    F = []
    for i in range(n - 1):
        cL, cLn = i, i + 1
        cR, cRn = n + i, n + i + 1
        cC, cCn = 2 * n + i, 2 * n + i + 1
        F += [[cL, cC, cLn], [cLn, cC, cCn], [cC, cR, cCn], [cCn, cR, cRn]]
    return tm.Trimesh(V, np.array(F), process=True)
