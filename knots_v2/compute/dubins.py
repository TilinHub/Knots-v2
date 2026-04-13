"""Camino de Dubins entre dos discos.

Un camino de Dubins es el trayecto más corto para un vehículo con radio de
giro mínimo (curvatura máxima fija). Este módulo implementa el caso LSL
(Left-Straight-Left) que es el más habitual para dos discos alineados.

Referencias:
    Dubins, L.E. (1957). "On curves of minimal length with a constraint
    on average curvature." American Journal of Mathematics, 79(3), 497–516.
"""

from __future__ import annotations

import math

from ..domain.disk import Disk
from ..domain.primitives import Point

# Número de puntos por arco al samplear la curva
_ARC_POINTS: int = 20


class DubinsPath:
    """Calcula caminos de Dubins entre pares de discos.

    El "inicio" y el "fin" del camino son los centros de los discos dados.
    La orientación inicial y final se infiere del vector que une ambos centros.
    """

    def compute(
        self, start: Disk, end: Disk, turning_radius: float
    ) -> list[Point]:
        """Calcula el camino LSL de Dubins de *start* a *end*.

        Args:
            start: Disco de origen (su centro es el punto de partida).
            end: Disco de destino (su centro es el punto final).
            turning_radius: Radio mínimo de giro del vehículo. Debe ser > 0.

        Returns:
            Lista de puntos que aproximan la trayectoria óptima LSL.

        Raises:
            ValueError: si *turning_radius* ≤ 0.
        """
        if turning_radius <= 0:
            raise ValueError(f"El radio de giro debe ser positivo, se recibió {turning_radius}")

        sx, sy = start.center.x, start.center.y
        ex, ey = end.center.x, end.center.y

        # La orientación inicial/final se alinea con el vector de inicio a fin
        heading = math.atan2(ey - sy, ex - sx)

        return self._lsl(sx, sy, heading, ex, ey, heading, turning_radius)

    # ------------------------------------------------------------------
    # Caso LSL
    # ------------------------------------------------------------------

    def _lsl(
        self,
        sx: float, sy: float, sa: float,
        ex: float, ey: float, ea: float,
        r: float,
    ) -> list[Point]:
        """Construye el camino LSL dado inicio (sx,sy,sa) y fin (ex,ey,ea).

        LSL = arco izquierdo + segmento recto + arco izquierdo.
        """
        # Centros de los círculos de giro izquierdo
        # El centro izquierdo desde un punto (x,y,θ) es (x - r·sin θ, y + r·cos θ)
        cx1 = sx - r * math.sin(sa)
        cy1 = sy + r * math.cos(sa)

        cx2 = ex - r * math.sin(ea)
        cy2 = ey + r * math.cos(ea)

        d = math.hypot(cx2 - cx1, cy2 - cy1)

        if d < 1e-10:
            # Los centros coinciden: solo hace falta girar en el mismo círculo
            arc_start = sa - math.pi / 2
            arc_end = ea - math.pi / 2
            return self._arc_points(cx1, cy1, r, arc_start, arc_end, left=True)

        # Ángulo de la tangente externa entre los dos círculos
        theta = math.atan2(cy2 - cy1, cx2 - cx1)

        # Puntos de tangencia sobre cada círculo
        # El punto de tangencia desde el centro C en dirección θ
        # (perpendicular a la tangente exterior para círculos del mismo radio)
        t1 = Point(cx1 + r * math.sin(theta), cy1 - r * math.cos(theta))
        t2 = Point(cx2 + r * math.sin(theta), cy2 - r * math.cos(theta))

        # --- Arco 1: desde posición inicial hasta t1 ---
        arc1_start = sa - math.pi / 2
        arc1_end = theta - math.pi / 2
        arc1 = self._arc_points(cx1, cy1, r, arc1_start, arc1_end, left=True)

        # --- Segmento recto: de t1 a t2 ---
        straight_len = t1.distance_to(t2)
        n_straight = max(2, int(straight_len / r * 10))
        straight = [
            Point(
                t1.x + (t2.x - t1.x) * i / n_straight,
                t1.y + (t2.y - t1.y) * i / n_straight,
            )
            for i in range(n_straight + 1)
        ]

        # --- Arco 2: desde t2 hasta posición final ---
        arc2_start = theta - math.pi / 2
        arc2_end = ea - math.pi / 2
        arc2 = self._arc_points(cx2, cy2, r, arc2_start, arc2_end, left=True)

        return arc1 + straight + arc2

    # ------------------------------------------------------------------
    # Utilidades de arco
    # ------------------------------------------------------------------

    def _arc_points(
        self,
        cx: float, cy: float, r: float,
        start_angle: float, end_angle: float,
        left: bool,
        n: int = _ARC_POINTS,
    ) -> list[Point]:
        """Muestrea n+1 puntos sobre un arco circular.

        Args:
            cx, cy: Centro del círculo.
            r: Radio.
            start_angle: Ángulo inicial (radianes).
            end_angle: Ángulo final (radianes).
            left: Si True, el arco recorre en sentido antihorario (ángulo creciente).
            n: Número de subdivisiones.
        """
        if left:
            # Antihorario: end_angle debe ser ≥ start_angle
            while end_angle < start_angle:
                end_angle += 2 * math.pi
        else:
            # Horario: end_angle debe ser ≤ start_angle
            while end_angle > start_angle:
                end_angle -= 2 * math.pi

        return [
            Point(
                cx + r * math.cos(start_angle + (end_angle - start_angle) * i / n),
                cy + r * math.sin(start_angle + (end_angle - start_angle) * i / n),
            )
            for i in range(n + 1)
        ]
