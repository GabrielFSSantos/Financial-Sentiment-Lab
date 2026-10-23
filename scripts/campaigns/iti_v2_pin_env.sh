#!/usr/bin/env bash
# Congela dependências Python para pacote SDumont (P12 / plano §7).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT="${ROOT}/outputs/campaigns/iti_v2/env_lock"
mkdir -p "$OUT"
"$ROOT/venv/bin/python" -m pip freeze > "$OUT/requirements-frozen.txt"
"$ROOT/venv/bin/python" -V > "$OUT/python-version.txt"
{
  echo "generated_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  uname -a
} > "$OUT/host-metadata.txt"
echo "Env lock: $OUT/requirements-frozen.txt"
