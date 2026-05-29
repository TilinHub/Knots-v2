"""Primera variación reducida Φ_seg, gradiente g_red y tests de criticidad.

Implementa el método reducido libre de gauge: el gradiente reducido se ensambla
solo a partir de los segmentos (los arcos no contribuyen al primer orden), y la
estacionariedad en el espacio de rodadura se comprueba por el test de base del
núcleo o por el test del espacio--fila (multiplicadores de Lagrange).
"""

from __future__ import annotations

import numpy as np

from ..domain.configuration import DiskConfiguration
from ..domain.cs_diagram import CsDiagram


def build_gradient(diagram: CsDiagram, config: DiskConfiguration) -> np.ndarray:
    """Ensambla g_red ∈ R^{2N} por actualizaciones de segmento (−v̂ en α, +v̂ en β)."""
    n = len(config)
    g = np.zeros(2 * n, dtype=np.float64)
    for seg in diagram.segments:
        alpha = diagram.label_by_name(seg.start)
        beta = diagram.label_by_name(seg.end)
        pa, pb = alpha.point, beta.point
        v = np.array([pb.x - pa.x, pb.y - pa.y], dtype=np.float64)
        norm = float(np.hypot(v[0], v[1]))
        if norm < 1e-15:
            continue
        v_hat = v / norm
        ka, kb = alpha.disk_idx, beta.disk_idx
        g[2 * ka : 2 * ka + 2] -= v_hat
        g[2 * kb : 2 * kb + 2] += v_hat
    return g


def first_variation(g_red: np.ndarray, delta_c: np.ndarray) -> float:
    """Φ_seg(δc) = g_red^T · δc."""
    return float(g_red @ delta_c)


def is_stationary_kernel(
    g_red: np.ndarray,
    K: np.ndarray,
    tol: float = 1e-9,
) -> tuple[bool, float]:
    """Test de base del núcleo: estacionario ⟺ g_red^T K ≈ 0.

    Retorna (es_estacionario, máximo |componente| de g_red^T K).
    """
    if K.shape[1] == 0:
        return True, 0.0
    residual = g_red @ K
    max_abs = float(np.max(np.abs(residual)))
    return max_abs <= tol, max_abs


def is_stationary_rowspace(
    g_red: np.ndarray,
    A: np.ndarray,
    tol: float = 1e-9,
) -> tuple[bool, np.ndarray | None]:
    """Test del espacio--fila: estacionario ⟺ g_red = A^T λ para algún λ.

    Resuelve λ por mínimos cuadrados. Retorna (es_estacionario, λ o None).
    Si A no tiene filas, estacionario ⟺ g_red ≈ 0.
    """
    if A.shape[0] == 0:
        return float(np.max(np.abs(g_red))) <= tol, None
    lam, *_ = np.linalg.lstsq(A.T, g_red, rcond=None)
    residual = A.T @ lam - g_red
    is_stationary = float(np.max(np.abs(residual))) <= tol
    return is_stationary, (lam if is_stationary else None)


def quadratic_form(
    diagram: CsDiagram,
    config: DiskConfiguration,
    delta_c: np.ndarray,
) -> float:
    """Q_red(δc) = Σ_s ‖P_s (δc_{k(β)} − δc_{k(α)})‖² / ℓ_s, con P_s = I − v̂_s v̂_s^T."""
    total = 0.0
    eye = np.eye(2, dtype=np.float64)
    for seg in diagram.segments:
        alpha = diagram.label_by_name(seg.start)
        beta = diagram.label_by_name(seg.end)
        pa, pb = alpha.point, beta.point
        v = np.array([pb.x - pa.x, pb.y - pa.y], dtype=np.float64)
        ell = float(np.hypot(v[0], v[1]))
        if ell < 1e-15:
            continue
        v_hat = v / ell
        proj = eye - np.outer(v_hat, v_hat)
        ka, kb = alpha.disk_idx, beta.disk_idx
        diff = delta_c[2 * kb : 2 * kb + 2] - delta_c[2 * ka : 2 * ka + 2]
        projected = proj @ diff
        total += float(projected @ projected) / ell
    return total


def quadratic_form_matrix(diagram: CsDiagram, config: DiskConfiguration) -> np.ndarray:
    """Matriz H ∈ R^{2N×2N} (simétrica) tal que Q_red(δc) = δc^T H δc.

    Por segmento s: α→β con bloques a=k(α), b=k(β) y M_s = P_s/ℓ_s, se acumula
    M_s en los bloques (a,a) y (b,b) y −M_s en (a,b) y (b,a).
    """
    n = len(config)
    H = np.zeros((2 * n, 2 * n), dtype=np.float64)
    eye = np.eye(2, dtype=np.float64)
    for seg in diagram.segments:
        alpha = diagram.label_by_name(seg.start)
        beta = diagram.label_by_name(seg.end)
        pa, pb = alpha.point, beta.point
        v = np.array([pb.x - pa.x, pb.y - pa.y], dtype=np.float64)
        ell = float(np.hypot(v[0], v[1]))
        if ell < 1e-15:
            continue
        v_hat = v / ell
        m = (eye - np.outer(v_hat, v_hat)) / ell
        a, b = alpha.disk_idx, beta.disk_idx
        H[2 * a : 2 * a + 2, 2 * a : 2 * a + 2] += m
        H[2 * b : 2 * b + 2, 2 * b : 2 * b + 2] += m
        H[2 * a : 2 * a + 2, 2 * b : 2 * b + 2] -= m
        H[2 * b : 2 * b + 2, 2 * a : 2 * a + 2] -= m
    return H


def is_stable(
    diagram: CsDiagram,
    config: DiskConfiguration,
    K: np.ndarray,
    tol: float = 1e-9,
) -> tuple[bool, float]:
    """Test de estabilidad linealizada (§7): Q_red ≥ 0 sobre Roll(c).

    Restringe la forma a la base K del espacio de rodadura (H_red = K^T H K) y
    comprueba que sea semidefinida positiva. Retorna (es_estable, autovalor_mínimo).
    """
    if K.shape[1] == 0:
        return True, 0.0
    H = quadratic_form_matrix(diagram, config)
    H_red = K.T @ H @ K
    eigenvalues = np.linalg.eigvalsh(0.5 * (H_red + H_red.T))
    min_eig = float(eigenvalues[0])
    return min_eig >= -tol, min_eig
