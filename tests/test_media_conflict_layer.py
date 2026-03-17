from sim.media import MediaOutlet, MediaSystem


def test_media_narrative_conflict_variants_link_event():
    media = MediaSystem(issue_interval=1)
    nations = [{"id": "n1", "stability": 0.4, "name": "N1"}]
    media.ensure_default_outlets(nations)
    media.outlets["ind"] = MediaOutlet("ind", "Independent Wire", "n1", "centrist", False, 0.85, 0.6, 0.1, 0.2)
    media.outlets["state"] = MediaOutlet("state", "State Voice", "n1", "state", True, 0.55, 0.8, 0.8, 0.4)

    events = [{"id": "evt-1", "tick": 2, "type": "security_incident", "message": "Border clash erupted."}]
    issues = media.tick(tick=2, visible_events=events, nations=nations, force_trigger=True)
    assert issues
    assert all(i.event_id == "evt-1" for i in issues)
    sample = issues[0]
    assert sample.narrative_variants
    biases = {v["bias"] for v in sample.narrative_variants}
    assert len(biases) >= 2
