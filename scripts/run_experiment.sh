#!/usr/bin/env bash

# ==============================================================================
# COMANDO PÚBLICO DO EXPERIMENTO
# ==============================================================================
#
# Este é o ponto de entrada único do projeto:
#
#   ./scripts/run_experiment.sh
#
# O ambiente é obtido de ``configs/experiment.yaml``:
#
#   execution:
#     environment: local
#
# ou pode ser substituído temporariamente:
#
#   ./scripts/run_experiment.sh --environment sdumont
#
# Fluxo local:
#
#   setup_env.sh -> run_service.sh -> pipeline.runner
#
# Fluxo SDumont:
#
#   sync_to_scratch.sh
#       -> setup_sdumont_env.sh
#       -> submit_sdumont.sh
#       -> download_sdumont_results.sh
#
# Modelos e datasets ativos continuam definidos exclusivamente em:
#
#   configs/models.yaml
#   configs/datasets.yaml
#
# As opções --model e --dataset alteram apenas a execução atual.
# ==============================================================================

set -Eeuo pipefail
IFS=$'\n\t'


# ==============================================================================
# CONSTANTES E ESTADO
# ==============================================================================

readonly SCRIPT_NAME="run_experiment"
readonly DEFAULT_EXPERIMENT_CONFIG="configs/experiment.yaml"
readonly DEFAULT_SDUMONT_CONFIG="configs/sdumont.env"
readonly DEFAULT_REQUIREMENTS_FILE="requirements.txt"
readonly DEFAULT_VENV_DIR="venv"

CHILD_PID=""

ENVIRONMENT_OVERRIDE="${EXECUTION_ENVIRONMENT:-}"
EXPERIMENT_CONFIG_INPUT="${EXPERIMENT_CONFIG:-${DEFAULT_EXPERIMENT_CONFIG}}"
SDUMONT_CONFIG_INPUT="${SDUMONT_CONFIG:-${DEFAULT_SDUMONT_CONFIG}}"

LOCAL_SKIP_SETUP=false
LOCAL_FORCE_SETUP=false
LOCAL_RECREATE_ENV=false
LOCAL_VENV_DIR="${VENV_DIR:-${DEFAULT_VENV_DIR}}"
LOCAL_PYTHON="${PYTHON_BIN:-python3}"
LOCAL_REQUIREMENTS="${REQUIREMENTS_FILE:-${DEFAULT_REQUIREMENTS_FILE}}"

SDUMONT_SKIP_SYNC=false
SDUMONT_SKIP_REMOTE_SETUP=false
SDUMONT_MONITOR=true
SDUMONT_DOWNLOAD=true
SDUMONT_PRINT_ONLY=false
SDUMONT_STATE_FILE=""

SHOW_HELP=false

RUNNER_ARGUMENTS=()
MODEL_ARGUMENT_COUNT=0
DATASET_ARGUMENT_COUNT=0
RUN_ID_WAS_SET=false
DRY_RUN_WAS_SET=false
LOG_LEVEL_WAS_SET=false
TRACEBACK_WAS_SET=false
PRINT_SUMMARY_WAS_SET=false


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
# ERROS E SINAIS
# ==============================================================================

