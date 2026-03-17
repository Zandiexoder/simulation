from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from sim.tuning import TuningConfig


@dataclass(slots=True)
class Scenario:
    scenario_id: str
    seed: int
    world_width: int
    world_height: int
    population_scale: float
    culture_mix: str
    fragmentation: float
    crisis_level: float
    org_media_permissiveness: float
    module_tunables: dict[str, Any] = field(default_factory=dict)
    subsystems: dict[str, bool] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


DEFAULT_SCENARIOS: dict[str, Scenario] = {
    "default": Scenario("default", 42, 48, 32, 1.0, "balanced", 0.5, 0.3, 0.5, {}),
    "high_fragmentation": Scenario("high_fragmentation", 77, 52, 34, 1.0, "fragmented", 0.85, 0.55, 0.7, {"international": {"org_formation_threshold": 0.58}}),
    "high_migration": Scenario("high_migration", 91, 56, 36, 1.15, "blended", 0.6, 0.6, 0.55, {"migration": {"surge_threshold": 0.55}, "emergence": {"major_migration_wave_threshold": 6}}),
    "crisis_heavy": Scenario("crisis_heavy", 123, 48, 32, 1.0, "stressed", 0.75, 0.9, 0.7, {"conflict": {"escalation_sensitivity": 1.2}, "politics": {"coup_risk_weight": 1.2}}),
    "stable_world": Scenario("stable_world", 33, 48, 32, 1.0, "cohesive", 0.3, 0.15, 0.4, {"politics": {"legitimacy_recovery_rate": 0.02, "legitimacy_decay_rate": 0.01}}),
    "debug_small": Scenario("debug_small", 5, 24, 16, 0.35, "balanced", 0.5, 0.25, 0.5, {"media": {"issue_interval": 3}}),
}


def list_scenarios() -> list[dict[str, Any]]:
    return [s.as_dict() for s in DEFAULT_SCENARIOS.values()]


def get_scenario(scenario_id: str) -> Scenario:
    return DEFAULT_SCENARIOS.get(scenario_id, DEFAULT_SCENARIOS["default"])


def merged_tuning(base: TuningConfig, scenario: Scenario) -> TuningConfig:
    from sim.tuning import tuning_from_dict

    merged = tuning_from_dict(base.as_dict())
    scenario_cfg = tuning_from_dict(scenario.module_tunables)
    return tuning_from_dict({**merged.as_dict(), **scenario_cfg.as_dict()})
