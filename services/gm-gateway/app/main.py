from __future__ import annotations

import json
import time
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

from shared.clients.ollama import generate_structured
from shared.config.settings import settings

app = FastAPI(title="gm-gateway", version="0.3.0")
GM_DIAGNOSTICS: dict[str, Any] = {"request_count": 0, "last_latency_s": 0.0}


class GMChatPayload(BaseModel):
    prompt: str
    mode: str = "public"
    tick: int
    public_events: list[dict[str, Any]] = []
    intel_reports: list[dict[str, Any]] = []
    causal_chains: list[dict[str, Any]] = []
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
    base = (
        "You are a simulation GM historian/analyst. Respect epistemic limits and uncertainty. "
        "Never claim hidden certainty. Distinguish facts from inference and analogies. "
        "Use only provided public events and intel reports as evidence. "
        "For historical reasoning, provide analogies (not deterministic predictions), explain similarities and differences, "
        "assign confidence levels, and clearly separate observed facts, inference, and analogy."
    )
    if mode == "admin":
        return base + " Admin/debug mode: include explicit unknowns and data quality concerns."
    return base


def _empty_sections() -> dict[str, Any]:
    return {
        "summary": "",
        "historical_analogies": [],
        "risk_assessment": [],
        "uncertainties": [],
        "possible_trajectories": [],
        "causal_summary": "",
    }


def _extract_sections(raw_text: str) -> dict[str, Any]:
    sections = _empty_sections()
    try:
        data = json.loads(raw_text)
        if isinstance(data, dict):
            for key in sections:
                value = data.get(key, sections[key])
                if isinstance(sections[key], list):
                    sections[key] = value if isinstance(value, list) else sections[key]
                elif isinstance(value, str):
                    sections[key] = value
    except Exception:
        pass
    return sections


@app.get('/health')
def health() -> dict:
    return {"status": "ok"}


@app.get("/diagnostics")
def diagnostics() -> dict[str, Any]:
    return GM_DIAGNOSTICS


@app.post("/gm/chat")
async def gm_chat(req: GMChatPayload) -> dict[str, Any]:
    started = time.perf_counter()
    GM_DIAGNOSTICS["request_count"] = GM_DIAGNOSTICS.get("request_count", 0) + 1
    prompt = (
        f"{_system_prompt(req.mode)}\nTick: {req.tick}\n"
        f"Public events: {req.public_events}\nIntel reports: {req.intel_reports}\nCausal chains: {req.causal_chains}\n"
        f"User prompt: {req.prompt}\n"
        "Return JSON with keys: "
        "summary (string), historical_analogies (list of objects with keys: analogy, similarities, differences, confidence), "
        "risk_assessment (list), uncertainties (list), possible_trajectories (list), causal_summary (string). "
        "Do not invent events; base all claims on provided context."
    )
    text = await generate_structured(
        base_url=settings.ollama_base_url,
        model=_resolve_model(req.model_role),
        prompt=prompt,
        timeout=settings.ollama_timeout,
        retries=settings.ollama_retries,
    )
    GM_DIAGNOSTICS["last_latency_s"] = round(time.perf_counter() - started, 6)
    sections = _extract_sections(text)
    message = sections["summary"] if sections["summary"] else text
    return {
        "message": message,
        "summary": sections["summary"],
        "historical_analogies": sections["historical_analogies"],
        "risk_assessment": sections["risk_assessment"],
        "uncertainties": sections["uncertainties"],
        "possible_trajectories": sections["possible_trajectories"],
        "causal_summary": sections.get("causal_summary", ""),
        "perspective": req.mode,
        "uncertainty_notes": ["Generated from non-omniscient context."],
        "interventions": [],
    }


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
