"""Galería de nudos: ventana *separada* con los diagramas estándar de Rolfsen.

Dibuja cada nudo a partir de su PD code (traversal → embedding planar de Tutte →
curva suave → over/under). Muestra además el vector de Conway y la fracción
2--puente b(p,q). Si un nudo tiene una construcción cs en el catálogo, ofrece
«Cargar en editor».

Se abre desde el visor o con ``python -m knots_v2.gallery``.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .pd_draw import KNOT_GAUSS_CODES, draw_on_canvas, knot_layout
from .presets import PRESETS
from .rational import ROLFSEN_2BRIDGE, fraction_label

_CARD_W = 220
_CANVAS_H = 190


def _crossing_number(name: str) -> int:
    return int(name.split("_")[0])


def _pretty(name: str) -> str:
    base, _, idx = name.partition("_")
    subs = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")
    return "Unknot" if name == "0_1" else f"{base}{idx.translate(subs)}"


class KnotGallery(tk.Toplevel):
    """Galería de los diagramas estándar de Rolfsen, agrupados por nº de cruces."""

    def __init__(self, master: tk.Misc | None = None, on_load=None):
        super().__init__(master)
        self.on_load = on_load
        self.title("Galería de Nudos — diagramas estándar (PD codes)")
        self.geometry("1100x760")
        self.configure(bg="#f4f5f7")
        # preset por vector de Conway (para el botón «Cargar en editor»)
        self._preset_by_conway = {p.conway: p for p in PRESETS if p.conway}
        self._build()

    def _build(self) -> None:
        ttk.Label(self, text="Galería de Nudos — diagramas estándar", font=("Inter", 16, "bold"),
                  foreground="#2A6496", background="#f4f5f7").pack(anchor=tk.W, padx=16, pady=(12, 0))
        ttk.Label(self, text="Trazados desde PD codes: embedding planar + curva suave + over/under. "
                             "Etiqueta: Conway C(...) → 2-puente b(p,q).",
                  background="#f4f5f7", foreground="#555").pack(anchor=tk.W, padx=16, pady=(0, 8))

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

        names = sorted(KNOT_GAUSS_CODES, key=lambda nm: (_crossing_number(nm), nm))
        groups: dict[int, list[str]] = {}
        for nm in names:
            groups.setdefault(_crossing_number(nm), []).append(nm)

        for cn, group in sorted(groups.items()):
            label = "0 cruces" if cn == 0 else ("1 cruce" if cn == 1 else f"{cn} cruces")
            tk.Label(inner, text=f"  ●  {label}", font=("Inter", 12, "bold"),
                     fg="#1c3046", bg="#e7edf6", anchor=tk.W).pack(fill=tk.X, pady=(10, 2))
            row = tk.Frame(inner, bg="#f4f5f7")
            row.pack(fill=tk.X, anchor=tk.W)
            for nm in group:
                self._make_card(row, nm)

    def _make_card(self, parent: tk.Misc, name: str) -> None:
        card = tk.Frame(parent, bg="#ffffff", bd=1, relief=tk.SOLID)
        card.pack(side=tk.LEFT, padx=6, pady=6, anchor=tk.N)

        cv = tk.Canvas(card, width=_CARD_W - 2, height=_CANVAS_H, bg="#ffffff", highlightthickness=0)
        cv.pack()
        layout = knot_layout(name)
        if layout["ok"]:
            draw_on_canvas(cv, layout, _CARD_W - 2, _CANVAS_H)
        else:
            cv.create_text((_CARD_W - 2) / 2, _CANVAS_H / 2 - 10, text="PD code inválido",
                           fill="#c0392b", font=("Inter", 10, "bold"))
            cv.create_text((_CARD_W - 2) / 2, _CANVAS_H / 2 + 10, text="(falta código estándar)",
                           fill="#999", font=("Inter", 8))

        tk.Label(card, text=_pretty(name), font=("Inter", 13, "bold"), fg="#2A6496",
                 bg="#ffffff").pack(anchor=tk.W, padx=8, pady=(4, 0))
        conway = ROLFSEN_2BRIDGE.get(name)
        if conway:
            tk.Label(card, text=f"Conway C{conway} → {fraction_label(conway)}",
                     font=("Consolas", 8), fg="#8e44ad", bg="#ffffff").pack(anchor=tk.W, padx=8)
            preset = self._preset_by_conway.get(conway)
            if preset and self.on_load is not None:
                ttk.Button(card, text="Cargar en editor",
                           command=lambda p=preset: self.on_load(p)).pack(fill=tk.X, padx=8, pady=(4, 8))
            else:
                tk.Frame(card, height=6, bg="#ffffff").pack()
        else:
            tk.Frame(card, height=6, bg="#ffffff").pack()


def main() -> None:
    root = tk.Tk()
    root.withdraw()
    gallery = KnotGallery(root)
    gallery.protocol("WM_DELETE_WINDOW", root.destroy)
    root.mainloop()


if __name__ == "__main__":
    main()
