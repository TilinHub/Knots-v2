"""Censo paralelo de configuraciones de discos.

Ejecuta el pipeline completo (envolvente, grafo de contacto, convex hull)
sobre una lista de configuraciones y retorna los resultados enriquecidos
con metadatos de tiempo.
"""

from __future__ import annotations

import time
import logging
from typing import Any

from ..domain.configuration import DiskConfiguration
from ..compute.envelope import EnvelopeComputer
from ..compute.contact_graph import ContactGraph
from ..compute.convex_hull import ConvexHull
from .cache import ResultCache
from .scheduler import TaskScheduler

logger = logging.getLogger(__name__)


class ParallelCensus:
    """Procesa en paralelo una lista de configuraciones y retorna resultados.

    Cada resultado tiene la forma::

        {
            "envelope":      [{"x": ..., "y": ...}, ...],
            "contact_graph": {0: [1, 2], 1: [0], ...},
            "convex_hull":   [{"x": ..., "y": ...}, ...],
            "metadata": {
                "n_disks":          int,
                "elapsed_seconds":  float,
                "is_valid":         bool,
            },
        }

    Los resultados se cachean automáticamente: si la misma configuración
    aparece más de una vez en la lista, se computa solo una vez.

    Args:
        scheduler: Planificador a usar. Si no se provee, se crea uno por defecto
            con ThreadPoolExecutor y 4 workers.
    """

    def __init__(self, scheduler: TaskScheduler | None = None) -> None:
        self.scheduler = scheduler if scheduler is not None else TaskScheduler()
        self.cache = ResultCache()

    def run(self, configurations: list[DiskConfiguration]) -> list[dict[str, Any] | None]:
        """Procesa todas las configuraciones en paralelo.

        Args:
            configurations: Lista de configuraciones a analizar.

        Returns:
            Lista de resultados en el mismo orden que *configurations*.
            Un elemento es ``None`` si su tarea falló.
        """
        tasks = [self._make_task(config) for config in configurations]
        return self.scheduler.run(tasks)

    # ------------------------------------------------------------------
    # Construcción de tareas
    # ------------------------------------------------------------------

    def _make_task(self, config: DiskConfiguration):
        """Retorna un callable que analiza *config* y usa la caché si es posible."""

        def task() -> dict[str, Any]:
            cache_key = ResultCache.config_key(config)

            cached = self.cache.get(cache_key)
            if cached is not None:
                logger.debug("Cache hit para configuración con %d discos", len(config))
                return cached

            start = time.perf_counter()

            envelope_pts = EnvelopeComputer().compute(config)
            contact_graph = ContactGraph().from_config(config)
            hull_pts = ConvexHull().compute(config)

            elapsed = time.perf_counter() - start

            result: dict[str, Any] = {
                "envelope": [{"x": p.x, "y": p.y} for p in envelope_pts],
                "contact_graph": contact_graph,
                "convex_hull": [{"x": p.x, "y": p.y} for p in hull_pts],
                "metadata": {
                    "n_disks": len(config),
                    "elapsed_seconds": elapsed,
                    "is_valid": config.validate(),
                },
            }

            self.cache.set(cache_key, result)
            return result

        return task
