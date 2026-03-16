from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sim.conflict import ConflictSystem
from sim.economy import EconomySystem
from sim.history import HistorySystem
from sim.households import HouseholdSystem
from sim.intelligence import IntelligenceSystem
from sim.migration import MigrationSystem
from sim.politics import PoliticsSystem
from sim.social import SocialGraph
from sim.urban import UrbanSystem


@dataclass(slots=True)
class ECSStore:
    identity: dict[str, dict] = field(default_factory=dict)
    location: dict[str, tuple[int, int]] = field(default_factory=dict)
    health: dict[str, float] = field(default_factory=dict)
    wealth: dict[str, float] = field(default_factory=dict)
    needs: dict[str, dict[str, float]] = field(default_factory=dict)
    goals: dict[str, list[str]] = field(default_factory=dict)
    traits: dict[str, dict[str, float]] = field(default_factory=dict)
    relationships: dict[str, dict[str, float]] = field(default_factory=dict)
    memory: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    household: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class SimulationState:
    tick: int = 0
    running: bool = False
    seed: int = 42
    ecs: ECSStore = field(default_factory=ECSStore)
    world_map: dict[str, Any] = field(default_factory=dict)
    cities: list[dict] = field(default_factory=list)
    nations: list[dict] = field(default_factory=list)
    agents: list[dict] = field(default_factory=list)

    true_state: dict[str, Any] = field(default_factory=dict)
    knowledge_state: dict[str, dict] = field(default_factory=dict)
    intelligence_reports: list[dict] = field(default_factory=list)
    events: list[dict] = field(default_factory=list)
    metrics: dict[str, float] = field(default_factory=dict)

    households: HouseholdSystem = field(default_factory=HouseholdSystem)
    economy: EconomySystem = field(default_factory=EconomySystem)
    social_graph: SocialGraph = field(default_factory=SocialGraph)
    migration: MigrationSystem = field(default_factory=MigrationSystem)
    urban: UrbanSystem = field(default_factory=UrbanSystem)
    politics: PoliticsSystem = field(default_factory=PoliticsSystem)
    intelligence: IntelligenceSystem = field(default_factory=IntelligenceSystem)
    conflict: ConflictSystem = field(default_factory=ConflictSystem)
    history: HistorySystem = field(default_factory=HistorySystem)

    narratives: dict[str, Any] = field(default_factory=dict)
