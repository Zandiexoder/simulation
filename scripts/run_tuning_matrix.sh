#!/usr/bin/env bash
set -euo pipefail

API_URL="${1:-http://localhost:8000}"
STAMP=$(date +%Y%m%d-%H%M%S)
OUT_DIR="reports/$STAMP"
mkdir -p "$OUT_DIR"
OUT="$OUT_DIR/tuning_matrix.jsonl"

cases=(
'{"migration":{"pressure_sensitivity":1.2}}'
'{"politics":{"coup_risk_weight":1.2}}'
'{"international":{"org_formation_threshold":0.58}}'
'{"conflict":{"escalation_sensitivity":1.15}}'
'{"politics":{"legitimacy_recovery_rate":0.005}}'
)

for cfg in "${cases[@]}"; do
  curl -fsS -X POST "$API_URL/tuning" -H 'content-type: application/json' -d "{\"config\":$cfg}" >/dev/null
  curl -fsS -X POST "$API_URL/simulation/step" -H 'content-type: application/json' -d '{"ticks":3}' >/dev/null
  python - <<PY >> "$OUT"
import json,urllib.request
api='$API_URL'
state=json.load(urllib.request.urlopen(f'{api}/simulation/state'))
perf=json.load(urllib.request.urlopen(f'{api}/diagnostics/performance'))
print(json.dumps({'tuning':$cfg,'tick':state['tick'],'metrics':state.get('metrics',{}),'perf':perf.get('module_timings_s',{})}))
PY
  echo "tuning case done"
done

echo "artifact: $OUT"
