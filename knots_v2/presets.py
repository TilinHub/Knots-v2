"""Catálogo de nudos/enlaces de referencia (figuras del paper de nudos de cinta).

Reproduce los diagramas cs minimales del paper "Immersed Flat Ribbon Knots"
(Ayala–Kirszenblat–Rubinstein, arXiv:2005.13168), categorizados por número de
cruces. Cada preset fija los centros de los discos y una o más rutas (lazo +
orientaciones por posición) que `build_route` convierte en el núcleo C¹.

Esto es una función *aparte* del editor principal: alimenta la galería de nudos
(ver :mod:`knots_v2.gallery`), no el lienzo interactivo.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .compute.cs_route import build_route
from .domain.primitives import Point

_S = math.sqrt(3.0)


@dataclass(frozen=True)
class KnotPreset:
    """Un nudo/enlace de referencia: discos + lazos (ruta, orientaciones)."""

    name: str
    crossings: int
    disks: tuple[tuple[float, float], ...]
    loops: tuple[tuple[tuple[int, ...], tuple[int, ...]], ...]
    ribbonlength: str = ""   # fórmula del paper (Rib = Longitud / 2)
    note: str = ""
    conway: tuple[int, ...] = ()   # vector de Conway (si es 2-puente racional)

    def fraction(self) -> str:
        """Etiqueta b(p,q) del nudo 2-puente, o '' si no tiene vector de Conway."""
        if not self.conway:
            return ""
        from .rational import fraction_label
        return fraction_label(self.conway)


def _ring(n: int, radius: float) -> tuple[tuple[float, float], ...]:
    """n discos equiespaciados sobre una circunferencia (vértice superior)."""
    return tuple(
        (radius * math.cos(2 * math.pi * k / n + math.pi / 2),
         radius * math.sin(2 * math.pi * k / n + math.pi / 2))
        for k in range(n)
    )


def _star_route(n: int, step: int = 2) -> tuple[int, ...]:
    """Recorrido de polígono estrella {n/step}: el nudo tórico (2,n)."""
    return tuple((step * k) % n for k in range(n))


# ----------------------------------------------------------------------
# Twist knots: dos discos laterales (clasp) + columna central de m discos.
# La ruta sube por la columna, va al lado, baja por la columna y cierra.
# Con tejido alternante produce el twist knot de m+3 cruces (5₂, 6₁, 7₂).
# ----------------------------------------------------------------------

# Separación (vgap vertical, dx lateral) ajustada por m para que el diagrama
# quede lo más compacto posible (bounding box casi cuadrado, no escalera alta).
_TWIST_SPACING: dict[int, tuple[float, float]] = {2: (2.5, 2.2), 3: (2.1, 2.2), 4: (2.3, 3.0)}


def _twist_disks(m: int) -> tuple[tuple[float, float], ...]:
    vgap, dx = _TWIST_SPACING.get(m, (2.2, 2.5))
    column = tuple((0.0, (k - (m - 1) / 2) * vgap) for k in range(m))
    return ((-dx, 0.0),) + column + ((dx, 0.0),)


def _twist_route(m: int) -> tuple[int, ...]:
    last = m + 1  # índice del disco lateral derecho
    return tuple([0] + list(range(1, m + 1)) + [last] + list(range(m, 0, -1)))


def _alt(n: int) -> tuple[int, ...]:
    return tuple((-1) ** i for i in range(n))


PRESETS: tuple[KnotPreset, ...] = (
    KnotPreset(
        name="Unknot (no nudo)",
        crossings=0,
        disks=((0.0, 0.0),),
        loops=(((0,), (1,)),),
        ribbonlength="π",
        note="Un disco; el núcleo es un círculo de radio 1. Longitud 2π.",
    ),
    KnotPreset(
        name="Unknot con torsión",
        crossings=1,
        disks=((-1.6, 0.0), (1.6, 0.0)),
        loops=(((0, 1), (1, -1)),),
        ribbonlength="2+π",
        note="Dos discos; tangentes internas cruzadas ⇒ un cruce (figura-8 trivial).",
    ),
    KnotPreset(
        name="Hopf link",
        crossings=2,
        disks=((-0.6, 0.0), (0.6, 0.0)),
        loops=(((0,), (1,)), ((1,), (1,))),
        ribbonlength="2+π",
        note="Enlace de dos componentes: dos círculos entrelazados (2 cruces).",
    ),
    KnotPreset(
        name="Trefoil (nudo trébol)",
        crossings=3,
        disks=((0.0, 0.0), (0.0, 2.0), (-_S, -1.0), (_S, -1.0)),
        loops=(((0, 1, 0, 2, 0, 3), (-1, -1, -1, -1, -1, -1)),),
        ribbonlength="6+2π",
        note="Disco central + 3 pétalos tangentes. Longitud mínima 12+4π (exacta).",
        conway=(3,),
    ),
    KnotPreset(
        name="Figure-eight 4₁ (twist)",
        crossings=4,
        disks=_twist_disks(2),
        loops=((_twist_route(2), (1, 1, 1, -1, -1, -1)),),
        ribbonlength="—",
        note="Twist knot: clasp + 2 giros ⇒ 4 cruces. Sombra de 4₁.",
        conway=(2, 2),
    ),
    KnotPreset(
        name="Cinquefoil 5₁ (tórico 2,5)",
        crossings=5,
        disks=_ring(5, 2.9),
        loops=((_star_route(5, 2), (1, 1, 1, 1, 1)),),
        ribbonlength="—",
        note="Nudo tórico (2,5) = pentagrama {5/2}. Sombra de 5 cruces; "
             "con la asignación alternante estándar es 5₁.",
        conway=(5,),
    ),
    KnotPreset(
        name="5₂ (twist)",
        crossings=5,
        disks=_twist_disks(2),
        loops=((_twist_route(2), _alt(6)),),
        ribbonlength="—",
        note="Twist knot: clasp + 3 giros ⇒ 5 cruces. Sombra de 5₂.",
        conway=(3, 2),
    ),
    KnotPreset(
        name="6₁ (twist)",
        crossings=6,
        disks=_twist_disks(3),
        loops=((_twist_route(3), _alt(8)),),
        ribbonlength="—",
        note="Twist knot: clasp + 4 giros ⇒ 6 cruces. Sombra de 6₁.",
        conway=(4, 2),
    ),
    KnotPreset(
        name="7₁ (tórico 2,7)",
        crossings=7,
        disks=_ring(7, 5.4),
        loops=((_star_route(7, 2), (1, 1, 1, 1, 1, 1, 1)),),
        ribbonlength="—",
        note="Nudo tórico (2,7) = heptagrama {7/2}. Sombra de 7 cruces; "
             "con la asignación alternante estándar es 7₁.",
        conway=(7,),
    ),
    KnotPreset(
        name="7₂ (twist)",
        crossings=7,
        disks=_twist_disks(4),
        loops=((_twist_route(4), _alt(10)),),
        ribbonlength="—",
        note="Twist knot: clasp + 5 giros ⇒ 7 cruces. Sombra de 7₂.",
        conway=(5, 2),
    ),
)


def build_preset(preset: KnotPreset, radius: float = 1.0) -> dict:
    """Construye las curvas de un preset.

    Returns:
        dict con "centers" (list[Point]), "loops" (list de resultados de
        build_route) y "length" (longitud total del núcleo).
    """
    centers = [Point(x, y) for x, y in preset.disks]
    loops = []
    total = 0.0
    for sequence, orientations in preset.loops:
        res = build_route(centers, radius, list(sequence), list(orientations))
        loops.append(res)
        if res["ok"]:
            total += res["length"]
    return {"centers": centers, "loops": loops, "length": total}


def presets_by_crossings() -> dict[int, list[KnotPreset]]:
    """Agrupa el catálogo por número de cruces (clave ordenable)."""
    groups: dict[int, list[KnotPreset]] = {}
    for p in PRESETS:
        groups.setdefault(p.crossings, []).append(p)
    return dict(sorted(groups.items()))
