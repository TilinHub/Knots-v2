"""Interfaces abstractas del dominio geométrico."""

from abc import ABC, abstractmethod


class GeometricObject(ABC):
    """Clase base abstracta para todos los objetos geométricos del sistema.

    Define el contrato mínimo que deben cumplir las entidades del dominio:
    poder calcular su caja delimitadora y serializarse a diccionario.
    """

    @abstractmethod
    def bounding_box(self) -> tuple[float, float, float, float]:
        """Retorna la caja delimitadora (min_x, min_y, max_x, max_y)."""
        ...

    @abstractmethod
    def to_dict(self) -> dict:
        """Serializa el objeto a un diccionario plano compatible con JSON."""
        ...
