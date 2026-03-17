from fastapi.testclient import TestClient

from services.naming.app import main as naming_main
from services.naming.app.main import app
from shared.config.settings import settings


def test_contextual_name_caching(monkeypatch):
    calls = {"n": 0}

    async def fake_generate(*, base_url, model, prompt, timeout, retries):
        calls["n"] += 1
        return '{"name":"Port Meridian","origin_note":"trade league memory","style_signature":"islander"}'

    monkeypatch.setattr(naming_main, "generate_structured", fake_generate)
    c = TestClient(app)
    payload = {
        "entity_id": "city-1",
        "role": "city",
        "culture_id": "islander",
        "geography": "coast",
        "historical_influences": ["port cities"],
        "tone": "civic",
    }
    r1 = c.post('/names/generate', json=payload)
    r2 = c.post('/names/generate', json=payload)
    assert r1.status_code == 200 and r2.status_code == 200
    assert r1.json()["name"] == r2.json()["name"]
    assert calls["n"] == 1


def test_different_cultures_produce_different_prompts(monkeypatch):
    seen = []

    async def fake_generate(*, base_url, model, prompt, timeout, retries):
        seen.append(prompt)
        return '{"items":[{"name":"A","culture":"northern"}]}'

    monkeypatch.setattr(naming_main, "generate_structured", fake_generate)
    c = TestClient(app)
    c.post('/names/cities', json={'culture': 'northern', 'count': 1})
    c.post('/names/cities', json={'culture': 'desert', 'count': 1})
    assert any("culture_id=northern" in p for p in seen)
    assert any("culture_id=desert" in p for p in seen)


def test_model_role_assignment_for_naming_vs_people(monkeypatch):
    models = []

    async def fake_generate(*, base_url, model, prompt, timeout, retries):
        models.append(model)
        if "description" in prompt.lower():
            return '{"description":"desc","perspective":"public","confidence":"high"}'
        return '{"name":"Iron Compact","origin_note":"legacy","style_signature":"frontier"}'

    monkeypatch.setattr(naming_main, "generate_structured", fake_generate)
    c = TestClient(app)
    c.post('/names/generate', json={"entity_id": "org-1", "role": "organization", "culture_id": "frontier"})
    c.post('/descriptions/generate', json={"entity_id": "org-1", "role": "organization", "name": "Iron Compact", "culture_id": "frontier"})
    assert settings.ollama_model_naming in models
    assert settings.ollama_model_people in models
    assert settings.ollama_model_gm not in models


def test_extended_naming_roles_supported(monkeypatch):
    async def fake_generate(*, base_url, model, prompt, timeout, retries):
        return "{\"name\":\"Harbor Concord\",\"origin_note\":\"league-era\",\"style_signature\":\"islander\"}"

    monkeypatch.setattr(naming_main, "generate_structured", fake_generate)
    c = TestClient(app)
    for role in ["embassy", "treaty", "conference", "summit", "institution", "newspaper", "alliance"]:
        r = c.post('/names/generate', json={"entity_id": f"{role}-1", "role": role, "culture_id": "islander"})
        assert r.status_code == 200
        assert r.json()["name"]


def test_naming_fallback_when_model_unavailable(monkeypatch):
    async def boom(*, base_url, model, prompt, timeout, retries):
        raise RuntimeError("ollama down")

    monkeypatch.setattr(naming_main, "generate_structured", boom)
    c = TestClient(app)
    r = c.post('/names/generate', json={"entity_id": "city-x", "role": "city", "culture_id": "industrial", "refresh": True})
    assert r.status_code == 200
    assert r.json()["name"]

