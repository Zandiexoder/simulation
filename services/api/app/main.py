from dataclasses import asdict
import hashlib
import time
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
from sim.scenarios import get_scenario, list_scenarios
from sim.tuning import TuningConfig, tuning_from_dict
from sim.worldgen.generator import generate_world, get_culture_definitions, seed_nations, seed_settlements

app = FastAPI(title="society-sim-api", version="0.4.0")

state = SimulationState(seed=settings.sim_seed)
kernel = SimulationKernel(state)
scheduler = Scheduler(kernel=kernel, state=state, speed=settings.scheduler_default_speed, snapshot_interval=settings.scheduler_snapshot_interval, snapshot_dir=settings.snapshot_dir)


class StepRequest(BaseModel):
    ticks: int = 1


class SpeedRequest(BaseModel):
    speed: int = 1


class ReplayRequest(BaseModel):
    enabled: bool = False


class ChatRequest(BaseModel):
    prompt: str
    mode: str = "public"


class MediaGenerateRequest(BaseModel):
    scope: str = "world"
    trigger: str = "on_demand"


class ScenarioLoadRequest(BaseModel):
    scenario_id: str = "default"


class TuningUpdateRequest(BaseModel):
    config: dict[str, Any]


class SnapshotLoadRequest(BaseModel):
    snapshot_id: str


class DescriptionQueueRequest(BaseModel):
    items: list[dict[str, Any]]


def _fetch_names(path: str, culture: str, count: int) -> list[dict]:
    try:
        with httpx.Client(timeout=settings.ollama_timeout) as client:
            resp = client.post(f"{settings.naming_service_url}{path}", json={"culture": culture, "count": count})
            resp.raise_for_status()
            return resp.json().get("items", [])
    except Exception as exc:
        state.diagnostics.setdefault("warnings", []).append(f"naming_fetch_failed:{exc}")
        return []




def _fetch_cultures() -> list[dict[str, Any]]:
    try:
        with httpx.Client(timeout=settings.ollama_timeout) as client:
            resp = client.get(f"{settings.naming_service_url}/cultures")
            resp.raise_for_status()
            return resp.json().get("items", [])
    except Exception:
        return get_culture_definitions()


def _name_entity(*, entity_id: str, role: str, culture_id: str, geography: str, tone: str, purpose: str, participants: list[str] | None = None) -> dict[str, Any]:
    payload = {
        "entity_id": entity_id,
        "role": role,
        "culture_id": culture_id,
        "geography": geography,
        "tone": tone,
        "historical_influences": [e.get("type", "event") for e in state.events[-6:]],
        "participants": participants or [],
        "purpose": purpose,
    }
    try:
        with httpx.Client(timeout=settings.ollama_timeout) as client:
            resp = client.post(f"{settings.naming_service_url}/names/generate", json=payload)
            resp.raise_for_status()
            state.diagnostics.setdefault("counters", {})["naming_generation_load"] = state.diagnostics.setdefault("counters", {}).get("naming_generation_load", 0) + 1
            return resp.json()
    except Exception as exc:
        state.diagnostics.setdefault("warnings", []).append(f"name_entity_degraded:{exc}")
        return {"name": f"{role.title()} {entity_id}", "origin_note": "degraded", "degraded_reason": "naming_service_unavailable"}


def _describe_entity(*, entity_id: str, role: str, name: str, culture_id: str, conditions: list[str], history: list[str]) -> dict[str, Any]:
    payload = {
        "entity_id": entity_id,
        "role": role,
        "name": name,
        "culture_id": culture_id,
        "current_conditions": conditions,
        "historical_context": history,
    }
    try:
        with httpx.Client(timeout=settings.ollama_timeout) as client:
            resp = client.post(f"{settings.naming_service_url}/descriptions/generate", json=payload)
            resp.raise_for_status()
            return resp.json()
    except Exception as exc:
        state.diagnostics.setdefault("warnings", []).append(f"description_degraded:{exc}")
        return {"description": f"{name}: description unavailable in degraded mode.", "confidence": "low", "degraded_reason": "people_model_unavailable"}

def _diag_trim_warnings() -> None:
    warnings = state.diagnostics.setdefault("warnings", [])
    keep = settings.diagnostics_warning_retention
    if len(warnings) > keep:
        state.diagnostics["warnings"] = warnings[-keep:]


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


