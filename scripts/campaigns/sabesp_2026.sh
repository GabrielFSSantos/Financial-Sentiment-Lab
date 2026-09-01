#!/usr/bin/env bash
# Campanha experimental Sabesp — R0–R9 com manifest estruturado.
#
#   ./scripts/campaigns/sabesp_2026.sh init
#   ./scripts/campaigns/sabesp_2026.sh corpus
#   ./scripts/campaigns/sabesp_2026.sh r0
#   ./scripts/campaigns/sabesp_2026.sh all
#   ./scripts/campaigns/sabesp_2026.sh analyze

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd -P)"
VENV_DIR="${PROJECT_ROOT}/venv"
CAMPAIGN_DIR="${PROJECT_ROOT}/outputs/campaigns/sabesp_2026"
MANIFEST="${CAMPAIGN_DIR}/manifest.json"
DATASET="saneamento_sabesp_strict_event"
RESEARCH_CONFIG="${PROJECT_ROOT}/configs/campaigns/sabesp_2026/research_weekly.yaml"
EXPERIMENTS_DIR="configs/campaigns/sabesp_2026/experiments"

RUNS=(
    "r0_baseline:sabesp_r0_baseline:finbert_ptbr"
    "r1_alpha070:sabesp_r1_alpha070:finbert_ptbr"
    "r2_alpha095:sabesp_r2_alpha095:finbert_ptbr"
    "r3_no_novelty:sabesp_r3_no_novelty:finbert_ptbr"
    "r4_no_event:sabesp_r4_no_event:finbert_ptbr"
    "r5_no_relevance:sabesp_r5_no_relevance:finbert_ptbr"
    "r6_simplified:sabesp_r6_simplified:finbert_ptbr"
    "r7_horizon_fixed:sabesp_r7_horizon_fixed:finbert_ptbr"
    "r8_weekly_mean:sabesp_r8_weekly_mean:finbert_ptbr"
    "r9_ensemble:sabesp_r9_ensemble:pt_br_financial_sentiment_analysis"
)

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

cmd_init() {
    activate_venv
    mkdir -p "${CAMPAIGN_DIR}"
    python -m modules.experiment.campaign.generate_configs
    python -m modules.experiment.campaign.init_manifest
    echo "Configs e manifest em ${CAMPAIGN_DIR}"
}

cmd_corpus() {
    activate_venv
    ./modules/scrapers/scripts/run_scrape.sh build-strict
    python -m modules.scrapers filter-corpus \
        --company Sabesp \
        --since 2023-11-01 \
        --until 2024-04-30 \
        -o data/saneamento_corpus/noticias_strict_sabesp.csv
    python -m modules.scrapers report \
        --corpus data/saneamento_corpus/noticias_strict_sabesp.csv
}

run_single() {
    local config_file="$1"
    local run_id="$2"
    local model="$3"
    local research_config="${RESEARCH_CONFIG}"

    if [[ "${config_file}" == *"r8_weekly_mean"* ]]; then
        research_config="${PROJECT_ROOT}/configs/campaigns/sabesp_2026/research_weekly_r8.yaml"
    fi

    echo "=== Experimento ${run_id} (${model}) ==="
    ./scripts/run_experiment.sh --skip-setup \
        --experiment-config "${EXPERIMENTS_DIR}/${config_file}.yaml" \
        --run-id "${run_id}" \
        --dataset "${DATASET}" \
        --model "${model}"

    echo "=== Research ${run_id} ==="
    ./scripts/run_research.sh \
        --run-id "${run_id}" \
        --config "${research_config}"

    python -m modules.experiment.campaign.update_manifest \
        --manifest "${MANIFEST}" \
        --run-id "${run_id}"
}

cmd_r0() {
    activate_venv
    cmd_init
    cmd_corpus
    run_single "r0_baseline" "sabesp_r0_baseline" "finbert_ptbr"
}

cmd_all() {
    activate_venv
    cmd_init
    if [[ ! -f "${PROJECT_ROOT}/data/saneamento_corpus/noticias_strict_sabesp.csv" ]]; then
        cmd_corpus
    fi
    for entry in "${RUNS[@]}"; do
        IFS=':' read -r config run_id model <<< "${entry}"
        run_single "${config}" "${run_id}" "${model}"
    done
    cmd_analyze
}

cmd_analyze() {
    activate_venv
    python -m modules.experiment.campaign.comparative_analysis \
        --manifest "${MANIFEST}" \
        --output "${CAMPAIGN_DIR}/comparative_analysis.md"
}

cmd_manual_sample() {
    activate_venv
    local predictions="${PROJECT_ROOT}/outputs/sabesp_r0_baseline/models/finbert_ptbr/saneamento_sabesp_strict_event/predictions.csv"
    if [[ ! -f "${predictions}" ]]; then
        echo "Rode R0 antes de gerar amostra manual." >&2
        exit 1
    fi
    python -m modules.evaluation.manual_labels sample \
        --predictions "${predictions}"
}

resolve_manual_predictions() {
    local candidates=(
        "${PROJECT_ROOT}/outputs/sabesp_r0_baseline/models/finbert_ptbr/saneamento_sabesp_strict_event/predictions.csv"
        "${PROJECT_ROOT}/outputs/sabesp_marco2_r0_baseline/models/finbert_ptbr/saneamento_sabesp_strict_expanded/predictions.csv"
    )
    local path
    for path in "${candidates[@]}"; do
        if [[ -f "${path}" ]]; then
            echo "${path}"
            return 0
        fi
    done
    echo "Nenhum predictions.csv encontrado (R0 Marco 1 ou Marco 2)." >&2
    return 1
}

cmd_manual_compare() {
    activate_venv
    local predictions
    predictions="$(resolve_manual_predictions)"
    python -m modules.evaluation.manual_labels compare \
        --predictions "${predictions}" \
        --report "${PROJECT_ROOT}/outputs/campaigns/sabesp_2026/manual_label_report.md"
    echo "Relatório: outputs/campaigns/sabesp_2026/manual_label_report.md"
}

MODE="${1:-}"
shift || true

case "${MODE}" in
    init) cmd_init ;;
    corpus) cmd_corpus ;;
    r0) cmd_r0 ;;
    all) cmd_all ;;
    analyze) cmd_analyze ;;
    manual-sample) cmd_manual_sample ;;
    manual-compare) cmd_manual_compare ;;
    marco2)
        echo "Use ./scripts/campaigns/sabesp_marco2.sh (scrape | corpus | replay | all)" >&2
        exit 0
        ;;
    -h|--help|"")
        cat <<'HELP'
Uso: ./scripts/campaigns/sabesp_2026.sh <subcomando>

Subcomandos:
  init           Gera configs/campaigns/sabesp_2026/experiments/*.yaml e manifest
  corpus         Build strict + filtro Sabesp (nov/23–abr/24)
  r0             Baseline R0 + research
  all            R0–R9 + análise comparativa
  analyze        comparative_analysis.md
  manual-sample  Amostra 100 para rotulação manual
  manual-compare Relatório rótulos manuais vs FinBERT
  marco2         Redireciona para sabesp_marco2.sh
HELP
        ;;
    *)
        echo "Subcomando desconhecido: ${MODE}" >&2
        exit 1
        ;;
esac
