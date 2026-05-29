"""Tests del método reducido libre de gauge: ejemplos N=2 y N=3 del paper.

Reproduce numéricamente los dos ejemplos del roadmap
(Reduced Gauge-Free Method for cs--Diagrams, R=1): la construcción de A(c),
el gradiente reducido g_red y los tests de estacionariedad.
"""

import math

import numpy as np
import numpy.testing as npt
import pytest

from knots_v2.compute.first_variation import (
    build_gradient,
    first_variation,
    is_stable,
    is_stationary_kernel,
    is_stationary_rowspace,
    quadratic_form,
    quadratic_form_matrix,
)
from knots_v2.compute.rolling import (
    build_rolling_matrix,
    detect_contact_set,
    rolling_space_basis,
    validate_contact_set,
)
from knots_v2.domain.configuration import DiskConfiguration
from knots_v2.domain.cs_diagram import (
    CsDiagram,
    DirectedArc,
    DirectedSegment,
    TangencyLabel,
)
from knots_v2.domain.disk import Disk
from knots_v2.domain.primitives import Point

S = math.sqrt(3.0)


# ----------------------------------------------------------------------
# Constructores de los ejemplos
# ----------------------------------------------------------------------

def _config(*centers: tuple[float, float]) -> DiskConfiguration:
    cfg = DiskConfiguration()
    for x, y in centers:
        cfg.add_disk(Disk(Point(x, y), 1.0))
    return cfg


def example1() -> tuple[DiskConfiguration, CsDiagram, set]:
    """N=2: stadium de dos discos."""
    cfg = _config((0.0, 0.0), (2.0, 0.0))
    diagram = CsDiagram(
        labels=[
            TangencyLabel("alpha", 0, Point(0.0, 1.0)),
            TangencyLabel("beta", 0, Point(0.0, -1.0)),
            TangencyLabel("gamma", 1, Point(2.0, 1.0)),
            TangencyLabel("delta", 1, Point(2.0, -1.0)),
        ],
        segments=[
            DirectedSegment("alpha", "gamma"),
            DirectedSegment("delta", "beta"),
        ],
        arcs=[
            DirectedArc("gamma", "delta", 1),
            DirectedArc("beta", "alpha", 0),
        ],
    )
    contacts = {frozenset({0, 1})}
    return cfg, diagram, contacts


def example2() -> tuple[DiskConfiguration, CsDiagram, set]:
    """N=3: triángulo exterior, sin contactos (E = ∅)."""
    cfg = _config((0.0, 0.0), (3.0, 0.0), (1.5, 1.5 * S))
    diagram = CsDiagram(
        labels=[
            TangencyLabel("alpha", 0, Point(0.0, 1.0)),
            TangencyLabel("beta", 0, Point(S / 2, -0.5)),
            TangencyLabel("gamma", 1, Point(3.0, 1.0)),
            TangencyLabel("delta", 1, Point(3.0 - S / 2, -0.5)),
            TangencyLabel("epsilon", 2, Point(1.5 - S / 2, 1.5 * S - 0.5)),
            TangencyLabel("zeta", 2, Point(1.5 + S / 2, 1.5 * S - 0.5)),
        ],
        segments=[
            DirectedSegment("alpha", "gamma"),
            DirectedSegment("delta", "epsilon"),
            DirectedSegment("zeta", "beta"),
        ],
        arcs=[
            DirectedArc("gamma", "delta", 1),
            DirectedArc("epsilon", "zeta", 2),
            DirectedArc("beta", "alpha", 0),
        ],
    )
    contacts: set = set()
    return cfg, diagram, contacts


# ----------------------------------------------------------------------
# Ejemplo 1: N=2 stadium
# ----------------------------------------------------------------------

