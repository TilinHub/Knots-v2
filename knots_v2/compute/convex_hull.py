"""Algoritmo de Convex Hull (Graham Scan) implementado desde cero.

Sin dependencias externas — solo geometría euclídea pura.
"""

from __future__ import annotations

import math

from ..domain.configuration import DiskConfiguration
from ..domain.primitives import Point


class ConvexHull:
    """Calcula el convex hull de un conjunto de discos mediante Graham Scan.

    Los puntos de entrada son muestras de la frontera de cada disco;
    el hull resultante es el polígono convexo más pequeño que contiene
    a todos los discos de la configuración.
    """

    # Número de puntos muestreados por disco en la frontera
    _BOUNDARY_SAMPLES: int = 24

    def compute(self, config: DiskConfiguration) -> list[Point]:
        """Calcula el convex hull de todos los discos en *config*.

        Args:
            config: Configuración de discos sobre la que operar.

        Returns:
            Lista de puntos en orden antihorario que forman el convex hull.
            Lista vacía si no hay discos; lista de 1-2 puntos si los hay muy pocos.
        """
        points = self._sample_boundary_points(config)
        if len(points) < 3:
            return points
        return self._graham_scan(points)

    # ------------------------------------------------------------------
    # Muestreo de fronteras
    # ------------------------------------------------------------------

    def _sample_boundary_points(self, config: DiskConfiguration) -> list[Point]:
        """Genera puntos en las fronteras de todos los discos."""
        points: list[Point] = []
        for disk in config:
            points.extend(disk.boundary_points(self._BOUNDARY_SAMPLES))
        return points

    # ------------------------------------------------------------------
    # Graham Scan
    # ------------------------------------------------------------------

    def _graham_scan(self, points: list[Point]) -> list[Point]:
        """Graham Scan clásico O(n log n).

        1. Encuentra el punto pivote (más bajo; en empate, más a la izquierda).
        2. Ordena los restantes por ángulo polar respecto al pivote.
        3. Recorre manteniendo solo giros a la izquierda (producto cruzado > 0).
        """
        # Eliminar duplicados exactos para evitar artefactos en el ordenamiento
        unique = list({(p.x, p.y): p for p in points}.values())
        if len(unique) < 3:
            return unique

        # Pivote: punto con la coordenada y mínima (desempate por x)
        pivot = min(unique, key=lambda p: (p.y, p.x))

        def _polar_angle(p: Point) -> float:
            return math.atan2(p.y - pivot.y, p.x - pivot.x)

        def _dist_sq(p: Point) -> float:
            return (p.x - pivot.x) ** 2 + (p.y - pivot.y) ** 2

        # Ordenar por ángulo polar; en empate, por distancia al pivote (más cerca primero)
        others = [p for p in unique if p != pivot]
        others.sort(key=lambda p: (_polar_angle(p), _dist_sq(p)))

        hull: list[Point] = [pivot]
        for p in others:
            # Eliminar puntos que crean un giro horario o son colineales
            while len(hull) >= 2 and self._cross(hull[-2], hull[-1], p) <= 0:
                hull.pop()
            hull.append(p)

        return hull

    @staticmethod
    def _cross(o: Point, a: Point, b: Point) -> float:
        """Producto cruzado del vector OA × OB.

        > 0  →  giro antihorario (izquierda)
        = 0  →  colineal
        < 0  →  giro horario (derecha)
        """
        return (a.x - o.x) * (b.y - o.y) - (a.y - o.y) * (b.x - o.x)