def bootstrap(scenario_id: str | None = None) -> None:
    scenario = get_scenario(scenario_id or settings.scenario_default)
    state.scenario_name = scenario.scenario_id
    state.seed = scenario.seed
    state.tuning = tuning_from_dict(scenario.module_tunables or {})
    state.run_metadata = {"seed": state.seed, "scenario": state.scenario_name, "started_at": time.time(), "history_event_retention": settings.history_event_retention}
    cfg_fingerprint = hashlib.sha256(str({"seed": state.seed, "scenario": state.scenario_name, "tuning": state.tuning.as_dict()}).encode()).hexdigest()[:16]
    state.run_metadata["config_fingerprint"] = cfg_fingerprint
    world = generate_world(seed=scenario.seed, width=scenario.world_width, height=scenario.world_height)
    state.world_map = {"width": world.width, "height": world.height, "cells": [asdict(c) for c in world.cells]}
    state.narratives["cultures"] = _fetch_cultures()
    state.cities = seed_settlements(world)
    state.nations = seed_nations()

    for city in state.cities:
        state.urban.register_city(city["id"], city.get("population", 0))

    for nation in state.nations:
        state.politics.register(nation["id"])
        state.conflict.register_nation(nation["id"])

    for city in state.cities:
        named = _name_entity(
            entity_id=city["id"],
            role="city",
            culture_id=city.get("culture", "industrial"),
            geography=f"x={city['x']},y={city['y']}",
            tone="civic",
            purpose="settlement identity",
        )
        city["name"] = named.get("name", city["name"])
        city["name_origin"] = named.get("origin_note", "")

    for nation in state.nations:
        named = _name_entity(
            entity_id=nation["id"],
            role="nation",
            culture_id=nation.get("culture", "industrial"),
            geography="regional",
            tone="formal",
            purpose="state identity",
        )
        nation["name"] = named.get("name", nation["name"])
        nation["name_origin"] = named.get("origin_note", "")

    state.agents = [{"id": f"agent-{i}", "name": f"Agent {i}", "tier": 1 if i % 12 else 2, "city_id": state.cities[i % len(state.cities)]["id"]} for i in range(256)]
    culture_to_agents: dict[str, list[dict]] = {}
    for agent in state.agents:
        culture_to_agents.setdefault(_culture_of_city(agent["city_id"]), []).append(agent)

    for culture, agents in culture_to_agents.items():
        names = _fetch_names("/names/people", culture, len(agents))
        for idx, agent in enumerate(agents):
            agent["culture"] = culture
            if idx < len(names):
                agent["name"] = f"{names[idx]['given_name']} {names[idx]['family_name']}"
                agent["name_origin"] = names[idx].get("origin_note", "")

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


bootstrap(settings.scenario_default)


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
        "models": {"naming": settings.ollama_model_naming, "people": settings.ollama_model_people, "gm": settings.ollama_model_gm},
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
        "run_metadata": state.run_metadata,
        "scenario": state.scenario_name,
        "overlay_summary": {
            "migration": int(state.metrics.get("migration_events", 0)),
            "conflict": int(state.metrics.get("conflict_incidents", 0)),
            "intel": int(state.metrics.get("intel_reports", 0)),
            "organizations": int(state.metrics.get("international_orgs", 0)),
            "news": int(state.metrics.get("media_issues", 0)),
        },
    }


@app.get("/world/cultures")
def world_cultures() -> dict[str, Any]:
    return {"items": state.narratives.get("cultures", [])}


@app.get("/world/overview")
def world_overview() -> dict[str, Any]:
    return {"tick": state.tick, "nations": len(state.nations), "cities": len(state.cities), "agents": len(state.agents), "events": len(state.events), "scenario": state.scenario_name}


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


@app.get("/diplomacy/organizations")
def diplomacy_organizations() -> list[dict]:
    out: list[dict] = []
    for o in state.international.organizations.values():
        row = asdict(o)
        if row.get("name", "").startswith("General Diplomatic") or row.get("name", "").startswith("Collective Security"):
            named = _name_entity(
                entity_id=row["org_id"],
                role="organization",
                culture_id=(state.nations[0].get("culture", "industrial") if state.nations else "industrial"),
                geography="multilateral",
                tone="bureaucratic",
                purpose=row.get("org_type", "institution"),
                participants=row.get("members", []),
            )
            row["name"] = named.get("name", row["name"])
        out.append(row)
    return out


