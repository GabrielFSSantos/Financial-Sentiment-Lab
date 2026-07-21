#!/usr/bin/env bash

# ==============================================================================
# DOWNLOAD DOS RESULTADOS DO SANTOS DUMONT
# ==============================================================================
#
# Baixa para o projeto local os resultados e logs produzidos por um job
# submetido com:
#
#   scripts/submit_sdumont.sh
#
# Uso normal:
#
#   ./scripts/download_sdumont_results.sh \
#       --config configs/sdumont.env \
#       --state-file .tmp/sdumont/submission.env
#
# Apenas visualizar os comandos:
#
#   ./scripts/download_sdumont_results.sh \
#       --config configs/sdumont.env \
#       --state-file .tmp/sdumont/submission.env \
#       --print-only
#
# Este script:
#
# - valida configs/sdumont.env;
# - lê o arquivo de estado criado por submit_sdumont.sh;
# - valida a conexão SSH;
# - baixa outputs/ e logs/ com rsync;
# - preserva execuções locais já existentes;
# - evita sobrescrever arquivos locais mais novos por padrão;
# - permite retomar transferências parciais;
# - valida os diretórios locais após a transferência;
# - pode remover, de forma restrita, a execução remota já baixada.
#
# Ele não submete nem monitora jobs.
# ==============================================================================

set -Eeuo pipefail
IFS=$'\n\t'


# ==============================================================================
# CONSTANTES E ESTADO
# ==============================================================================

readonly SCRIPT_NAME="download_sdumont_results"
readonly EXPECTED_CONFIG_SCHEMA_VERSION="2.0"
readonly EXPECTED_STATE_SCHEMA_VERSION="2.0"
readonly DEFAULT_CONFIG_FILE="configs/sdumont.env"

CONFIG_INPUT="${SDUMONT_CONFIG:-${DEFAULT_CONFIG_FILE}}"
STATE_FILE_INPUT=""

PRINT_ONLY=false
VERBOSE=false
ALLOW_INCOMPLETE=false
SKIP_CONNECTIVITY_CHECK=false
SKIP_REMOTE_VALIDATION=false
SKIP_LOCAL_VALIDATION=false

DOWNLOAD_OUTPUTS_OVERRIDE=""
DOWNLOAD_LOGS_OVERRIDE=""
DOWNLOAD_DELETE_OVERRIDE=""
DOWNLOAD_CHECKSUM_OVERRIDE=""
DOWNLOAD_OVERWRITE_NEWER_OVERRIDE=""
KEEP_REMOTE_RESULTS_OVERRIDE=""

REMOTE_OUTPUT_DIR_OVERRIDE=""
REMOTE_LOG_DIR_OVERRIDE=""
LOCAL_OUTPUT_DIR_OVERRIDE=""
LOCAL_LOG_DIR_OVERRIDE=""

CONFIG_PATH=""
STATE_FILE_PATH=""
CHILD_PID=""
TEMP_EXCLUDE_FILE=""

DOWNLOADED_OUTPUTS=false
DOWNLOADED_LOGS=false


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

    error "O download foi interrompido."
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
  ./scripts/download_sdumont_results.sh [opções]

Configuração:
  --config ARQUIVO             Configuração privada do SDumont.
  --state-file ARQUIVO         Estado criado por submit_sdumont.sh.

Conteúdo:
  --outputs                    Baixa os resultados.
  --no-outputs                 Não baixa os resultados.
  --logs                       Baixa os logs.
  --no-logs                    Não baixa os logs.
  --delete                     Remove localmente arquivos ausentes no remoto.
  --no-delete                  Desativa a remoção local.
  --checksum                   Compara arquivos por checksum.
  --no-checksum                Usa tamanho e data.
  --overwrite-newer            Permite sobrescrever arquivos locais mais novos.
  --no-overwrite-newer         Preserva arquivos locais mais novos.

Caminhos:
  --remote-output-dir CAMINHO  Substitui o diretório remoto de resultados.
  --remote-log-dir CAMINHO     Substitui o diretório remoto de logs.
  --local-output-dir CAMINHO   Substitui o diretório local de resultados.
  --local-log-dir CAMINHO      Substitui o diretório local de logs.

Finalização:
  --keep-remote                Mantém os resultados no Scratch.
  --remove-remote              Remove somente a execução baixada identificada
                               por RUN_ID e os dois logs do job.

