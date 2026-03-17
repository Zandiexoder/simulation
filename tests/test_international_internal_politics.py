from sim.international import InternationalSystem


def test_org_internal_politics_fields_present_and_deadlock_possible():
    system = InternationalSystem()
    nations = [{"id": f"n{i}", "stability": 0.5 + (i % 2) * 0.1} for i in range(5)]
    system.tick(
        tick=1,
        nations=nations,
        crisis_signal={
            "diplomatic_summits": 0.9,
            "interstate_wars": 0.6,
            "refugee_crises": 0.7,
            "trade_interdependence": 0.7,
            "sanctions_coordination": 0.7,
            "great_power_rivalry": 0.4,
            "crisis_load": 0.3,
        },
    )
    assert system.organizations
    org = next(iter(system.organizations.values()))
    assert isinstance(org.influence, dict)
    assert isinstance(org.internal_factions, list)
    assert org.status in {"deadlocked", "dominant_bloc", "contested"}
