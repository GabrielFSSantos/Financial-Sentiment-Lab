#!/usr/bin/env bash
# Trilha B — avaliação de classificador EN (PhraseBank + NOSIBLE).

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd -P)"
VENV_DIR="${PROJECT_ROOT}/venv"
MODEL="finbert_en"
REPORT_DIR="${PROJECT_ROOT}/outputs/campaigns/classifier_eval_en"
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

run_eval() {
    local dataset="$1"
    local run_id="eval_en_${dataset}"

    ./scripts/run_experiment.sh --skip-setup \
        --experiment-config "${CLASSIFIER_CONFIG}" \
        --run-id "${run_id}" \
        --dataset "${dataset}" \
        --model "${MODEL}"

    local predictions="${PROJECT_ROOT}/outputs/${run_id}/models/${MODEL}/${dataset}/predictions.csv"
    mkdir -p "${REPORT_DIR}"
    python -m modules.evaluation.classifier_eval \
        --predictions "${predictions}" \
        --report "${REPORT_DIR}/${dataset}_report.md"
}

cmd_fetch() {
    activate_venv
    python -m modules.datasets fetch \
        --dataset financial_phrasebank_en \
        --dataset nosible_financial_sentiment_en
}

cmd_phrasebank() { activate_venv; run_eval "financial_phrasebank_en"; }
cmd_nosible() { activate_venv; run_eval "nosible_financial_sentiment_en"; }
cmd_all() { cmd_fetch; cmd_phrasebank; cmd_nosible; }

MODE="${1:-}"
shift || true

case "${MODE}" in
    fetch) cmd_fetch ;;
    phrasebank) cmd_phrasebank ;;
    nosible) cmd_nosible ;;
    all) cmd_all ;;
    -h|--help|"")
        cat <<'HELP'
Uso: ./scripts/campaigns/classifier_eval_en.sh <fetch|phrasebank|nosible|all>
HELP
        ;;
    *) echo "Subcomando desconhecido: ${MODE}" >&2; exit 1 ;;
esac
