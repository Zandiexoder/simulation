from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class NationPolitics:
    nation_id: str
    government_type: str = "hybrid_republic"
    ruling_coalition: list[str] = field(default_factory=lambda: ["civic_front"])
    opposition_groups: list[str] = field(default_factory=lambda: ["labor_bloc"])
    legitimacy: float = 0.6
    elite_cohesion: float = 0.6
    corruption: float = 0.3
    repression: float = 0.2
    reform_pressure: float = 0.3
    state_capacity: float = 0.6
    protest_potential: float = 0.2
    coup_risk: float = 0.1


@dataclass(slots=True)
class PoliticsSystem:
    nations: dict[str, NationPolitics] = field(default_factory=dict)

    def register(self, nation_id: str) -> None:
        self.nations.setdefault(nation_id, NationPolitics(nation_id=nation_id))

    def tick(self, *, econ_stress: float, migration_stress: float, security_threat: float) -> list[dict]:
        events: list[dict] = []
        for n in self.nations.values():
            n.legitimacy = max(0.0, min(1.0, n.legitimacy + 0.02 * n.state_capacity - 0.03 * econ_stress - 0.02 * migration_stress - 0.03 * n.corruption))
            n.protest_potential = max(0.0, min(1.0, 0.4 * (1.0 - n.legitimacy) + 0.3 * econ_stress + 0.2 * migration_stress + 0.1 * security_threat))
            n.coup_risk = max(0.0, min(1.0, 0.5 * (1.0 - n.elite_cohesion) + 0.4 * n.protest_potential + 0.1 * n.corruption))
            if n.protest_potential > 0.65:
                events.append({"type": "protest_wave", "nation_id": n.nation_id, "message": "Protest potential crossed alert threshold."})
            if n.coup_risk > 0.72:
                events.append({"type": "coup_risk", "nation_id": n.nation_id, "message": "Coup-risk estimate elevated."})
        return events
