from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
from pathlib import Path
import time
from typing import Any

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
    snapshot_dir: str = "./data/snapshots"
    manifest: dict[str, Any] = field(default_factory=lambda: {"snapshots": []})

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

    def _config_fingerprint(self) -> str:
        payload = {
            "seed": self.state.seed,
            "scenario": self.state.scenario_name,
            "tuning": self.state.tuning.as_dict() if hasattr(self.state, "tuning") else {},
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]

    def _snapshot_payload(self) -> dict[str, Any]:
        return {
            "metadata": {
                "tick": self.state.tick,
                "saved_at": time.time(),
                "seed": self.state.seed,
                "scenario": self.state.scenario_name,
                "config_fingerprint": self._config_fingerprint(),
                "reproducibility_notes": "Deterministic given same seed/config and service responses.",
            },
            "state": {
                "tick": self.state.tick,
                "metrics": dict(self.state.metrics),
                "events": self.state.events[-500:],
                "cities": self.state.cities,
                "nations": self.state.nations,
                "history": {
                    "events": self.state.history.events[-1000:],
                    "media_issues": self.state.history.media_issues[-500:],
                    "causal_index": self.state.history.causal_index,
                    "milestones": self.state.history.milestones,
                },
                "organizations": {k: asdict(v) for k, v in self.state.international.organizations.items()},
                "outlets": {k: asdict(v) for k, v in self.state.media.outlets.items()},
                "diagnostics": self.state.diagnostics,
            },
        }

    def save_snapshot(self) -> dict[str, Any]:
        payload = self._snapshot_payload()
        out_dir = Path(self.snapshot_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        sid = f"snap-{self.state.tick}-{int(time.time())}"
        path = out_dir / f"{sid}.json"
        path.write_text(json.dumps(payload))
        entry = {"snapshot_id": sid, "tick": self.state.tick, "path": str(path), **payload["metadata"]}
        self.manifest.setdefault("snapshots", []).append(entry)
        (out_dir / "manifest.json").write_text(json.dumps(self.manifest))
        self.snapshots.append({"tick": self.state.tick, "metrics": dict(self.state.metrics), "events": len(self.state.events), "snapshot_id": sid})
        return entry

    def list_snapshots(self) -> list[dict[str, Any]]:
        return self.manifest.get("snapshots", [])[-100:]

    def load_snapshot(self, snapshot_id: str) -> dict[str, Any]:
        entry = next((s for s in self.manifest.get("snapshots", []) if s.get("snapshot_id") == snapshot_id), None)
        if not entry:
            return {"error": "snapshot_not_found"}
        try:
            payload = json.loads(Path(entry["path"]).read_text())
        except Exception:
            return {"error": "snapshot_corrupt", "snapshot_id": snapshot_id}

        st = payload.get("state", {})
        self.state.tick = st.get("tick", self.state.tick)
        self.state.metrics = st.get("metrics", self.state.metrics)
        self.state.events = st.get("events", self.state.events)
        self.state.cities = st.get("cities", self.state.cities)
        self.state.nations = st.get("nations", self.state.nations)
        hist = st.get("history", {})
        self.state.history.events = hist.get("events", self.state.history.events)
        self.state.history.media_issues = hist.get("media_issues", self.state.history.media_issues)
        self.state.history.causal_index = hist.get("causal_index", self.state.history.causal_index)
        self.state.history.milestones = hist.get("milestones", self.state.history.milestones)
        self.state.diagnostics = st.get("diagnostics", self.state.diagnostics)
        self.replay_mode = True
        return {"loaded": snapshot_id, "tick": self.state.tick}

    def step(self, ticks: int = 1) -> SimulationState:
        if self.replay_mode:
            return self.state
        target = max(1, ticks) * self.speed
        self.kernel.step(target)
        if self.state.tick % self.snapshot_interval == 0:
            self.state.history.add_snapshot(
                tick=self.state.tick,
                metrics=dict(self.state.metrics),
                city_stats={c["id"]: {"population": c.get("population", 0)} for c in self.state.cities},
                nation_stats={n["id"]: {"stability": n.get("stability", 0)} for n in self.state.nations},
            )
            self.save_snapshot()
        return self.state
