"""Cross-domain lineage: a directed graph of product -> product edges.

Upstream = what feeds this product; downstream = what it feeds.
Both queries are BFS with hop distances, so an impact report can say
"2 hops away" instead of just "affected". Cycles are detected (not
silently tolerated) because a cycle in a mesh usually means a
mis-declared edge.
"""

from __future__ import annotations

from collections import deque

from .errors import AlreadyExistsError
from .models import LineageEdge


class LineageGraph:
    def __init__(self) -> None:
        self.edges: list[LineageEdge] = []
        self._down: dict[str, set[str]] = {}  # upstream -> {downstream}
        self._up: dict[str, set[str]] = {}    # downstream -> {upstream}

    def add_edge(self, upstream: str, downstream: str,
                 description: str = "") -> LineageEdge:
        if upstream == downstream:
            raise ValueError("a product cannot depend on itself")
        edge = LineageEdge(upstream, downstream, description)
        if edge in self.edges:
            raise AlreadyExistsError(f"edge {upstream} -> {downstream} already exists")
        self.edges.append(edge)
        self._down.setdefault(upstream, set()).add(downstream)
        self._up.setdefault(downstream, set()).add(upstream)
        return edge

    def _bfs(self, start: str, adjacency: dict[str, set[str]]) -> dict[str, int]:
        distances: dict[str, int] = {}
        queue: deque[tuple[str, int]] = deque([(start, 0)])
        seen = {start}
        while queue:
            node, dist = queue.popleft()
            for nxt in sorted(adjacency.get(node, set())):
                if nxt not in seen:
                    seen.add(nxt)
                    distances[nxt] = dist + 1
                    queue.append((nxt, dist + 1))
        return distances

    def upstream(self, product_id: str) -> dict[str, int]:
        """Products that (transitively) feed this product, with hop counts."""
        return self._bfs(product_id, self._up)

    def downstream(self, product_id: str) -> dict[str, int]:
        """Products (transitively) fed by this product, with hop counts."""
        return self._bfs(product_id, self._down)

    def impact(self, product_id: str) -> dict[str, dict[str, int]]:
        return {"upstream": self.upstream(product_id),
                "downstream": self.downstream(product_id)}

    def has_cycle(self) -> bool:
        """DFS cycle detection over the full graph."""
        WHITE, GREY, BLACK = 0, 1, 2
        color: dict[str, int] = {}
        nodes = set(self._down) | set(self._up)

        def visit(node: str) -> bool:
            color[node] = GREY
            for nxt in sorted(self._down.get(node, set())):
                if color.get(nxt, WHITE) == GREY:
                    return True
                if color.get(nxt, WHITE) == WHITE and visit(nxt):
                    return True
            color[node] = BLACK
            return False

        return any(color.get(n, WHITE) == WHITE and visit(n) for n in sorted(nodes))
