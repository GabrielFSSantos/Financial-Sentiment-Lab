#!/usr/bin/env bash

# Validação do projeto: estrutura, configuração, pytest e dry-run.

set -uo pipefail
IFS=$'\n\t'

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd -P)"

VENV_DIR="${PROJECT_ROOT}/venv"
LOG_DIR="${PROJECT_ROOT}/logs/audit"

RUN_SMOKE=false
SDUMONT_MODE=false
ASSETS_READY=false

PASS_COUNT=0
WARN_COUNT=0
FAIL_COUNT=0
INFO_COUNT=0

section() {
    printf '\n%s\n' '=============================================================================='
    printf '%s\n' "$1"
    printf '%s\n' '=============================================================================='
}

ok() { PASS_COUNT=$((PASS_COUNT + 1)); printf '[OK] %s\n' "$*"; }
warn() { WARN_COUNT=$((WARN_COUNT + 1)); printf '[AVISO] %s\n' "$*"; }
fail() { FAIL_COUNT=$((FAIL_COUNT + 1)); printf '[ERRO] %s\n' "$*"; }
info() { INFO_COUNT=$((INFO_COUNT + 1)); printf '[INFO] %s\n' "$*"; }

run_check() {
    local label="$1"
    shift
    local temporary_output exit_code=0
    temporary_output="$(mktemp)"
    "$@" >"${temporary_output}" 2>&1
    exit_code=$?
    if [[ "${exit_code}" -eq 0 ]]; then
        ok "${label}"
    else
        fail "${label} (código ${exit_code})"
    fi
    if [[ -s "${temporary_output}" ]]; then
        sed 's/^/       /' "${temporary_output}"
    fi
    rm -f -- "${temporary_output}"
}

usage() {
    cat <<'HELP'
Uso:
  ./scripts/audit_project.sh
  ./scripts/audit_project.sh --smoke
  ./scripts/audit_project.sh --sdumont

  --smoke    Executa inferência curta após a validação (exige model_store/)
  --sdumont  Exige CUDA e model_store/; dry-run obrigatório
  -h, --help Mostra esta ajuda
HELP
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --smoke) RUN_SMOKE=true ;;
        --sdumont) SDUMONT_MODE=true ;;
        -h|--help) usage; exit 0 ;;
        *)
            fail "Opção desconhecida: $1"
            usage
            exit 1
            ;;
    esac
    shift
done

mkdir -p "${LOG_DIR}"
REPORT_FILE="${LOG_DIR}/audit_project_$(date '+%Y%m%d_%H%M%S').log"
exec > >(tee -a "${REPORT_FILE}") 2>&1
cd "${PROJECT_ROOT}" || exit 1

info "Relatório: ${REPORT_FILE}"
info "Projeto: ${PROJECT_ROOT}"

mkdir -p "${PROJECT_ROOT}/outputs" "${PROJECT_ROOT}/logs"

section "1. AMBIENTE"

if [[ -d "${VENV_DIR}" ]]; then
    ok "Ambiente virtual presente: ${VENV_DIR}"
else
    warn "Ambiente virtual ausente: ${VENV_DIR}"
fi

if [[ -x "${VENV_DIR}/bin/python" ]]; then
    PYTHON="${VENV_DIR}/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON="$(command -v python3)"
else
    PYTHON=""
fi

if [[ -z "${PYTHON}" ]]; then
    fail "Python não encontrado"
else
    ok "Python: ${PYTHON}"
    run_check "Python >= 3.10" "${PYTHON}" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)'
    if "${PYTHON}" -c 'import sys; raise SystemExit(0 if sys.version_info < (3, 15) else 1)'; then
        ok "Python na faixa suportada (< 3.15)"
    else
        warn "Python fora da faixa testada (>= 3.15); use 3.10–3.14"
    fi
fi

export PYTHONPATH="${PROJECT_ROOT}${PYTHONPATH:+:${PYTHONPATH}}"

section "2. ESTRUTURA"

