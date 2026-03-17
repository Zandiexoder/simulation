from fastapi.testclient import TestClient

from services.api.app.main import app


def test_orgs_and_media_endpoints_compatibility():
    c = TestClient(app)
    c.post('/simulation/step', json={'ticks': 6})

    orgs = c.get('/diplomacy/organizations').json()
    assert isinstance(orgs, list)

    outlets = c.get('/media/outlets').json()
    issues = c.get('/media/issues').json()
    assert isinstance(outlets, list)
    assert isinstance(issues, list)


def test_media_archive_persistence_and_generation():
    c = TestClient(app)
    before = len(c.get('/history/media').json())
    r = c.post('/media/generate', json={'scope': 'world', 'trigger': 'on_demand'})
    assert r.status_code == 200
    after = len(c.get('/history/media').json())
    assert after >= before
