from __future__ import annotations

from dataclasses import dataclass
import random


@dataclass(slots=True)
class KnowledgeState:
    observed: dict
    reported: dict
    inferred: dict
    believed: dict
    unknown: list[str]
    trust_scores: dict[str, float]
    suspicion_scores: dict[str, float]


DEFAULT_GOALS = ["survival", "wealth", "family", "status", "security", "ideology"]


def default_knowledge() -> KnowledgeState:
    return KnowledgeState(
        observed={},
        reported={},
        inferred={},
        believed={},
        unknown=["other_agents_private_goals", "hidden_affiliations", "future_actions"],
        trust_scores={},
        suspicion_scores={},
    )


def default_traits(seed: int) -> dict[str, float]:
    rng = random.Random(seed)
    return {
        "ambition": rng.random(),
        "conformity": rng.random(),
        "empathy": rng.random(),
        "aggression": rng.random(),
        "risk_tolerance": rng.random(),
        "religiosity": rng.random(),
        "curiosity": rng.random(),
    }


def perception_stage(neighborhood_size: int, market_signal: float, risk: float) -> dict:
    return {
        "social_opportunity": min(1.0, neighborhood_size / 10),
        "market_signal": market_signal,
        "risk": risk,
    }


def needs_update_stage(needs: dict, traits: dict) -> dict:
    return {
        "hunger": max(0.0, min(1.0, needs.get("hunger", 0.5) + 0.02)),
        "wealth": needs.get("wealth", 0.5),
        "safety": max(0.0, 1.0 - traits.get("risk_tolerance", 0.5)),
    }


def candidate_action_stage() -> list[str]:
    return ["work", "socialize", "rest", "trade", "forage", "organize", "pray"]


def utility_scoring_stage(candidates: list[str], needs: dict, perception: dict, traits: dict, goals: list[str]) -> dict[str, float]:
    wealth_goal = 1.0 if "wealth" in goals else 0.4
    family_goal = 1.0 if "family" in goals else 0.2
    ideology_goal = 0.8 if "ideology" in goals else 0.1
    return {
        "work": 0.4 + wealth_goal + traits.get("ambition", 0.5),
        "socialize": 0.2 + family_goal + perception.get("social_opportunity", 0.1) + traits.get("empathy", 0.5),
        "rest": 0.2 + needs.get("hunger", 0.5),
        "trade": 0.3 + wealth_goal + perception.get("market_signal", 0.2),
        "forage": 0.2 + needs.get("hunger", 0.5),
        "organize": 0.1 + ideology_goal + traits.get("aggression", 0.3),
        "pray": 0.1 + traits.get("religiosity", 0.3),
    }


def stochastic_selection_stage(scores: dict[str, float], rng: random.Random) -> str:
    return max(scores, key=lambda c: scores[c] + rng.random() * 0.1)


def execution_stage(action: str) -> str:
    return action


def run_cognition(tier: int, needs: dict, perception: dict, seed: int, traits: dict | None = None, goals: list[str] | None = None) -> str:
    rng = random.Random(seed)
    traits = traits or default_traits(seed)
    goals = goals or DEFAULT_GOALS
    updated_needs = needs_update_stage(needs, traits)
    candidates = candidate_action_stage()
    scores = utility_scoring_stage(candidates, updated_needs, perception, traits, goals)
    action = stochastic_selection_stage(scores, rng)
    if tier == 2 and perception.get("risk", 0.0) > 0.8:
        action = "avoid_risk"
    return execution_stage(action)
