#!/usr/bin/env bash
# Marco 2 — amostra PT expandida (Sabesp mai/22–abr/24).
#
#   ./scripts/campaigns/sabesp_marco2.sh scrape
#   ./scripts/campaigns/sabesp_marco2.sh corpus
#   ./scripts/campaigns/sabesp_marco2.sh replay
#   ./scripts/campaigns/sabesp_marco2.sh all

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd -P)"
VENV_DIR="${PROJECT_ROOT}/venv"
CAMPAIGN_DIR="${PROJECT_ROOT}/outputs/campaigns/sabesp_marco2"
DATASET="saneamento_sabesp_strict_expanded"
RESEARCH_CONFIG="${PROJECT_ROOT}/configs/campaigns/sabesp_2026/research_weekly.yaml"
EXPERIMENTS_DIR="configs/campaigns/sabesp_2026/experiments"
CORPUS_PATH="data/saneamento_corpus/noticias_strict_sabesp.csv"

activate_venv() {
    if [[ -f "${VENV_DIR}/bin/activate" ]]; then
        # shellcheck disable=SC1091
        source "${VENV_DIR}/bin/activate"
    elif [[ -z "${VIRTUAL_ENV:-}" ]]; then
        echo "Ambiente virtual não encontrado: ${VENV_DIR}" >&2
        exit 1
    fi
    export PYTHONPATH="${PROJECT_ROOT}${PYTHONPATH:+:${PYTHONPATH}}"
}

cmd_scrape() {
    activate_venv
    "${PROJECT_ROOT}/modules/scrapers/scripts/run_scrape.sh" historical \
        --since 2022-05-01 \
        --until 2022-10-31
}

cmd_scrape_2023() {
    activate_venv
    "${PROJECT_ROOT}/modules/scrapers/scripts/run_scrape.sh" historical \
        --since 2023-01-01 \
        --until 2023-04-30
}

cmd_corpus() {
    activate_venv
    "${PROJECT_ROOT}/modules/scrapers/scripts/run_scrape.sh" build-strict
    python -m modules.scrapers filter-corpus \
        --company Sabesp \
        --since 2022-05-01 \
        --until 2024-04-30 \
        -o "${CORPUS_PATH}"
    python -m modules.scrapers report --corpus "${CORPUS_PATH}"
}

run_replay() {
    local config_file="$1"
    local run_id="$2"
    local model="$3"

    echo "=== Marco 2 — ${run_id} (${model}) ==="
    ./scripts/run_experiment.sh --skip-setup \
        --experiment-config "${EXPERIMENTS_DIR}/${config_file}.yaml" \
        --run-id "${run_id}" \
        --dataset "${DATASET}" \
        --model "${model}"

    ./scripts/run_research.sh \
        --run-id "${run_id}" \
        --dataset "${DATASET}" \
        --model "${model}" \
        --config "${RESEARCH_CONFIG}"
}

cmd_replay() {
    activate_venv
    mkdir -p "${CAMPAIGN_DIR}"
    if [[ ! -f "${PROJECT_ROOT}/${CORPUS_PATH}" ]]; then
        echo "Corpus ausente. Rode: ./scripts/campaigns/sabesp_marco2.sh corpus" >&2
        exit 1
    fi
    run_replay "r0_baseline" "sabesp_marco2_r0_baseline" "finbert_ptbr"
    run_replay "r1_alpha070" "sabesp_marco2_r1_alpha070" "finbert_ptbr"
    echo "Resultados em outputs/sabesp_marco2_r*/"
}

cmd_significant_wins() {
    activate_venv
    mkdir -p "${CAMPAIGN_DIR}"
    python -m modules.evaluation.significant_wins_report \
        --run-id sabesp_gap2023_event_r1_alpha070 \
        --output-dir "${CAMPAIGN_DIR}"
}

run_replay_event_dataset() {
    local config_file="$1"
    local run_id="$2"
    local model="$3"
    local dataset="$4"

    echo "=== Evento (${dataset}) — ${run_id} (${model}) ==="
    ./scripts/run_experiment.sh --skip-setup \
        --experiment-config "${EXPERIMENTS_DIR}/${config_file}.yaml" \
        --run-id "${run_id}" \
        --dataset "${dataset}" \
        --model "${model}"

    ./scripts/run_research.sh \
        --run-id "${run_id}" \
        --dataset "${dataset}" \
        --model "${model}" \
        --config "${RESEARCH_CONFIG}"
}

cmd_replay_event_filtered() {
    activate_venv
    mkdir -p "${CAMPAIGN_DIR}"
    local eval_summary="${PROJECT_ROOT}/outputs/campaigns/classifier_eval_pt/error_analysis_summary.json"
    if [[ ! -f "${eval_summary}" ]]; then
        echo "error_analysis_summary ausente — rode: ./scripts/campaigns/classifier_eval_pt.sh error-analysis" >&2
        exit 1
    fi
    local high_contamination
    high_contamination="$(python -c "import json; d=json.load(open('${eval_summary}')); print('yes' if d.get('high_contamination') else 'no')")"
    if [[ "${high_contamination}" != "yes" ]]; then
        echo "Contaminação roundup < 25% — run filtrada omitida (ver error_analysis.md)."
        return 0
    fi
    python -m modules.evaluation.event_corpus_filter
    run_replay_event_dataset \
        "r1_alpha070" \
        "sabesp_event_r1_filtered" \
        "finbert_ptbr" \
        "saneamento_sabesp_strict_event_filtered"
    echo "Resultados em outputs/sabesp_event_r1_filtered/"
}

