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


# Pétalos simétricos a distancia 2 del centro (discos tangentes al central).
def _petals(angles_deg: tuple[float, ...], radius: float = 2.0) -> tuple[tuple[float, float], ...]:
    return tuple(
        (radius * math.cos(math.radians(a)), radius * math.sin(math.radians(a)))
        for a in angles_deg
    )


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
    ),
    KnotPreset(
        name="Figure-eight (nudo 4₁)",
        crossings=4,
        disks=((0.0, 0.0),) + _petals((45.0, 135.0, 225.0, 315.0)),
        loops=(((0, 1, 0, 2, 0, 3, 0, 4), (-1, -1, -1, -1, -1, -1, -1, -1)),),
        ribbonlength="—",
        note="Disco central + 4 pétalos tangentes ⇒ 4 cruces.",
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
