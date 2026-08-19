#!/usr/bin/env bash
# Wrapper para download de datasets via python -m modules.datasets

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/../../.." && pwd -P)"

export PYTHONPATH="${PROJECT_ROOT}${PYTHONPATH:+:${PYTHONPATH}}"

exec python -m modules.datasets fetch "$@"
