"""Galería de nudos: ventana *separada* que muestra los presets del paper.

Reproduce los diagramas cs minimales (arXiv:2005.13168) agrupados por número de
cruces. Es una función independiente del editor principal: se puede abrir desde
un botón del visor o ejecutarse sola con ``python -m knots_v2.gallery``.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .presets import KnotPreset, build_preset, presets_by_crossings

_R = 1.0
_CARD_W = 240
_CANVAS_H = 200
_DISK_FILL = "#dce9fb"
_DISK_OUTLINE = "#9bbbe6"
_CURVE = "#c0392b"


def _draw_preset(canvas: tk.Canvas, built: dict, w: int, h: int, pad: int = 20) -> None:
    """Dibuja un preset en *canvas* ajustando la escala para que entre completo."""
    xs: list[float] = []
    ys: list[float] = []
    for res in built["loops"]:
        for p in res["polyline"]:
            xs.append(p.x)
            ys.append(p.y)
    for c in built["centers"]:
        xs.extend([c.x - _R, c.x + _R])
        ys.extend([c.y - _R, c.y + _R])
    if not xs:
        return

    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    span_x = max(1e-6, maxx - minx)
    span_y = max(1e-6, maxy - miny)
    scale = min((w - 2 * pad) / span_x, (h - 2 * pad) / span_y)
    off_x = (w - span_x * scale) / 2
    off_y = (h - span_y * scale) / 2

    def tx(x: float, y: float) -> tuple[float, float]:
        return off_x + (x - minx) * scale, h - (off_y + (y - miny) * scale)

    # Discos (regiones complementarias)
    for c in built["centers"]:
        x0, y0 = tx(c.x - _R, c.y - _R)
        x1, y1 = tx(c.x + _R, c.y + _R)
        canvas.create_oval(
            min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1),
            fill=_DISK_FILL, outline=_DISK_OUTLINE,
        )

    # Núcleo del nudo (una polilínea por lazo; los cruces aparecen solos)
    for res in built["loops"]:
        if len(res["polyline"]) >= 2:
            coords: list[float] = []
            for p in res["polyline"]:
                sx, sy = tx(p.x, p.y)
                coords.extend([sx, sy])
            canvas.create_line(
                coords, fill=_CURVE, width=3, joinstyle=tk.ROUND, capstyle=tk.ROUND
            )


class KnotGallery(tk.Toplevel):
    """Ventana con la galería de nudos agrupada por número de cruces."""

    def __init__(self, master: tk.Misc | None = None):
        super().__init__(master)
        self.title("Galería de Nudos — diagramas cs del paper (arXiv:2005.13168)")
        self.geometry("1040x720")
        self.configure(bg="#f4f5f7")
        self._build()

    def _build(self) -> None:
        ttk.Label(
            self, text="Galería de Nudos cs", font=("Inter", 16, "bold"),
            foreground="#2A6496", background="#f4f5f7",
        ).pack(anchor=tk.W, padx=16, pady=(12, 0))
        ttk.Label(
            self,
            text="Diagramas de longitud mínima por número de cruces. Discos = regiones; "
                 "curva roja = núcleo (arcos de radio 1 + segmentos tangentes).",
            background="#f4f5f7", foreground="#555",
        ).pack(anchor=tk.W, padx=16, pady=(0, 8))

        # Área desplazable
        container = tk.Frame(self, bg="#f4f5f7")
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)
        canvas = tk.Canvas(container, bg="#f4f5f7", highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient=tk.VERTICAL, command=canvas.yview)
        inner = tk.Frame(canvas, bg="#f4f5f7")
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        for crossings, group in presets_by_crossings().items():
            label = "0 cruces" if crossings == 0 else (
                "1 cruce" if crossings == 1 else f"{crossings} cruces"
            )
            header = tk.Frame(inner, bg="#f4f5f7")
            header.pack(fill=tk.X, pady=(10, 2))
            tk.Label(
                header, text=f"  ●  {label}", font=("Inter", 12, "bold"),
                fg="#1c3046", bg="#e7edf6", anchor=tk.W,
            ).pack(fill=tk.X)

            row = tk.Frame(inner, bg="#f4f5f7")
            row.pack(fill=tk.X, anchor=tk.W)
            for preset in group:
                self._make_card(row, preset)

    def _make_card(self, parent: tk.Misc, preset: KnotPreset) -> None:
        # Sin pack_propagate(False): la tarjeta se dimensiona a su contenido
        # (el canvas fija el ancho; las etiquetas hacen wrap dentro de ese ancho).
        card = tk.Frame(parent, bg="#ffffff", bd=1, relief=tk.SOLID)
        card.pack(side=tk.LEFT, padx=6, pady=6, anchor=tk.N)

        cv = tk.Canvas(card, width=_CARD_W - 2, height=_CANVAS_H, bg="#ffffff", highlightthickness=0)
        cv.pack()
        built = build_preset(preset, _R)
        cv.update_idletasks()
        _draw_preset(cv, built, _CARD_W - 2, _CANVAS_H)

        tk.Label(card, text=preset.name, font=("Inter", 11, "bold"), fg="#2A6496", bg="#ffffff",
                 wraplength=_CARD_W - 16).pack(anchor=tk.W, padx=8, pady=(4, 0))
        length = built["length"]
        tk.Label(
            card,
            text=f"Cruces: {preset.crossings}    Longitud: {length:.3f}  ({length / 3.141592653589793:.3f} π)",
            font=("Consolas", 8), fg="#333", bg="#ffffff",
        ).pack(anchor=tk.W, padx=8)
        if preset.ribbonlength and preset.ribbonlength != "—":
            tk.Label(card, text=f"Ribbonlength (paper): {preset.ribbonlength}",
                     font=("Consolas", 8), fg="#2e7d32", bg="#ffffff").pack(anchor=tk.W, padx=8)
        tk.Label(card, text=preset.note, font=("Inter", 7), fg="#777", bg="#ffffff",
                 wraplength=_CARD_W - 16, justify=tk.LEFT).pack(anchor=tk.W, padx=8, pady=(2, 8))


def main() -> None:
    """Punto de entrada autónomo: abre la galería en su propia ventana."""
    root = tk.Tk()
    root.withdraw()
    gallery = KnotGallery(root)
    gallery.protocol("WM_DELETE_WINDOW", root.destroy)
    root.mainloop()


if __name__ == "__main__":
    main()
