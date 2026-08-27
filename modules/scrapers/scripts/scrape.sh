#!/usr/bin/env bash
# Alias de run_scrape.sh once (compatibilidade).

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"

exec "${SCRIPT_DIR}/run_scrape.sh" once "$@"
