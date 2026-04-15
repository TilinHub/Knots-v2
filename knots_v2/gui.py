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
                # Obtenemos la última tarea (ignorar encoladas si el usuario mueve rápido)
                task = self.task_queue.get()
                while not self.task_queue.empty():
                    try:
                        task = self.task_queue.get_nowait()
                    except queue.Empty:
                        break
                
                centers, radius = task
                if not centers:
                    self.result_queue.put({"envelope": [], "measure": 0.0})
                    continue
                
                # Para radio constante, CS = Convex Hull de centros + offsets
                hull_points = self.hull_computer._graham_scan(centers)
                
                envelope_contour = []
                measure = 0.0

                n = len(hull_points)
                if n == 0:
                    pass
                elif n == 1:
                    measure = 2 * math.pi * radius
                    # 1 círculo
                    cx, cy = hull_points[0].x, hull_points[0].y
                    for i in range(40):
                        ang = 2 * math.pi * i / 40
                        envelope_contour.append((cx + radius * math.cos(ang), cy + radius * math.sin(ang)))
                elif n == 2:
                    dist = math.hypot(hull_points[1].x - hull_points[0].x, hull_points[1].y - hull_points[0].y)
                    measure = 2 * dist + 2 * math.pi * radius
                    # Cápsula
                    dx = (hull_points[1].x - hull_points[0].x) / dist
                    dy = (hull_points[1].y - hull_points[0].y) / dist
                    nx, ny = dy, -dx
                    
                    envelope_contour.append((hull_points[0].x + radius*nx, hull_points[0].y + radius*ny))
                    envelope_contour.append((hull_points[1].x + radius*nx, hull_points[1].y + radius*ny))
                    for i in range(1, 20):
                        ang = math.atan2(ny, nx) - math.pi * i / 20
                        envelope_contour.append((hull_points[1].x + radius * math.cos(ang), hull_points[1].y + radius * math.sin(ang)))
                    
                    envelope_contour.append((hull_points[1].x - radius*nx, hull_points[1].y - radius*ny))
                    envelope_contour.append((hull_points[0].x - radius*nx, hull_points[0].y - radius*ny))
                    for i in range(1, 20):
                        ang = math.atan2(-ny, -nx) - math.pi * i / 20
                        envelope_contour.append((hull_points[0].x + radius * math.cos(ang), hull_points[0].y + radius * math.sin(ang)))
                    
                else:
                    perimeter = 0.0
                    angles = []
                    normals = []
                    for i in range(n):
                        p1 = hull_points[i]
                        p2 = hull_points[(i + 1) % n]
                        dx, dy = p2.x - p1.x, p2.y - p1.y
                        dist = math.hypot(dx, dy)
                        perimeter += dist
                        nx, ny = dy/dist, -dx/dist
                        normals.append((nx, ny))
                    
                    measure = perimeter + 2 * math.pi * radius
                    
                    for i in range(n):
                        p = hull_points[i]
                        n_prev = normals[(i - 1) % n]
                        n_cur = normals[i]
                        
                        a_start = math.atan2(n_prev[1], n_prev[0])
                        a_end = math.atan2(n_cur[1], n_cur[0])
                        
                        if a_start < a_end:
                            a_start += 2 * math.pi
                        
                        ang_diff = a_start - a_end
                        if ang_diff < 0:
                            ang_diff += 2 * math.pi
                            
                        # Dibujar arco para este vértice
                        steps = max(5, int(20 * ang_diff / (2 * math.pi)))
                        for j in range(steps + 1):
                            ang = a_start - ang_diff * (j / steps)
                            envelope_contour.append((p.x + radius * math.cos(ang), p.y + radius * math.sin(ang)))
                            
                self.result_queue.put({"envelope": envelope_contour, "measure": measure})
                
            except Exception as e:
                print(f"Error en Worker de Envolvente: {e}")

class KnotsApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Knots-v2: Visor Interactivo (POO y Paralelismo)")
        self.geometry("900x700")
        
        # Estado Numérico
        self.scale = 80.0
        self.r_math = 1.0  # Radio fijo en espacio espacial para cálculo
        self.disks = [
            Point(1.99, 2.45),
            Point(0.02, -0.22),
            Point(-2.38, -2.83),
            Point(3.00, -2.63)
        ]
        
        self.dragged_disk_idx = None
        self.show_envelope = tk.BooleanVar(value=True)
        
        # Concurrencia
        self.task_queue = queue.Queue()
        self.result_queue = queue.Queue()
        self.worker = EnvelopeWorker(self.task_queue, self.result_queue)
        self.worker.start()
        
        self._build_ui()
        self._update_envelope_task() # Solicitud inicial
        
        # Loop chequeo cola
        self.after(50, self._check_results)

    def _build_ui(self):
        self.top_frame = ttk.Frame(self, padding=10)
        self.top_frame.pack(side=tk.TOP, fill=tk.X)
        
        self.lbl_measure = ttk.Label(self.top_frame, text="Medida de la envolvente: 0.00", font=("Arial", 14, "bold"))
        self.lbl_measure.pack(side=tk.LEFT)
        
        self.btn_toggle = ttk.Checkbutton(self.top_frame, text="Mostrar Dibujo de Envolvente", variable=self.show_envelope, command=self._redraw)
        self.btn_toggle.pack(side=tk.RIGHT)
        
        # Herramienta para resetear  o agregar si amerita
        self.btn_draw = ttk.Button(self.top_frame, text="Centrar Vista", command=self._center_view)
        self.btn_draw.pack(side=tk.RIGHT, padx=10)
        
        self.canvas = tk.Canvas(self, bg="white")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        
        # Grid visual como en la imagen
        self.bind("<Configure>", lambda e: self._redraw())
        
    def math_to_screen(self, x, y):
        w = self.canvas.winfo_width() / 2
        h = self.canvas.winfo_height() / 2
        return w + x * self.scale, h - y * self.scale
        
    def screen_to_math(self, x, y):
        w = self.canvas.winfo_width() / 2
        h = self.canvas.winfo_height() / 2
        return (x - w) / self.scale, (h - y) / self.scale

    def _draw_grid(self):
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w <= 1: return
        
        cx, cy = w/2, h/2
        grid_step = self.scale * 0.5
        
        # Verticals
        x = cx % grid_step
        while x < w:
            self.canvas.create_line(x, 0, x, h, fill="#eeeeee")
            x += grid_step
            
        # Horizontals
        y = cy % grid_step
        while y < h:
            self.canvas.create_line(0, y, w, y, fill="#eeeeee")
            y += grid_step

    def _update_envelope_task(self):
        # Desencadenar proceso en background
        self.task_queue.put(([Point(p.x, p.y) for p in self.disks], self.r_math))

    def _check_results(self):
        try:
            while not self.result_queue.empty():
                res = self.result_queue.get_nowait()
                self.current_envelope = res["envelope"]
                self.lbl_measure.config(text=f"Medida de la envolvente: {res['measure']:.4f}")
                self._redraw()
        except queue.Empty:
            pass
        finally:
            self.after(50, self._check_results)

    def _redraw(self):
        self.canvas.delete("all")
        self._draw_grid()
        
        r_screen = self.r_math * self.scale
        
        # 1. Dibujar envolvente (gruesa y negra)
        if getattr(self, "current_envelope", None) and self.show_envelope.get():
            coords = []
            for px, py in self.current_envelope:
                sx, sy = self.math_to_screen(px, py)
                coords.extend([sx, sy])
            if len(coords) >= 4:
                self.canvas.create_polygon(coords, fill="", outline="black", width=6, joinstyle=tk.ROUND, smooth=False)

        # 2. Dibujar Discos (celestes con borde y coordenadas)
        for i, p in enumerate(self.disks):
            sx, sy = self.math_to_screen(p.x, p.y)
            self.canvas.create_oval(
                sx - r_screen, sy - r_screen, sx + r_screen, sy + r_screen,
                fill="#87CEEB", outline="black", width=3, tags=f"disk_{i}"
            )
            # Punto central
            self.canvas.create_oval(sx - 2, sy - 2, sx + 2, sy + 2, fill="black")
            
            # Texto coordenadas
            text_str = f"({p.x:.2f}, {p.y:.2f})"
            self.canvas.create_text(
                sx, sy + 15, text=text_str, fill="#333333", font=("Courier New", 10, "bold")
            )

    def _center_view(self):
        self.scale = 80.0
        self._redraw()

    def _on_press(self, event):
        mx, my = self.screen_to_math(event.x, event.y)
        self.dragged_disk_idx = None
        for i, p in enumerate(self.disks):
            if math.hypot(p.x - mx, p.y - my) <= self.r_math:
                self.dragged_disk_idx = i
                break

    def _on_drag(self, event):
        if self.dragged_disk_idx is not None:
            mx, my = self.screen_to_math(event.x, event.y)
            self.disks[self.dragged_disk_idx] = Point(mx, my)
            self._update_envelope_task() # Actualizamos envolvente en paralelo
            self._redraw()

    def _on_release(self, event):
        self.dragged_disk_idx = None

if __name__ == "__main__":
    app = KnotsApp()
    app.mainloop()
