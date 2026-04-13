"""Exportador de configuraciones de discos a SVG.

Genera un SVG como string que puede guardarse en archivo o insertarse
directamente en HTML. No requiere dependencias externas.
"""

from __future__ import annotations

from typing import Any

from ..domain.configuration import DiskConfiguration


class SVGExporter:
    """Convierte una configuración de discos y sus resultados de análisis a SVG.

    El SVG incluye:
    - Los discos como círculos con relleno semitransparente.
    - La envolvente como polyline cerrada en rojo.
    - El grafo de contacto como líneas discontinuas entre centros.
    - El convex hull como polyline en naranja (si difiere de la envolvente).

    Example::

        svg_str = SVGExporter().export(config, results)
        Path("salida.svg").write_text(svg_str)
    """

    # Padding alrededor del contenido en unidades de usuario
    _PADDING: float = 5.0

    def export(self, config: DiskConfiguration, results: dict[str, Any]) -> str:
        """Genera el SVG completo como string.

        Args:
            config: Configuración de discos a visualizar.
            results: Diccionario de resultados del censo
                (con claves ``envelope``, ``contact_graph``, ``convex_hull``).

        Returns:
            SVG como string UTF-8.
        """
        disks = list(config)
        vb = self._viewbox(config)
        min_x, min_y, width, height = vb

        lines: list[str] = [
            f'<svg xmlns="http://www.w3.org/2000/svg"'
            f' viewBox="{min_x:.3f} {min_y:.3f} {width:.3f} {height:.3f}"'
            f' width="{width:.0f}" height="{height:.0f}">',
            "  <!-- Knots v2 — generado automáticamente -->",
        ]

        lines.extend(self._render_disks(disks))
        lines.extend(self._render_hull(results.get("convex_hull", [])))
        lines.extend(self._render_envelope(results.get("envelope", [])))
        lines.extend(self._render_contact_graph(disks, results.get("contact_graph", {})))

        lines.append("</svg>")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Renderizado de capas
    # ------------------------------------------------------------------

    def _render_disks(self, disks) -> list[str]:
        lines = ["  <!-- Discos -->"]
        for i, disk in enumerate(disks):
            cx, cy, r = disk.center.x, disk.center.y, disk.radius
            lines.append(
                f'  <circle cx="{cx:.4f}" cy="{cy:.4f}" r="{r:.4f}"'
                f' fill="#aecde8" stroke="#2a6496" stroke-width="{r * 0.04:.4f}"'
                f' opacity="0.75" id="disk-{i}"/>'
            )
            # Etiquetar con el índice del disco
            lines.append(
                f'  <text x="{cx:.4f}" y="{cy:.4f}" text-anchor="middle"'
                f' dominant-baseline="central" font-size="{r * 0.4:.4f}"'
                f' fill="#1a3e5c">{i}</text>'
            )
        return lines

    def _render_envelope(self, envelope: list[dict]) -> list[str]:
        if len(envelope) < 2:
            return []
        pts_str = " ".join(f"{p['x']:.4f},{p['y']:.4f}" for p in envelope)
        # Cerramos el polígono repitiendo el primer punto
        first = envelope[0]
        pts_str += f" {first['x']:.4f},{first['y']:.4f}"
        return [
            "  <!-- Envolvente exterior -->",
            f'  <polyline points="{pts_str}"'
            f' fill="none" stroke="#e74c3c" stroke-width="0.8"'
            f' stroke-linejoin="round"/>',
        ]

    def _render_hull(self, hull: list[dict]) -> list[str]:
        if len(hull) < 2:
            return []
        pts_str = " ".join(f"{p['x']:.4f},{p['y']:.4f}" for p in hull)
        first = hull[0]
        pts_str += f" {first['x']:.4f},{first['y']:.4f}"
        return [
            "  <!-- Convex hull -->",
            f'  <polyline points="{pts_str}"'
            f' fill="none" stroke="#e67e22" stroke-width="0.5"'
            f' stroke-dasharray="3,2" opacity="0.7"/>',
        ]

    def _render_contact_graph(self, disks, graph: dict) -> list[str]:
        if not graph or not disks:
            return []
        lines = ["  <!-- Grafo de contacto -->"]
        for i_key, neighbors in graph.items():
            i = int(i_key)
            if i >= len(disks):
                continue
            for j in neighbors:
                if j <= i or j >= len(disks):
                    # Dibujamos cada arista solo una vez (i < j)
                    continue
                d1, d2 = disks[i], disks[j]
                lines.append(
                    f'  <line x1="{d1.center.x:.4f}" y1="{d1.center.y:.4f}"'
                    f' x2="{d2.center.x:.4f}" y2="{d2.center.y:.4f}"'
                    f' stroke="#27ae60" stroke-width="0.4"'
                    f' stroke-dasharray="1.5,1" opacity="0.8"/>'
                )
        return lines

    # ------------------------------------------------------------------
    # ViewBox
    # ------------------------------------------------------------------

    def _viewbox(
        self, config: DiskConfiguration
    ) -> tuple[float, float, float, float]:
        """Calcula (min_x, min_y, width, height) con padding."""
        bb = config.bounding_box()
        if bb is None:
            return (-10.0, -10.0, 20.0, 20.0)
        x0, y0, x1, y1 = bb
        p = self._PADDING
        return (x0 - p, y0 - p, (x1 - x0) + 2 * p, (y1 - y0) + 2 * p)
