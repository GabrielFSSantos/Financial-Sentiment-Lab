#!/usr/bin/env bash
# Coleta notícias (--since/--until ou --cron).

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/../../.." && pwd -P)"

cd "${PROJECT_ROOT}"
export PYTHONPATH="${PROJECT_ROOT}${PYTHONPATH:+:${PYTHONPATH}}"

PYTHON="${PROJECT_ROOT}/venv/bin/python"
if [[ ! -x "${PYTHON}" ]]; then
    PYTHON=python3
fi

exec "${PYTHON}" -m modules.scrapers "$@"