on_error() {
    local exit_code=$?
    local line_number="${BASH_LINENO[0]:-desconhecida}"
    local failed_command="${BASH_COMMAND:-desconhecido}"

    trap - ERR

    error "A execução foi interrompida."
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
            "Encaminhando ${signal_name} ao processo filho " \
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
# AJUDA
# ==============================================================================

show_help() {
    cat <<'HELP'
Uso:
  ./scripts/run_experiment.sh [opções]

Seleção e execução:
  --environment AMBIENTE       local ou sdumont.
  --experiment-config ARQUIVO  Arquivo principal do experimento.
  --model CHAVE                Seleciona um modelo. Pode ser repetido.
  --dataset CHAVE              Seleciona um dataset. Pode ser repetido.
  --run-id ID                  Define o identificador da execução.
  --dry-run                    Valida sem executar inferência.
  --no-dry-run                 Força a execução real.
  --log-level NÍVEL            DEBUG, INFO, WARNING, ERROR ou CRITICAL.
  --traceback                  Mostra tracebacks completos.
  --print-summary-json         Imprime o resumo final em JSON.

Preparação local:
  --skip-setup                 Não executa scripts/setup_env.sh.
  --force-setup                Reinstala requirements.txt.
  --recreate-env               Recria o ambiente virtual.
  --venv-dir CAMINHO           Pasta do ambiente virtual.
  --python EXECUTÁVEL          Python base usado para criar o venv.
  --requirements ARQUIVO       Arquivo de dependências.

Execução no SDumont:
  --sdumont-config ARQUIVO     Arquivo de configuração privada.
  --no-sync                    Não sincroniza o projeto.
  --no-remote-setup            Não prepara o ambiente remoto.
  --no-monitor                 Submete e retorna sem aguardar o job.
  --no-download                Não baixa os resultados.
  --state-file ARQUIVO         Arquivo de estado da submissão.
  --print-only                 Apenas imprime ações/comandos remotos.

Outras:
  --                           Encaminha os argumentos restantes ao runner.
  -h, --help                   Exibe esta ajuda.

Exemplos:
  ./scripts/run_experiment.sh

  ./scripts/run_experiment.sh --dry-run

  ./scripts/run_experiment.sh \
    --model finbert_ptbr \
    --dataset noticias_exemplo

  ./scripts/run_experiment.sh \
    --environment sdumont \
    --run-id experimento_001

  ./scripts/run_experiment.sh \
    --environment sdumont \
    --no-monitor \
    --no-download
HELP
}


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


resolve_project_path() {
    local value="$1"

    [[ -n "${value}" ]] || return 1

    if [[ "${value}" = /* ]]; then
        printf '%s\n' "${value}"
    else
        printf '%s\n' "${PROJECT_ROOT}/${value}"
    fi
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


require_file() {
    local path="$1"
    local description="$2"

    [[ -f "${path}" ]] || die \
        "${description} não encontrado: ${path}"

    [[ -r "${path}" ]] || die \
        "${description} sem permissão de leitura: ${path}"
}


require_executable_script() {
    local path="$1"
    local description="$2"

    require_file "${path}" "${description}"

    [[ -x "${path}" ]] || die \
        "${description} não possui permissão de execução: ${path}. " \
        "Execute: chmod +x ${path}"
}


run_child() {
    local command=("$@")
    local exit_code=0

    print_command "${command[@]}"

    set +e

    "${command[@]}" &
    CHILD_PID=$!

    wait "${CHILD_PID}"
    exit_code=$?

    CHILD_PID=""

    set -e

    return "${exit_code}"
}


append_csv_runner_arguments() {
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

            if [[ "${option_name}" == "--model" ]]; then
                MODEL_ARGUMENT_COUNT=$((MODEL_ARGUMENT_COUNT + 1))
            else
                DATASET_ARGUMENT_COUNT=$((DATASET_ARGUMENT_COUNT + 1))
            fi
        fi
    done
}


strip_yaml_comment() {
    local value="$1"

    # Os valores utilizados por este script são escalares simples.
    # Comentários após aspas não são interpretados como parte do valor.
    value="${value%%#*}"

    printf '%s\n' "${value}"
}


normalize_yaml_scalar() {
    local value="$1"

    value="$(strip_yaml_comment "${value}")"
    value="$(trim_value "${value}")"

    if [[ "${value}" == \"*\" && "${value}" == *\" ]]; then
        value="${value:1:${#value}-2}"
    elif [[ "${value}" == \'*\' && "${value}" == *\' ]]; then
        value="${value:1:${#value}-2}"
    fi

    case "$(normalize_lowercase "${value}")" in
        null|"~")
            value=""
            ;;
    esac

    printf '%s\n' "${value}"
}


read_yaml_scalar() {
    local file_path="$1"
    local section_name="$2"
    local key_name="$3"
    local raw_value=""

    raw_value="$(
        awk \
            -v section="${section_name}" \
            -v key="${key_name}" \
            '
            BEGIN {
                in_section = 0
            }

            /^[[:space:]]*#/ {
                next
            }

            /^[^[:space:]][^:]*:[[:space:]]*/ {
                line = $0
                sub(/^[[:space:]]*/, "", line)

                if (line ~ ("^" section ":[[:space:]]*($|#)")) {
                    in_section = 1
                    next
                }

                if (in_section) {
                    exit
                }
            }

            in_section {
                line = $0
                sub(/^[[:space:]]+/, "", line)

                if (line ~ ("^" key ":[[:space:]]*")) {
                    sub(("^" key ":[[:space:]]*"), "", line)
                    print line
                    exit
                }
            }
            ' \
            "${file_path}"
    )"

    normalize_yaml_scalar "${raw_value}"
}


resolve_environment() {
    local configured=""
    local normalized=""

    if [[ -n "${ENVIRONMENT_OVERRIDE}" ]]; then
        configured="${ENVIRONMENT_OVERRIDE}"
    else
        configured="$(
            read_yaml_scalar \
                "${EXPERIMENT_CONFIG_PATH}" \
                "execution" \
                "environment"
        )"
    fi

    normalized="$(normalize_lowercase "${configured}")"

    case "${normalized}" in
        local|sdumont)
            printf '%s\n' "${normalized}"
            ;;
        "")
            die \
                "execution.environment não foi encontrado em " \
                "${EXPERIMENT_CONFIG_PATH}."
            ;;
        *)
            die \
                "Ambiente inválido: ${configured}. " \
                "Use local ou sdumont."
            ;;
    esac
}


