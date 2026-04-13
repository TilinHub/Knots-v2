"""Capa de dominio: tipos de valor y entidades del problema geométrico."""

from .primitives import Point, Segment
from .disk import Disk
from .configuration import DiskConfiguration

__all__ = ["Point", "Segment", "Disk", "DiskConfiguration"]
