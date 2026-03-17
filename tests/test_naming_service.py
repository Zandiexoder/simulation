from fastapi.testclient import TestClient

from services.naming.app.main import app


def test_people_name_schema_and_batching():
    c = TestClient(app)
    r = c.post('/names/people', json={'culture': 'northern', 'count': 40})
    assert r.status_code == 200
    items = r.json()['items']
    assert len(items) == 40
    assert {'given_name', 'family_name', 'culture', 'gender_style'} <= set(items[0].keys())


def test_city_names_schema():
    c = TestClient(app)
    r = c.post('/names/cities', json={'culture': 'eastern', 'count': 12})
    assert r.status_code == 200
    items = r.json()['items']
    assert len(items) == 12
    assert {'name', 'culture'} <= set(items[0].keys())


def test_naming_batch_cache_reduces_calls(monkeypatch):
    from services.naming.app import main as naming_main
    calls = {"n": 0}

    async def fake_generate(*, base_url, model, prompt, timeout, retries):
        calls["n"] += 1
        items = [{"given_name": "Aren", "family_name": "Velk", "culture": "northern", "gender_style": "neutral"} for _ in range(64)]
        import json
        return json.dumps({"items": items})

    monkeypatch.setattr(naming_main, "generate_structured", fake_generate)
    c = TestClient(app)
    r1 = c.post('/names/people', json={'culture': 'northern', 'count': 1})
    r2 = c.post('/names/people', json={'culture': 'northern', 'count': 1})
    assert r1.status_code == 200 and r2.status_code == 200
    assert calls["n"] <= 1
