#!/usr/bin/env bash
set -euo pipefail

API_URL="${1:-http://localhost:8000}"
TICKS="${2:-5}"
STAMP=$(date +%Y%m%d-%H%M%S)
OUT_DIR="reports/$STAMP"
mkdir -p "$OUT_DIR"
OUT="$OUT_DIR/scenario_matrix.jsonl"

SCENARIOS=$(curl -fsS "$API_URL/scenarios" | python -c 'import sys,json; print(" ".join([s["scenario_id"] for s in json.load(sys.stdin)]))')
for s in $SCENARIOS; do
  curl -fsS -X POST "$API_URL/scenarios/load" -H 'content-type: application/json' -d "{\"scenario_id\":\"$s\"}" >/dev/null
  curl -fsS -X POST "$API_URL/simulation/step" -H 'content-type: application/json' -d "{\"ticks\":$TICKS}" >/dev/null
  python - <<PY >> "$OUT"
import json,urllib.request
api='$API_URL'
state=json.load(urllib.request.urlopen(f'{api}/simulation/state'))
perf=json.load(urllib.request.urlopen(f'{api}/diagnostics/performance'))
miles=json.load(urllib.request.urlopen(f'{api}/history/milestones'))
print(json.dumps({'scenario':'$s','tick':state['tick'],'metrics':state.get('metrics',{}),'tick_duration_s':perf.get('tick_duration_s',0.0),'milestone_count':len(miles)}))
PY
  echo "scenario $s done"
done

echo "artifact: $OUT"
