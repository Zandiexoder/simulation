#!/usr/bin/env bash
set -euo pipefail

STAMP=$(date +%Y%m%d-%H%M%S)
OUT_DIR="reports/$STAMP"
mkdir -p "$OUT_DIR"

echo "== running full test suite =="
pytest -q | tee "$OUT_DIR/pytest.txt"
python - <<PY
from pathlib import Path
from sim.validation import write_json
text=Path('$OUT_DIR/pytest.txt').read_text()
passed='passed' in text and 'failed' not in text.lower()
write_json('$OUT_DIR/test_summary.json', {'status':'pass' if passed else 'needs_review','raw_tail': text.splitlines()[-5:]})
PY

echo "test artifacts: $OUT_DIR"
