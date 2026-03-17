#!/usr/bin/env bash
set -euo pipefail

API_URL="${1:-http://localhost:8000}"
RUNS="${2:-30}"
STAMP=$(date +%Y%m%d-%H%M%S)
OUT_DIR="reports/$STAMP"
mkdir -p "$OUT_DIR"
OUT="$OUT_DIR/benchmark.json"

python - <<PY
import json,urllib.request,urllib.error
from sim.validation import benchmark_summary, write_json
api='$API_URL'
runs=int('$RUNS')
vals=[]
for _ in range(runs):
    req=urllib.request.Request(f'{api}/simulation/step',data=b'{"ticks":1}',headers={'content-type':'application/json'},method='POST')
    urllib.request.urlopen(req).read()
    perf=json.load(urllib.request.urlopen(f'{api}/diagnostics/performance'))
    vals.append(float(perf.get('tick_duration_s',0.0)))
summary=benchmark_summary(vals)
write_json('$OUT', {'runs':runs,'tick_duration_s':summary})
print(json.dumps(summary, indent=2))
PY

echo "artifact: $OUT"
