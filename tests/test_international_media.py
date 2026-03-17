from sim.international import InternationalSystem
from sim.media import MediaOutlet, MediaSystem


def test_emergent_organization_founding_conditions():
    system = InternationalSystem()
    nations = [{"id": "n1"}, {"id": "n2"}, {"id": "n3"}, {"id": "n4"}]
    events = system.tick(
        tick=5,
        nations=nations,
        crisis_signal={
            "diplomatic_summits": 0.9,
            "interstate_wars": 0.7,
            "refugee_crises": 0.8,
            "sanctions_coordination": 0.6,
            "trade_interdependence": 0.7,
            "great_power_rivalry": 0.2,
            "crisis_load": 0.4,
        },
    )
    assert len(system.organizations) >= 1
    assert any(e["type"] == "org_founded" for e in events)


def test_organization_join_leave_and_effectiveness_erosion():
    system = InternationalSystem()
    nations = [{"id": "n1"}, {"id": "n2"}, {"id": "n3"}, {"id": "n4"}, {"id": "n5"}]
    system.tick(
        tick=1,
        nations=nations,
        crisis_signal={
            "diplomatic_summits": 1.0,
            "interstate_wars": 0.7,
            "refugee_crises": 0.8,
            "sanctions_coordination": 0.7,
            "trade_interdependence": 0.8,
            "great_power_rivalry": 0.1,
            "crisis_load": 0.4,
        },
    )
    org = next(iter(system.organizations.values()))
    baseline_members = len(org.members)

    system.tick(
        tick=2,
        nations=nations,
        crisis_signal={
            "diplomatic_summits": 0.9,
            "interstate_wars": 0.4,
            "refugee_crises": 0.3,
            "sanctions_coordination": 0.4,
            "trade_interdependence": 0.9,
            "great_power_rivalry": 0.2,
            "crisis_load": 0.2,
        },
    )
    org2 = system.organizations[org.org_id]
    assert len(org2.members) >= baseline_members

    for _ in range(10):
        system.tick(
            tick=20,
            nations=nations,
            crisis_signal={
                "diplomatic_summits": 0.1,
                "interstate_wars": 0.1,
                "refugee_crises": 0.1,
                "sanctions_coordination": 0.1,
                "trade_interdependence": 0.1,
                "great_power_rivalry": 1.0,
                "crisis_load": 1.0,
            },
        )
    assert org2.institutional_effectiveness <= 1.0


def test_media_generation_trigger_and_framing_difference():
    media = MediaSystem(issue_interval=3)
    nations = [{"id": "n1", "name": "Nation One", "stability": 0.7}]
    media.ensure_default_outlets(nations)
    # add two custom outlets with distinct framing
    media.outlets["ind"] = MediaOutlet("ind", "Independent Wire", "n1", "centrist", False, 0.8, 0.6, 0.2, 0.2)
    media.outlets["state"] = MediaOutlet("state", "State Voice", "n1", "state", True, 0.5, 0.8, 0.8, 0.4)

    issues = media.tick(
        tick=3,
        visible_events=[{"tick": 3, "type": "security_incident", "message": "Border clash erupted."}],
        nations=nations,
    )
    assert issues
    ind_issue = next(i for i in issues if i.outlet_id == "ind")
    state_issue = next(i for i in issues if i.outlet_id == "state")
    assert ind_issue.top_stories[0]["story"] != state_issue.top_stories[0]["story"]
    assert "Hidden" not in ind_issue.top_stories[0]["story"]
