#!/usr/bin/env bash
set -euo pipefail

API_URL="${1:-http://localhost:8000}"
TICKS="${2:-100}"
SNAP_EVERY="${3:-20}"
STAMP=$(date +%Y%m%d-%H%M%S)
OUT_DIR="reports/$STAMP"
mkdir -p "$OUT_DIR"
OUT="$OUT_DIR/soak_summary.json"

for i in $(seq 1 "$TICKS"); do
  curl -fsS -X POST "$API_URL/simulation/step" -H 'content-type: application/json' -d '{"ticks":1}' >/dev/null
  if (( i % SNAP_EVERY == 0 )); then
    curl -fsS -X POST "$API_URL/snapshots/save" >/dev/null
  fi
done

python - <<PY
import json,urllib.request
from sim.validation import write_json
api='$API_URL'
state=json.load(urllib.request.urlopen(f'{api}/simulation/state'))
diag=json.load(urllib.request.urlopen(f'{api}/diagnostics/performance'))
warn=json.load(urllib.request.urlopen(f'{api}/diagnostics/health')).get('degraded_reasons',[])
snaps=json.load(urllib.request.urlopen(f'{api}/snapshots'))
payload={'tick':state.get('tick'), 'history_events':len(json.load(urllib.request.urlopen(f'{api}/events'))), 'snapshot_count':len(snaps), 'warnings':warn[-20:], 'perf':diag}
write_json('$OUT', payload)
print(json.dumps(payload, indent=2)[:1200])
PY

echo "artifact: $OUT"
