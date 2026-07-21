#!/usr/bin/env bash

# ==============================================================================
# SINCRONIZAÇÃO DO PROJETO COM O SCRATCH DO SANTOS DUMONT
# ==============================================================================
#
# Envia a cópia local do projeto para o diretório remoto configurado em:
#
#   configs/sdumont.env
#
# Uso normal:
#
#   ./scripts/sync_to_scratch.sh \
#       --config configs/sdumont.env \
#       --experiment-config configs/experiment.yaml
#
# Apenas visualizar os comandos:
#
#   ./scripts/sync_to_scratch.sh \
#       --config configs/sdumont.env \
#       --experiment-config configs/experiment.yaml \
#       --print-only
#
# Este script:
#
# - valida a configuração privada;
# - deriva os caminhos remotos;
# - testa a conexão SSH;
# - cria os diretórios necessários no Scratch;
# - sincroniza o projeto com rsync sobre SSH;
# - exclui ambientes virtuais, caches, resultados locais e dados privados;
# - preserva permissões dos scripts;
# - valida a cópia remota após a transferência.
#
# Ele não prepara o ambiente Python remoto e não submete jobs.
# Essas responsabilidades pertencem a:
#
#   scripts/setup_sdumont_env.sh
#   scripts/submit_sdumont.sh
# ==============================================================================

set -Eeuo pipefail
IFS=$'\n\t'


# ==============================================================================
# CONSTANTES E ESTADO
# ==============================================================================

readonly SCRIPT_NAME="sync_to_scratch"
readonly EXPECTED_CONFIG_SCHEMA_VERSION="2.0"
readonly DEFAULT_CONFIG_FILE="configs/sdumont.env"
readonly DEFAULT_EXPERIMENT_CONFIG="configs/experiment.yaml"

CONFIG_INPUT="${SDUMONT_CONFIG:-${DEFAULT_CONFIG_FILE}}"
EXPERIMENT_CONFIG_INPUT="${EXPERIMENT_CONFIG:-${DEFAULT_EXPERIMENT_CONFIG}}"

PRINT_ONLY=false
RSYNC_DRY_RUN=false
VERBOSE=false
SKIP_CONNECTIVITY_CHECK=false
SKIP_REMOTE_VALIDATION=false

DELETE_OVERRIDE=""
SYNC_MODEL_STORE_OVERRIDE=""
SYNC_DATASETS_OVERRIDE=""
SYNC_OUTPUTS_OVERRIDE=""
SYNC_LOGS_OVERRIDE=""
CHECKSUM_OVERRIDE=""

REMOTE_PROJECT_DIR_OVERRIDE=""

CHILD_PID=""
TEMP_EXCLUDE_FILE=""


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
        "${SCRIPT_NAME}" \
        "${message}"
}


warning() {
    local message=""
    printf -v message '%s' "$@"

    printf '[%s] [%s] AVISO: %s\n' \
        "$(timestamp)" \
        "${SCRIPT_NAME}" \
        "${message}" \
        >&2
}


error() {
    local message=""
    printf -v message '%s' "$@"

    printf '[%s] [%s] ERRO: %s\n' \
        "$(timestamp)" \
        "${SCRIPT_NAME}" \
        "${message}" \
        >&2
}


die() {
    error "$*"
    exit 1
}


print_command() {
    printf '[%s] [%s] Comando:' \
        "$(timestamp)" \
        "${SCRIPT_NAME}"

    printf ' %q' "$@"
    printf '\n'
}


# ==============================================================================
# ERROS, LIMPEZA E SINAIS
# ==============================================================================

cleanup() {
    if [[ -n "${TEMP_EXCLUDE_FILE}" ]]; then
        rm -f -- "${TEMP_EXCLUDE_FILE}" 2>/dev/null || true
        TEMP_EXCLUDE_FILE=""
    fi
}


on_error() {
    local exit_code=$?
    local line_number="${BASH_LINENO[0]:-desconhecida}"
    local failed_command="${BASH_COMMAND:-desconhecido}"

    trap - ERR

    error "A sincronização foi interrompida."
    error "Código de saída: ${exit_code}"
    error "Linha aproximada: ${line_number}"
    error "Comando: ${failed_command}"

    cleanup
    exit "${exit_code}"
}


forward_signal() {
    local signal_name="$1"

    if [[ -z "${CHILD_PID}" ]]; then
        return 0
    fi

    if kill -0 "${CHILD_PID}" 2>/dev/null; then
        warning \
            "Encaminhando ${signal_name} ao processo filho " \
            "(PID ${CHILD_PID})."

        kill "-${signal_name}" "${CHILD_PID}" 2>/dev/null || true
    fi
}


trap cleanup EXIT
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
# AJUDA
# ==============================================================================

