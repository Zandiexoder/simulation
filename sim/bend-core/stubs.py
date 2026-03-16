"""Bend bridge stubs.

These stubs define integration points for future Bend kernels while preserving
pure-Python fallback behavior in the MVP.
"""


def score_agents(batch: list[dict]) -> list[dict]:
    return [{"agent_id": b.get("agent_id"), "scores": b.get("scores", {})} for b in batch]


def propagate_influence(graph: dict, signals: dict) -> dict:
    return {"graph_nodes": len(graph.get("nodes", [])), "signals": signals}


def clear_market(offers: list[dict], bids: list[dict]) -> dict:
    return {"clearing_price": 1.0, "matched": min(len(offers), len(bids))}


def regional_update(regions: list[dict]) -> list[dict]:
    return regions


def aggregate_metrics(values: list[float]) -> float:
    return sum(values)
