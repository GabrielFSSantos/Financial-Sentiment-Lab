#!/usr/bin/env bash
# Mescla CSVs em raw/ → noticias.csv + noticias_pendentes.csv

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/../../.." && pwd -P)"

cd "${PROJECT_ROOT}"
export PYTHONPATH="${PROJECT_ROOT}${PYTHONPATH:+:${PYTHONPATH}}"

PYTHON="${PROJECT_ROOT}/venv/bin/python"
if [[ ! -x "${PYTHON}" ]]; then
    PYTHON=python3
fi

exec "${PYTHON}" - <<'PY'
from modules.scrapers.config.loader import load_scrapers_configuration
from modules.scrapers.pipeline.corpus import build_merged_corpus

configuration = load_scrapers_configuration()
result = build_merged_corpus(
    raw_dir=configuration.raw_dir,
    corpus_path=configuration.corpus_path,
    pending_path=configuration.pending_corpus_path,
)
print(
    f"Corpus mesclado: {result.classified_count} classificado(s) → {configuration.corpus_path}"
)
print(
    f"Pendentes: {result.pending_count} → {configuration.pending_corpus_path}"
)
if result.discarded_count:
    print(f"Descartados: {result.discarded_count}")
PY
