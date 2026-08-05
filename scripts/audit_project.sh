#!/usr/bin/env bash

# ==============================================================================
# AUDITORIA DO FINANCIAL SENTIMENT LAB
# ==============================================================================
#
# Validação estrutural padrão (sem dry-run):
#
#   ./scripts/audit_project.sh
#
# Integração completa (exige model_store/):
#
#   ./scripts/audit_project.sh --full-dry-run
#
# Opções adicionais:
#
#   --model-smoke          Inferência curta do FinBERT em CPU
#   --ensemble-smoke       Inferência curta do ensemble em CPU
#   --require-cuda         Falha se CUDA não estiver disponível
#   --require-model-store  Falha se pesos locais estiverem ausentes
#   --check-tests          Executa pytest se tests/ existir
#   --environment ENV      local ou sdumont (para dry-run)
#   --python EXEC          Python usado na auditoria
#   --venv-dir CAMINHO     Ambiente virtual usado na auditoria
#
# Relatório salvo em logs/audit/audit_project_<timestamp>.log
# ==============================================================================

set -uo pipefail
IFS=$'\n\t'

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd -P)"

VENV_DIR="${VENV_DIR:-${PROJECT_ROOT}/venv}"
PYTHON_INPUT="${PYTHON_BIN:-}"
AUDIT_ENVIRONMENT="${EXECUTION_ENVIRONMENT:-local}"
LOG_DIR="${AUDIT_LOG_DIR:-${PROJECT_ROOT}/logs/audit}"

RUN_FULL_DRY_RUN=false
RUN_MODEL_SMOKE=false
RUN_ENSEMBLE_SMOKE=false
RUN_CHECK_TESTS=false
REQUIRE_CUDA=false
REQUIRE_MODEL_STORE=false

PASS_COUNT=0
WARN_COUNT=0
FAIL_COUNT=0
INFO_COUNT=0

timestamp() {
    date '+%Y-%m-%d %H:%M:%S'
}

section() {
    printf '\n%s\n' '=============================================================================='
    printf '%s\n' "$1"
    printf '%s\n' '=============================================================================='
}

ok() {
    PASS_COUNT=$((PASS_COUNT + 1))
    printf '[OK] %s\n' "$*"
}

warn() {
    WARN_COUNT=$((WARN_COUNT + 1))
    printf '[AVISO] %s\n' "$*"
}

fail() {
    FAIL_COUNT=$((FAIL_COUNT + 1))
    printf '[ERRO] %s\n' "$*"
}

info() {
    INFO_COUNT=$((INFO_COUNT + 1))
    printf '[INFO] %s\n' "$*"
}

run_check() {
    local label="$1"
    shift

    local temporary_output=""
    local exit_code=0

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
    return 0
}

usage() {
    sed -n '2,28p' "$0" | sed 's/^# \{0,1\}//'
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --full-dry-run)
            RUN_FULL_DRY_RUN=true
            ;;
        --model-smoke)
            RUN_MODEL_SMOKE=true
            ;;
        --ensemble-smoke)
            RUN_ENSEMBLE_SMOKE=true
            ;;
        --check-tests)
            RUN_CHECK_TESTS=true
            ;;
        --require-cuda)
            REQUIRE_CUDA=true
            ;;
        --require-model-store)
            REQUIRE_MODEL_STORE=true
            ;;
        --skip-dry-run)
            RUN_FULL_DRY_RUN=false
            ;;
        --environment)
            shift
            AUDIT_ENVIRONMENT="${1:-local}"
            ;;
        --python)
            shift
            PYTHON_INPUT="${1:-}"
            ;;
        --venv-dir)
            shift
            VENV_DIR="${1:-${PROJECT_ROOT}/venv}"
            ;;
        -h|--help)
            usage
            exit 0
            ;;
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

# ==============================================================================
# 1. AMBIENTE
# ==============================================================================

section "1. AMBIENTE"

info "Hostname: $(hostname 2>/dev/null || echo desconhecido)"
info "Sistema: $(uname -srmo 2>/dev/null || echo desconhecido)"

if command -v squeue >/dev/null 2>&1; then
    info "Slurm detectado (squeue disponível)"
else
    info "Slurm não detectado neste host"
fi

if [[ -d "${VENV_DIR}" ]]; then
    ok "Ambiente virtual presente: ${VENV_DIR}"
else
    warn "Ambiente virtual ausente: ${VENV_DIR}"
fi

if [[ -n "${PYTHON_INPUT}" ]]; then
    PYTHON="${PYTHON_INPUT}"
elif [[ -x "${VENV_DIR}/bin/python" ]]; then
    PYTHON="${VENV_DIR}/bin/python"
