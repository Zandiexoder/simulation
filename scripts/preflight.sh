#!/usr/bin/env bash
set -euo pipefail

API_URL="${1:-http://localhost:8000}"

echo "== preflight =="
curl -fsS "$API_URL/health" >/dev/null && echo "api health: ok" || echo "api health: fail"
curl -fsS "$API_URL/preflight" || true
echo
