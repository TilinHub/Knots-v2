"""Ejemplo de uso end-to-end de Knots v2.

Demuestra el flujo completo:
1. Crear una DiskConfiguration con varios discos.
2. Suscribirse a eventos del bus para monitorear el progreso.
3. Ejecutar un censo paralelo con ParallelCensus.
4. Exportar el resultado a SVG.
5. Serializar el resultado a JSON.
6. Imprimir un resumen en la terminal.

Para ejecutar::

    python main.py
"""

from __future__ import annotations

import logging
from pathlib import Path

from knots_v2.domain.configuration import DiskConfiguration
from knots_v2.domain.disk import Disk
from knots_v2.domain.primitives import Point
from knots_v2.orchestration.census import ParallelCensus
from knots_v2.orchestration.events import EventBus
from knots_v2.orchestration.scheduler import TaskScheduler
from knots_v2.output.serializer import JSONSerializer
from knots_v2.output.svg_exporter import SVGExporter

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)-8s %(name)s — %(message)s",
)
logger = logging.getLogger("knots.main")


def build_example_config() -> DiskConfiguration:
    """Construye una configuración de ejemplo con cinco discos."""
    cfg = DiskConfiguration()
    cfg.add_disk(Disk(Point(0.0, 0.0), 1.5))
    cfg.add_disk(Disk(Point(4.0, 0.0), 1.5))
    cfg.add_disk(Disk(Point(8.0, 0.0), 1.0))
    cfg.add_disk(Disk(Point(2.0, 3.5), 1.5))
    cfg.add_disk(Disk(Point(6.0, 3.5), 1.2))
    return cfg


def main() -> None:
    # ------------------------------------------------------------------
    # 1. Configuración de discos
    # ------------------------------------------------------------------
    config = build_example_config()
    logger.info("Configuración creada: %d discos", len(config))
    logger.info("Válida (sin superposición): %s", config.validate())

    # ------------------------------------------------------------------
    # 2. Bus de eventos para monitorear el progreso en tiempo real
    # ------------------------------------------------------------------
    bus = EventBus()
    bus.subscribe(
        "task_started",
        lambda d: logger.info("► Tarea %d iniciada (total: %d)", d["task_index"], d["total"]),
    )
    bus.subscribe(
        "task_completed",
        lambda d: logger.info("✓ Tarea %d completada", d["task_index"]),
    )
    bus.subscribe(
        "task_failed",
        lambda d: logger.error("✗ Tarea %d falló: %s", d["task_index"], d["error"]),
    )
    bus.subscribe(
        "progress",
        lambda d: logger.info("  Progreso: %d/%d", d["completed"], d["total"]),
    )

    # ------------------------------------------------------------------
    # 3. Censo paralelo
    # ------------------------------------------------------------------
    scheduler = TaskScheduler(executor_type="thread", max_workers=4, event_bus=bus)
    census = ParallelCensus(scheduler=scheduler)

    # Procesamos tres configuraciones distintas para mostrar el paralelismo
    config2 = DiskConfiguration()
    config2.add_disk(Disk(Point(0.0, 0.0), 1.0))
    config2.add_disk(Disk(Point(2.5, 0.0), 1.0))
    config2.add_disk(Disk(Point(1.25, 2.0), 1.0))

    config3 = DiskConfiguration()
    config3.add_disk(Disk(Point(0.0, 0.0), 2.0))
    config3.add_disk(Disk(Point(5.0, 0.0), 2.0))

    all_results = census.run([config, config2, config3])

    # ------------------------------------------------------------------
    # 4. Resumen en consola
    # ------------------------------------------------------------------
    print("\n" + "=" * 55)
    print("  KNOTS v2 — RESUMEN DEL CENSO")
    print("=" * 55)
    for i, result in enumerate(all_results):
        if result is None:
            print(f"\n  Config #{i}: FALLÓ")
            continue
        meta = result["metadata"]
        print(f"\n  Config #{i}:")
        print(f"    Discos           : {meta['n_disks']}")
        print(f"    Válida           : {meta['is_valid']}")
        print(f"    Tiempo (s)       : {meta['elapsed_seconds']:.5f}")
        print(f"    Puntos envolvente: {len(result['envelope'])}")
        print(f"    Puntos hull      : {len(result['convex_hull'])}")
        n_aristas = sum(len(v) for v in result["contact_graph"].values()) // 2
        print(f"    Aristas contacto : {n_aristas}")

    # ------------------------------------------------------------------
    # 5. Exportar la primera configuración a SVG
    # ------------------------------------------------------------------
    if all_results[0] is not None:
        svg_path = Path("output.svg")
        svg_content = SVGExporter().export(config, all_results[0])
        svg_path.write_text(svg_content, encoding="utf-8")
        print(f"\n  SVG exportado → {svg_path.resolve()}")

    # ------------------------------------------------------------------
    # 6. Serializar todos los resultados a JSON
    # ------------------------------------------------------------------
    json_path = Path("output.json")
    serializer = JSONSerializer()
    json_path.write_text(serializer.serialize(all_results), encoding="utf-8")
    print(f"  JSON guardado  → {json_path.resolve()}")
    print("=" * 55 + "\n")


if __name__ == "__main__":
    main()