else
    PYTHON="$(command -v python3 || command -v python || true)"
fi

if [[ -z "${PYTHON}" ]]; then
    fail "Python não encontrado"
else
    ok "Python selecionado: ${PYTHON}"
fi

if [[ -n "${PYTHON}" ]]; then
    run_check "Python >= 3.10" \
        "${PYTHON}" - <<'PY'
import sys
raise SystemExit(0 if sys.version_info >= (3, 10) else 1)
PY
fi

export PYTHONPATH="${PROJECT_ROOT}${PYTHONPATH:+:${PYTHONPATH}}"

# ==============================================================================
# 2. ESTRUTURA
# ==============================================================================

section "2. ESTRUTURA DO PROJETO"

EXPECTED_FILES=(
    ".gitignore"
    "README.md"
    "requirements.txt"
    "pytest.ini"
    "configs/experiment.yaml"
    "configs/models.yaml"
    "configs/datasets.yaml"
    "datasets/raw/noticias_exemplo/noticias.csv"
    "scripts/setup_env.sh"
    "scripts/run_service.sh"
    "scripts/run_experiment.sh"
    "scripts/audit_project.sh"
    "jobs/sdumont/run_experiment.srm"
    "pipeline/common.py"
    "pipeline/configuration.py"
    "pipeline/dataset_loader.py"
    "pipeline/registry.py"
    "pipeline/output_schema.py"
    "pipeline/metrics.py"
    "pipeline/aggregation.py"
    "pipeline/results.py"
    "pipeline/runner.py"
    "models/sentiment.py"
    "models/base_model.py"
    "models/finbert_ptbr.py"
    "models/pt_br_financial_sentiment_analysis.py"
)

for relative_path in "${EXPECTED_FILES[@]}"; do
    if [[ -f "${PROJECT_ROOT}/${relative_path}" ]]; then
        ok "Arquivo presente: ${relative_path}"
    else
        fail "Arquivo ausente: ${relative_path}"
    fi
done

EXPECTED_DIRECTORIES=(
    "configs"
    "datasets/raw"
    "jobs/sdumont"
    "model_store"
    "models"
    "outputs"
    "logs"
    "pipeline"
    "scripts"
)

for relative_path in "${EXPECTED_DIRECTORIES[@]}"; do
    if [[ -d "${PROJECT_ROOT}/${relative_path}" ]]; then
        ok "Diretório presente: ${relative_path}/"
    else
        fail "Diretório ausente: ${relative_path}/"
    fi
done

LEGACY_PATTERNS=(
    "scripts/sync_sdumont.sh"
    "scripts/submit_sdumont.sh"
    "jobs/sdumont/sync_project.srm"
)

for relative_path in "${LEGACY_PATTERNS[@]}"; do
    if [[ -e "${PROJECT_ROOT}/${relative_path}" ]]; then
        warn "Script legado detectado: ${relative_path}"
    fi
done

SRM_FILE="${PROJECT_ROOT}/jobs/sdumont/run_experiment.srm"
if [[ -f "${SRM_FILE}" ]]; then
    working_dir="$(grep -E '^WORKING_DIR=' "${SRM_FILE}" | head -n 1 | cut -d'"' -f2 || true)"
    if [[ -n "${working_dir}" && "${working_dir}" != "${PROJECT_ROOT}" ]]; then
        warn "WORKING_DIR do job Slurm difere do repositório local: ${working_dir}"
    else
        ok "WORKING_DIR do job Slurm coerente com o repositório"
    fi
fi

if [[ -d "${PROJECT_ROOT}/model_store" ]]; then
    lfs_pointer_count="$(find "${PROJECT_ROOT}/model_store" -type f -name '*.safetensors' -exec grep -Il 'git-lfs' {} + 2>/dev/null | wc -l | tr -d ' ')"
    if [[ "${lfs_pointer_count}" != "0" ]]; then
        warn "Possíveis ponteiros Git LFS em model_store/ (${lfs_pointer_count} arquivo(s))"
    else
        ok "Nenhum ponteiro Git LFS óbvio em model_store/"
    fi
fi

# ==============================================================================
# 3. SHELL / SLURM
# ==============================================================================

section "3. SHELL E SLURM"

for script in \
    "${PROJECT_ROOT}/scripts/setup_env.sh" \
    "${PROJECT_ROOT}/scripts/run_service.sh" \
    "${PROJECT_ROOT}/scripts/run_experiment.sh" \
    "${PROJECT_ROOT}/scripts/audit_project.sh"
