from fastapi.testclient import TestClient

from services.api.app.main import app


def test_world_cultures_endpoint():
    c = TestClient(app)
    res = c.get('/world/cultures')
    assert res.status_code == 200
    data = res.json()
    assert data['items']
    assert 'culture_id' in data['items'][0]


def test_descriptions_endpoint_has_fallback_shape():
    c = TestClient(app)
    nations = c.get('/world/nations').json()
    assert nations
    res = c.get(f"/descriptions/nation/{nations[0]['id']}")
    assert res.status_code == 200
    body = res.json()
    assert 'description' in body
    assert 'entity' in body