default_state_file() {
    local identifier=""

    identifier="$(
        date '+%Y%m%d_%H%M%S'
    )_$$"

    printf '%s\n' \
        "${PROJECT_ROOT}/.tmp/sdumont/submission_${identifier}.env"
}


validate_log_level() {
    local value="$1"
    local normalized=""

    normalized="$(
        printf '%s' "${value}" |
            tr '[:lower:]' '[:upper:]'
    )"

    case "${normalized}" in
        DEBUG|INFO|WARNING|ERROR|CRITICAL)
            printf '%s\n' "${normalized}"
            ;;
        *)
            die \
                "Nível de log inválido: ${value}. " \
                "Use DEBUG, INFO, WARNING, ERROR ou CRITICAL."
            ;;
    esac
}


# ==============================================================================
# ARGUMENTOS
# ==============================================================================

while [[ "$#" -gt 0 ]]; do
    case "$1" in
        --environment)
            [[ "$#" -ge 2 ]] || die \
                "--environment exige local ou sdumont."

            ENVIRONMENT_OVERRIDE="$2"
            shift 2
            ;;

        --environment=*)
            ENVIRONMENT_OVERRIDE="${1#*=}"
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

        --model)
            [[ "$#" -ge 2 ]] || die \
                "--model exige uma chave."

            RUNNER_ARGUMENTS+=("--model" "$2")
            MODEL_ARGUMENT_COUNT=$((MODEL_ARGUMENT_COUNT + 1))
            shift 2
            ;;

        --model=*)
            RUNNER_ARGUMENTS+=("--model" "${1#*=}")
            MODEL_ARGUMENT_COUNT=$((MODEL_ARGUMENT_COUNT + 1))
            shift
            ;;

        --dataset)
            [[ "$#" -ge 2 ]] || die \
                "--dataset exige uma chave."

            RUNNER_ARGUMENTS+=("--dataset" "$2")
            DATASET_ARGUMENT_COUNT=$((DATASET_ARGUMENT_COUNT + 1))
            shift 2
            ;;

        --dataset=*)
            RUNNER_ARGUMENTS+=("--dataset" "${1#*=}")
            DATASET_ARGUMENT_COUNT=$((DATASET_ARGUMENT_COUNT + 1))
            shift
            ;;

        --run-id)
            [[ "$#" -ge 2 ]] || die \
                "--run-id exige um identificador."

            RUNNER_ARGUMENTS+=("--run-id" "$2")
            RUN_ID_WAS_SET=true
            shift 2
            ;;

        --run-id=*)
            RUNNER_ARGUMENTS+=("--run-id" "${1#*=}")
            RUN_ID_WAS_SET=true
            shift
            ;;

        --dry-run)
            RUNNER_ARGUMENTS+=("--dry-run")
            DRY_RUN_WAS_SET=true
            shift
            ;;

        --no-dry-run)
            RUNNER_ARGUMENTS+=("--no-dry-run")
            DRY_RUN_WAS_SET=true
            shift
            ;;

        --log-level)
            [[ "$#" -ge 2 ]] || die \
                "--log-level exige um valor."

            RUNNER_ARGUMENTS+=(
                "--log-level"
                "$(validate_log_level "$2")"
            )
            LOG_LEVEL_WAS_SET=true
            shift 2
            ;;

        --log-level=*)
            RUNNER_ARGUMENTS+=(
                "--log-level"
                "$(validate_log_level "${1#*=}")"
            )
            LOG_LEVEL_WAS_SET=true
            shift
            ;;

        --traceback)
            RUNNER_ARGUMENTS+=("--traceback")
            TRACEBACK_WAS_SET=true
            shift
            ;;

        --print-summary-json)
            RUNNER_ARGUMENTS+=("--print-summary-json")
            PRINT_SUMMARY_WAS_SET=true
            shift
            ;;

        --skip-setup)
            LOCAL_SKIP_SETUP=true
            shift
            ;;

        --force-setup)
            LOCAL_FORCE_SETUP=true
            shift
            ;;

        --recreate-env)
            LOCAL_RECREATE_ENV=true
            shift
            ;;

        --venv-dir)
            [[ "$#" -ge 2 ]] || die \
                "--venv-dir exige um caminho."

            LOCAL_VENV_DIR="$2"
            shift 2
            ;;

        --venv-dir=*)
            LOCAL_VENV_DIR="${1#*=}"
            shift
            ;;

        --python)
            [[ "$#" -ge 2 ]] || die \
                "--python exige um executável."

            LOCAL_PYTHON="$2"
            shift 2
            ;;

        --python=*)
            LOCAL_PYTHON="${1#*=}"
            shift
            ;;

        --requirements)
            [[ "$#" -ge 2 ]] || die \
                "--requirements exige um arquivo."

            LOCAL_REQUIREMENTS="$2"
            shift 2
            ;;

        --requirements=*)
            LOCAL_REQUIREMENTS="${1#*=}"
            shift
            ;;

        --sdumont-config)
            [[ "$#" -ge 2 ]] || die \
                "--sdumont-config exige um arquivo."

            SDUMONT_CONFIG_INPUT="$2"
            shift 2
            ;;

        --sdumont-config=*)
            SDUMONT_CONFIG_INPUT="${1#*=}"
            shift
            ;;

        --no-sync)
            SDUMONT_SKIP_SYNC=true
            shift
            ;;

        --no-remote-setup)
            SDUMONT_SKIP_REMOTE_SETUP=true
            shift
            ;;

        --no-monitor)
            SDUMONT_MONITOR=false
            shift
            ;;

        --no-download)
            SDUMONT_DOWNLOAD=false
            shift
            ;;

        --state-file)
            [[ "$#" -ge 2 ]] || die \
                "--state-file exige um caminho."

            SDUMONT_STATE_FILE="$2"
            shift 2
            ;;

        --state-file=*)
            SDUMONT_STATE_FILE="${1#*=}"
            shift
            ;;

        --print-only)
            SDUMONT_PRINT_ONLY=true
            shift
            ;;

        -h|--help)
            SHOW_HELP=true
            shift
            ;;

        --)
            shift

            if [[ "$#" -gt 0 ]]; then
                RUNNER_ARGUMENTS+=("$@")
            fi

            break
            ;;

        -*)
            die "Opção desconhecida: $1"
            ;;

        *)
            die "Argumento posicional não suportado: $1"
            ;;
    esac
