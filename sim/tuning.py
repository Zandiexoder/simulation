from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class MigrationTuning:
    pressure_sensitivity: float = 1.0
    surge_threshold: float = 0.7


@dataclass(slots=True)
class PoliticsTuning:
    protest_escalation_threshold: float = 0.65
    coup_risk_weight: float = 1.0
    legitimacy_recovery_rate: float = 0.01
    legitimacy_decay_rate: float = 0.02


@dataclass(slots=True)
class InternationalTuning:
    org_formation_threshold: float = 0.63
    deadlock_band_low: float = 0.45
    deadlock_band_high: float = 0.62


@dataclass(slots=True)
class MediaTuning:
    issue_interval: int = 5
    major_event_window: int = 20


@dataclass(slots=True)
class ConflictTuning:
    escalation_sensitivity: float = 1.0


@dataclass(slots=True)
class EmergenceTuning:
    major_migration_wave_threshold: int = 8


@dataclass(slots=True)
class TuningConfig:
    migration: MigrationTuning = field(default_factory=MigrationTuning)
    politics: PoliticsTuning = field(default_factory=PoliticsTuning)
    international: InternationalTuning = field(default_factory=InternationalTuning)
    media: MediaTuning = field(default_factory=MediaTuning)
    conflict: ConflictTuning = field(default_factory=ConflictTuning)
    emergence: EmergenceTuning = field(default_factory=EmergenceTuning)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def tuning_from_dict(data: dict[str, Any]) -> TuningConfig:
    t = TuningConfig()
    for section in ["migration", "politics", "international", "media", "conflict", "emergence"]:
        if section not in data:
            continue
        target = getattr(t, section)
        for k, v in data[section].items():
            if hasattr(target, k):
                setattr(target, k, v)
    return t