@app.get("/diplomacy/organizations/{org_id}")
def diplomacy_organization(org_id: str) -> dict[str, Any]:
    org = state.international.organizations.get(org_id)
    return asdict(org) if org else {"error": "not found"}


@app.get("/media/outlets")
def media_outlets() -> list[dict]:
    out: list[dict] = []
    for outlet in state.media.outlets.values():
        row = asdict(outlet)
        if row["name"] in {"Global Dispatch"} or row["name"].endswith("Herald"):
            nation = next((n for n in state.nations if n["id"] == row["nation_alignment"]), None)
            culture = nation.get("culture", "industrial") if nation else "industrial"
            named = _name_entity(
                entity_id=row["outlet_id"],
                role="media",
                culture_id=culture,
                geography=row["nation_alignment"],
                tone="journalistic",
                purpose=f"{row['ideological_slant']} media",
            )
            row["name"] = named.get("name", row["name"])
        out.append(row)
    return out


@app.get("/media/issues")
def media_issues(limit: int = 100) -> list[dict]:
    return state.history.recent_media_issues(limit)


@app.post("/media/generate")
async def media_generate(req: MediaGenerateRequest) -> dict[str, Any]:
    issues = state.media.tick(tick=state.tick, visible_events=state.events, nations=state.nations, force_trigger=True)
    created = []
    for issue in issues:
        issue_dict = asdict(issue)
        # try to enrich prose using people-model via GM gateway
        try:
            prompt = f"Generate concise newspaper prose for outlet {issue_dict['outlet_id']} with headlines {issue_dict['headlines']} as JSON with top_stories text."
            payload = {"prompt": prompt, "mode": "public", "tick": state.tick, "public_events": state.events[-8:], "intel_reports": [], "model_role": "people"}
            async with httpx.AsyncClient(timeout=settings.ollama_timeout) as client:
                resp = await client.post(f"{settings.gm_gateway_url}/gm/chat", json=payload)
                resp.raise_for_status()
                issue_dict["ai_enrichment"] = resp.json().get("message", "")
        except Exception:
            issue_dict["ai_enrichment"] = "People model unavailable; local framing used."
        state.history.add_media_issue(issue_dict)
        created.append(issue_dict)
    return {"generated": len(created), "issues": created}


@app.get("/history/timeline")
def history_timeline(start_tick: int = Query(0), end_tick: int = Query(999999)) -> list[dict]:
    return state.history.replay_window(start_tick, end_tick)


@app.get("/history/compare")
def history_compare(tick_a: int, tick_b: int) -> dict:
    return state.history.compare(tick_a, tick_b)


@app.get("/history/media")
def history_media(limit: int = 100) -> list[dict]:
    return state.history.recent_media_issues(limit)




@app.get("/history/causality/{event_id}")
def history_causality(event_id: str) -> dict[str, Any]:
    return state.history.causal_for_event(event_id)


@app.get("/history/milestones")
def history_milestones(limit: int = 25) -> list[dict]:
    return state.history.milestones[-limit:]


@app.get("/media/narratives/{event_id}")
def media_narratives(event_id: str) -> dict[str, Any]:
    coverage = []
    for issue in state.history.media_issues[-300:]:
        if issue.get("event_id") == event_id:
            for v in issue.get("narrative_variants", []):
                coverage.append(v)
    # de-duplicate by outlet/headline
    uniq = []
    seen = set()
    for c in coverage:
        k = (c.get("outlet"), c.get("headline"))
        if k in seen:
            continue
        seen.add(k)
        uniq.append(c)
    return {"event_id": event_id, "coverage": uniq}


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


