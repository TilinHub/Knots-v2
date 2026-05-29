"""Construcción automática de un cs--diagrama a partir de una ruta de discos.

Dada una secuencia cíclica de discos y una orientación de envoltura por disco
(antihoraria σ=+1 o horaria σ=−1), genera el núcleo C¹ del nudo: una
concatenación de segmentos rectos *tangentes* a los discos y arcos de círculo
de radio R que los conectan, tal como se describe en el paper de nudos de
cinta plana (cs ribbon diagrams: arcos de círculos de radio 1 + segmentos).

El segmento entre dos discos es una *tangente común*:
    - externa  si ambos discos se envuelven en el mismo sentido (σ_a = σ_b),
    - interna (cruzada) si se envuelven en sentidos opuestos (σ_a ≠ σ_b),
      lo que produce auto-intersecciones (nudos como el trébol).

Convención: J(x, y) = (−y, x) (rotación de 90° antihoraria). En un punto de
tangencia con normal exterior N, la dirección de viaje al envolver en sentido
antihorario (σ=+1) es J(N); en sentido horario (σ=−1) es −J(N).
"""

from __future__ import annotations

import math

from ..domain.cs_diagram import CsDiagram, DirectedArc, DirectedSegment, TangencyLabel
from ..domain.primitives import Point


def _j(v: Point) -> Point:
    return Point(-v.y, v.x)


def _dot(a: Point, b: Point) -> float:
    return a.x * b.x + a.y * b.y


def _rotate(v: Point, angle: float) -> Point:
    c, s = math.cos(angle), math.sin(angle)
    return Point(v.x * c - v.y * s, v.x * s + v.y * c)


def tangent_points(
    ca: Point,
    cb: Point,
    r: float,
    sa: int,
    sb: int,
) -> tuple[Point, Point] | None:
    """Puntos de tangencia (salida en D_a, llegada en D_b) del segmento común.

    σ_a = σ_b ⇒ tangente externa; σ_a ≠ σ_b ⇒ tangente interna (cruzada).
    Retorna None si la tangente no existe (discos solapados para la interna).
    """
    d_vec = cb - ca
    dist = d_vec.norm()
    if dist < 1e-12:
        return None
    d = d_vec * (1.0 / dist)

    if sa == sb:
        # Tangente externa: normal común N = −σ_a · J(d) (radios iguales).
        normal = _j(d) * float(-sa)
        return ca + normal * r, cb + normal * r

    # Tangente interna: requiere dist ≥ 2R.
    ratio = 2.0 * r / dist
    if ratio > 1.0 + 1e-12:
        return None
    phi = math.acos(max(-1.0, min(1.0, ratio)))
    # Dos normales candidatas (d rotado ±φ); se elige la de avance hacia D_b.
    for sign in (1.0, -1.0):
        normal_a = _rotate(d, sign * phi)
        travel = _j(normal_a) * float(sa)
        if _dot(travel, d) > 0.0:
            ta = ca + normal_a * r
            tb = cb + (normal_a * -1.0) * r
            return ta, tb
    return None


def _point_segment_distance(c: Point, a: Point, b: Point) -> float:
    """Distancia del punto c al segmento ab."""
    ab = b - a
    length_sq = ab.x * ab.x + ab.y * ab.y
    if length_sq < 1e-15:
        return (c - a).norm()
    t = ((c.x - a.x) * ab.x + (c.y - a.y) * ab.y) / length_sq
    t = max(0.0, min(1.0, t))
    proj = Point(a.x + t * ab.x, a.y + t * ab.y)
    return (c - proj).norm()


def _sample_arc(
    center: Point,
    r: float,
    p_from: Point,
    p_to: Point,
    sigma: int,
    min_steps: int = 6,
) -> tuple[list[Point], float]:
    """Muestrea el arco de *p_from* a *p_to* sobre el círculo, en sentido σ."""
    a0 = math.atan2(p_from.y - center.y, p_from.x - center.x)
    a1 = math.atan2(p_to.y - center.y, p_to.x - center.x)
    if sigma > 0:  # antihorario
        sweep = (a1 - a0) % (2.0 * math.pi)
    else:  # horario
        sweep = -((a0 - a1) % (2.0 * math.pi))
    steps = max(min_steps, int(40 * abs(sweep) / (2.0 * math.pi)))
    pts = [
        Point(
            center.x + r * math.cos(a0 + sweep * (k / steps)),
            center.y + r * math.sin(a0 + sweep * (k / steps)),
        )
        for k in range(steps + 1)
    ]
    return pts, r * abs(sweep)