Validação:
  --allow-incomplete           Permite download de job ainda não terminal.
  --skip-connectivity-check    Não testa o SSH antes do rsync.
  --skip-remote-validation     Não valida os diretórios remotos.
  --skip-local-validation      Não valida o conteúdo local baixado.
  --print-only                 Apenas imprime os comandos.
  --verbose                    Exibe informações adicionais.
  -h, --help                   Exibe esta ajuda.

Exemplos:
  ./scripts/download_sdumont_results.sh \
    --config configs/sdumont.env \
    --state-file .tmp/sdumont/submission.env

  ./scripts/download_sdumont_results.sh \
    --config configs/sdumont.env \
    --state-file .tmp/sdumont/submission.env \
    --print-only

  ./scripts/download_sdumont_results.sh \
    --config configs/sdumont.env \
    --state-file .tmp/sdumont/submission.env \
    --logs \
    --no-outputs
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


require_non_empty() {
    local value="$1"
    local field_name="$2"

    [[ -n "$(trim_value "${value}")" ]] || die \
        "${field_name} precisa ser preenchido."
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


validate_local_destination() {
    local value="$1"
    local field_name="$2"

    require_non_empty "${value}" "${field_name}"

    case "${value}" in
        "/"|"${HOME}"|"${PROJECT_ROOT}")
            die \
                "${field_name} não pode apontar para um diretório amplo: " \
                "${value}"
            ;;
    esac
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


split_literal_options() {
    local raw="$1"
    local destination_name="$2"
    local -n destination="${destination_name}"
    local parsed=()

    [[ -n "$(trim_value "${raw}")" ]] || return 0

    # Divisão literal e sem eval.
    read -r -a parsed <<< "${raw}"
    destination+=("${parsed[@]}")
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
            "DOWNLOAD_EXTRA_EXCLUDES contém valor inválido."

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
    local tolerate_failure="${2:-false}"
    local command=(
        "${SSH_COMMAND_PATH}"
        "${SSH_ARGUMENTS[@]}"
        "${SSH_TARGET}"
        "${REMOTE_SHELL}"
        "-lc"
        "${remote_command}"
    )
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

    if [[ "${exit_code}" -ne 0 ]] && \
        [[ "${tolerate_failure}" != true ]]
    then
        return "${exit_code}"
    fi

    return 0
}


state_is_terminal() {
    local value=""

    value="$(
        printf '%s' "${1:-}" |
            tr '[:lower:]' '[:upper:]'
    )"
    value="${value%%+*}"
    value="${value%% *}"

    case "${value}" in
        COMPLETED|FAILED|CANCELLED|TIMEOUT|NODE_FAIL|OUT_OF_MEMORY|\
        PREEMPTED|BOOT_FAIL|DEADLINE|REVOKED|SPECIAL_EXIT|INTERRUPTED)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}


write_exclude_file() {
    mkdir -p -- "${PROJECT_ROOT}/.tmp/sdumont"

    TEMP_EXCLUDE_FILE="$(
        mktemp \
            "${PROJECT_ROOT}/.tmp/sdumont/download-excludes.XXXXXX"
    )"

    : > "${TEMP_EXCLUDE_FILE}"
    append_csv_excludes "${DOWNLOAD_EXTRA_EXCLUDES}"

    if [[ "${VERBOSE}" == true ]] && \
        [[ -s "${TEMP_EXCLUDE_FILE}" ]]
    then
        log "Exclusões aplicadas ao download:"
        sed 's/^/  - /' "${TEMP_EXCLUDE_FILE}"
    fi
}


build_rsync_arguments() {
    local destination_name="$1"
    local -n destination="${destination_name}"

    destination=(
        "--archive"
        "--human-readable"
        "--itemize-changes"
        "--rsh"
        "${RSYNC_SSH_COMMAND}"
    )

    if [[ -s "${TEMP_EXCLUDE_FILE}" ]]; then
        destination+=(
            "--exclude-from"
            "${TEMP_EXCLUDE_FILE}"
        )
    fi

    if [[ "${DOWNLOAD_PARTIAL}" == true ]]; then
        destination+=("--partial")
    fi

    if [[ "${DOWNLOAD_COMPRESS}" == true ]]; then
        destination+=("--compress")
    fi

    if [[ "${DOWNLOAD_PROGRESS}" == true ]]; then
        destination+=("--info=progress2")
    fi

    if [[ "${DOWNLOAD_CHECKSUM_EFFECTIVE}" == true ]]; then
        destination+=("--checksum")
    fi

    if [[ "${DOWNLOAD_DELETE_EFFECTIVE}" == true ]]; then
        destination+=("--delete" "--delete-delay")
    fi

    if [[ "${DOWNLOAD_OVERWRITE_NEWER_EFFECTIVE}" == false ]]; then
        destination+=("--update")
    fi

    if [[ "${VERBOSE}" == true ]]; then
        destination+=("--verbose")
    fi
}


