#!/usr/bin/env bash

# Executa diretamente o runner Python da pipeline.

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd -P)"

cd "${PROJECT_ROOT}"

if [[ -n "${PYTHON_BIN:-}" ]]; then
    PYTHON_EXECUTABLE="${PYTHON_BIN}"

elif [[ -n "${VIRTUAL_ENV:-}" && \
        -x "${VIRTUAL_ENV}/bin/python" ]]
then
    PYTHON_EXECUTABLE="${VIRTUAL_ENV}/bin/python"

elif [[ -x "${PROJECT_ROOT}/venv/bin/python" ]]; then
    PYTHON_EXECUTABLE="${PROJECT_ROOT}/venv/bin/python"

else
    PYTHON_EXECUTABLE="python3"
fi

export PYTHONPATH="${PROJECT_ROOT}${PYTHONPATH:+:${PYTHONPATH}}"

export PYTHONUNBUFFERED=1
export PYTHONIOENCODING=utf-8
export PYTHONHASHSEED="${PYTHONHASHSEED:-42}"

export HF_HOME="${HF_HOME:-${PROJECT_ROOT}/.cache/huggingface}"
export TRANSFORMERS_OFFLINE="${TRANSFORMERS_OFFLINE:-1}"
export HF_HUB_OFFLINE="${HF_HUB_OFFLINE:-1}"
export HF_HUB_DISABLE_TELEMETRY="${HF_HUB_DISABLE_TELEMETRY:-1}"
export TOKENIZERS_PARALLELISM="${TOKENIZERS_PARALLELISM:-false}"

CPU_THREADS="${SLURM_CPUS_PER_TASK:-1}"

export OMP_NUM_THREADS="${OMP_NUM_THREADS:-${CPU_THREADS}}"
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-${CPU_THREADS}}"
export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-${CPU_THREADS}}"
export NUMEXPR_NUM_THREADS="${NUMEXPR_NUM_THREADS:-${CPU_THREADS}}"

printf 'Executando com Python: %s\n' \
    "${PYTHON_EXECUTABLE}"

exec "${PYTHON_EXECUTABLE}" \
    -m pipeline.runner \
    "$@"