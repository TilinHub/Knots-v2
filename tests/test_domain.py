"""Tests para la capa domain: primitivas, discos y configuraciones."""

import math
import pytest

from knots_v2.domain.base import GeometricObject
from knots_v2.domain.configuration import DiskConfiguration
from knots_v2.domain.disk import Disk
from knots_v2.domain.primitives import Point, Segment


# ==================================================================
# Point
# ==================================================================

class TestPoint:
    def test_distance_to_same_point(self, origin: Point) -> None:
        assert origin.distance_to(Point(0.0, 0.0)) == 0.0

    def test_distance_pythagorean(self, origin: Point) -> None:
        assert origin.distance_to(Point(3.0, 4.0)) == pytest.approx(5.0)

    def test_distance_symmetry(self) -> None:
        a, b = Point(1.0, 2.0), Point(4.0, 6.0)
        assert a.distance_to(b) == pytest.approx(b.distance_to(a))

    def test_addition(self) -> None:
        assert Point(1.0, 2.0) + Point(3.0, 4.0) == Point(4.0, 6.0)

    def test_subtraction(self) -> None:
        assert Point(5.0, 3.0) - Point(2.0, 1.0) == Point(3.0, 2.0)

    def test_scalar_multiplication(self) -> None:
        assert Point(2.0, 3.0) * 2.0 == Point(4.0, 6.0)

    def test_norm(self) -> None:
        assert Point(3.0, 4.0).norm() == pytest.approx(5.0)

    def test_frozen_immutability(self, origin: Point) -> None:
        with pytest.raises((AttributeError, TypeError)):
            origin.x = 99.0  # type: ignore[misc]

    def test_to_dict(self) -> None:
        p = Point(1.5, -2.5)
        d = p.to_dict()
        assert d == {"x": 1.5, "y": -2.5}


# ==================================================================
# Segment
# ==================================================================

class TestSegment:
    def test_length_unit(self, unit_segment: Segment) -> None:
        assert unit_segment.length() == pytest.approx(1.0)

    def test_length_345(self) -> None:
        s = Segment(Point(0.0, 0.0), Point(3.0, 4.0))
        assert s.length() == pytest.approx(5.0)

    def test_midpoint(self, unit_segment: Segment) -> None:
        assert unit_segment.midpoint() == Point(0.5, 0.0)

    def test_direction_unit(self, unit_segment: Segment) -> None:
        d = unit_segment.direction()
        assert d.x == pytest.approx(1.0)
        assert d.y == pytest.approx(0.0)

    def test_distance_to_point_on_segment(self, unit_segment: Segment) -> None:
        # Punto directamente encima del segmento
        assert unit_segment.distance_to_point(Point(0.5, 1.0)) == pytest.approx(1.0)

    def test_distance_to_point_endpoint(self, unit_segment: Segment) -> None:
        # Punto más allá del extremo B → distancia al extremo B
        p = Point(2.0, 0.0)
        assert unit_segment.distance_to_point(p) == pytest.approx(1.0)

    def test_to_dict(self) -> None:
        s = Segment(Point(0.0, 0.0), Point(1.0, 0.0))
        d = s.to_dict()
        assert "a" in d and "b" in d


# ==================================================================
# Disk
# ==================================================================

