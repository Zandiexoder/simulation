from __future__ import annotations

from dataclasses import dataclass
import random
from typing import List


CULTURES = ["northern", "eastern", "desert", "islander", "industrial", "frontier"]


@dataclass(slots=True)
class Cell:
    x: int
    y: int
    elevation: float
    biome: str
    fertility: float
    resource_richness: float
    population_capacity: int
    habitability: float
    culture_region: str


@dataclass(slots=True)
class WorldMap:
    width: int
    height: int
    cells: List[Cell]


def _noise(rng: random.Random, base: float = 0.0, scale: float = 1.0) -> float:
    return base + (rng.random() - 0.5) * scale


def _culture_for_cell(x: int, y: int, width: int, height: int, biome: str) -> str:
    if biome == "desert":
        return "desert"
    if y < height * 0.2:
        return "northern"
    if x > width * 0.75:
        return "eastern"
    if x < width * 0.2 and biome in {"ocean", "plains"}:
        return "islander"
    if biome == "mountain":
        return "frontier"
    return "industrial"


def generate_world(seed: int, width: int, height: int) -> WorldMap:
    rng = random.Random(seed)
    cells: list[Cell] = []
    for y in range(height):
        for x in range(width):
            cx = (x - width / 2) / (width / 2)
            cy = (y - height / 2) / (height / 2)
            continental_bias = 1.0 - min(1.0, (cx * cx + cy * cy))
            elevation = max(0.0, min(1.0, continental_bias + _noise(rng, scale=0.5)))
            latitude = abs((y / max(1, height - 1)) * 2 - 1)
            climate = max(0.0, min(1.0, 1.0 - latitude - elevation * 0.3 + _noise(rng, scale=0.2)))

            if elevation < 0.18:
                biome = "ocean"
            elif elevation > 0.82:
                biome = "mountain"
            elif latitude > 0.75:
                biome = "tundra"
            elif climate < 0.25:
                biome = "desert"
            elif climate > 0.65:
                biome = "forest"
            else:
                biome = "plains"

            resource = max(0.0, min(1.0, elevation * 0.4 + climate * 0.4 + _noise(rng, scale=0.3)))
            fertility = max(0.0, min(1.0, climate * (1.0 - abs(elevation - 0.45))))
            habitability = max(0.0, min(1.0, fertility * 0.7 + resource * 0.3))
            capacity = int(10 + habitability * 190)
            culture_region = _culture_for_cell(x, y, width, height, biome)

            cells.append(
                Cell(
                    x=x,
                    y=y,
                    elevation=elevation,
                    biome=biome,
                    fertility=fertility,
                    resource_richness=resource,
                    population_capacity=capacity,
                    habitability=habitability,
                    culture_region=culture_region,
                )
            )

    return WorldMap(width=width, height=height, cells=cells)


def seed_settlements(world: WorldMap, n_cities: int = 12) -> list[dict]:
    sorted_cells = sorted((c for c in world.cells if c.biome != "ocean"), key=lambda c: c.habitability, reverse=True)
    cities: list[dict] = []
    for idx, cell in enumerate(sorted_cells[:n_cities]):
        cities.append(
            {
                "id": f"city-{idx}",
                "name": f"City {idx}",
                "x": cell.x,
                "y": cell.y,
                "population": int(cell.population_capacity * 0.5),
                "nation_id": f"nation-{idx % 4}",
                "culture": cell.culture_region,
            }
        )
    return cities


def seed_nations(count: int = 4) -> list[dict]:
    return [
        {
            "id": f"nation-{i}",
            "name": f"Nation {i}",
            "stability": 0.6 + 0.1 * (i % 3),
            "culture": CULTURES[i % len(CULTURES)],
        }
        for i in range(count)
    ]
