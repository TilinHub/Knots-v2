"""Tests del trazado de nudos desde Gauss codes (diagramas estándar de Rolfsen)."""

from knots_v2.pd_draw import (
    KNOT_GAUSS_CODES,
    _rotation_system,
    _self_crossings,
    _trace_faces,
    knot_layout,
)


class TestGaussCodes:
    def test_each_crossing_appears_twice_signed(self) -> None:
        # Cada cruce k aparece una vez como +k (over) y una como −k (under).
        for name, gauss in KNOT_GAUSS_CODES.items():
            n = len(gauss) // 2
            for k in range(1, n + 1):
                assert gauss.count(k) == 1, f"{name}: falta +{k}"
                assert gauss.count(-k) == 1, f"{name}: falta -{k}"

    def test_all_knots_have_planar_embedding(self) -> None:
        # Todo Gauss code realizable admite un embedding planar (caras = n+2).
        for name, gauss in KNOT_GAUSS_CODES.items():
            if not gauss:
                continue
            n = len(gauss) // 2
            planar = any(
                len(_trace_faces(_rotation_system(gauss, f))) == n + 2
                for f in range(1 << n)
            )
            assert planar, f"{name}: sin embedding planar"

    def test_all_knots_layout_ok(self) -> None:
        for name in KNOT_GAUSS_CODES:
            layout = knot_layout(name)
            assert layout["ok"], f"{name}: knot_layout falló"

    def test_crossing_count_matches(self) -> None:
        for name, gauss in KNOT_GAUSS_CODES.items():
            layout = knot_layout(name)
            assert len(layout["crossings"]) == len(gauss) // 2, name

    def test_curve_is_nonempty(self) -> None:
        for name in KNOT_GAUSS_CODES:
            layout = knot_layout(name)
            assert len(layout["curve"]) >= 2, name

    def test_drawn_curve_has_exactly_n_crossings(self) -> None:
        # El diagrama dibujado no debe tener cruces espurios (curva limpia).
        for name, gauss in KNOT_GAUSS_CODES.items():
            n = len(gauss) // 2
            if n == 0:
                continue
            layout = knot_layout(name)
            assert _self_crossings(layout["curve"]) == n, (
                f"{name}: {_self_crossings(layout['curve'])} cruces dibujados, esperado {n}"
            )

    def test_one_disk_per_bounded_region(self) -> None:
        # El modelo del paper: un disco por región acotada (n+1 para un nudo de
        # n cruces; 1 para el unknot).
        for name, gauss in KNOT_GAUSS_CODES.items():
            layout = knot_layout(name)
            n = len(gauss) // 2
            expected = 0 if n == 0 else n + 1  # unknot: círculo limpio, sin disco
            assert len(layout["regions"]) == expected, name
