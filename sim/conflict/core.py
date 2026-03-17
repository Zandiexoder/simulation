from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class ForcePool:
    nation_id: str
    readiness: float = 0.5
    morale: float = 0.6
    logistics: float = 0.6
    recruitment: float = 0.4


@dataclass(slots=True)
class ConflictSystem:
    force_pools: dict[str, ForcePool] = field(default_factory=dict)
    incidents: list[dict] = field(default_factory=list)

    def register_nation(self, nation_id: str) -> None:
        self.force_pools.setdefault(nation_id, ForcePool(nation_id=nation_id))

    def tick(self, *, tick: int, legitimacy: float, intelligence_quality: float, urban_density: float) -> list[dict]:
        out: list[dict] = []
        risk = max(0.0, min(1.0, 0.35 * (1 - legitimacy) + 0.25 * (1 - intelligence_quality) + 0.2 * urban_density + 0.2 * 0.4))
        if risk > 0.6:
            ev = {"type": "security_incident", "tick": tick, "risk": risk, "message": "Security incident probability elevated."}
            self.incidents.append(ev)
            out.append(ev)
        return out
