from sim.migration import MigrationSystem
from sim.urban import UrbanSystem
from sim.politics import PoliticsSystem
from sim.intelligence import IntelligenceSystem
from sim.conflict import ConflictSystem
from sim.history import HistorySystem


def test_migration_scoring_and_event():
    m = MigrationSystem()
    score = m.score_destination(
        wage_delta=0.9, unemployment=0.1, housing_pressure=0.2, food_pressure=0.2,
        conflict_risk=0.1, repression=0.2, affinity=1.0, climate_stress=0.3,
        border_policy=0.8, network_pull=0.8, prestige=0.9, misinformation=0.1,
    )
    assert score > 0.55
    city, rec = m.decide_and_apply(
        tick=3,
        agent={"id": "a1", "culture": "northern"},
        cities=[{"id": "c1", "culture": "northern"}, {"id": "c2", "culture": "northern"}],
        city_metrics={"c1": {"wage_delta": 0.1}, "c2": {"wage_delta": 1.0}},
        household_city="c1",
    )
    assert city == "c2"
    assert rec is not None


def test_urban_growth_decline():
    u = UrbanSystem()
    u.register_city("c1", 1000)
    u.cities["c1"].job_capacity = 1.5
    ev = u.tick()
    assert isinstance(ev, list)


def test_politics_legitimacy_and_coup_risk():
    p = PoliticsSystem()
    p.register("n1")
    events = p.tick(econ_stress=0.8, migration_stress=0.7, security_threat=0.5)
    assert p.nations["n1"].legitimacy < 0.7
    assert p.nations["n1"].coup_risk >= 0
    assert isinstance(events, list)


def test_intelligence_staleness_and_fog():
    i = IntelligenceSystem()
    r = i.add_report(tick=1, target_scope="foreign_readiness")
    i.tick(60)
    assert r.staleness > 0.9
    i.update_fog("n1", known={"a":1}, suspected={}, estimated={}, unknown=["x"])
    assert "x" in i.nation_fog["n1"]["unknown"]


def test_conflict_uncertainty_incident():
    c = ConflictSystem()
    out = c.tick(tick=2, legitimacy=0.2, intelligence_quality=0.2, urban_density=0.9)
    assert isinstance(out, list)


def test_history_replay_compare():
    h = HistorySystem()
    h.append_event({"tick": 1, "type": "a"})
    h.add_snapshot(tick=1, metrics={"x": 1}, city_stats={}, nation_stats={})
    h.add_snapshot(tick=2, metrics={"x": 3}, city_stats={}, nation_stats={})
    cmp = h.compare(1, 2)
    assert cmp["metric_delta"]["x"] == 2
    assert len(h.replay_window(1, 1)) == 1
