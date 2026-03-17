#!/usr/bin/env bash
set -euo pipefail

SRC_DIR="${1:-reports}"
STAMP=$(date +%Y%m%d-%H%M%S)
OUT_DIR="$SRC_DIR/$STAMP"
mkdir -p "$OUT_DIR"

python - <<PY
from pathlib import Path
import json
from sim.validation import write_json
src=Path('$SRC_DIR')
files=list(src.rglob('*.json'))
summary={
  'artifacts_found': len(files),
  'known_limitations': [
    'External AI connectivity affects live naming/people/GM latency and enrichment quality.',
    'Determinism guarantees are bounded by configured seed/tuning and service response variability.'
  ],
  'ready_for_experimentation': len(files) > 0,
}
write_json(Path('$OUT_DIR')/'readiness_summary.json', summary)
(Path('$OUT_DIR')/'readiness_summary.md').write_text('\n'.join([
  '# Release Readiness Summary',
  f"- artifacts_found: {summary['artifacts_found']}",
  f"- ready_for_experimentation: {summary['ready_for_experimentation']}",
  '## Known limitations',
  *[f"- {x}" for x in summary['known_limitations']],
]))
print(json.dumps(summary, indent=2))
PY

echo "artifacts: $OUT_DIR"
