#!/usr/bin/env bash

# Cria ou atualiza o ambiente virtual do projeto.
#
#   ./scripts/setup_env.sh
#   ./scripts/setup_env.sh --recreate
#   ./scripts/setup_env.sh --fetch-assets
#
# Variáveis opcionais:
#   PYTHON  — interpretador para criar o venv (ex.: /usr/bin/python3.12)

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd -P)"
VENV_DIR="${PROJECT_ROOT}/venv"
REQUIREMENTS_BASE_FILE="${PROJECT_ROOT}/requirements-base.txt"
DEV_REQUIREMENTS_FILE="${PROJECT_ROOT}/requirements-dev.txt"
TORCH_SPEC="torch>=2.1,<3.0"
TORCH_CPU_INDEX="https://download.pytorch.org/whl/cpu"

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

Variáveis opcionais:
  PYTHON   Interpretador para criar o venv (ex.: /usr/bin/python3.12)
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

if [[ ! -f "${REQUIREMENTS_BASE_FILE}" ]]; then
    printf 'Arquivo não encontrado: %s\n' "${REQUIREMENTS_BASE_FILE}" >&2
    exit 1
fi

python_version_tuple() {
    local interpreter="$1"
    "${interpreter}" -c 'import sys; print(".".join(map(str, sys.version_info[:3])))'
}

python_version_supported() {
    local interpreter="$1"
    "${interpreter}" -c 'import sys; raise SystemExit(0 if (3, 10) <= sys.version_info[:2] < (3, 15) else 1)'
}

resolve_python() {
    local candidate=""

    if [[ -n "${PYTHON:-}" ]]; then
        if command -v "${PYTHON}" >/dev/null 2>&1; then
            candidate="${PYTHON}"
        elif [[ -x "${PYTHON}" ]]; then
            candidate="${PYTHON}"
        else
            printf 'PYTHON definido mas não encontrado: %s\n' "${PYTHON}" >&2
            return 1
        fi
        if python_version_supported "${candidate}"; then
            printf '%s' "${candidate}"
            return 0
        fi
        printf 'PYTHON=%s fora da faixa suportada (3.10–3.14).\n' "${candidate}" >&2
        return 1
    fi

    local version
    for version in 3.14 3.13 3.12 3.11 3.10; do
        candidate="python${version}"
        if command -v "${candidate}" >/dev/null 2>&1 \
            && python_version_supported "${candidate}"; then
            printf '%s' "${candidate}"
            return 0
        fi
    done

    candidate="python3"
    if command -v "${candidate}" >/dev/null 2>&1 \
        && python_version_supported "${candidate}"; then
        printf '%s' "${candidate}"
        return 0
    fi

    printf 'Nenhum Python compatível encontrado (requer 3.10–3.14).\n' >&2
    return 1
}

has_nvidia_gpu() {
    command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi >/dev/null 2>&1
}

install_torch() {
    if has_nvidia_gpu; then
        printf 'GPU NVIDIA detectada — instalando PyTorch (CUDA).\n'
        python -m pip install "${TORCH_SPEC}"
        TORCH_VARIANT="CUDA"
    else
        printf 'GPU NVIDIA não detectada — instalando PyTorch (CPU).\n'
        python -m pip install "${TORCH_SPEC}" --index-url "${TORCH_CPU_INDEX}"
        TORCH_VARIANT="CPU"
    fi
}

PYTHON_BIN="$(resolve_python)"
PYTHON_VERSION="$(python_version_tuple "${PYTHON_BIN}")"
printf 'Python selecionado: %s (%s)\n' "${PYTHON_BIN}" "${PYTHON_VERSION}"

if [[ "${RECREATE}" == true && -d "${VENV_DIR}" ]]; then
    rm -rf -- "${VENV_DIR}"
fi

if [[ ! -f "${VENV_DIR}/bin/activate" ]]; then
    "${PYTHON_BIN}" -m venv "${VENV_DIR}"
fi

# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"

python -m pip install --upgrade pip
python -m pip install -r "${REQUIREMENTS_BASE_FILE}"
install_torch

if [[ -f "${DEV_REQUIREMENTS_FILE}" ]]; then
    python -m pip install -r "${DEV_REQUIREMENTS_FILE}"
fi

printf 'Ambiente pronto: %s\n' "${VENV_DIR}"
printf 'Python: %s | PyTorch: %s\n' "${PYTHON_VERSION}" "${TORCH_VARIANT}"
printf 'Próximo passo sugerido: ./scripts/audit_project.sh\n'

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
