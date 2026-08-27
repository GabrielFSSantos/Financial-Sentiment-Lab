#!/usr/bin/env bash
# Wrapper de compatibilidade — use modules/scrapers/scripts/run_scrape.sh smoke

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd -P)"

if [[ $# -eq 0 || "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    exec "${PROJECT_ROOT}/modules/scrapers/scripts/run_scrape.sh" smoke --help
fi

SITE="${1:-}"
SINCE="${2:-2023-11-01}"
UNTIL="${3:-2023-11-30}"
shift $# 2>/dev/null || true

exec "${PROJECT_ROOT}/modules/scrapers/scripts/run_scrape.sh" smoke \
    --site "${SITE}" --since "${SINCE}" --until "${UNTIL}"
