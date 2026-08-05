#!/usr/bin/env bash

# Validação do projeto: estrutura, configuração, pytest e dry-run automático.
#
#   ./scripts/audit_project.sh            # validação padrão
#   ./scripts/audit_project.sh --smoke    # inclui inferência curta (exige pesos)
#   ./scripts/audit_project.sh --sdumont  # validação pré-job no cluster
#
# Relatório: logs/audit/audit_project_<timestamp>.log

set -uo pipefail
IFS=$'\n\t'

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd -P)"

VENV_DIR="${PROJECT_ROOT}/venv"
LOG_DIR="${PROJECT_ROOT}/logs/audit"
FINBERT_DIR="${PROJECT_ROOT}/model_store/FinBERT-PT-BR"

RUN_SMOKE=false
SDUMONT_MODE=false

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

# 1. Ambiente
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
fi

export PYTHONPATH="${PROJECT_ROOT}${PYTHONPATH:+:${PYTHONPATH}}"

# 2. Estrutura
section "2. ESTRUTURA"

EXPECTED_FILES=(
    README.md requirements.txt pytest.ini requirements-dev.txt
    configs/experiment.yaml configs/models.yaml configs/datasets.yaml
    datasets/raw/noticias_exemplo/noticias.csv
    scripts/setup_env.sh scripts/run_service.sh scripts/run_experiment.sh scripts/audit_project.sh
    jobs/sdumont/run_experiment.srm
    pipeline/common.py pipeline/configuration.py pipeline/runner.py pipeline/temporal_index.py
    models/sentiment.py models/base_model.py models/finbert_ptbr.py
    models/pt_br_financial_sentiment_analysis.py
    tests/conftest.py tests/test_sentiment.py tests/test_configuration.py tests/test_compatibility.py tests/test_temporal_index.py
)

for relative_path in "${EXPECTED_FILES[@]}"; do
    if [[ -f "${relative_path}" ]]; then
        ok "Arquivo: ${relative_path}"
    else
        fail "Arquivo ausente: ${relative_path}"
    fi
done

for relative_path in configs datasets/raw jobs/sdumont model_store models outputs logs pipeline scripts tests; do
    if [[ -d "${relative_path}" ]]; then
        ok "Diretório: ${relative_path}/"
    else
        fail "Diretório ausente: ${relative_path}/"
    fi
done

# 3. Shell
section "3. SHELL"

for script in scripts/*.sh; do
    run_check "bash -n $(basename "${script}")" bash -n "${script}"
done
run_check "bash -n run_experiment.srm" bash -n jobs/sdumont/run_experiment.srm

# 4. Configuração
section "4. CONFIGURAÇÃO"

if [[ -n "${PYTHON}" ]]; then
    run_check "load_configuration()" "${PYTHON}" -c \
        'from pathlib import Path; from pipeline.configuration import load_configuration; load_configuration(project_root=Path(".")); print("OK")'
fi

# 5. Testes
section "5. TESTES"

if [[ ! -d tests ]]; then
    fail "Diretório tests/ ausente"
elif [[ -x "${VENV_DIR}/bin/pytest" ]]; then
    run_check "pytest" "${VENV_DIR}/bin/pytest" tests
elif command -v pytest >/dev/null 2>&1; then
    run_check "pytest" pytest tests
else
    fail "pytest não encontrado (pip install -r requirements-dev.txt)"
fi

# 6. Integração
section "6. INTEGRAÇÃO"

if [[ "${SDUMONT_MODE}" == true ]]; then
    run_check "CUDA disponível" "${PYTHON}" -c 'import torch; raise SystemExit(0 if torch.cuda.is_available() else 1)'
    if [[ -d "${FINBERT_DIR}" ]]; then
        ok "Pesos FinBERT presentes"
    else
        fail "Pesos ausentes: ${FINBERT_DIR}"
    fi
    run_check "Dry-run (SDumont)" \
        "${PROJECT_ROOT}/scripts/run_service.sh" \
        --environment sdumont \
        --dry-run \
        --model finbert_ptbr \
        --dataset noticias_exemplo
elif [[ -d "${FINBERT_DIR}" ]]; then
    run_check "Dry-run automático" \
        "${PROJECT_ROOT}/scripts/run_service.sh" \
        --dry-run \
        --model finbert_ptbr \
        --dataset noticias_exemplo
else
    info "Dry-run ignorado: model_store/FinBERT-PT-BR ausente"
fi

if [[ "${RUN_SMOKE}" == true ]]; then
    if [[ ! -d "${FINBERT_DIR}" ]]; then
        fail "Smoke requer pesos em ${FINBERT_DIR}"
    else
        run_check "Smoke FinBERT" "${PYTHON}" - <<'PY'
from pipeline.configuration import load_configuration
from pipeline.dataset_loader import DatasetLoader
from pipeline.registry import create_model_registry

configuration = load_configuration(
    model_keys=["finbert_ptbr"],
    dataset_keys=["noticias_exemplo"],
)
registry = create_model_registry(configuration)
registered = registry.create(
    configuration.get_model("finbert_ptbr"),
    load=True,
)
dataset = DatasetLoader().load(configuration.get_dataset("noticias_exemplo"))
predictions = registered.predict(dataset.texts[:2])
if len(predictions) != 2:
    raise SystemExit(f"Esperadas 2 previsões, recebidas {len(predictions)}")
registered.unload()
print("Smoke OK.")
PY
    fi
fi

# 7. Resumo
section "7. RESUMO"
info "OK: ${PASS_COUNT} | AVISO: ${WARN_COUNT} | ERRO: ${FAIL_COUNT}"
info "Relatório: ${REPORT_FILE}"

if [[ "${FAIL_COUNT}" -gt 0 ]]; then
    exit 1
fi
exit 0
