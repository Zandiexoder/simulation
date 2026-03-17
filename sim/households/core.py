from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class Household:
    household_id: str
    members: list[str]
    city_id: str
    shared_income: float = 0.0
    food_budget: float = 0.0
    housing_cost: float = 0.1
    savings: float = 0.0
    child_count: int = 0


@dataclass(slots=True)
class HouseholdSystem:
    households: dict[str, Household] = field(default_factory=dict)

    def add_household(self, household: Household) -> None:
        self.households[household.household_id] = household

    def run_tick(self) -> None:
        for h in self.households.values():
            expenses = h.housing_cost + (0.03 * max(1, len(h.members))) + (0.02 * h.child_count)
            h.savings = max(0.0, h.savings + h.shared_income - expenses)
            h.food_budget = max(0.05, h.food_budget + h.shared_income * 0.2)

    def relocation_candidates(self) -> list[str]:
        return [h.household_id for h in self.households.values() if h.savings < 0.05]
