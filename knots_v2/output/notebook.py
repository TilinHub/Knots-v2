"""Visualización de configuraciones de discos con matplotlib.

Compatible con Jupyter Notebook y con scripts Python estándar.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class NotebookBridge:
    """Visualiza una configuración de discos y sus resultados de análisis.

    Usa matplotlib internamente. Si matplotlib no está disponible, emite
    un mensaje explicativo en lugar de lanzar ImportError.

    Example en Jupyter::

        bridge = NotebookBridge()
        bridge.plot(config, results)   # muestra inline en el notebook

    Example en script::

        bridge = NotebookBridge()
        fig = bridge.plot(config, results)
        fig.savefig("visualizacion.png", dpi=150)
    """

    def plot(
        self,
        config,
        results: dict[str, Any],
        title: str = "Configuración de discos — Knots v2",
        figsize: tuple[float, float] = (9, 9),
    ):
        """Genera la figura de visualización.

        Args:
            config: DiskConfiguration a visualizar.
            results: Resultados del censo (envelope, contact_graph, convex_hull).
            title: Título de la figura.
            figsize: Tamaño de la figura en pulgadas (ancho, alto).

        Returns:
            El objeto ``matplotlib.figure.Figure``, o None si matplotlib no está disponible.
        """
        try:
            import matplotlib.pyplot as plt
            import matplotlib.patches as mpatches
        except ImportError:
            logger.error(
                "matplotlib no está instalado. Instálalo con: pip install matplotlib"
            )
            print("matplotlib no está disponible. Instálalo con: pip install matplotlib")
            return None

        fig, ax = plt.subplots(figsize=figsize)
        disks = list(config)

        # --- Discos ---
        for i, disk in enumerate(disks):
            circle = mpatches.Circle(
                (disk.center.x, disk.center.y),
                disk.radius,
                facecolor="#aecde8",
                edgecolor="#2a6496",
                linewidth=1.2,
                alpha=0.75,
                zorder=2,
            )
            ax.add_patch(circle)
            ax.text(
                disk.center.x,
                disk.center.y,
                str(i),
                ha="center",
                va="center",
                fontsize=max(6, disk.radius * 3),
                color="#1a3e5c",
                zorder=3,
            )

        # --- Convex hull ---
        hull = results.get("convex_hull", [])
        if len(hull) >= 2:
            xs = [p["x"] for p in hull] + [hull[0]["x"]]
            ys = [p["y"] for p in hull] + [hull[0]["y"]]
            ax.plot(xs, ys, color="#e67e22", linewidth=1.2,
                    linestyle="--", alpha=0.7, label="Convex hull", zorder=4)

        # --- Envolvente ---
        envelope = results.get("envelope", [])
        if len(envelope) >= 2:
            xs = [p["x"] for p in envelope] + [envelope[0]["x"]]
            ys = [p["y"] for p in envelope] + [envelope[0]["y"]]
            ax.plot(xs, ys, color="#e74c3c", linewidth=2.0,
                    label="Envolvente", zorder=5)

        # --- Grafo de contacto ---
        graph = results.get("contact_graph", {})
        plotted_edges: set[frozenset] = set()
        for i_key, neighbors in graph.items():
            i = int(i_key)
            if i >= len(disks):
                continue
            for j in neighbors:
                edge = frozenset({i, j})
                if edge in plotted_edges or j >= len(disks):
                    continue
                plotted_edges.add(edge)
                d1, d2 = disks[i], disks[j]
                ax.plot(
                    [d1.center.x, d2.center.x],
                    [d1.center.y, d2.center.y],
                    color="#27ae60",
                    linewidth=1.0,
                    linestyle=":",
                    alpha=0.8,
                    zorder=6,
                    label="Contacto" if not plotted_edges - {edge} else "_nolegend_",
                )

        # --- Metadatos ---
        meta = results.get("metadata", {})
        info = (
            f"Discos: {meta.get('n_disks', len(disks))}  |  "
            f"Válida: {meta.get('is_valid', '?')}  |  "
            f"Tiempo: {meta.get('elapsed_seconds', 0):.4f}s"
        )
        ax.set_title(title, fontsize=13)
        ax.text(
            0.5, -0.04, info,
            transform=ax.transAxes,
            ha="center", fontsize=9, color="#555",
        )

        ax.set_aspect("equal")
        ax.autoscale_view()
        ax.grid(True, alpha=0.25)

        # Eliminar entradas duplicadas de la leyenda
        handles, labels = ax.get_legend_handles_labels()
        seen: set[str] = set()
        unique_handles, unique_labels = [], []
        for h, l in zip(handles, labels):
            if l not in seen and not l.startswith("_"):
                seen.add(l)
                unique_handles.append(h)
                unique_labels.append(l)
        if unique_handles:
            ax.legend(unique_handles, unique_labels, loc="upper right", fontsize=9)

        # Detectar si estamos en Jupyter para usar display() en lugar de show()
        try:
            get_ipython()  # type: ignore[name-defined]
            plt.show()
        except NameError:
            plt.show()

        return fig
