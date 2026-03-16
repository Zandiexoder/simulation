from fastapi.testclient import TestClient

from services.api.app.main import app


def test_health():
    c = TestClient(app)
    r = c.get('/health')
    assert r.status_code == 200
    assert r.json()['status'] == 'ok'


def test_step_and_events():
    c = TestClient(app)
    start_tick = c.get('/simulation/state').json()['tick']
    r = c.post('/simulation/step', json={'ticks': 2})
    assert r.status_code == 200
    assert r.json()['tick'] >= start_tick + 2
    events = c.get('/events').json()
    assert len(events) > 0


def test_world_data():
    c = TestClient(app)
    assert c.get('/world/map').status_code == 200
    assert len(c.get('/world/nations').json()) > 0
    assert len(c.get('/world/cities').json()) > 0


def test_agent_naming_integration():
    c = TestClient(app)
    agents = c.get('/world/agents').json()
    assert len(agents) > 0
    assert 'name' in agents[0]
    assert 'culture' in agents[0]
