from __future__ import annotations

from collections import defaultdict


class SpatialIndex:
    def __init__(self) -> None:
        self._grid: dict[tuple[int, int], list[str]] = defaultdict(list)

    def rebuild(self, locations: dict[str, tuple[int, int]]) -> None:
        self._grid.clear()
        for entity_id, pos in locations.items():
            self._grid[pos].append(entity_id)

    def neighbors(self, pos: tuple[int, int], radius: int = 1) -> list[str]:
        out: list[str] = []
        x, y = pos
        for yy in range(y - radius, y + radius + 1):
            for xx in range(x - radius, x + radius + 1):
                out.extend(self._grid.get((xx, yy), []))
        return out
