#!/usr/bin/env bash

# Ponto de entrada do experimento.
#
#   ./scripts/run_experiment.sh
#   ./scripts/run_experiment.sh --skip-setup
#   ./scripts/run_experiment.sh --model finbert_ptbr --dataset noticias_exemplo
#   ./scripts/run_experiment.sh --run-id meu_experimento

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd -P)"
VENV_DIR="${PROJECT_ROOT}/venv"

SKIP_SETUP=false
RUNNER_ARGS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --skip-setup)
            SKIP_SETUP=true
            shift
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
  --skip-setup   Não recria o venv (usado no job Slurm)
  -h, --help     Mostra esta ajuda

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
