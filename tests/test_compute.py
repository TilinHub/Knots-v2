"""Tests para la capa compute: convex hull, envolvente, grafo de contacto y Dubins."""

import math
import pytest

from knots_v2.compute.contact_graph import ContactGraph
from knots_v2.compute.convex_hull import ConvexHull
from knots_v2.compute.dubins import DubinsPath
from knots_v2.compute.envelope import EnvelopeComputer
from knots_v2.domain.configuration import DiskConfiguration
from knots_v2.domain.disk import Disk
from knots_v2.domain.primitives import Point


# ==================================================================
# ConvexHull
# ==================================================================

class TestConvexHull:
    def test_empty_config_returns_empty(self) -> None:
        cfg = DiskConfiguration()
        hull = ConvexHull().compute(cfg)
        assert hull == []

    def test_single_disk_returns_points(self, single_disk_config: DiskConfiguration) -> None:
        hull = ConvexHull().compute(single_disk_config)
        assert len(hull) >= 3

    def test_triangle_returns_polygon(self, triangle_config: DiskConfiguration) -> None:
        hull = ConvexHull().compute(triangle_config)
        assert len(hull) >= 3

    def test_all_results_are_points(self, dense_config: DiskConfiguration) -> None:
        hull = ConvexHull().compute(dense_config)
        assert all(isinstance(p, Point) for p in hull)

    def test_hull_points_on_boundary(self, single_disk_config: DiskConfiguration) -> None:
        """Todos los puntos del hull deben estar sobre la frontera del disco."""
        disk = single_disk_config[0]
        hull = ConvexHull().compute(single_disk_config)
        for p in hull:
            dist = disk.center.distance_to(p)
            assert abs(dist - disk.radius) < 1e-9

    def test_cross_product_left_turn(self) -> None:
        """El producto cruzado debe ser positivo para un giro a la izquierda."""
        o = Point(0.0, 0.0)
        a = Point(1.0, 0.0)
        b = Point(1.0, 1.0)
        assert ConvexHull._cross(o, a, b) > 0

    def test_cross_product_right_turn(self) -> None:
        o = Point(0.0, 0.0)
        a = Point(1.0, 0.0)
        b = Point(1.0, -1.0)
        assert ConvexHull._cross(o, a, b) < 0

    def test_hull_is_convex(self, triangle_config: DiskConfiguration) -> None:
        """Verificar que el hull resultante sea convexo (todos los giros son positivos)."""
        hull = ConvexHull().compute(triangle_config)
        n = len(hull)
        if n < 3:
            pytest.skip("Hull demasiado pequeño para verificar convexidad")
        for i in range(n):
            o = hull[i]
            a = hull[(i + 1) % n]
            b = hull[(i + 2) % n]
            # En un polígono convexo todos los productos cruzados tienen el mismo signo
            assert ConvexHull._cross(o, a, b) >= 0


# ==================================================================
# EnvelopeComputer
# ==================================================================

class TestEnvelopeComputer:
    def test_empty_config_uses_fallback(self) -> None:
        cfg = DiskConfiguration()
        # No debe lanzar excepción; retorna lista vacía via fallback
        pts = EnvelopeComputer().compute(cfg)
        assert isinstance(pts, list)

    def test_single_disk_returns_points(self, single_disk_config: DiskConfiguration) -> None:
        pts = EnvelopeComputer().compute(single_disk_config)
        assert len(pts) >= 3

    def test_returns_point_instances(self, two_separate_disks: DiskConfiguration) -> None:
        pts = EnvelopeComputer().compute(two_separate_disks)
        assert all(isinstance(p, Point) for p in pts)

    def test_more_disks_more_envelope_points(
        self,
        single_disk_config: DiskConfiguration,
        triangle_config: DiskConfiguration,
    ) -> None:
        pts_single = EnvelopeComputer().compute(single_disk_config)
        pts_tri = EnvelopeComputer().compute(triangle_config)
        # La configuración de tres discos debe producir más puntos de envolvente
        assert len(pts_tri) >= len(pts_single)

    def test_overlapping_config_uses_fallback(
        self, overlapping_config: DiskConfiguration
    ) -> None:
        # Con discos superpuestos el algoritmo principal sigue funcionando
        pts = EnvelopeComputer().compute(overlapping_config)
        assert isinstance(pts, list)

    def test_envelope_points_not_inside_any_disk(
        self, two_separate_disks: DiskConfiguration
    ) -> None:
        """Los puntos de la envolvente no deben estar en el interior de ningún disco."""
        pts = EnvelopeComputer().compute(two_separate_disks)
        disks = list(two_separate_disks)
        for p in pts:
            # Ningún disco debe contener estrictamente el punto
            for disk in disks:
                assert not (disk.center.distance_to(p) < disk.radius - 1e-6), (
                    f"Punto {p} está en el interior del disco {disk}"
                )


