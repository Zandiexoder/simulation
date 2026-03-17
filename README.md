# Society Simulation Platform (Phase 3)

Microkernel-style civilization-scale simulation with deterministic kernel ticks, strict epistemic separation, scheduler mediation, and strategic operations UI.

## Architecture layers
- Simulation kernel (`sim/kernel`)
- Agent cognition (`sim/agents`) - algorithmic only
- Migration (`sim/migration`)
- Urban development (`sim/urban`)
- Politics/governance (`sim/politics`)
- Intelligence and fog of war (`sim/intelligence`)
- Conflict/security (`sim/conflict`)
- History/replay (`sim/history`)
- Scheduler (`sim/scheduler`)
- API orchestration (`services/api`)
- Naming service (`services/naming`)
- GM gateway (`services/gm-gateway`)
- Frontend strategic console (`services/frontend`)

## Model roles (remote Ollama)
- `OLLAMA_MODEL_NAMING`
- `OLLAMA_MODEL_PEOPLE`
- `OLLAMA_MODEL_GM`


Canonical defaults:
- `OLLAMA_MODEL_NAMING=qwen3.5:0.8b`
- `OLLAMA_MODEL_PEOPLE=qwen3.5:4b`
- `OLLAMA_MODEL_GM=qwen3.5:9b`

Optional high-end GM override:
- `OLLAMA_MODEL_GM=qwen3.5:27b`

## Setup
```bash
./scripts/setup.sh
```

`setup.sh` provisions `.env` defaults (Qwen 3.5 role matrix), validates required keys, checks Ollama connectivity/model availability, and suggests pull commands when models are missing.

Suggested pulls:
- `ollama pull qwen3.5:0.8b`
- `ollama pull qwen3.5:4b`
- `ollama pull qwen3.5:9b`

## Run
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r services/api/requirements.txt -r services/gm-gateway/requirements.txt -r services/naming/requirements.txt
./scripts/run_local.sh
# or docker compose up --build
```

## Key endpoints
- `POST /simulation/start|pause|speed|step|replay-mode`
- `GET /simulation/state`
- `GET /world/map|nations|cities|agents|cultures`
- `GET /events`
- `GET /intel/reports`
- `GET /intel/fog/{nation_id}`
- `GET /history/timeline`
- `GET /history/compare`
- `GET /diplomacy/organizations`
- `GET /media/outlets`
- `GET /media/issues`
- `POST /media/generate`
- `GET /history/media`
- `GET /gm/summary`
- `POST /gm/chat`

- `GET /history/causality/{event_id}`
- `GET /history/milestones`
- `GET /media/narratives/{event_id}`
## Notes
- API does not mutate kernel directly; scheduler mediates stepping.
- UI/inspectors avoid hidden private state unless debug mode is explicitly enabled.


Additional endpoints:
- `POST /names/generate` (naming service)
- `POST /descriptions/generate` (naming service, people model)
- `GET /cache/context/{entity_id}` (naming context cache)
- `GET /descriptions/{entity_type}/{entity_id}` (API)


## Phase 5 operator readiness
- Diagnostics endpoints: `/diagnostics/health`, `/diagnostics/performance`, `/diagnostics/caches`, `/diagnostics/run`
- Scenario endpoints: `/scenarios`, `/scenarios/load`
- Tuning endpoints: `/tuning` (GET/POST)
- Snapshot/replay endpoints: `/snapshots`, `/snapshots/save`, `/snapshots/load`, `/replay/status`
- Repro/compare helpers: `/runs/compare`, `/preflight`
- Description scheduler: `/descriptions/queue`, `/descriptions/process`, `/descriptions/status`

Pre-testing scripts:
- `scripts/preflight.sh`
- `scripts/smoke_run.sh`
- `scripts/benchmark_tick.sh`


## Final testing and benchmarking
Run full regression suite:
```bash
./scripts/test_all.sh
```

Run scenario sweep (requires running API):
```bash
./scripts/run_scenario_matrix.sh http://localhost:8000 5
```

Run tuning sweep:
```bash
./scripts/run_tuning_matrix.sh http://localhost:8000
```

Run benchmark pass:
```bash
./scripts/run_benchmarks.sh http://localhost:8000 30
```

Run soak validation:
```bash
./scripts/run_soak.sh http://localhost:8000 100 20
```

Generate readiness summary from collected artifacts:
```bash
./scripts/generate_readiness_report.sh reports
```

Deterministic guarantee:
- Runs are reproducible within tolerance for the same seed/scenario/tuning fingerprint.
- External AI service variability may affect enrichment text and latency, but simulation core progression remains seed/config-driven.

Artifacts:
- Scripts emit JSON/MD artifacts under timestamped `reports/<stamp>/` folders for operator review.
