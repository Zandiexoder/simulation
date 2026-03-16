from __future__ import annotations

import json
import random
from dataclasses import dataclass
from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel, Field

from shared.clients.ollama import generate_structured
from shared.config.settings import settings

app = FastAPI(title="naming-service", version="0.2.0")


Culture = Literal["northern", "eastern", "desert", "islander", "industrial", "frontier"]


class NameRequest(BaseModel):
    culture: Culture = "northern"
    count: int = Field(default=10, ge=1, le=5000)


class PersonName(BaseModel):
    given_name: str
    family_name: str
    culture: Culture
    gender_style: str = "neutral"


class EntityName(BaseModel):
    name: str
    culture: Culture


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


async def _generate_batch(kind: str, culture: Culture, count: int) -> list[dict]:
    prompt = (
        "Return strict JSON object with key 'items'. "
        f"Generate {count} {kind} names for culture={culture}. "
        "If people, each item must include given_name,family_name,culture,gender_style. "
        "If non-people, each item must include name,culture."
    )
    raw = await generate_structured(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model_naming,
        prompt=prompt,
        timeout=settings.ollama_timeout,
        retries=settings.ollama_retries,
    )
    try:
        parsed = json.loads(raw)
        items = parsed.get("items", [])
        if isinstance(items, list) and items:
            return items
    except Exception:  # noqa: BLE001
        pass

    # deterministic fallback if remote LLM is unavailable
    rng = random.Random(hash((kind, culture, count)) & 0xFFFF)
    syllables = ["ar", "en", "vel", "tor", "na", "shi", "ka", "dur", "lin", "or"]
    out: list[dict] = []
    for _ in range(count):
        if kind == "people":
            out.append(
                {
                    "given_name": (rng.choice(syllables) + rng.choice(syllables)).title(),
                    "family_name": (rng.choice(syllables) + rng.choice(syllables)).title(),
                    "culture": culture,
                    "gender_style": rng.choice(["masculine", "feminine", "neutral"]),
                }
            )
        else:
            out.append({"name": (rng.choice(syllables) + rng.choice(syllables) + rng.choice(syllables)).title(), "culture": culture})
    return out


async def _get_or_generate_people(culture: Culture, count: int) -> list[PersonName]:
    bucket = CACHE[culture]
    if len(bucket.people) < count:
        items = await _generate_batch("people", culture, max(64, count))
        bucket.people.extend(PersonName.model_validate(i) for i in items)
    take = bucket.people[:count]
    del bucket.people[:count]
    return take


async def _get_or_generate_entities(kind: str, culture: Culture, count: int) -> list[EntityName]:
    bucket = CACHE[culture]
    store = getattr(bucket, kind)
    if len(store) < count:
        items = await _generate_batch(kind, culture, max(32, count))
        store.extend(EntityName.model_validate(i) for i in items)
    take = store[:count]
    del store[:count]
    return take


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/names/people")
async def names_people(req: NameRequest) -> dict:
    items = await _get_or_generate_people(req.culture, req.count)
    return {"items": [i.model_dump() for i in items]}


@app.post("/names/cities")
async def names_cities(req: NameRequest) -> dict:
    items = await _get_or_generate_entities("cities", req.culture, req.count)
    return {"items": [i.model_dump() for i in items]}


@app.post("/names/nations")
async def names_nations(req: NameRequest) -> dict:
    items = await _get_or_generate_entities("nations", req.culture, req.count)
    return {"items": [i.model_dump() for i in items]}


@app.post("/names/factions")
async def names_factions(req: NameRequest) -> dict:
    items = await _get_or_generate_entities("factions", req.culture, req.count)
    return {"items": [i.model_dump() for i in items]}