def build_route(
    centers: list[Point],
    r: float,
    sequence: list[int],
    orientations: list[int],
) -> dict:
    """Construye el cs--diagrama de la ruta cíclica dada.

    Args:
        centers: centros de todos los discos.
        r: radio común.
        sequence: índices de disco en orden de recorrido (cíclico).
        orientations: sentido de envoltura (+1 antihorario, −1 horario) por
            posición de *sequence*.

    Returns:
        dict con:
            "ok": bool — si la construcción fue posible,
            "valid": bool — si la ruta no atraviesa discos ajenos,
            "polyline": list[Point] — curva C¹ muestreada para dibujar,
            "length": float — longitud del núcleo (segmentos + arcos),
            "arc_length"/"segment_length": float — descomposición de la longitud,
            "diagram": CsDiagram | None — estructura formal para la 1ª variación.
    """
    empty = {"ok": True, "valid": True, "polyline": [], "length": 0.0,
             "arc_length": 0.0, "segment_length": 0.0, "diagram": None}
    m = len(sequence)
    if m == 0:
        return empty
    if m == 1:
        c = centers[sequence[0]]
        pts = [
            Point(c.x + r * math.cos(2 * math.pi * k / 60), c.y + r * math.sin(2 * math.pi * k / 60))
            for k in range(61)
        ]
        return {**empty, "polyline": pts, "length": 2 * math.pi * r, "arc_length": 2 * math.pi * r}

    tangents: list[tuple[Point, Point] | None] = []
    for i in range(m):
        a, b = sequence[i], sequence[(i + 1) % m]
        tp = tangent_points(centers[a], centers[b], r, orientations[i], orientations[(i + 1) % m])
        tangents.append(tp)
        if tp is None:
            return {**empty, "ok": False, "valid": False}

    polyline: list[Point] = []
    arc_length = 0.0
    segment_length = 0.0
    labels: list[TangencyLabel] = []
    segments: list[DirectedSegment] = []
    arcs: list[DirectedArc] = []

    for i in range(m):
        disk = sequence[i]
        arrival = tangents[(i - 1) % m][1]   # llegada = Tb del borde previo
        departure = tangents[i][0]            # salida = Ta del borde actual
        edge_end = tangents[i][1]             # fin del segmento recto actual

        arc_pts, arc_len = _sample_arc(centers[disk], r, arrival, departure, orientations[i])
        polyline.extend(arc_pts)
        polyline.append(edge_end)
        arc_length += arc_len
        segment_length += (edge_end - departure).norm()

        labels.append(TangencyLabel(f"p{i}i", disk, arrival))
        labels.append(TangencyLabel(f"p{i}o", disk, departure))
        arcs.append(DirectedArc(f"p{i}i", f"p{i}o", disk))

    for i in range(m):
        segments.append(DirectedSegment(f"p{i}o", f"p{(i + 1) % m}i"))

    # Validez geométrica: ningún segmento recto debe atravesar un disco que no
    # sea uno de sus dos extremos (si lo hace, la banda tendría que rodearlo:
    # la ruta no produce un cs--diagrama embebido válido).
    valid = True
    for i in range(m):
        a_disk, b_disk = sequence[i], sequence[(i + 1) % m]
        seg_a, seg_b = tangents[i][0], tangents[i][1]
        for di, center in enumerate(centers):
            if di == a_disk or di == b_disk:
                continue
            if _point_segment_distance(center, seg_a, seg_b) < r - 1e-6:
                valid = False
                break
        if not valid:
            break

    diagram = CsDiagram(labels=labels, segments=segments, arcs=arcs)
    return {
        "ok": True,
        "valid": valid,
        "polyline": polyline,
        "length": arc_length + segment_length,
        "arc_length": arc_length,
        "segment_length": segment_length,
        "diagram": diagram,
    }
