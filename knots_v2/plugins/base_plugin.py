"""Interfaz base para plugins de Knots v2.

Los plugins permiten extender el sistema sin modificar el núcleo.
Se enganchan desde fuera de las capas principales siguiendo el principio
"abierto/cerrado": abierto para extensión, cerrado para modificación.

Ejemplo de plugins que se podrían implementar:
- ``AIClassifier``: clasifica configuraciones con un modelo de ML.
- ``WebAPIAdapter``: envía resultados a un endpoint REST.
- ``DatabaseWriter``: persiste resultados en PostgreSQL/MongoDB.
- ``ReportGenerator``: genera PDF con visualizaciones y estadísticas.

Para registrar un plugin en el sistema basta con instanciarlo y pasarlo
al runner correspondiente::

    from knots_v2.plugins.my_plugin import MyPlugin

    plugin = MyPlugin()
    result = plugin.run(config, census_results)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..domain.configuration import DiskConfiguration


class BasePlugin(ABC):
    """Clase base abstracta para todos los plugins de Knots v2.

    Los plugins reciben la configuración de discos y los resultados del
    análisis, y pueden producir salidas adicionales (clasificaciones,
    métricas, exportaciones a servicios externos, etc.).

    Subclase mínima::

        class MiPlugin(BasePlugin):
            def name(self) -> str:
                return "mi-plugin"

            def run(self, config: DiskConfiguration, results: dict) -> dict:
                # lógica personalizada
                return {"mi_metrica": calcular(config)}
    """

    @abstractmethod
    def name(self) -> str:
        """Identificador único del plugin (slug en minúsculas con guiones).

        Debe ser único entre todos los plugins registrados.
        """
        ...

    @abstractmethod
    def run(self, config: DiskConfiguration, results: dict[str, Any]) -> dict[str, Any]:
        """Ejecuta la lógica del plugin sobre *config* y *results*.

        Args:
            config: La configuración de discos analizada.
            results: Resultados del censo (envelope, contact_graph, etc.).

        Returns:
            Diccionario con las salidas adicionales del plugin.
            Las claves deben estar prefijadas con el nombre del plugin
            para evitar colisiones (p.ej. ``{"mi-plugin.score": 0.95}``).
        """
        ...

    def version(self) -> str:
        """Versión del plugin en formato semver (opcional, por defecto '0.1.0')."""
        return "0.1.0"

    def description(self) -> str:
        """Descripción breve del plugin (opcional)."""
        return ""


# ------------------------------------------------------------------
# Ejemplo comentado: AIClassifier
# ------------------------------------------------------------------
#
# class AIClassifier(BasePlugin):
#     """Clasifica configuraciones de discos usando un modelo de ML.
#
#     Para registrarlo en el sistema:
#
#         classifier = AIClassifier(model_path="models/knots_clf.pkl")
#         # En el pipeline de census:
#         extra = classifier.run(config, census_result)
#         census_result.update(extra)
#     """
#
#     def __init__(self, model_path: str) -> None:
#         import pickle
#         with open(model_path, "rb") as f:
#             self._model = pickle.load(f)
#
#     def name(self) -> str:
#         return "ai-classifier"
#
#     def run(self, config: DiskConfiguration, results: dict) -> dict:
#         features = self._extract_features(config, results)
#         label = self._model.predict([features])[0]
#         return {"ai-classifier.label": label}
#
#     def _extract_features(self, config, results) -> list[float]:
#         return [
#             len(config),
#             len(results.get("envelope", [])),
#             sum(len(v) for v in results.get("contact_graph", {}).values()),
#         ]


# ------------------------------------------------------------------
# Ejemplo comentado: WebAPIAdapter
# ------------------------------------------------------------------
#
# class WebAPIAdapter(BasePlugin):
#     """Envía los resultados del análisis a un endpoint REST externo.
#
#     Para registrarlo:
#
#         adapter = WebAPIAdapter(endpoint="https://api.example.com/knots")
#         adapter.run(config, census_result)
#     """
#
#     def __init__(self, endpoint: str, api_key: str = "") -> None:
#         self._endpoint = endpoint
#         self._api_key = api_key
#
#     def name(self) -> str:
#         return "web-api-adapter"
#
#     def run(self, config: DiskConfiguration, results: dict) -> dict:
#         import urllib.request, json as _json
#         payload = _json.dumps({"config": config.to_dict(), "results": results}).encode()
#         req = urllib.request.Request(
#             self._endpoint,
#             data=payload,
#             headers={"Content-Type": "application/json", "X-API-Key": self._api_key},
#             method="POST",
#         )
#         with urllib.request.urlopen(req, timeout=10) as resp:
#             body = _json.loads(resp.read())
#         return {"web-api-adapter.response": body}
