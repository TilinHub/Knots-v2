"""Serialización y deserialización de resultados a JSON.

Maneja correctamente tipos especiales como claves enteras del grafo de contacto
que JSON convierte a strings al serializar.
"""

from __future__ import annotations

import json
from typing import Any


class _IntKeyDecoder(json.JSONDecoder):
    """Decoder que convierte claves de objetos a int cuando sea posible.

    JSON solo permite strings como claves de objeto. Al deserializar el
    grafo de contacto necesitamos recuperar las claves enteras originales.
    """

    def decode(self, s: str) -> Any:
        obj = super().decode(s)
        return self._restore_int_keys(obj)

    def _restore_int_keys(self, obj: Any) -> Any:
        if isinstance(obj, dict):
            restored = {}
            for k, v in obj.items():
                new_key = int(k) if isinstance(k, str) and k.lstrip("-").isdigit() else k
                restored[new_key] = self._restore_int_keys(v)
            return restored
        if isinstance(obj, list):
            return [self._restore_int_keys(item) for item in obj]
        return obj


class JSONSerializer:
    """Serializa y deserializa los resultados del censo a/desde JSON.

    Example::

        ser = JSONSerializer()
        json_str = ser.serialize(results)
        # ... guardar en archivo ...
        recovered = ser.deserialize(json_str)
    """

    def serialize(self, results: Any, indent: int = 2) -> str:
        """Serializa *results* a una cadena JSON con formato legible.

        Args:
            results: Cualquier estructura serializable (dict, list, etc.).
            indent: Sangría en espacios para el JSON de salida.

        Returns:
            String JSON.
        """
        return json.dumps(results, indent=indent, ensure_ascii=False)

    def deserialize(self, json_str: str) -> Any:
        """Deserializa *json_str* recuperando claves enteras donde corresponda.

        Args:
            json_str: String JSON a parsear.

        Returns:
            Estructura Python equivalente al JSON de entrada.

        Raises:
            json.JSONDecodeError: si el string no es JSON válido.
        """
        return json.loads(json_str, cls=_IntKeyDecoder)

    def serialize_to_file(self, results: Any, path: str) -> None:
        """Serializa *results* y guarda el JSON en *path*."""
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.serialize(results))

    def deserialize_from_file(self, path: str) -> Any:
        """Lee el archivo en *path* y deserializa su contenido JSON."""
        with open(path, encoding="utf-8") as f:
            return self.deserialize(f.read())
