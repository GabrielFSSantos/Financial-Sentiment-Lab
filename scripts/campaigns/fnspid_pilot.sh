#!/usr/bin/env bash
# Piloto FNSPID (Marco 4) — painel US separado do Sabesp.

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd -P)"
VENV_DIR="${PROJECT_ROOT}/venv"
DATASET="fnspid_pilot"
RUN_ID="fnspid_r0_pilot"
MODEL="finbert_en"

activate_venv() {
    if [[ -f "${VENV_DIR}/bin/activate" ]]; then
        # shellcheck disable=SC1091
        source "${VENV_DIR}/bin/activate"
    elif [[ -z "${VIRTUAL_ENV:-}" ]]; then
        echo "Ambiente virtual não encontrado: ${VENV_DIR}" >&2
        exit 1
    fi
    export PYTHONPATH="${PROJECT_ROOT}${PYTHONPATH:+:${PYTHONPATH}}"
}

cmd_fetch() {
    activate_venv
    python -m modules.datasets fetch --dataset "${DATASET}"
    python -m modules.market fetch --config configs/campaigns/fnspid_pilot/market.yaml
}

cmd_run() {
    activate_venv
    cmd_fetch
    ./scripts/run_experiment.sh --skip-setup \
        --experiment-config configs/campaigns/fnspid_pilot/experiments/r0_pilot.yaml \
        --run-id "${RUN_ID}" \
        --dataset "${DATASET}" \
        --model "${MODEL}"
    ./scripts/run_research.sh \
        --run-id "${RUN_ID}" \
        --dataset "${DATASET}" \
        --model "${MODEL}" \
        --config configs/campaigns/fnspid_pilot/research_weekly.yaml
    echo "Piloto concluído: outputs/${RUN_ID}/"
}

MODE="${1:-}"
shift || true

case "${MODE}" in
    fetch) cmd_fetch ;;
    run) cmd_run ;;
    -h|--help|"")
        cat <<'HELP'
Uso: ./scripts/campaigns/fnspid_pilot.sh <fetch|run>
HELP
        ;;
    *) echo "Subcomando desconhecido: ${MODE}" >&2; exit 1 ;;
esac