class TestDisk:
    def test_invalid_radius_raises(self) -> None:
        with pytest.raises(ValueError):
            Disk(Point(0.0, 0.0), -1.0)

    def test_bounding_box(self, unit_disk: Disk) -> None:
        assert unit_disk.bounding_box() == (-1.0, -1.0, 1.0, 1.0)

    def test_contains_center(self, unit_disk: Disk) -> None:
        assert unit_disk.contains_point(Point(0.0, 0.0))

    def test_contains_boundary_point(self, unit_disk: Disk) -> None:
        assert unit_disk.contains_point(Point(1.0, 0.0))

    def test_not_contains_exterior(self, unit_disk: Disk) -> None:
        assert not unit_disk.contains_point(Point(2.0, 0.0))

    def test_intersects_overlapping(self) -> None:
        d1 = Disk(Point(0.0, 0.0), 1.0)
        d2 = Disk(Point(1.0, 0.0), 1.0)
        assert d1.intersects(d2)

    def test_not_intersects_separated(self) -> None:
        d1 = Disk(Point(0.0, 0.0), 1.0)
        d2 = Disk(Point(5.0, 0.0), 1.0)
        assert not d1.intersects(d2)

    def test_touches_tangential(self) -> None:
        d1 = Disk(Point(0.0, 0.0), 1.0)
        d2 = Disk(Point(2.0, 0.0), 1.0)
        assert d1.touches(d2)

    def test_distance_to_disjoint(self) -> None:
        d1 = Disk(Point(0.0, 0.0), 1.0)
        d2 = Disk(Point(4.0, 0.0), 1.0)
        assert d1.distance_to(d2) == pytest.approx(2.0)

    def test_distance_to_overlapping_is_zero(self) -> None:
        d1 = Disk(Point(0.0, 0.0), 2.0)
        d2 = Disk(Point(1.0, 0.0), 2.0)
        assert d1.distance_to(d2) == pytest.approx(0.0)

    def test_contains_disk(self) -> None:
        outer = Disk(Point(0.0, 0.0), 5.0)
        inner = Disk(Point(1.0, 0.0), 1.0)
        assert outer.contains_disk(inner)
        assert not inner.contains_disk(outer)

    def test_boundary_points_count(self, unit_disk: Disk) -> None:
        pts = unit_disk.boundary_points(n=32)
        assert len(pts) == 32

    def test_boundary_points_on_circle(self, unit_disk: Disk) -> None:
        for p in unit_disk.boundary_points(n=16):
            assert unit_disk.center.distance_to(p) == pytest.approx(1.0, abs=1e-10)

    def test_to_dict_roundtrip(self, unit_disk: Disk) -> None:
        d = unit_disk.to_dict()
        recovered = Disk.from_dict(d)
        assert recovered.radius == unit_disk.radius
        assert recovered.center == unit_disk.center

    def test_is_geometric_object(self, unit_disk: Disk) -> None:
        assert isinstance(unit_disk, GeometricObject)


# ==================================================================
# DiskConfiguration
# ==================================================================

class TestDiskConfiguration:
    def test_empty_length(self) -> None:
        cfg = DiskConfiguration()
        assert len(cfg) == 0

    def test_add_increases_length(self, unit_disk: Disk) -> None:
        cfg = DiskConfiguration()
        cfg.add_disk(unit_disk)
        assert len(cfg) == 1

    def test_remove_decreases_length(self, two_separate_disks: DiskConfiguration) -> None:
        two_separate_disks.remove_disk(0)
        assert len(two_separate_disks) == 1

    def test_remove_invalid_index_raises(self, unit_disk: Disk) -> None:
        cfg = DiskConfiguration()
        cfg.add_disk(unit_disk)
        with pytest.raises(IndexError):
            cfg.remove_disk(5)

    def test_iter_yields_disks(self, two_separate_disks: DiskConfiguration) -> None:
        disks = list(two_separate_disks)
        assert len(disks) == 2
        assert all(isinstance(d, Disk) for d in disks)

    def test_getitem(self, two_separate_disks: DiskConfiguration) -> None:
        first = two_separate_disks[0]
        assert isinstance(first, Disk)

    def test_validate_valid(self, two_separate_disks: DiskConfiguration) -> None:
        assert two_separate_disks.validate() is True

    def test_validate_invalid(self, overlapping_config: DiskConfiguration) -> None:
        assert overlapping_config.validate() is False

    def test_validate_touching_is_valid(self, two_touching_disks: DiskConfiguration) -> None:
        # El contacto tangencial NO es superposición
        assert two_touching_disks.validate() is True

    def test_bounding_box_none_when_empty(self) -> None:
        cfg = DiskConfiguration()
        assert cfg.bounding_box() is None

    def test_bounding_box_single_disk(self, unit_disk: Disk) -> None:
        cfg = DiskConfiguration()
        cfg.add_disk(unit_disk)
        assert cfg.bounding_box() == (-1.0, -1.0, 1.0, 1.0)

    def test_to_dict_roundtrip(self, triangle_config: DiskConfiguration) -> None:
        d = triangle_config.to_dict()
        recovered = DiskConfiguration.from_dict(d)
        assert len(recovered) == len(triangle_config)

    def test_clear(self, triangle_config: DiskConfiguration) -> None:
        triangle_config.clear()
        assert len(triangle_config) == 0