EXPECTED_FILES=(
    README.md pyproject.toml requirements.txt requirements-base.txt pytest.ini requirements-dev.txt
    configs/experiment.yaml configs/models.yaml configs/datasets.yaml configs/scrapers.yaml
    configs/market.yaml configs/research.yaml
    data/noticias_exemplo_ptbr/noticias.csv
    data/news_example_en/news.csv
    data/saneamento_corpus/noticias.csv
    scripts/setup_env.sh scripts/run_service.sh scripts/run_experiment.sh scripts/run_research.sh scripts/audit_project.sh
    jobs/sdumont/run_experiment.srm
    modules/experiment/__main__.py modules/experiment/common.py
    modules/experiment/config/loader.py modules/experiment/config/assets.py
    modules/models/__main__.py modules/models/base.py modules/models/sentiment.py
    modules/models/config/loader.py modules/models/assets.py modules/models/registry.py
    modules/models/adapters/bert/finbert_hf.py modules/models/adapters/bert/finbert_ptbr.py
    modules/models/adapters/bert/finbert_en.py modules/models/adapters/bert/finbert_tone_en.py
    modules/models/adapters/bert/pt_br_financial_sentiment_analysis.py
    modules/datasets/__main__.py modules/datasets/common.py modules/datasets/loader.py
    modules/datasets/config/loader.py modules/datasets/assets.py
    modules/market/__main__.py modules/market/common.py modules/market/loader.py
    modules/market/config/loader.py modules/market/assets.py modules/market/scripts/fetch.sh
    modules/research/__main__.py modules/research/common.py modules/research/config/loader.py
    modules/research/io/experiment.py modules/research/io/align.py modules/research/io/reports.py
    modules/research/validation/metrics.py modules/research/validation/inference.py
    modules/research/validation/incremental.py
    modules/research/validation/market.py modules/research/validation/baselines.py
    modules/research/pipeline/runner.py
    modules/experiment/pipeline/runner.py modules/experiment/indexing/temporal_index.py
    modules/experiment/indexing/constants.py modules/experiment/indexing/dimensions.py modules/experiment/indexing/baselines.py
    modules/experiment/io/output_schema.py modules/experiment/io/results.py
    modules/scrapers/__main__.py modules/scrapers/cli/main.py modules/scrapers/config/loader.py
    modules/scrapers/schema/csv.py modules/scrapers/schema/entities.py
    modules/scrapers/pipeline/runner.py modules/scrapers/pipeline/state.py modules/scrapers/core/search.py
    modules/scrapers/sites/base.py modules/scrapers/scripts/scrape.sh modules/scrapers/scripts/build_corpus.sh
    tests/fixtures/research/outputs/test_run/indices/finbert_ptbr/noticias_exemplo_ptbr/iti_daily.csv
    tests/fixtures/research/outputs/test_run/indices/finbert_ptbr/noticias_exemplo_ptbr/baselines_daily.csv
    tests/conftest.py tests/test_sentiment.py tests/test_configuration.py tests/test_compatibility.py tests/test_temporal_index.py
    tests/test_experiment_dimensions.py tests/test_experiment_baselines.py
    tests/test_models_config.py tests/test_models_assets.py
    tests/test_datasets_config.py tests/test_datasets_assets.py tests/test_datasets_validation.py
    tests/test_market_config.py tests/test_market_loader.py tests/test_market_assets.py
    tests/test_research_config.py tests/test_research_align.py tests/test_research_metrics.py
    tests/test_research_incremental.py tests/test_research_runner.py
    tests/test_scrapers_config.py tests/test_scrapers_schema.py tests/test_scrapers_search.py
    tests/test_scrapers_cron.py tests/test_scrapers_corpus.py tests/test_scrapers_live.py
)

for relative_path in "${EXPECTED_FILES[@]}"; do
    if [[ -f "${relative_path}" ]]; then
        ok "Arquivo: ${relative_path}"
    else
        fail "Arquivo ausente: ${relative_path}"
    fi
done

for relative_path in configs data jobs/sdumont model_store modules outputs logs scripts tests; do
    if [[ -d "${relative_path}" ]]; then
        ok "Diretório: ${relative_path}/"
    else
        fail "Diretório ausente: ${relative_path}/"
    fi
done

section "3. SHELL"

