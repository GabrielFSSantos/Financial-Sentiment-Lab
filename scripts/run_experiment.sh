#!/usr/bin/env bash

# Ponto de entrada do experimento.
#
#   ./scripts/run_experiment.sh
#   ./scripts/run_experiment.sh --skip-setup
#   ./scripts/run_experiment.sh --model finbert_ptbr --dataset noticias_exemplo_ptbr
#   ./scripts/run_experiment.sh --run-id meu_experimento
#   ./scripts/run_experiment.sh --campaign sabesp_2026 --campaign-run r0_baseline

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd -P)"
VENV_DIR="${PROJECT_ROOT}/venv"

SKIP_SETUP=false
CAMPAIGN=""
CAMPAIGN_RUN=""
RUNNER_ARGS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --skip-setup)
            SKIP_SETUP=true
            shift
            ;;
        --campaign)
            CAMPAIGN="${2:-}"
            shift 2
            ;;
        --campaign-run)
            CAMPAIGN_RUN="${2:-}"
            shift 2
            ;;
        --dry-run)
            printf 'Use ./scripts/audit_project.sh para validação sem inferência.\n' >&2
            exit 1
            ;;
        -h|--help)
            cat <<'HELP'
Uso:
  ./scripts/run_experiment.sh [opções] [-- argumentos do runner]

Opções:
  --skip-setup        Não recria o venv (usado no job Slurm)
  --campaign ID       Campanha experimental (ex.: sabesp_2026)
  --campaign-run KEY  Run da campanha (ex.: r0_baseline)
  -h, --help          Mostra esta ajuda

Com --campaign e --campaign-run, o script define --experiment-config,
--run-id, --model e --dataset conforme configs/campaigns/<ID>/.

Argumentos repassados ao runner:
  --model CHAVE
  --dataset CHAVE
  --run-id ID
  --environment local|sdumont
HELP
            exit 0
            ;;
        --)
            shift
            RUNNER_ARGS+=("$@")
            break
            ;;
        *)
            RUNNER_ARGS+=("$1")
            shift
            ;;
    esac
done

if [[ -n "${CAMPAIGN}" || -n "${CAMPAIGN_RUN}" ]]; then
    if [[ -z "${CAMPAIGN}" || -z "${CAMPAIGN_RUN}" ]]; then
        printf 'Use --campaign e --campaign-run juntos.\n' >&2
        exit 1
    fi
    # shellcheck disable=SC1090
    eval "$("${SCRIPT_DIR}/lib/resolve_campaign_run.sh" "${CAMPAIGN}" "${CAMPAIGN_RUN}")"
    RUNNER_ARGS=(
        --experiment-config "${PROJECT_ROOT}/${CAMPAIGN_EXPERIMENT_CONFIG}"
        --run-id "${CAMPAIGN_RUN_ID}"
        --model "${CAMPAIGN_MODEL}"
        --dataset "${CAMPAIGN_DATASET}"
        "${RUNNER_ARGS[@]}"
    )
fi

if [[ "${SKIP_SETUP}" == false && ! -f "${VENV_DIR}/bin/activate" ]]; then
    "${PROJECT_ROOT}/scripts/setup_env.sh"
fi

if [[ -f "${VENV_DIR}/bin/activate" ]]; then
    # shellcheck disable=SC1091
    source "${VENV_DIR}/bin/activate"
elif [[ -z "${VIRTUAL_ENV:-}" ]]; then
    printf 'Ambiente virtual não encontrado: %s\n' "${VENV_DIR}" >&2
    exit 1
fi

export VENV_DIR
export PYTHON_BIN="${VIRTUAL_ENV:-${VENV_DIR}}/bin/python"

exec "${PROJECT_ROOT}/scripts/run_service.sh" "${RUNNER_ARGS[@]}"