class TestExample1Stadium:
    def test_contact_set_detected(self) -> None:
        cfg, _, _ = example1()
        assert detect_contact_set(cfg) == {frozenset({0, 1})}

    def test_rolling_matrix(self) -> None:
        cfg, _, contacts = example1()
        A = build_rolling_matrix(cfg, contacts)
        npt.assert_allclose(A, np.array([[-1.0, 0.0, 1.0, 0.0]]), rtol=1e-10, atol=1e-12)

    def test_gradient(self) -> None:
        cfg, diagram, _ = example1()
        g = build_gradient(diagram, cfg)
        npt.assert_allclose(g, np.array([-2.0, 0.0, 2.0, 0.0]), rtol=1e-10, atol=1e-12)

    def test_stationary_kernel(self) -> None:
        cfg, diagram, contacts = example1()
        A = build_rolling_matrix(cfg, contacts)
        K = rolling_space_basis(A)
        g = build_gradient(diagram, cfg)
        assert K.shape == (4, 3)  # dim ker = 2N − rank = 4 − 1
        is_stat, residual = is_stationary_kernel(g, K)
        assert is_stat
        assert residual < 1e-9

    def test_stationary_rowspace(self) -> None:
        cfg, diagram, contacts = example1()
        A = build_rolling_matrix(cfg, contacts)
        g = build_gradient(diagram, cfg)
        is_stat, lam = is_stationary_rowspace(g, A)
        assert is_stat
        # g_red = A^T λ con λ = [2]
        npt.assert_allclose(lam, np.array([2.0]), rtol=1e-10, atol=1e-12)

    def test_structure_valid(self) -> None:
        cfg, diagram, _ = example1()
        assert diagram.validate_cycle()
        assert diagram.validate_c1(cfg)
        ok, errors = diagram.validate(cfg)
        assert ok and errors == []


# ----------------------------------------------------------------------
# Ejemplo 2: N=3 triángulo exterior
# ----------------------------------------------------------------------

class TestExample2Triangle:
    def test_no_contacts(self) -> None:
        cfg, _, _ = example2()
        assert detect_contact_set(cfg) == set()

    def test_rolling_matrix_empty(self) -> None:
        cfg, _, contacts = example2()
        A = build_rolling_matrix(cfg, contacts)
        assert A.shape == (0, 6)

    def test_gradient(self) -> None:
        cfg, diagram, _ = example2()
        g = build_gradient(diagram, cfg)
        expected = np.array([-1.5, -S / 2, 1.5, -S / 2, 0.0, S])
        npt.assert_allclose(g, expected, rtol=1e-10, atol=1e-12)

    def test_rolling_space_is_full(self) -> None:
        cfg, _, contacts = example2()
        A = build_rolling_matrix(cfg, contacts)
        K = rolling_space_basis(A)
        npt.assert_allclose(K, np.eye(6), rtol=1e-10, atol=1e-12)

    def test_not_stationary_kernel(self) -> None:
        cfg, diagram, contacts = example2()
        A = build_rolling_matrix(cfg, contacts)
        K = rolling_space_basis(A)
        g = build_gradient(diagram, cfg)
        is_stat, residual = is_stationary_kernel(g, K)
        assert not is_stat
        assert residual > 1e-6

    def test_not_stationary_rowspace(self) -> None:
        cfg, diagram, contacts = example2()
        A = build_rolling_matrix(cfg, contacts)
        g = build_gradient(diagram, cfg)
        is_stat, lam = is_stationary_rowspace(g, A)
        assert not is_stat
        assert lam is None

    def test_structure_valid(self) -> None:
        cfg, diagram, _ = example2()
        assert diagram.validate_cycle()
        assert diagram.validate_c1(cfg)
        ok, errors = diagram.validate(cfg)
        assert ok and errors == []


# ----------------------------------------------------------------------
# Propiedades generales
# ----------------------------------------------------------------------

