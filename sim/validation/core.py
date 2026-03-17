from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
from typing import Any


@dataclass(slots=True)
class ReproComparison:
    equal_within_tolerance: bool
    max_abs_delta: float
    deltas: dict[str, float]


def compare_metrics(a: dict[str, float], b: dict[str, float], tolerance: float = 1e-9) -> ReproComparison:
    keys = set(a) | set(b)
    deltas = {k: abs(float(a.get(k, 0.0)) - float(b.get(k, 0.0))) for k in keys}
    max_abs_delta = max(deltas.values()) if deltas else 0.0
    return ReproComparison(equal_within_tolerance=max_abs_delta <= tolerance, max_abs_delta=max_abs_delta, deltas=deltas)


def p95(values: list[float]) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    idx = int(0.95 * (len(s) - 1))
    return float(s[idx])


def benchmark_summary(samples: list[float]) -> dict[str, Any]:
    if not samples:
        return {"count": 0, "avg": 0.0, "p95": 0.0, "min": 0.0, "max": 0.0}
    return {
        "count": len(samples),
        "avg": sum(samples) / len(samples),
        "p95": p95(samples),
        "min": min(samples),
        "max": max(samples),
    }


def write_json(path: str | Path, payload: Any) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(f"{json.dumps(payload, indent=2, sort_keys=True)}\n", encoding="utf-8")
