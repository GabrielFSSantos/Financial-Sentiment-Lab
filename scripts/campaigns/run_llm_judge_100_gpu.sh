#!/usr/bin/env bash
# Rotulação LLM (até 100 notícias) — GPU. Saída em outputs/campaigns/llm_judge_pilot/
set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
cd "${REPO_ROOT}"

LOG_DIR="${REPO_ROOT}/logs/llm_judge"
mkdir -p "${LOG_DIR}"
STAMP="$(date +%Y%m%d_%H%M%S)"
LOG="${LOG_DIR}/llm_judge_100_${STAMP}.log"
OUT="${REPO_ROOT}/outputs/campaigns/llm_judge_pilot/llm_judge_full_100.csv"
VENV="${REPO_ROOT}/venv/bin/python"

export PYTHONUNBUFFERED=1
export LLM_JUDGE_MOCK="${LLM_JUDGE_MOCK:-0}"

echo "Log: ${LOG}"
echo "Saída: ${OUT}"
echo "Início: $(date -Iseconds)" | tee "${LOG}"

"${VENV}" -m modules.evaluation llm-judge-pilot \
  --all-manual \
  --limit 100 \
  --output-csv "${OUT}" \
  2>&1 | tee -a "${LOG}"

echo "Fim: $(date -Iseconds)" | tee -a "${LOG}"
