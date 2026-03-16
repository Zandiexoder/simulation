from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class MigrationRecord:
    tick: int
    agent_id: str
    from_city: str
    to_city: str
    reason: str
    score: float


@dataclass(slots=True)
class MigrationSystem:
    records: list[MigrationRecord] = field(default_factory=list)

    def score_destination(self, *, wage_delta: float, unemployment: float, housing_pressure: float, food_pressure: float,
                          conflict_risk: float, repression: float, affinity: float, climate_stress: float,
                          border_policy: float, network_pull: float, prestige: float, misinformation: float) -> float:
        return (
            wage_delta * 0.22
            + (1.0 - unemployment) * 0.12
            + (1.0 - housing_pressure) * 0.09
            + (1.0 - food_pressure) * 0.09
            + (1.0 - conflict_risk) * 0.14
            + (1.0 - repression) * 0.08
            + affinity * 0.07
            + (1.0 - climate_stress) * 0.06
            + border_policy * 0.04
            + network_pull * 0.05
            + prestige * 0.03
            - misinformation * 0.03
        )

    def decide_and_apply(self, *, tick: int, agent: dict, cities: list[dict], city_metrics: dict[str, dict], household_city: str) -> tuple[str, MigrationRecord | None]:
        current = household_city
        best_city = current
        best_score = -10.0
        for city in cities:
            m = city_metrics.get(city["id"], {})
            score = self.score_destination(
                wage_delta=m.get("wage_delta", 0.5),
                unemployment=m.get("unemployment", 0.5),
                housing_pressure=m.get("housing_pressure", 0.5),
                food_pressure=m.get("food_pressure", 0.5),
                conflict_risk=m.get("conflict_risk", 0.5),
                repression=m.get("repression", 0.5),
                affinity=1.0 if city.get("culture") == agent.get("culture") else 0.4,
                climate_stress=m.get("climate_stress", 0.5),
                border_policy=m.get("border_policy", 0.6),
                network_pull=m.get("network_pull", 0.4),
                prestige=m.get("prestige", 0.5),
                misinformation=m.get("misinformation", 0.2),
            )
            if score > best_score:
                best_score = score
                best_city = city["id"]

        if best_city != current and best_score > 0.55:
            rec = MigrationRecord(
                tick=tick,
                agent_id=agent["id"],
                from_city=current,
                to_city=best_city,
                reason="opportunity_pull",
                score=best_score,
            )
            self.records.append(rec)
            return best_city, rec
        return current, None
