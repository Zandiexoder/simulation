from fastapi.testclient import TestClient

from services.api.app.main import app


def test_ui_api_contracts_and_replay():
    c = TestClient(app)
    assert c.post('/simulation/replay-mode', json={'enabled': True}).status_code == 200
    st = c.get('/simulation/state').json()
    assert 'replay_mode' in st
    assert 'overlay_summary' in st


def test_fog_of_war_endpoint_and_agent_privacy():
    c = TestClient(app)
    nations = c.get('/world/nations').json()
    if nations:
        fog = c.get(f"/intel/fog/{nations[0]['id']}").json()
        assert 'unknown' in fog
    agents = c.get('/world/agents').json()
    assert agents
    assert 'private_goals' not in agents[0]


def test_degraded_gm_fallback_behavior():
    c = TestClient(app)
    res = c.post('/gm/chat', json={'prompt': 'status', 'mode': 'public'})
    assert res.status_code == 200
    body = res.json()
    assert 'message' in body