class TestFirstVariationProperties:
    def test_first_variation_matches_dot(self) -> None:
        cfg, diagram, _ = example1()
        g = build_gradient(diagram, cfg)
        dc = np.array([1.0, 2.0, 3.0, 4.0])
        assert first_variation(g, dc) == pytest.approx(float(g @ dc))

    def test_first_variation_vanishes_on_kernel(self) -> None:
        """Φ_seg(δc) = 0 para toda variación admisible δc ∈ Roll(c) (estacionario)."""
        cfg, diagram, contacts = example1()
        A = build_rolling_matrix(cfg, contacts)
        K = rolling_space_basis(A)
        g = build_gradient(diagram, cfg)
        for col in range(K.shape[1]):
            assert first_variation(g, K[:, col]) == pytest.approx(0.0, abs=1e-9)

    def test_quadratic_form_nonnegative(self) -> None:
        cfg, diagram, _ = example1()
        rng = np.random.default_rng(0)
        for _ in range(20):
            dc = rng.standard_normal(2 * len(cfg))
            assert quadratic_form(diagram, cfg, dc) >= -1e-12

    def test_quadratic_form_zero_on_translation(self) -> None:
        """Una traslación global no estira ningún segmento: Q_red = 0."""
        cfg, diagram, _ = example1()
        n = len(cfg)
        dc = np.tile([1.0, 0.0], n)  # misma velocidad para todos los centros
        assert quadratic_form(diagram, cfg, dc) == pytest.approx(0.0, abs=1e-12)

    def test_quadratic_form_matrix_matches_pointwise(self) -> None:
        """δc^T H δc == Q_red(δc) para vectores aleatorios (ambos ejemplos)."""
        rng = np.random.default_rng(1)
        for builder in (example1, example2):
            cfg, diagram, _ = builder()
            H = quadratic_form_matrix(diagram, cfg)
            npt.assert_allclose(H, H.T, rtol=1e-12, atol=1e-12)  # simétrica
            for _ in range(10):
                dc = rng.standard_normal(2 * len(cfg))
                assert float(dc @ H @ dc) == pytest.approx(
                    quadratic_form(diagram, cfg, dc), abs=1e-9
                )

    def test_stability_form_is_psd(self) -> None:
        """Q_red es suma de cuadrados ⇒ semidefinida positiva sobre Roll(c) (§7 «safe»)."""
        for builder in (example1, example2):
            cfg, diagram, contacts = builder()
            A = build_rolling_matrix(cfg, contacts)
            K = rolling_space_basis(A)
            stable, min_eig = is_stable(diagram, cfg, K)
            assert stable
            assert min_eig >= -1e-9


# ----------------------------------------------------------------------
# Validez del estrato de contacto (A2) y geometría (A3)
# ----------------------------------------------------------------------

class TestContactStratumValidity:
    def test_valid_stratum_no_errors(self) -> None:
        cfg, _, contacts = example1()
        assert validate_contact_set(cfg, contacts) == []

    def test_invalid_stratum_detected(self) -> None:
        """Un contacto declarado entre discos NO tangentes debe reportar error."""
        cfg, _, _ = example2()  # discos a distancia 3, no 2
        bad = {frozenset({0, 1})}
        errors = validate_contact_set(cfg, bad)
        assert errors and "no están tangentes" in errors[0]

    def test_out_of_range_index(self) -> None:
        cfg, _, _ = example1()
        errors = validate_contact_set(cfg, {frozenset({0, 5})})
        assert errors and "fuera de rango" in errors[0]


class TestDiagramGeometryValidity:
    def test_point_off_boundary_detected(self) -> None:
        cfg, diagram, _ = example1()
        diagram.labels.append(TangencyLabel("bad", 0, Point(5.0, 5.0)))
        errors = diagram.validate_geometry(cfg)
        assert any("no está en" in e for e in errors)

    def test_arc_disk_mismatch_detected(self) -> None:
        cfg, diagram, _ = example1()
        # 'alpha' pertenece a D0, pero declaramos un arco suyo sobre D1
        diagram.arcs.append(DirectedArc("alpha", "gamma", 1))
        errors = diagram.validate_geometry(cfg)
        assert any("pertenece a D0" in e for e in errors)

    def test_examples_pass_full_validation(self) -> None:
        for builder in (example1, example2):
            cfg, diagram, _ = builder()
            ok, errors = diagram.validate(cfg)
            assert ok and errors == []
