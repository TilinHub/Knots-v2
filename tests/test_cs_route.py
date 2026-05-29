"""Tests de la construcción automática de cs--diagramas desde una ruta de discos.

Verifica las tangentes comunes (externa/interna), que el stadium reproduce el
Ejemplo 1 del roadmap (longitud 4+2π, g_red=[-2,0,2,0], estacionario), que el
diagrama generado es C¹ por construcción, y que las rutas con orientaciones
opuestas producen tangentes cruzadas.
"""

import math

import numpy.testing as npt
import pytest

from knots_v2.compute.cs_route import build_route, tangent_points
from knots_v2.compute.first_variation import build_gradient
from knots_v2.domain.configuration import DiskConfiguration
from knots_v2.domain.disk import Disk
from knots_v2.domain.primitives import Point


def _config(centers: list[Point], r: float = 1.0) -> DiskConfiguration:
    cfg = DiskConfiguration()
    for c in centers:
        cfg.add_disk(Disk(c, r))
    return cfg


# ----------------------------------------------------------------------
# Tangentes comunes
# ----------------------------------------------------------------------

class TestTangentPoints:
    def test_external_tangent_stadium(self) -> None:
        ta, tb = tangent_points(Point(0, 0), Point(2, 0), 1.0, +1, +1)
        npt.assert_allclose([ta.x, ta.y], [0.0, -1.0], atol=1e-12)
        npt.assert_allclose([tb.x, tb.y], [2.0, -1.0], atol=1e-12)

    def test_external_tangent_other_side(self) -> None:
        ta, tb = tangent_points(Point(0, 0), Point(2, 0), 1.0, -1, -1)
        npt.assert_allclose([ta.x, ta.y], [0.0, 1.0], atol=1e-12)
        npt.assert_allclose([tb.x, tb.y], [2.0, 1.0], atol=1e-12)

    def test_internal_tangent_crosses_midpoint(self) -> None:
        """Para radios iguales, la tangente interna cruza en el punto medio."""
        ta, tb = tangent_points(Point(0, 0), Point(4, 0), 1.0, +1, -1)
        # el segmento ta->tb debe cruzar la recta de centros en x=2, y=0
        t = (0.0 - ta.y) / (tb.y - ta.y)
        x_cross = ta.x + t * (tb.x - ta.x)
        assert x_cross == pytest.approx(2.0, abs=1e-9)
        # tangencia: el segmento es perpendicular al radio en ta
        radius_a = Point(ta.x - 0.0, ta.y - 0.0)
        seg = Point(tb.x - ta.x, tb.y - ta.y)
        assert (radius_a.x * seg.x + radius_a.y * seg.y) == pytest.approx(0.0, abs=1e-9)

    def test_internal_tangent_none_when_overlapping(self) -> None:
        assert tangent_points(Point(0, 0), Point(1.5, 0), 1.0, +1, -1) is None

    def test_overlapping_disks_external_still_defined(self) -> None:
        # la tangente externa existe aunque los discos se toquen/solapen
        assert tangent_points(Point(0, 0), Point(1.0, 0), 1.0, +1, +1) is not None


# ----------------------------------------------------------------------
# build_route: stadium reproduce el Ejemplo 1
# ----------------------------------------------------------------------

class TestBuildRouteStadium:
    def test_length_is_4_plus_2pi(self) -> None:
        res = build_route([Point(0, 0), Point(2, 0)], 1.0, [0, 1], [+1, +1])
        assert res["ok"]
        assert res["length"] == pytest.approx(4.0 + 2.0 * math.pi, abs=1e-9)

    def test_reproduces_example1_gradient(self) -> None:
        centers = [Point(0, 0), Point(2, 0)]
        res = build_route(centers, 1.0, [0, 1], [+1, +1])
        g = build_gradient(res["diagram"], _config(centers))
        npt.assert_allclose(g, [-2.0, 0.0, 2.0, 0.0], atol=1e-9)

    def test_generated_diagram_is_c1(self) -> None:
        centers = [Point(0, 0), Point(2, 0)]
        res = build_route(centers, 1.0, [0, 1], [+1, +1])
        cfg = _config(centers)
        assert res["diagram"].validate_cycle()
        assert res["diagram"].validate_c1(cfg)

    def test_tangency_points_on_boundary(self) -> None:
        centers = [Point(0, 0), Point(2, 0)]
        res = build_route(centers, 1.0, [0, 1], [+1, +1])
        cfg = _config(centers)
        assert res["diagram"].validate_geometry(cfg) == []


