#!/usr/bin/env bash
# Ponto de entrada unificado do módulo scrapers.
#
#   ./modules/scrapers/scripts/run_scrape.sh historical --since ... --until ...
#   ./modules/scrapers/scripts/run_scrape.sh smoke --site valor [--since ...] [--until ...]
#   ./modules/scrapers/scripts/run_scrape.sh once --since ... --until ... [--site ...] [--use-state]
#   ./modules/scrapers/scripts/run_scrape.sh build-corpus
#   ./modules/scrapers/scripts/run_scrape.sh report
#   ./modules/scrapers/scripts/run_scrape.sh debug-search --site valor --since ... --until ... --query Sabesp

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/../../.." && pwd -P)"

resolve_python() {
    local python="${PROJECT_ROOT}/venv/bin/python"
    if [[ ! -x "${python}" ]]; then
        python=python3
    fi
    printf '%s' "${python}"
}

setup_env() {
    cd "${PROJECT_ROOT}"
    export PYTHONPATH="${PROJECT_ROOT}${PYTHONPATH:+:${PYTHONPATH}}"
    PYTHON="$(resolve_python)"
}

print_usage() {
    cat <<'HELP'
Uso: ./modules/scrapers/scripts/run_scrape.sh <subcomando> [opções]

Subcomandos:
  historical    Coleta mês a mês com --use-state; ao final build-corpus + report
  smoke         Smoke de um portal em janela fixa
  once          Uma janela (--since/--until); repassa flags ao python -m modules.scrapers
  build-corpus  Mescla raw/ → noticias.csv + noticias_pendentes.csv
  build-strict  Mescla raw/ → noticias_strict.csv (filtro entidade offline)
  report        Relatório de volume do corpus
  debug-search  Diagnóstico Playwright (links vs filtro de data)

Exemplos:
  ./modules/scrapers/scripts/run_scrape.sh historical --since 2023-11-01 --until 2024-04-30
  ./modules/scrapers/scripts/run_scrape.sh smoke --site valor --since 2023-11-01 --until 2023-11-30
  ./modules/scrapers/scripts/run_scrape.sh once --since 2024-01-01 --until 2024-03-31 --use-state
  ./modules/scrapers/scripts/run_scrape.sh debug-search --site valor --since 2023-11-01 --until 2023-11-30 --query Sabesp
HELP
}

cmd_historical() {
    local since="" until="" site="" dry_run=false

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --since) since="$2"; shift 2 ;;
            --until) until="$2"; shift 2 ;;
            --site) site="$2"; shift 2 ;;
            --dry-run) dry_run=true; shift ;;
            -h|--help)
                cat <<'HELP'
Uso: run_scrape.sh historical --since YYYY-MM-DD --until YYYY-MM-DD [--site PORTAL] [--dry-run]

Coleta notícias mês a mês com --use-state (pula URLs já vistas).
Ao final, mescla raw/ → noticias.csv + noticias_pendentes.csv.
HELP
                exit 0
                ;;
            *) echo "Opção desconhecida: $1" >&2; exit 1 ;;
        esac
    done

    if [[ -z "${since}" || -z "${until}" ]]; then
        echo "Informe --since e --until (YYYY-MM-DD)." >&2
        exit 1
    fi

    setup_env
    mkdir -p "${PROJECT_ROOT}/logs/scrape"
    local log_file="${PROJECT_ROOT}/logs/scrape/scrape_$(date +%Y%m%d_%H%M%S).log"
    exec > >(tee -a "${log_file}") 2>&1

    echo "Log: ${log_file}"
    echo "Janela total: ${since} → ${until}"

    local site_arg=()
    if [[ -n "${site}" ]]; then
        site_arg=(--site "${site}")
    fi

    mapfile -t windows < <(
        "${PYTHON}" - <<PY
from datetime import date
import calendar

since = date.fromisoformat("${since}")
until = date.fromisoformat("${until}")
year, month = since.year, since.month
while date(year, month, 1) <= until:
    last_day = calendar.monthrange(year, month)[1]
    month_start = date(year, month, 1)
    month_end = date(year, month, last_day)
    window_start = max(month_start, since)
    window_end = min(month_end, until)
    print(f"{window_start.isoformat()} {window_end.isoformat()}")
    if month == 12:
        year += 1
        month = 1
    else:
        month += 1
PY
    )

    if [[ "${#windows[@]}" -eq 0 ]]; then
        echo "Nenhuma janela mensal gerada." >&2
        exit 1
    fi

    for window in "${windows[@]}"; do
        local window_since="${window%% *}"
        local window_until="${window##* }"
        echo ""
        echo "=== Janela ${window_since} → ${window_until} ==="
        if [[ "${dry_run}" == true ]]; then
            echo "[dry-run] ${PYTHON} -m modules.scrapers --since ${window_since} --until ${window_until} --use-state ${site_arg[*]:-}"
            continue
        fi
        "${PYTHON}" -m modules.scrapers \
            --since "${window_since}" \
            --until "${window_until}" \
            --use-state \
            "${site_arg[@]}"
    done

    if [[ "${dry_run}" == true ]]; then
        echo ""
        echo "[dry-run] run_scrape.sh build-corpus"
        exit 0
    fi

    echo ""
    echo "=== Mesclando corpus ==="
    bash "${SCRIPT_DIR}/build_corpus.sh"

    echo ""
    echo "=== Relatório ==="
    "${PYTHON}" -m modules.scrapers report

    echo ""
    echo "Concluído. Log: ${log_file}"
}

