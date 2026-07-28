#!/usr/bin/env bash

# Ponto de entrada do projeto.
#
# Responsabilidades:
#   1. preparar o ambiente, quando necessário;
#   2. ativar o venv;
#   3. chamar scripts/run_service.sh.
#
# Todos os argumentos não relacionados ao ambiente são enviados
# diretamente para pipeline.runner.

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd -P)"

VENV_DIR="${VENV_DIR:-${PROJECT_ROOT}/venv}"
PYTHON_BASE="${PYTHON_BASE:-${PYTHON_BIN:-python3}}"
REQUIREMENTS_FILE="${REQUIREMENTS_FILE:-${PROJECT_ROOT}/requirements.txt}"

SKIP_SETUP=false
SETUP_ARGS=()
RUNNER_ARGS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --skip-setup)
            SKIP_SETUP=true
            shift
            ;;

        --force-setup)
            SETUP_ARGS+=("--force")
            shift
            ;;

        --recreate-env)
            SETUP_ARGS+=("--recreate")
            shift
            ;;

        --venv-dir)
            VENV_DIR="$2"
            shift 2
            ;;

        --python)
            PYTHON_BASE="$2"
            shift 2
            ;;

        --requirements)
            REQUIREMENTS_FILE="$2"
            shift 2
            ;;

        -h|--help)
            cat <<'HELP'
Uso:
  ./scripts/run_experiment.sh [opções do ambiente] [opções da pipeline]

Opções do ambiente:
  --skip-setup
  --force-setup
  --recreate-env
  --venv-dir CAMINHO
  --python EXECUTÁVEL
  --requirements ARQUIVO
  -h, --help

As demais opções são enviadas diretamente para pipeline.runner.

Exemplos:
  ./scripts/run_experiment.sh

  ./scripts/run_experiment.sh --dry-run

  ./scripts/run_experiment.sh \
      --model finbert_ptbr \
      --dataset noticias_exemplo

  ./scripts/run_experiment.sh \
      --environment sdumont \
      --skip-setup
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

if [[ "${VENV_DIR}" != /* ]]; then
    VENV_DIR="${PROJECT_ROOT}/${VENV_DIR}"
fi

if [[ "${REQUIREMENTS_FILE}" != /* ]]; then
    REQUIREMENTS_FILE="${PROJECT_ROOT}/${REQUIREMENTS_FILE}"
fi

if [[ "${SKIP_SETUP}" == false ]]; then
    "${PROJECT_ROOT}/scripts/setup_env.sh" \
        --venv-dir "${VENV_DIR}" \
        --python "${PYTHON_BASE}" \
        --requirements "${REQUIREMENTS_FILE}" \
        "${SETUP_ARGS[@]}"
fi

if [[ -f "${VENV_DIR}/bin/activate" ]]; then
    # shellcheck disable=SC1091
    source "${VENV_DIR}/bin/activate"

elif [[ -z "${VIRTUAL_ENV:-}" ]]; then
    printf 'Ambiente virtual não encontrado: %s\n' \
        "${VENV_DIR}" >&2
    exit 1
fi

export VENV_DIR
export PYTHON_BIN="${VIRTUAL_ENV:-${VENV_DIR}}/bin/python"

exec "${PROJECT_ROOT}/scripts/run_service.sh" \
    "${RUNNER_ARGS[@]}"