# ----------------------------------------------------------------------
# build_route: rutas generales y cruces
# ----------------------------------------------------------------------

class TestBuildRouteGeneral:
    def test_triangle_outer_band_is_c1(self) -> None:
        s = math.sqrt(3.0)
        centers = [Point(0, 0), Point(4, 0), Point(2, 2 * s)]
        res = build_route(centers, 1.0, [0, 1, 2], [+1, +1, +1])
        cfg = _config(centers)
        assert res["ok"]
        assert res["diagram"].validate_c1(cfg)
        # banda exterior: 3 lados + arcos que suman 2π (vuelta completa)
        assert res["length"] > 0.0

    def test_crossing_route_builds_and_is_c1(self) -> None:
        """Orientaciones opuestas ⇒ tangentes internas ⇒ curva con cruces."""
        centers = [Point(-3, 0), Point(3, 0), Point(0, 5)]
        res = build_route(centers, 1.0, [0, 1, 2], [+1, -1, +1])
        cfg = _config(centers)
        assert res["ok"]
        assert res["diagram"].validate_c1(cfg)
        assert len(res["polyline"]) > 3

    def test_single_disk_is_full_circle(self) -> None:
        res = build_route([Point(0, 0)], 1.0, [0], [+1])
        assert res["ok"]
        assert res["length"] == pytest.approx(2.0 * math.pi, abs=1e-9)

    def test_empty_route(self) -> None:
        res = build_route([Point(0, 0)], 1.0, [], [])
        assert res["ok"]
        assert res["polyline"] == []

    def test_arc_lengths_consistent_with_total(self) -> None:
        """La longitud total = suma de segmentos rectos + arcos."""
        centers = [Point(0, 0), Point(3, 0)]
        res = build_route(centers, 1.0, [0, 1], [+1, +1])
        # 2 segmentos de longitud 3 + 2 semicírculos (π cada uno)
        assert res["length"] == pytest.approx(6.0 + 2.0 * math.pi, abs=1e-9)

    def test_length_decomposition(self) -> None:
        """arc_length + segment_length == length (stadium: 2π de arcos, 4 de rectas)."""
        res = build_route([Point(0, 0), Point(2, 0)], 1.0, [0, 1], [+1, +1])
        assert res["arc_length"] == pytest.approx(2.0 * math.pi, abs=1e-9)
        assert res["segment_length"] == pytest.approx(4.0, abs=1e-9)
        assert res["arc_length"] + res["segment_length"] == pytest.approx(res["length"], abs=1e-12)

    def test_valid_route_flag_true(self) -> None:
        s = math.sqrt(3.0)
        centers = [Point(0, 0), Point(0, 2), Point(-s, -1), Point(s, -1)]
        res = build_route(centers, 1.0, [0, 1, 0, 2, 0, 3], [-1] * 6)
        assert res["valid"]

    def test_invalid_when_segment_crosses_foreign_disk(self) -> None:
        """Un disco ajeno que penetra un segmento marca la ruta como no embebida."""
        centers = [Point(0, 0), Point(6, 0), Point(3, 0.5)]  # D2 atraviesa el borde y=1
        res = build_route(centers, 1.0, [0, 1], [+1, +1])
        assert res["ok"]
        assert not res["valid"]
