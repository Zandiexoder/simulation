from dataclasses import asdict
from typing import Any

import httpx
from fastapi import FastAPI, Query
from pydantic import BaseModel

from shared.config.settings import settings
from sim.agents.cognition import DEFAULT_GOALS, default_traits
from sim.economy import Firm
from sim.households import Household
from sim.kernel.pipeline import SimulationKernel
from sim.kernel.state import SimulationState
from sim.scheduler import Scheduler
from sim.worldgen.generator import generate_world, seed_nations, seed_settlements

app = FastAPI(title="society-sim-api", version="0.3.0")

state = SimulationState(seed=settings.sim_seed)
kernel = SimulationKernel(state)
scheduler = Scheduler(kernel=kernel, state=state, speed=settings.scheduler_default_speed, snapshot_interval=settings.scheduler_snapshot_interval)


class StepRequest(BaseModel):
    ticks: int = 1


class SpeedRequest(BaseModel):
    speed: int = 1


class ReplayRequest(BaseModel):
    enabled: bool = False


class ChatRequest(BaseModel):
    prompt: str
    mode: str = "public"


def _fetch_names(path: str, culture: str, count: int) -> list[dict]:
    try:
        with httpx.Client(timeout=settings.ollama_timeout) as client:
            resp = client.post(f"{settings.naming_service_url}{path}", json={"culture": culture, "count": count})
            resp.raise_for_status()
            return resp.json().get("items", [])
    except Exception:
        return []


def _service_health(url: str) -> str:
    try:
        with httpx.Client(timeout=2) as client:
            r = client.get(url)
            return "ok" if r.status_code < 500 else "degraded"
    except Exception:
        return "down"


def _culture_of_city(city_id: str) -> str:
    city = next((c for c in state.cities if c["id"] == city_id), None)
    return city.get("culture", "industrial") if city else "industrial"


def bootstrap() -> None:
    world = generate_world(seed=settings.sim_seed, width=settings.world_width, height=settings.world_height)
    state.world_map = {"width": world.width, "height": world.height, "cells": [asdict(c) for c in world.cells]}
    state.cities = seed_settlements(world)
    state.nations = seed_nations()

    for city in state.cities:
        state.urban.register_city(city["id"], city.get("population", 0))

    for nation in state.nations:
        state.politics.register(nation["id"])
        state.conflict.register_nation(nation["id"])

    for culture in {c["culture"] for c in state.cities}:
        city_candidates = [c for c in state.cities if c["culture"] == culture]
        names = _fetch_names("/names/cities", culture, len(city_candidates))
        for idx, city in enumerate(city_candidates):
            if idx < len(names):
                city["name"] = names[idx]["name"]

    for culture in {n["culture"] for n in state.nations}:
        nation_candidates = [n for n in state.nations if n["culture"] == culture]
        names = _fetch_names("/names/nations", culture, len(nation_candidates))
        for idx, nation in enumerate(nation_candidates):
            if idx < len(names):
                nation["name"] = names[idx]["name"]

    state.agents = [{"id": f"agent-{i}", "name": f"Agent {i}", "tier": 1 if i % 12 else 2, "city_id": state.cities[i % len(state.cities)]["id"]} for i in range(256)]
    culture_to_agents: dict[str, list[dict]] = {}
    for agent in state.agents:
        culture_to_agents.setdefault(_culture_of_city(agent["city_id"]), []).append(agent)

    for culture, agents in culture_to_agents.items():
        names = _fetch_names("/names/people", culture, len(agents))
        for idx, agent in enumerate(agents):
            if idx < len(names):
                agent["name"] = f"{names[idx]['given_name']} {names[idx]['family_name']}"
                agent["culture"] = names[idx]["culture"]
            else:
                agent["culture"] = culture

    for i, agent in enumerate(state.agents):
        aid = agent["id"]
        city = state.cities[i % len(state.cities)]
        state.ecs.identity[aid] = {"name": agent["name"], "class": "person", "culture": agent.get("culture", "industrial")}
        state.ecs.location[aid] = (city["x"], city["y"])
        state.ecs.health[aid] = 1.0
        state.ecs.wealth[aid] = 0.4 + (i % 7) * 0.05
        state.ecs.needs[aid] = {"hunger": 0.3 + (i % 5) * 0.1, "wealth": 0.5}
        state.ecs.traits[aid] = default_traits(state.seed + i)
        state.ecs.goals[aid] = DEFAULT_GOALS.copy()

        hid = f"household-{i // 4}"
        state.ecs.household[aid] = hid
        if hid not in state.households.households:
            state.households.add_household(Household(household_id=hid, members=[], city_id=city["id"], shared_income=0.15, savings=0.2))
        state.households.households[hid].members.append(aid)

        state.social_graph.add_node(aid)
        if i > 0:
            state.social_graph.add_edge(aid, state.agents[i - 1]["id"], "friendship", trust=0.4 + (i % 5) * 0.1)

    for city in state.cities:
        state.economy.register_city(city["id"])
        state.economy.add_firm(Firm(firm_id=f"firm-{city['id']}", city_id=city["id"], sector="general", wage_offer=1.0, productivity=0.9))


bootstrap()


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "tick": state.tick,
        "services": {
            "api": "ok",
            "naming": _service_health(f"{settings.naming_service_url}/health"),
            "gm": _service_health(f"{settings.gm_gateway_url}/health"),
        },
    }


@app.post("/simulation/start")
def simulation_start() -> dict[str, Any]:
    scheduler.start()
    return {"running": state.running, "speed": scheduler.speed}


@app.post("/simulation/pause")
def simulation_pause() -> dict[str, Any]:
    scheduler.pause()
    return {"running": state.running}


