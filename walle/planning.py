"""Grid path planning over WALL-E's *partial* map.

Unknown cells ('?') are costed differently depending on the question:
* optimistic when looking for somewhere to explore (unknown = probably open),
* pessimistic when asking "can I still get home?" (unknown = rubble).
"""
from __future__ import annotations

import heapq

import numpy as np

UNKNOWN = "?"
DIRS = {(0, -1): "N", (0, 1): "S", (1, 0): "E", (-1, 0): "W"}


def cost_grid(known: np.ndarray, costs, unknown_cost: float) -> np.ndarray:
    """Battery cost of *entering* each cell (inf for walls)."""
    g = np.full(known.shape, costs.move, dtype=float)
    g[known == "~"] = costs.move_rubble
    g[known == "#"] = np.inf
    g[known == UNKNOWN] = unknown_cost
    return g


def dijkstra(enter_cost: np.ndarray, sources) -> tuple[np.ndarray, dict]:
    """Multi-source shortest paths. Returns (distance grid, parent map)."""
    H, W = enter_cost.shape
    dist = np.full((H, W), np.inf)
    parent: dict = {}
    pq = []
    for s in sources:
        dist[s[1], s[0]] = 0.0
        pq.append((0.0, tuple(s)))
    heapq.heapify(pq)
    while pq:
        d, (x, y) = heapq.heappop(pq)
        if d > dist[y, x]:
            continue
        for dx, dy in DIRS:
            nx, ny = x + dx, y + dy
            if 0 <= nx < W and 0 <= ny < H:
                c = enter_cost[ny, nx]
                if not np.isfinite(c):
                    continue
                nd = d + c
                if nd < dist[ny, nx] - 1e-12:
                    dist[ny, nx] = nd
                    parent[(nx, ny)] = (x, y)
                    heapq.heappush(pq, (nd, (nx, ny)))
    return dist, parent


def extract_path(parent: dict, src, dst) -> list | None:
    """Cells from src (exclusive) to dst (inclusive)."""
    src, dst = tuple(src), tuple(dst)
    if src == dst:
        return []
    if dst not in parent:
        return None
    path = [dst]
    while path[-1] != src:
        path.append(parent[path[-1]])
    path.reverse()
    return path[1:]


def direction(frm, to) -> str:
    return DIRS[(to[0] - frm[0], to[1] - frm[1])]
