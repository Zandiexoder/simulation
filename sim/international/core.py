from __future__ import annotations

from dataclasses import dataclass, field
import uuid


@dataclass(slots=True)
class InternationalOrganization:
    org_id: str
    name: str
    org_type: str
    founding_members: list[str]
    members: list[str]
    charter: str
    mandate: list[str]
    legitimacy: float
    enforcement_capacity: float
    budget: float
    voting_structure: str
    membership_rules: str
    ideological_character: str
    prestige: float
    institutional_effectiveness: float
    influence: dict[str, float] = field(default_factory=dict)
    voting_blocs: list[list[str]] = field(default_factory=list)
    internal_factions: list[list[str]] = field(default_factory=list)
    status: str = "active"


@dataclass(slots=True)
class InternationalSystem:
    organizations: dict[str, InternationalOrganization] = field(default_factory=dict)
    org_formation_threshold: float = 0.63
    deadlock_band_low: float = 0.45
    deadlock_band_high: float = 0.62

    def _recompute_internal_politics(self, org: InternationalOrganization, nations: list[dict]) -> None:
        st = {n["id"]: n.get("stability", 0.5) for n in nations}
        weights = {m: max(0.05, min(0.6, 0.2 + 0.6 * st.get(m, 0.5))) for m in org.members}
        total = sum(weights.values()) or 1.0
        org.influence = {k: round(v / total, 3) for k, v in weights.items()}

        sorted_members = sorted(org.members, key=lambda m: org.influence.get(m, 0), reverse=True)
        top = sorted_members[: max(1, len(sorted_members) // 3)]
        rest = [m for m in sorted_members if m not in top]
        org.voting_blocs = [top, rest] if rest else [top]
        org.internal_factions = org.voting_blocs.copy()

        top_power = sum(org.influence.get(m, 0) for m in top)
        if self.deadlock_band_low <= top_power <= self.deadlock_band_high and len(org.members) >= 3:
            org.status = "deadlocked"
        elif top_power > 0.68:
            org.status = "dominant_bloc"
        else:
            org.status = "contested"

    def _effectiveness(self, org: InternationalOrganization) -> float:
        cohesion = min(1.0, max(0.0, len(org.members) / 8))
        deadlock_penalty = 0.2 if org.status == "deadlocked" else 0.0
        return max(
            0.0,
            min(
                1.0,
                0.25 * org.legitimacy
                + 0.2 * org.enforcement_capacity
                + 0.2 * min(1.0, org.budget / 100)
                + 0.2 * cohesion
                + 0.15 * org.prestige
                - deadlock_penalty,
            ),
        )

    def tick(self, *, tick: int, nations: list[dict], crisis_signal: dict[str, float]) -> list[dict]:
        events: list[dict] = []
        if len(nations) < 2:
            return events

        summit_pressure = crisis_signal.get("diplomatic_summits", 0.0)
        war_pressure = crisis_signal.get("interstate_wars", 0.0)
        refugee_pressure = crisis_signal.get("refugee_crises", 0.0)
        trade_interdep = crisis_signal.get("trade_interdependence", 0.0)
        sanctions = crisis_signal.get("sanctions_coordination", 0.0)

        need_score = 0.28 * summit_pressure + 0.2 * war_pressure + 0.2 * refugee_pressure + 0.18 * trade_interdep + 0.14 * sanctions
        if need_score > self.org_formation_threshold and len(self.organizations) < 6:
            founders = [n["id"] for n in nations[: min(4, len(nations))]]
            org_type = "general_diplomatic_assembly" if war_pressure < 0.55 else "collective_security_council"
            org = InternationalOrganization(
                org_id=f"org-{uuid.uuid4().hex[:8]}",
                name=f"{org_type.replace('_', ' ').title()} {tick}",
                org_type=org_type,
                founding_members=founders,
                members=founders.copy(),
                charter="Members coordinate crisis response and arbitration under shared procedures.",
                mandate=["diplomacy", "arbitration", "coordination"],
                legitimacy=0.45 + 0.3 * need_score,
                enforcement_capacity=0.25 + 0.25 * war_pressure,
                budget=20 + 50 * trade_interdep,
                voting_structure="weighted_consensus",
                membership_rules="charter_signatory",
                ideological_character="mixed",
                prestige=0.35 + 0.2 * summit_pressure,
                institutional_effectiveness=0.0,
            )
            self._recompute_internal_politics(org, nations)
            org.institutional_effectiveness = self._effectiveness(org)
            self.organizations[org.org_id] = org
            events.append({"tick": tick, "type": "org_founded", "org_id": org.org_id, "message": f"{org.name} founded by {', '.join(founders)}."})

        for org in self.organizations.values():
            for n in nations:
                nid = n["id"]
                if nid in org.members:
                    continue
                join_score = 0.35 * trade_interdep + 0.25 * summit_pressure + 0.2 * refugee_pressure + 0.2 * org.prestige
                if join_score > 0.62:
                    org.members.append(nid)
                    events.append({"tick": tick, "type": "org_join", "org_id": org.org_id, "nation_id": nid, "message": f"{nid} joined {org.name}."})

            leave_candidates = []
            for member in org.members:
                leave_pressure = 0.45 * crisis_signal.get("great_power_rivalry", 0.0) + 0.3 * (1 - org.legitimacy) + 0.25 * (1 - org.enforcement_capacity)
                if leave_pressure > 0.76 and len(org.members) > 2:
                    leave_candidates.append(member)
            for m in leave_candidates[:1]:
                org.members.remove(m)
                events.append({"tick": tick, "type": "org_leave", "org_id": org.org_id, "nation_id": m, "message": f"{m} left {org.name}."})

            self._recompute_internal_politics(org, nations)
            if org.status == "deadlocked":
                org.legitimacy = max(0.0, org.legitimacy - 0.03)
                events.append({"tick": tick, "type": "org_deadlock", "org_id": org.org_id, "message": f"{org.name} entered voting deadlock."})
            elif org.status == "dominant_bloc":
                org.legitimacy = max(0.0, min(1.0, org.legitimacy - 0.01 + 0.02 * org.enforcement_capacity))
            else:
                org.legitimacy = max(0.0, min(1.0, org.legitimacy + 0.01))

            org.institutional_effectiveness = self._effectiveness(org)
            org.budget = max(0.0, org.budget + 0.6 * len(org.members) - 1.2 * crisis_signal.get("crisis_load", 0.0))

        dissolve = [oid for oid, org in self.organizations.items() if org.institutional_effectiveness < 0.18 and org.legitimacy < 0.22]
        for oid in dissolve:
            name = self.organizations[oid].name
            del self.organizations[oid]
            events.append({"tick": tick, "type": "org_dissolved", "org_id": oid, "message": f"{name} dissolved after institutional collapse."})

        return events
