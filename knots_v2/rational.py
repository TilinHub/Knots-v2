"""Clasificación de nudos racionales (2-puente) por fracción continua de Conway.

Un tangle racional con vector de Conway C(a₁, …, aₙ) tiene una fracción
    p/q = a₁ + 1/(a₂ + 1/(… + 1/aₙ)),
y su cierre numerador es el nudo 2-puente b(p, q). La fracción identifica el
nudo de forma única (a equivalencia 2-puente), de modo que es el invariante
riguroso que usamos para nombrar las construcciones cs (cf. la teoría de
tangles de Conway). El número de cruces del diagrama alternante es Σ aᵢ.
"""

from __future__ import annotations

from fractions import Fraction


def conway_fraction(conway: tuple[int, ...]) -> Fraction:
    """Fracción p/q del tangle racional con vector de Conway dado."""
    value = Fraction(conway[-1])
    for a in reversed(conway[:-1]):
        value = a + 1 / value
    return value


def crossing_number(conway: tuple[int, ...]) -> int:
    """Número de cruces del diagrama alternante (suma del vector de Conway)."""
    return sum(conway)


# Vectores de Conway de los nudos 2-puente hasta 7 cruces (tabla de Rolfsen).
# Cada uno es alternante y minimal: Σ aᵢ = número de cruces.
ROLFSEN_2BRIDGE: dict[str, tuple[int, ...]] = {
    "3_1": (3,),
    "4_1": (2, 2),
    "5_1": (5,),
    "5_2": (3, 2),
    "6_1": (4, 2),
    "6_2": (3, 1, 2),
    "6_3": (2, 1, 1, 2),
    "7_1": (7,),
    "7_2": (5, 2),
    "7_3": (4, 3),
    "7_4": (3, 1, 3),
    "7_5": (3, 2, 2),
    "7_6": (2, 2, 1, 2),
    "7_7": (2, 1, 1, 1, 2),
}


def fraction_label(conway: tuple[int, ...]) -> str:
    """Etiqueta b(p,q) a partir del vector de Conway."""
    f = conway_fraction(conway)
    return f"b({f.numerator},{f.denominator})"
