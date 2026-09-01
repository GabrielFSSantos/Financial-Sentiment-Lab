#!/usr/bin/env bash
# Diagnóstico FinMarBa (Marco 5) — concordância FinBERT × rótulo de mercado.

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd -P)"
VENV_DIR="${PROJECT_ROOT}/venv"
DATASET="finmarba_headlines_en"
RUN_ID="finmarba_classifier_diag"
MODEL="finbert_en"
PREDICTIONS="outputs/${RUN_ID}/models/${MODEL}/${DATASET}/predictions.csv"
REPORT="outputs/campaigns/finmarba_diag/concordance_report.md"
CLASSIFIER_CONFIG="configs/campaigns/trilha_b/classifier_diag.yaml"

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
}

cmd_run() {
    activate_venv
    cmd_fetch
    ./scripts/run_experiment.sh --skip-setup \
        --experiment-config "${CLASSIFIER_CONFIG}" \
        --run-id "${RUN_ID}" \
        --dataset "${DATASET}" \
        --model "${MODEL}"
    mkdir -p "$(dirname "${REPORT}")"
    python -m modules.evaluation.classifier_eval \
        --predictions "${PREDICTIONS}" \
        --report "${REPORT}"
    echo "Relatório: ${REPORT}"
}

MODE="${1:-}"
shift || true

case "${MODE}" in
    fetch) cmd_fetch ;;
    run) cmd_run ;;
    -h|--help|"")
        cat <<'HELP'
Uso: ./scripts/campaigns/finmarba_diag.sh <fetch|run>
HELP
        ;;
    *) echo "Subcomando desconhecido: ${MODE}" >&2; exit 1 ;;
esac
