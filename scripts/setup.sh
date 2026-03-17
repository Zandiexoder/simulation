#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -f .env ]]; then
  cp .env.example .env
fi

set_default() {
  local key="$1" value="$2"
  if ! rg -q "^${key}=" .env; then
    echo "${key}=${value}" >> .env
  fi
}

set_default OLLAMA_MODEL_NAMING "${OLLAMA_MODEL_NAMING:-qwen3.5:0.8b}"
set_default OLLAMA_MODEL_PEOPLE "${OLLAMA_MODEL_PEOPLE:-qwen3.5:4b}"
set_default OLLAMA_MODEL_GM "${OLLAMA_MODEL_GM:-qwen3.5:9b}"
set_default OLLAMA_MODEL_ANALYSIS "${OLLAMA_MODEL_ANALYSIS:-qwen3.5:1.5b}"
set_default DIAGNOSTICS_WARNING_RETENTION "${DIAGNOSTICS_WARNING_RETENTION:-200}"
set_default HISTORY_EVENT_RETENTION "${HISTORY_EVENT_RETENTION:-5000}"
set_default SNAPSHOT_DIR "${SNAPSHOT_DIR:-./data/snapshots}"
set_default SCENARIO_DEFAULT "${SCENARIO_DEFAULT:-default}"

echo "Generated/updated .env"
./scripts/validate_config.sh .env

echo "Setup done. Run one of:"
echo "  docker compose up --build"
echo "  ./scripts/run_local.sh"