done

if [[ "${SHOW_HELP}" == true ]]; then
    show_help
    exit 0
fi


# ==============================================================================
# CAMINHOS E CONFIGURAÇÃO
# ==============================================================================

EXPERIMENT_CONFIG_PATH="$(
    resolve_project_path "${EXPERIMENT_CONFIG_INPUT}"
)" || die "EXPERIMENT_CONFIG não pode ficar vazio."

require_file \
    "${EXPERIMENT_CONFIG_PATH}" \
    "Arquivo do experimento"

RUN_ENVIRONMENT="$(resolve_environment)"

REMOTE_EXPERIMENT_CONFIG="$(
    relative_project_path "${EXPERIMENT_CONFIG_PATH}"
)" || true

if [[ "${RUN_ENVIRONMENT}" == "sdumont" ]]; then
    [[ -n "${REMOTE_EXPERIMENT_CONFIG}" ]] || die \
        "No SDumont, o arquivo de experimento precisa estar dentro " \
        "da raiz do projeto: ${PROJECT_ROOT}"
fi


# ==============================================================================
# VALORES OPCIONAIS RECEBIDOS PELO AMBIENTE
# ==============================================================================

if [[ "${MODEL_ARGUMENT_COUNT}" -eq 0 ]]; then
    append_csv_runner_arguments \
        "--model" \
        "${MODEL_KEYS:-}"
fi

if [[ "${DATASET_ARGUMENT_COUNT}" -eq 0 ]]; then
    append_csv_runner_arguments \
        "--dataset" \
        "${DATASET_KEYS:-}"
fi

if [[ "${RUN_ID_WAS_SET}" == false && -n "${RUN_ID:-}" ]]; then
    RUNNER_ARGUMENTS+=("--run-id" "${RUN_ID}")
fi

