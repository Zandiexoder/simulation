#!/usr/bin/env bash
set -euo pipefail

API_URL="${1:-http://localhost:8000}"
TICKS="${2:-5}"

echo "== smoke run ($TICKS ticks) =="
curl -fsS -X POST "$API_URL/simulation/step" -H 'content-type: application/json' -d "{\"ticks\":$TICKS}" | cat
curl -fsS "$API_URL/diagnostics/performance" | cat
echo