@app.get("/descriptions/{entity_type}/{entity_id}")
def descriptions(entity_type: str, entity_id: str) -> dict[str, Any]:
    if entity_type == "nation":
        ent = next((n for n in state.nations if n["id"] == entity_id), None)
    elif entity_type == "city":
        ent = next((c for c in state.cities if c["id"] == entity_id), None)
    elif entity_type == "agent":
        ent = next((a for a in state.agents if a["id"] == entity_id), None)
    else:
        ent = None
    if not ent:
        return {"error": "not found"}
    role = "person" if entity_type == "agent" else entity_type
    cache = state.narratives.setdefault("description_cache", {})
    cache_key = f"{role}:{entity_id}"
    if cache_key in cache:
        desc = cache[cache_key]
    else:
        desc = _describe_entity(
            entity_id=entity_id,
            role=role,
            name=ent.get("name", entity_id),
            culture_id=ent.get("culture", "industrial"),
            conditions=[f"tick={state.tick}", f"stability={ent.get('stability', 'n/a')}"] if entity_type == "nation" else [f"tick={state.tick}"],
            history=[e.get("type", "event") for e in state.events[-8:]],
        )
        cache[cache_key] = desc
    return {**desc, "entity": ent}




@app.get("/diagnostics/health")
def diagnostics_health() -> dict[str, Any]:
    _diag_trim_warnings()
    return {
        "tick": state.tick,
        "scenario": state.scenario_name,
        "services": {
            "api": "ok",
            "naming": _service_health(f"{settings.naming_service_url}/health"),
            "gm": _service_health(f"{settings.gm_gateway_url}/health"),
        },
        "models": {"naming": settings.ollama_model_naming, "people": settings.ollama_model_people, "gm": settings.ollama_model_gm},
        "degraded_reasons": state.diagnostics.get("warnings", [])[-20:],
    }


@app.get("/diagnostics/performance")
def diagnostics_performance() -> dict[str, Any]:
    perf = state.diagnostics.get("perf", {})
    counters = state.diagnostics.get("counters", {})
    return {
        "tick": state.tick,
        "tick_duration_s": perf.get("last_tick_duration_s", 0.0),
        "module_timings_s": perf.get("module_timings_s", {}),
        "counters": counters,
        "queue_lengths": {
            "description_queue": len(state.narratives.get("description_queue", [])),
            "naming_requests": state.diagnostics.get("counters", {}).get("naming_generation_load", 0),
            "gm_requests": state.diagnostics.get("counters", {}).get("gm_request_count", 0),
        },
    }


@app.get("/diagnostics/caches")
def diagnostics_caches() -> dict[str, Any]:
    return {
        "description_cache_size": len(state.narratives.get("description_cache", {})),
        "causal_index_size": len(state.history.causal_index),
        "media_archive_size": len(state.history.media_issues),
        "snapshot_count": len(scheduler.list_snapshots()),
    }


@app.get("/diagnostics/run")
def diagnostics_run() -> dict[str, Any]:
    return {
        "metadata": state.run_metadata,
        "scenario": state.scenario_name,
        "tuning": state.tuning.as_dict(),
        "replay_mode": scheduler.replay_mode,
        "last_snapshot": scheduler.list_snapshots()[-1] if scheduler.list_snapshots() else None,
    }


@app.get("/scenarios")
def scenarios() -> list[dict[str, Any]]:
    return list_scenarios()


@app.post("/scenarios/load")
def scenarios_load(req: ScenarioLoadRequest) -> dict[str, Any]:
    scheduler.pause()
    # reset lightweight runtime state and bootstrap with scenario
    state.events.clear()
    state.history.events.clear()
    state.history.media_issues.clear()
    state.history.causal_index.clear()
    state.history.milestones.clear()
    state.narratives.setdefault("description_cache", {}).clear()
    state.narratives.setdefault("description_queue", []).clear()
    bootstrap(req.scenario_id)
    return {"loaded": state.scenario_name, "seed": state.seed}


@app.get("/tuning")
def tuning_get() -> dict[str, Any]:
    return state.tuning.as_dict()


@app.post("/tuning")
def tuning_update(req: TuningUpdateRequest) -> dict[str, Any]:
    state.tuning = tuning_from_dict(req.config)
    state.media.issue_interval = state.tuning.media.issue_interval
    state.international.org_formation_threshold = state.tuning.international.org_formation_threshold
    state.international.deadlock_band_low = state.tuning.international.deadlock_band_low
    state.international.deadlock_band_high = state.tuning.international.deadlock_band_high
    state.run_metadata["history_event_retention"] = settings.history_event_retention
    return {"updated": True, "tuning": state.tuning.as_dict()}


