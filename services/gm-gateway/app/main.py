from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

from shared.clients.ollama import generate_structured
from shared.config.settings import settings

app = FastAPI(title="gm-gateway", version="0.3.0")


class GMChatPayload(BaseModel):
    prompt: str
    mode: str = "public"
    tick: int
    public_events: list[dict[str, Any]] = []
    intel_reports: list[dict[str, Any]] = []
    model_role: str = "gm"


class GMSummaryPayload(BaseModel):
    tick: int
    events: list[dict[str, Any]] = []
    metrics: dict[str, float] = {}
    model_role: str = "gm"


def _resolve_model(role: str) -> str:
    if role == "people":
        return settings.ollama_model_people
    if role == "naming":
        return settings.ollama_model_naming
    return settings.ollama_model_gm


def _system_prompt(mode: str) -> str:
    if mode == "admin":
        return "You are in admin/debug mode; separate observations, inference, and unknowns."
    return "You are a simulation GM. Respect epistemic limits and uncertainty."


@app.get('/health')
def health() -> dict:
    return {"status": "ok"}


@app.post("/gm/chat")
async def gm_chat(req: GMChatPayload) -> dict[str, Any]:
    prompt = (
        f"{_system_prompt(req.mode)}\nTick: {req.tick}\n"
        f"Public events: {req.public_events}\nIntel reports: {req.intel_reports}\n"
        f"User prompt: {req.prompt}\nReturn concise JSON string response."
    )
    text = await generate_structured(
        base_url=settings.ollama_base_url,
        model=_resolve_model(req.model_role),
        prompt=prompt,
        timeout=settings.ollama_timeout,
        retries=settings.ollama_retries,
    )
    return {"message": text, "perspective": req.mode, "uncertainty_notes": ["Generated from non-omniscient context."], "interventions": []}


@app.post("/gm/summary")
async def gm_summary(req: GMSummaryPayload) -> dict[str, Any]:
    prompt = f"{_system_prompt('public')}\nTick {req.tick}\nEvents: {req.events}\nMetrics:{req.metrics}\nProvide uncertainty-aware briefing."
    text = await generate_structured(
        base_url=settings.ollama_base_url,
        model=_resolve_model(req.model_role),
        prompt=prompt,
        timeout=settings.ollama_timeout,
        retries=settings.ollama_retries,
    )
    return {"summary": text, "tick": req.tick}