show_help() {
    cat <<'HELP'
Uso:
  ./scripts/sync_to_scratch.sh [opções]

Obrigatórias no uso normal:
  --config ARQUIVO              Configuração privada do SDumont.
  --experiment-config ARQUIVO   Configuração do experimento a sincronizar.

Caminhos:
  --remote-project-dir CAMINHO  Substitui REMOTE_PROJECT_DIR nesta execução.

Conteúdo:
  --delete                      Remove do destino arquivos ausentes localmente.
  --no-delete                   Desativa a remoção remota.
  --model-store                 Inclui model_store/.
  --no-model-store              Exclui model_store/.
  --datasets                    Inclui datasets/.
  --no-datasets                 Exclui datasets/.
  --outputs                     Inclui outputs/.
  --no-outputs                  Exclui outputs/.
  --logs                        Inclui logs/.
  --no-logs                     Exclui logs/.
  --checksum                    Compara arquivos por checksum.
  --no-checksum                 Usa tamanho e data de modificação.

Validação e execução:
  --skip-connectivity-check     Não executa o teste SSH inicial.
  --skip-remote-validation      Não valida os arquivos após o rsync.
  --rsync-dry-run               Executa rsync com --dry-run.
  --print-only                  Apenas imprime os comandos.
  --verbose                     Ativa saída detalhada.
  -h, --help                    Exibe esta ajuda.

Exemplos:
  ./scripts/sync_to_scratch.sh \
    --config configs/sdumont.env \
    --experiment-config configs/experiment.yaml

  ./scripts/sync_to_scratch.sh \
    --config configs/sdumont.env \
    --experiment-config configs/experiment.yaml \
    --print-only

  ./scripts/sync_to_scratch.sh \
    --config configs/sdumont.env \
    --experiment-config configs/experiment.yaml \
    --no-model-store \
    --no-datasets
HELP
}


# ==============================================================================
# FUNÇÕES AUXILIARES
# ==============================================================================

normalize_lowercase() {
    printf '%s' "${1:-}" | tr '[:upper:]' '[:lower:]'
}


