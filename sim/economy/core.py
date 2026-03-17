from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class Firm:
    firm_id: str
    city_id: str
    sector: str
    wage_offer: float
    productivity: float


@dataclass(slots=True)
class CityEconomy:
    city_id: str
    price_index: float = 1.0
    wage_index: float = 1.0
    trade_flow: float = 0.0


@dataclass(slots=True)
class EconomySystem:
    firms: dict[str, Firm] = field(default_factory=dict)
    city_profiles: dict[str, CityEconomy] = field(default_factory=dict)

    def register_city(self, city_id: str) -> None:
        self.city_profiles.setdefault(city_id, CityEconomy(city_id=city_id))

    def add_firm(self, firm: Firm) -> None:
        self.firms[firm.firm_id] = firm
        self.register_city(firm.city_id)

    def market_tick(self) -> None:
        for city in self.city_profiles.values():
            local_firms = [f for f in self.firms.values() if f.city_id == city.city_id]
            if not local_firms:
                continue
            avg_wage = sum(f.wage_offer for f in local_firms) / len(local_firms)
            avg_prod = sum(f.productivity for f in local_firms) / len(local_firms)
            city.wage_index = max(0.1, avg_wage)
            city.price_index = max(0.1, 1.2 - avg_prod * 0.3)
            city.trade_flow = avg_prod * len(local_firms)

    def execute_transaction(self, payer_wealth: float, amount: float) -> tuple[float, float]:
        spend = min(payer_wealth, max(0.0, amount))
        return payer_wealth - spend, spend
