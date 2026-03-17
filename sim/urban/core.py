from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class CityProfile:
    city_id: str
    population: int = 0
    housing_supply: float = 1.0
    job_capacity: float = 1.0
    infrastructure_capacity: float = 1.0
    food_access: float = 0.8
    transport_connectivity: float = 0.6
    sanitation: float = 0.7
    industrial_profile: float = 0.5
    trade_connectivity: float = 0.5
    pollution: float = 0.2
    crime_pressure: float = 0.2
    legitimacy: float = 0.6
    density_pressure: float = 0.3
    growth_trend: float = 0.0


@dataclass(slots=True)
class UrbanSystem:
    cities: dict[str, CityProfile] = field(default_factory=dict)

    def register_city(self, city_id: str, population: int) -> None:
        self.cities.setdefault(city_id, CityProfile(city_id=city_id, population=population))

    def tick(self) -> list[dict]:
        events: list[dict] = []
        for c in self.cities.values():
            pressure = max(0.0, c.population / max(1, int(c.housing_supply * 1000)) - 1.0)
            c.density_pressure = min(1.0, 0.6 * c.density_pressure + 0.4 * pressure)
            c.growth_trend = (c.job_capacity + c.infrastructure_capacity + c.trade_connectivity) / 3 - c.pollution - c.crime_pressure
            if c.growth_trend > 0.25:
                c.population = int(c.population * 1.01)
                c.housing_supply += 0.01
                events.append({"type": "urban_growth", "city_id": c.city_id, "message": "City expanded."})
            elif c.growth_trend < -0.15:
                c.population = int(c.population * 0.995)
                c.crime_pressure = min(1.0, c.crime_pressure + 0.02)
                events.append({"type": "urban_decline", "city_id": c.city_id, "message": "City under stress."})
        return events
