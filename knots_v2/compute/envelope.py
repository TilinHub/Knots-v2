"""Cálculo de la envolvente elástica (elastic envelope) de una configuración de discos.

El algoritmo principal genera la "frontera exterior" de la unión de discos:
solo conserva los arcos de la frontera de cada disco que no quedan cubiertos
por ningún otro disco. Si algo falla, cae al ConvexHull como respaldo.
"""

from __future__ import annotations

import logging
import math

from ..domain.configuration import DiskConfiguration
from ..domain.primitives import Point
from .convex_hull import ConvexHull

logger = logging.getLogger(__name__)


class EnvelopeComputer:
    """Calcula la envolvente exterior de la unión de discos.

    Algoritmo principal:
        Para cada disco D_i, muestrea su frontera con alta densidad y retiene
        solo los puntos que no están en el interior de ningún otro disco.
        El conjunto resultante se ordena mediante Graham Scan para obtener
        un polígono convexo simplificado de la envolvente.

    Fallback:
        Si la configuración está vacía, tiene un solo disco, o el algoritmo
        principal no produce suficientes puntos, se usa :class:`ConvexHull`.
    """

    _BOUNDARY_SAMPLES: int = 64  # mayor densidad que el hull para mayor precisión

    def compute(self, config: DiskConfiguration) -> list[Point]:
        """Calcula la envolvente de *config*.

        Args:
            config: Configuración de discos.

        Returns:
            Lista de puntos que aproximan la frontera exterior de la unión.
        """
        try:
            if len(config) == 0:
                raise ValueError("La configuración no contiene discos.")
            result = self._elastic_envelope(config)
            if len(result) < 3:
                raise ValueError(
                    f"El algoritmo de envolvente produjo solo {len(result)} punto(s)."
                )
            return result
        except Exception as exc:
            logger.warning(
                "EnvelopeComputer: usando ConvexHull como fallback. Causa: %s", exc
            )
            return ConvexHull().compute(config)

    # ------------------------------------------------------------------
    # Algoritmo principal
    # ------------------------------------------------------------------

    def _elastic_envelope(self, config: DiskConfiguration) -> list[Point]:
        """Retorna los puntos de frontera expuestos (no cubiertos por otros discos)."""
        disks = list(config)
        exterior_points: list[Point] = []

        for disk in disks:
            for i in range(self._BOUNDARY_SAMPLES):
                angle = 2 * math.pi * i / self._BOUNDARY_SAMPLES
                px = disk.center.x + disk.radius * math.cos(angle)
                py = disk.center.y + disk.radius * math.sin(angle)
                p = Point(px, py)

                # El punto pertenece a la envolvente si ningún OTRO disco lo contiene
                # (se usa un pequeño margen para puntos en la frontera de dos discos)
                covered = any(
                    other is not disk and other.center.distance_to(p) < other.radius - 1e-9
                    for other in disks
                )
                if not covered:
                    exterior_points.append(p)

        if len(exterior_points) < 3:
            return exterior_points

        # Usar Graham Scan para ordenar los puntos exteriores en orden convexo
        return ConvexHull()._graham_scan(exterior_points)
