"""Tests de la clasificación racional (Conway → fracción 2-puente)."""

from fractions import Fraction

from knots_v2.presets import PRESETS
from knots_v2.rational import (
    ROLFSEN_2BRIDGE,
    conway_fraction,
    crossing_number,
    fraction_label,
)


class TestConwayFraction:
    def test_crossing_number_equals_conway_sum(self) -> None:
        # En el diagrama alternante, #cruces = suma del vector de Conway.
        expected = {
            "3_1": 3, "4_1": 4, "5_1": 5, "5_2": 5, "6_1": 6, "6_2": 6, "6_3": 6,
            "7_1": 7, "7_2": 7, "7_3": 7, "7_4": 7, "7_5": 7, "7_6": 7, "7_7": 7,
        }
        for name, conway in ROLFSEN_2BRIDGE.items():
            assert crossing_number(conway) == expected[name], name

    def test_fractions_are_distinct(self) -> None:
        # La fracción p/q identifica unívocamente el nudo 2-puente.
        fracs = [conway_fraction(c) for c in ROLFSEN_2BRIDGE.values()]
        assert len(set(fracs)) == len(fracs)

    def test_known_fractions(self) -> None:
        assert conway_fraction((3,)) == Fraction(3, 1)
        assert conway_fraction((2, 2)) == Fraction(5, 2)      # 4_1
        assert conway_fraction((3, 2)) == Fraction(7, 2)      # 5_2
        assert conway_fraction((3, 1, 2)) == Fraction(11, 3)  # 6_2
        assert conway_fraction((2, 1, 1, 2)) == Fraction(13, 5)  # 6_3

    def test_fraction_label_format(self) -> None:
        assert fraction_label((2, 2)) == "b(5,2)"


class TestPresetConwayConsistency:
    def test_preset_conway_matches_crossings(self) -> None:
        # Cada preset con vector de Conway: Σ aᵢ == número de cruces declarado.
        for preset in PRESETS:
            if preset.conway:
                assert crossing_number(preset.conway) == preset.crossings, preset.name

    def test_preset_fractions_match_rolfsen(self) -> None:
        # Los presets construibles coinciden con su fracción 2-puente de Rolfsen.
        name_by_conway = {v: k for k, v in ROLFSEN_2BRIDGE.items()}
        for preset in PRESETS:
            if preset.conway:
                assert preset.conway in name_by_conway, (
                    f"{preset.name}: Conway {preset.conway} no es 2-puente conocido"
                )
