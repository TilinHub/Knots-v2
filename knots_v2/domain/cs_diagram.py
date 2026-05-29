"""cs--diagrama dirigido: etiquetas de tangencia, segmentos y arcos.

Un cs--diagrama es una curva cerrada del plano formada por segmentos rectos
tangentes a discos unitarios y arcos circulares sobre la frontera de los discos.
Este módulo define los datos combinatorios/geométricos (T, S, A) y las
comprobaciones estructurales (CYCLE) y (C1) del método reducido libre de gauge.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .configuration import DiskConfiguration
from .primitives import Point

_TOL: float = 1e-9


# ----------------------------------------------------------------------
# Utilidades vectoriales 2D (sin numpy: la capa de dominio es liviana)
# ----------------------------------------------------------------------

def _dot(a: Point, b: Point) -> float:
    return a.x * b.x + a.y * b.y


def _perp(v: Point) -> Point:
    """Rotación J de 90° antihoraria: J(x, y) = (-y, x)."""
    return Point(-v.y, v.x)


def _normalize(v: Point) -> Point:
    n = v.norm()
    return v if n < _TOL else v * (1.0 / n)


# ----------------------------------------------------------------------
# Datos del cs--diagrama
# ----------------------------------------------------------------------

@dataclass(frozen=True)
class TangencyLabel:
    """Etiqueta de tangencia α: punto p_α sobre la frontera del disco k(α)."""

    name: str
    disk_idx: int
    point: Point


@dataclass
class DirectedSegment:
    """Segmento dirigido s: α→β entre dos etiquetas de tangencia."""

    start: str
    end: str


@dataclass
class DirectedArc:
    """Arco dirigido a: α→β sobre la frontera del disco *disk_idx*."""

    start: str
    end: str
    disk_idx: int


@dataclass
class CsDiagram:
    """cs--diagrama dirigido: etiquetas T, segmentos S y arcos A."""

    labels: list[TangencyLabel] = field(default_factory=list)
    segments: list[DirectedSegment] = field(default_factory=list)
    arcs: list[DirectedArc] = field(default_factory=list)

    def label_by_name(self, name: str) -> TangencyLabel:
        """Retorna la etiqueta de tangencia con el nombre dado."""
        for lbl in self.labels:
            if lbl.name == name:
                return lbl
        raise KeyError(f"Etiqueta de tangencia desconocida: {name!r}")

    # ------------------------------------------------------------------
    # Comprobaciones estructurales
    # ------------------------------------------------------------------

    def validate_cycle(self) -> bool:
        """(CYCLE): cada etiqueta aparece una vez como inicio y una como fin en S ∪ A."""
        names = sorted(lbl.name for lbl in self.labels)
        starts = sorted([p.start for p in self.segments] + [a.start for a in self.arcs])
        ends = sorted([p.end for p in self.segments] + [a.end for a in self.arcs])
        return starts == names and ends == names

    def validate_c1(self, config: DiskConfiguration, tol: float = _TOL) -> bool:
        """(C1): la tangente de viaje entrante coincide con la saliente en cada junción.

        Las tangentes de los segmentos están determinadas por v̂_s. Las de los
        arcos son ±n_α^⊥; la orientación de cada arco se infiere haciendo coincidir
        su tangente de inicio con la tangente de salida de la pieza precedente
        (que en un cs--diagrama alternante es un segmento, con tangente definida).
        """
        if not self.validate_cycle():
            return False
        pieces = self._ordered_cycle()
        if not pieces:
            return True

        n = len(pieces)

        def _compute_tangents(initial_prev: Point | None) -> tuple[bool, list[Point], list[Point]]:
            st: list[Point] = [Point(0.0, 0.0)] * n
            et: list[Point] = [Point(0.0, 0.0)] * n
            prev = initial_prev
            for idx, piece in enumerate(pieces):
                st[idx], et[idx] = self._piece_tangents(piece, config, prev)
                prev = et[idx]
            ok = all(
                (et[idx - 1] - st[idx]).norm() <= tol for idx in range(n)
            )
            return ok, st, et

        # Primera pasada: el primer arco (si existe) se orienta CCW por defecto.
        ok, _, _ = _compute_tangents(None)
        if ok:
            return True
        # Si el primer arco fue orientado al revés, intentar con la dirección opuesta.
        if isinstance(pieces[0], DirectedArc):
            s0, _ = self._piece_tangents(pieces[0], config, None)
            ok, _, _ = _compute_tangents(s0 * -1.0)  # forzar la otra orientación
            return ok
        return False

    def validate_geometry(self, config: DiskConfiguration, tol: float = _TOL) -> list[str]:
        """Chequeos A2/A3/A4 del paper: puntos en frontera y consistencia de arcos.

        Retorna lista de errores (vacía si todo está bien).
        """
        errors: list[str] = []
        n = len(config)
        for lbl in self.labels:
            if lbl.disk_idx < 0 or lbl.disk_idx >= n:
                errors.append(
                    f"Etiqueta {lbl.name!r}: disk_idx={lbl.disk_idx} fuera de rango [0, {n-1}]."
                )
                continue
            disk = config[lbl.disk_idx]
            dist = disk.center.distance_to(lbl.point)
            if abs(dist - disk.radius) > tol:
                errors.append(
                    f"Etiqueta {lbl.name!r}: p_α no está en ∂D_{lbl.disk_idx} "
                    f"(distancia al centro = {dist:.6f}, radio = {disk.radius:.6f})."
                )
        for arc in self.arcs:
            for end_name in (arc.start, arc.end):
                try:
                    lbl = self.label_by_name(end_name)
                except KeyError:
                    continue
                if lbl.disk_idx != arc.disk_idx:
                    errors.append(
                        f"Arco {arc.start!r}→{arc.end!r}: etiqueta {end_name!r} "
                        f"pertenece a D{lbl.disk_idx} pero el arco es sobre D{arc.disk_idx}."
                    )
        return errors

    def validate(self, config: DiskConfiguration) -> tuple[bool, list[str]]:
        """Comprueba geometría (A2/A3), (CYCLE) y (C1); retorna (ok, lista_de_errores)."""
        errors: list[str] = []
        errors.extend(self.validate_geometry(config))
        if not self.validate_cycle():
            errors.append(
                "(CYCLE) Cada etiqueta debe aparecer exactamente una vez como "
                "inicio y una vez como fin de una pieza."
            )
        elif not self.validate_c1(config):
            errors.append(
                "(C1) Las tangentes de viaje entrante y saliente no coinciden "
                "en alguna junción."
            )
        return (len(errors) == 0, errors)

    # ------------------------------------------------------------------
    # Internos
    # ------------------------------------------------------------------

    def _ordered_cycle(self) -> list[DirectedSegment | DirectedArc]:
        """Ordena las piezas siguiendo el ciclo; arranca en un segmento si existe."""
        by_start: dict[str, DirectedSegment | DirectedArc] = {}
        for seg in self.segments:
            by_start[seg.start] = seg
        for arc in self.arcs:
            by_start[arc.start] = arc
        if not by_start:
            return []

        start_label = self.segments[0].start if self.segments else self.arcs[0].start
        ordered: list[DirectedSegment | DirectedArc] = []
        seen: set[str] = set()
        label = start_label
        while label in by_start and label not in seen:
            piece = by_start[label]
            ordered.append(piece)
            seen.add(label)
            label = piece.end
        return ordered

    def _piece_tangents(
        self,
        piece: DirectedSegment | DirectedArc,
        config: DiskConfiguration,
        prev_end: Point | None,
    ) -> tuple[Point, Point]:
        """Tangentes unitarias de viaje (inicio, fin) de *piece*."""
        if isinstance(piece, DirectedSegment):
            a = self.label_by_name(piece.start).point
            b = self.label_by_name(piece.end).point
            u = _normalize(b - a)
            return u, u

        center = config[piece.disk_idx].center
        n_start = _normalize(self.label_by_name(piece.start).point - center)
        n_end = _normalize(self.label_by_name(piece.end).point - center)
        ccw_start = _perp(n_start)  # tangente de viaje si el arco es antihorario
        ccw_end = _perp(n_end)
        # Orientar el arco para empatar la tangente de inicio con la pieza previa.
        if prev_end is not None and _dot(ccw_start, prev_end) < 0.0:
            return ccw_start * -1.0, ccw_end * -1.0
        return ccw_start, ccw_end
