#!/usr/bin/env bash
# Validação local completa ITI-v2 (plano P08) — não substitui o job GPU.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
LOG="${ROOT}/docs/plans/iti_v2_validation_latest.log"
mkdir -p "$(dirname "$LOG")"
{
  echo "=== $(date -u +%Y-%m-%dT%H:%M:%SZ) ITI-v2 gate local ==="
  ./scripts/campaigns/iti_v2.sh smoke
  ./venv/bin/python -m pytest -m "not network and not slow" -q
  ./scripts/campaigns/iti_v2_sdumont_preflight.sh
} 2>&1 | tee "$LOG"
echo "Log: $LOG"
