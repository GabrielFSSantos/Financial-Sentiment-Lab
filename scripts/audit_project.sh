#!/usr/bin/env bash

# ==============================================================================
# AUDITORIA DO FINANCIAL SENTIMENT LAB
# ==============================================================================
#
# Executa verificações não destrutivas do projeto e salva um relatório em:
#
#   logs/audit/audit_project_<data>_<hora>.log
#
# Uso padrão:
#
#   ./scripts/audit_project.sh
#
# Opções principais:
#
#   --skip-dry-run       Não executa o dry-run da pipeline.
#   --model-smoke        Executa uma inferência real curta em CPU.
#   --require-cuda       Considera a ausência de CUDA como falha.
#   --environment ENV    Ambiente usado no dry-run: local ou sdumont.
#   --python EXECUTÁVEL  Python utilizado na auditoria.
#   --venv-dir CAMINHO   Ambiente virtual utilizado na auditoria.
#
# A auditoria não instala, atualiza ou remove dependências.
# ==============================================================================

set -uo pipefail
IFS=$'\n\t'


# ==============================================================================
# CONFIGURAÇÃO
# ==============================================================================

readonly SCRIPT_NAME="audit_project"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd -P)"

VENV_DIR="${VENV_DIR:-${PROJECT_ROOT}/venv}"
PYTHON_INPUT="${PYTHON_BIN:-}"
AUDIT_ENVIRONMENT="${EXECUTION_ENVIRONMENT:-}"
LOG_DIR="${AUDIT_LOG_DIR:-${PROJECT_ROOT}/logs/audit}"

RUN_DRY_RUN=true
RUN_MODEL_SMOKE=false
REQUIRE_CUDA=false

PASS_COUNT=0
WARN_COUNT=0
FAIL_COUNT=0
INFO_COUNT=0


# ==============================================================================
# FUNÇÕES DE SAÍDA
# ==============================================================================

timestamp() {
    date '+%Y-%m-%d %H:%M:%S'
}


