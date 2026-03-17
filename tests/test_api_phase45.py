from fastapi.testclient import TestClient

from services.api.app.main import app


def test_api_causality_and_milestones_endpoints():
    c = TestClient(app)
    c.post('/simulation/step', json={'ticks': 2})
    events = c.get('/events').json()
    assert events
    ev = events[-1]
    causal = c.get(f"/history/causality/{ev['id']}")
    assert causal.status_code == 200
    assert 'causal_chain' in causal.json()

    milestones = c.get('/history/milestones').json()
    assert isinstance(milestones, list)


def test_api_media_narrative_comparison_shape():
    c = TestClient(app)
    c.post('/media/generate', json={'scope': 'world', 'trigger': 'on_demand'})
    issues = c.get('/media/issues').json()
    if not issues:
        return
    event_id = issues[-1].get('event_id', '')
    res = c.get(f'/media/narratives/{event_id}')
    assert res.status_code == 200
    body = res.json()
    assert 'coverage' in body