download_directory() {
    local description="$1"
    local remote_directory="$2"
    local local_directory="$3"
    local arguments=()
    local command=()

    mkdir -p -- "${local_directory}"

    build_rsync_arguments arguments

    command=(
        "${RSYNC_COMMAND_PATH}"
        "${arguments[@]}"
        "${SSH_TARGET}:${remote_directory%/}/"
        "${local_directory%/}/"
    )

    log \
        "Baixando ${description}: " \
        "${remote_directory} → ${local_directory}"

    run_child "${command[@]}"
}


safe_remote_cleanup() {
    local remote_run_directory=""
    local cleanup_command=""

    if [[ "${KEEP_REMOTE_RESULTS_EFFECTIVE}" == true ]]; then
        return 0
    fi

    if [[ "${PRINT_ONLY}" == true ]]; then
        warning \
            "O modo print-only mostrará a limpeza remota, mas não a executará."
    fi

    if [[ -z "${RUN_ID}" ]]; then
        warning \
            "KEEP_REMOTE_RESULTS=false, mas o arquivo de estado não possui " \
            "RUN_ID. Nenhum resultado remoto será removido."
        return 0
    fi

    [[ "${RUN_ID}" =~ ^[A-Za-z0-9._-]+$ ]] || {
        warning \
            "RUN_ID contém caracteres inseguros para limpeza: ${RUN_ID}. " \
            "Nenhum resultado remoto será removido."
        return 0
    }

    remote_run_directory="${REMOTE_OUTPUT_DIR%/}/${RUN_ID}"

    path_is_under \
        "${remote_run_directory}" \
        "${REMOTE_OUTPUT_DIR}" || die \
        "Recusa de segurança ao remover ${remote_run_directory}."

    cleanup_command="$(
        printf \
            'set -Eeuo pipefail; if [[ -d %q ]]; then rm -rf -- %q; fi' \
            "${remote_run_directory}" \
            "${remote_run_directory}"
    )"

    if [[ -n "${REMOTE_STDOUT_FILE}" ]]; then
        cleanup_command+="; if [[ -f "
        cleanup_command+="$(printf '%q' "${REMOTE_STDOUT_FILE}")"
        cleanup_command+=" ]]; then rm -f -- "
        cleanup_command+="$(printf '%q' "${REMOTE_STDOUT_FILE}")"
        cleanup_command+="; fi"
    fi

    if [[ -n "${REMOTE_STDERR_FILE}" ]]; then
        cleanup_command+="; if [[ -f "
        cleanup_command+="$(printf '%q' "${REMOTE_STDERR_FILE}")"
        cleanup_command+=" ]]; then rm -f -- "
        cleanup_command+="$(printf '%q' "${REMOTE_STDERR_FILE}")"
        cleanup_command+="; fi"
    fi

    warning \
        "Removendo somente a execução remota identificada por RUN_ID=${RUN_ID}."

    run_ssh_command "${cleanup_command}" || die \
        "O download terminou, mas a limpeza remota falhou."
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

        --state-file)
            [[ "$#" -ge 2 ]] || die \
                "--state-file exige um arquivo."

            STATE_FILE_INPUT="$2"
            shift 2
            ;;

        --state-file=*)
            STATE_FILE_INPUT="${1#*=}"
            shift
            ;;

        --outputs)
            DOWNLOAD_OUTPUTS_OVERRIDE="true"
            shift
            ;;

        --no-outputs)
            DOWNLOAD_OUTPUTS_OVERRIDE="false"
            shift
            ;;

        --logs)
            DOWNLOAD_LOGS_OVERRIDE="true"
            shift
            ;;

        --no-logs)
            DOWNLOAD_LOGS_OVERRIDE="false"
            shift
            ;;

        --delete)
            DOWNLOAD_DELETE_OVERRIDE="true"
            shift
            ;;

        --no-delete)
            DOWNLOAD_DELETE_OVERRIDE="false"
            shift
            ;;

        --checksum)
            DOWNLOAD_CHECKSUM_OVERRIDE="true"
            shift
            ;;

        --no-checksum)
            DOWNLOAD_CHECKSUM_OVERRIDE="false"
            shift
            ;;

        --overwrite-newer)
            DOWNLOAD_OVERWRITE_NEWER_OVERRIDE="true"
            shift
            ;;

        --no-overwrite-newer)
            DOWNLOAD_OVERWRITE_NEWER_OVERRIDE="false"
            shift
            ;;

        --keep-remote)
            KEEP_REMOTE_RESULTS_OVERRIDE="true"
            shift
            ;;

        --remove-remote)
            KEEP_REMOTE_RESULTS_OVERRIDE="false"
            shift
            ;;

        --remote-output-dir)
            [[ "$#" -ge 2 ]] || die \
                "--remote-output-dir exige um caminho."

            REMOTE_OUTPUT_DIR_OVERRIDE="$2"
            shift 2
            ;;

        --remote-output-dir=*)
            REMOTE_OUTPUT_DIR_OVERRIDE="${1#*=}"
            shift
            ;;

        --remote-log-dir)
            [[ "$#" -ge 2 ]] || die \
                "--remote-log-dir exige um caminho."

            REMOTE_LOG_DIR_OVERRIDE="$2"
            shift 2
            ;;

        --remote-log-dir=*)
            REMOTE_LOG_DIR_OVERRIDE="${1#*=}"
            shift
            ;;

        --local-output-dir)
            [[ "$#" -ge 2 ]] || die \
                "--local-output-dir exige um caminho."

            LOCAL_OUTPUT_DIR_OVERRIDE="$2"
            shift 2
            ;;

        --local-output-dir=*)
            LOCAL_OUTPUT_DIR_OVERRIDE="${1#*=}"
            shift
            ;;

        --local-log-dir)
            [[ "$#" -ge 2 ]] || die \
                "--local-log-dir exige um caminho."

            LOCAL_LOG_DIR_OVERRIDE="$2"
            shift 2
            ;;

        --local-log-dir=*)
            LOCAL_LOG_DIR_OVERRIDE="${1#*=}"
            shift
            ;;

        --allow-incomplete)
            ALLOW_INCOMPLETE=true
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

        --skip-local-validation)
            SKIP_LOCAL_VALIDATION=true
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
# CONFIGURAÇÃO E ESTADO
# ==============================================================================

