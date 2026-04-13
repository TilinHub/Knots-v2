"""Fixtures reutilizables para todos los tests de Knots v2."""

import pytest

from knots_v2.domain.configuration import DiskConfiguration
from knots_v2.domain.disk import Disk
from knots_v2.domain.primitives import Point, Segment


# ------------------------------------------------------------------
# Primitivas
# ------------------------------------------------------------------

@pytest.fixture
def origin() -> Point:
    """Punto en el origen."""
    return Point(0.0, 0.0)


@pytest.fixture
def unit_segment() -> Segment:
    """Segmento de longitud 1 a lo largo del eje X."""
    return Segment(Point(0.0, 0.0), Point(1.0, 0.0))


# ------------------------------------------------------------------
# Discos individuales
# ------------------------------------------------------------------

@pytest.fixture
def unit_disk() -> Disk:
    """Disco unitario centrado en el origen."""
    return Disk(center=Point(0.0, 0.0), radius=1.0)


@pytest.fixture
def small_disk() -> Disk:
    """Disco pequeño desplazado."""
    return Disk(center=Point(5.0, 5.0), radius=0.5)


# ------------------------------------------------------------------
# Configuraciones de discos
# ------------------------------------------------------------------

@pytest.fixture
def single_disk_config(unit_disk: Disk) -> DiskConfiguration:
    """Configuración con un solo disco unitario."""
    cfg = DiskConfiguration()
    cfg.add_disk(unit_disk)
    return cfg


@pytest.fixture
def two_separate_disks() -> DiskConfiguration:
    """Dos discos separados (sin contacto)."""
    cfg = DiskConfiguration()
    cfg.add_disk(Disk(Point(0.0, 0.0), 1.0))
    cfg.add_disk(Disk(Point(3.0, 0.0), 1.0))
    return cfg


@pytest.fixture
def two_touching_disks() -> DiskConfiguration:
    """Dos discos en contacto tangencial (centros a distancia = suma de radios)."""
    cfg = DiskConfiguration()
    cfg.add_disk(Disk(Point(0.0, 0.0), 1.0))
    cfg.add_disk(Disk(Point(2.0, 0.0), 1.0))
    return cfg


@pytest.fixture
def overlapping_config() -> DiskConfiguration:
    """Configuración inválida: discos superpuestos."""
    cfg = DiskConfiguration()
    cfg.add_disk(Disk(Point(0.0, 0.0), 2.0))
    cfg.add_disk(Disk(Point(1.0, 0.0), 2.0))
    return cfg


@pytest.fixture
def triangle_config() -> DiskConfiguration:
    """Tres discos en disposición triangular, separados."""
    cfg = DiskConfiguration()
    cfg.add_disk(Disk(Point(0.0, 0.0), 1.0))
    cfg.add_disk(Disk(Point(4.0, 0.0), 1.0))
    cfg.add_disk(Disk(Point(2.0, 3.46), 1.0))  # triángulo equilátero aprox.
    return cfg


@pytest.fixture
def dense_config() -> DiskConfiguration:
    """Cuatro discos en cuadrícula 2×2 con radios distintos."""
    cfg = DiskConfiguration()
    cfg.add_disk(Disk(Point(0.0, 0.0), 1.0))
    cfg.add_disk(Disk(Point(3.0, 0.0), 1.0))
    cfg.add_disk(Disk(Point(0.0, 3.0), 1.0))
    cfg.add_disk(Disk(Point(3.0, 3.0), 1.0))
    return cfg
