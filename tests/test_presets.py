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
        # cubre 0..4 cruces
        assert {0, 1, 2, 3, 4} <= set(groups.keys())

    def test_crossing_numbers_are_documented(self) -> None:
        # cada preset declara su número de cruces (valor del paper)
        for preset in PRESETS:
            assert preset.crossings >= 0
