from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class EmergenceSystem:
    seen: set[str] = field(default_factory=set)
    milestones: list[dict[str, Any]] = field(default_factory=list)

    def evaluate(
        self,
        *,
        tick: int,
        events: list[dict[str, Any]],
        org_count: int,
        media_count: int,
        conflict_incidents: int,
        migration_events: int,
        migration_wave_threshold: int = 8,
    ) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []

        checks = [
            ("first_org", org_count > 0, "First international organization formed."),
            ("first_media", media_count > 0, "First newspaper/media issue published."),
            ("first_war_escalation", any(e.get("type") == "security_incident" for e in events[-30:]) and conflict_incidents > 0, "First major war/security escalation observed."),
            ("first_revolutionary_signal", any(e.get("type") == "coup_risk" for e in events[-40:]), "First revolutionary/coup-risk signal emerged."),
            ("major_migration_wave", migration_events >= migration_wave_threshold, "Major migration wave crossed system threshold."),
        ]
        for key, cond, msg in checks:
            if cond and key not in self.seen:
                ev = {
                    "type": "milestone",
                    "tick": tick,
                    "milestone_key": key,
                    "message": msg,
                    "milestone": True,
                }
                self.seen.add(key)
                self.milestones.append(ev)
                out.append(ev)
        return out