CONFIG_PATH="$(canonical_existing_file "${CONFIG_INPUT}")" || die \
    "Configuração do SDumont não encontrada: ${CONFIG_INPUT}"

require_non_empty "${STATE_FILE_INPUT}" "--state-file"

STATE_FILE_PATH="$(
    canonical_existing_file "${STATE_FILE_INPUT}"
)" || die \
    "Arquivo de estado não encontrado: ${STATE_FILE_INPUT}"

# Primeiro carrega a configuração de infraestrutura.
# shellcheck disable=SC1090
source "${CONFIG_PATH}"

: "${SDUMONT_CONFIG_SCHEMA_VERSION:=}"
: "${USERNAME:=}"
: "${LOGIN_HOST:=}"
: "${SCRATCH_DIR:=}"

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
: "${REMOTE_OUTPUT_DIR:=}"
: "${REMOTE_LOG_DIR:=}"

: "${LOCAL_OUTPUT_DIR:=outputs}"
: "${LOCAL_LOG_DIR:=logs}"

: "${DOWNLOAD_OUTPUTS:=true}"
: "${DOWNLOAD_LOGS:=true}"
: "${DOWNLOAD_DELETE:=false}"
: "${DOWNLOAD_PARTIAL:=true}"
: "${DOWNLOAD_COMPRESS:=true}"
: "${DOWNLOAD_PROGRESS:=true}"
: "${DOWNLOAD_CHECKSUM:=false}"
: "${DOWNLOAD_OVERWRITE_NEWER:=false}"
: "${DOWNLOAD_EXTRA_EXCLUDES:=}"
: "${KEEP_REMOTE_RESULTS:=true}"

: "${REQUIRE_ABSOLUTE_REMOTE_PATHS:=true}"
: "${REQUIRE_REMOTE_PATH_UNDER_SCRATCH:=true}"

: "${SSH_COMMAND:=ssh}"
: "${RSYNC_COMMAND:=rsync}"
: "${REMOTE_SHELL:=bash}"

[[ "${SDUMONT_CONFIG_SCHEMA_VERSION}" == \
    "${EXPECTED_CONFIG_SCHEMA_VERSION}" ]] || die \
    "Versão de configs/sdumont.env incompatível. " \
    "Esperada: ${EXPECTED_CONFIG_SCHEMA_VERSION}; " \
    "recebida: ${SDUMONT_CONFIG_SCHEMA_VERSION:-vazia}."

