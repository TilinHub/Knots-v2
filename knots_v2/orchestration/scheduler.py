"""Planificador de tareas con ejecución paralela.

Soporta dos modos:
- ``"thread"``: ThreadPoolExecutor, ideal para tareas con I/O (lectura de archivos,
  llamadas HTTP, etc.).
- ``"process"``: ProcessPoolExecutor, ideal para tareas CPU-intensivas (computo
  geométrico pesado). Nota: las funciones deben ser serializables con pickle.
"""

from __future__ import annotations

import logging
from concurrent.futures import (
    Future,
    ProcessPoolExecutor,
    ThreadPoolExecutor,
    as_completed,
)
from typing import Any, Callable

from .events import EventBus

logger = logging.getLogger(__name__)


class TaskScheduler:
    """Ejecuta una lista de callables de forma paralela y emite eventos de progreso.

    Args:
        executor_type: ``"thread"`` (por defecto) o ``"process"``.
        max_workers: Número máximo de workers simultáneos.
        event_bus: Bus de eventos para notificaciones de progreso. Si no se
            provee, se crea uno nuevo.

    Example::

        scheduler = TaskScheduler(executor_type="thread", max_workers=4)
        results = scheduler.run([lambda: calcular(c) for c in configuraciones])
    """

    def __init__(
        self,
        executor_type: str = "thread",
        max_workers: int = 4,
        event_bus: EventBus | None = None,
    ) -> None:
        if executor_type not in ("thread", "process"):
            raise ValueError(
                f"executor_type debe ser 'thread' o 'process', se recibió '{executor_type}'"
            )
        self.executor_type = executor_type
        self.max_workers = max_workers
        self.event_bus = event_bus if event_bus is not None else EventBus()

    def run(self, tasks: list[Callable[[], Any]]) -> list[Any]:
        """Ejecuta todas las tareas en paralelo y retorna sus resultados.

        Los resultados se devuelven en el **mismo orden** que las tareas de entrada.
        Si una tarea lanza una excepción, su posición en el resultado es ``None``
        y se emite un evento ``task_failed``.

        Args:
            tasks: Lista de callables sin argumentos.

        Returns:
            Lista de resultados en el mismo orden que *tasks*.
        """
        if not tasks:
            return []

        ExecutorClass = (
            ThreadPoolExecutor if self.executor_type == "thread" else ProcessPoolExecutor
        )

        total = len(tasks)
        results: list[Any] = [None] * total
        completed_count = 0

        with ExecutorClass(max_workers=self.max_workers) as executor:
            # Mapear cada future a su índice original para mantener el orden
            index_by_future: dict[Future, int] = {}

            for idx, task in enumerate(tasks):
                self.event_bus.emit("task_started", {"task_index": idx, "total": total})
                future = executor.submit(task)
                index_by_future[future] = idx

            for future in as_completed(index_by_future):
                idx = index_by_future[future]
                try:
                    result = future.result()
                    results[idx] = result
                    self.event_bus.emit(
                        "task_completed", {"task_index": idx, "result": result}
                    )
                except Exception as exc:
                    logger.error("Tarea %d falló: %s", idx, exc)
                    self.event_bus.emit(
                        "task_failed", {"task_index": idx, "error": str(exc)}
                    )
                finally:
                    completed_count += 1
                    self.event_bus.emit(
                        "progress",
                        {"completed": completed_count, "total": total},
                    )

        return results