section() {
    printf '\n%s\n' \
        "=============================================================================="
    printf '%s\n' "$1"
    printf '%s\n' \
        "=============================================================================="
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


run_optional_check() {
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
        warn "${label} não foi aprovado (código ${exit_code})"
    fi

    if [[ -s "${temporary_output}" ]]; then
        sed 's/^/       /' "${temporary_output}"
    fi

    rm -f -- "${temporary_output}"
    return 0
}


show_help() {
    cat <<'HELP'
Uso:
  ./scripts/audit_project.sh [opções]

Opções:
  --python EXECUTÁVEL   Python utilizado nas verificações.
  --venv-dir CAMINHO    Ambiente virtual utilizado.
  --environment ENV     Ambiente do dry-run: local ou sdumont.
  --skip-dry-run        Não executa o dry-run da pipeline.
  --model-smoke         Executa uma inferência real curta em CPU.
  --require-cuda        Falha quando o PyTorch não reconhecer CUDA.
  --log-dir CAMINHO     Diretório onde o relatório será salvo.
  -h, --help            Exibe esta ajuda.

Exemplos:
  ./scripts/audit_project.sh

  ./scripts/audit_project.sh --skip-dry-run

  ./scripts/audit_project.sh --model-smoke

  ./scripts/audit_project.sh \
      --environment sdumont \
      --require-cuda
HELP
}


resolve_project_path() {
    local value="$1"

    if [[ "${value}" = /* ]]; then
        printf '%s\n' "${value}"
    else
        printf '%s\n' "${PROJECT_ROOT}/${value}"
    fi
}


find_python() {
    local candidate=""

    if [[ -n "${PYTHON_INPUT}" ]]; then
        if [[ "${PYTHON_INPUT}" == */* ]]; then
            candidate="$(resolve_project_path "${PYTHON_INPUT}")"

            if [[ -x "${candidate}" ]]; then
                printf '%s\n' "${candidate}"
                return 0
            fi
        elif command -v "${PYTHON_INPUT}" >/dev/null 2>&1; then
            command -v "${PYTHON_INPUT}"
            return 0
        fi

        return 1
    fi

    for candidate in \
        "${VENV_DIR}/bin/python" \
        "${PROJECT_ROOT}/.venv/bin/python" \
        "python3" \
        "python"
    do
        if [[ "${candidate}" == */* ]]; then
            if [[ -x "${candidate}" ]]; then
                printf '%s\n' "${candidate}"
                return 0
            fi
        elif command -v "${candidate}" >/dev/null 2>&1; then
            command -v "${candidate}"
            return 0
        fi
    done

    return 1
}


# ==============================================================================
# ARGUMENTOS
# ==============================================================================

while [[ "$#" -gt 0 ]]; do
    case "$1" in
        --python)
            [[ "$#" -ge 2 ]] || {
                printf 'A opção --python exige um valor.\n' >&2
                exit 2
            }

            PYTHON_INPUT="$2"
            shift 2
            ;;

        --venv-dir)
            [[ "$#" -ge 2 ]] || {
                printf 'A opção --venv-dir exige um valor.\n' >&2
                exit 2
            }

            VENV_DIR="$(resolve_project_path "$2")"
            shift 2
            ;;

        --environment)
            [[ "$#" -ge 2 ]] || {
                printf 'A opção --environment exige local ou sdumont.\n' >&2
                exit 2
            }

            AUDIT_ENVIRONMENT="$2"
            shift 2
            ;;

        --skip-dry-run)
            RUN_DRY_RUN=false
            shift
            ;;

        --model-smoke)
            RUN_MODEL_SMOKE=true
            shift
            ;;

        --require-cuda)
            REQUIRE_CUDA=true
            shift
            ;;

        --log-dir)
            [[ "$#" -ge 2 ]] || {
                printf 'A opção --log-dir exige um caminho.\n' >&2
                exit 2
            }

            LOG_DIR="$(resolve_project_path "$2")"
            shift 2
            ;;

        -h|--help)
            show_help
            exit 0
            ;;

        *)
            printf 'Opção desconhecida: %s\n' "$1" >&2
            exit 2
            ;;
    esac
done


# ==============================================================================
# INICIALIZAÇÃO
# ==============================================================================

if [[ -z "${AUDIT_ENVIRONMENT}" ]]; then
    if [[ -n "${SLURM_JOB_ID:-}" ]]; then
        AUDIT_ENVIRONMENT="sdumont"
    else
        AUDIT_ENVIRONMENT="local"
    fi
fi

case "${AUDIT_ENVIRONMENT}" in
    local|sdumont)
        ;;
    *)
        printf 'Ambiente inválido: %s\n' "${AUDIT_ENVIRONMENT}" >&2
        exit 2
        ;;
esac

mkdir -p -- "${LOG_DIR}"

REPORT_PATH="$(
    printf '%s/audit_project_%s.log' \
        "${LOG_DIR}" \
        "$(date '+%Y%m%d_%H%M%S')"
)"

exec > >(tee "${REPORT_PATH}") 2>&1

cd "${PROJECT_ROOT}"

printf 'Auditoria iniciada em: %s\n' "$(timestamp)"
printf 'Projeto: %s\n' "${PROJECT_ROOT}"
printf 'Relatório: %s\n' "${REPORT_PATH}"
printf 'Ambiente do dry-run: %s\n' "${AUDIT_ENVIRONMENT}"
printf 'Dry-run: %s\n' "${RUN_DRY_RUN}"
printf 'Model smoke: %s\n' "${RUN_MODEL_SMOKE}"
printf 'CUDA obrigatória: %s\n' "${REQUIRE_CUDA}"

PYTHON_EXECUTABLE="$(find_python || true)"

if [[ -n "${PYTHON_EXECUTABLE}" ]]; then
    info "Python selecionado: ${PYTHON_EXECUTABLE}"
else
    fail "Nenhum executável Python foi encontrado."
fi


# ==============================================================================
# 1. AMBIENTE DE EXECUÇÃO
# ==============================================================================

section "1. AMBIENTE DE EXECUÇÃO"

info "Hostname: $(hostname 2>/dev/null || printf 'desconhecido')"
info "Sistema: $(uname -srm 2>/dev/null || printf 'desconhecido')"
info "Diretório atual: $(pwd -P)"

if [[ -n "${SLURM_JOB_ID:-}" ]]; then
    info "Job Slurm: ${SLURM_JOB_ID}"
    info "Partição: ${SLURM_JOB_PARTITION:-não informada}"
    info "Nós: ${SLURM_JOB_NODELIST:-não informado}"
    info "CPUs por tarefa: ${SLURM_CPUS_PER_TASK:-não informado}"
    info "GPUs: ${SLURM_JOB_GPUS:-${CUDA_VISIBLE_DEVICES:-não informado}}"
else
    info "A auditoria não está sendo executada dentro de um job Slurm."
fi

if type module >/dev/null 2>&1; then
    info "Módulos carregados:"
    module list 2>&1 | sed 's/^/       /' || true
else
    info "O comando module não está disponível neste shell."
fi


# ==============================================================================
# 2. ESTRUTURA DO PROJETO
# ==============================================================================

section "2. ESTRUTURA DO PROJETO"

EXPECTED_FILES=(
    ".gitignore"
    "requirements.txt"
    "configs/experiment.yaml"
    "configs/models.yaml"
    "configs/datasets.yaml"
    "scripts/setup_env.sh"
    "scripts/run_service.sh"
    "scripts/run_experiment.sh"
    "scripts/audit_project.sh"
    "jobs/sdumont/run_experiment.srm"
    "models/__init__.py"
    "models/base_model.py"
    "models/finbert_ptbr.py"
    "pipeline/__init__.py"
    "pipeline/configuration.py"
    "pipeline/dataset_loader.py"
    "pipeline/registry.py"
    "pipeline/output_schema.py"
    "pipeline/metrics.py"
    "pipeline/aggregation.py"
    "pipeline/results.py"
    "pipeline/runner.py"
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
    "datasets"
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
        warn "Diretório ausente: ${relative_path}/"
    fi
done

OBSOLETE_PATHS=(
    "configs/sdumont.env"
    "configs/sdumont.env.example"
    "scripts/sync_to_scratch.sh"
    "scripts/setup_sdumont_env.sh"
    "scripts/submit_sdumont.sh"
    "scripts/download_sdumont_results.sh"
)

for relative_path in "${OBSOLETE_PATHS[@]}"; do
    if [[ -e "${PROJECT_ROOT}/${relative_path}" ]]; then
        warn "Arquivo antigo ainda presente: ${relative_path}"
    else
        ok "Arquivo antigo removido: ${relative_path}"
    fi
done


# ==============================================================================
# 3. SCRIPTS SHELL E SLURM
# ==============================================================================

section "3. SCRIPTS SHELL E SLURM"

EXECUTABLE_FILES=(
    "scripts/setup_env.sh"
    "scripts/run_service.sh"
    "scripts/run_experiment.sh"
    "scripts/audit_project.sh"
)

for relative_path in "${EXECUTABLE_FILES[@]}"; do
    absolute_path="${PROJECT_ROOT}/${relative_path}"

    if [[ ! -f "${absolute_path}" ]]; then
        fail "Não foi possível validar permissão: ${relative_path}"
    elif [[ -x "${absolute_path}" ]]; then
        ok "Executável: ${relative_path}"
    else
        fail \
            "Sem permissão de execução: ${relative_path}. " \
            "Use chmod +x ${relative_path}"
    fi
done

mapfile -d '' -t SHELL_FILES < <(
    find \
        "${PROJECT_ROOT}/scripts" \
        "${PROJECT_ROOT}/jobs" \
        -type f \
        \( -name '*.sh' -o -name '*.srm' \) \
        -print0 \
        2>/dev/null
)

if [[ "${#SHELL_FILES[@]}" -eq 0 ]]; then
    fail "Nenhum arquivo Shell foi encontrado."
else
    for file_path in "${SHELL_FILES[@]}"; do
        relative_path="${file_path#"${PROJECT_ROOT}/"}"

        if bash -n "${file_path}"; then
            ok "Sintaxe Bash: ${relative_path}"
        else
            fail "Erro de sintaxe Bash: ${relative_path}"
        fi
    done
fi

CRLF_FOUND=false

while IFS= read -r -d '' file_path; do
    if LC_ALL=C grep -q $'\r' "${file_path}" 2>/dev/null; then
        fail "Quebra de linha CRLF: ${file_path#"${PROJECT_ROOT}/"}"
        CRLF_FOUND=true
    fi
done < <(
    find \
        "${PROJECT_ROOT}/scripts" \
        "${PROJECT_ROOT}/jobs" \
        "${PROJECT_ROOT}/pipeline" \
        "${PROJECT_ROOT}/models" \
        "${PROJECT_ROOT}/configs" \
        -type f \
        \( \
            -name '*.sh' -o \
            -name '*.srm' -o \
            -name '*.py' -o \
            -name '*.yaml' -o \
            -name '*.yml' \
        \) \
        -print0 \
        2>/dev/null
)

if [[ "${CRLF_FOUND}" == false ]]; then
    ok "Nenhum CRLF foi encontrado nos arquivos principais."
fi

SLURM_SCRIPT="${PROJECT_ROOT}/jobs/sdumont/run_experiment.srm"

if [[ -f "${SLURM_SCRIPT}" ]]; then
    if head -n 1 "${SLURM_SCRIPT}" | grep -Fxq '#!/bin/bash'; then
        ok "Cabeçalho correto no job Slurm."
    else
        fail "O job Slurm deve começar com #!/bin/bash."
    fi

    if grep -Eq '^[[:space:]]*#SBATCH' "${SLURM_SCRIPT}"; then
        ok "O job Slurm possui diretivas #SBATCH."
    else
        fail "O job Slurm não possui diretivas #SBATCH."
    fi

    if grep -Fq 'scripts/run_experiment.sh' "${SLURM_SCRIPT}"; then
        ok "O job Slurm chama scripts/run_experiment.sh."
    else
        fail "O job Slurm não chama scripts/run_experiment.sh."
    fi

    if grep -Fq 'source venv/bin/activate' "${SLURM_SCRIPT}"; then
        ok "O job Slurm ativa o ambiente virtual."
    else
        warn "O job Slurm não contém source venv/bin/activate."
    fi

    if grep -Eq \
        'sync_to_scratch|setup_sdumont_env|submit_sdumont|download_sdumont_results|sdumont\.env' \
        "${SLURM_SCRIPT}"
    then
        fail "O job Slurm ainda referencia a arquitetura remota antiga."
    else
        ok "O job Slurm não referencia a arquitetura remota antiga."
    fi
fi

if command -v shellcheck >/dev/null 2>&1; then
    run_optional_check \
        "ShellCheck dos scripts" \
        shellcheck \
        -x \
        "${SHELL_FILES[@]}"
else
    warn "shellcheck não está instalado; análise opcional ignorada."
fi


# ==============================================================================
# 4. CONFIGURAÇÕES YAML
# ==============================================================================

section "4. CONFIGURAÇÕES YAML"

if [[ -n "${PYTHON_EXECUTABLE}" ]]; then
    run_check \
        "Sintaxe e consistência básica dos YAMLs" \
        env PYTHONPATH="${PROJECT_ROOT}" \
        "${PYTHON_EXECUTABLE}" \
        - "${PROJECT_ROOT}" <<'PYTHON_YAML_CHECK'
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml

root = Path(sys.argv[1])

paths = {
    "experiment": root / "configs" / "experiment.yaml",
    "models": root / "configs" / "models.yaml",
    "datasets": root / "configs" / "datasets.yaml",
}

documents: dict[str, dict[str, Any]] = {}

for name, path in paths.items():
    content = yaml.safe_load(path.read_text(encoding="utf-8"))

    if not isinstance(content, dict):
        raise SystemExit(f"{path.name} precisa conter um mapeamento.")

    documents[name] = content
    print(
        f"{path.name}: schema_version="
        f"{content.get('schema_version', '<ausente>')}"
    )

experiment = documents["experiment"]

required_experiment_sections = {
    "experiment",
    "execution",
    "configuration_files",
    "paths",
    "outputs",
    "classification_metrics",
    "performance_metrics",
    "aggregation",
    "reproducibility",
    "preflight_checks",
}

missing_sections = sorted(
    required_experiment_sections.difference(experiment)
)

if missing_sections:
    raise SystemExit(
        "Seções ausentes em experiment.yaml: "
        + ", ".join(missing_sections)
    )

environment = str(
    experiment["execution"].get("environment", "")
).strip().lower()

if environment not in {"local", "sdumont"}:
    raise SystemExit(
        "execution.environment precisa ser local ou sdumont."
    )

configuration_files = experiment["configuration_files"]

if configuration_files.get("models") != "configs/models.yaml":
    raise SystemExit(
        "configuration_files.models precisa apontar para "
        "configs/models.yaml."
    )

if configuration_files.get("datasets") != "configs/datasets.yaml":
    raise SystemExit(
        "configuration_files.datasets precisa apontar para "
        "configs/datasets.yaml."
    )

models = documents["models"].get("models")
datasets = documents["datasets"].get("datasets")

if not isinstance(models, dict) or not models:
    raise SystemExit("models.yaml não possui modelos configurados.")

if not isinstance(datasets, dict) or not datasets:
    raise SystemExit("datasets.yaml não possui datasets configurados.")

enabled_models = [
    key
    for key, value in models.items()
    if isinstance(value, dict)
    and bool(value.get("enabled", False))
]

enabled_datasets = [
    key
    for key, value in datasets.items()
    if isinstance(value, dict)
    and bool(value.get("enabled", False))
]

if not enabled_models:
    raise SystemExit("Nenhum modelo está enabled: true.")

if not enabled_datasets:
    raise SystemExit("Nenhum dataset está enabled: true.")

print(f"environment: {environment}")
print(f"modelos habilitados: {enabled_models}")
print(f"datasets habilitados: {enabled_datasets}")
print(
    "combinações padrão: "
    f"{len(enabled_models) * len(enabled_datasets)}"
)
PYTHON_YAML_CHECK
else
    fail "Os YAMLs não puderam ser analisados sem Python."
fi


# ==============================================================================
# 5. PYTHON E DEPENDÊNCIAS
# ==============================================================================

section "5. PYTHON E DEPENDÊNCIAS"

if [[ -n "${PYTHON_EXECUTABLE}" ]]; then
    run_check \
        "Python 3.10 ou superior" \
        "${PYTHON_EXECUTABLE}" \
        -c \
        'import sys; assert sys.version_info >= (3, 10), sys.version'

    run_check \
        "Disponibilidade de _ctypes e ctypes" \
        "${PYTHON_EXECUTABLE}" \
        -c \
        'import _ctypes, ctypes; print("_ctypes e ctypes: OK")'

    run_check \
        "Compilação de pipeline/ e models/" \
        "${PYTHON_EXECUTABLE}" \
        -m compileall \
        -q \
        "${PROJECT_ROOT}/pipeline" \
        "${PROJECT_ROOT}/models"

    run_check \
        "Importação das dependências principais" \
        env PYTHONPATH="${PROJECT_ROOT}" \
        "${PYTHON_EXECUTABLE}" \
        - <<'PYTHON_IMPORT_CHECK'
from __future__ import annotations

import platform
import sys

import numpy
import pandas
import scipy
import sklearn
import torch
import transformers
import yaml

print(f"Python: {platform.python_version()}")
print(f"Executável: {sys.executable}")
print(f"NumPy: {numpy.__version__}")
print(f"Pandas: {pandas.__version__}")
print(f"SciPy: {scipy.__version__}")
print(f"PyYAML: {yaml.__version__}")
print(f"Scikit-learn: {sklearn.__version__}")
print(f"PyTorch: {torch.__version__}")
print(f"Transformers: {transformers.__version__}")
print(f"CUDA disponível: {torch.cuda.is_available()}")
print(f"CUDA do PyTorch: {torch.version.cuda}")
print(f"GPUs visíveis: {torch.cuda.device_count()}")

for index in range(torch.cuda.device_count()):
    print(f"GPU {index}: {torch.cuda.get_device_name(index)}")
PYTHON_IMPORT_CHECK

    run_check \
        "Compatibilidade com requirements.txt" \
        "${PYTHON_EXECUTABLE}" \
        - "${PROJECT_ROOT}/requirements.txt" <<'PYTHON_REQUIREMENTS_CHECK'
from __future__ import annotations

import importlib.metadata
import sys
from pathlib import Path

from packaging.requirements import Requirement

requirements_path = Path(sys.argv[1])
errors: list[str] = []

for raw_line in requirements_path.read_text(
    encoding="utf-8"
).splitlines():
    line = raw_line.strip()

    if (
        not line
        or line.startswith("#")
        or line.startswith("-")
    ):
        continue

    requirement = Requirement(line)

    if requirement.marker and not requirement.marker.evaluate():
        continue

    try:
        installed = importlib.metadata.version(requirement.name)
    except importlib.metadata.PackageNotFoundError:
        errors.append(f"{requirement.name}: não instalado")
        continue

    if requirement.specifier and installed not in requirement.specifier:
        errors.append(
            f"{requirement.name}: instalado={installed}; "
            f"esperado={requirement.specifier}"
        )
    else:
        print(f"{requirement.name}: {installed}")

if errors:
    print("Incompatibilidades encontradas:", file=sys.stderr)

    for error in errors:
        print(f"  - {error}", file=sys.stderr)

    raise SystemExit(1)
PYTHON_REQUIREMENTS_CHECK

    run_check \
        "Consistência das dependências com pip check" \
        "${PYTHON_EXECUTABLE}" \
        -m pip check

    run_check \
        "Importação dos módulos internos" \
        env PYTHONPATH="${PROJECT_ROOT}" \
        "${PYTHON_EXECUTABLE}" \
        - <<'PYTHON_PROJECT_IMPORTS'
from __future__ import annotations

import models.base_model
import models.finbert_ptbr
import pipeline.aggregation
import pipeline.configuration
import pipeline.dataset_loader
import pipeline.metrics
import pipeline.output_schema
import pipeline.registry
import pipeline.results
import pipeline.runner

print("Módulos internos: OK")
PYTHON_PROJECT_IMPORTS

    run_check \
        "Interface do pipeline.runner" \
        env PYTHONPATH="${PROJECT_ROOT}" \
        "${PYTHON_EXECUTABLE}" \
        -m pipeline.runner \
        --help
else
    fail "As verificações de Python foram ignoradas."
fi


# ==============================================================================
# 6. CUDA
# ==============================================================================

section "6. CUDA"

if [[ -n "${PYTHON_EXECUTABLE}" ]]; then
    if [[ "${REQUIRE_CUDA}" == true ]]; then
        run_check \
            "CUDA disponível no PyTorch" \
            "${PYTHON_EXECUTABLE}" \
            - <<'PYTHON_CUDA_REQUIRED'
import torch

print(f"PyTorch: {torch.__version__}")
print(f"CUDA do PyTorch: {torch.version.cuda}")
print(f"CUDA disponível: {torch.cuda.is_available()}")

if not torch.cuda.is_available():
    raise SystemExit("CUDA não está disponível.")

print(f"GPUs visíveis: {torch.cuda.device_count()}")

for index in range(torch.cuda.device_count()):
    print(f"GPU {index}: {torch.cuda.get_device_name(index)}")
PYTHON_CUDA_REQUIRED
    else
        run_optional_check \
            "Informações de CUDA" \
            "${PYTHON_EXECUTABLE}" \
            - <<'PYTHON_CUDA_OPTIONAL'
import torch

print(f"PyTorch: {torch.__version__}")
print(f"CUDA do PyTorch: {torch.version.cuda}")
print(f"CUDA disponível: {torch.cuda.is_available()}")
print(f"GPUs visíveis: {torch.cuda.device_count()}")

for index in range(torch.cuda.device_count()):
    print(f"GPU {index}: {torch.cuda.get_device_name(index)}")
PYTHON_CUDA_OPTIONAL
    fi

    if command -v nvidia-smi >/dev/null 2>&1; then
        run_optional_check \
            "nvidia-smi" \
            nvidia-smi
    else
        info "nvidia-smi não está disponível neste ambiente."
    fi
else
    fail "CUDA não pôde ser analisada sem Python."
fi


# ==============================================================================
# 7. GIT E ARQUIVOS IGNORADOS
# ==============================================================================

section "7. GIT E ARQUIVOS IGNORADOS"

if git -C "${PROJECT_ROOT}" \
    rev-parse --is-inside-work-tree >/dev/null 2>&1
then
    ok "O diretório é um repositório Git."

    info \
        "Branch: $(git -C "${PROJECT_ROOT}" branch --show-current 2>/dev/null || true)"
    info \
        "Commit: $(git -C "${PROJECT_ROOT}" rev-parse --short HEAD 2>/dev/null || printf 'sem commit')"

    printf '%s\n' "       git status --short:"
    git -C "${PROJECT_ROOT}" status --short 2>/dev/null |
        sed 's/^/       /' || true

    if git -C "${PROJECT_ROOT}" \
        check-ignore -q outputs/audit_test/summary.json
    then
        ok ".gitignore protege outputs/."
    else
        fail ".gitignore não protege outputs/."
    fi

    if git -C "${PROJECT_ROOT}" \
        check-ignore -q logs/audit_test.log
    then
        ok ".gitignore protege logs/."
    else
        fail ".gitignore não protege logs/."
    fi

    if git -C "${PROJECT_ROOT}" \
        check-ignore -q model_store/FinBERT-PT-BR/model.safetensors
    then
        ok ".gitignore protege os pesos dos modelos."
    else
        fail ".gitignore não protege os pesos dos modelos."
    fi

    if git -C "${PROJECT_ROOT}" \
        check-ignore -q datasets/raw/noticias_exemplo/noticias.csv
    then
        fail \
            "O dataset noticias_exemplo está ignorado, " \
            "mas deveria permanecer versionável."
    else
        ok "O dataset noticias_exemplo permanece versionável."
    fi
else
    warn "O diretório não é um repositório Git."
fi


# ==============================================================================
# 8. DRY-RUN DA PIPELINE
# ==============================================================================

section "8. DRY-RUN DA PIPELINE"

if [[ "${RUN_DRY_RUN}" == true ]]; then
    if [[ -x "${PROJECT_ROOT}/scripts/run_experiment.sh" ]]; then
        AUDIT_RUN_ID="audit_$(date '+%Y%m%d_%H%M%S')"

        run_check \
            "Dry-run completo da pipeline" \
            "${PROJECT_ROOT}/scripts/run_experiment.sh" \
            --skip-setup \
            --environment "${AUDIT_ENVIRONMENT}" \
            --dry-run \
            --log-level INFO \
            --run-id "${AUDIT_RUN_ID}"
    else
        fail "scripts/run_experiment.sh não está executável."
    fi
else
    warn "Dry-run ignorado por --skip-dry-run."
fi


# ==============================================================================
# 9. INFERÊNCIA OPCIONAL
# ==============================================================================

section "9. INFERÊNCIA OPCIONAL"

if [[ "${RUN_MODEL_SMOKE}" == true ]]; then
    if [[ -n "${PYTHON_EXECUTABLE}" ]]; then
        run_check \
            "Inferência real curta do FinBERT-PT-BR em CPU" \
            env PYTHONPATH="${PROJECT_ROOT}" \
            "${PYTHON_EXECUTABLE}" \
            - "${PROJECT_ROOT}/model_store/FinBERT-PT-BR" \
            <<'PYTHON_MODEL_SMOKE'
from __future__ import annotations

import sys

from models.finbert_ptbr import FinBertPtBrModel

model = FinBertPtBrModel(
    model_dir=sys.argv[1],
    batch_size=1,
    max_length=128,
    device="cpu",
)

prediction = model.predict(
    ["Lucro da empresa cresce acima do esperado."]
)[0]

print(prediction.to_dict())
model.unload()
PYTHON_MODEL_SMOKE
    else
        fail "A inferência opcional não pôde ser executada sem Python."
    fi
else
    info "Inferência real não solicitada. Use --model-smoke para executá-la."
fi


# ==============================================================================
# 10. ANÁLISE ESTÁTICA OPCIONAL
# ==============================================================================

section "10. ANÁLISE ESTÁTICA OPCIONAL"

if [[ -n "${PYTHON_EXECUTABLE}" ]] && \
    "${PYTHON_EXECUTABLE}" -c \
        'import importlib.util; raise SystemExit(0 if importlib.util.find_spec("pyright") else 1)' \
        >/dev/null 2>&1
then
    run_optional_check \
        "Pyright em pipeline/ e models/" \
        "${PYTHON_EXECUTABLE}" \
        -m pyright \
        "${PROJECT_ROOT}/pipeline" \
        "${PROJECT_ROOT}/models"
elif command -v pyright >/dev/null 2>&1; then
    run_optional_check \
        "Pyright em pipeline/ e models/" \
        pyright \
        "${PROJECT_ROOT}/pipeline" \
        "${PROJECT_ROOT}/models"
else
    warn "Pyright não está instalado; análise estática ignorada."
fi


# ==============================================================================
# 11. REFERÊNCIAS ANTIGAS
# ==============================================================================

section "11. REFERÊNCIAS ANTIGAS"

FILES_TO_INSPECT=(
    "${PROJECT_ROOT}/README.md"
    "${PROJECT_ROOT}/scripts/run_experiment.sh"
    "${PROJECT_ROOT}/scripts/run_service.sh"
    "${PROJECT_ROOT}/scripts/setup_env.sh"
    "${PROJECT_ROOT}/jobs/sdumont/run_experiment.srm"
)

STALE_PATTERN='sync_to_scratch|setup_sdumont_env|submit_sdumont|download_sdumont_results|configs/sdumont\.env'

STALE_FOUND=false

for file_path in "${FILES_TO_INSPECT[@]}"; do
    [[ -f "${file_path}" ]] || continue

    if grep -En "${STALE_PATTERN}" "${file_path}" >/dev/null 2>&1; then
        warn \
            "Referência antiga em ${file_path#"${PROJECT_ROOT}/"}:"

        grep -En "${STALE_PATTERN}" "${file_path}" |
            sed 's/^/       /'

        STALE_FOUND=true
    fi
done

if [[ "${STALE_FOUND}" == false ]]; then
    ok "Nenhuma referência ativa à arquitetura antiga foi encontrada."
fi


# ==============================================================================
# 12. RESUMO
# ==============================================================================

section "12. RESUMO FINAL"

printf 'OK: %s\n' "${PASS_COUNT}"
printf 'AVISOS: %s\n' "${WARN_COUNT}"
printf 'ERROS: %s\n' "${FAIL_COUNT}"
printf 'INFORMAÇÕES: %s\n' "${INFO_COUNT}"
printf 'Relatório salvo em: %s\n' "${REPORT_PATH}"

if [[ "${FAIL_COUNT}" -eq 0 ]]; then
    printf '\nRESULTADO GERAL: APROVADO COM %s AVISO(S).\n' \
        "${WARN_COUNT}"
    exit 0
fi

printf '\nRESULTADO GERAL: REVISÃO NECESSÁRIA — %s ERRO(S).\n' \
    "${FAIL_COUNT}"

exit 1