trim_value() {
    local value="$1"

    value="${value#"${value%%[![:space:]]*}"}"
    value="${value%"${value##*[![:space:]]}"}"

    printf '%s\n' "${value}"
}


is_true() {
    local value=""

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
    local value=""

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


normalize_boolean() {
    local value="$1"
    local field_name="$2"

    if is_true "${value}"; then
        printf 'true\n'
        return 0
    fi

    if is_false "${value}"; then
        printf 'false\n'
        return 0
    fi

    die \
        "${field_name} precisa ser true ou false. " \
        "Recebido: ${value}"
}


resolve_project_path() {
    local value="$1"

    [[ -n "${value}" ]] || return 1

    if [[ "${value}" = /* ]]; then
        printf '%s\n' "${value}"
    else
        printf '%s\n' "${PROJECT_ROOT}/${value}"
    fi
}


canonical_existing_file() {
    local value="$1"
    local path=""
    local directory=""
    local filename=""

    path="$(resolve_project_path "${value}")" || return 1

    [[ -f "${path}" ]] || return 1

    directory="$(
        cd -- "$(dirname -- "${path}")" >/dev/null 2>&1
        pwd -P
    )"
    filename="$(basename -- "${path}")"

    printf '%s/%s\n' "${directory}" "${filename}"
}


relative_project_path() {
    local absolute_path="$1"

    case "${absolute_path}" in
        "${PROJECT_ROOT}")
            printf '.\n'
            ;;
        "${PROJECT_ROOT}/"*)
            printf '%s\n' "${absolute_path#"${PROJECT_ROOT}/"}"
            ;;
        *)
            return 1
            ;;
    esac
}


require_non_empty() {
    local value="$1"
    local field_name="$2"

    [[ -n "$(trim_value "${value}")" ]] || die \
        "${field_name} precisa ser preenchido em ${CONFIG_PATH}."
}


require_positive_integer() {
    local value="$1"
    local field_name="$2"

    [[ "${value}" =~ ^[1-9][0-9]*$ ]] || die \
        "${field_name} precisa ser um inteiro positivo. " \
        "Recebido: ${value}"
}


require_non_negative_integer() {
    local value="$1"
    local field_name="$2"

    [[ "${value}" =~ ^[0-9]+$ ]] || die \
        "${field_name} precisa ser um inteiro não negativo. " \
        "Recebido: ${value}"
}


validate_remote_path() {
    local value="$1"
    local field_name="$2"

    require_non_empty "${value}" "${field_name}"

    if is_true "${REQUIRE_ABSOLUTE_REMOTE_PATHS}"; then
        [[ "${value}" = /* ]] || die \
            "${field_name} precisa ser absoluto: ${value}"
    fi

    case "${value}" in
        "/"|"/home"|"/scratch"|"/tmp")
            die \
                "${field_name} é amplo demais e não pode ser usado: " \
                "${value}"
            ;;
    esac

    [[ "${value}" != *$'\n'* ]] || die \
        "${field_name} não pode conter quebra de linha."

    [[ "${value}" != *$'\r'* ]] || die \
        "${field_name} não pode conter retorno de carro."

    [[ "${value}" != *$'\t'* ]] || die \
        "${field_name} não pode conter tabulação."

    [[ "${value}" != *" "* ]] || die \
        "${field_name} não pode conter espaços: ${value}"
}


path_is_under() {
    local child="$1"
    local parent="$2"
    local normalized_parent="${parent%/}"

    [[ "${child}" == "${normalized_parent}" ]] && return 0
    [[ "${child}" == "${normalized_parent}/"* ]]
}


shell_join() {
    local output=""
    local item=""
    local quoted=""

    for item in "$@"; do
        printf -v quoted '%q' "${item}"

        if [[ -n "${output}" ]]; then
            output+=" "
        fi

        output+="${quoted}"
    done

    printf '%s\n' "${output}"
}


split_literal_options() {
    local raw="$1"
    local destination_name="$2"
    local -n destination="${destination_name}"
    local parsed=()

    [[ -n "$(trim_value "${raw}")" ]] || return 0

    # Esta divisão é deliberadamente literal. Aspas internas não são
    # interpretadas para evitar eval e execução acidental de conteúdo.
    read -r -a parsed <<< "${raw}"

    destination+=("${parsed[@]}")
}


append_csv_excludes() {
    local raw="$1"
    local values=()
    local value=""

    [[ -n "$(trim_value "${raw}")" ]] || return 0

    IFS=',' read -r -a values <<< "${raw}"

    for value in "${values[@]}"; do
        value="$(trim_value "${value}")"

        [[ -n "${value}" ]] || continue

        [[ "${value}" != *$'\n'* ]] || die \
            "SYNC_EXTRA_EXCLUDES contém valor inválido."

        printf '%s\n' "${value}" >> "${TEMP_EXCLUDE_FILE}"
    done
}


run_child() {
    local command=("$@")
    local exit_code=0

    print_command "${command[@]}"

    if [[ "${PRINT_ONLY}" == true ]]; then
        return 0
    fi

    set +e

    "${command[@]}" &
    CHILD_PID=$!

    wait "${CHILD_PID}"
    exit_code=$?

    CHILD_PID=""

    set -e

    return "${exit_code}"
}


run_ssh_command() {
    local remote_command="$1"
    local command=(
        "${SSH_COMMAND_PATH}"
        "${SSH_ARGUMENTS[@]}"
        "${SSH_TARGET}"
        "${REMOTE_SHELL}"
        "-lc"
        "${remote_command}"
    )

    run_child "${command[@]}"
}


write_exclude_file() {
    TEMP_EXCLUDE_FILE="$(
        mktemp \
            "${PROJECT_ROOT}/.tmp/sdumont/rsync-excludes.XXXXXX"
    )"

    cat > "${TEMP_EXCLUDE_FILE}" <<'EXCLUDES'
.git/
venv/
.venv/
__pycache__/
*.py[cod]
*$py.class
.pytest_cache/
.mypy_cache/
.ruff_cache/
.pyright/
.coverage
htmlcov/
.ipynb_checkpoints/
.DS_Store
Thumbs.db
.tmp/
configs/sdumont.env
EXCLUDES

    if [[ "${SYNC_MODEL_STORE_EFFECTIVE}" == false ]]; then
        printf 'model_store/\n' >> "${TEMP_EXCLUDE_FILE}"
    fi

    if [[ "${SYNC_DATASETS_EFFECTIVE}" == false ]]; then
        printf 'datasets/\n' >> "${TEMP_EXCLUDE_FILE}"
    fi

    if [[ "${SYNC_OUTPUTS_EFFECTIVE}" == false ]]; then
        printf 'outputs/\n' >> "${TEMP_EXCLUDE_FILE}"
    fi

    if [[ "${SYNC_LOGS_EFFECTIVE}" == false ]]; then
        printf 'logs/\n' >> "${TEMP_EXCLUDE_FILE}"
    fi

    append_csv_excludes "${SYNC_EXTRA_EXCLUDES}"

    if [[ "${VERBOSE}" == true ]]; then
        log "Exclusões aplicadas pelo rsync:"
        sed 's/^/  - /' "${TEMP_EXCLUDE_FILE}"
    fi
}


resolve_command_path() {
    local command_name="$1"
    local field_name="$2"

    if [[ "${PRINT_ONLY}" == true ]]; then
        printf '%s\n' "${command_name}"
        return 0
    fi

    if [[ "${command_name}" == */* ]]; then
        [[ -x "${command_name}" ]] || die \
            "${field_name} não é executável: ${command_name}"

        printf '%s\n' "${command_name}"
        return 0
    fi

    command -v "${command_name}" 2>/dev/null || die \
        "${field_name} não foi encontrado no PATH: ${command_name}"
}


# ==============================================================================
# ARGUMENTOS
# ==============================================================================

while [[ "$#" -gt 0 ]]; do
    case "$1" in
        --config)
            [[ "$#" -ge 2 ]] || die \
                "--config exige um arquivo."

            CONFIG_INPUT="$2"
            shift 2
            ;;

        --config=*)
            CONFIG_INPUT="${1#*=}"
            shift
            ;;

        --experiment-config)
            [[ "$#" -ge 2 ]] || die \
                "--experiment-config exige um arquivo."

            EXPERIMENT_CONFIG_INPUT="$2"
            shift 2
            ;;

        --experiment-config=*)
            EXPERIMENT_CONFIG_INPUT="${1#*=}"
            shift
            ;;

        --remote-project-dir)
            [[ "$#" -ge 2 ]] || die \
                "--remote-project-dir exige um caminho."

            REMOTE_PROJECT_DIR_OVERRIDE="$2"
            shift 2
            ;;

        --remote-project-dir=*)
            REMOTE_PROJECT_DIR_OVERRIDE="${1#*=}"
            shift
            ;;

        --delete)
            DELETE_OVERRIDE="true"
            shift
            ;;

        --no-delete)
            DELETE_OVERRIDE="false"
            shift
            ;;

        --model-store)
            SYNC_MODEL_STORE_OVERRIDE="true"
            shift
            ;;

        --no-model-store)
            SYNC_MODEL_STORE_OVERRIDE="false"
            shift
            ;;

        --datasets)
            SYNC_DATASETS_OVERRIDE="true"
            shift
            ;;

        --no-datasets)
            SYNC_DATASETS_OVERRIDE="false"
            shift
            ;;

        --outputs)
            SYNC_OUTPUTS_OVERRIDE="true"
            shift
            ;;

        --no-outputs)
            SYNC_OUTPUTS_OVERRIDE="false"
            shift
            ;;

        --logs)
            SYNC_LOGS_OVERRIDE="true"
            shift
            ;;

        --no-logs)
            SYNC_LOGS_OVERRIDE="false"
            shift
            ;;

        --checksum)
            CHECKSUM_OVERRIDE="true"
            shift
            ;;

        --no-checksum)
            CHECKSUM_OVERRIDE="false"
            shift
            ;;

        --skip-connectivity-check)
            SKIP_CONNECTIVITY_CHECK=true
            shift
            ;;

        --skip-remote-validation)
            SKIP_REMOTE_VALIDATION=true
            shift
            ;;

        --rsync-dry-run)
            RSYNC_DRY_RUN=true
            shift
            ;;

        --print-only)
            PRINT_ONLY=true
            shift
            ;;

        --verbose)
            VERBOSE=true
            shift
            ;;

        -h|--help)
            show_help
            exit 0
            ;;

        --)
            shift

            if [[ "$#" -gt 0 ]]; then
                die \
                    "Argumentos após -- não são suportados: $*"
            fi
            ;;

        -*)
            die "Opção desconhecida: $1"
            ;;

        *)
            die "Argumento posicional não suportado: $1"
            ;;
    esac
