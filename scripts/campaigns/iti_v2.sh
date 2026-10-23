#!/usr/bin/env bash
# Invólucro fino ITI-v2 — delega aos módulos existentes (P07/P08/P11/P12).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
CONFIG="${ITI_V2_CONFIG:-configs/campaigns/iti_v2/protocol.yaml}"
PY="${ROOT}/venv/bin/python"
CORPUS="${ITI_V2_CORPUS_DIR:-outputs/corpus_inventory/iti_v2_p02}"
INFER_LIMIT="${ITI_V2_INFER_LIMIT:-0}"

usage() {
  cat <<EOF
Uso: $0 <comando> [opções]

  prepare         — pipeline P02
  lock-protocol   — protocol_lock.json (P11)
  check           — audit + pytest offline
  smoke           — testes ITI-v2 rápidos
  infer <run_id>  — inferência views+canônico (ITI_V2_INFER_LIMIT=0 = completo)
  indices         — run_id [predictions.csv]
  evaluate|report — run_id
  validate        — [run_id] critérios do plano
  run-all         — run_id [corpus.csv] — cadeia completa
  export-thesis   — run_id — pacote thesis_export/
  postprocess     — run_id — evaluate→report→validate→LaTeX→figuras
  gate-local      — smoke + pytest + preflight SDumont (log em logs/iti_v2/)
  sdumont-preflight — artefatos obrigatórios antes do sbatch

EOF
}

cmd="${1:-}"
shift || true

case "$cmd" in
  prepare)
    CSV="${1:-data/water_utilities_corpus/articles_strict_sabesp.csv}"
    exec "$PY" -m modules.datasets prepare-corpus "$CSV" --output-dir "$CORPUS"
    ;;
  check)
    ./scripts/audit_project.sh
    ;;
  smoke)
    exec "$PY" -m pytest -m "not network" tests/test_iti_v2.py tests/test_text_views.py tests/test_iti_v2_acceptance.py -q
    ;;
  select-holdout)
    WEEKS="${1:-12}"
    exec "$PY" -m modules.datasets select-holdout --corpus-dir "$CORPUS" --holdout-weeks "$WEEKS"
    ;;
  lock-protocol)
    exec "$PY" -m modules.experiment.campaign.iti_v2_pipeline lock-protocol \
      --corpus-dir "$CORPUS" --execution-mode "${ITI_V2_MODE:-exploratory}"
    ;;
  indices)
    RUN_ID="${1:?run_id obrigatório}"
    PRED="${2:-outputs/campaigns/iti_v2/${RUN_ID}/predictions.csv}"
    exec "$PY" -m modules.experiment.campaign.iti_v2_pipeline indices \
      --run-id "$RUN_ID" --predictions "$PRED"
    ;;
  infer)
    RUN_ID="${1:?run_id obrigatório}"
    exec "$PY" -m modules.experiment.campaign.iti_v2_pipeline infer \
      --run-id "$RUN_ID" --corpus-dir "$CORPUS" --limit "$INFER_LIMIT"
    ;;
  evaluate)
    RUN_ID="${1:?run_id obrigatório}"
    exec "$PY" -m modules.experiment.campaign.iti_v2_pipeline evaluate --run-id "$RUN_ID"
    ;;
  report)
    RUN_ID="${1:?run_id obrigatório}"
    exec "$PY" -m modules.experiment.campaign.iti_v2_pipeline report --run-id "$RUN_ID"
    ;;
  validate)
    RUN_ID="${1:-}"
    if [[ -n "$RUN_ID" ]]; then
      exec "$PY" -m modules.experiment.campaign.iti_v2_pipeline validate \
        --corpus-dir "$CORPUS" --run-id "$RUN_ID"
    fi
    exec "$PY" -m modules.experiment.campaign.iti_v2_pipeline validate --corpus-dir "$CORPUS"
    ;;
  run-all)
    RUN_ID="${1:?run_id obrigatório}"
    CSV="${2:-data/water_utilities_corpus/articles_strict_sabesp.csv}"
    exec "$PY" -m modules.experiment.campaign.iti_v2_pipeline run-all \
      --run-id "$RUN_ID" --corpus-csv "$CSV" --infer-limit "$INFER_LIMIT"
    ;;
  export-thesis)
    RUN_ID="${1:?run_id obrigatório}"
    exec "$PY" -m modules.experiment.campaign.iti_v2_pipeline export-thesis --run-id "$RUN_ID"
    ;;
  postprocess)
    RUN_ID="${1:?run_id obrigatório}"
    "$PY" -m modules.experiment.campaign.iti_v2_pipeline evaluate --run-id "$RUN_ID"
    "$PY" -m modules.experiment.campaign.iti_v2_pipeline report --run-id "$RUN_ID"
    "$PY" -m modules.experiment.campaign.iti_v2_pipeline validate \
      --corpus-dir "$CORPUS" --run-id "$RUN_ID"
    "$PY" scripts/dissertation/iti_v2/export_iti_v2_latex.py "$RUN_ID"
    "$PY" scripts/dissertation/iti_v2/export_iti_v2_dissertation_tables.py "$RUN_ID"
    "$PY" scripts/dissertation/iti_v2/generate_iti_v2_figures.py "$RUN_ID"
    (cd docs/Dissertacao_PPGCC && latexmk -pdf -interaction=nonstopmode ufsj-abntex2.tex) || true
    "$PY" scripts/references/export_references_downloads_pending.py
    exec "$PY" -m modules.experiment.campaign.iti_v2_pipeline export-thesis --run-id "$RUN_ID"
    ;;
  pin-env)
    exec ./scripts/campaigns/iti_v2_pin_env.sh
    ;;
  gate-local)
    exec ./scripts/campaigns/iti_v2_gate_local.sh
    ;;
  sdumont-preflight)
    exec ./scripts/campaigns/iti_v2_sdumont_preflight.sh
    ;;
  export-annotation-blind)
    OUT="${1:-outputs/campaigns/iti_v2/annotation_blind_pack}"
    exec "$PY" -m modules.evaluation.manual_labels export-blind \
      --manual data/water_utilities_corpus/manual_labels_100.csv \
      --corpus data/water_utilities_corpus/articles_strict_sabesp.csv \
      --output-dir "$OUT"
    ;;
  -h|--help|help|"")
    usage
    exit 0
    ;;
  *)
    echo "Comando desconhecido: $cmd" >&2
    usage
    exit 1
    ;;
esac
