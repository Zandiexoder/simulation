from __future__ import annotations

from dataclasses import dataclass
import random

from sim.social.graph import SocialGraph


@dataclass(slots=True)
class Message:
    message_id: str
    source: str
    content: str
    reliability: float
    confidence: float
    mutation_probability: float


class InformationSystem:
    def __init__(self, seed: int = 0) -> None:
        self.rng = random.Random(seed)

    def propagate(self, graph: SocialGraph, seeds: list[str], message: Message) -> dict[str, dict]:
        inbox: dict[str, dict] = {}
        frontier = list(seeds)
        visited = set(frontier)
        while frontier:
            src = frontier.pop(0)
            for dst in graph.neighbors(src):
                if dst in visited:
                    continue
                visited.add(dst)
                mutated = self.rng.random() < message.mutation_probability
                confidence = max(0.0, min(1.0, message.confidence - (0.05 if mutated else 0.0)))
                reliability = max(0.0, min(1.0, message.reliability - (0.07 if mutated else 0.01)))
                inbox[dst] = {
                    "content": message.content + (" (rumor variant)" if mutated else ""),
                    "confidence": confidence,
                    "reliability": reliability,
                    "source": src,
                }
                frontier.append(dst)
        return inbox