done


# ==============================================================================
# CARREGAMENTO DA CONFIGURAÇÃO
# ==============================================================================

CONFIG_PATH="$(canonical_existing_file "${CONFIG_INPUT}")" || die \
    "Configuração do SDumont não encontrada: ${CONFIG_INPUT}"

EXPERIMENT_CONFIG_PATH="$(
    canonical_existing_file "${EXPERIMENT_CONFIG_INPUT}"
)" || die \
    "Arquivo do experimento não encontrado: ${EXPERIMENT_CONFIG_INPUT}"

EXPERIMENT_CONFIG_RELATIVE="$(
    relative_project_path "${EXPERIMENT_CONFIG_PATH}"
)" || die \
    "O arquivo do experimento precisa estar dentro do projeto: " \
    "${EXPERIMENT_CONFIG_PATH}"

# shellcheck disable=SC1090
source "${CONFIG_PATH}"

: "${SDUMONT_CONFIG_SCHEMA_VERSION:=}"
: "${USERNAME:=}"
: "${LOGIN_HOST:=}"
: "${ACCOUNT:=}"
: "${PARTITION:=}"
: "${SCRATCH_DIR:=}"
: "${PYTHON_MODULE:=}"

: "${SSH_PORT:=22}"
: "${SSH_IDENTITY_FILE:=}"
: "${SSH_PROXY_JUMP:=}"
: "${SSH_CONTROL_PATH:=}"
: "${SSH_CONNECT_TIMEOUT_SECONDS:=20}"
: "${SSH_SERVER_ALIVE_INTERVAL_SECONDS:=30}"
: "${SSH_SERVER_ALIVE_COUNT_MAX:=3}"
: "${SSH_BATCH_MODE:=true}"
: "${SSH_STRICT_HOST_KEY_CHECKING:=accept-new}"
: "${SSH_KNOWN_HOSTS_FILE:=}"
: "${SSH_EXTRA_OPTIONS:=}"

: "${REMOTE_PROJECT_NAME:=financial-sentiment-lab}"
: "${REMOTE_PROJECT_DIR:=}"
: "${REMOTE_VENV_DIR:=}"
: "${REMOTE_PIP_CACHE_DIR:=}"
: "${REMOTE_HF_HOME:=}"
: "${REMOTE_OUTPUT_DIR:=}"
: "${REMOTE_LOG_DIR:=}"
: "${REMOTE_TEMP_DIR:=}"

: "${RSYNC_COMMAND:=rsync}"
: "${SYNC_DELETE:=false}"
: "${SYNC_MODEL_STORE:=true}"
: "${SYNC_DATASETS:=true}"
: "${SYNC_OUTPUTS:=false}"
: "${SYNC_LOGS:=false}"
: "${SYNC_PARTIAL:=true}"
: "${SYNC_COMPRESS:=true}"
: "${SYNC_PROGRESS:=true}"
: "${SYNC_CHECKSUM:=false}"
: "${SYNC_BWLIMIT_KBPS:=0}"
: "${SYNC_EXTRA_EXCLUDES:=}"