for script in scripts/*.sh modules/scrapers/scripts/*.sh; do
    [[ -f "${script}" ]] || continue
    run_check "bash -n $(basename "${script}")" bash -n "${script}"
done
run_check "bash -n run_experiment.srm" bash -n jobs/sdumont/run_experiment.srm

section "4. CONFIGURAÇÃO"

if [[ -n "${PYTHON}" ]]; then
    run_check "load_configuration()" "${PYTHON}" -c \
        'from pathlib import Path; from modules.experiment.config.loader import load_configuration; load_configuration(project_root=Path(".")); print("OK")'

    ASSET_CHECK_FILE="$(mktemp)"
    if "${PYTHON}" - <<'PY' >"${ASSET_CHECK_FILE}" 2>&1; then
from pathlib import Path

from modules.experiment.config.assets import check_enabled_assets
from modules.experiment.config.loader import load_configuration

configuration = load_configuration(project_root=Path("."))
missing = check_enabled_assets(configuration)
if missing:
    print("Assets ausentes para recursos enabled:")
    for item in missing:
        print(f"  - {item}")
    print("Execute: ./scripts/setup_env.sh --fetch-assets")
    raise SystemExit(1)
print("Assets enabled presentes.")
PY
        ok "Assets enabled presentes"
        ASSETS_READY=true
    else
        fail "Assets enabled ausentes"
        sed 's/^/       /' "${ASSET_CHECK_FILE}"
    fi
    rm -f -- "${ASSET_CHECK_FILE}"
fi

section "5. TESTES"

if [[ ! -d tests ]]; then
    fail "Diretório tests/ ausente"
elif [[ -x "${VENV_DIR}/bin/pytest" ]]; then
    run_check "pytest (sem rede)" "${VENV_DIR}/bin/pytest" tests -m "not network"
elif command -v pytest >/dev/null 2>&1; then
    run_check "pytest (sem rede)" pytest tests -m "not network"
else
    fail "pytest não encontrado (pip install -r requirements-dev.txt)"
fi

section "6. INTEGRAÇÃO"

if [[ "${ASSETS_READY}" == true ]]; then
    if [[ "${SDUMONT_MODE}" == true ]]; then
        run_check "CUDA disponível" "${PYTHON}" -c 'import torch; raise SystemExit(0 if torch.cuda.is_available() else 1)'
        run_check "Dry-run (SDumont)" \
            "${PROJECT_ROOT}/scripts/run_service.sh" \
            --environment sdumont \
            --dry-run \
            --model finbert_ptbr \
            --dataset noticias_exemplo_ptbr
    else
        run_check "Dry-run automático" \
            "${PROJECT_ROOT}/scripts/run_service.sh" \
            --dry-run \
            --model finbert_ptbr \
            --dataset noticias_exemplo_ptbr
    fi
else
    info "Dry-run ignorado: assets enabled ausentes"
fi

if [[ "${RUN_SMOKE}" == true ]]; then
    if [[ "${ASSETS_READY}" != true ]]; then
        fail "Smoke requer assets enabled presentes"
    else
        run_check "Smoke FinBERT" "${PYTHON}" - <<'PY'
from modules.experiment.config.loader import load_configuration
from modules.datasets.loader import DatasetLoader
from modules.models.registry import create_model_registry

configuration = load_configuration(
    model_keys=["finbert_ptbr"],
    dataset_keys=["noticias_exemplo_ptbr"],
)
registry = create_model_registry(configuration)
registered = registry.create(
    configuration.get_model("finbert_ptbr"),
    load=True,
)
dataset = DatasetLoader().load(configuration.get_dataset("noticias_exemplo_ptbr"))
predictions = registered.predict(dataset.texts[:2])
if len(predictions) != 2:
    raise SystemExit(f"Esperadas 2 previsões, recebidas {len(predictions)}")
registered.unload()
print("Smoke OK.")
PY
    fi
fi

section "7. RESUMO"
info "OK: ${PASS_COUNT} | AVISO: ${WARN_COUNT} | ERRO: ${FAIL_COUNT}"
info "Relatório: ${REPORT_FILE}"

if [[ "${FAIL_COUNT}" -gt 0 ]]; then
    exit 1
fi
exit 0
