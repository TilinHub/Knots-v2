"""Interfaz de línea de comandos para Knots v2.

Usa Typer para definir tres comandos:
- ``analyze``: analiza una sola configuración desde un archivo JSON.
- ``census``:  corre un censo paralelo sobre un directorio de archivos JSON.
- ``export``:  exporta una configuración a SVG.

Uso::

    knots analyze config.json
    knots census ./configs/ --output ./results/ --workers 8
    knots export config.json --output salida.svg
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import typer

from ..domain.configuration import DiskConfiguration
from ..domain.disk import Disk
from ..domain.primitives import Point
from ..orchestration.census import ParallelCensus
from ..orchestration.events import EventBus
from ..orchestration.scheduler import TaskScheduler
from .serializer import JSONSerializer
from .svg_exporter import SVGExporter

app = typer.Typer(
    name="knots",
    help="Knots v2 — Análisis geométrico de configuraciones de discos.",
    add_completion=False,
)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _load_config(path: Path) -> DiskConfiguration:
    """Carga una DiskConfiguration desde un archivo JSON."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        typer.echo(f"Error: el archivo '{path}' no es JSON válido: {e}", err=True)
        raise typer.Exit(1)

    config = DiskConfiguration()
    for disk_data in data.get("disks", []):
        try:
            center = Point(disk_data["center"]["x"], disk_data["center"]["y"])
            config.add_disk(Disk(center, disk_data["radius"]))
        except (KeyError, ValueError) as e:
            typer.echo(f"Error al parsear disco: {e}", err=True)
            raise typer.Exit(1)

    return config


def _progress_callback(data: dict) -> None:
    """Muestra el progreso en la terminal."""
    completed = data.get("completed", 0)
    total = data.get("total", 0)
    typer.echo(f"  [{completed}/{total}] tareas completadas", err=True)


# ------------------------------------------------------------------
# Comandos
# ------------------------------------------------------------------

@app.command()
def analyze(
    config_path: Path = typer.Argument(..., help="Ruta al JSON de configuración"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Archivo JSON de salida"),
    pretty: bool = typer.Option(True, help="Formatear JSON de salida"),
) -> None:
    """Analiza una configuración de discos y muestra o guarda los resultados."""
    if not config_path.exists():
        typer.echo(f"Error: el archivo '{config_path}' no existe.", err=True)
        raise typer.Exit(1)

    config = _load_config(config_path)
    typer.echo(f"Analizando configuración con {len(config)} discos…", err=True)

    census = ParallelCensus()
    results = census.run([config])

    if not results or results[0] is None:
        typer.echo("Error: el análisis falló.", err=True)
        raise typer.Exit(1)

    ser = JSONSerializer()
    json_str = ser.serialize(results[0])

    if output:
        output.write_text(json_str, encoding="utf-8")
        typer.echo(f"Resultados guardados en '{output}'")
    else:
        typer.echo(json_str)


@app.command()
def census(
    config_dir: Path = typer.Argument(..., help="Directorio con archivos JSON"),
    output_dir: Path = typer.Option(Path("."), "--output", "-o", help="Directorio de resultados"),
    workers: int = typer.Option(4, "--workers", "-w", help="Workers paralelos"),
    executor: str = typer.Option("thread", help="Tipo de executor: 'thread' o 'process'"),
) -> None:
    """Ejecuta un censo paralelo sobre todos los JSON de un directorio."""
    if not config_dir.is_dir():
        typer.echo(f"Error: '{config_dir}' no es un directorio.", err=True)
        raise typer.Exit(1)

    paths = sorted(config_dir.glob("*.json"))
    if not paths:
        typer.echo(f"No se encontraron archivos .json en '{config_dir}'.", err=True)
        raise typer.Exit(1)

    typer.echo(f"Procesando {len(paths)} configuraciones con {workers} workers…", err=True)

    configs = [_load_config(p) for p in paths]

    bus = EventBus()
    bus.subscribe("progress", _progress_callback)

    scheduler = TaskScheduler(executor_type=executor, max_workers=workers, event_bus=bus)
    parallel_census = ParallelCensus(scheduler=scheduler)
    all_results = parallel_census.run(configs)

    output_dir.mkdir(parents=True, exist_ok=True)
    ser = JSONSerializer()

    ok = 0
    for i, result in enumerate(all_results):
        if result is not None:
            out_path = output_dir / f"result_{i:04d}.json"
            out_path.write_text(ser.serialize(result), encoding="utf-8")
            ok += 1

    typer.echo(f"Completado: {ok}/{len(configs)} resultados en '{output_dir}'")


@app.command()
def export(
    config_path: Path = typer.Argument(..., help="Ruta al JSON de configuración"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Archivo SVG de salida"),
) -> None:
    """Exporta una configuración de discos a SVG."""
    if not config_path.exists():
        typer.echo(f"Error: el archivo '{config_path}' no existe.", err=True)
        raise typer.Exit(1)

    config = _load_config(config_path)
    typer.echo(f"Generando SVG para {len(config)} discos…", err=True)

    census = ParallelCensus()
    results = census.run([config])

    if not results or results[0] is None:
        typer.echo("Error: el análisis falló.", err=True)
        raise typer.Exit(1)

    svg = SVGExporter().export(config, results[0])

    if output:
        output.write_text(svg, encoding="utf-8")
        typer.echo(f"SVG guardado en '{output}'")
    else:
        sys.stdout.write(svg)


if __name__ == "__main__":
    app()
