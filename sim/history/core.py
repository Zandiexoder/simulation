from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class Snapshot:
    tick: int
    metrics: dict
    city_stats: dict
    nation_stats: dict


@dataclass(slots=True)
class HistorySystem:
    events: list[dict] = field(default_factory=list)
    snapshots: list[Snapshot] = field(default_factory=list)

    def append_event(self, event: dict) -> None:
        self.events.append(event)

    def add_snapshot(self, *, tick: int, metrics: dict, city_stats: dict, nation_stats: dict) -> None:
        self.snapshots.append(Snapshot(tick=tick, metrics=metrics, city_stats=city_stats, nation_stats=nation_stats))

    def compare(self, tick_a: int, tick_b: int) -> dict:
        a = next((s for s in self.snapshots if s.tick == tick_a), None)
        b = next((s for s in self.snapshots if s.tick == tick_b), None)
        if not a or not b:
            return {"error": "snapshot_missing"}
        return {
            "tick_a": tick_a,
            "tick_b": tick_b,
            "metric_delta": {k: b.metrics.get(k, 0) - a.metrics.get(k, 0) for k in set(a.metrics) | set(b.metrics)},
        }

    def replay_window(self, start_tick: int, end_tick: int) -> list[dict]:
        return [e for e in self.events if start_tick <= e.get("tick", -1) <= end_tick]
