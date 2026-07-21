#!/usr/bin/env bash

# ==============================================================================
# SERVIÇO INTERNO DE EXECUÇÃO DA PIPELINE
# ==============================================================================
#
# Este script é a camada fina entre os scripts de infraestrutura e o runner
# Python. Ele:
#
# - localiza a raiz do projeto;
# - seleciona um interpretador Python válido;
# - configura variáveis de ambiente comuns ao ambiente local e ao SDumont;
# - valida Python e dependências essenciais;
# - converte variáveis de ambiente opcionais em argumentos do runner;
# - executa ``python -m pipeline.runner``;
# - preserva o código de saída retornado pelo runner.
#
# Execução direta:
#
#   ./scripts/run_service.sh
#
# Dry-run:
#
#   ./scripts/run_service.sh --dry-run
#
# Seleção temporária:
#
#   ./scripts/run_service.sh \
#       --model finbert_ptbr \
#       --dataset noticias_exemplo
#
# Normalmente este arquivo será chamado por:
#
#   ./scripts/run_experiment.sh
#
# No job Slurm, será chamado por:
#
#   jobs/sdumont/run_experiment.srm
#
# Este script não cria ambiente virtual e não instala dependências.
# Essas responsabilidades pertencem a:
#
#   scripts/setup_env.sh
#   scripts/setup_sdumont_env.sh
# ==============================================================================

set -Eeuo pipefail
IFS=$'\n\t'


# ==============================================================================
# CONSTANTES
# ==============================================================================

readonly SERVICE_NAME="run_service"
readonly MINIMUM_PYTHON_MAJOR=3
readonly MINIMUM_PYTHON_MINOR=10

CHILD_PID=""


# ==============================================================================
# LOG
# ==============================================================================

timestamp() {
    date '+%Y-%m-%d %H:%M:%S'
}


log() {
    local message=""
    printf -v message '%s' "$@"

    printf '[%s] [%s] %s\n' \
        "$(timestamp)" \
        "${SERVICE_NAME}" \
        "${message}"
}


warning() {
    local message=""
    printf -v message '%s' "$@"

    printf '[%s] [%s] AVISO: %s\n' \
        "$(timestamp)" \
        "${SERVICE_NAME}" \
        "${message}" \
        >&2
}


error() {
    local message=""
    printf -v message '%s' "$@"

    printf '[%s] [%s] ERRO: %s\n' \
        "$(timestamp)" \
        "${SERVICE_NAME}" \
        "${message}" \
        >&2
}


die() {
    error "$*"
    exit 1
}


# ==============================================================================
# TRATAMENTO DE ERROS E SINAIS
# ==============================================================================

on_error() {
    local exit_code=$?
    local line_number="${BASH_LINENO[0]:-desconhecida}"
    local failed_command="${BASH_COMMAND:-desconhecido}"

    trap - ERR

    error "A execução do serviço foi interrompida."
    error "Código de saída: ${exit_code}"
    error "Linha aproximada: ${line_number}"
    error "Comando: ${failed_command}"

    exit "${exit_code}"
}


forward_signal() {
    local signal_name="$1"

    if [[ -z "${CHILD_PID}" ]]; then
        return 0
    fi

    if kill -0 "${CHILD_PID}" 2>/dev/null; then
        warning \
            "Encaminhando o sinal ${signal_name} ao runner " \
            "(PID ${CHILD_PID})."

        kill "-${signal_name}" "${CHILD_PID}" 2>/dev/null || true
    fi
}


trap on_error ERR
trap 'forward_signal INT' INT
trap 'forward_signal TERM' TERM
trap 'forward_signal HUP' HUP


# ==============================================================================
# LOCALIZAÇÃO DO PROJETO
# ==============================================================================

SCRIPT_DIR="$(
    cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1
    pwd -P
)"

PROJECT_ROOT="$(
    cd -- "${SCRIPT_DIR}/.." >/dev/null 2>&1
    pwd -P
)"

[[ -d "${PROJECT_ROOT}" ]] || die \
    "Não foi possível identificar a raiz do projeto."

cd "${PROJECT_ROOT}"


# ==============================================================================
# FUNÇÕES AUXILIARES
# ==============================================================================

