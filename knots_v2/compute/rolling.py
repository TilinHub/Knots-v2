"""Matriz de rodadura A(c) y espacio de rodadura Roll(c) = ker A(c).

El estrato de contacto disco--disco impone restricciones de rodadura
linealizadas sobre las velocidades de los centros δc ∈ R^{2N}. La matriz
A(c) codifica esas restricciones y su núcleo es el espacio de variaciones
admisibles. El núcleo se calcula por SVD (sin scipy).
"""

from __future__ import annotations

import numpy as np

from ..domain.configuration import DiskConfiguration


def build_rolling_matrix(
    config: DiskConfiguration,
    contact_set: set[frozenset[int]],
) -> np.ndarray:
    """Construye A(c) ∈ R^{|E| × 2N} a partir del conjunto de contactos.

    Para cada par {i, j} (con i < j) define u_ij = (c_i − c_j)/‖c_i − c_j‖ y
    coloca u_ij^T en las columnas del disco i y −u_ij^T en las del disco j.
    Las filas se ordenan de forma determinista por (i, j).
    """
    n = len(config)
    pairs = sorted(tuple(sorted(pair)) for pair in contact_set)
    A = np.zeros((len(pairs), 2 * n), dtype=np.float64)
    for row, (i, j) in enumerate(pairs):
        ci, cj = config[i].center, config[j].center
        d = np.array([ci.x - cj.x, ci.y - cj.y], dtype=np.float64)
        norm = float(np.hypot(d[0], d[1]))
        if norm < 1e-15:
            continue
        u = d / norm
        A[row, 2 * i : 2 * i + 2] = u
        A[row, 2 * j : 2 * j + 2] = -u
    return A


def rolling_space_basis(A: np.ndarray, tol: float = 1e-10) -> np.ndarray:
    """Base ortonormal de ker(A) (columnas) calculada por SVD.

    Retorna una matriz K de forma (2N, dim_kernel). Si A no tiene filas,
    Roll(c) = R^{2N} y se devuelve la identidad.
    """
    n = A.shape[1]
    if A.shape[0] == 0:
        return np.eye(n, dtype=np.float64)
    _, s, vh = np.linalg.svd(A, full_matrices=True)
    rank = int(np.sum(s > tol))
    return vh[rank:].conj().T.copy()


def detect_contact_set(
    config: DiskConfiguration,
    epsilon: float = 1e-9,
) -> set[frozenset[int]]:
    """Detecta los pares de discos en contacto tangencial (‖c_i − c_j‖ ≈ r_i + r_j)."""
    disks = list(config)
    contacts: set[frozenset[int]] = set()
    for i in range(len(disks)):
        for j in range(i + 1, len(disks)):
            if disks[i].touches(disks[j], epsilon):
                contacts.add(frozenset({i, j}))
    return contacts


def validate_contact_set(
    config: DiskConfiguration,
    contact_set: set[frozenset[int]],
    epsilon: float = 1e-9,
) -> list[str]:
    """Chequeo A2 del paper: ‖c_i − c_j‖ = r_i + r_j para cada {i, j} ∈ E.

    Retorna lista de errores (vacía si el estrato de contacto es válido).
    """
    n = len(config)
    errors: list[str] = []
    for pair in contact_set:
        i, j = sorted(pair)
        if i < 0 or j >= n:
            errors.append(f"Contacto {{{i}, {j}}}: índice de disco fuera de rango [0, {n - 1}].")
            continue
        di, dj = config[i], config[j]
        dist = di.center.distance_to(dj.center)
        expected = di.radius + dj.radius
        if abs(dist - expected) > epsilon:
            errors.append(
                f"Contacto {{{i}, {j}}}: ‖c_i − c_j‖ = {dist:.6f} ≠ {expected:.6f} "
                "(los discos no están tangentes en el estrato)."
            )
    return errors
