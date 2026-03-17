from __future__ import annotations

import json
import random
from dataclasses import dataclass
from hashlib import sha1
from typing import Any, Literal

from fastapi import FastAPI
from pydantic import BaseModel, Field

from shared.clients.ollama import generate_structured
from shared.config.settings import settings
from sim.worldgen.generator import CULTURE_DEFINITIONS, get_culture_definitions

app = FastAPI(title="naming-service", version="0.3.0")


Culture = Literal["northern", "eastern", "desert", "islander", "industrial", "frontier"]
Role = Literal["person", "city", "nation", "organization", "institution", "media", "newspaper", "embassy", "alliance", "treaty", "conference", "summit", "event", "faction"]


class NameRequest(BaseModel):
    culture: Culture = "northern"
    count: int = Field(default=10, ge=1, le=5000)


class NameContextRequest(BaseModel):
    entity_id: str
    role: Role
    culture_id: str = "industrial"
    geography: str = "unknown"
    tone: str = "formal"
    historical_influences: list[str] = Field(default_factory=list)
    participants: list[str] = Field(default_factory=list)
    purpose: str = "general"
    refresh: bool = False


class DescriptionRequest(BaseModel):
    entity_id: str
    role: Role
    name: str
    culture_id: str = "industrial"
    current_conditions: list[str] = Field(default_factory=list)
    historical_context: list[str] = Field(default_factory=list)
    refresh: bool = False


class PersonName(BaseModel):
    given_name: str
    family_name: str
    culture: str
    gender_style: str = "neutral"
    origin_note: str = ""


class EntityName(BaseModel):
    name: str
    culture: str


@dataclass(slots=True)
class CacheBucket:
    people: list[PersonName]
    cities: list[EntityName]
    nations: list[EntityName]
    factions: list[EntityName]


CACHE: dict[str, CacheBucket] = {
    c: CacheBucket(people=[], cities=[], nations=[], factions=[])
    for c in ["northern", "eastern", "desert", "islander", "industrial", "frontier"]
}
ENTITY_NAME_CACHE: dict[str, dict[str, Any]] = {}
DESCRIPTION_CACHE: dict[str, dict[str, Any]] = {}
NAMING_DIAGNOSTICS: dict[str, Any] = {"request_count": 0, "fallback_count": 0}


def _fallback_token(parts: list[str]) -> str:
    seed = sha1("|".join(parts).encode()).hexdigest()
    alpha = "bcdfghjklmnpqrstvwxyz"
    vowels = "aeiou"
    rng = random.Random(int(seed[:8], 16))
    chunk = "".join(rng.choice(alpha) + rng.choice(vowels) for _ in range(3))
    return chunk.title()


def _culture_prompt(culture_id: str) -> str:
    c = CULTURE_DEFINITIONS.get(culture_id, CULTURE_DEFINITIONS["industrial"])
    return (
        f"culture_id={c.culture_id}; language_style={c.language_style}; "
        f"traits={c.traits}; influences={c.influences}; naming_style={c.naming_style}; "
        f"historical_flavor_tags={c.historical_flavor_tags}"
    )


async def _generate_batch(kind: str, culture: str, count: int) -> list[dict]:
    prompt = (
        "Return strict JSON object with key 'items'. "
        f"Generate {count} {kind} names with culturally cohesive style. "
        f"Context: {_culture_prompt(culture)}. "
        "If people, each item must include given_name,family_name,culture,gender_style,origin_note. "
        "If non-people, each item must include name,culture. No commentary."
    )
    try:
        raw = await generate_structured(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model_naming,
            prompt=prompt,
            timeout=settings.ollama_timeout,
            retries=settings.ollama_retries,
        )
    except Exception:
        raw = "{}"
    try:
        parsed = json.loads(raw)
        items = parsed.get("items", [])
        if isinstance(items, list) and items:
            return items
    except Exception:
        pass

    NAMING_DIAGNOSTICS["fallback_count"] = NAMING_DIAGNOSTICS.get("fallback_count", 0) + count
    out: list[dict] = []
    for i in range(count):
        token = _fallback_token([kind, culture, str(i)])
        if kind == "people":
            out.append({"given_name": token, "family_name": _fallback_token([culture, token]), "culture": culture, "gender_style": "neutral", "origin_note": "fallback"})
        else:
            out.append({"name": f"{token} {_fallback_token([token, 'hold'])}", "culture": culture})
    return out


async def _get_or_generate_people(culture: str, count: int) -> list[PersonName]:
    bucket = CACHE[culture]
    if len(bucket.people) < count:
        items = await _generate_batch("people", culture, max(64, count))
        bucket.people.extend(PersonName.model_validate(i) for i in items)
    take = bucket.people[:count]
    del bucket.people[:count]
    return take


async def _get_or_generate_entities(kind: str, culture: str, count: int) -> list[EntityName]:
    bucket = CACHE[culture]
    store = getattr(bucket, kind)
    if len(store) < count:
        items = await _generate_batch(kind, culture, max(32, count))
        store.extend(EntityName.model_validate(i) for i in items)
    take = store[:count]
    del store[:count]
    return take


