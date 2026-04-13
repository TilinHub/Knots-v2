"""Caché de resultados en memoria con claves hasheadas.

Permite evitar recalcular configuraciones ya procesadas durante un censo.
La clave canónica de una configuración se obtiene con :meth:`config_key`.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from ..domain.configuration import DiskConfiguration


class ResultCache:
    """Caché de resultados basada en diccionario con claves SHA-256.

    El hash de la clave permite que strings largos (representación JSON
    de una configuración) se conviertan en claves compactas de longitud fija.

    Example::

        cache = ResultCache()
        key = ResultCache.config_key(mi_config)
        if cache.get(key) is None:
            resultado = calcular(mi_config)
            cache.set(key, resultado)
    """

    def __init__(self) -> None:
        # Almacén interno: hash_hexdigest → valor
        self._store: dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Interfaz pública
    # ------------------------------------------------------------------

    def get(self, key: str) -> Any | None:
        """Retorna el valor asociado a *key*, o None si no existe."""
        return self._store.get(self._hash(key))

    def set(self, key: str, value: Any) -> None:
        """Almacena *value* bajo la clave *key*."""
        self._store[self._hash(key)] = value

    def invalidate(self, key: str) -> None:
        """Elimina la entrada de *key* si existe. No hace nada si no existe."""
        self._store.pop(self._hash(key), None)

    def invalidate_all(self) -> None:
        """Vacía completamente el caché."""
        self._store.clear()

    def __len__(self) -> int:
        return len(self._store)

    def __contains__(self, key: str) -> bool:
        return self._hash(key) in self._store

    # ------------------------------------------------------------------
    # Generación de claves
    # ------------------------------------------------------------------

    @staticmethod
    def config_key(config: DiskConfiguration) -> str:
        """Genera una clave de texto canónica para *config*.

        La clave es el JSON serializado con claves ordenadas, lo que garantiza
        que dos configuraciones con los mismos discos producen la misma clave
        independientemente del orden de construcción del diccionario.
        """
        return json.dumps(config.to_dict(), sort_keys=True)

    @staticmethod
    def _hash(key: str) -> str:
        """SHA-256 del string *key* como hexdigest (64 caracteres)."""
        return hashlib.sha256(key.encode("utf-8")).hexdigest()
