from pathlib import Path

from sim.kernel.pipeline import SimulationKernel
from sim.kernel.state import SimulationState
from sim.scheduler import Scheduler


def _run(seed: int, ticks: int = 4):
    s = SimulationState(seed=seed)
    s.agents = []
    k = SimulationKernel(s)
    k.step(ticks)
    return s.tick, dict(s.metrics), [e.get("type") for e in s.events[-10:]]


def test_same_seed_reproducible_metrics_and_event_shapes():
    a = _run(101, 5)
    b = _run(101, 5)
    assert a[0] == b[0]
    assert a[1] == b[1]
    assert a[2] == b[2]


def test_snapshot_roundtrip_load(tmp_path: Path):
    state = SimulationState(seed=7)
    state.agents = []
    sched = Scheduler(kernel=SimulationKernel(state), state=state, snapshot_interval=1, snapshot_dir=str(tmp_path))
    sched.step(2)
    snaps = sched.list_snapshots()
    assert snaps
    sid = snaps[-1]["snapshot_id"]

    state.metrics["dummy"] = 999
    loaded = sched.load_snapshot(sid)
    assert loaded.get("loaded") == sid
    assert state.tick == snaps[-1]["tick"]