trim_value() {
    local value="$1"

    value="${value#"${value%%[![:space:]]*}"}"
    value="${value%"${value##*[![:space:]]}"}"

    printf '%s\n' "${value}"
}


normalize_lowercase() {
    printf '%s' "${1:-}" | tr '[:upper:]' '[:lower:]'
}


is_true() {
    local value

    value="$(normalize_lowercase "${1:-false}")"

    case "${value}" in
        1|true|yes|y|on|sim|s)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}


is_false() {
    local value

    value="$(normalize_lowercase "${1:-false}")"

    case "${value}" in
        0|false|no|n|off|nao|não)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}


resolve_project_path() {
    local path_value="$1"

    if [[ "${path_value}" = /* ]]; then
        printf '%s\n' "${path_value}"
    else
        printf '%s\n' "${PROJECT_ROOT}/${path_value}"
    fi
}


resolve_executable() {
    local value="$1"
    local candidate=""

    [[ -n "${value}" ]] || return 1

    if [[ "${value}" == */* ]]; then
        candidate="${value}"

        if [[ "${candidate}" != /* ]]; then
            candidate="${PROJECT_ROOT}/${candidate}"
        fi

        [[ -x "${candidate}" ]] || return 1

        printf '%s\n' "${candidate}"
        return 0
    fi

    command -v "${value}" 2>/dev/null
}


resolve_venv_directory() {
    local value="${1:-venv}"

    if [[ "${value}" = /* ]]; then
        printf '%s\n' "${value}"
    else
        printf '%s\n' "${PROJECT_ROOT}/${value}"
    fi
}


resolve_python() {
    local candidate=""
    local configured_venv=""

    # 1. Interpretador explicitamente informado.
    if [[ -n "${PYTHON_BIN:-}" ]]; then
        candidate="$(resolve_executable "${PYTHON_BIN}")" || die \
            "PYTHON_BIN não aponta para um executável válido: ${PYTHON_BIN}"

        printf '%s\n' "${candidate}"
        return 0
    fi

    # 2. Ambiente virtual já ativado.
    if [[ -n "${VIRTUAL_ENV:-}" ]]; then
        candidate="${VIRTUAL_ENV}/bin/python"

        if [[ -x "${candidate}" ]]; then
            printf '%s\n' "${candidate}"
            return 0
        fi
    fi

    # 3. Ambiente Conda já ativado.
    if [[ -n "${CONDA_PREFIX:-}" ]]; then
        candidate="${CONDA_PREFIX}/bin/python"

        if [[ -x "${candidate}" ]]; then
            printf '%s\n' "${candidate}"
            return 0
        fi
    fi

    # 4. Ambiente virtual configurado para o projeto.
    configured_venv="$(
        resolve_venv_directory "${VENV_DIR:-venv}"
    )"
    candidate="${configured_venv}/bin/python"

    if [[ -x "${candidate}" ]]; then
        printf '%s\n' "${candidate}"
        return 0
    fi

    # 5. Alternativas convencionais.
    for candidate in \
        "${PROJECT_ROOT}/venv/bin/python" \
        "${PROJECT_ROOT}/.venv/bin/python"
    do
        if [[ -x "${candidate}" ]]; then
            printf '%s\n' "${candidate}"
            return 0
        fi
    done

    # 6. Python disponível no PATH.
    if command -v python3 >/dev/null 2>&1; then
        command -v python3
        return 0
    fi

    if command -v python >/dev/null 2>&1; then
        command -v python
        return 0
    fi

    die "Nenhum interpretador Python foi encontrado."
}


append_csv_arguments() {
    local option_name="$1"
    local raw_values="$2"
    local values=()
    local value=""

    [[ -n "${raw_values}" ]] || return 0

    IFS=',' read -r -a values <<< "${raw_values}"

    for value in "${values[@]}"; do
        value="$(trim_value "${value}")"

        if [[ -n "${value}" ]]; then
            RUNNER_ARGUMENTS+=(
                "${option_name}"
                "${value}"
            )
        fi
    done
}


append_boolean_override() {
    local raw_value="$1"
    local true_option="$2"
    local false_option="${3:-}"
    local normalized=""

    normalized="$(normalize_lowercase "${raw_value}")"

    case "${normalized}" in
        ""|auto|default|yaml)
            return 0
            ;;
    esac

    if is_true "${normalized}"; then
        RUNNER_ARGUMENTS+=("${true_option}")
        return 0
    fi

    if is_false "${normalized}"; then
        if [[ -n "${false_option}" ]]; then
            RUNNER_ARGUMENTS+=("${false_option}")
        fi
        return 0
    fi

    die \
        "Valor booleano inválido: ${raw_value}. " \
        "Use true, false ou auto."
}


print_command() {
    printf '[%s] [%s] Comando:' \
        "$(timestamp)" \
        "${SERVICE_NAME}"

    printf ' %q' "$@"
    printf '\n'
}


# ==============================================================================
# VALIDAÇÃO DOS ARQUIVOS ESSENCIAIS
# ==============================================================================

[[ -f "${PROJECT_ROOT}/pipeline/runner.py" ]] || die \
    "Arquivo principal não encontrado: ${PROJECT_ROOT}/pipeline/runner.py"

[[ -f "${PROJECT_ROOT}/pipeline/__init__.py" ]] || die \
    "Pacote pipeline incompleto: ${PROJECT_ROOT}/pipeline/__init__.py"

EXPERIMENT_CONFIG_INPUT="${EXPERIMENT_CONFIG:-configs/experiment.yaml}"

EXPERIMENT_CONFIG_RESOLVED="$(
    resolve_project_path "${EXPERIMENT_CONFIG_INPUT}"
)"

[[ -f "${EXPERIMENT_CONFIG_RESOLVED}" ]] || die \
    "Arquivo de experimento não encontrado: ${EXPERIMENT_CONFIG_RESOLVED}"

[[ -r "${EXPERIMENT_CONFIG_RESOLVED}" ]] || die \
    "Arquivo de experimento sem permissão de leitura: " \
    "${EXPERIMENT_CONFIG_RESOLVED}"


# ==============================================================================
# SELEÇÃO E VALIDAÇÃO DO PYTHON
# ==============================================================================

PYTHON_EXECUTABLE="$(resolve_python)"

[[ -x "${PYTHON_EXECUTABLE}" ]] || die \
    "Python selecionado não é executável: ${PYTHON_EXECUTABLE}"

"${PYTHON_EXECUTABLE}" - \
    "${MINIMUM_PYTHON_MAJOR}" \
    "${MINIMUM_PYTHON_MINOR}" \
    <<'PYTHON_VERSION_CHECK'
from __future__ import annotations

import sys

minimum = (int(sys.argv[1]), int(sys.argv[2]))
current = sys.version_info[:2]

if current < minimum:
    raise SystemExit(
        "Python incompatível. "
        f"Mínimo: {minimum[0]}.{minimum[1]}. "
        f"Encontrado: {sys.version.split()[0]}"
    )
PYTHON_VERSION_CHECK


# ==============================================================================
# VARIÁVEIS DE AMBIENTE
# ==============================================================================

export PYTHONPATH="${PROJECT_ROOT}${PYTHONPATH:+:${PYTHONPATH}}"
export PYTHONUNBUFFERED="${PYTHONUNBUFFERED:-1}"
export PYTHONIOENCODING="${PYTHONIOENCODING:-utf-8}"

export TOKENIZERS_PARALLELISM="${TOKENIZERS_PARALLELISM:-false}"
export TRANSFORMERS_OFFLINE="${TRANSFORMERS_OFFLINE:-1}"
export HF_HUB_OFFLINE="${HF_HUB_OFFLINE:-1}"
export HF_HUB_DISABLE_TELEMETRY="${HF_HUB_DISABLE_TELEMETRY:-1}"

# ==============================================================================
# THREADS DE CPU
# ==============================================================================

DEFAULT_CPU_THREADS="${SLURM_CPUS_PER_TASK:-1}"

if [[ ! "${DEFAULT_CPU_THREADS}" =~ ^[1-9][0-9]*$ ]]; then
    warning \
        "SLURM_CPUS_PER_TASK não é um inteiro positivo: " \
        "${DEFAULT_CPU_THREADS}. Usando 1."

    DEFAULT_CPU_THREADS="1"
fi

export OMP_NUM_THREADS="${OMP_NUM_THREADS:-${DEFAULT_CPU_THREADS}}"
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-${OMP_NUM_THREADS}}"
export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-${OMP_NUM_THREADS}}"
export NUMEXPR_NUM_THREADS="${NUMEXPR_NUM_THREADS:-${OMP_NUM_THREADS}}"


# ==============================================================================
# VALIDAÇÃO DAS DEPENDÊNCIAS
# ==============================================================================
#
# Esta validação pode ser ignorada de forma explícita:
#
#   SKIP_DEPENDENCY_CHECK=1 ./scripts/run_service.sh
#
# Ela não instala pacotes. Para instalar ou atualizar o ambiente, use:
#
#   ./scripts/setup_env.sh
# ==============================================================================

if ! is_true "${SKIP_DEPENDENCY_CHECK:-false}"; then
    "${PYTHON_EXECUTABLE}" - <<'PYTHON_DEPENDENCY_CHECK'
from __future__ import annotations

import importlib.util

required_modules = {
    "numpy": "numpy",
    "pandas": "pandas",
    "yaml": "PyYAML",
    "torch": "torch",
    "transformers": "transformers",
    "sklearn": "scikit-learn",
}

missing = [
    package_name
    for module_name, package_name in required_modules.items()
    if importlib.util.find_spec(module_name) is None
]

if missing:
    raise SystemExit(
        "Dependências ausentes: "
        + ", ".join(missing)
        + ". Execute ./scripts/setup_env.sh."
    )

if importlib.util.find_spec("pipeline.runner") is None:
    raise SystemExit(
        "O módulo pipeline.runner não foi encontrado no PYTHONPATH."
    )
PYTHON_DEPENDENCY_CHECK
fi


# O hash seed precisa existir antes de o processo do runner iniciar.
# Quando não for informado, tenta usar experiment.random_seed.
if [[ -z "${PYTHONHASHSEED:-}" ]]; then
    RESOLVED_HASH_SEED="$(
        "${PYTHON_EXECUTABLE}" \
            - "${EXPERIMENT_CONFIG_RESOLVED}" \
            <<'PYTHON_SEED_RESOLUTION'
from __future__ import annotations

import sys
from pathlib import Path

import yaml

config_path = Path(sys.argv[1])

try:
    content = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    experiment = (
        content.get("experiment", {})
        if isinstance(content, dict)
        else {}
    )
    seed = int(experiment.get("random_seed", 42))

    if seed < 0:
        raise ValueError
except Exception:
    seed = 42

print(seed)
PYTHON_SEED_RESOLUTION
    )"

    export PYTHONHASHSEED="${RESOLVED_HASH_SEED}"
fi


# ==============================================================================
# MONTAGEM DOS ARGUMENTOS DO RUNNER
# ==============================================================================

RUNNER_ARGUMENTS=(
    "--project-root"
    "${PROJECT_ROOT}"
    "--experiment-config"
    "${EXPERIMENT_CONFIG_RESOLVED}"
)

# Seleções temporárias por variáveis de ambiente.
append_csv_arguments \
    "--model" \
    "${MODEL_KEYS:-}"

append_csv_arguments \
    "--dataset" \
    "${DATASET_KEYS:-}"

# Sobrescrita temporária do ambiente.
if [[ -n "${EXECUTION_ENVIRONMENT:-}" ]]; then
    EXECUTION_ENVIRONMENT_NORMALIZED="$(
        normalize_lowercase "${EXECUTION_ENVIRONMENT}"
    )"

    case "${EXECUTION_ENVIRONMENT_NORMALIZED}" in
        local|sdumont)
            RUNNER_ARGUMENTS+=(
                "--environment"
                "${EXECUTION_ENVIRONMENT_NORMALIZED}"
            )
            ;;
        *)
            die \
                "EXECUTION_ENVIRONMENT precisa ser local ou sdumont. " \
                "Recebido: ${EXECUTION_ENVIRONMENT}"
            ;;
    esac
fi

if [[ -n "${RUN_ID:-}" ]]; then
    RUNNER_ARGUMENTS+=(
        "--run-id"
        "${RUN_ID}"
    )
fi

if [[ -n "${LOG_LEVEL:-}" ]]; then
    LOG_LEVEL_NORMALIZED="$(
        printf '%s' "${LOG_LEVEL}" |
            tr '[:lower:]' '[:upper:]'
    )"

    case "${LOG_LEVEL_NORMALIZED}" in
        DEBUG|INFO|WARNING|ERROR|CRITICAL)
            RUNNER_ARGUMENTS+=(
                "--log-level"
                "${LOG_LEVEL_NORMALIZED}"
            )
            ;;
        *)
            die \
                "LOG_LEVEL inválido: ${LOG_LEVEL}. " \
                "Use DEBUG, INFO, WARNING, ERROR ou CRITICAL."
            ;;
    esac
fi

# DRY_RUN vazio/auto mantém o valor do YAML.
# true força dry-run e false força execução real.
append_boolean_override \
    "${DRY_RUN:-auto}" \
    "--dry-run" \
    "--no-dry-run"

append_boolean_override \
    "${TRACEBACK:-false}" \
    "--traceback"

append_boolean_override \
    "${PRINT_SUMMARY_JSON:-false}" \
    "--print-summary-json"

# Os argumentos fornecidos diretamente têm precedência por serem adicionados
# ao final. Para --model e --dataset, múltiplas ocorrências são acumuladas.
if [[ "$#" -gt 0 ]]; then
    RUNNER_ARGUMENTS+=("$@")
fi

RUNNER_COMMAND=(
    "${PYTHON_EXECUTABLE}"
    "-m"
    "pipeline.runner"
    "${RUNNER_ARGUMENTS[@]}"
)


# ==============================================================================
# INFORMAÇÕES DA EXECUÇÃO
# ==============================================================================

log "Raiz do projeto: ${PROJECT_ROOT}"
log "Diretório atual: $(pwd -P)"
log "Python: ${PYTHON_EXECUTABLE}"
log "Versão do Python: $("${PYTHON_EXECUTABLE}" --version 2>&1)"
log "Arquivo do experimento: ${EXPERIMENT_CONFIG_RESOLVED}"
log "Hostname: $(hostname 2>/dev/null || printf 'desconhecido')"
log "PYTHONHASHSEED: ${PYTHONHASHSEED}"
log "OMP_NUM_THREADS: ${OMP_NUM_THREADS}"

if [[ -n "${VIRTUAL_ENV:-}" ]]; then
    log "Ambiente virtual ativo: ${VIRTUAL_ENV}"
elif [[ -n "${CONDA_PREFIX:-}" ]]; then
    log "Ambiente Conda ativo: ${CONDA_PREFIX}"
elif [[ "${PYTHON_EXECUTABLE}" == "${PROJECT_ROOT}/venv/bin/python" ]]; then
    log "Ambiente virtual do projeto: ${PROJECT_ROOT}/venv"
elif [[ "${PYTHON_EXECUTABLE}" == "${PROJECT_ROOT}/.venv/bin/python" ]]; then
    log "Ambiente virtual do projeto: ${PROJECT_ROOT}/.venv"
else
    warning "A execução está utilizando um Python fora do venv padrão."
fi

if [[ -n "${SLURM_JOB_ID:-}" ]]; then
    log "Job Slurm: ${SLURM_JOB_ID}"
    log "Nome do job: ${SLURM_JOB_NAME:-não informado}"
    log "Nós: ${SLURM_NODELIST:-não informado}"
    log "Quantidade de nós: ${SLURM_NNODES:-não informado}"
    log "Quantidade de tarefas: ${SLURM_NTASKS:-não informado}"
    log "CPUs por tarefa: ${SLURM_CPUS_PER_TASK:-não informado}"
    log "GPUs do job: ${SLURM_JOB_GPUS:-${SLURM_GPUS:-não informado}}"
fi

if [[ -n "${CUDA_VISIBLE_DEVICES:-}" ]]; then
    log "CUDA_VISIBLE_DEVICES: ${CUDA_VISIBLE_DEVICES}"
fi

print_command "${RUNNER_COMMAND[@]}"


# ==============================================================================
# EXECUÇÃO
# ==============================================================================

SERVICE_STARTED_AT="$(date +%s)"

set +e

"${RUNNER_COMMAND[@]}" &
CHILD_PID=$!

wait "${CHILD_PID}"
SERVICE_EXIT_CODE=$?

CHILD_PID=""

set -e

SERVICE_FINISHED_AT="$(date +%s)"
SERVICE_DURATION_SECONDS=$((SERVICE_FINISHED_AT - SERVICE_STARTED_AT))

if [[ "${SERVICE_EXIT_CODE}" -eq 0 ]]; then
    log \
        "Pipeline concluída com sucesso em " \
        "${SERVICE_DURATION_SECONDS} segundo(s)."
else
    error \
        "Pipeline concluída com código ${SERVICE_EXIT_CODE} após " \
        "${SERVICE_DURATION_SECONDS} segundo(s)."
fi

exit "${SERVICE_EXIT_CODE}"