: "${REQUIRE_ABSOLUTE_REMOTE_PATHS:=true}"
: "${REQUIRE_REMOTE_PATH_UNDER_SCRATCH:=true}"
: "${VALIDATE_REMOTE_PROJECT:=true}"

: "${SSH_COMMAND:=ssh}"
: "${REMOTE_SHELL:=bash}"


# ==============================================================================
# VALIDAÇÃO DA CONFIGURAÇÃO
# ==============================================================================

[[ "${SDUMONT_CONFIG_SCHEMA_VERSION}" == \
    "${EXPECTED_CONFIG_SCHEMA_VERSION}" ]] || die \
    "Versão de configs/sdumont.env incompatível. " \
    "Esperada: ${EXPECTED_CONFIG_SCHEMA_VERSION}; " \
    "recebida: ${SDUMONT_CONFIG_SCHEMA_VERSION:-vazia}."

for required_pair in \
    "USERNAME:${USERNAME}" \
    "LOGIN_HOST:${LOGIN_HOST}" \
    "ACCOUNT:${ACCOUNT}" \
    "PARTITION:${PARTITION}" \
    "SCRATCH_DIR:${SCRATCH_DIR}" \
    "PYTHON_MODULE:${PYTHON_MODULE}"
do
    field_name="${required_pair%%:*}"
    field_value="${required_pair#*:}"
    require_non_empty "${field_value}" "${field_name}"
done

require_positive_integer \
    "${SSH_PORT}" \
    "SSH_PORT"

require_positive_integer \
    "${SSH_CONNECT_TIMEOUT_SECONDS}" \
    "SSH_CONNECT_TIMEOUT_SECONDS"

require_positive_integer \
    "${SSH_SERVER_ALIVE_INTERVAL_SECONDS}" \
    "SSH_SERVER_ALIVE_INTERVAL_SECONDS"

require_non_negative_integer \
    "${SSH_SERVER_ALIVE_COUNT_MAX}" \
    "SSH_SERVER_ALIVE_COUNT_MAX"

require_non_negative_integer \
    "${SYNC_BWLIMIT_KBPS}" \
    "SYNC_BWLIMIT_KBPS"

SSH_BATCH_MODE="$(normalize_boolean "${SSH_BATCH_MODE}" "SSH_BATCH_MODE")"
SYNC_DELETE="$(normalize_boolean "${SYNC_DELETE}" "SYNC_DELETE")"
SYNC_MODEL_STORE="$(
    normalize_boolean "${SYNC_MODEL_STORE}" "SYNC_MODEL_STORE"
)"
SYNC_DATASETS="$(normalize_boolean "${SYNC_DATASETS}" "SYNC_DATASETS")"
SYNC_OUTPUTS="$(normalize_boolean "${SYNC_OUTPUTS}" "SYNC_OUTPUTS")"
SYNC_LOGS="$(normalize_boolean "${SYNC_LOGS}" "SYNC_LOGS")"
SYNC_PARTIAL="$(normalize_boolean "${SYNC_PARTIAL}" "SYNC_PARTIAL")"
SYNC_COMPRESS="$(normalize_boolean "${SYNC_COMPRESS}" "SYNC_COMPRESS")"
SYNC_PROGRESS="$(normalize_boolean "${SYNC_PROGRESS}" "SYNC_PROGRESS")"
SYNC_CHECKSUM="$(normalize_boolean "${SYNC_CHECKSUM}" "SYNC_CHECKSUM")"
REQUIRE_ABSOLUTE_REMOTE_PATHS="$(
    normalize_boolean \
        "${REQUIRE_ABSOLUTE_REMOTE_PATHS}" \
        "REQUIRE_ABSOLUTE_REMOTE_PATHS"
)"
REQUIRE_REMOTE_PATH_UNDER_SCRATCH="$(
    normalize_boolean \
        "${REQUIRE_REMOTE_PATH_UNDER_SCRATCH}" \
        "REQUIRE_REMOTE_PATH_UNDER_SCRATCH"
)"
VALIDATE_REMOTE_PROJECT="$(
    normalize_boolean \
        "${VALIDATE_REMOTE_PROJECT}" \
        "VALIDATE_REMOTE_PROJECT"
)"

if [[ -n "${DELETE_OVERRIDE}" ]]; then
    SYNC_DELETE="${DELETE_OVERRIDE}"
fi

if [[ -n "${SYNC_MODEL_STORE_OVERRIDE}" ]]; then
    SYNC_MODEL_STORE="${SYNC_MODEL_STORE_OVERRIDE}"
fi

if [[ -n "${SYNC_DATASETS_OVERRIDE}" ]]; then
    SYNC_DATASETS="${SYNC_DATASETS_OVERRIDE}"
fi

if [[ -n "${SYNC_OUTPUTS_OVERRIDE}" ]]; then
    SYNC_OUTPUTS="${SYNC_OUTPUTS_OVERRIDE}"
fi

if [[ -n "${SYNC_LOGS_OVERRIDE}" ]]; then
    SYNC_LOGS="${SYNC_LOGS_OVERRIDE}"
fi

if [[ -n "${CHECKSUM_OVERRIDE}" ]]; then
    SYNC_CHECKSUM="${CHECKSUM_OVERRIDE}"
