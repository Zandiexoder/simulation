from __future__ import annotations

import random
import time
from collections import Counter
from dataclasses import asdict
import uuid

from sim.agents.cognition import default_knowledge, run_cognition
from sim.information import InformationSystem, Message
from sim.kernel.spatial import SpatialIndex
from sim.kernel.state import SimulationState


class SimulationKernel:
    def __init__(self, state: SimulationState):
        self.state = state
        self.spatial = SpatialIndex()
        self.information = InformationSystem(seed=state.seed)
        self.state.media.issue_interval = self.state.tuning.media.issue_interval

    def step(self, ticks: int = 1) -> SimulationState:
        for _ in range(ticks):
            self._single_tick()
        return self.state


    def _attach_causality(self, event: dict) -> dict:
        derived = self.state.causality.derive(event=event, recent_events=self.state.events, metrics=self.state.metrics)
        self.state.causality.attach(event, derived)
        return event

    def _single_tick(self) -> None:
        self.state.tick += 1
        tick = self.state.tick
        rng = random.Random(self.state.seed + tick)
        tick_started = time.perf_counter()
        module_timings: dict[str, float] = {}

        for nation in self.state.nations:
            nation["stability"] = max(0.0, min(1.0, nation["stability"] + (rng.random() - 0.5) * 0.02))

        t0 = time.perf_counter(); self.state.economy.market_tick(); module_timings["economy"] = time.perf_counter() - t0
        t0 = time.perf_counter(); self.state.households.run_tick(); module_timings["households"] = time.perf_counter() - t0
        t0 = time.perf_counter(); urban_events = self.state.urban.tick(); module_timings["urban"] = time.perf_counter() - t0

        migration_city_metrics = {
            c["id"]: {
                "wage_delta": 0.4 + rng.random() * 0.6,
                "unemployment": rng.random() * 0.7,
                "housing_pressure": self.state.urban.cities.get(c["id"], None).density_pressure if c["id"] in self.state.urban.cities else 0.5,
                "food_pressure": 1 - (self.state.urban.cities.get(c["id"], None).food_access if c["id"] in self.state.urban.cities else 0.7),
                "conflict_risk": rng.random() * 0.6,
                "repression": rng.random() * 0.5,
                "climate_stress": rng.random() * 0.6,
                "network_pull": rng.random(),
                "prestige": rng.random(),
                "misinformation": rng.random() * 0.5,
                "border_policy": 0.45 + rng.random() * 0.5,
            }
            for c in self.state.cities
        }

        self.spatial.rebuild(self.state.ecs.location)
        actions: list[tuple[str, str]] = []
        migration_events: list[dict] = []

        for idx, agent in enumerate(self.state.agents):
            agent_id = agent["id"]
            loc = self.state.ecs.location.get(agent_id, (0, 0))
            neighborhood = self.spatial.neighbors(loc)
            perception = {
                "social_opportunity": min(1.0, len(neighborhood) / 10),
                "market_signal": rng.random(),
                "risk": rng.random(),
            }
            ks = self.state.knowledge_state.setdefault(agent_id, asdict(default_knowledge()))
            ks["observed"] = {"neighbors": [n for n in neighborhood if n != agent_id]}
            ks["inferred"]["regional_risk"] = perception["risk"]

            action = run_cognition(
                agent.get("tier", 1),
                self.state.ecs.needs.get(agent_id, {}),
                perception,
                self.state.seed + tick + idx,
                traits=self.state.ecs.traits.get(agent_id),
                goals=self.state.ecs.goals.get(agent_id),
            )
            actions.append((agent_id, action))

            current_city = agent.get("city_id", self.state.cities[0]["id"] if self.state.cities else "")
            next_city, rec = self.state.migration.decide_and_apply(
                tick=tick,
                agent=agent,
                cities=self.state.cities,
                city_metrics=migration_city_metrics,
                household_city=current_city,
            )
            if rec:
                agent["city_id"] = next_city
                target_city = next((c for c in self.state.cities if c["id"] == next_city), None)
                if target_city:
                    self.state.ecs.location[agent_id] = (target_city["x"], target_city["y"])
                migration_events.append({"tick": tick, "type": "migration", "agent_id": rec.agent_id, "from": rec.from_city, "to": rec.to_city, "score": rec.score})

        for agent_id, action in actions:
            wealth = self.state.ecs.wealth.get(agent_id, 0.5)
            if action == "work":
                wealth += 0.05
            elif action == "trade":
                wealth, _ = self.state.economy.execute_transaction(wealth, 0.03)
                wealth += 0.04
            elif action == "forage":
                wealth += 0.01
            else:
                wealth -= 0.01
            self.state.ecs.wealth[agent_id] = max(0.0, min(2.0, wealth))

        if self.state.agents:
            seed_actor = self.state.agents[tick % len(self.state.agents)]["id"]
            msg = Message(
                message_id=str(uuid.uuid4()),
                source=seed_actor,
                content="Market uncertainty is rising in nearby districts.",
                reliability=0.72,
                confidence=0.66,
                mutation_probability=0.18,
            )
            diffusion = self.information.propagate(self.state.social_graph, [seed_actor], msg)
            for aid, packet in diffusion.items():
                ks = self.state.knowledge_state.setdefault(aid, asdict(default_knowledge()))
                ks["reported"][f"msg-{tick}"] = packet
                ks["believed"]["market_uncertainty"] = packet["confidence"] * packet["reliability"]

        t0 = time.perf_counter()
        political_events = self.state.politics.tick(
            econ_stress=min(1.0, 1 - self.state.metrics.get("avg_wealth", 0.5)),
            migration_stress=min(1.0, len(migration_events) / max(1, len(self.state.agents))),
            security_threat=min(1.0, len(self.state.conflict.incidents) / 20),
        )
        module_timings["politics"] = time.perf_counter() - t0

        t0 = time.perf_counter()
        intel = self.state.intelligence.add_report(
            tick=tick,
            target_scope="military_posture",
            source_type="recon",
            reliability=round(0.5 + rng.random() * 0.4, 2),
            confidence=round(0.4 + rng.random() * 0.4, 2),
            bias="institutional",
            secrecy="secret",
            summary="Partial estimate of border readiness.",
        )
        self.state.intelligence.tick(tick)
        module_timings["intelligence"] = time.perf_counter() - t0
        for n in self.state.nations:
            self.state.intelligence.update_fog(
                n["id"],
                known={"own_readiness": 0.7},
                suspected={"neighbor_mobilization": 0.4},
                estimated={"foreign_coup_risk": 0.3},
                unknown=["covert_programs", "hidden_shortages"],
            )

        t0 = time.perf_counter()
        conflict_events = self.state.conflict.tick(
            tick=tick,
            legitimacy=sum(v.legitimacy for v in self.state.politics.nations.values()) / max(1, len(self.state.politics.nations)),
            intelligence_quality=intel.confidence_score,
            urban_density=sum(v.density_pressure for v in self.state.urban.cities.values()) / max(1, len(self.state.urban.cities)),
        )
        module_timings["conflict"] = time.perf_counter() - t0

        crisis_signal = {
            "diplomatic_summits": min(1.0, 0.2 + len(self.state.events) / 400),
            "interstate_wars": min(1.0, len(conflict_events) / 6),
            "refugee_crises": min(1.0, len(migration_events) / 35),
            "sanctions_coordination": min(1.0, len([e for e in self.state.events[-25:] if e.get("type") == "coup_risk"]) / 8),
            "trade_interdependence": min(1.0, len(self.state.economy.firms) / 30),
            "great_power_rivalry": min(1.0, len([e for e in self.state.events[-20:] if e.get("type") == "security_incident"]) / 8),
            "crisis_load": min(1.0, (len(conflict_events) + len(migration_events)) / 20),
        }
        t0 = time.perf_counter(); org_events = self.state.international.tick(tick=tick, nations=self.state.nations, crisis_signal=crisis_signal); module_timings["international"] = time.perf_counter() - t0

        action_counts = Counter(a for _, a in actions)
        event = {
            "id": str(uuid.uuid4()),
            "tick": tick,
            "type": "tick_summary",
            "message": f"Tick {tick} resolved with {len(actions)} agent actions.",
            "actions": dict(action_counts),
        }
        event = self._attach_causality(event)
        self.state.events.append(event)
        self.state.history.append_event(event)

        all_events = [*urban_events, *migration_events, *political_events, *conflict_events, *org_events]
        for ev in all_events:
            e = {"id": str(uuid.uuid4()), **ev}
            e = self._attach_causality(e)
            self.state.events.append(e)
            self.state.history.append_event(e)

        t0 = time.perf_counter()
        media_issues = self.state.media.tick(
            tick=tick,
            visible_events=self.state.events,
            nations=self.state.nations,
            force_trigger=False,
        )
        module_timings["media"] = time.perf_counter() - t0
        for issue in media_issues:
            issue_dict = asdict(issue)
            self.state.history.add_media_issue(issue_dict)
            news_event = {
                "id": str(uuid.uuid4()),
                "tick": tick,
                "type": "news_issue",
                "issue_id": issue.issue_id,
                "event_id": issue.event_id,
                "message": f"{issue_dict['outlet_id']} published issue.",
            }
            news_event = self._attach_causality(news_event)
            self.state.events.append(news_event)
            self.state.history.append_event(news_event)

        self.state.intelligence_reports.append(asdict(intel))

        milestone_events = self.state.emergence.evaluate(
            tick=tick,
            events=self.state.events,
            org_count=len(self.state.international.organizations),
            media_count=len(self.state.history.media_issues),
            conflict_incidents=len(self.state.conflict.incidents),
            migration_events=len(migration_events),
            migration_wave_threshold=self.state.tuning.emergence.major_migration_wave_threshold,
        )
        for mev in milestone_events:
            m = {"id": str(uuid.uuid4()), **mev}
            m = self._attach_causality(m)
            self.state.events.append(m)
            self.state.history.append_event(m)

        wealths = list(self.state.ecs.wealth.values())
        self.state.metrics = {
            "agent_count": float(len(self.state.agents)),
            "avg_wealth": sum(wealths) / max(1, len(wealths)),
            "event_count": float(len(self.state.events)),
            "household_count": float(len(self.state.households.households)),
            "firm_count": float(len(self.state.economy.firms)),
            "migration_events": float(len(migration_events)),
            "urban_growth_cities": float(sum(1 for c in self.state.urban.cities.values() if c.growth_trend > 0.2)),
            "avg_legitimacy": sum(v.legitimacy for v in self.state.politics.nations.values()) / max(1, len(self.state.politics.nations)),
            "conflict_incidents": float(len(self.state.conflict.incidents)),
            "intel_reports": float(len(self.state.intelligence.reports)),
            "international_orgs": float(len(self.state.international.organizations)),
            "media_issues": float(len(self.state.history.media_issues)),
        }

        tick_duration = time.perf_counter() - tick_started
        perf = self.state.diagnostics.setdefault("perf", {})
        perf["last_tick_duration_s"] = round(tick_duration, 6)
        perf["module_timings_s"] = {k: round(v, 6) for k, v in module_timings.items()}
        counters = self.state.diagnostics.setdefault("counters", {})
        counters["media_generation_count"] = counters.get("media_generation_count", 0) + len(media_issues)
        counters["history_archive_size"] = len(self.state.history.events)
        counters["causal_index_size"] = len(self.state.history.causal_index)
        max_events = int(self.state.run_metadata.get("history_event_retention", 5000))
        if len(self.state.events) > max_events:
            self.state.events = self.state.events[-max_events:]
        if len(self.state.history.events) > max_events:
            self.state.history.events = self.state.history.events[-max_events:]

        self.state.true_state["last_published_tick"] = tick
