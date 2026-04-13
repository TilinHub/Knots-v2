"""Grafo de contacto entre discos de una configuración.

Dos discos están en "contacto" si la distancia entre sus centros es menor
o igual a la suma de sus radios más una tolerancia epsilon.
"""

from __future__ import annotations

from ..domain.configuration import DiskConfiguration

# Tolerancia para considerar dos discos en contacto (absorbe errores de punto flotante)
_EPSILON: float = 1e-9


class ContactGraph:
    """Construye el grafo de contacto de una configuración de discos.

    El grafo se representa como un diccionario de listas de adyacencia:
        ``{índice_disco: [índices_de_discos_en_contacto]}``

    El grafo es siempre simétrico: si j ∈ graph[i] entonces i ∈ graph[j].
    """

    def from_config(
        self,
        config: DiskConfiguration,
        epsilon: float = _EPSILON,
    ) -> dict[int, list[int]]:
        """Calcula el grafo de contacto para *config*.

        Args:
            config: Configuración de discos sobre la que operar.
            epsilon: Tolerancia adicional para la detección de contacto.

        Returns:
            Diccionario ``{i: [j, ...]}`` con los índices de discos adyacentes.
        """
        disks = list(config)
        n = len(disks)
        graph: dict[int, list[int]] = {i: [] for i in range(n)}

        for i in range(n):
            for j in range(i + 1, n):
                dist = disks[i].center.distance_to(disks[j].center)
                umbral = disks[i].radius + disks[j].radius + epsilon
                if dist <= umbral:
                    graph[i].append(j)
                    graph[j].append(i)

        return graph

    def adjacency_matrix(self, config: DiskConfiguration) -> list[list[int]]:
        """Retorna la matriz de adyacencia (lista de listas) del grafo de contacto.

        Útil para algoritmos de grafos que prefieren representación matricial.
        """
        n = len(list(config))
        graph = self.from_config(config)
        matrix = [[0] * n for _ in range(n)]
        for i, neighbors in graph.items():
            for j in neighbors:
                matrix[i][j] = 1
        return matrix

    def connected_components(self, config: DiskConfiguration) -> list[list[int]]:
        """Retorna las componentes conexas del grafo como listas de índices."""
        graph = self.from_config(config)
        n = len(list(config))
        visited: set[int] = set()
        components: list[list[int]] = []

        for start in range(n):
            if start in visited:
                continue
            # BFS desde start
            component: list[int] = []
            queue = [start]
            while queue:
                node = queue.pop(0)
                if node in visited:
                    continue
                visited.add(node)
                component.append(node)
                queue.extend(graph[node])
            components.append(component)

        return components
