#!/usr/bin/env bash

# Cria ou atualiza o ambiente virtual do projeto.
#
#   ./scripts/setup_env.sh
#   ./scripts/setup_env.sh --recreate
#   ./scripts/setup_env.sh --fetch-assets

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd -P)"
VENV_DIR="${PROJECT_ROOT}/venv"
REQUIREMENTS_FILE="${PROJECT_ROOT}/requirements.txt"
DEV_REQUIREMENTS_FILE="${PROJECT_ROOT}/requirements-dev.txt"

RECREATE=false
FETCH_ASSETS=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --recreate) RECREATE=true ;;
        --fetch-assets) FETCH_ASSETS=true ;;
        -h|--help)
            cat <<'HELP'
Uso:
  ./scripts/setup_env.sh
  ./scripts/setup_env.sh --recreate
  ./scripts/setup_env.sh --fetch-assets
HELP
            exit 0
            ;;
        *)
            printf 'Opção desconhecida: %s\n' "$1" >&2
            exit 1
            ;;
    esac
    shift
done

if [[ ! -f "${REQUIREMENTS_FILE}" ]]; then
    printf 'Arquivo não encontrado: %s\n' "${REQUIREMENTS_FILE}" >&2
    exit 1
fi

if [[ "${RECREATE}" == true && -d "${VENV_DIR}" ]]; then
    rm -rf -- "${VENV_DIR}"
fi

if [[ ! -f "${VENV_DIR}/bin/activate" ]]; then
    python3 -m venv "${VENV_DIR}"
fi

# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"

python -m pip install -r "${REQUIREMENTS_FILE}"
if [[ -f "${DEV_REQUIREMENTS_FILE}" ]]; then
    python -m pip install -r "${DEV_REQUIREMENTS_FILE}"
fi

printf 'Ambiente pronto: %s\n' "${VENV_DIR}"

if [[ "${FETCH_ASSETS}" == true ]]; then
    export PYTHONPATH="${PROJECT_ROOT}${PYTHONPATH:+:${PYTHONPATH}}"
    "${VENV_DIR}/bin/python" - <<'PY'
from pathlib import Path

from modules.experiment.config.assets import fetch_assets_for_configuration
from modules.experiment.config.loader import load_configuration

configuration = load_configuration(project_root=Path("."))
summary = fetch_assets_for_configuration(configuration)
print(
    f"Assets: {summary.downloaded_count} baixado(s), "
    f"{summary.failed_count} falha(s)."
)
if summary.failed_count:
    raise SystemExit(1)
PY
fi
