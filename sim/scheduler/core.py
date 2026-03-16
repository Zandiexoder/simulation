from __future__ import annotations

from dataclasses import dataclass, field

from sim.kernel.pipeline import SimulationKernel
from sim.kernel.state import SimulationState


@dataclass(slots=True)
class Scheduler:
    kernel: SimulationKernel
    state: SimulationState
    running: bool = False
    speed: int = 1
    snapshot_interval: int = 10
    snapshots: list[dict] = field(default_factory=list)
    replay_mode: bool = False

    def start(self) -> None:
        self.running = True
        self.state.running = True

    def pause(self) -> None:
        self.running = False
        self.state.running = False

    def set_speed(self, speed: int) -> None:
        self.speed = max(1, speed)

    def set_replay_mode(self, enabled: bool) -> None:
        self.replay_mode = enabled

    def step(self, ticks: int = 1) -> SimulationState:
        if self.replay_mode:
            return self.state
        target = max(1, ticks) * self.speed
        self.kernel.step(target)
        if self.state.tick % self.snapshot_interval == 0:
            snap = {
                "tick": self.state.tick,
                "metrics": dict(self.state.metrics),
                "events": len(self.state.events),
            }
            self.snapshots.append(snap)
            self.state.history.add_snapshot(
                tick=self.state.tick,
                metrics=dict(self.state.metrics),
                city_stats={c["id"]: {"population": c.get("population", 0)} for c in self.state.cities},
                nation_stats={n["id"]: {"stability": n.get("stability", 0)} for n in self.state.nations},
            )
        return self.state
