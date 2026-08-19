#!/usr/bin/env bash

# Ponto de entrada da validação científica.
#
#   ./scripts/run_research.sh
#   ./scripts/run_research.sh --run-id meu_experimento

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd -P)"
VENV_DIR="${PROJECT_ROOT}/venv"

RUNNER_ARGS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help)
            cat <<'HELP'
Uso:
  ./scripts/run_research.sh [opções]

Opções repassadas ao runner:
  --run-id ID
  --model CHAVE
  --dataset CHAVE
  --config CAMINHO
HELP
            exit 0
            ;;
        *)
            RUNNER_ARGS+=("$1")
            shift
            ;;
    esac
done

if [[ -f "${VENV_DIR}/bin/activate" ]]; then
    # shellcheck disable=SC1091
    source "${VENV_DIR}/bin/activate"
elif [[ -z "${VIRTUAL_ENV:-}" ]]; then
    printf 'Ambiente virtual não encontrado: %s\n' "${VENV_DIR}" >&2
    exit 1
fi

export PYTHONPATH="${PROJECT_ROOT}${PYTHONPATH:+:${PYTHONPATH}}"

exec python -m modules.research validate "${RUNNER_ARGS[@]}"
