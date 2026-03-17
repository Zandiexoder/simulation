#!/usr/bin/env bash
set -euo pipefail
export PYTHONPATH="${PYTHONPATH:-}:$(pwd)"
uvicorn services.api.app.main:app --host 0.0.0.0 --port 8000 &
API_PID=$!
uvicorn app.main:app --app-dir services/gm-gateway --host 0.0.0.0 --port 8010 &
GM_PID=$!
uvicorn services.naming.app.main:app --host 0.0.0.0 --port 8020 &
N_PID=$!
python3 -m http.server 8080 --directory services/frontend &
FE_PID=$!
trap 'kill $API_PID $GM_PID $N_PID $FE_PID 2>/dev/null || true' EXIT
wait
