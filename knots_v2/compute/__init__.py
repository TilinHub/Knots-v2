"""Capa de cómputo: algoritmos geométricos puros."""

from .convex_hull import ConvexHull
from .envelope import EnvelopeComputer
from .contact_graph import ContactGraph
from .dubins import DubinsPath

__all__ = ["ConvexHull", "EnvelopeComputer", "ContactGraph", "DubinsPath"]