# ==================================================================
# ContactGraph
# ==================================================================

class TestContactGraph:
    def test_empty_config_empty_graph(self) -> None:
        cfg = DiskConfiguration()
        graph = ContactGraph().from_config(cfg)
        assert graph == {}

    def test_single_disk_no_contacts(self, single_disk_config: DiskConfiguration) -> None:
        graph = ContactGraph().from_config(single_disk_config)
        assert graph == {0: []}

    def test_separated_disks_no_contact(self, two_separate_disks: DiskConfiguration) -> None:
        graph = ContactGraph().from_config(two_separate_disks)
        assert graph[0] == []
        assert graph[1] == []

    def test_touching_disks_in_contact(self, two_touching_disks: DiskConfiguration) -> None:
        graph = ContactGraph().from_config(two_touching_disks)
        assert 1 in graph[0]
        assert 0 in graph[1]

    def test_graph_is_symmetric(self, triangle_config: DiskConfiguration) -> None:
        graph = ContactGraph().from_config(triangle_config)
        for i, neighbors in graph.items():
            for j in neighbors:
                assert i in graph[j], f"Grafo asimétrico: {j}→{i} falta"

    def test_all_keys_present(self, dense_config: DiskConfiguration) -> None:
        graph = ContactGraph().from_config(dense_config)
        assert set(graph.keys()) == {0, 1, 2, 3}

    def test_connected_components_single(
        self, single_disk_config: DiskConfiguration
    ) -> None:
        components = ContactGraph().connected_components(single_disk_config)
        assert len(components) == 1

    def test_connected_components_two_separate(
        self, two_separate_disks: DiskConfiguration
    ) -> None:
        components = ContactGraph().connected_components(two_separate_disks)
        assert len(components) == 2

    def test_adjacency_matrix_shape(self, triangle_config: DiskConfiguration) -> None:
        matrix = ContactGraph().adjacency_matrix(triangle_config)
        assert len(matrix) == 3
        assert all(len(row) == 3 for row in matrix)


# ==================================================================
# DubinsPath
# ==================================================================

class TestDubinsPath:
    def test_invalid_radius_raises(self) -> None:
        with pytest.raises(ValueError):
            DubinsPath().compute(
                Disk(Point(0.0, 0.0), 1.0),
                Disk(Point(5.0, 0.0), 1.0),
                turning_radius=0.0,
            )

    def test_returns_nonempty_list(self) -> None:
        path = DubinsPath().compute(
            Disk(Point(0.0, 0.0), 1.0),
            Disk(Point(10.0, 0.0), 1.0),
            turning_radius=2.0,
        )
        assert len(path) > 0

    def test_all_points_are_points(self) -> None:
        path = DubinsPath().compute(
            Disk(Point(0.0, 0.0), 1.0),
            Disk(Point(8.0, 0.0), 1.0),
            turning_radius=1.5,
        )
        assert all(isinstance(p, Point) for p in path)

    def test_first_point_near_start(self) -> None:
        start = Disk(Point(0.0, 0.0), 1.0)
        path = DubinsPath().compute(start, Disk(Point(10.0, 0.0), 1.0), turning_radius=2.0)
        # El primer punto del camino debe estar relativamente cerca del inicio
        first = path[0]
        assert first.distance_to(start.center) < 10.0

    def test_diagonal_path(self) -> None:
        path = DubinsPath().compute(
            Disk(Point(0.0, 0.0), 0.5),
            Disk(Point(5.0, 5.0), 0.5),
            turning_radius=1.0,
        )
        assert len(path) > 0

    def test_same_position_returns_path(self) -> None:
        # Inicio y fin en el mismo punto
        disk = Disk(Point(0.0, 0.0), 1.0)
        path = DubinsPath().compute(disk, disk, turning_radius=1.0)
        assert isinstance(path, list)