fi

SYNC_DELETE_EFFECTIVE="${SYNC_DELETE}"
SYNC_MODEL_STORE_EFFECTIVE="${SYNC_MODEL_STORE}"
SYNC_DATASETS_EFFECTIVE="${SYNC_DATASETS}"
SYNC_OUTPUTS_EFFECTIVE="${SYNC_OUTPUTS}"
SYNC_LOGS_EFFECTIVE="${SYNC_LOGS}"
SYNC_CHECKSUM_EFFECTIVE="${SYNC_CHECKSUM}"

require_non_empty "${REMOTE_PROJECT_NAME}" "REMOTE_PROJECT_NAME"

[[ "${REMOTE_PROJECT_NAME}" =~ ^[A-Za-z0-9._-]+$ ]] || die \
    "REMOTE_PROJECT_NAME possui caracteres inválidos: " \
    "${REMOTE_PROJECT_NAME}"

validate_remote_path "${SCRATCH_DIR}" "SCRATCH_DIR"

if [[ -n "${REMOTE_PROJECT_DIR_OVERRIDE}" ]]; then
    REMOTE_PROJECT_DIR="${REMOTE_PROJECT_DIR_OVERRIDE}"
fi

if [[ -z "${REMOTE_PROJECT_DIR}" ]]; then
    REMOTE_PROJECT_DIR="${SCRATCH_DIR%/}/${REMOTE_PROJECT_NAME}"
fi

if [[ -z "${REMOTE_VENV_DIR}" ]]; then
    REMOTE_VENV_DIR="${SCRATCH_DIR%/}/.venvs/${REMOTE_PROJECT_NAME}"
fi

if [[ -z "${REMOTE_PIP_CACHE_DIR}" ]]; then
    REMOTE_PIP_CACHE_DIR="${SCRATCH_DIR%/}/.cache/pip"
fi

if [[ -z "${REMOTE_HF_HOME}" ]]; then
    REMOTE_HF_HOME="${SCRATCH_DIR%/}/.cache/huggingface"
fi

if [[ -z "${REMOTE_OUTPUT_DIR}" ]]; then
    REMOTE_OUTPUT_DIR="${REMOTE_PROJECT_DIR%/}/outputs"
fi

if [[ -z "${REMOTE_LOG_DIR}" ]]; then
    REMOTE_LOG_DIR="${REMOTE_PROJECT_DIR%/}/logs"
fi

if [[ -z "${REMOTE_TEMP_DIR}" ]]; then
    REMOTE_TEMP_DIR="${REMOTE_PROJECT_DIR%/}/.tmp"
fi

for remote_pair in \
    "REMOTE_PROJECT_DIR:${REMOTE_PROJECT_DIR}" \
    "REMOTE_VENV_DIR:${REMOTE_VENV_DIR}" \
    "REMOTE_PIP_CACHE_DIR:${REMOTE_PIP_CACHE_DIR}" \
    "REMOTE_HF_HOME:${REMOTE_HF_HOME}" \
    "REMOTE_OUTPUT_DIR:${REMOTE_OUTPUT_DIR}" \
    "REMOTE_LOG_DIR:${REMOTE_LOG_DIR}" \
    "REMOTE_TEMP_DIR:${REMOTE_TEMP_DIR}"
do
    field_name="${remote_pair%%:*}"
    field_value="${remote_pair#*:}"

    validate_remote_path "${field_value}" "${field_name}"

    if is_true "${REQUIRE_REMOTE_PATH_UNDER_SCRATCH}"; then
        path_is_under "${field_value}" "${SCRATCH_DIR}" || die \
            "${field_name} precisa estar abaixo de SCRATCH_DIR. " \
            "Valor: ${field_value}; SCRATCH_DIR: ${SCRATCH_DIR}"
    fi
done

if [[ -n "${SSH_IDENTITY_FILE}" ]]; then
    SSH_IDENTITY_FILE="$(
        resolve_project_path "${SSH_IDENTITY_FILE}"
    )"

    [[ -f "${SSH_IDENTITY_FILE}" ]] || die \
        "Chave SSH não encontrada: ${SSH_IDENTITY_FILE}"

    [[ -r "${SSH_IDENTITY_FILE}" ]] || die \
        "Chave SSH sem permissão de leitura: ${SSH_IDENTITY_FILE}"
fi

mkdir -p -- "${PROJECT_ROOT}/.tmp/sdumont"

if [[ -z "${SSH_CONTROL_PATH}" ]]; then
    SSH_CONTROL_PATH="${PROJECT_ROOT}/.tmp/sdumont/ssh-%C"
