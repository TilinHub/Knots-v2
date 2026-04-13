"""Entidad Disk: disco en el plano definido por centro y radio."""

from __future__ import annotations

import math
from dataclasses import dataclass

from .base import GeometricObject
from .primitives import Point


@dataclass
class Disk(GeometricObject):
    """Disco cerrado en R² — región compacta delimitada por una circunferencia.

    Attributes:
        center: Centro del disco.
        radius: Radio (debe ser estrictamente positivo).
    """

    center: Point
    radius: float

    def __post_init__(self) -> None:
        if self.radius <= 0:
            raise ValueError(f"El radio debe ser positivo, se recibió {self.radius}")

    # ------------------------------------------------------------------
    # Relaciones espaciales
    # ------------------------------------------------------------------

    def intersects(self, other: Disk) -> bool:
        """Retorna True si los interiores de ambos discos se solapan."""
        return self.center.distance_to(other.center) < self.radius + other.radius

    def touches(self, other: Disk, epsilon: float = 1e-9) -> bool:
        """Retorna True si los discos se tocan tangencialmente (sin solaparse)."""
        d = self.center.distance_to(other.center)
        return abs(d - (self.radius + other.radius)) <= epsilon

    def distance_to(self, other: Disk) -> float:
        """Distancia entre las fronteras de los dos discos. 0 si se solapan."""
        return max(0.0, self.center.distance_to(other.center) - self.radius - other.radius)

    def contains_point(self, p: Point) -> bool:
        """Retorna True si el punto p pertenece al disco (incluida la frontera)."""
        return self.center.distance_to(p) <= self.radius

    def contains_disk(self, other: Disk) -> bool:
        """Retorna True si *other* está completamente dentro de este disco."""
        return self.center.distance_to(other.center) + other.radius <= self.radius

    # ------------------------------------------------------------------
    # Muestreo de la frontera
    # ------------------------------------------------------------------

    def boundary_points(self, n: int = 32) -> list[Point]:
        """Genera n puntos equidistantes sobre la circunferencia del disco."""
        return [
            Point(
                self.center.x + self.radius * math.cos(2 * math.pi * i / n),
                self.center.y + self.radius * math.sin(2 * math.pi * i / n),
            )
            for i in range(n)
        ]

    # ------------------------------------------------------------------
    # GeometricObject
    # ------------------------------------------------------------------

    def bounding_box(self) -> tuple[float, float, float, float]:
        """Caja delimitadora como (min_x, min_y, max_x, max_y)."""
        return (
            self.center.x - self.radius,
            self.center.y - self.radius,
            self.center.x + self.radius,
            self.center.y + self.radius,
        )

    def to_dict(self) -> dict:
        return {
            "center": {"x": self.center.x, "y": self.center.y},
            "radius": self.radius,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Disk:
        """Reconstruye un Disk desde un diccionario serializado."""
        return cls(
            center=Point(data["center"]["x"], data["center"]["y"]),
            radius=data["radius"],
        )
