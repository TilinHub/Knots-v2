import math
import tkinter as tk
from tkinter import ttk
import threading
import queue
from typing import List, Tuple

from knots_v2.domain.primitives import Point
from knots_v2.compute.convex_hull import ConvexHull

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
                    self.result_queue.put({"envelope": [], "measure": 0.0})
                    continue
                
                # Definir Puntos y Orden
                if custom_seq:
                    # Envolvente Customizada
                    route_points = [centers[i] for i in custom_seq]
                else:
                    # Envolvente Por Defecto
                    route_points = self.hull_computer._graham_scan(centers)
                
                envelope_contour = []
                measure = 0.0

                n = len(route_points)
                if n == 0:
                    pass
                elif n == 1:
                    measure = 2 * math.pi * radius
                    cx, cy = route_points[0].x, route_points[0].y
                    for i in range(40):
                        ang = 2 * math.pi * i / 40
                        envelope_contour.append((cx + radius * math.cos(ang), cy + radius * math.sin(ang)))
                elif n == 2:
                    dist = math.hypot(route_points[1].x - route_points[0].x, route_points[1].y - route_points[0].y)
                    measure = 2 * dist + 2 * math.pi * radius
                    if dist < 1e-9:
                        dx, dy = 1.0, 0.0
                    else:
                        dx, dy = (route_points[1].x - route_points[0].x) / dist, (route_points[1].y - route_points[0].y) / dist
                    nx, ny = dy, -dx
                    
                    envelope_contour.append((route_points[0].x + radius*nx, route_points[0].y + radius*ny))
                    envelope_contour.append((route_points[1].x + radius*nx, route_points[1].y + radius*ny))
                    for i in range(1, 20):
                        ang = math.atan2(ny, nx) + math.pi * i / 20
                        envelope_contour.append((route_points[1].x + radius * math.cos(ang), route_points[1].y + radius * math.sin(ang)))
                    
                    envelope_contour.append((route_points[1].x - radius*nx, route_points[1].y - radius*ny))
                    envelope_contour.append((route_points[0].x - radius*nx, route_points[0].y - radius*ny))
                    for i in range(1, 20):
                        ang = math.atan2(-ny, -nx) + math.pi * i / 20
                        envelope_contour.append((route_points[0].x + radius * math.cos(ang), route_points[0].y + radius * math.sin(ang)))
                else:
                    perimeter = 0.0
                    angles = []
                    normals = []
                    for i in range(n):
                        p1 = route_points[i]
                        p2 = route_points[(i + 1) % n]
                        dx, dy = p2.x - p1.x, p2.y - p1.y
                        dist = math.hypot(dx, dy)
                        perimeter += dist
                        
                        if dist < 1e-9:
                            nx, ny = 1.0, 0.0
                        else:
                            nx, ny = dy/dist, -dx/dist
                        normals.append((nx, ny))
                    
                    measure = perimeter
                    
                    for i in range(n):
                        p = route_points[i]
                        n_prev = normals[(i - 1) % n]
                        n_cur = normals[i]
                        
                        a_start = math.atan2(n_prev[1], n_prev[0])
                        a_end = math.atan2(n_cur[1], n_cur[0])
                        
                        ang_diff = (a_end - a_start) % (2 * math.pi)
                        
                        if ang_diff < 1e-9: 
                            pass 

                        measure += radius * ang_diff
                            
                        # Arc creation for point p CCW to wrap the outside
                        steps = max(5, int(30 * ang_diff / (2 * math.pi)))
                        if steps > 0:
                            for j in range(steps + 1):
                                ang = a_start + ang_diff * (j / steps)
                                envelope_contour.append((p.x + radius * math.cos(ang), p.y + radius * math.sin(ang)))
                            
                self.result_queue.put({"envelope": envelope_contour, "measure": measure})
                
            except Exception as e:
                print(f"Error en Worker de Envolvente: {e}")

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
        
        self.mode = tk.StringVar(value="move")
        self.show_envelope = tk.BooleanVar(value=True)
        
        self.task_queue = queue.Queue()
        self.result_queue = queue.Queue()
        self.worker = EnvelopeWorker(self.task_queue, self.result_queue)
        self.worker.start()
        
        self._build_ui()
        self._update_envelope_task()
        self.after(50, self._check_results)

    def _build_ui(self):
        self.top_frame = ttk.Frame(self, padding=15)
        self.top_frame.pack(side=tk.TOP, fill=tk.X)
        
        # Resumen Metric
        self.lbl_measure = ttk.Label(self.top_frame, text="Medida de la envolvente: 0.000", font=("Inter", 16, "bold"), foreground="#2A6496")
        self.lbl_measure.pack(side=tk.LEFT)
        
        # Tools
        tools_frame = ttk.Frame(self.top_frame)
        tools_frame.pack(side=tk.RIGHT)

        ttk.Radiobutton(tools_frame, text="Mover (Arrastrar / Doble Click: Añadir)", variable=self.mode, value="move").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(tools_frame, text="Delinear Envolvente", variable=self.mode, value="draw").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(tools_frame, text="Borrar Disco", variable=self.mode, value="delete").pack(side=tk.LEFT, padx=5)
        
        ttk.Separator(tools_frame, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=10, fill=tk.Y)
        ttk.Button(tools_frame, text="Borrar Recorrido", command=self._clear_sequence).pack(side=tk.LEFT, padx=4)
        ttk.Checkbutton(tools_frame, text="Ver Envolvente", variable=self.show_envelope, command=self._redraw).pack(side=tk.LEFT, padx=5)

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
        try:
            while not self.result_queue.empty():
                res = self.result_queue.get_nowait()
                self.current_envelope = res["envelope"]
                self.lbl_measure.config(text=f"Medida de la envolvente: {res['measure']:.4f}")
                self._redraw()
        except queue.Empty: pass
        finally: self.after(50, self._check_results)

    def _redraw(self):
        self.canvas.delete("all")
        self._draw_grid()
        r_screen = self.r_math * self.scale
        
        # 1. Dibujar Contorno (Envolvente Elastic CS)
        if getattr(self, "current_envelope", None) and self.show_envelope.get():
            coords = []
            for px, py in self.current_envelope:
                sx, sy = self.math_to_screen(px, py)
                coords.extend([sx, sy])
            if len(coords) >= 4:
                self.canvas.create_polygon(
                    coords, fill="", outline="#1b1c20", width=8, 
                    joinstyle=tk.ROUND, smooth=False
                )

        # 2. Dibujar Discos
        for i, p in enumerate(self.disks):
            sx, sy = self.math_to_screen(p.x, p.y)
            color = "#a3d1ff"
            outline_c = "#2A6496"
            
            if self.mode.get() == "draw" and i in self.custom_sequence:
                color = "#ffd27a"
                outline_c = "#e09000"
                
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

    def _get_clicked_disk(self, event) -> int | None:
        mx, my = self.screen_to_math(event.x, event.y)
        for i, p in enumerate(self.disks):
            if math.hypot(p.x - mx, p.y - my) <= self.r_math:
                return i
        return None

    def _on_press(self, event):
        idx = self._get_clicked_disk(event)
        
        if self.mode.get() == "delete":
            if idx is not None:
                self._delete_disk(idx)
        
        elif self.mode.get() == "draw":
            if idx is not None:
                self.custom_sequence.append(idx)
                self._update_envelope_task()
                self._redraw()
                
        else: # move mode
            self.dragged_disk_idx = idx

    def _on_drag(self, event):
        if self.mode.get() == "move" and self.dragged_disk_idx is not None:
            mx, my = self.screen_to_math(event.x, event.y)
            
            # Resolución de colisiones (3 pasadas para estabilidad con multiples)
            for _ in range(3):
                for i, p in enumerate(self.disks):
                    if i != self.dragged_disk_idx:
                        dist = math.hypot(mx - p.x, my - p.y)
                        min_dist = 2.0 * self.r_math
                        if dist < min_dist:
                            if dist == 0:
                                mx += 0.01; my += 0.01
                                dist = math.hypot(mx - p.x, my - p.y)
                            overlap = min_dist - dist
                            mx += (mx - p.x) / dist * overlap
                            my += (my - p.y) / dist * overlap

            self.disks[self.dragged_disk_idx] = Point(mx, my)
            self._update_envelope_task()
            self._redraw()

    def _on_release(self, event):
        self.dragged_disk_idx = None

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
        if idx is not None:
            self._delete_disk(idx)

    def _delete_disk(self, idx):
        del self.disks[idx]
        self.custom_sequence = [seq for seq in self.custom_sequence if seq != idx]
        self.custom_sequence = [s if s < idx else s - 1 for s in self.custom_sequence]
        self._update_envelope_task()
        self._redraw()

if __name__ == "__main__":
    app = KnotsApp()
    app.mainloop()
