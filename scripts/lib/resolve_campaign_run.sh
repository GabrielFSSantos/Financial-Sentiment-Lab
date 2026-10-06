#!/usr/bin/env bash
# Resolve --campaign / --campaign-run para variáveis de ambiente do runner.
# Uso (eval):
#   eval "$(./scripts/lib/resolve_campaign_run.sh sabesp_2026 r0_baseline)"

set -euo pipefail

CAMPAIGN="${1:-}"
RUN_KEY="${2:-}"

if [[ -z "${CAMPAIGN}" || -z "${RUN_KEY}" ]]; then
    echo "echo 'ERRO: campaign e campaign-run são obrigatórios' >&2; exit 1" >&2
    exit 1
fi

case "${CAMPAIGN}" in
    sabesp_2026)
        EXPERIMENTS_DIR="configs/campaigns/sabesp_2026/experiments"
        CAMPAIGN_DATASET="saneamento_sabesp_strict_event"
        case "${RUN_KEY}" in
            r0_baseline) CONFIG_FILE="r0_baseline"; RUN_ID="sabesp_r0_baseline"; MODEL="finbert_ptbr" ;;
            r1_alpha070) CONFIG_FILE="r1_alpha070"; RUN_ID="sabesp_r1_alpha070"; MODEL="finbert_ptbr" ;;
            r2_alpha095) CONFIG_FILE="r2_alpha095"; RUN_ID="sabesp_r2_alpha095"; MODEL="finbert_ptbr" ;;
            r3_no_novelty) CONFIG_FILE="r3_no_novelty"; RUN_ID="sabesp_r3_no_novelty"; MODEL="finbert_ptbr" ;;
            r4_no_event) CONFIG_FILE="r4_no_event"; RUN_ID="sabesp_r4_no_event"; MODEL="finbert_ptbr" ;;
            r5_no_relevance) CONFIG_FILE="r5_no_relevance"; RUN_ID="sabesp_r5_no_relevance"; MODEL="finbert_ptbr" ;;
            r6_simplified) CONFIG_FILE="r6_simplified"; RUN_ID="sabesp_r6_simplified"; MODEL="finbert_ptbr" ;;
            r7_horizon_fixed) CONFIG_FILE="r7_horizon_fixed"; RUN_ID="sabesp_r7_horizon_fixed"; MODEL="finbert_ptbr" ;;
            r8_weekly_mean) CONFIG_FILE="r8_weekly_mean"; RUN_ID="sabesp_r8_weekly_mean"; MODEL="finbert_ptbr" ;;
            r9_ensemble) CONFIG_FILE="r9_ensemble"; RUN_ID="sabesp_r9_ensemble"; MODEL="pt_br_financial_sentiment_analysis" ;;
            *)
                echo "echo 'Run de campanha desconhecido: ${RUN_KEY}' >&2; exit 1" >&2
                exit 1
                ;;
        esac
        cat <<EOF
export CAMPAIGN_EXPERIMENT_CONFIG="${EXPERIMENTS_DIR}/${CONFIG_FILE}.yaml"
export CAMPAIGN_RUN_ID="${RUN_ID}"
export CAMPAIGN_MODEL="${MODEL}"
export CAMPAIGN_DATASET="${CAMPAIGN_DATASET}"
EOF
        ;;
    *)
        echo "echo 'Campanha desconhecida: ${CAMPAIGN}' >&2; exit 1" >&2
        exit 1
        ;;
esac
