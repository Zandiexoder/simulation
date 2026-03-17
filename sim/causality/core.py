from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class CausalityLink:
    type: str
    description: str


@dataclass(slots=True)
class CausalitySystem:
    chains: dict[str, dict[str, Any]] = field(default_factory=dict)

    def _metric_chain(self, metrics: dict[str, float]) -> list[CausalityLink]:
        out: list[CausalityLink] = []
        if metrics.get("avg_wealth", 1.0) < 0.45:
            out.append(CausalityLink("economic", "household purchasing power deteriorated"))
        if metrics.get("migration_events", 0.0) > 4:
            out.append(CausalityLink("social", "population displacement increased local pressure"))
        if metrics.get("avg_legitimacy", 1.0) < 0.5:
            out.append(CausalityLink("political", "governance legitimacy weakened"))
        if metrics.get("conflict_incidents", 0.0) > 0:
            out.append(CausalityLink("security", "security incidents raised escalation risk"))
        return out

    def derive(self, *, event: dict[str, Any], recent_events: list[dict[str, Any]], metrics: dict[str, float]) -> dict[str, Any] | None:
        et = event.get("type", "")
        major_types = {"migration", "coup_risk", "security_incident", "org_founded", "org_dissolved", "news_issue"}
        if et not in major_types:
            return None

        chain: list[CausalityLink] = []
        prev_types = [e.get("type") for e in recent_events[-20:]]
        if "migration" in prev_types and et in {"security_incident", "coup_risk"}:
            chain.append(CausalityLink("social", "migration shocks amplified urban and political tension"))
        if "coup_risk" in prev_types and et == "security_incident":
            chain.append(CausalityLink("political", "elite fragmentation reduced command coherence"))
        if "security_incident" in prev_types and et.startswith("org_"):
            chain.append(CausalityLink("diplomatic", "recurring security incidents increased coordination pressure"))
        if et == "news_issue":
            chain.append(CausalityLink("information", "public event cadence triggered outlet publication cycle"))

        chain.extend(self._metric_chain(metrics))
        if not chain:
            return None

        confidence = min(0.95, 0.45 + 0.08 * len(chain))
        return {
            "event_id": event.get("id", ""),
            "causal_chain": [{"type": c.type, "description": c.description} for c in chain[:5]],
            "confidence": round(confidence, 2),
        }

    def attach(self, event: dict[str, Any], derived: dict[str, Any] | None) -> None:
        if not derived:
            return
        event["causal_chain"] = derived["causal_chain"]
        event["causal_confidence"] = derived["confidence"]
        if event.get("id"):
            self.chains[event["id"]] = derived
