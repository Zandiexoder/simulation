from __future__ import annotations

from dataclasses import dataclass, field


EDGE_TYPES = {"family", "friendship", "coworker", "political", "religious"}


@dataclass(slots=True)
class SocialGraph:
    nodes: set[str] = field(default_factory=set)
    edges: dict[str, dict[str, dict]] = field(default_factory=dict)

    def add_node(self, node_id: str) -> None:
        self.nodes.add(node_id)
        self.edges.setdefault(node_id, {})

    def add_edge(self, src: str, dst: str, edge_type: str, trust: float = 0.5) -> None:
        if edge_type not in EDGE_TYPES:
            raise ValueError(f"invalid edge_type: {edge_type}")
        self.add_node(src)
        self.add_node(dst)
        self.edges[src][dst] = {"type": edge_type, "trust": max(0.0, min(1.0, trust))}

    def neighbors(self, node_id: str) -> list[str]:
        return list(self.edges.get(node_id, {}).keys())

    def degree(self, node_id: str) -> int:
        return len(self.edges.get(node_id, {}))
