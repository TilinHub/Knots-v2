"""Primitivas geométricas: Point y Segment.

Estos tipos son inmutables de facto (dataclasses frozen=True) para garantizar
que puedan usarse como claves de diccionario y en conjuntos cuando sea necesario.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Point:
    """Punto en el plano euclídeo 2D.

    Attributes:
        x: Coordenada horizontal.
        y: Coordenada vertical.
    """

    x: float
    y: float

    def distance_to(self, other: Point) -> float:
        """Distancia euclídea entre este punto y otro."""
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)

    def __add__(self, other: Point) -> Point:
        return Point(self.x + other.x, self.y + other.y)

    def __sub__(self, other: Point) -> Point:
        return Point(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> Point:
        return Point(self.x * scalar, self.y * scalar)

    def norm(self) -> float:
        """Módulo del vector desde el origen hasta este punto."""
        return math.sqrt(self.x ** 2 + self.y ** 2)

    def to_dict(self) -> dict:
        return {"x": self.x, "y": self.y}


@dataclass(frozen=True)
class Segment:
    """Segmento dirigido entre dos puntos A y B.

    Attributes:
        a: Punto inicial.
        b: Punto final.
    """

    a: Point
    b: Point

    def length(self) -> float:
        """Longitud euclídea del segmento."""
        return self.a.distance_to(self.b)

    def midpoint(self) -> Point:
        """Punto medio del segmento."""
        return Point((self.a.x + self.b.x) / 2.0, (self.a.y + self.b.y) / 2.0)

    def direction(self) -> Point:
        """Vector unitario en la dirección A→B. Lanza ZeroDivisionError si la longitud es 0."""
        lng = self.length()
        dx = self.b.x - self.a.x
        dy = self.b.y - self.a.y
        return Point(dx / lng, dy / lng)

    def distance_to_point(self, p: Point) -> float:
        """Distancia mínima desde el punto p hasta este segmento (no a la recta)."""
        lng_sq = (self.b.x - self.a.x) ** 2 + (self.b.y - self.a.y) ** 2
        if lng_sq == 0.0:
            return self.a.distance_to(p)
        # Parámetro t de proyección sobre la recta; lo clampeamos a [0,1]
        t = max(0.0, min(1.0, (
            (p.x - self.a.x) * (self.b.x - self.a.x) +
            (p.y - self.a.y) * (self.b.y - self.a.y)
        ) / lng_sq))
        proj = Point(self.a.x + t * (self.b.x - self.a.x),
                     self.a.y + t * (self.b.y - self.a.y))
        return p.distance_to(proj)

    def to_dict(self) -> dict:
        return {"a": self.a.to_dict(), "b": self.b.to_dict()}
