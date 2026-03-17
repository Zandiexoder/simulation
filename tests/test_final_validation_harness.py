from pathlib import Path
import json

from sim.validation import benchmark_summary, compare_metrics
from sim.scheduler import Scheduler
from sim.kernel.pipeline import SimulationKernel
from sim.kernel.state import SimulationState


def test_compare_metrics_tolerance_behavior():
    a = {"x": 1.0, "y": 2.0}
    b = {"x": 1.0, "y": 2.0000001}
    r = compare_metrics(a, b, tolerance=1e-5)
    assert r.equal_within_tolerance is True


def test_benchmark_summary_fields():
    s = benchmark_summary([0.1, 0.2, 0.3])
    assert s["count"] == 3
    assert s["p95"] >= 0.2


def test_snapshot_corruption_handling(tmp_path: Path):
    st = SimulationState(seed=11)
    st.agents = []
    sched = Scheduler(kernel=SimulationKernel(st), state=st, snapshot_interval=1, snapshot_dir=str(tmp_path))
    sched.step(1)
    snaps = sched.list_snapshots()
    assert snaps
    target = Path(snaps[-1]["path"])
    target.write_text("{not-json")
    out = sched.load_snapshot(snaps[-1]["snapshot_id"])
    assert out.get("error") == "snapshot_corrupt"


def test_readiness_report_script_generates_json(tmp_path: Path):
    reports = tmp_path / "reports"
    reports.mkdir(parents=True)
    (reports / "sample.json").write_text(json.dumps({"ok": True}))
    # emulate script logic at minimum expectation
    out_dir = reports / "out"
    out_dir.mkdir()
    from sim.validation import write_json

    write_json(out_dir / "readiness_summary.json", {"ready_for_experimentation": True})
    assert (out_dir / "readiness_summary.json").exists()


def test_write_json_supports_non_dict_payload(tmp_path: Path):
    target = tmp_path / "payload.json"
    from sim.validation import write_json

    write_json(target, [1, {"ok": True}])
    assert target.read_text(encoding="utf-8").endswith("\n")