cmd_smoke() {
    local site="" since="2023-11-01" until="2023-11-30"

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --site) site="$2"; shift 2 ;;
            --since) since="$2"; shift 2 ;;
            --until) until="$2"; shift 2 ;;
            -h|--help)
                cat <<'HELP'
Uso: run_scrape.sh smoke --site PORTAL [--since YYYY-MM-DD] [--until YYYY-MM-DD]

Smoke de um portal em janela fixa (debug rápido sem campanha completa).
HELP
                exit 0
                ;;
            *)
                if [[ -z "${site}" ]]; then
                    site="$1"
                    shift
                else
                    echo "Opção desconhecida: $1" >&2
                    exit 1
                fi
                ;;
        esac
    done

    if [[ -z "${site}" ]]; then
        echo "Informe --site PORTAL." >&2
        exit 1
    fi

    setup_env
    export PYTHONUNBUFFERED=1

    echo "=== Smoke: ${site} (${since} → ${until}) ==="
    "${PYTHON}" -m modules.scrapers \
        --since "${since}" \
        --until "${until}" \
        --site "${site}"

    local raw_file="${PROJECT_ROOT}/data/water_utilities_corpus/raw/${site}.csv"
    if [[ "${site}" == "g1_economia" ]]; then
        raw_file="${PROJECT_ROOT}/data/water_utilities_corpus/raw/g1.csv"
    fi

    if [[ -f "${raw_file}" ]]; then
        echo ""
        echo "Primeiras URLs em ${raw_file}:"
        "${PYTHON}" - <<PY
import csv
from pathlib import Path

path = Path("${raw_file}")
with path.open(encoding="utf-8") as handle:
    rows = list(csv.DictReader(handle))
print(f"Total no arquivo: {len(rows)}")
for row in rows[:3]:
    print(f"  {row.get('data', '')} | {row.get('url', '')[:100]}")
PY
    fi
}

cmd_once() {
    setup_env
    export PYTHONUNBUFFERED=1
    exec "${PYTHON}" -m modules.scrapers "$@"
}

cmd_build_strict() {
    setup_env
    exec "${PYTHON}" -m modules.scrapers build-strict "$@"
}

cmd_build_corpus() {
    setup_env
    exec bash "${SCRIPT_DIR}/build_corpus.sh"
}

cmd_report() {
    setup_env
    exec "${PYTHON}" -m modules.scrapers report "$@"
}

cmd_debug_search() {
    setup_env
    exec "${PYTHON}" -m modules.scrapers debug-search "$@"
}

MODE="${1:-}"
if [[ -z "${MODE}" || "${MODE}" == "-h" || "${MODE}" == "--help" ]]; then
    print_usage
    exit 0
fi
shift || true

case "${MODE}" in
    historical) cmd_historical "$@" ;;
    smoke) cmd_smoke "$@" ;;
    once) cmd_once "$@" ;;
    build-corpus) cmd_build_corpus "$@" ;;
    build-strict) cmd_build_strict "$@" ;;
    report) cmd_report "$@" ;;
    debug-search) cmd_debug_search "$@" ;;
    *)
        echo "Subcomando desconhecido: ${MODE}" >&2
        print_usage
        exit 1
        ;;
esac
