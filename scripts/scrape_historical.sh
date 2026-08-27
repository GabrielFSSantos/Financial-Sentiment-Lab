#!/usr/bin/env bash
# Wrapper de compatibilidade — use modules/scrapers/scripts/run_scrape.sh historical

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd -P)"

exec "${PROJECT_ROOT}/modules/scrapers/scripts/run_scrape.sh" historical "$@"
