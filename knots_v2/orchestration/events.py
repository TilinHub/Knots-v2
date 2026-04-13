"""Bus de eventos para la comunicación desacoplada entre capas.

Implementación simple pub/sub en memoria. No requiere ninguna dependencia externa.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Callable

logger = logging.getLogger(__name__)

# Eventos reconocidos por el sistema
_KNOWN_EVENTS = frozenset({
    "task_started",
    "task_completed",
    "task_failed",
    "progress",
})


class EventBus:
    """Bus de eventos pub/sub en memoria.

    Los suscriptores se registran con :meth:`subscribe` y reciben los datos
    emitidos mediante :meth:`emit`. Un mismo evento puede tener varios
    suscriptores; se llaman en orden de registro.

    No se valida el tipo de evento para permitir eventos personalizados de
    plugins, aunque se registra una advertencia si el evento no es conocido.

    Example::

        bus = EventBus()
        bus.subscribe("task_completed", lambda d: print(d))
        bus.emit("task_completed", {"task_index": 0})
    """

    def __init__(self) -> None:
        self._listeners: dict[str, list[Callable[[Any], None]]] = defaultdict(list)

    def subscribe(self, event: str, callback: Callable[[Any], None]) -> None:
        """Registra *callback* para que se llame cada vez que se emita *event*.

        Args:
            event: Nombre del evento. Los eventos conocidos son:
                ``task_started``, ``task_completed``, ``task_failed``, ``progress``.
            callback: Función que recibe un único argumento con los datos del evento.
        """
        if event not in _KNOWN_EVENTS:
            logger.debug("EventBus: suscripción a evento no conocido '%s'", event)
        self._listeners[event].append(callback)

    def unsubscribe(self, event: str, callback: Callable[[Any], None]) -> None:
        """Elimina *callback* de la lista de suscriptores de *event*."""
        try:
            self._listeners[event].remove(callback)
        except ValueError:
            pass  # El callback no estaba registrado; ignorar silenciosamente

    def emit(self, event: str, data: Any = None) -> None:
        """Invoca todos los callbacks suscritos a *event* con *data*.

        Si un callback lanza una excepción, se registra el error pero el resto
        de suscriptores siguen recibiendo el evento.

        Args:
            event: Nombre del evento a emitir.
            data: Datos asociados al evento (cualquier tipo).
        """
        for callback in list(self._listeners[event]):
            try:
                callback(data)
            except Exception as exc:
                logger.error(
                    "EventBus: error en suscriptor de '%s': %s", event, exc
                )

    def clear(self, event: str | None = None) -> None:
        """Elimina todos los suscriptores de *event*, o de todos los eventos si es None."""
        if event is None:
            self._listeners.clear()
        else:
            self._listeners[event].clear()

    def subscriber_count(self, event: str) -> int:
        """Retorna el número de suscriptores actuales de *event*."""
        return len(self._listeners[event])