async def _generate_contextual_name(req: NameContextRequest) -> dict[str, Any]:
    prompt = (
        "Return strict JSON object with keys name, origin_note, style_signature. "
        f"role={req.role}; tone={req.tone}; geography={req.geography}; purpose={req.purpose}; "
        f"culture_context={_culture_prompt(req.culture_id)}; historical_influences={req.historical_influences}; "
        f"participants={req.participants}. Keep concise and culturally coherent."
    )
    try:
        raw = await generate_structured(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model_naming,
            prompt=prompt,
            timeout=settings.ollama_timeout,
            retries=settings.ollama_retries,
        )
    except Exception:
        raw = "{}"
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict) and parsed.get("name"):
            return parsed
    except Exception:
        pass
    token = _fallback_token([req.entity_id, req.culture_id, req.role])
    return {"name": f"{token} {_fallback_token([req.role, req.tone])}", "origin_note": "fallback placeholder", "style_signature": req.culture_id}


async def _generate_description(req: DescriptionRequest) -> dict[str, Any]:
    prompt = (
        "Return strict JSON object with keys description, perspective, confidence. "
        f"Entity: role={req.role} name={req.name} culture={req.culture_id}. "
        f"Culture context: {_culture_prompt(req.culture_id)}. "
        f"Current conditions={req.current_conditions}; historical_context={req.historical_context}."
    )
    try:
        raw = await generate_structured(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model_people,
            prompt=prompt,
            timeout=settings.ollama_timeout,
            retries=settings.ollama_retries,
        )
    except Exception:
        raw = "{}"
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict) and parsed.get("description"):
            return parsed
    except Exception:
        pass
    return {"description": f"{req.name} is currently in a degraded narrative mode.", "perspective": "fallback", "confidence": "low"}


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "model_naming": settings.ollama_model_naming, "model_people": settings.ollama_model_people}


@app.get("/cultures")
def cultures() -> dict[str, Any]:
    return {"items": get_culture_definitions()}


@app.get("/diagnostics")
def diagnostics() -> dict[str, Any]:
    return {**NAMING_DIAGNOSTICS, "name_cache": len(ENTITY_NAME_CACHE), "description_cache": len(DESCRIPTION_CACHE)}


@app.post("/names/people")
async def names_people(req: NameRequest) -> dict:
    NAMING_DIAGNOSTICS["request_count"] = NAMING_DIAGNOSTICS.get("request_count", 0) + 1
    items = await _get_or_generate_people(req.culture, req.count)
    return {"items": [i.model_dump() for i in items], "model": settings.ollama_model_naming}


@app.post("/names/cities")
async def names_cities(req: NameRequest) -> dict:
    NAMING_DIAGNOSTICS["request_count"] = NAMING_DIAGNOSTICS.get("request_count", 0) + 1
    items = await _get_or_generate_entities("cities", req.culture, req.count)
    return {"items": [i.model_dump() for i in items], "model": settings.ollama_model_naming}


@app.post("/names/nations")
async def names_nations(req: NameRequest) -> dict:
    NAMING_DIAGNOSTICS["request_count"] = NAMING_DIAGNOSTICS.get("request_count", 0) + 1
    items = await _get_or_generate_entities("nations", req.culture, req.count)
    return {"items": [i.model_dump() for i in items], "model": settings.ollama_model_naming}


@app.post("/names/factions")
async def names_factions(req: NameRequest) -> dict:
    NAMING_DIAGNOSTICS["request_count"] = NAMING_DIAGNOSTICS.get("request_count", 0) + 1
    items = await _get_or_generate_entities("factions", req.culture, req.count)
    return {"items": [i.model_dump() for i in items], "model": settings.ollama_model_naming}


@app.post("/names/generate")
async def names_generate(req: NameContextRequest) -> dict[str, Any]:
    NAMING_DIAGNOSTICS["request_count"] = NAMING_DIAGNOSTICS.get("request_count", 0) + 1
    cache_key = f"{req.role}:{req.entity_id}"
    if cache_key in ENTITY_NAME_CACHE and not req.refresh:
        return {**ENTITY_NAME_CACHE[cache_key], "cached": True, "model": settings.ollama_model_naming}
    generated = await _generate_contextual_name(req)
    out = {
        "entity_id": req.entity_id,
        "role": req.role,
        "culture_id": req.culture_id,
        "name": generated.get("name", "Unnamed"),
        "origin_note": generated.get("origin_note", ""),
        "style_signature": generated.get("style_signature", ""),
    }
    ENTITY_NAME_CACHE[cache_key] = out
    return {**out, "cached": False, "model": settings.ollama_model_naming}


@app.post("/descriptions/generate")
async def descriptions_generate(req: DescriptionRequest) -> dict[str, Any]:
    NAMING_DIAGNOSTICS["request_count"] = NAMING_DIAGNOSTICS.get("request_count", 0) + 1
    cache_key = f"{req.role}:{req.entity_id}"
    if cache_key in DESCRIPTION_CACHE and not req.refresh:
        return {**DESCRIPTION_CACHE[cache_key], "cached": True, "model": settings.ollama_model_people}
    generated = await _generate_description(req)
    out = {
        "entity_id": req.entity_id,
        "role": req.role,
        "name": req.name,
        "culture_id": req.culture_id,
        "description": generated.get("description", ""),
        "perspective": generated.get("perspective", "public"),
        "confidence": generated.get("confidence", "medium"),
    }
    DESCRIPTION_CACHE[cache_key] = out
    return {**out, "cached": False, "model": settings.ollama_model_people}


@app.get("/cache/context/{entity_id}")
def naming_context(entity_id: str) -> dict[str, Any]:
    items = [v for k, v in ENTITY_NAME_CACHE.items() if k.endswith(f":{entity_id}")]
    descs = [v for k, v in DESCRIPTION_CACHE.items() if k.endswith(f":{entity_id}")]
    return {"name_entries": items, "description_entries": descs}