DATASET_EVENT="saneamento_sabesp_strict_event"

run_replay_event() {
    local config_file="$1"
    local run_id="$2"
    local model="$3"

    echo "=== Marco 2 evento — ${run_id} (${model}) ==="
    ./scripts/run_experiment.sh --skip-setup \
        --experiment-config "${EXPERIMENTS_DIR}/${config_file}.yaml" \
        --run-id "${run_id}" \
        --dataset "${DATASET_EVENT}" \
        --model "${model}"

    ./scripts/run_research.sh \
        --run-id "${run_id}" \
        --dataset "${DATASET_EVENT}" \
        --model "${model}" \
        --config "${RESEARCH_CONFIG}"
}

cmd_replay_event() {
    activate_venv
    mkdir -p "${CAMPAIGN_DIR}"
    run_replay_event "r0_baseline" "sabesp_marco2_event_r0_baseline" "finbert_ptbr"
    run_replay_event "r1_alpha070" "sabesp_marco2_event_r1_alpha070" "finbert_ptbr"
    echo "Resultados em outputs/sabesp_marco2_event_r*/"
}

cmd_replay_gap2023() {
    activate_venv
    mkdir -p "${CAMPAIGN_DIR}" "${PROJECT_ROOT}/logs/campaigns"
    if [[ ! -f "${PROJECT_ROOT}/${CORPUS_PATH}" ]]; then
        echo "Corpus ausente. Rode: ./scripts/campaigns/sabesp_marco2.sh corpus" >&2
        exit 1
    fi
    run_replay "r0_baseline" "sabesp_gap2023_r0_baseline" "finbert_ptbr"
    run_replay "r1_alpha070" "sabesp_gap2023_r1_alpha070" "finbert_ptbr"
    python -m modules.evaluation.gap2023_summary write
    echo "Resultados em outputs/sabesp_gap2023_r*/"
}

cmd_replay_event_gap2023() {
    activate_venv
    mkdir -p "${CAMPAIGN_DIR}"
    run_replay_event "r0_baseline" "sabesp_gap2023_event_r0_baseline" "finbert_ptbr"
    run_replay_event "r1_alpha070" "sabesp_gap2023_event_r1_alpha070" "finbert_ptbr"
    python -m modules.evaluation.gap2023_summary write
    echo "Resultados em outputs/sabesp_gap2023_event_r*/"
}

cmd_analyze_periods() {
    activate_venv
    local run_id="sabesp_gap2023_r1_alpha070"
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --run-id) run_id="$2"; shift 2 ;;
            *) shift ;;
        esac
    done
    python -m modules.evaluation.period_breakdown \
        --run-id "${run_id}" \
        --dataset saneamento_sabesp_strict_expanded \
        --model finbert_ptbr \
        --output "${CAMPAIGN_DIR}/period_breakdown_gap2023.md"
}

cmd_all() {
    cmd_scrape
    cmd_corpus
    cmd_replay
}

MODE="${1:-}"
shift || true

case "${MODE}" in
    scrape) cmd_scrape ;;
    scrape-2023) cmd_scrape_2023 ;;
    corpus) cmd_corpus ;;
    replay) cmd_replay ;;
    replay-event) cmd_replay_event ;;
    replay-gap2023) cmd_replay_gap2023 ;;
    replay-event-gap2023) cmd_replay_event_gap2023 ;;
    replay-event-filtered) cmd_replay_event_filtered ;;
    analyze-periods) cmd_analyze_periods "$@" ;;
    significant-wins) cmd_significant_wins ;;
    all) cmd_all ;;
    -h|--help|"")
        cat <<'HELP'
Uso: ./scripts/campaigns/sabesp_marco2.sh <subcomando>

Subcomandos:
  scrape         Coleta histórica mai–out/2022
  scrape-2023    Coleta histórica jan–abr/2023 (lacuna)
  corpus         build-strict + filtro Sabesp mai/22–abr/24
  replay         R0 + R1 no dataset expandido (run_ids Marco 2 — sobrescreve)
  replay-event   R0 + R1 só janela evento (run_ids Marco 2 — sobrescreve)
  replay-gap2023 R0 + R1 expandido corpus 1.254 (run_ids sabesp_gap2023_*)
  replay-event-gap2023  Sanity evento com corpus atual (sabesp_gap2023_event_*)
  replay-event-filtered R1 evento sem roundups (só se contaminação ≥25%)
  analyze-periods  ITI×retorno por subperíodo [--run-id ID]
  significant-wins  Tabela das vitórias significativas R1 evento
  all            scrape + corpus + replay
HELP
        ;;
    *)
        echo "Subcomando desconhecido: ${MODE}" >&2
        exit 1
        ;;
esac