# Preserva valores da configuração antes de carregar o estado.
CONFIG_USERNAME="${USERNAME}"
CONFIG_LOGIN_HOST="${LOGIN_HOST}"
CONFIG_SCRATCH_DIR="${SCRATCH_DIR}"
CONFIG_REMOTE_PROJECT_DIR="${REMOTE_PROJECT_DIR}"
CONFIG_REMOTE_OUTPUT_DIR="${REMOTE_OUTPUT_DIR}"
CONFIG_REMOTE_LOG_DIR="${REMOTE_LOG_DIR}"

# O estado é gerado localmente por submit_sdumont.sh com printf %q.
# shellcheck disable=SC1090
source "${STATE_FILE_PATH}"

: "${STATE_SCHEMA_VERSION:=}"
: "${STATUS:=}"
: "${JOB_ID:=}"
: "${FINAL_STATE:=}"
: "${FINAL_EXIT_CODE:=}"
: "${SSH_TARGET:=}"
: "${REMOTE_PROJECT_DIR:=}"
: "${REMOTE_OUTPUT_DIR:=}"
: "${REMOTE_LOG_DIR:=}"
: "${REMOTE_STDOUT_FILE:=}"
: "${REMOTE_STDERR_FILE:=}"
: "${RUN_ID:=}"

[[ "${STATE_SCHEMA_VERSION}" == \
    "${EXPECTED_STATE_SCHEMA_VERSION}" ]] || die \
    "Versão do arquivo de estado incompatível. " \
    "Esperada: ${EXPECTED_STATE_SCHEMA_VERSION}; " \
    "recebida: ${STATE_SCHEMA_VERSION:-vazia}."

USERNAME="${CONFIG_USERNAME}"
LOGIN_HOST="${CONFIG_LOGIN_HOST}"
SCRATCH_DIR="${CONFIG_SCRATCH_DIR}"

require_non_empty "${USERNAME}" "USERNAME"
require_non_empty "${LOGIN_HOST}" "LOGIN_HOST"
require_non_empty "${SCRATCH_DIR}" "SCRATCH_DIR"

if [[ -z "${REMOTE_PROJECT_DIR}" ]]; then
    REMOTE_PROJECT_DIR="${CONFIG_REMOTE_PROJECT_DIR}"
fi

if [[ -z "${REMOTE_PROJECT_DIR}" ]]; then
    REMOTE_PROJECT_DIR="${SCRATCH_DIR%/}/${REMOTE_PROJECT_NAME}"
fi

if [[ -z "${REMOTE_OUTPUT_DIR}" ]]; then
    REMOTE_OUTPUT_DIR="${CONFIG_REMOTE_OUTPUT_DIR}"
fi

if [[ -z "${REMOTE_OUTPUT_DIR}" ]]; then
    REMOTE_OUTPUT_DIR="${REMOTE_PROJECT_DIR%/}/outputs"
fi

if [[ -z "${REMOTE_LOG_DIR}" ]]; then
    REMOTE_LOG_DIR="${CONFIG_REMOTE_LOG_DIR}"
fi

if [[ -z "${REMOTE_LOG_DIR}" ]]; then
    REMOTE_LOG_DIR="${REMOTE_PROJECT_DIR%/}/logs"
fi

if [[ -n "${REMOTE_OUTPUT_DIR_OVERRIDE}" ]]; then
    REMOTE_OUTPUT_DIR="${REMOTE_OUTPUT_DIR_OVERRIDE}"
fi

if [[ -n "${REMOTE_LOG_DIR_OVERRIDE}" ]]; then
    REMOTE_LOG_DIR="${REMOTE_LOG_DIR_OVERRIDE}"
fi

if [[ -n "${LOCAL_OUTPUT_DIR_OVERRIDE}" ]]; then
    LOCAL_OUTPUT_DIR="${LOCAL_OUTPUT_DIR_OVERRIDE}"
fi

if [[ -n "${LOCAL_LOG_DIR_OVERRIDE}" ]]; then
    LOCAL_LOG_DIR="${LOCAL_LOG_DIR_OVERRIDE}"
fi

LOCAL_OUTPUT_DIR_PATH="$(resolve_project_path "${LOCAL_OUTPUT_DIR}")"
LOCAL_LOG_DIR_PATH="$(resolve_project_path "${LOCAL_LOG_DIR}")"


# ==============================================================================
# VALIDAÇÃO DOS VALORES
# ==============================================================================