if [[ "${DRY_RUN_WAS_SET}" == false ]]; then
    case "$(normalize_lowercase "${DRY_RUN:-}")" in
        1|true|yes|y|on|sim|s)
            RUNNER_ARGUMENTS+=("--dry-run")
            ;;
        0|false|no|n|off|nao|não)
            RUNNER_ARGUMENTS+=("--no-dry-run")
            ;;
        ""|auto|default|yaml)
            ;;
        *)
            die \
                "DRY_RUN possui valor inválido: ${DRY_RUN}. " \
                "Use true, false ou auto."
            ;;
    esac
fi

if [[ "${LOG_LEVEL_WAS_SET}" == false && -n "${LOG_LEVEL:-}" ]]; then
    RUNNER_ARGUMENTS+=(
        "--log-level"
        "$(validate_log_level "${LOG_LEVEL}")"
    )
fi

if [[ "${TRACEBACK_WAS_SET}" == false ]]; then
    case "$(normalize_lowercase "${TRACEBACK:-}")" in
        1|true|yes|y|on|sim|s)
            RUNNER_ARGUMENTS+=("--traceback")
            ;;
    esac
fi

if [[ "${PRINT_SUMMARY_WAS_SET}" == false ]]; then
    case "$(normalize_lowercase "${PRINT_SUMMARY_JSON:-}")" in
        1|true|yes|y|on|sim|s)
            RUNNER_ARGUMENTS+=("--print-summary-json")
            ;;
    esac
fi


# ==============================================================================
# EXECUÇÃO LOCAL
# ==============================================================================

run_local() {
    local setup_script="${PROJECT_ROOT}/scripts/setup_env.sh"
    local service_script="${PROJECT_ROOT}/scripts/run_service.sh"
    local setup_command=()
    local service_command=()

    require_executable_script \
        "${service_script}" \
        "Serviço local"

    if [[ "${LOCAL_SKIP_SETUP}" == false ]]; then
        require_executable_script \
            "${setup_script}" \
            "Preparador do ambiente local"

        setup_command=(
            "${setup_script}"
            "--venv-dir"
            "${LOCAL_VENV_DIR}"
            "--python"
            "${LOCAL_PYTHON}"
            "--requirements"
            "${LOCAL_REQUIREMENTS}"
        )

        if [[ "${LOCAL_FORCE_SETUP}" == true ]]; then
            setup_command+=("--force")
        fi

        if [[ "${LOCAL_RECREATE_ENV}" == true ]]; then
            setup_command+=("--recreate")
        fi

        log "Preparando o ambiente local."

        run_child "${setup_command[@]}" || return $?
    else
        warning \
            "A preparação local foi ignorada por --skip-setup."
    fi

    service_command=(
        "${service_script}"
        "--experiment-config"
        "${EXPERIMENT_CONFIG_PATH}"
        "--environment"
        "local"
        "${RUNNER_ARGUMENTS[@]}"
    )

    log "Executando a pipeline localmente."

    VENV_DIR="${LOCAL_VENV_DIR}" \
    REQUIREMENTS_FILE="${LOCAL_REQUIREMENTS}" \
        run_child "${service_command[@]}"
}


# ==============================================================================
# EXECUÇÃO NO SDUMONT
# ==============================================================================

