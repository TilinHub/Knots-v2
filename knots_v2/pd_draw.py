"""Trazado de nudos a partir de Gauss codes (diagramas estándar de Rolfsen).

Dibujamos el diagrama estándar de cada nudo:
  1. el Gauss code da la secuencia de cruces con over/under (signo) al recorrer
     el nudo; de ahí se reconstruye el grafo 4--valente (cruces + arcos),
  2. se subdivide cada arco con un punto medio y se busca un embedding planar
     (sistema de rotación con la handedness correcta por cruce ⇒ caras = n+2),
  3. se ubican los nodos con el embedding de Tutte (baricéntrico),
  4. se traza una curva suave (Catmull--Rom) y se dibuja over/under.

Gauss code: lista de 2n enteros ±k; +k = paso POR ENCIMA del cruce k, −k = por
debajo. Cada cruce aparece una vez con cada signo.
"""

from __future__ import annotations

import math

KNOT_GAUSS_CODES: dict[str, list[int]] = {
    "0_1": [],
    "3_1": [-1, 3, -2, 1, -3, 2],
    "4_1": [1, -3, 4, -2, 3, -4, 2, -1],
    "5_1": [1, -2, 3, -4, 5, -1, 2, -3, 4, -5],
    "5_2": [1, -2, 5, -4, 3, -1, 2, -5, 4, -3],
    "6_1": [1, -4, 3, -6, 5, -2, 6, -1, 4, -3, 2, -5],
    "6_2": [1, -4, 5, -2, 3, -6, 4, -1, 6, -5, 2, -3],
    "6_3": [1, -4, 3, -2, 5, -6, 4, -3, 2, -1, 6, -5],
    "7_1": [1, -2, 3, -4, 5, -6, 7, -1, 2, -3, 4, -5, 6, -7],
    "7_2": [1, -2, 7, -6, 5, -4, 3, -1, 2, -7, 6, -5, 4, -3],
    "7_3": [1, -2, 5, -6, 3, -4, 7, -1, 2, -3, 6, -5, 4, -7],
    "7_4": [1, -4, 7, -6, 3, -2, 5, -1, 4, -7, 6, -5, 2, -3],
    "7_5": [1, -4, 3, -6, 7, -2, 5, -1, 4, -3, 6, -7, 2, -5],
    "7_6": [1, -2, 5, -4, 7, -6, 3, -1, 2, -5, 4, -7, 6, -3],
    "7_7": [1, -2, 3, -4, 5, -6, 2, -1, 7, -3, 4, -5, 6, -7],
}


def _rotation_system(gauss: list[int], flips: int) -> dict[int, list[int]]:
    """Rotación del grafo subdividido para una handedness por cruce (*flips*).

    Nodos: 0..n-1 cruces; n..n+2n-1 puntos medios (arco i → nodo n+i, donde el
    arco i une la visita i con la i+1). La hebra over (a–c) y la under (b–d) se
    interleavan; el bit i de *flips* invierte la handedness del cruce i.
    """
    n = len(gauss) // 2
    length = len(gauss)
    visits = [(abs(g) - 1, g > 0) for g in gauss]
    over_pos: dict[int, int] = {}
    under_pos: dict[int, int] = {}
    for i, (ci, is_over) in enumerate(visits):
        (over_pos if is_over else under_pos)[ci] = i

    rot: dict[int, list[int]] = {}
    for k in range(n):
        i, j = over_pos[k], under_pos[k]
        over_in, over_out = n + (i - 1) % length, n + i
        under_in, under_out = n + (j - 1) % length, n + j
        if (flips >> k) & 1:
            rot[k] = [over_in, under_out, over_out, under_in]
        else:
            rot[k] = [over_in, under_in, over_out, under_out]
    for i in range(length):
        rot[n + i] = [visits[i][0], visits[(i + 1) % length][0]]
    return rot


def _trace_faces(rot: dict[int, list[int]]) -> list[list[int]]:
    def nxt(u: int, v: int) -> tuple[int, int]:
        r = rot[v]
        return v, r[(r.index(u) - 1) % len(r)]

    seen: set[tuple[int, int]] = set()
    faces: list[list[int]] = []
    for u in rot:
        for v in rot[u]:
            if (u, v) in seen:
                continue
            face: list[int] = []
            cur = (u, v)
            while cur not in seen:
                seen.add(cur)
                face.append(cur[0])
                cur = nxt(*cur)
            faces.append(face)
    return faces


def _tutte(rot: dict[int, list[int]], outer: list[int], iters: int = 500) -> dict[int, list[float]]:
    pos = {node: [0.0, 0.0] for node in rot}
    fixed = set(outer)
    for i, node in enumerate(outer):
        ang = 2 * math.pi * i / len(outer)
        pos[node] = [math.cos(ang), math.sin(ang)]
    interior = [node for node in rot if node not in fixed]
    for _ in range(iters):
        for node in interior:
            nbrs = rot[node]
            pos[node][0] = sum(pos[m][0] for m in nbrs) / len(nbrs)
            pos[node][1] = sum(pos[m][1] for m in nbrs) / len(nbrs)
    return pos


