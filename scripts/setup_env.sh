#!/usr/bin/env bash

# Cria ou atualiza o ambiente virtual do projeto.
#
# Uso:
#   ./scripts/setup_env.sh
#   ./scripts/setup_env.sh --force
#   ./scripts/setup_env.sh --recreate
#   ./scripts/setup_env.sh --python python3.11

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd -P)"

VENV_DIR="${VENV_DIR:-${PROJECT_ROOT}/venv}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
REQUIREMENTS_FILE="${REQUIREMENTS_FILE:-${PROJECT_ROOT}/requirements.txt}"

FORCE_INSTALL=false
RECREATE_ENV=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --venv-dir)
            VENV_DIR="$2"
            shift 2
            ;;

        --python)
            PYTHON_BIN="$2"
            shift 2
            ;;

        --requirements)
            REQUIREMENTS_FILE="$2"
            shift 2
            ;;

        --force)
            FORCE_INSTALL=true
            shift
            ;;

        --recreate)
            RECREATE_ENV=true
            shift
            ;;

        -h|--help)
            cat <<'HELP'
Uso:
  ./scripts/setup_env.sh [opções]

Opções:
  --venv-dir CAMINHO
  --python EXECUTÁVEL
  --requirements ARQUIVO
  --force
  --recreate
  -h, --help
HELP
            exit 0
            ;;

        *)
            printf 'Opção desconhecida: %s\n' "$1" >&2
            exit 1
            ;;
    esac
done

if [[ "${VENV_DIR}" != /* ]]; then
    VENV_DIR="${PROJECT_ROOT}/${VENV_DIR}"
fi

if [[ "${REQUIREMENTS_FILE}" != /* ]]; then
    REQUIREMENTS_FILE="${PROJECT_ROOT}/${REQUIREMENTS_FILE}"
fi

if [[ ! -f "${REQUIREMENTS_FILE}" ]]; then
    printf 'Arquivo de dependências não encontrado: %s\n' \
        "${REQUIREMENTS_FILE}" >&2
    exit 1
fi

if [[ "${RECREATE_ENV}" == true && -d "${VENV_DIR}" ]]; then
    if [[ "${VENV_DIR}" == "/" || "${VENV_DIR}" == "${PROJECT_ROOT}" ]]; then
        printf 'Caminho inválido para recriação: %s\n' \
            "${VENV_DIR}" >&2
        exit 1
    fi

    rm -rf -- "${VENV_DIR}"
fi

CREATED_ENV=false

if [[ ! -f "${VENV_DIR}/bin/activate" ]]; then
    printf 'Criando ambiente virtual em %s\n' "${VENV_DIR}"

    "${PYTHON_BIN}" -m venv "${VENV_DIR}"

    CREATED_ENV=true
fi

# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"

INSTALL_MARKER="${VENV_DIR}/.requirements-installed"

if [[ "${CREATED_ENV}" == true ]] || \
   [[ "${FORCE_INSTALL}" == true ]] || \
   [[ ! -f "${INSTALL_MARKER}" ]] || \
   [[ "${REQUIREMENTS_FILE}" -nt "${INSTALL_MARKER}" ]]
then
    printf 'Instalando dependências de %s\n' \
        "${REQUIREMENTS_FILE}"

    python -m pip install \
        -r "${REQUIREMENTS_FILE}"

    touch "${INSTALL_MARKER}"
else
    printf 'Dependências já instaladas.\n'
fi

printf 'Ambiente pronto: %s\n' "${VENV_DIR}"