do
    if [[ -f "${script}" ]]; then
        run_check "bash -n $(basename "${script}")" bash -n "${script}"
        if [[ -x "${script}" ]]; then
            ok "Executável: $(basename "${script}")"
        else
            warn "Sem permissão de execução: ${script}"
        fi
        if grep -q $'\r' "${script}"; then
            fail "CRLF detectado em ${script}"
        else
            ok "Sem CRLF: $(basename "${script}")"
        fi
    fi
done

if [[ -f "${SRM_FILE}" ]]; then
    run_check "bash -n run_experiment.srm" bash -n "${SRM_FILE}"
    for directive in "#SBATCH --partition" "#SBATCH --gres" "#SBATCH --time"; do
        if grep -q "${directive}" "${SRM_FILE}"; then
            ok "Diretiva Slurm presente: ${directive}"
        else
            fail "Diretiva Slurm ausente: ${directive}"
        fi
    done
fi

if command -v shellcheck >/dev/null 2>&1; then
    run_check "ShellCheck scripts/" \
        shellcheck "${PROJECT_ROOT}/scripts/"*.sh
else
    warn "ShellCheck não instalado (opcional)"
fi

# ==============================================================================
# 4. CONFIGURAÇÃO (PYTHON)
# ==============================================================================

section "4. CONFIGURAÇÃO YAML"

if [[ -n "${PYTHON}" ]]; then
    run_check "load_configuration()" \
        "${PYTHON}" - <<PY
from pathlib import Path
from pipeline.configuration import load_configuration

load_configuration(project_root=Path("${PROJECT_ROOT}"))
print("Configuração carregada com sucesso.")
PY

    run_check "Dataset de exemplo válido" \
        "${PYTHON}" - <<'PY'
import csv
from pathlib import Path

from pipeline.common import CANONICAL_LABELS

csv_path = Path("datasets/raw/noticias_exemplo/noticias.csv")
if not csv_path.exists():
    raise SystemExit(f"Arquivo ausente: {csv_path}")

with csv_path.open(newline="", encoding="utf-8") as handle:
    rows = list(csv.DictReader(handle))

if not rows:
    raise SystemExit("CSV de exemplo está vazio")

labels = {row.get("true_label", "").strip().upper() for row in rows if row.get("true_label")}
invalid = sorted(label for label in labels if label and label not in CANONICAL_LABELS)
if invalid:
    raise SystemExit(f"Labels inválidos no CSV de exemplo: {invalid}")

print(f"Dataset de exemplo OK ({len(rows)} linhas).")
PY
fi

# ==============================================================================
# 5. PYTHON BÁSICO
# ==============================================================================

section "5. PYTHON BÁSICO"

if [[ -n "${PYTHON}" ]]; then
    run_check "compileall pipeline/ e models/" \
        "${PYTHON}" -m compileall -q "${PROJECT_ROOT}/pipeline" "${PROJECT_ROOT}/models"

    run_check "Imports dos módulos registrados" \
        "${PYTHON}" - <<PY
import importlib
from pathlib import Path

import yaml

from pipeline.configuration import load_configuration

configuration = load_configuration(project_root=Path("${PROJECT_ROOT}"))
models_yaml = Path("${PROJECT_ROOT}") / "configs" / "models.yaml"
raw = yaml.safe_load(models_yaml.read_text(encoding="utf-8"))
models = raw.get("models", {})

for key, entry in models.items():
    adapter = entry.get("adapter")
    if not adapter:
        continue
    importlib.import_module(adapter.rsplit(".", 1)[0])
    module_name, class_name = adapter.rsplit(".", 1)
    getattr(importlib.import_module(module_name), class_name)

import pipeline.runner
import models.sentiment

print(f"Imports OK ({len(configuration.models)} modelos configurados).")
PY

    run_check "pipeline.runner --help" \
        "${PYTHON}" -m pipeline.runner --help

    if [[ -f "${PROJECT_ROOT}/requirements.txt" ]]; then
        run_check "Dependências principais importáveis" \
            "${PYTHON}" - <<'PY'
import numpy
import pandas
import yaml
import sklearn
import torch
import transformers
import safetensors
print("Dependências principais OK.")
PY
    fi

    if command -v "${VENV_DIR}/bin/pip" >/dev/null 2>&1; then
        run_check "pip check" "${VENV_DIR}/bin/pip" check
    elif command -v pip >/dev/null 2>&1; then
        run_check "pip check" pip check
    else
        warn "pip não encontrado para pip check"
    fi

    if command -v pyright >/dev/null 2>&1; then
        run_check "pyright pipeline/ models/" \
            pyright "${PROJECT_ROOT}/pipeline" "${PROJECT_ROOT}/models"
    else
        warn "Pyright não instalado (opcional)"
    fi
fi

if [[ "${REQUIRE_MODEL_STORE}" == true ]]; then
    run_check "model_store/ contém diretórios de modelos enabled" \
        "${PYTHON}" - <<PY
