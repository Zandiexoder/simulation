from sim.causality import CausalitySystem
from sim.emergence import EmergenceSystem


def test_causal_chain_creation_from_prior_signals():
    c = CausalitySystem()
    event = {"id": "e2", "type": "security_incident", "message": "Clashes erupted"}
    recent = [{"id": "e0", "type": "migration"}, {"id": "e1", "type": "coup_risk"}]
    metrics = {"avg_wealth": 0.4, "avg_legitimacy": 0.45, "conflict_incidents": 2}
    d = c.derive(event=event, recent_events=recent, metrics=metrics)
    assert d is not None
    assert d["event_id"] == "e2"
    assert len(d["causal_chain"]) >= 2


def test_emergence_triggers_firsts_and_wave_threshold():
    e = EmergenceSystem()
    out = e.evaluate(
        tick=5,
        events=[{"type": "coup_risk"}, {"type": "security_incident"}],
        org_count=1,
        media_count=1,
        conflict_incidents=1,
        migration_events=10,
    )
    keys = {x["milestone_key"] for x in out}
    assert "first_org" in keys
    assert "first_media" in keys
    assert "major_migration_wave" in keys
    out2 = e.evaluate(tick=6, events=[], org_count=2, media_count=2, conflict_incidents=2, migration_events=12)
    assert out2 == []