elif [[ "${SSH_CONTROL_PATH}" != /* ]]; then
    SSH_CONTROL_PATH="${PROJECT_ROOT}/${SSH_CONTROL_PATH}"
fi

mkdir -p -- "$(dirname -- "${SSH_CONTROL_PATH}")"

case "${SSH_STRICT_HOST_KEY_CHECKING}" in
    yes|no|accept-new)
        ;;
    *)
        die \
            "SSH_STRICT_HOST_KEY_CHECKING precisa ser yes, no ou " \
            "accept-new."
        ;;
esac


# ==============================================================================
# VALIDAÇÃO DO CONTEÚDO LOCAL
# ==============================================================================

for required_local_file in \
    "${PROJECT_ROOT}/pipeline/runner.py" \
    "${PROJECT_ROOT}/pipeline/configuration.py" \
    "${PROJECT_ROOT}/scripts/run_service.sh" \
    "${PROJECT_ROOT}/requirements.txt" \
    "${PROJECT_ROOT}/${EXPERIMENT_CONFIG_RELATIVE}"
do
    [[ -f "${required_local_file}" ]] || die \
        "Arquivo local obrigatório ausente: ${required_local_file}"
done

if [[ "${SYNC_MODEL_STORE_EFFECTIVE}" == true ]]; then
    [[ -d "${PROJECT_ROOT}/model_store" ]] || die \
        "SYNC_MODEL_STORE=true, mas model_store/ não existe."
fi

if [[ "${SYNC_DATASETS_EFFECTIVE}" == true ]]; then
    [[ -d "${PROJECT_ROOT}/datasets" ]] || die \
        "SYNC_DATASETS=true, mas datasets/ não existe."
fi


# ==============================================================================
# COMANDOS SSH E RSYNC
# ==============================================================================

SSH_COMMAND_PATH="$(
    resolve_command_path "${SSH_COMMAND}" "SSH_COMMAND"
)"

RSYNC_COMMAND_PATH="$(
    resolve_command_path "${RSYNC_COMMAND}" "RSYNC_COMMAND"
)"

SSH_TARGET="${USERNAME}@${LOGIN_HOST}"

SSH_ARGUMENTS=(
    "-p"
    "${SSH_PORT}"
    "-o"
    "ConnectTimeout=${SSH_CONNECT_TIMEOUT_SECONDS}"
    "-o"
    "ServerAliveInterval=${SSH_SERVER_ALIVE_INTERVAL_SECONDS}"
    "-o"
    "ServerAliveCountMax=${SSH_SERVER_ALIVE_COUNT_MAX}"
    "-o"
    "StrictHostKeyChecking=${SSH_STRICT_HOST_KEY_CHECKING}"
    "-o"
    "ControlMaster=auto"
    "-o"
    "ControlPersist=10m"
    "-o"
    "ControlPath=${SSH_CONTROL_PATH}"
)

if [[ "${SSH_BATCH_MODE}" == true ]]; then
    SSH_ARGUMENTS+=("-o" "BatchMode=yes")
else
    SSH_ARGUMENTS+=("-o" "BatchMode=no")
fi

if [[ -n "${SSH_IDENTITY_FILE}" ]]; then
    SSH_ARGUMENTS+=("-i" "${SSH_IDENTITY_FILE}")
fi

if [[ -n "${SSH_PROXY_JUMP}" ]]; then
    SSH_ARGUMENTS+=("-J" "${SSH_PROXY_JUMP}")
fi

if [[ -n "${SSH_KNOWN_HOSTS_FILE}" ]]; then
    SSH_ARGUMENTS+=(
        "-o"
        "UserKnownHostsFile=${SSH_KNOWN_HOSTS_FILE}"
    )
fi

split_literal_options \
    "${SSH_EXTRA_OPTIONS}" \
    "SSH_ARGUMENTS"

RSYNC_SSH_COMMAND="$(
    shell_join \
        "${SSH_COMMAND_PATH}" \
        "${SSH_ARGUMENTS[@]}"
)"

write_exclude_file

RSYNC_ARGUMENTS=(
    "--archive"
    "--human-readable"
    "--itemize-changes"
    "--exclude-from"
    "${TEMP_EXCLUDE_FILE}"
    "--rsh"
    "${RSYNC_SSH_COMMAND}"
)

if [[ "${SYNC_PARTIAL}" == true ]]; then
    RSYNC_ARGUMENTS+=("--partial")
fi

if [[ "${SYNC_COMPRESS}" == true ]]; then
    RSYNC_ARGUMENTS+=("--compress")
fi

if [[ "${SYNC_PROGRESS}" == true ]]; then
    RSYNC_ARGUMENTS+=("--info=progress2")
fi

if [[ "${SYNC_CHECKSUM_EFFECTIVE}" == true ]]; then
    RSYNC_ARGUMENTS+=("--checksum")
fi

if [[ "${SYNC_DELETE_EFFECTIVE}" == true ]]; then
    RSYNC_ARGUMENTS+=("--delete" "--delete-delay")
fi

if [[ "${SYNC_BWLIMIT_KBPS}" != "0" ]]; then
    RSYNC_ARGUMENTS+=(
        "--bwlimit=${SYNC_BWLIMIT_KBPS}"
    )
fi

if [[ "${RSYNC_DRY_RUN}" == true ]]; then
    RSYNC_ARGUMENTS+=("--dry-run")
fi

if [[ "${VERBOSE}" == true ]]; then
    RSYNC_ARGUMENTS+=("--verbose")
fi

REMOTE_DESTINATION="${SSH_TARGET}:${REMOTE_PROJECT_DIR%/}/"

RSYNC_COMMAND_LINE=(
    "${RSYNC_COMMAND_PATH}"
    "${RSYNC_ARGUMENTS[@]}"
    "${PROJECT_ROOT}/"
    "${REMOTE_DESTINATION}"
)


# ==============================================================================
# RESUMO
# ==============================================================================

log "Raiz local: ${PROJECT_ROOT}"
log "Experimento: ${EXPERIMENT_CONFIG_RELATIVE}"
log "Destino SSH: ${SSH_TARGET}"
log "Projeto remoto: ${REMOTE_PROJECT_DIR}"
log "Scratch: ${SCRATCH_DIR}"
log "Sincronizar model_store/: ${SYNC_MODEL_STORE_EFFECTIVE}"
log "Sincronizar datasets/: ${SYNC_DATASETS_EFFECTIVE}"
log "Sincronizar outputs/: ${SYNC_OUTPUTS_EFFECTIVE}"
log "Sincronizar logs/: ${SYNC_LOGS_EFFECTIVE}"
log "Excluir arquivos remotos ausentes localmente: ${SYNC_DELETE_EFFECTIVE}"
log "Comparar por checksum: ${SYNC_CHECKSUM_EFFECTIVE}"

if [[ "${RSYNC_DRY_RUN}" == true ]]; then
    warning "O rsync será executado em modo dry-run."
fi

if [[ "${PRINT_ONLY}" == true ]]; then
    warning "Modo print-only: nenhuma conexão será realizada."
fi


# ==============================================================================
# TESTE DE CONECTIVIDADE
# ==============================================================================

if [[ "${SKIP_CONNECTIVITY_CHECK}" == false ]]; then
    connectivity_command="printf '%s\n' 'Conexão SSH validada.'"

    log "Validando a conexão SSH."

    run_ssh_command "${connectivity_command}" || die \
        "Não foi possível conectar a ${SSH_TARGET}."
else
    warning \
        "Teste inicial de conectividade ignorado."
fi


# ==============================================================================
# PREPARAÇÃO DOS DIRETÓRIOS REMOTOS
# ==============================================================================

REMOTE_DIRECTORY_COMMAND="$(
    printf \
        'umask 077; mkdir -p -- %q %q %q %q %q %q %q' \
        "${REMOTE_PROJECT_DIR}" \
        "${REMOTE_VENV_DIR}" \
        "${REMOTE_PIP_CACHE_DIR}" \
        "${REMOTE_HF_HOME}" \
        "${REMOTE_OUTPUT_DIR}" \
        "${REMOTE_LOG_DIR}" \
        "${REMOTE_TEMP_DIR}"
)"

log "Criando os diretórios remotos necessários."

run_ssh_command "${REMOTE_DIRECTORY_COMMAND}" || die \
    "Não foi possível criar os diretórios no Scratch."


# ==============================================================================
# SINCRONIZAÇÃO
# ==============================================================================

STARTED_AT="$(date +%s)"

log "Iniciando a sincronização com rsync."

run_child "${RSYNC_COMMAND_LINE[@]}" || die \
    "O rsync terminou com falha."

FINISHED_AT="$(date +%s)"
DURATION_SECONDS=$((FINISHED_AT - STARTED_AT))

if [[ "${RSYNC_DRY_RUN}" == true ]]; then
    log \
        "Simulação do rsync concluída em " \
        "${DURATION_SECONDS} segundo(s)."
else
    log \
        "Sincronização concluída em " \
        "${DURATION_SECONDS} segundo(s)."
fi


# ==============================================================================
# VALIDAÇÃO REMOTA
# ==============================================================================

if [[ "${RSYNC_DRY_RUN}" == true ]]; then
    warning \
        "A validação remota foi ignorada porque o rsync usou --dry-run."
elif [[ "${SKIP_REMOTE_VALIDATION}" == true ]]; then
    warning \
        "A validação remota foi ignorada por opção da linha de comando."
elif [[ "${VALIDATE_REMOTE_PROJECT}" == true ]]; then
    REMOTE_VALIDATION_COMMAND="$(
        printf \
            'set -Eeuo pipefail; test -f %q; test -f %q; test -f %q; test -f %q; printf "Projeto remoto validado em %%s\n" %q' \
            "${REMOTE_PROJECT_DIR}/pipeline/runner.py" \
            "${REMOTE_PROJECT_DIR}/scripts/run_service.sh" \
            "${REMOTE_PROJECT_DIR}/requirements.txt" \
            "${REMOTE_PROJECT_DIR}/${EXPERIMENT_CONFIG_RELATIVE}" \
            "${REMOTE_PROJECT_DIR}"
    )"

    log "Validando a cópia remota."

    run_ssh_command "${REMOTE_VALIDATION_COMMAND}" || die \
        "A sincronização terminou, mas a validação remota falhou."
else
    warning \
        "VALIDATE_REMOTE_PROJECT=false: validação remota desativada."
fi


# ==============================================================================
# FINALIZAÇÃO
# ==============================================================================

log "Projeto disponível no Scratch:"
printf '  %s:%s\n' \
    "${SSH_TARGET}" \
    "${REMOTE_PROJECT_DIR}"

log "Próxima etapa:"
printf '  ./scripts/setup_sdumont_env.sh --config %q\n' \
    "${CONFIG_PATH}"
