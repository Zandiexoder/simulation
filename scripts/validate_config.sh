#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="${1:-.env}"
if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: $ENV_FILE not found"
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

required=(
  OLLAMA_BASE_URL OLLAMA_MODEL_NAMING OLLAMA_MODEL_PEOPLE OLLAMA_MODEL_GM
  API_HOST API_PORT NAMING_SERVICE_URL GM_GATEWAY_URL
)
for key in "${required[@]}"; do
  if [[ -z "${!key:-}" ]]; then
    echo "ERROR: missing $key"
    exit 1
  fi
done

echo "Config keys present."
echo "Health summary:"
echo "  OLLAMA_BASE_URL=$OLLAMA_BASE_URL"
echo "  OLLAMA_MODEL_NAMING=$OLLAMA_MODEL_NAMING"
echo "  OLLAMA_MODEL_PEOPLE=$OLLAMA_MODEL_PEOPLE"
echo "  OLLAMA_MODEL_GM=$OLLAMA_MODEL_GM"
echo "  SCENARIO_DEFAULT=${SCENARIO_DEFAULT:-default}"
echo "  SNAPSHOT_DIR=${SNAPSHOT_DIR:-./data/snapshots}"

if command -v curl >/dev/null 2>&1; then
  if curl -fsS "${OLLAMA_BASE_URL}/api/tags" >/tmp/ollama_tags.json 2>/dev/null; then
    for model in "$OLLAMA_MODEL_NAMING" "$OLLAMA_MODEL_PEOPLE" "$OLLAMA_MODEL_GM"; do
      if ! rg -q "\"name\"\s*:\s*\"${model}\"" /tmp/ollama_tags.json; then
        echo "WARN: model missing in Ollama: $model"
        echo "      suggested: ollama pull $model"
      else
        echo "OK model present: $model"
      fi
    done
  else
    echo "WARN: unable to query Ollama tags at ${OLLAMA_BASE_URL}"
  fi
else
  echo "WARN: curl not installed; skipping connectivity checks"
fi

echo "Suggested canonical pulls:"
echo "  ollama pull qwen3.5:0.8b"
echo "  ollama pull qwen3.5:4b"
echo "  ollama pull qwen3.5:9b"
echo "Validation complete."
