from __future__ import annotations

import random
from dataclasses import asdict
import uuid
from collections import Counter

from sim.agents.cognition import default_knowledge, run_cognition
from sim.information import InformationSystem, Message
from sim.kernel.spatial import SpatialIndex
from sim.kernel.state import SimulationState


class SimulationKernel:
    def __init__(self, state: SimulationState):
        self.state = state
        self.spatial = SpatialIndex()
        self.information = InformationSystem(seed=state.seed)

    def step(self, ticks: int = 1) -> SimulationState:
        for _ in range(ticks):
            self._single_tick()
        return self.state

    def _single_tick(self) -> None:
        self.state.tick += 1
        tick = self.state.tick
        rng = random.Random(self.state.seed + tick)

        for nation in self.state.nations:
            nation["stability"] = max(0.0, min(1.0, nation["stability"] + (rng.random() - 0.5) * 0.02))

        self.state.economy.market_tick()
        self.state.households.run_tick()

        urban_events = self.state.urban.tick()

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

        political_events = self.state.politics.tick(
            econ_stress=min(1.0, 1 - self.state.metrics.get("avg_wealth", 0.5)),
            migration_stress=min(1.0, len(migration_events) / max(1, len(self.state.agents))),
            security_threat=min(1.0, len(self.state.conflict.incidents) / 20),
        )

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
        for n in self.state.nations:
            self.state.intelligence.update_fog(
                n["id"],
                known={"own_readiness": 0.7},
                suspected={"neighbor_mobilization": 0.4},
                estimated={"foreign_coup_risk": 0.3},
                unknown=["covert_programs", "hidden_shortages"],
            )

        conflict_events = self.state.conflict.tick(
            tick=tick,
            legitimacy=sum(v.legitimacy for v in self.state.politics.nations.values()) / max(1, len(self.state.politics.nations)),
            intelligence_quality=intel.confidence_score,
            urban_density=sum(v.density_pressure for v in self.state.urban.cities.values()) / max(1, len(self.state.urban.cities)),
        )

        action_counts = Counter(a for _, a in actions)
        event = {
            "id": str(uuid.uuid4()),
            "tick": tick,
            "type": "tick_summary",
            "message": f"Tick {tick} resolved with {len(actions)} agent actions.",
            "actions": dict(action_counts),
        }
        self.state.events.append(event)
        self.state.history.append_event(event)
        for ev in [*urban_events, *migration_events, *political_events, *conflict_events]:
            e = {"id": str(uuid.uuid4()), **ev}
            self.state.events.append(e)
            self.state.history.append_event(e)

        self.state.intelligence_reports.append(asdict(intel))

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
        }

        self.state.true_state["last_published_tick"] = tick
