#!/usr/bin/env bash
set -euo pipefail

API_URL="${1:-http://localhost:8000}"
RUNS="${2:-10}"

echo "== benchmark tick ($RUNS runs) =="
for i in $(seq 1 "$RUNS"); do
  curl -fsS -X POST "$API_URL/simulation/step" -H 'content-type: application/json' -d '{"ticks":1}' >/dev/null
  dur=$(curl -fsS "$API_URL/diagnostics/performance" | python -c 'import sys,json; print(json.load(sys.stdin).get("tick_duration_s",0.0))')
  echo "$i,$dur"
done
