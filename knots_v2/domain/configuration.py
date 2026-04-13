"""Configuración de discos: colección mutable con validación geométrica."""

from __future__ import annotations

from typing import Iterator

from .disk import Disk
from .primitives import Point


class DiskConfiguration:
    """Colección ordenada de discos que representa una configuración geométrica.

    Las configuraciones son mutables: se pueden agregar y eliminar discos.
    El método :meth:`validate` comprueba que no haya superposición entre discos.

    Example::

        cfg = DiskConfiguration()
        cfg.add_disk(Disk(Point(0, 0), 1.0))
        cfg.add_disk(Disk(Point(3, 0), 1.0))
        assert cfg.validate()  # los discos no se solapan
    """

    def __init__(self) -> None:
        self._disks: list[Disk] = []

    # ------------------------------------------------------------------
    # Mutación
    # ------------------------------------------------------------------

    def add_disk(self, disk: Disk) -> None:
        """Agrega un disco al final de la configuración."""
        self._disks.append(disk)

    def remove_disk(self, index: int) -> None:
        """Elimina el disco en la posición *index*.

        Raises:
            IndexError: si el índice está fuera de rango.
        """
        if index < 0 or index >= len(self._disks):
            raise IndexError(f"Índice {index} fuera de rango (len={len(self._disks)})")
        del self._disks[index]

    def clear(self) -> None:
        """Elimina todos los discos de la configuración."""
        self._disks.clear()

    # ------------------------------------------------------------------
    # Validación
    # ------------------------------------------------------------------

    def validate(self) -> bool:
        """Verifica que ningún par de discos se solape.

        Dos discos se solapan si la distancia entre sus centros es estrictamente
        menor que la suma de sus radios (se permite el contacto tangencial).

        Returns:
            True si la configuración es válida (sin superposición).
        """
        for i in range(len(self._disks)):
            for j in range(i + 1, len(self._disks)):
                if self._disks[i].intersects(self._disks[j]):
                    return False
        return True

    def bounding_box(self) -> tuple[float, float, float, float] | None:
        """Caja delimitadora que contiene todos los discos, o None si está vacía."""
        if not self._disks:
            return None
        boxes = [d.bounding_box() for d in self._disks]
        return (
            min(b[0] for b in boxes),
            min(b[1] for b in boxes),
            max(b[2] for b in boxes),
            max(b[3] for b in boxes),
        )

    # ------------------------------------------------------------------
    # Protocolo de secuencia
    # ------------------------------------------------------------------

    def __iter__(self) -> Iterator[Disk]:
        return iter(self._disks)

    def __len__(self) -> int:
        return len(self._disks)

    def __getitem__(self, index: int) -> Disk:
        return self._disks[index]

    # ------------------------------------------------------------------
    # Serialización
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        return {"disks": [d.to_dict() for d in self._disks]}

    @classmethod
    def from_dict(cls, data: dict) -> DiskConfiguration:
        """Reconstruye una configuración desde un diccionario serializado."""
        cfg = cls()
        for disk_data in data.get("disks", []):
            cfg.add_disk(Disk.from_dict(disk_data))
        return cfg

    def __repr__(self) -> str:
        return f"DiskConfiguration(n_disks={len(self._disks)})"
