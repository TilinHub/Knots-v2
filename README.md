# Knots v2

Plataforma de análisis geométrico de configuraciones de discos, escrita en Python 3.11+.

Analiza envolventes elásticas, grafos de contacto, caminos de Dubins y convex hulls de
configuraciones de discos en el plano, sin dependencias pesadas como NumPy o SciPy.

## Arquitectura por capas

```
knots_v2/
├── domain/          ← Tipos de valor y entidades (Point, Disk, DiskConfiguration)
├── compute/         ← Algoritmos geométricos puros (Graham Scan, Dubins LSL, etc.)
├── orchestration/   ← Ejecución paralela, caché y bus de eventos
├── output/          ← SVG, JSON, CLI (Typer) y visualización (matplotlib)
└── plugins/         ← Interfaz ABC para extensiones externas
```

Las dependencias solo van hacia arriba: `domain` no importa nada interno,
`compute` solo importa `domain`, etc.

## Instalación

```bash
pip install -e ".[dev]"
```

## Uso rápido

### Script de ejemplo

```bash
python main.py
```

### CLI

```bash
# Analizar una configuración
knots analyze config.json

# Censo paralelo sobre un directorio
knots census ./configs/ --output ./results/ --workers 8

# Exportar a SVG
knots export config.json --output salida.svg
```

### Formato de `config.json`

```json
{
  "disks": [
    {"center": {"x": 0.0, "y": 0.0}, "radius": 1.5},
    {"center": {"x": 4.0, "y": 0.0}, "radius": 1.5}
  ]
}
```

### API Python

```python
from knots_v2.domain.configuration import DiskConfiguration
from knots_v2.domain.disk import Disk
from knots_v2.domain.primitives import Point
from knots_v2.orchestration.census import ParallelCensus
from knots_v2.output.svg_exporter import SVGExporter

cfg = DiskConfiguration()
cfg.add_disk(Disk(Point(0.0, 0.0), 1.5))
cfg.add_disk(Disk(Point(4.0, 0.0), 1.5))

results = ParallelCensus().run([cfg])
svg = SVGExporter().export(cfg, results[0])
```

## Tests

```bash
pytest
pytest --cov=knots_v2 --cov-report=term-missing
```

## Módulos principales

| Módulo | Clase | Responsabilidad |
|--------|-------|-----------------|
| `domain/primitives.py` | `Point`, `Segment` | Tipos de valor geométricos |
| `domain/disk.py` | `Disk` | Disco en R² con operaciones espaciales |
| `domain/configuration.py` | `DiskConfiguration` | Colección mutable de discos |
| `compute/convex_hull.py` | `ConvexHull` | Graham Scan desde cero |
| `compute/envelope.py` | `EnvelopeComputer` | Envolvente exterior + fallback a hull |
| `compute/contact_graph.py` | `ContactGraph` | Grafo de adyacencia por contacto |
| `compute/dubins.py` | `DubinsPath` | Camino LSL de Dubins |
| `orchestration/events.py` | `EventBus` | Pub/sub en memoria |
| `orchestration/cache.py` | `ResultCache` | Caché con hash SHA-256 |
| `orchestration/scheduler.py` | `TaskScheduler` | Pool de threads/procesos |
| `orchestration/census.py` | `ParallelCensus` | Pipeline completo paralelo |
| `output/svg_exporter.py` | `SVGExporter` | Exporta configuración a SVG |
| `output/serializer.py` | `JSONSerializer` | Serializa/deserializa resultados |
| `output/cli.py` | `app` (Typer) | CLI con comandos analyze/census/export |
| `output/notebook.py` | `NotebookBridge` | Visualización matplotlib |
| `plugins/base_plugin.py` | `BasePlugin` | ABC para extensiones externas |

## Plugins

Para crear un plugin personalizado:

```python
from knots_v2.plugins.base_plugin import BasePlugin
from knots_v2.domain.configuration import DiskConfiguration

class MiPlugin(BasePlugin):
    def name(self) -> str:
        return "mi-plugin"

    def run(self, config: DiskConfiguration, results: dict) -> dict:
        return {"mi-plugin.n_contactos": sum(len(v) for v in results["contact_graph"].values())}
```

## Licencia

MIT
