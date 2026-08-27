#!/usr/bin/env bash
# Dashboard Streamlit — exploração da pesquisa
#
#   ./scripts/run_dashboard.sh
#   ./scripts/run_dashboard.sh --port 8502

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd -P)"
VENV_DIR="${PROJECT_ROOT}/venv"

if [[ -f "${VENV_DIR}/bin/activate" ]]; then
    # shellcheck disable=SC1091
    source "${VENV_DIR}/bin/activate"
elif [[ -z "${VIRTUAL_ENV:-}" ]]; then
    printf 'Ambiente virtual não encontrado: %s\n' "${VENV_DIR}" >&2
    exit 1
fi

export PYTHONPATH="${PROJECT_ROOT}${PYTHONPATH:+:${PYTHONPATH}}"

PORT=8501
EXTRA_ARGS=()
while [[ $# -gt 0 ]]; do
    case "$1" in
        --port) PORT="$2"; shift 2 ;;
        *) EXTRA_ARGS+=("$1"); shift ;;
    esac
done

exec streamlit run "${PROJECT_ROOT}/modules/dashboard/app.py" \
    --server.port "${PORT}" \
    --server.address 0.0.0.0 \
    "${EXTRA_ARGS[@]}"