require_positive_integer "${SSH_PORT}" "SSH_PORT"
require_positive_integer \
    "${SSH_CONNECT_TIMEOUT_SECONDS}" \
    "SSH_CONNECT_TIMEOUT_SECONDS"
require_positive_integer \
    "${SSH_SERVER_ALIVE_INTERVAL_SECONDS}" \
    "SSH_SERVER_ALIVE_INTERVAL_SECONDS"
require_non_negative_integer \
    "${SSH_SERVER_ALIVE_COUNT_MAX}" \
    "SSH_SERVER_ALIVE_COUNT_MAX"

SSH_BATCH_MODE="$(normalize_boolean "${SSH_BATCH_MODE}" "SSH_BATCH_MODE")"
DOWNLOAD_OUTPUTS="$(
    normalize_boolean "${DOWNLOAD_OUTPUTS}" "DOWNLOAD_OUTPUTS"
)"
DOWNLOAD_LOGS="$(
    normalize_boolean "${DOWNLOAD_LOGS}" "DOWNLOAD_LOGS"
)"
DOWNLOAD_DELETE="$(
    normalize_boolean "${DOWNLOAD_DELETE}" "DOWNLOAD_DELETE"
)"
DOWNLOAD_PARTIAL="$(
    normalize_boolean "${DOWNLOAD_PARTIAL}" "DOWNLOAD_PARTIAL"
)"
DOWNLOAD_COMPRESS="$(
    normalize_boolean "${DOWNLOAD_COMPRESS}" "DOWNLOAD_COMPRESS"
)"
DOWNLOAD_PROGRESS="$(
    normalize_boolean "${DOWNLOAD_PROGRESS}" "DOWNLOAD_PROGRESS"
)"
DOWNLOAD_CHECKSUM="$(
    normalize_boolean "${DOWNLOAD_CHECKSUM}" "DOWNLOAD_CHECKSUM"
)"
DOWNLOAD_OVERWRITE_NEWER="$(
    normalize_boolean \
        "${DOWNLOAD_OVERWRITE_NEWER}" \
        "DOWNLOAD_OVERWRITE_NEWER"
)"
KEEP_REMOTE_RESULTS="$(
    normalize_boolean "${KEEP_REMOTE_RESULTS}" "KEEP_REMOTE_RESULTS"
)"
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

if [[ -n "${DOWNLOAD_OUTPUTS_OVERRIDE}" ]]; then
    DOWNLOAD_OUTPUTS="${DOWNLOAD_OUTPUTS_OVERRIDE}"
fi

if [[ -n "${DOWNLOAD_LOGS_OVERRIDE}" ]]; then
    DOWNLOAD_LOGS="${DOWNLOAD_LOGS_OVERRIDE}"
fi

if [[ -n "${DOWNLOAD_DELETE_OVERRIDE}" ]]; then
    DOWNLOAD_DELETE="${DOWNLOAD_DELETE_OVERRIDE}"
fi

if [[ -n "${DOWNLOAD_CHECKSUM_OVERRIDE}" ]]; then
    DOWNLOAD_CHECKSUM="${DOWNLOAD_CHECKSUM_OVERRIDE}"
fi

if [[ -n "${DOWNLOAD_OVERWRITE_NEWER_OVERRIDE}" ]]; then
    DOWNLOAD_OVERWRITE_NEWER="${DOWNLOAD_OVERWRITE_NEWER_OVERRIDE}"
fi

if [[ -n "${KEEP_REMOTE_RESULTS_OVERRIDE}" ]]; then
    KEEP_REMOTE_RESULTS="${KEEP_REMOTE_RESULTS_OVERRIDE}"
fi

DOWNLOAD_OUTPUTS_EFFECTIVE="${DOWNLOAD_OUTPUTS}"
DOWNLOAD_LOGS_EFFECTIVE="${DOWNLOAD_LOGS}"
DOWNLOAD_DELETE_EFFECTIVE="${DOWNLOAD_DELETE}"
DOWNLOAD_CHECKSUM_EFFECTIVE="${DOWNLOAD_CHECKSUM}"
DOWNLOAD_OVERWRITE_NEWER_EFFECTIVE="${DOWNLOAD_OVERWRITE_NEWER}"
KEEP_REMOTE_RESULTS_EFFECTIVE="${KEEP_REMOTE_RESULTS}"

if [[ "${DOWNLOAD_OUTPUTS_EFFECTIVE}" == false ]] && \
    [[ "${DOWNLOAD_LOGS_EFFECTIVE}" == false ]]