def _catmull_rom(pts: list[list[float]], samples: int) -> list[tuple[float, float]]:
    m = len(pts)
    curve: list[tuple[float, float]] = []
    for i in range(m):
        p0, p1, p2, p3 = pts[(i - 1) % m], pts[i], pts[(i + 1) % m], pts[(i + 2) % m]
        for s in range(samples):
            t = s / samples
            t2, t3 = t * t, t * t * t
            x = 0.5 * (2 * p1[0] + (-p0[0] + p2[0]) * t +
                       (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 +
                       (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3)
            y = 0.5 * (2 * p1[1] + (-p0[1] + p2[1]) * t +
                       (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 +
                       (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)
            curve.append((x, y))
    return curve


# Nudos tóricos T(2,q): se trazan con fórmula paramétrica (forma canónica exacta).
KNOT_PARAMETRIC: dict[str, tuple[int, int]] = {"3_1": (2, 3), "5_1": (2, 5), "7_1": (2, 7)}


def _torus_curve(p: int, q: int, n: int = 600) -> list[tuple[float, float]]:
    """Proyección 2D del nudo tórico T(p,q): r=cos(q t)+2, (r cos p t, r sin p t)."""
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        r = math.cos(q * t) + 2
        pts.append((r * math.cos(p * t), r * math.sin(p * t)))
    return pts


def _seg_intersect(p1, p2, p3, p4):
    (x1, y1), (x2, y2), (x3, y3), (x4, y4) = p1, p2, p3, p4
    den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(den) < 1e-12:
        return None
    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / den
    u = ((x1 - x3) * (y1 - y2) - (y1 - y3) * (x1 - x2)) / den
    if 0 <= t <= 1 and 0 <= u <= 1:
        return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))
    return None


def _find_self_crossings(curve):
    """Autointersecciones de la polilínea cerrada: lista de (punto, i, j), i<j."""
    n = len(curve)
    res = []
    for i in range(n):
        a, b = curve[i], curve[(i + 1) % n]
        for j in range(i + 2, n):
            if i == 0 and j == n - 1:
                continue
            x = _seg_intersect(a, b, curve[j], curve[(j + 1) % n])
            if x:
                res.append((x, i, j))
    return res


def _geometric_regions(curve, crossings_raw):
    """Discos en cada región acotada de una curva auto-intersectante."""
    big = len(curve)
    n = len(crossings_raw)
    if n == 0:
        return [(0.0, 0.0, 0.5)]
    passes = []
    for ci, (_, i, j) in enumerate(crossings_raw):
        passes.append((i, ci))
        passes.append((j, ci))
    passes.sort()
    length = len(passes)
    cross_pt = [crossings_raw[ci][0] for ci in range(n)]
    pass_of_cross: dict[int, list[tuple[int, int]]] = {}
    for s, (p, ci) in enumerate(passes):
        pass_of_cross.setdefault(ci, []).append((s, p))

    def arc_mid(k):
        a, b = passes[k][0], passes[(k + 1) % length][0]
        if b <= a:
            b += big
        return curve[((a + b) // 2) % big]

    rot: dict[int, list[int]] = {}
    for ci in range(n):
        (s1, i), (s2, j) = pass_of_cross[ci]
        px, py = cross_pt[ci]
        ends = [
            (n + (s1 - 1) % length, curve[i]),
            (n + s1, curve[(i + 1) % big]),
            (n + (s2 - 1) % length, curve[j]),
            (n + s2, curve[(j + 1) % big]),
        ]
        ends.sort(key=lambda e: math.atan2(e[1][1] - py, e[1][0] - px))
        rot[ci] = [e[0] for e in ends]
    for k in range(length):
        rot[n + k] = [passes[k][1], passes[(k + 1) % length][1]]

    node_pos = {ci: cross_pt[ci] for ci in range(n)}
    for k in range(length):
        node_pos[n + k] = arc_mid(k)

    def area(face):
        ps = [node_pos[x] for x in face]
        s = sum(ps[a][0] * ps[(a + 1) % len(ps)][1] - ps[(a + 1) % len(ps)][0] * ps[a][1]
                for a in range(len(ps)))
        return abs(s) / 2

    faces = _trace_faces(rot)
    outer = max(faces, key=area)
    regions = []
    for face in faces:
        if face is outer:
            continue
        ps = [node_pos[x] for x in face]
        cx = sum(p[0] for p in ps) / len(ps)
        cy = sum(p[1] for p in ps) / len(ps)
        rad = 0.42 * min(math.hypot(p[0] - cx, p[1] - cy) for p in ps)
        regions.append((cx, cy, max(rad, 0.05)))
    return regions


def _torus_layout(p: int, q: int) -> dict:
    """Trazado canónico de T(p,q) por fórmula paramétrica + over/under (t menor = encima)."""
    curve = _torus_curve(p, q)
    raw = _find_self_crossings(curve)
    crossings = [
        {"pos": pt, "over_sample": i, "under_sample": j}  # menor índice (t menor) = encima
        for (pt, i, j) in raw
    ]
    return {"ok": True, "curve": curve, "crossings": crossings,
            "regions": _geometric_regions(curve, raw), "samples": 10, "n": len(crossings)}


def knot_layout(name: str, samples: int = 16) -> dict:
    """Trazado del nudo *name*: curva suave + posiciones/muestras de los cruces."""
    if name in KNOT_PARAMETRIC:
        return _torus_layout(*KNOT_PARAMETRIC[name])
    gauss = KNOT_GAUSS_CODES[name]
    if not gauss:
        circle = [(math.cos(2 * math.pi * i / 80), math.sin(2 * math.pi * i / 80)) for i in range(80)]
        return {"ok": True, "curve": circle, "crossings": [],
                "regions": [(0.0, 0.0, 0.5)], "samples": 80, "n": 0}

    n = len(gauss) // 2
    length = len(gauss)
    visits = [(abs(g) - 1, g > 0) for g in gauss]
    seq: list[int] = []
    for i in range(length):
        seq.append(visits[i][0])
        seq.append(n + i)

    rot = None
    faces: list[list[int]] = []
    for flips in range(1 << n):
        candidate = _rotation_system(gauss, flips)
        faces = _trace_faces(candidate)
        if len(faces) == n + 2:
            rot = candidate
            break
    if rot is None:
        return {"ok": False, "curve": [], "crossings": [], "regions": [], "samples": samples, "n": n}

    # Probar cada cara como externa y quedarse con el layout que más separa los
    # cruces (evita diagramas amontonados / "bolita").
    def spread_score(positions: dict[int, list[float]]) -> float:
        cps = [positions[k] for k in range(n)]
        xs = [p[0] for p in cps]
        ys = [p[1] for p in cps]
        diag = math.hypot(max(xs) - min(xs), max(ys) - min(ys)) + 1e-9
        return min(
            math.hypot(cps[i][0] - cps[j][0], cps[i][1] - cps[j][1])
            for i in range(n) for j in range(i + 1, n)
        ) / diag if n >= 2 else 1.0

    outer = max(faces, key=len)
    pos = _tutte(rot, outer)
    best = spread_score(pos)
    for cand in faces:
        cand_pos = _tutte(rot, cand)
        score = spread_score(cand_pos)
        if score > best:
            best, outer, pos = score, cand, cand_pos

    # Un disco por región acotada (cara distinta de la externa): el modelo del
    # paper pone un disco unidad en cada región complementaria.
    regions: list[tuple[float, float, float]] = []
    for face in faces:
        if face == outer:
            continue
        pts_f = [pos[node] for node in face]
        cx = sum(p[0] for p in pts_f) / len(pts_f)
        cy = sum(p[1] for p in pts_f) / len(pts_f)
        rad = 0.42 * min(math.hypot(p[0] - cx, p[1] - cy) for p in pts_f)
        regions.append((cx, cy, max(rad, 0.05)))

    curve = _catmull_rom([pos[node] for node in seq], samples)
    over_pos = {ci: i for i, (ci, is_over) in enumerate(visits) if is_over}
    under_pos = {ci: i for i, (ci, is_over) in enumerate(visits) if not is_over}
    crossings = [
        {
            "pos": tuple(pos[k]),
            "over_sample": (2 * over_pos[k] * samples) % len(curve),
            "under_sample": (2 * under_pos[k] * samples) % len(curve),
        }
        for k in range(n)
    ]
    return {"ok": True, "curve": curve, "crossings": crossings,
            "regions": regions, "samples": samples, "n": n}


def draw_on_canvas(canvas, layout: dict, w: int, h: int, pad: int = 18,
                   color: str = "#1f6feb", bg: str = "#ffffff", width: int = 5) -> None:
    """Dibuja el nudo en un canvas tkinter con cruces over/under (auto-ajuste)."""
    curve = layout["curve"]
    if len(curve) < 2:
        return
    xs = [p[0] for p in curve]
    ys = [p[1] for p in curve]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    scale = min((w - 2 * pad) / max(1e-6, maxx - minx), (h - 2 * pad) / max(1e-6, maxy - miny))
    ox = (w - (maxx - minx) * scale) / 2
    oy = (h - (maxy - miny) * scale) / 2

    def tx(p):
        return ox + (p[0] - minx) * scale, h - (oy + (p[1] - miny) * scale)

    pts = [tx(p) for p in curve]

    def polyline(seg):
        flat = [c for p in seg for c in p]
        canvas.create_line(flat, fill=color, width=width, joinstyle="round",
                           capstyle="round", smooth=True)

    # Discos en cada región (modelo del paper), detrás de la curva.
    for cx0, cy0, r0 in layout.get("regions", []):
        cx, cy = tx((cx0, cy0))
        rr = r0 * scale
        canvas.create_oval(cx - rr, cy - rr, cx + rr, cy + rr,
                           fill="#dce9fb", outline="#9bbbe6")

    polyline(pts + [pts[0]])
    r = width + 4
    half = max(2, layout["samples"] - 2)
    m = len(pts)
    for cr in layout["crossings"]:
        cx, cy = tx(cr["pos"])
        canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill=bg, outline=bg)
        s = cr["over_sample"]
        polyline([pts[(s + i) % m] for i in range(-half, half + 1)])
