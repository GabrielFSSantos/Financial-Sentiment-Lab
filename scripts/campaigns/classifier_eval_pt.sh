#!/usr/bin/env bash
# Trilha B — bateria PT: FinBERT-PT vs BERTweet vs BERTimbau (100 rótulos manuais).
#
# Gate: acurácia >= 70% OU kappa >= 0,40 (vs kappa=0,163 do FinBERT no Marco 3).
# ITI condicional (janela evento, alpha=0,70) só se o gate passar.

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd -P)"
VENV_DIR="${PROJECT_ROOT}/venv"

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

cmd_prepare() {
    activate_venv
    python -m modules.evaluation.classifier_eval_pt prepare
}

cmd_run() {
    activate_venv
    python -m modules.evaluation.classifier_eval_pt run
}

cmd_iti_if_gate() {
    activate_venv
    python -m modules.evaluation.classifier_eval_pt iti-if-gate
}

cmd_error_analysis() {
    activate_venv
    python -m modules.evaluation.classifier_error_analysis
}

cmd_all() {
    cmd_prepare
    cmd_run
    cmd_error_analysis
    cmd_iti_if_gate
}

MODE="${1:-}"
shift || true

case "${MODE}" in
    prepare) cmd_prepare ;;
    run) cmd_run ;;
    error-analysis) cmd_error_analysis ;;
    iti-if-gate) cmd_iti_if_gate ;;
    all) cmd_all ;;
    -h|--help|"")
        cat <<'HELP'
Uso: ./scripts/campaigns/classifier_eval_pt.sh <subcomando>

Subcomandos:
  prepare      Gera data/water_utilities_corpus/manual_labels_100_eval.csv
  run          Inferência (sem ITI) + kappa para finbert_ptbr, bertweet, bertimbau
  error-analysis  F1 por classe + tipologia roundup vs focal
  iti-if-gate  ITI evento alpha=0,70 só se algum modelo passar o gate
  all          prepare + run + error-analysis + iti-if-gate

Relatórios: outputs/campaigns/classifier_eval_pt/
HELP
        ;;
    *)
        echo "Subcomando desconhecido: ${MODE}" >&2
        exit 1
        ;;
esac
