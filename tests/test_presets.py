"""Tests del catálogo de nudos de referencia (presets del paper)."""

import math

import pytest

from knots_v2.presets import PRESETS, build_preset, presets_by_crossings


class TestPresets:
    def test_all_presets_build_ok(self) -> None:
        for preset in PRESETS:
            built = build_preset(preset)
            for res in built["loops"]:
                assert res["ok"], f"{preset.name}: build_route falló"

    def test_unknot_length_is_2pi(self) -> None:
        unknot = next(p for p in PRESETS if p.crossings == 0)
        built = build_preset(unknot)
        assert built["length"] == pytest.approx(2.0 * math.pi, abs=1e-9)

    def test_trefoil_minimal_length_matches_paper(self) -> None:
        """El trefoil reproduce la longitud mínima del paper: 12 + 4π."""
        trefoil = next(p for p in PRESETS if "Trefoil" in p.name)
        built = build_preset(trefoil)
        assert built["length"] == pytest.approx(12.0 + 4.0 * math.pi, abs=1e-6)

    def test_hopf_is_two_components(self) -> None:
        hopf = next(p for p in PRESETS if "Hopf" in p.name)
        assert len(hopf.loops) == 2
        built = build_preset(hopf)
        assert built["length"] == pytest.approx(4.0 * math.pi, abs=1e-9)

    def test_grouped_by_crossings_sorted(self) -> None:
        groups = presets_by_crossings()
        assert list(groups.keys()) == sorted(groups.keys())
        # cubre 0..5 y 7 cruces (tóricos 5₁, 7₁ incluidos)
        assert {0, 1, 2, 3, 4, 5, 7} <= set(groups.keys())

    def test_crossing_numbers_are_documented(self) -> None:
        # cada preset declara su número de cruces
        for preset in PRESETS:
            assert preset.crossings >= 0

    def test_single_loop_knots_have_exact_crossings(self) -> None:
        """Todo nudo de un lazo con segmentos tiene exactamente sus cruces declarados.

        Cubre 3₁, 4₁, 5₁, 5₂, 6₁, 7₁, 7₂ (tóricos y twist knots).
        """
        for preset in PRESETS:
            if len(preset.loops) != 1:
                continue
            res = build_preset(preset)["loops"][0]
            if res["diagram"] is None or not res["diagram"].segments:
                continue  # círculo puro (unknot): sin segmentos
            assert res["ok"] and res["valid"], f"{preset.name}: no válido"
            assert _segment_crossings(res) == preset.crossings, (
                f"{preset.name}: {_segment_crossings(res)} cruces, esperado {preset.crossings}"
            )

    def test_covers_all_crossings_up_to_7(self) -> None:
        """La galería cubre todos los números de cruce de 0 a 7."""
        assert set(presets_by_crossings().keys()) == {0, 1, 2, 3, 4, 5, 6, 7}


def _segment_crossings(res: dict) -> int:
    """Cuenta intersecciones transversales entre los segmentos rectos del diagrama."""
    diagram = res["diagram"]
    pts = {lbl.name: lbl.point for lbl in diagram.labels}
    segs = [(pts[s.start], pts[s.end]) for s in diagram.segments]

    def orient(p, q, r):
        return (q.x - p.x) * (r.y - p.y) - (q.y - p.y) * (r.x - p.x)

    def proper_cross(a, b, c, d):
        o1, o2 = orient(a, b, c), orient(a, b, d)
        o3, o4 = orient(c, d, a), orient(c, d, b)
        return (o1 > 1e-9) != (o2 > 1e-9) and (o3 > 1e-9) != (o4 > 1e-9)

    total = 0
    for i in range(len(segs)):
        for j in range(i + 1, len(segs)):
            a, b = segs[i]
            c, d = segs[j]
            shared = any(abs(p.x - q.x) < 1e-6 and abs(p.y - q.y) < 1e-6
                         for p in (a, b) for q in (c, d))
            if not shared and proper_cross(a, b, c, d):
                total += 1
    return total
