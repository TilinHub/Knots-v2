import math
import tkinter as tk
from tkinter import ttk
import threading
import queue

import numpy as np

from knots_v2.domain.primitives import Point
from knots_v2.domain.disk import Disk
from knots_v2.domain.configuration import DiskConfiguration
from knots_v2.compute.convex_hull import ConvexHull
from knots_v2.compute.cs_route import build_route
from knots_v2.compute.first_variation import build_gradient, is_stationary_kernel
from knots_v2.compute.rolling import (
    build_rolling_matrix,
    detect_contact_set,
    rolling_space_basis,
)

class EnvelopeWorker(threading.Thread):
    """Proceso en segundo plano para cálculo CS paralelo."""
    def __init__(self, task_queue: queue.Queue, result_queue: queue.Queue):
        super().__init__(daemon=True)
        self.task_queue = task_queue
        self.result_queue = result_queue
        self.hull_computer = ConvexHull()

    def run(self):
        while True:
            try:
                task = self.task_queue.get()
                # Empty queue skipping to the last update
                while not self.task_queue.empty():
                    try: task = self.task_queue.get_nowait()
                    except queue.Empty: break

                centers, radius, custom_seq = task
                if not centers:
                    self.result_queue.put({"envelope": [], "rectas": 0.0, "arcos_pi": 0.0})
                    continue

                route_points = (
                    [centers[i] for i in custom_seq] if custom_seq
                    else self.hull_computer._graham_scan(centers)
                )

                # Despacho por número de puntos (switch en vez de if/elif anidado).
                match len(route_points):
                    case 0:
                        result = {"envelope": [], "rectas": 0.0, "arcos_pi": 0.0}
                    case 1:
                        result = self._envelope_single(route_points, radius)
                    case 2:
                        result = self._envelope_pair(route_points, radius)
                    case _:
                        result = self._envelope_polygon(route_points, radius)
                self.result_queue.put(result)

            except Exception as e:
                print(f"Error en Worker de Envolvente: {e}")

    @staticmethod
    def _envelope_single(route_points, radius):
        """Un punto: círculo completo (arco 2π, sin rectas)."""
        cx, cy = route_points[0].x, route_points[0].y
        contour = [
            (cx + radius * math.cos(2 * math.pi * i / 40), cy + radius * math.sin(2 * math.pi * i / 40))
            for i in range(40)
        ]
        return {"envelope": contour, "rectas": 0.0, "arcos_pi": 2.0 * radius}

    @staticmethod
    def _envelope_pair(route_points, radius):
        """Dos puntos: stadium (dos rectas + dos semicírculos)."""
        p0, p1 = route_points[0], route_points[1]
        dist = math.hypot(p1.x - p0.x, p1.y - p0.y)
        dx, dy = (1.0, 0.0) if dist < 1e-9 else ((p1.x - p0.x) / dist, (p1.y - p0.y) / dist)
        nx, ny = dy, -dx
        contour = [
            (p0.x + radius * nx, p0.y + radius * ny),
            (p1.x + radius * nx, p1.y + radius * ny),
        ]
        contour += [
            (p1.x + radius * math.cos(math.atan2(ny, nx) + math.pi * i / 20),
             p1.y + radius * math.sin(math.atan2(ny, nx) + math.pi * i / 20))
            for i in range(1, 20)
        ]
        contour += [
            (p1.x - radius * nx, p1.y - radius * ny),
            (p0.x - radius * nx, p0.y - radius * ny),
        ]
        contour += [
            (p0.x + radius * math.cos(math.atan2(-ny, -nx) + math.pi * i / 20),
             p0.y + radius * math.sin(math.atan2(-ny, -nx) + math.pi * i / 20))
            for i in range(1, 20)
        ]
        return {"envelope": contour, "rectas": 2.0 * dist, "arcos_pi": 2.0 * radius}

    @staticmethod
    def _envelope_polygon(route_points, radius):
        """Tres o más puntos: banda exterior (perímetro + arcos en los vértices)."""
        n = len(route_points)
        normals = []
        perimeter = 0.0
        for i in range(n):
            p1, p2 = route_points[i], route_points[(i + 1) % n]
            dx, dy = p2.x - p1.x, p2.y - p1.y
            dist = math.hypot(dx, dy)
            perimeter += dist
            normals.append((1.0, 0.0) if dist < 1e-9 else (dy / dist, -dx / dist))

        contour = []
        arcos_pi = 0.0
        for i in range(n):
            p = route_points[i]
            a_start = math.atan2(*reversed(normals[(i - 1) % n]))
            a_end = math.atan2(*reversed(normals[i]))
            ang_diff = (a_end - a_start) % (2 * math.pi)
            arcos_pi += (radius * ang_diff) / math.pi
            steps = max(5, int(30 * ang_diff / (2 * math.pi)))
            contour += [
                (p.x + radius * math.cos(a_start + ang_diff * (j / steps)),
                 p.y + radius * math.sin(a_start + ang_diff * (j / steps)))
                for j in range(steps + 1)
            ]
        return {"envelope": contour, "rectas": perimeter, "arcos_pi": arcos_pi}

class KnotsApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Knots-v2: Visor Interactivo (POO y Paralelismo)")
        self.geometry("1100x750")
        self.configure(bg="#f4f5f7")
        
        self.scale = 80.0
        self.r_math = 1.0  
        self.disks = [
            Point(1.99, 2.45),
            Point(0.02, -0.22),
            Point(-2.38, -2.83),
            Point(3.00, -2.63)
        ]
        
        self.dragged_disk_idx = None
        self.current_envelope = []
        self.custom_sequence = []

        # Modo Rodar: un disco pivote y un disco que gira a su alrededor.
        self.roll_pivot = None
        self.roll_disk = None
        self.rolling = False

        # Estado del cs-diagrama: una lista de LAZOS cíclicos (un nudo = 1 lazo;
        # un enlace = varios). Cada lazo es {"seq": [índices de disco en orden],
        # "orient": {disk_idx: +1 antihorario | -1 horario}}. Los segmentos
        # tangentes y arcos se calculan solos ⇒ C¹ por construcción; permite cruces.
        self.cs_loops: list[dict] = []
        self._cs_results: list[dict] = []  # resultado de build_route por lazo
        self.loaded_layout = None          # diagrama estándar cargado desde la galería

        self.mode = tk.StringVar(value="move")
        self.show_envelope = tk.BooleanVar(value=True)
        
        self.task_queue = queue.Queue()
        self.result_queue = queue.Queue()
        self.worker = EnvelopeWorker(self.task_queue, self.result_queue)
        self.worker.start()
        
        self._build_ui()
        self._update_envelope_task()
        self.after(15, self._check_results)

    def _build_ui(self):
        self.top_frame = ttk.Frame(self, padding=15)
        self.top_frame.pack(side=tk.TOP, fill=tk.X)
        
        # Resumen Metric
        self.lbl_measure = ttk.Label(self.top_frame, text="Medida de la envolvente: 0.000", font=("Inter", 16, "bold"), foreground="#2A6496")
        self.lbl_measure.pack(side=tk.LEFT)
        
        # Tools
        tools_frame = ttk.Frame(self.top_frame)
        tools_frame.pack(side=tk.RIGHT)

        ttk.Radiobutton(tools_frame, text="Mover (Arrastrar / Doble Click)", variable=self.mode, value="move").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(tools_frame, text="Delinear Envolvente", variable=self.mode, value="draw").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(tools_frame, text="Borrar Disco", variable=self.mode, value="delete").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(tools_frame, text="Construir Nudo (cs)", variable=self.mode, value="cs_build").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(tools_frame, text="Rodar", variable=self.mode, value="rolling").pack(side=tk.LEFT, padx=5)
        ttk.Button(tools_frame, text="↺", width=2, command=lambda: self._roll_start(+1)).pack(side=tk.LEFT)
        ttk.Button(tools_frame, text="↻", width=2, command=lambda: self._roll_start(-1)).pack(side=tk.LEFT, padx=(0, 5))

        ttk.Separator(tools_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=10, fill=tk.Y)
        ttk.Button(tools_frame, text="Añadir Disco", command=self._add_disk_btn).pack(side=tk.LEFT, padx=4)
        ttk.Button(tools_frame, text="Borrar Recorrido", command=self._clear_sequence).pack(side=tk.LEFT, padx=4)
        ttk.Checkbutton(tools_frame, text="Ver Envolvente", variable=self.show_envelope, command=self._redraw).pack(side=tk.LEFT, padx=5)
        ttk.Button(tools_frame, text="Galería de Nudos", command=self._open_gallery).pack(side=tk.LEFT, padx=4)

        # Panel lateral del cs-diagrama (se empaqueta antes que el canvas para
        # reservar la franja derecha; el canvas rellena el resto).
        self._build_cs_panel()

        # Main Canvas Area
        self.canvas = tk.Canvas(self, bg="#ffffff", highlightthickness=1, highlightbackground="#d1d6e3")
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<Double-Button-1>", self._on_double_click)
        self.canvas.bind("<ButtonPress-3>", self._on_right_click)
        
        self.bind("<Configure>", lambda e: self._redraw())
        
    def math_to_screen(self, x, y):
        w, h = self.canvas.winfo_width() / 2, self.canvas.winfo_height() / 2
        return w + x * self.scale, h - y * self.scale
        
    def screen_to_math(self, x, y):
        w, h = self.canvas.winfo_width() / 2, self.canvas.winfo_height() / 2
        return (x - w) / self.scale, (h - y) / self.scale

    def _draw_grid(self):
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        if w <= 1: return
        cx, cy = w/2, h/2
        grid_step = self.scale * 0.5
        
        # Verticals
        x = cx % grid_step
        while x < w:
            self.canvas.create_line(x, 0, x, h, fill="#f0f2f5")
            x += grid_step
            
        # Horizontals
        y = cy % grid_step
        while y < h:
            self.canvas.create_line(0, y, w, y, fill="#f0f2f5")
            y += grid_step

    def _clear_sequence(self):
        self.custom_sequence.clear()
        self._update_envelope_task()
        self._redraw()

    def _update_envelope_task(self):
        self.task_queue.put((
            [Point(p.x, p.y) for p in self.disks], 
            self.r_math,
            list(self.custom_sequence)
        ))

    def _check_results(self):
        needs_redraw = False
        try:
            while not self.result_queue.empty():
                res = self.result_queue.get_nowait()
                self.current_envelope = res["envelope"]
                
                rectas = res["rectas"]
                arcos_pi = res["arcos_pi"]
                total = rectas + arcos_pi * math.pi
                
                # Fomatear a string sin decimales si es entero, ej 4.0 -> 4
                arcos_str = f"{arcos_pi:g}"

                # La etiqueta superior pertenece a la envolvente solo si no hay nudo activo.
                self._env_measure_text = f"Envolvente: {arcos_str}π + {rectas:.2f}  (Total: {total:.4f} u)"
                if not self.cs_loops:
                    self.lbl_measure.config(text=self._env_measure_text)
                needs_redraw = True
        except queue.Empty: pass
        
        if needs_redraw:
            self._redraw()
            
        self.after(15, self._check_results)

    def _redraw(self):
        self.canvas.delete("all")

        # Vista de un diagrama estándar cargado desde la galería (cualquier nudo).
        if self.loaded_layout and self.loaded_layout.get("ok"):
            w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
            if w > 1:
                from knots_v2.pd_draw import draw_on_canvas
                draw_on_canvas(self.canvas, self.loaded_layout, w, h, show_disks=True)
                self.canvas.create_text(
                    15, 15, anchor=tk.NW, fill="#1f6feb", font=("Inter", 11, "bold"),
                    text="Viendo diagrama estándar — «Borrar Nudo» para volver al editor cs",
                )
            return

        self._draw_grid()
        r_screen = self.r_math * self.scale
        
        # 1. Dibujar Contorno (Envolvente Elastic CS) — se oculta si hay un nudo activo
        if getattr(self, "current_envelope", None) and self.show_envelope.get() and not self.cs_loops:
            coords = []
            for px, py in self.current_envelope:
                sx, sy = self.math_to_screen(px, py)
                coords.extend([sx, sy])
            if len(coords) >= 4:
                self.canvas.create_polygon(
                    coords, fill="", outline="#1b1c20", width=8, 
                    joinstyle=tk.ROUND, smooth=False
                )

        # Circunferencia guía del giro (modo Rodar) detrás de los discos.
        if self.mode.get() == "rolling" and self.roll_pivot is not None and self.roll_disk is not None:
            piv = self.disks[self.roll_pivot]
            rol = self.disks[self.roll_disk]
            rad = math.hypot(rol.x - piv.x, rol.y - piv.y) * self.scale
            pcx, pcy = self.math_to_screen(piv.x, piv.y)
            self.canvas.create_oval(pcx - rad, pcy - rad, pcx + rad, pcy + rad,
                                    outline="#bdbdbd", dash=(4, 4))

        # 2. Dibujar Discos
        for i, p in enumerate(self.disks):
            sx, sy = self.math_to_screen(p.x, p.y)
            color = "#a3d1ff"
            outline_c = "#2A6496"

            if self.mode.get() == "draw" and i in self.custom_sequence:
                color = "#ffd27a"
                outline_c = "#e09000"
            if self.mode.get() == "rolling" and i == self.roll_pivot:
                color = "#a5d6a7"; outline_c = "#2e7d32"   # pivote: verde
            elif self.mode.get() == "rolling" and i == self.roll_disk:
                color = "#ffcc80"; outline_c = "#e65100"   # rodante: naranja

            self.canvas.create_oval(
                sx - r_screen, sy - r_screen, sx + r_screen, sy + r_screen,
                fill=color, outline=outline_c, width=3, tags=f"disk_{i}"
            )
            self.canvas.create_oval(sx - 2, sy - 2, sx + 2, sy + 2, fill="#000")
            
            # Texto con Coordenadas Claras e Índice (Para trazar el nudo)
            self.canvas.create_text(
                sx, sy + 20, text=f"D{i}\n({p.x:.2f}, {p.y:.2f})", 
                fill="#1c3046", font=("Consolas", 10, "bold"), justify=tk.CENTER
            )

        # 3. Mostrar Secuencia Superpuesta Interfaz
        if self.custom_sequence:
            seq_text = "Nudo Activo: " + " → ".join(f"D{x}" for x in self.custom_sequence)
            self.canvas.create_text(
                15, 15, text=seq_text, anchor=tk.NW, fill="#e74c3c", font=("Inter", 12, "bold")
            )

        # Guía del modo Rodar
        if self.mode.get() == "rolling":
            if self.roll_pivot is None:
                hint = "Rodar: clic en el disco PIVOTE"
            elif self.roll_disk is None:
                hint = f"Rodar: pivote D{self.roll_pivot} ✓ — clic en el disco que va a RODAR"
            else:
                hint = (f"Rodar: pivote D{self.roll_pivot}, rodante D{self.roll_disk} — "
                        "↺/↻ para girar (se detiene al chocar)")
            self.canvas.create_text(15, 15, text=hint, anchor=tk.NW,
                                    fill="#2e7d32", font=("Inter", 12, "bold"))

        # 4. Superponer el cs-diagrama (etiquetas, segmentos, arcos)
        self._draw_cs_overlay()

    def _get_clicked_disk(self, event) -> int | None:
        mx, my = self.screen_to_math(event.x, event.y)
        for i, p in enumerate(self.disks):
            if math.hypot(p.x - mx, p.y - my) <= self.r_math:
                return i
        return None

    def _on_press(self, event):
        idx = self._get_clicked_disk(event)
        match self.mode.get():
            case "delete":
                if idx is not None:
                    self._delete_disk(idx)
            case "draw":
                if idx is not None:
                    self.custom_sequence.append(idx)
                    self._update_envelope_task()
                    self._redraw()
            case "cs_build":
                self._cs_build_click(event, idx)
            case "rolling":
                self._roll_click(idx)
            case _:  # modo mover
                self.dragged_disk_idx = idx

    def _roll_click(self, idx):
        """1er clic: disco pivote. 2º clic: disco que rodará. 3er clic: reinicia."""
        self.rolling = False
        if idx is None:
            self.roll_pivot = self.roll_disk = None
        elif self.roll_pivot is None:
            self.roll_pivot = idx
        elif self.roll_disk is None and idx != self.roll_pivot:
            self.roll_disk = idx
        else:
            self.roll_pivot, self.roll_disk = idx, None
        self._redraw()

    def _roll_start(self, direction):
        """Inicia el giro del disco rodante alrededor del pivote (+1 izq, −1 der)."""
        if self.roll_pivot is None or self.roll_disk is None:
            return
        self.rolling = True
        self._roll_dir = direction
        self._roll_traveled = 0.0
        self._roll_step()

    def _roll_step(self):
        if not self.rolling or self.roll_pivot is None or self.roll_disk is None:
            return
        pivot = self.disks[self.roll_pivot]
        roll = self.disks[self.roll_disk]
        radius = math.hypot(roll.x - pivot.x, roll.y - pivot.y)
        if radius < 1e-9:
            self.rolling = False
            return
        angle = math.atan2(roll.y - pivot.y, roll.x - pivot.x)
        d_ang = 0.02 * self._roll_dir
        new_angle = angle + d_ang
        nx = pivot.x + radius * math.cos(new_angle)
        ny = pivot.y + radius * math.sin(new_angle)

        # ¿Choca con algún otro disco (no el pivote ni él mismo)?
        for i, p in enumerate(self.disks):
            if i in (self.roll_pivot, self.roll_disk):
                continue
            if math.hypot(nx - p.x, ny - p.y) < 2.0 * self.r_math - 1e-6:
                self.rolling = False   # se detiene al chocar
                return

        self.disks[self.roll_disk] = Point(nx, ny)
        self._roll_traveled += abs(d_ang)
        self._update_envelope_task()
        if self.cs_loops:
            self._rebuild_knot()
        self._redraw()
        if self._roll_traveled < 2 * math.pi:   # como máximo una vuelta completa
            self.after(20, self._roll_step)
        else:
            self.rolling = False

    def _on_drag(self, event):
        if self.mode.get() == "move" and self.dragged_disk_idx is not None:
            mx, my = self.screen_to_math(event.x, event.y)
            # El disco arrastrado sigue al cursor; los demás se empujan (elástico),
            # de modo que nunca se solapan y la envolvente se deforma sin cruzarlos.
            self.disks[self.dragged_disk_idx] = Point(mx, my)
            self._resolve_collisions(fixed=self.dragged_disk_idx)
            self._update_envelope_task()
            if self.cs_loops:
                self._rebuild_knot()
            self._redraw()

    def _resolve_collisions(self, fixed=None):
        """Empuja los discos para que no se solapen. *fixed* (si se da) no se mueve."""
        min_dist = 2.0 * self.r_math
        n = len(self.disks)
        for _ in range(30):
            moved = False
            for i in range(n):
                for j in range(i + 1, n):
                    pi, pj = self.disks[i], self.disks[j]
                    dx, dy = pj.x - pi.x, pj.y - pi.y
                    d = math.hypot(dx, dy)
                    if d >= min_dist - 1e-9:
                        continue
                    if d < 1e-9:
                        dx, dy, d = 1.0, 0.0, 1.0
                    ux, uy = dx / d, dy / d
                    overlap = min_dist - d
                    if i == fixed:
                        self.disks[j] = Point(pj.x + ux * overlap, pj.y + uy * overlap)
                    elif j == fixed:
                        self.disks[i] = Point(pi.x - ux * overlap, pi.y - uy * overlap)
                    else:
                        self.disks[i] = Point(pi.x - ux * overlap / 2, pi.y - uy * overlap / 2)
                        self.disks[j] = Point(pj.x + ux * overlap / 2, pj.y + uy * overlap / 2)
                    moved = True
            if not moved:
                break

    def _on_release(self, event):
        self.dragged_disk_idx = None

    def _add_disk_btn(self):
        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        import random
        if w > 1:
            mx, my = self.screen_to_math(w/2 + random.uniform(-20, 20), h/2 + random.uniform(-20, 20))
        else:
            mx, my = 0.0, 0.0
            
        # Evitar posición exacta ocupada empujando un poco
        for _ in range(10):
            overlap = False
            for p in self.disks:
                if math.hypot(p.x - mx, p.y - my) < 2.0 * self.r_math:
                    overlap = True
                    mx += self.r_math * 2.0
            if not overlap:
                break
                
        self.disks.append(Point(mx, my))
        self._update_envelope_task()
        self._redraw()

    def _on_double_click(self, event):
        if self.mode.get() == "move" or self.mode.get() == "draw":
            mx, my = self.screen_to_math(event.x, event.y)
            
            # Evitar crear discos superpuestos
            for p in self.disks:
                if math.hypot(p.x - mx, p.y - my) < 2.0 * self.r_math - 1e-4:
                    return # Falla silente si trata de crear dentro de otro

            self.disks.append(Point(mx, my))
            self._update_envelope_task()
            self._redraw()

    def _on_right_click(self, event):
        idx = self._get_clicked_disk(event)
        if idx is None:
            return
        if self.mode.get() == "cs_build":
            self._cs_toggle_orientation(idx)
        else:
            self._delete_disk(idx)

    def _delete_disk(self, idx):
        del self.disks[idx]
        self.custom_sequence = [seq for seq in self.custom_sequence if seq != idx]
        self.custom_sequence = [s if s < idx else s - 1 for s in self.custom_sequence]
        self._purge_cs_for_deleted_disk(idx)
        self._update_envelope_task()
        self._redraw()

    # ==================================================================
    # cs-Diagrama: panel lateral, construcción y cálculos
    # ==================================================================

    def _build_cs_panel(self):
        panel = ttk.Frame(self, padding=10, width=320)
        panel.pack(side=tk.RIGHT, fill=tk.Y)
        panel.pack_propagate(False)

        ttk.Label(
            panel, text="Nudo cs", font=("Inter", 13, "bold"), foreground="#2A6496"
        ).pack(anchor=tk.W)

        self.cs_text = tk.Text(
            panel, width=38, height=9, font=("Consolas", 9), wrap=tk.WORD, bg="#fbfcfe"
        )
        self.cs_text.pack(fill=tk.X, pady=(6, 6))

        self.lbl_length = tk.Label(
            panel, text="Longitud del núcleo: —", font=("Inter", 11, "bold"),
            fg="#2A6496", bg="#f4f5f7",
        )
        self.lbl_length.pack(anchor=tk.W)
        self.lbl_cycle = tk.Label(panel, text="C1: —", font=("Inter", 10, "bold"), fg="#777", bg="#f4f5f7")
        self.lbl_cycle.pack(anchor=tk.W)
        self.lbl_variation = tk.Label(
            panel, text="Primera variación: —", font=("Consolas", 9), justify=tk.LEFT,
            anchor=tk.W, wraplength=290, fg="#1c3046", bg="#f4f5f7",
        )
        self.lbl_variation.pack(fill=tk.X, pady=(4, 0))

        ttk.Separator(panel, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=8)
        ttk.Button(panel, text="Nuevo Lazo (enlace)", command=self._new_cs_loop).pack(fill=tk.X, pady=(0, 4))
        ttk.Button(panel, text="Borrar Nudo", command=self._clear_cs_route).pack(fill=tk.X)
        tk.Label(
            panel,
            text=("Modo «Construir Nudo (cs)»:\n"
                  "• clic en discos → arma la ruta\n"
                  "   (segmentos = tangentes comunes,\n"
                  "    arcos automáticos ⇒ C¹)\n"
                  "• clic derecho en un disco → invierte\n"
                  "   su giro ↺/↻ (opuestos ⇒ cruce)\n"
                  "• «Nuevo Lazo» para enlaces de\n"
                  "   varias componentes\n"
                  "• «Galería de Nudos» → cargar presets"),
            font=("Inter", 8), fg="#777", bg="#f4f5f7", justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(8, 0))

        self._rebuild_knot()

    def _cfg(self) -> DiskConfiguration:
        """DiskConfiguration con la posición actual de los discos."""
        cfg = DiskConfiguration()
        for p in self.disks:
            cfg.add_disk(Disk(Point(p.x, p.y), self.r_math))
        return cfg

    def _rebuild_knot(self):
        """Recalcula todos los lazos (curvas + diagramas) y refresca el panel."""
        centers = [Point(p.x, p.y) for p in self.disks]
        self._cs_results = []
        for loop in self.cs_loops:
            orient = [loop["orient"].get(d, 1) for d in loop["seq"]]
            self._cs_results.append(
                build_route(centers, self.r_math, list(loop["seq"]), orient)
            )
        self._refresh_cs_panel()

    def _refresh_cs_panel(self):
        if not hasattr(self, "cs_text"):
            return
        results = self._cs_results

        # Descripción de los lazos (↺ antihorario, ↻ horario)
        self.cs_text.delete("1.0", tk.END)
        if not self.cs_loops:
            self.cs_text.insert("1.0", "Sin nudo.\nClic en discos para armar un lazo.")
        else:
            lines = []
            for k, loop in enumerate(self.cs_loops):
                parts = [f"D{d}{'↺' if loop['orient'].get(d, 1) > 0 else '↻'}" for d in loop["seq"]]
                prefix = f"L{k + 1}: " if len(self.cs_loops) > 1 else "Ruta: "
                lines.append(prefix + " → ".join(parts))
            self.cs_text.insert("1.0", "\n".join(lines))

        ok_results = [r for r in results if r["ok"]]
        if not ok_results:
            self.lbl_length.config(text="Longitud del núcleo: —")
            self.lbl_cycle.config(text="Tangente imposible (discos solapados)", fg="#c0392b")
            self.lbl_variation.config(text="Primera variación: —", fg="#777")
            return

        # Longitud agregada de TODOS los lazos (incl. círculos): arcos (π) + rectas.
        arc_total = sum(r["arc_length"] for r in ok_results)
        seg_total = sum(r["segment_length"] for r in ok_results)
        length = arc_total + seg_total
        text = f"{arc_total / math.pi:g}π + {seg_total:.2f}  (Total: {length:.4f})"
        self.lbl_length.config(text=f"Longitud del núcleo: {text}")
        self.lbl_measure.config(text=f"Nudo cs:  {text} u")

        cfg = self._cfg()
        diagrammed = [r for r in ok_results if r["diagram"] is not None]
        all_valid = all(r["valid"] for r in ok_results)
        all_c1 = all(r["diagram"].validate_c1(cfg) for r in diagrammed)
        if not all_valid:
            self.lbl_cycle.config(text="⚠ La ruta atraviesa discos (no embebido)", fg="#c0392b")
        else:
            self.lbl_cycle.config(text=f"C1: {'OK' if all_c1 else 'FALLA'}",
                                  fg="#2e7d32" if all_c1 else "#c0392b")

        # Lazos solo-círculo (un disco) no tienen segmentos ⇒ primera variación nula.
        if not diagrammed:
            self.lbl_variation.config(text="Primera variación: 0 (círculos, sin segmentos)", fg="#777")
            return

        # Primera variación: g_red es aditivo sobre los segmentos de todos los lazos.
        contacts = detect_contact_set(cfg)
        A = build_rolling_matrix(cfg, contacts)
        K = rolling_space_basis(A)
        g = np.zeros(2 * len(self.disks))
        for r in diagrammed:
            g += build_gradient(r["diagram"], cfg)
        is_stat, residual = is_stationary_kernel(g, K)
        status = "ESTACIONARIO" if is_stat else f"no estacionario (residuo {residual:.1e})"
        self.lbl_variation.config(
            text=f"Contactos |E|={len(contacts)}, dim Roll={K.shape[1]}\nPrimera variación: {status}",
            fg="#2e7d32" if is_stat else "#c0392b",
        )

    def _open_gallery(self):
        """Abre la galería de nudos en una ventana aparte."""
        from knots_v2.gallery import KnotGallery
        KnotGallery(self, on_load=self._load_knot)

    def _load_knot(self, name: str):
        """Carga CUALQUIER nudo de la galería en el editor.

        Si tiene construcción cs (tóricos + twist), la carga MANIPULABLE (discos
        arrastrables + primera variación), como antes. Si no (6₂,6₃,7₃₋₇), muestra
        el diagrama estándar (solo vista).
        """
        from knots_v2.presets import PRESETS
        from knots_v2.rational import ROLFSEN_2BRIDGE
        conway = ROLFSEN_2BRIDGE.get(name)
        preset = next((p for p in PRESETS if p.conway and p.conway == conway), None)
        if preset is not None:
            self._load_preset(preset)
        else:
            from knots_v2.pd_draw import knot_layout
            self.loaded_layout = knot_layout(name)
        self._redraw()
        self.lift()
        self.focus_force()

    def _load_preset(self, preset):
        """Carga un preset de la galería en el editor (reemplaza discos y lazos)."""
        self.loaded_layout = None  # sale del modo vista, vuelve al editor cs
        self.disks = [Point(x, y) for x, y in preset.disks]
        self.cs_loops = []
        for sequence, orientations in preset.loops:
            orient = {d: orientations[pos] for pos, d in enumerate(sequence)}
            self.cs_loops.append({"seq": list(sequence), "orient": orient})
        self.mode.set("cs_build")
        self.custom_sequence = []
        self.dragged_disk_idx = None
        self._update_envelope_task()
        self._rebuild_knot()
        self._redraw()
        self.lift()
        self.focus_force()

    def _clear_cs_route(self):
        self.loaded_layout = None  # cierra la vista del diagrama estándar cargado
        self.cs_loops = []
        self._cs_results = []
        self._rebuild_knot()
        # Restaura de inmediato la etiqueta superior a la envolvente.
        self.lbl_measure.config(text=getattr(self, "_env_measure_text", "Envolvente: —"))
        self._update_envelope_task()
        self._redraw()

    def _new_cs_loop(self):
        """Inicia un nuevo lazo vacío (para enlaces de varias componentes)."""
        if not self.cs_loops or self.cs_loops[-1]["seq"]:
            self.cs_loops.append({"seq": [], "orient": {}})

    # ------------------------------------------------------------------
    # Interacción del modo construcción
    # ------------------------------------------------------------------

    def _cs_build_click(self, event, disk_idx):
        """Clic izquierdo en modo nudo: añade el disco al lazo activo (el último)."""
        if disk_idx is None:
            return
        if not self.cs_loops:
            self.cs_loops.append({"seq": [], "orient": {}})
        loop = self.cs_loops[-1]
        loop["seq"].append(disk_idx)
        loop["orient"].setdefault(disk_idx, 1)
        self._rebuild_knot()
        self._redraw()

    def _cs_toggle_orientation(self, disk_idx):
        """Clic derecho en modo nudo: invierte el giro del disco en todos los lazos."""
        flipped = False
        for loop in self.cs_loops:
            if disk_idx in loop["orient"]:
                loop["orient"][disk_idx] = -loop["orient"][disk_idx]
                flipped = True
        if flipped:
            self._rebuild_knot()
            self._redraw()

    def _purge_cs_for_deleted_disk(self, idx):
        """Reindexa/elimina los lazos tras borrar el disco *idx*."""
        new_loops = []
        for loop in self.cs_loops:
            seq = [d - 1 if d > idx else d for d in loop["seq"] if d != idx]
            orient = {(d - 1 if d > idx else d): s
                      for d, s in loop["orient"].items() if d != idx}
            if seq:
                new_loops.append({"seq": seq, "orient": orient})
        self.cs_loops = new_loops
        self._rebuild_knot()

    # ------------------------------------------------------------------
    # Dibujo del overlay (la curva C¹ del nudo, con cruces)
    # ------------------------------------------------------------------

    def _draw_cs_overlay(self):
        # Cada lazo es una polilínea (los cruces aparecen naturalmente).
        # Naranja si el lazo atraviesa discos (no embebido); rojo si es válido.
        for res in self._cs_results:
            poly = res.get("polyline", [])
            if len(poly) < 2:
                continue
            color = "#c0392b" if res.get("valid", True) else "#e67e22"
            coords = []
            for p in poly:
                sx, sy = self.math_to_screen(p.x, p.y)
                coords.extend([sx, sy])
            self.canvas.create_line(coords, fill=color, width=4, joinstyle=tk.ROUND, capstyle=tk.ROUND)

        # Orden y giro de cada disco en cada lazo.
        for loop in self.cs_loops:
            for order, d in enumerate(loop["seq"]):
                if d >= len(self.disks):
                    continue
                c = self.disks[d]
                sx, sy = self.math_to_screen(c.x, c.y)
                spin = "↺" if loop["orient"].get(d, 1) > 0 else "↻"
                self.canvas.create_text(
                    sx, sy - 18, text=f"{order + 1}{spin}", anchor=tk.CENTER,
                    fill="#c0392b", font=("Inter", 11, "bold"),
                )

if __name__ == "__main__":
    app = KnotsApp()
    app.mainloop()