then
    die \
        "DOWNLOAD_OUTPUTS e DOWNLOAD_LOGS estão desativados. " \
        "Não há conteúdo para baixar."
fi

validate_remote_path "${SCRATCH_DIR}" "SCRATCH_DIR"
validate_remote_path "${REMOTE_PROJECT_DIR}" "REMOTE_PROJECT_DIR"
validate_remote_path "${REMOTE_OUTPUT_DIR}" "REMOTE_OUTPUT_DIR"
validate_remote_path "${REMOTE_LOG_DIR}" "REMOTE_LOG_DIR"

if is_true "${REQUIRE_REMOTE_PATH_UNDER_SCRATCH}"; then
    for remote_path in \
        "${REMOTE_PROJECT_DIR}" \
        "${REMOTE_OUTPUT_DIR}" \
        "${REMOTE_LOG_DIR}"
    do
        path_is_under "${remote_path}" "${SCRATCH_DIR}" || die \
            "Caminho remoto fora de SCRATCH_DIR: ${remote_path}"
    done
fi

validate_local_destination \
    "${LOCAL_OUTPUT_DIR_PATH}" \
    "LOCAL_OUTPUT_DIR"
validate_local_destination \
    "${LOCAL_LOG_DIR_PATH}" \
    "LOCAL_LOG_DIR"

if [[ "${ALLOW_INCOMPLETE}" == false ]]; then
    terminal_candidate="${FINAL_STATE:-${STATUS}}"

    state_is_terminal "${terminal_candidate}" || die \
        "O job ainda não possui estado terminal " \
        "(STATUS=${STATUS:-vazio}, FINAL_STATE=${FINAL_STATE:-vazio}). " \
        "Use --allow-incomplete para baixar arquivos parciais."
fi

if [[ -n "${SSH_IDENTITY_FILE}" ]]; then
    SSH_IDENTITY_FILE="$(resolve_project_path "${SSH_IDENTITY_FILE}")"

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
# SSH E RSYNC
# ==============================================================================

SSH_COMMAND_PATH="$(
    resolve_command_path "${SSH_COMMAND}" "SSH_COMMAND"
)"

RSYNC_COMMAND_PATH="$(
    resolve_command_path "${RSYNC_COMMAND}" "RSYNC_COMMAND"
)"

SSH_TARGET_EFFECTIVE="${USERNAME}@${LOGIN_HOST}"

if [[ -n "${SSH_TARGET}" ]] && \
    [[ "${SSH_TARGET}" != "${SSH_TARGET_EFFECTIVE}" ]]
then
    warning \
        "O SSH_TARGET do estado (${SSH_TARGET}) difere da configuração " \
        "atual (${SSH_TARGET_EFFECTIVE}). Será usada a configuração atual."
fi

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


# ==============================================================================
# RESUMO
# ==============================================================================

log "Arquivo de estado: ${STATE_FILE_PATH}"
log "Job ID: ${JOB_ID:-não informado}"
log "Status: ${STATUS:-não informado}"
log "Estado final: ${FINAL_STATE:-não informado}"
log "Código final: ${FINAL_EXIT_CODE:-não informado}"
log "Run ID: ${RUN_ID:-não informado}"
log "Destino SSH: ${SSH_TARGET_EFFECTIVE}"
log "Outputs remotos: ${REMOTE_OUTPUT_DIR}"
log "Outputs locais: ${LOCAL_OUTPUT_DIR_PATH}"
log "Logs remotos: ${REMOTE_LOG_DIR}"
log "Logs locais: ${LOCAL_LOG_DIR_PATH}"
log "Baixar outputs: ${DOWNLOAD_OUTPUTS_EFFECTIVE}"
log "Baixar logs: ${DOWNLOAD_LOGS_EFFECTIVE}"
log "Remover arquivos locais ausentes no remoto: ${DOWNLOAD_DELETE_EFFECTIVE}"
log "Preservar arquivos locais mais novos: $(
    if [[ "${DOWNLOAD_OVERWRITE_NEWER_EFFECTIVE}" == false ]]; then
        printf true
    else
        printf false
    fi
)"
log "Manter resultados no Scratch: ${KEEP_REMOTE_RESULTS_EFFECTIVE}"

if [[ "${PRINT_ONLY}" == true ]]; then
    warning "Modo print-only: nenhuma conexão ou transferência será realizada."
fi


# ==============================================================================
# CONECTIVIDADE E VALIDAÇÃO REMOTA
# ==============================================================================