run_sdumont() {
    local sync_script="${PROJECT_ROOT}/scripts/sync_to_scratch.sh"
    local setup_script="${PROJECT_ROOT}/scripts/setup_sdumont_env.sh"
    local submit_script="${PROJECT_ROOT}/scripts/submit_sdumont.sh"
    local download_script="${PROJECT_ROOT}/scripts/download_sdumont_results.sh"

    local sdumont_config_path=""
    local state_file_path=""
    local sync_command=()
    local setup_command=()
    local submit_command=()
    local download_command=()
    local remote_runner_arguments=()

    sdumont_config_path="$(
        resolve_project_path "${SDUMONT_CONFIG_INPUT}"
    )" || die "SDUMONT_CONFIG não pode ficar vazio."

    require_file \
        "${sdumont_config_path}" \
        "Configuração privada do SDumont"

    require_executable_script \
        "${submit_script}" \
        "Script de submissão ao SDumont"

    if [[ "${SDUMONT_SKIP_SYNC}" == false ]]; then
        require_executable_script \
            "${sync_script}" \
            "Script de sincronização com o SDumont"
    fi

    if [[ "${SDUMONT_SKIP_REMOTE_SETUP}" == false ]]; then
        require_executable_script \
            "${setup_script}" \
            "Preparador do ambiente do SDumont"
    fi

    if [[ "${SDUMONT_DOWNLOAD}" == true ]] &&         [[ "${SDUMONT_MONITOR}" == true ]]
    then
        require_executable_script \
            "${download_script}" \
            "Script de download dos resultados"
    fi

    if [[ -n "${SDUMONT_STATE_FILE}" ]]; then
        state_file_path="$(
            resolve_project_path "${SDUMONT_STATE_FILE}"
        )"
    else
        state_file_path="$(default_state_file)"
    fi

    mkdir -p -- "$(dirname -- "${state_file_path}")"

    remote_runner_arguments=(
        "--experiment-config"
        "${REMOTE_EXPERIMENT_CONFIG}"
        "--environment"
        "sdumont"
        "${RUNNER_ARGUMENTS[@]}"
    )

    log "Fluxo remoto selecionado."
    log "Configuração do SDumont: ${sdumont_config_path}"
    log "Arquivo de estado: ${state_file_path}"

    if [[ "${SDUMONT_SKIP_SYNC}" == false ]]; then
        sync_command=(
            "${sync_script}"
            "--config"
            "${sdumont_config_path}"
            "--experiment-config"
            "${REMOTE_EXPERIMENT_CONFIG}"
        )

        if [[ "${SDUMONT_PRINT_ONLY}" == true ]]; then
            sync_command+=("--print-only")
        fi

        log "Sincronizando o projeto com o Scratch."

        run_child "${sync_command[@]}" || return $?
    else
        warning "Sincronização ignorada por --no-sync."
    fi

    if [[ "${SDUMONT_SKIP_REMOTE_SETUP}" == false ]]; then
        setup_command=(
            "${setup_script}"
            "--config"
            "${sdumont_config_path}"
        )

        if [[ "${SDUMONT_PRINT_ONLY}" == true ]]; then
            setup_command+=("--print-only")
        fi

        log "Preparando o ambiente remoto."

        run_child "${setup_command[@]}" || return $?
    else
        warning \
            "Preparação remota ignorada por --no-remote-setup."
    fi

    submit_command=(
        "${submit_script}"
        "--config"
        "${sdumont_config_path}"
        "--state-file"
        "${state_file_path}"
    )

    if [[ "${SDUMONT_MONITOR}" == false ]]; then
        submit_command+=("--no-monitor")
    fi

    if [[ "${SDUMONT_PRINT_ONLY}" == true ]]; then
        submit_command+=("--print-only")
    fi

    submit_command+=(
        "--"
        "${remote_runner_arguments[@]}"
    )

    log "Submetendo o experimento ao Slurm."

    run_child "${submit_command[@]}" || return $?

    if [[ "${SDUMONT_PRINT_ONLY}" == true ]]; then
        log "Modo print-only concluído."
        return 0
    fi

    if [[ "${SDUMONT_MONITOR}" == false ]]; then
        warning \
            "O job foi submetido sem monitoramento. " \
            "O download automático não será executado."

        return 0
    fi

    if [[ "${SDUMONT_DOWNLOAD}" == false ]]; then
        warning \
            "O job foi monitorado, mas o download foi ignorado " \
            "por --no-download."

        return 0
    fi

    download_command=(
        "${download_script}"
        "--config"
        "${sdumont_config_path}"
        "--state-file"
        "${state_file_path}"
    )

    log "Baixando os resultados concluídos."

    run_child "${download_command[@]}"
}


# ==============================================================================
# EXECUÇÃO PRINCIPAL
# ==============================================================================

log "Raiz do projeto: ${PROJECT_ROOT}"
log "Arquivo do experimento: ${EXPERIMENT_CONFIG_PATH}"
log "Ambiente resolvido: ${RUN_ENVIRONMENT}"

STARTED_AT="$(date +%s)"
EXIT_CODE=0

case "${RUN_ENVIRONMENT}" in
    local)
        run_local || EXIT_CODE=$?
        ;;

    sdumont)
        run_sdumont || EXIT_CODE=$?
        ;;
esac

FINISHED_AT="$(date +%s)"
DURATION_SECONDS=$((FINISHED_AT - STARTED_AT))

if [[ "${EXIT_CODE}" -eq 0 ]]; then
    log \
        "Fluxo ${RUN_ENVIRONMENT} concluído com sucesso em " \
        "${DURATION_SECONDS} segundo(s)."
else
    error \
        "Fluxo ${RUN_ENVIRONMENT} terminou com código " \
        "${EXIT_CODE} após ${DURATION_SECONDS} segundo(s)."
fi

exit "${EXIT_CODE}"