from pathlib import Path

from pipeline.configuration import load_configuration

configuration = load_configuration(project_root=Path("${PROJECT_ROOT}"))
missing = []
for model in configuration.models:
    if not model.model_dir.exists():
        missing.append(str(model.model_dir))
if missing:
    raise SystemExit("Pesos ausentes:\\n" + "\\n".join(missing))
print("model_store/ OK.")
PY
fi

# ==============================================================================
# 6. INTEGRAÇÃO (OPCIONAL)
# ==============================================================================

section "6. INTEGRAÇÃO OPCIONAL"

if [[ "${REQUIRE_CUDA}" == true ]]; then
    if [[ -n "${PYTHON}" ]]; then
        run_check "CUDA disponível" \
            "${PYTHON}" - <<'PY'
import torch
raise SystemExit(0 if torch.cuda.is_available() else 1)
PY
    fi
else
    if [[ -n "${PYTHON}" ]]; then
        if "${PYTHON}" - <<'PY'
import torch
raise SystemExit(0 if torch.cuda.is_available() else 1)
PY
        then
            ok "CUDA disponível"
        else
            info "CUDA indisponível (esperado em ambiente local)"
        fi
    fi
fi

if [[ "${RUN_FULL_DRY_RUN}" == true ]]; then
    run_check "Dry-run completo da pipeline" \
        "${PROJECT_ROOT}/scripts/run_experiment.sh" \
        --environment "${AUDIT_ENVIRONMENT}" \
        --dry-run
fi

if [[ "${RUN_MODEL_SMOKE}" == true && -n "${PYTHON}" ]]; then
    run_check "Smoke FinBERT (CPU)" \
        "${PYTHON}" - <<'PY'
from pipeline.configuration import load_configuration
from pipeline.dataset_loader import DatasetLoader
from pipeline.registry import create_model_registry

configuration = load_configuration(
    model_keys=["finbert_ptbr"],
    dataset_keys=["noticias_exemplo"],
)
registry = create_model_registry(configuration)
model_cfg = configuration.get_model("finbert_ptbr")
registered = registry.create(model_cfg, load=True)
dataset = DatasetLoader().load(configuration.get_dataset("noticias_exemplo"))
predictions = registered.predict(dataset.texts[:2])
if len(predictions) != 2:
    raise SystemExit(f"Esperadas 2 previsões, recebidas {len(predictions)}")
registered.unload()
print("Smoke FinBERT OK.")
PY
fi

if [[ "${RUN_ENSEMBLE_SMOKE}" == true && -n "${PYTHON}" ]]; then
    run_check "Smoke ensemble (CPU)" \
        "${PYTHON}" - <<'PY'
from pipeline.configuration import load_configuration
from pipeline.dataset_loader import DatasetLoader
from pipeline.registry import create_model_registry

configuration = load_configuration(
    model_keys=["pt_br_financial_sentiment_analysis"],
    dataset_keys=["noticias_exemplo"],
)
registry = create_model_registry(configuration)
model_cfg = configuration.get_model("pt_br_financial_sentiment_analysis")
registered = registry.create(model_cfg, load=True)
dataset = DatasetLoader().load(configuration.get_dataset("noticias_exemplo"))
predictions = registered.predict(dataset.texts[:2])
if len(predictions) != 2:
    raise SystemExit(f"Esperadas 2 previsões, recebidas {len(predictions)}")
registered.unload()
print("Smoke ensemble OK.")
PY
fi

if [[ "${RUN_CHECK_TESTS}" == true ]]; then
    if [[ -d "${PROJECT_ROOT}/tests" ]]; then
        if command -v pytest >/dev/null 2>&1 || [[ -x "${VENV_DIR}/bin/pytest" ]]; then
            PYTEST_BIN="${VENV_DIR}/bin/pytest"
            if [[ ! -x "${PYTEST_BIN}" ]]; then
                PYTEST_BIN="$(command -v pytest)"
            fi
            run_check "pytest" "${PYTEST_BIN}" "${PROJECT_ROOT}/tests"
        else
            fail "pytest não encontrado (instale requirements-dev.txt)"
        fi
    else
        warn "Diretório tests/ ainda não existe; nada a executar"
    fi
fi

# ==============================================================================
# 7. RESUMO
# ==============================================================================

section "7. RESUMO"

info "OK: ${PASS_COUNT} | AVISO: ${WARN_COUNT} | ERRO: ${FAIL_COUNT}"
info "Relatório salvo em: ${REPORT_FILE}"

if [[ "${FAIL_COUNT}" -gt 0 ]]; then
    exit 1
fi

exit 0