@app.get("/snapshots")
def snapshots_list() -> list[dict[str, Any]]:
    return scheduler.list_snapshots()


@app.post("/snapshots/save")
def snapshots_save() -> dict[str, Any]:
    return scheduler.save_snapshot()


@app.post("/snapshots/load")
def snapshots_load(req: SnapshotLoadRequest) -> dict[str, Any]:
    return scheduler.load_snapshot(req.snapshot_id)


@app.get("/replay/status")
def replay_status() -> dict[str, Any]:
    return {"replay_mode": scheduler.replay_mode, "tick": state.tick, "snapshot_count": len(scheduler.list_snapshots())}


@app.post("/descriptions/queue")
def descriptions_queue(req: DescriptionQueueRequest) -> dict[str, Any]:
    q = state.narratives.setdefault("description_queue", [])
    q.extend(req.items)
    return {"queued": len(req.items), "queue_length": len(q)}


@app.post("/descriptions/process")
def descriptions_process(limit: int = 16) -> dict[str, Any]:
    q = state.narratives.setdefault("description_queue", [])
    cache = state.narratives.setdefault("description_cache", {})
    processed = 0
    while q and processed < limit:
        item = q.pop(0)
        key = f"{item.get('role','entity')}:{item.get('entity_id','unknown')}"
        if key in cache:
            processed += 1
            continue
        res = _describe_entity(
            entity_id=item.get("entity_id", "unknown"),
            role=item.get("role", "entity"),
            name=item.get("name", item.get("entity_id", "unknown")),
            culture_id=item.get("culture_id", "industrial"),
            conditions=item.get("current_conditions", [f"tick={state.tick}"]),
            history=[e.get("type", "event") for e in state.events[-8:]],
        )
        cache[key] = res
        processed += 1
    state.diagnostics.setdefault("counters", {})["description_generation_load"] = processed
    return {"processed": processed, "queue_length": len(q), "cache_size": len(cache)}


@app.get("/descriptions/status")
def descriptions_status() -> dict[str, Any]:
    return {
        "queue_length": len(state.narratives.get("description_queue", [])),
        "cache_size": len(state.narratives.get("description_cache", {})),
        "last_processed": state.diagnostics.get("counters", {}).get("description_generation_load", 0),
    }




@app.get("/runs/compare")
def runs_compare(tick_a: int, tick_b: int) -> dict[str, Any]:
    comp = state.history.compare(tick_a, tick_b)
    comp["run_metadata"] = state.run_metadata
    return comp


@app.get("/preflight")
def preflight() -> dict[str, Any]:
    return {
        "services": {
            "naming": _service_health(f"{settings.naming_service_url}/health"),
            "gm": _service_health(f"{settings.gm_gateway_url}/health"),
        },
        "models": {
            "naming": settings.ollama_model_naming,
            "people": settings.ollama_model_people,
            "gm": settings.ollama_model_gm,
        },
        "snapshot_dir": scheduler.snapshot_dir,
        "scenario": state.scenario_name,
    }


@app.post("/gm/chat")
async def gm_chat(req: ChatRequest) -> dict[str, Any]:
    payload = {"prompt": req.prompt, "mode": req.mode, "tick": state.tick, "public_events": state.events[-5:], "intel_reports": state.intelligence_reports[-5:], "causal_chains": [state.history.causal_for_event(e.get("id", "")) for e in state.events[-5:]], "model_role": "gm"}
    try:
        state.diagnostics.setdefault("counters", {})["gm_request_count"] = state.diagnostics.setdefault("counters", {}).get("gm_request_count", 0) + 1
        async with httpx.AsyncClient(timeout=settings.ollama_timeout) as client:
            resp = await client.post(f"{settings.gm_gateway_url}/gm/chat", json=payload)
            resp.raise_for_status()
            return resp.json()
    except Exception:
        return {
            "message": "GM unavailable",
            "summary": "",
            "historical_analogies": [],
            "risk_assessment": [],
            "uncertainties": ["Using local degraded fallback."],
            "possible_trajectories": [],
            "causal_summary": "",
            "uncertainty_notes": ["Using local degraded fallback."],
            "interventions": [],
        }


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
