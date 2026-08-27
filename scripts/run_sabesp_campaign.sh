#!/usr/bin/env bash
# Campanha experimental Sabesp — R0–R9 com manifest estruturado.
#
#   ./scripts/run_sabesp_campaign.sh init          # gera configs + manifest
#   ./scripts/run_sabesp_campaign.sh corpus        # Fase 1: strict + filtro Sabesp
#   ./scripts/run_sabesp_campaign.sh r0            # baseline apenas
#   ./scripts/run_sabesp_campaign.sh all           # R0–R9 (GPU ~3–4h)
#   ./scripts/run_sabesp_campaign.sh analyze       # análise comparativa

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd -P)"
VENV_DIR="${PROJECT_ROOT}/venv"
CAMPAIGN_DIR="${PROJECT_ROOT}/outputs/campaigns/sabesp_2026"
MANIFEST="${CAMPAIGN_DIR}/manifest.json"
DATASET="saneamento_sabesp_strict_event"
RESEARCH_CONFIG="${PROJECT_ROOT}/configs/research_weekly_sabesp.yaml"

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
        research_config="${PROJECT_ROOT}/configs/research_weekly_sabesp_r8.yaml"
    fi

    echo "=== Experimento ${run_id} (${model}) ==="
    ./scripts/run_experiment.sh --skip-setup \
        --experiment-config "configs/experiments/sabesp/${config_file}.yaml" \
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

MODE="${1:-}"
shift || true

case "${MODE}" in
    init) cmd_init ;;
    corpus) cmd_corpus ;;
    r0) cmd_r0 ;;
    all) cmd_all ;;
    analyze) cmd_analyze ;;
    manual-sample) cmd_manual_sample ;;
    -h|--help|"")
        cat <<'HELP'
Uso: ./scripts/run_sabesp_campaign.sh <subcomando>

Subcomandos:
  init           Gera configs/experiments/sabesp/*.yaml e manifest.json
  corpus         Build strict + filtro Sabesp (nov/23–abr/24)
  r0             Fase 2: baseline R0 + research
  all            R0–R9 + análise comparativa
  analyze        Fase 5: comparative_analysis.md
  manual-sample  Fase 4: amostra 100 para rotulação manual
HELP
        ;;
    *)
        echo "Subcomando desconhecido: ${MODE}" >&2
        exit 1
        ;;
esac
