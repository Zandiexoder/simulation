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

## Run
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r services/api/requirements.txt -r services/gm-gateway/requirements.txt -r services/naming/requirements.txt
./scripts/run_local.sh
```

## Key endpoints
- `POST /simulation/start|pause|speed|step|replay-mode`
- `GET /simulation/state`
- `GET /world/map|nations|cities|agents`
- `GET /events`
- `GET /intel/reports`
- `GET /intel/fog/{nation_id}`
- `GET /history/timeline`
- `GET /history/compare`
- `GET /gm/summary`
- `POST /gm/chat`

## Notes
- API does not mutate kernel directly; scheduler mediates stepping.
- UI/inspectors avoid hidden private state unless debug mode is explicitly enabled.