if [[ "${SKIP_CONNECTIVITY_CHECK}" == false ]]; then
    log "Validando a conexão SSH."

    run_ssh_command \
        "printf '%s\n' 'Conexão SSH validada.'" || die \
        "Não foi possível conectar a ${SSH_TARGET_EFFECTIVE}."
else
    warning "Teste de conectividade ignorado."
fi

if [[ "${SKIP_REMOTE_VALIDATION}" == false ]]; then
    REMOTE_VALIDATION_COMMAND="set -Eeuo pipefail"

    if [[ "${DOWNLOAD_OUTPUTS_EFFECTIVE}" == true ]]; then
        REMOTE_VALIDATION_COMMAND+="; test -d "
        REMOTE_VALIDATION_COMMAND+="$(printf '%q' "${REMOTE_OUTPUT_DIR}")"
    fi

    if [[ "${DOWNLOAD_LOGS_EFFECTIVE}" == true ]]; then
        REMOTE_VALIDATION_COMMAND+="; test -d "
        REMOTE_VALIDATION_COMMAND+="$(printf '%q' "${REMOTE_LOG_DIR}")"
    fi

    log "Validando os diretórios remotos."

    run_ssh_command "${REMOTE_VALIDATION_COMMAND}" || die \
        "Um ou mais diretórios remotos solicitados não existem."
else
    warning "Validação dos diretórios remotos ignorada."
fi


# ==============================================================================
# DOWNLOAD
# ==============================================================================

STARTED_AT="$(date +%s)"

if [[ "${DOWNLOAD_OUTPUTS_EFFECTIVE}" == true ]]; then
    download_directory \
        "resultados" \
        "${REMOTE_OUTPUT_DIR}" \
        "${LOCAL_OUTPUT_DIR_PATH}" || die \
        "Falha ao baixar os resultados."

    DOWNLOADED_OUTPUTS=true
fi

if [[ "${DOWNLOAD_LOGS_EFFECTIVE}" == true ]]; then
    download_directory \
        "logs" \
        "${REMOTE_LOG_DIR}" \
        "${LOCAL_LOG_DIR_PATH}" || die \
        "Falha ao baixar os logs."

    DOWNLOADED_LOGS=true
fi

FINISHED_AT="$(date +%s)"
DURATION_SECONDS=$((FINISHED_AT - STARTED_AT))


# ==============================================================================
# VALIDAÇÃO LOCAL
# ==============================================================================

if [[ "${PRINT_ONLY}" == true ]]; then
    warning \
        "Validação local ignorada porque o modo print-only está ativo."
elif [[ "${SKIP_LOCAL_VALIDATION}" == true ]]; then
    warning "Validação local ignorada por opção da linha de comando."
else
    if [[ "${DOWNLOADED_OUTPUTS}" == true ]]; then
        [[ -d "${LOCAL_OUTPUT_DIR_PATH}" ]] || die \
            "O diretório local de resultados não foi criado."

        if [[ -n "${RUN_ID}" ]]; then
            if [[ -d "${LOCAL_OUTPUT_DIR_PATH%/}/${RUN_ID}" ]]; then
                log \
                    "Execução local encontrada em: " \
                    "${LOCAL_OUTPUT_DIR_PATH%/}/${RUN_ID}"
            else
                warning \
                    "O download terminou, mas outputs/${RUN_ID} não foi " \
                    "encontrado. A execução pode ter utilizado outro run_id."
            fi
        fi
    fi

    if [[ "${DOWNLOADED_LOGS}" == true ]]; then
        [[ -d "${LOCAL_LOG_DIR_PATH}" ]] || die \
            "O diretório local de logs não foi criado."
    fi
fi


# ==============================================================================
# LIMPEZA REMOTA OPCIONAL
# ==============================================================================

safe_remote_cleanup


# ==============================================================================
# FINALIZAÇÃO
# ==============================================================================

if [[ "${PRINT_ONLY}" == true ]]; then
    log "Comandos de download montados com sucesso."
else
    log \
        "Download concluído com sucesso em " \
        "${DURATION_SECONDS} segundo(s)."
fi

if [[ "${DOWNLOAD_OUTPUTS_EFFECTIVE}" == true ]]; then
    printf 'Resultados locais: %s\n' "${LOCAL_OUTPUT_DIR_PATH}"
fi

if [[ "${DOWNLOAD_LOGS_EFFECTIVE}" == true ]]; then
    printf 'Logs locais: %s\n' "${LOCAL_LOG_DIR_PATH}"
fi