@app.post("/simulation/speed")
def simulation_speed(req: SpeedRequest) -> dict[str, Any]:
    scheduler.set_speed(req.speed)
    return {"speed": scheduler.speed}


@app.post("/simulation/replay-mode")
def replay_mode(req: ReplayRequest) -> dict[str, Any]:
    scheduler.set_replay_mode(req.enabled)
    return {"replay_mode": scheduler.replay_mode}


@app.post("/simulation/step")
def simulation_step(req: StepRequest) -> dict[str, Any]:
    scheduler.step(req.ticks)
    return {"tick": state.tick, "metrics": state.metrics}


@app.get("/simulation/state")
def simulation_state() -> dict[str, Any]:
    return {
        "tick": state.tick,
        "running": state.running,
        "replay_mode": scheduler.replay_mode,
        "metrics": state.metrics,
        "snapshots": scheduler.snapshots[-20:],
        "overlay_summary": {
            "migration": int(state.metrics.get("migration_events", 0)),
            "conflict": int(state.metrics.get("conflict_incidents", 0)),
            "intel": int(state.metrics.get("intel_reports", 0)),
        },
    }


@app.get("/world/map")
def world_map() -> dict[str, Any]:
    return state.world_map


@app.get("/world/nations")
def world_nations() -> list[dict]:
    out = []
    for n in state.nations:
        p = state.politics.nations.get(n["id"])
        out.append({
            **n,
            "government_type": p.government_type if p else "unknown",
            "legitimacy": round(p.legitimacy, 3) if p else 0.0,
            "coup_risk_estimate": round(p.coup_risk, 3) if p else 0.0,
            "intel_confidence": state.intelligence.nation_fog.get(n["id"], {}).get("estimated", {}).get("foreign_coup_risk", 0.0),
        })
    return out


@app.get("/world/cities")
def world_cities() -> list[dict]:
    out = []
    for c in state.cities:
        up = state.urban.cities.get(c["id"])
        out.append({
            **c,
            "growth_trend": round(up.growth_trend, 3) if up else 0.0,
            "housing_pressure": round(up.density_pressure, 3) if up else 0.0,
            "crime_pressure": round(up.crime_pressure, 3) if up else 0.0,
        })
    return out


@app.get("/world/agents")
def world_agents(limit: int = 100, admin: bool = False) -> list[dict]:
    rows = []
    for a in state.agents[:limit]:
        row = {"id": a["id"], "name": a.get("name"), "city_id": a.get("city_id"), "culture": a.get("culture"), "tier": a.get("tier")}
        if admin and settings.admin_debug_mode:
            row["private_goals"] = state.ecs.goals.get(a["id"], [])
        rows.append(row)
    return rows


@app.get("/events")
def events(limit: int = 100) -> list[dict]:
    return state.events[-limit:]


@app.get("/intel/reports")
def intel_reports(limit: int = 100) -> list[dict]:
    return [asdict(r) for r in state.intelligence.reports[-limit:]]


@app.get("/intel/fog/{nation_id}")
def intel_fog(nation_id: str) -> dict:
    return state.intelligence.nation_fog.get(nation_id, {"known": {}, "suspected": {}, "estimated": {}, "unknown": []})


@app.get("/history/timeline")
def history_timeline(start_tick: int = Query(0), end_tick: int = Query(999999)) -> list[dict]:
    return state.history.replay_window(start_tick, end_tick)


@app.get("/history/compare")
def history_compare(tick_a: int, tick_b: int) -> dict:
    return state.history.compare(tick_a, tick_b)


@app.get("/narratives/agents/{agent_id}")
async def agent_narrative(agent_id: str) -> dict[str, Any]:
    agent = next((a for a in state.agents if a["id"] == agent_id), None)
    if not agent:
        return {"error": "not found"}
    payload = {"prompt": f"Write a short biography and quote for {agent['name']} from culture {agent.get('culture','industrial')}.", "mode": "public", "tick": state.tick, "public_events": state.events[-5:], "intel_reports": [], "model_role": "people"}
    try:
        async with httpx.AsyncClient(timeout=settings.ollama_timeout) as client:
            resp = await client.post(f"{settings.gm_gateway_url}/gm/chat", json=payload)
            resp.raise_for_status()
            return resp.json()
    except Exception:
        return {"message": "People model unavailable", "uncertainty_notes": ["Narrative degraded mode active."]}


@app.post("/gm/chat")
async def gm_chat(req: ChatRequest) -> dict[str, Any]:
    payload = {"prompt": req.prompt, "mode": req.mode, "tick": state.tick, "public_events": state.events[-5:], "intel_reports": state.intelligence_reports[-5:], "model_role": "gm"}
    try:
        async with httpx.AsyncClient(timeout=settings.ollama_timeout) as client:
            resp = await client.post(f"{settings.gm_gateway_url}/gm/chat", json=payload)
            resp.raise_for_status()
            return resp.json()
    except Exception:
        return {"message": "GM unavailable", "uncertainty_notes": ["Using local degraded fallback."], "interventions": []}


@app.get("/gm/summary")
async def gm_summary() -> dict[str, Any]:
    payload = {"tick": state.tick, "events": state.events[-20:], "metrics": state.metrics, "model_role": "gm"}
    try:
        async with httpx.AsyncClient(timeout=settings.ollama_timeout) as client:
            resp = await client.post(f"{settings.gm_gateway_url}/gm/summary", json=payload)
            resp.raise_for_status()
            return resp.json()
    except Exception:
        return {"summary": "GM unavailable. Fallback: consult events and intel tabs.", "tick": state.tick}
