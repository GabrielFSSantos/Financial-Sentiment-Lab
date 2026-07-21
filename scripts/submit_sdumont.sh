#!/usr/bin/env bash

# ==============================================================================
# SUBMISSÃO E MONITORAMENTO DE EXPERIMENTOS NO SANTOS DUMONT
# ==============================================================================
#
# Este script é o adaptador entre o fluxo local e o Slurm remoto.
#
# Uso normal:
#
#   ./scripts/submit_sdumont.sh \
#       --config configs/sdumont.env \
#       --state-file .tmp/sdumont/submission.env \
#       -- \
#       --experiment-config configs/experiment.yaml \
#       --environment sdumont
#
# Submeter sem aguardar:
#
#   ./scripts/submit_sdumont.sh \
#       --config configs/sdumont.env \
#       --state-file .tmp/sdumont/submission.env \
#       --no-monitor \
#       -- \
#       --experiment-config configs/experiment.yaml \
#       --environment sdumont
#
# Apenas visualizar:
#
#   ./scripts/submit_sdumont.sh \
#       --config configs/sdumont.env \
#       --print-only \
#       -- \
#       --experiment-config configs/experiment.yaml \
#       --environment sdumont
#
# Responsabilidades:
#
# - validar configs/sdumont.env;
# - derivar os caminhos no Scratch;
# - validar a conexão SSH e o projeto remoto;
# - montar uma única submissão sbatch;
# - encaminhar todos os argumentos após ``--`` ao job;
# - registrar os dados da submissão em um arquivo de estado;
# - monitorar o job com squeue e sacct;
# - preservar o código de saída do experimento;
# - mostrar os logs finais quando o job falhar.
#
# O script não sincroniza arquivos, não instala dependências e não baixa
# resultados. Essas responsabilidades pertencem a:
#
#   scripts/sync_to_scratch.sh
#   scripts/setup_sdumont_env.sh
#   scripts/download_sdumont_results.sh
#
# O fluxo usa somente:
#
#   jobs/sdumont/run_experiment.srm
#
# Não são utilizados arrays Slurm. Todos os pares modelo × dataset são
# executados sequencialmente pelo pipeline.runner dentro do mesmo job inicial.
# ==============================================================================

set -Eeuo pipefail
IFS=$'\n\t'


# ==============================================================================
# CONSTANTES E ESTADO
# ==============================================================================

readonly SCRIPT_NAME="submit_sdumont"
readonly EXPECTED_CONFIG_SCHEMA_VERSION="2.0"
readonly STATE_SCHEMA_VERSION="2.0"
readonly DEFAULT_CONFIG_FILE="configs/sdumont.env"
readonly DEFAULT_JOB_SCRIPT="jobs/sdumont/run_experiment.srm"

CONFIG_INPUT="${SDUMONT_CONFIG:-${DEFAULT_CONFIG_FILE}}"
STATE_FILE_INPUT=""
JOB_SCRIPT_INPUT="${DEFAULT_JOB_SCRIPT}"
JOB_NAME_OVERRIDE=""

MONITOR_OVERRIDE=""
PRINT_ONLY=false
VERBOSE=false
SKIP_CONNECTIVITY_CHECK=false
SKIP_REMOTE_VALIDATION=false
CANCEL_ON_SIGNAL_OVERRIDE=""
MONITOR_TIMEOUT_OVERRIDE=""
MONITOR_INTERVAL_OVERRIDE=""

RUNNER_ARGUMENTS=()

CHILD_PID=""
JOB_ID=""
JOB_FINISHED=false
STATE_FILE_PATH=""
CONFIG_PATH=""

declare -A STATE=()


# ==============================================================================
# LOG
# ==============================================================================

timestamp() {
    date '+%Y-%m-%d %H:%M:%S'
}


utc_timestamp() {
    date -u '+%Y-%m-%dT%H:%M:%SZ'
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
    {
        printf '[%s] [%s] Comando:' \
            "$(timestamp)" \
            "${SCRIPT_NAME}"

        printf ' %q' "$@"
        printf '\n'
    } >&2
}


# ==============================================================================
# ERROS E SINAIS
# ==============================================================================

write_state_file() {
    local temporary_file=""
    local key=""

    [[ -n "${STATE_FILE_PATH}" ]] || return 0

    mkdir -p -- "$(dirname -- "${STATE_FILE_PATH}")"

    temporary_file="$(
        mktemp \
            "$(dirname -- "${STATE_FILE_PATH}")/.submission-state.XXXXXX"
    )"

    {
        printf '# Gerado por scripts/submit_sdumont.sh\n'
        printf '# Arquivo Bash sourceable. Não edite durante o monitoramento.\n'

        for key in \
            STATE_SCHEMA_VERSION \
            STATUS \
            JOB_ID \
            JOB_NAME \
            SUBMITTED_AT \
            COMPLETED_AT \
            FINAL_STATE \
            FINAL_EXIT_CODE \
            MONITOR_ENABLED \
            CONFIG_FILE \
            SSH_TARGET \
            ACCOUNT \
            PARTITION \
            REMOTE_PROJECT_DIR \
            REMOTE_OUTPUT_DIR \
            REMOTE_LOG_DIR \
            REMOTE_TEMP_DIR \
            REMOTE_JOB_SCRIPT \
            REMOTE_STDOUT_FILE \
            REMOTE_STDERR_FILE \
            RUN_ID \
            RUNNER_ARGUMENTS \
            SLURM_ELAPSED \
            SLURM_START \
            SLURM_END \
            SLURM_NODELIST \
            MESSAGE
        do
            printf '%s=%q\n' \
                "${key}" \
                "${STATE[${key}]:-}"
        done
    } > "${temporary_file}"

    chmod 600 "${temporary_file}"
    mv -f -- "${temporary_file}" "${STATE_FILE_PATH}"
}


set_state() {
    local key="$1"
    local value="${2:-}"

    STATE["${key}"]="${value}"
}


cancel_remote_job() {
    [[ -n "${JOB_ID}" ]] || return 0
    [[ "${PRINT_ONLY}" == false ]] || return 0
    [[ "${JOB_FINISHED}" == false ]] || return 0

    warning "Solicitando o cancelamento do job ${JOB_ID}."

    run_ssh_no_capture \
        "$(shell_join "${SCANCEL_COMMAND}" "${JOB_ID}")" \
        true || warning \
        "Não foi possível confirmar o cancelamento do job ${JOB_ID}."
}


on_signal() {
    local signal_name="$1"

    trap - INT TERM HUP

    warning "Sinal ${signal_name} recebido."

    if [[ -n "${CHILD_PID}" ]] && \
        kill -0 "${CHILD_PID}" 2>/dev/null
    then
        kill "-${signal_name}" "${CHILD_PID}" 2>/dev/null || true
    fi

    if [[ "${MONITOR_CANCEL_JOB_ON_SIGNAL_EFFECTIVE:-false}" == true ]]; then
        cancel_remote_job
    else
        warning \
            "O job remoto não será cancelado automaticamente. " \
            "ID: ${JOB_ID:-ainda não submetido}"
    fi

    set_state "STATUS" "INTERRUPTED"
    set_state "FINAL_STATE" "INTERRUPTED"
    set_state "FINAL_EXIT_CODE" "130"
    set_state "COMPLETED_AT" "$(utc_timestamp)"
    set_state "MESSAGE" "Monitoramento interrompido por ${signal_name}."
    write_state_file

    exit 130
}


on_error() {
    local exit_code=$?
    local line_number="${BASH_LINENO[0]:-desconhecida}"
    local failed_command="${BASH_COMMAND:-desconhecido}"

    trap - ERR

    error "A submissão ou o monitoramento foi interrompido."
    error "Código de saída: ${exit_code}"
    error "Linha aproximada: ${line_number}"
    error "Comando: ${failed_command}"

    if [[ -n "${STATE_FILE_PATH}" ]]; then
        set_state "STATUS" "ERROR"
        set_state "FINAL_STATE" "${STATE[FINAL_STATE]:-ERROR}"
        set_state "FINAL_EXIT_CODE" "${exit_code}"
        set_state "COMPLETED_AT" "$(utc_timestamp)"
        set_state "MESSAGE" \
            "Falha local no submit_sdumont.sh: ${failed_command}"
        write_state_file
    fi

    exit "${exit_code}"
}


trap on_error ERR
trap 'on_signal INT' INT
trap 'on_signal TERM' TERM
trap 'on_signal HUP' HUP


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
  ./scripts/submit_sdumont.sh [opções] [-- argumentos-do-runner]

Configuração:
  --config ARQUIVO           Configuração privada do SDumont.
  --state-file ARQUIVO       Arquivo local de estado da submissão.
  --job-script ARQUIVO       Job Slurm relativo ao projeto.
                             Padrão: jobs/sdumont/run_experiment.srm
  --job-name NOME            Sobrescreve SLURM_JOB_NAME.

Monitoramento:
  --monitor                  Aguarda o término do job.
  --no-monitor               Retorna após a submissão.
  --monitor-timeout SEG      Sobrescreve MONITOR_TIMEOUT_SECONDS.
  --monitor-interval SEG     Sobrescreve MONITOR_INTERVAL_SECONDS.
  --cancel-on-signal         Cancela o job ao receber SIGINT/SIGTERM.
  --no-cancel-on-signal      Não cancela o job ao interromper o monitor.

Validação:
  --skip-connectivity-check  Não executa o teste SSH inicial.
  --skip-remote-validation   Não verifica o projeto remoto.
  --print-only               Apenas imprime os comandos.
  --verbose                  Exibe informações adicionais.
  -h, --help                 Exibe esta ajuda.

Tudo após ``--`` é encaminhado ao job e, posteriormente, ao
scripts/run_service.sh remoto.

Exemplos:
  ./scripts/submit_sdumont.sh \
    --config configs/sdumont.env \
    --state-file .tmp/sdumont/submission.env \
    -- \
    --experiment-config configs/experiment.yaml \
    --environment sdumont

  ./scripts/submit_sdumont.sh \
    --config configs/sdumont.env \
    --no-monitor \
    -- \
    --model finbert_ptbr \
    --dataset noticias_exemplo

  ./scripts/submit_sdumont.sh \
    --config configs/sdumont.env \
    --print-only \
    -- \
    --dry-run
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


resolve_local_command() {
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

    # Divisão literal, sem eval.
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


replace_slurm_tokens() {
    local pattern="$1"
    local job_name="$2"
    local job_id="$3"

    pattern="${pattern//%x/${job_name}}"
    pattern="${pattern//%j/${job_id}}"
    pattern="${pattern//%A/${job_id}}"
    pattern="${pattern//%a/0}"

    printf '%s\n' "${pattern}"
}


extract_runner_value() {
    local option_name="$1"
    local index=0
    local argument=""

    while (( index < ${#RUNNER_ARGUMENTS[@]} )); do
        argument="${RUNNER_ARGUMENTS[index]}"

        if [[ "${argument}" == "${option_name}" ]]; then
            if (( index + 1 < ${#RUNNER_ARGUMENTS[@]} )); then
                printf '%s\n' "${RUNNER_ARGUMENTS[index + 1]}"
                return 0
            fi
        elif [[ "${argument}" == "${option_name}="* ]]; then
            printf '%s\n' "${argument#*=}"
            return 0
        fi

        index=$((index + 1))
    done

    return 1
}


validate_runner_arguments() {
    local argument=""

    for argument in "${RUNNER_ARGUMENTS[@]}"; do
        # Bash não consegue armazenar bytes NUL em variáveis. Portanto,
        # apenas quebras de linha e retornos de carro precisam ser rejeitados.
        [[ "${argument}" != *$'\n'* ]] || die \
            "Argumento do runner contém quebra de linha."

        [[ "${argument}" != *$'\r'* ]] || die \
            "Argumento do runner contém retorno de carro."
    done
}


parse_extra_exports() {
    local raw="$1"
    local destination_name="$2"
    local -n destination="${destination_name}"
    local entries=()
    local entry=""
    local name=""
    local value=""

    [[ -n "$(trim_value "${raw}")" ]] || return 0

    IFS=',' read -r -a entries <<< "${raw}"

    for entry in "${entries[@]}"; do
        entry="$(trim_value "${entry}")"
        [[ -n "${entry}" ]] || continue

        [[ "${entry}" == *=* ]] || die \
            "SLURM_EXPORT_EXTRA precisa usar NOME=valor: ${entry}"

        name="${entry%%=*}"
        value="${entry#*=}"

        [[ "${name}" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || die \
            "Nome inválido em SLURM_EXPORT_EXTRA: ${name}"

        [[ "${value}" != *$'\n'* ]] || die \
            "Valor inválido em SLURM_EXPORT_EXTRA: ${name}"

        destination+=("${name}=${value}")
    done
}


run_ssh_no_capture() {
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


run_ssh_capture() {
    local remote_command="$1"
    local output_variable="$2"
    local tolerate_failure="${3:-false}"
    local -n output_reference="${output_variable}"
    local stdout_file=""
    local stderr_file=""
    local exit_code=0
    local command=(
        "${SSH_COMMAND_PATH}"
        "${SSH_ARGUMENTS[@]}"
        "${SSH_TARGET}"
        "${REMOTE_SHELL}"
        "-lc"
        "${remote_command}"
    )

    print_command "${command[@]}"

    if [[ "${PRINT_ONLY}" == true ]]; then
        output_reference=""
        return 0
    fi

    stdout_file="$(
        mktemp "${PROJECT_ROOT}/.tmp/sdumont/ssh-out.XXXXXX"
    )"
    stderr_file="$(
        mktemp "${PROJECT_ROOT}/.tmp/sdumont/ssh-err.XXXXXX"
    )"

    set +e

    "${command[@]}" \
        > "${stdout_file}" \
        2> "${stderr_file}" &
    CHILD_PID=$!

    wait "${CHILD_PID}"
    exit_code=$?

    CHILD_PID=""

    set -e

    output_reference="$(
        cat -- "${stdout_file}"
    )"

    if [[ -s "${stderr_file}" ]] && \
        { [[ "${VERBOSE}" == true ]] || [[ "${exit_code}" -ne 0 ]]; }
    then
        cat -- "${stderr_file}" >&2
    fi

    rm -f -- "${stdout_file}" "${stderr_file}"

    if [[ "${exit_code}" -ne 0 ]] && \
        [[ "${tolerate_failure}" != true ]]
    then
        return "${exit_code}"
    fi

    return 0
}


remote_command_exists() {
    local command_name="$1"
    local result=""

    run_ssh_capture \
        "command -v $(shell_join "${command_name}") >/dev/null 2>&1 && printf yes || printf no" \
        result \
        true

    [[ "$(trim_value "${result}")" == "yes" ]]
}


normalize_job_id() {
    local raw="$1"
    local first_line=""

    first_line="$(
        printf '%s\n' "${raw}" |
            sed -n '1p'
    )"
    first_line="$(trim_value "${first_line}")"
    first_line="${first_line%%;*}"

    [[ "${first_line}" =~ ^[0-9]+([_][0-9]+)?$ ]] || die \
        "O sbatch não retornou um ID de job válido: ${raw}"

    printf '%s\n' "${first_line}"
}


normalize_slurm_state() {
    local value="$1"

    value="$(trim_value "${value}")"
    value="${value%%+*}"
    value="${value%% *}"
    value="${value%%(*}"
    value="$(
        printf '%s' "${value}" |
            tr '[:lower:]' '[:upper:]'
    )"

    printf '%s\n' "${value}"
}


slurm_state_is_success() {
    [[ "$(normalize_slurm_state "$1")" == "COMPLETED" ]]
}


slurm_state_is_terminal() {
    local state=""

    state="$(normalize_slurm_state "$1")"

    case "${state}" in
        COMPLETED|CANCELLED|FAILED|TIMEOUT|NODE_FAIL|OUT_OF_MEMORY|\
        PREEMPTED|BOOT_FAIL|DEADLINE|REVOKED|SPECIAL_EXIT)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}


query_queue_state() {
    local output=""

    run_ssh_capture \
        "$(shell_join "${SQUEUE_COMMAND}" -h -j "${JOB_ID}" -o '%T') | head -n 1" \
        output \
        true

    trim_value "${output}"
}


query_accounting_record() {
    local output=""
    local command=""

    command="$(
        shell_join \
            "${SACCT_COMMAND}" \
            -n \
            -P \
            -j "${JOB_ID}" \
            --format=JobIDRaw,State,ExitCode,Elapsed,Start,End,NodeList
    )"

    command+=" | awk -F'|' -v requested="
    command+="$(printf '%q' "${JOB_ID}")"
    command+=" '\$1 == requested {print; exit}'"

    run_ssh_capture "${command}" output true
    trim_value "${output}"
}


query_scontrol_state() {
    local output=""

    run_ssh_capture \
        "$(shell_join "${SCONTROL_COMMAND}" show job "${JOB_ID}" -o)" \
        output \
        true

    printf '%s\n' "${output}"
}


show_failure_logs() {
    local tail_lines="${SLURM_FAILURE_LOG_LINES}"
    local remote_command=""

    [[ -n "${REMOTE_STDOUT_FILE}" ]] || return 0
    [[ -n "${REMOTE_STDERR_FILE}" ]] || return 0

    remote_command="$(
        printf \
            'for file in %q %q; do if [[ -f "$file" ]]; then printf "\\n===== %%s =====\\n" "$file"; tail -n %q -- "$file"; fi; done' \
            "${REMOTE_STDERR_FILE}" \
            "${REMOTE_STDOUT_FILE}" \
            "${tail_lines}"
    )"

    warning \
        "Exibindo as últimas ${tail_lines} linhas dos logs do job."

    run_ssh_no_capture "${remote_command}" true
}


monitor_job() {
    local started_epoch=""
    local now_epoch=""
    local elapsed_monitor=""
    local queue_state=""
    local previous_state=""
    local accounting_record=""
    local accounting_attempt=0
    local job_id_raw=""
    local final_state=""
    local exit_code=""
    local slurm_elapsed=""
    local slurm_start=""
    local slurm_end=""
    local node_list=""
    local scontrol_record=""

    started_epoch="$(date +%s)"

    set_state "STATUS" "MONITORING"
    set_state "MESSAGE" "Monitorando o job no Slurm."
    write_state_file

    log "Monitorando o job ${JOB_ID}."

    while true; do
        queue_state="$(query_queue_state)"

        if [[ -n "${queue_state}" ]]; then
            queue_state="$(normalize_slurm_state "${queue_state}")"

            if [[ "${queue_state}" != "${previous_state}" ]]; then
                log "Estado do job ${JOB_ID}: ${queue_state}"
                previous_state="${queue_state}"
                set_state "STATUS" "${queue_state}"
                set_state "FINAL_STATE" ""
                set_state "MESSAGE" \
                    "Job presente no squeue com estado ${queue_state}."
                write_state_file
            fi
        else
            break
        fi

        if (( MONITOR_TIMEOUT_SECONDS_EFFECTIVE > 0 )); then
            now_epoch="$(date +%s)"
            elapsed_monitor=$((now_epoch - started_epoch))

            if (( elapsed_monitor >= MONITOR_TIMEOUT_SECONDS_EFFECTIVE )); then
                set_state "STATUS" "MONITOR_TIMEOUT"
                set_state "FINAL_STATE" "MONITOR_TIMEOUT"
                set_state "FINAL_EXIT_CODE" "124"
                set_state "COMPLETED_AT" "$(utc_timestamp)"
                set_state "MESSAGE" \
                    "Tempo máximo do monitor local excedido."
                write_state_file

                die \
                    "O monitor atingiu o limite de " \
                    "${MONITOR_TIMEOUT_SECONDS_EFFECTIVE} segundo(s). " \
                    "O job ${JOB_ID} pode continuar em execução."
            fi
        fi

        sleep "${MONITOR_INTERVAL_SECONDS_EFFECTIVE}"
    done

    if (( MONITOR_ACCOUNTING_GRACE_SECONDS > 0 )); then
        log \
            "Job ausente do squeue; aguardando " \
            "${MONITOR_ACCOUNTING_GRACE_SECONDS} segundo(s) " \
            "para a contabilização."

        sleep "${MONITOR_ACCOUNTING_GRACE_SECONDS}"
    fi

    while (( accounting_attempt < MONITOR_ACCOUNTING_RETRIES )); do
        accounting_attempt=$((accounting_attempt + 1))
        accounting_record="$(query_accounting_record)"

        if [[ -n "${accounting_record}" ]]; then
            break
        fi

        if (( accounting_attempt < MONITOR_ACCOUNTING_RETRIES )); then
            sleep "${MONITOR_ACCOUNTING_RETRY_SECONDS}"
        fi
    done

    if [[ -n "${accounting_record}" ]]; then
        IFS='|' read -r \
            job_id_raw \
            final_state \
            exit_code \
            slurm_elapsed \
            slurm_start \
            slurm_end \
            node_list \
            <<< "${accounting_record}"

        final_state="$(normalize_slurm_state "${final_state}")"
    else
        warning \
            "O sacct não retornou o registro principal do job. " \
            "Tentando scontrol."

        scontrol_record="$(query_scontrol_state)"

        if [[ "${scontrol_record}" =~ JobState=([^[:space:]]+) ]]; then
            final_state="$(
                normalize_slurm_state "${BASH_REMATCH[1]}"
            )"
        else
            final_state="UNKNOWN"
        fi

        if [[ "${scontrol_record}" =~ ExitCode=([^[:space:]]+) ]]; then
            exit_code="${BASH_REMATCH[1]}"
        else
            exit_code=""
        fi

        if [[ "${scontrol_record}" =~ RunTime=([^[:space:]]+) ]]; then
            slurm_elapsed="${BASH_REMATCH[1]}"
        fi

        if [[ "${scontrol_record}" =~ NodeList=([^[:space:]]+) ]]; then
            node_list="${BASH_REMATCH[1]}"
        fi
    fi

    JOB_FINISHED=true

    set_state "FINAL_STATE" "${final_state}"
    set_state "FINAL_EXIT_CODE" "${exit_code}"
    set_state "COMPLETED_AT" "$(utc_timestamp)"
    set_state "SLURM_ELAPSED" "${slurm_elapsed}"
    set_state "SLURM_START" "${slurm_start}"
    set_state "SLURM_END" "${slurm_end}"
    set_state "SLURM_NODELIST" "${node_list}"

    if slurm_state_is_success "${final_state}"; then
        set_state "STATUS" "COMPLETED"
        set_state "MESSAGE" "Job concluído com sucesso."
        write_state_file

        log "Job ${JOB_ID} concluído com sucesso."
        return 0
    fi

    set_state "STATUS" "FAILED"
    set_state "MESSAGE" \
        "Job terminou no estado ${final_state}; ExitCode=${exit_code}."
    write_state_file

    error \
        "Job ${JOB_ID} terminou no estado ${final_state}. " \
        "ExitCode=${exit_code:-não informado}."

    show_failure_logs
    return 1
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
                "--state-file exige um caminho."

            STATE_FILE_INPUT="$2"
            shift 2
            ;;

        --state-file=*)
            STATE_FILE_INPUT="${1#*=}"
            shift
            ;;

        --job-script)
            [[ "$#" -ge 2 ]] || die \
                "--job-script exige um arquivo."

            JOB_SCRIPT_INPUT="$2"
            shift 2
            ;;

        --job-script=*)
            JOB_SCRIPT_INPUT="${1#*=}"
            shift
            ;;

        --job-name)
            [[ "$#" -ge 2 ]] || die \
                "--job-name exige um nome."

            JOB_NAME_OVERRIDE="$2"
            shift 2
            ;;

        --job-name=*)
            JOB_NAME_OVERRIDE="${1#*=}"
            shift
            ;;

        --monitor)
            MONITOR_OVERRIDE="true"
            shift
            ;;

        --no-monitor)
            MONITOR_OVERRIDE="false"
            shift
            ;;

        --monitor-timeout)
            [[ "$#" -ge 2 ]] || die \
                "--monitor-timeout exige segundos."

            MONITOR_TIMEOUT_OVERRIDE="$2"
            shift 2
            ;;

        --monitor-timeout=*)
            MONITOR_TIMEOUT_OVERRIDE="${1#*=}"
            shift
            ;;

        --monitor-interval)
            [[ "$#" -ge 2 ]] || die \
                "--monitor-interval exige segundos."

            MONITOR_INTERVAL_OVERRIDE="$2"
            shift 2
            ;;

        --monitor-interval=*)
            MONITOR_INTERVAL_OVERRIDE="${1#*=}"
            shift
            ;;

        --cancel-on-signal)
            CANCEL_ON_SIGNAL_OVERRIDE="true"
            shift
            ;;

        --no-cancel-on-signal)
            CANCEL_ON_SIGNAL_OVERRIDE="false"
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
            RUNNER_ARGUMENTS=("$@")
            break
            ;;

        -*)
            die \
                "Opção desconhecida: $1. " \
                "Use -- para iniciar os argumentos do runner."
            ;;

        *)
            die \
                "Argumento posicional não suportado antes de --: $1"
            ;;
    esac
done

validate_runner_arguments


# ==============================================================================
# CONFIGURAÇÃO
# ==============================================================================

CONFIG_PATH="$(canonical_existing_file "${CONFIG_INPUT}")" || die \
    "Configuração do SDumont não encontrada: ${CONFIG_INPUT}"

LOCAL_JOB_SCRIPT_PATH="$(
    canonical_existing_file "${JOB_SCRIPT_INPUT}"
)" || die \
    "Job Slurm local não encontrado: ${JOB_SCRIPT_INPUT}"

JOB_SCRIPT_RELATIVE="$(
    relative_project_path "${LOCAL_JOB_SCRIPT_PATH}"
)" || die \
    "O job Slurm precisa estar dentro do projeto: " \
    "${LOCAL_JOB_SCRIPT_PATH}"

if [[ -z "${STATE_FILE_INPUT}" ]]; then
    STATE_FILE_INPUT=".tmp/sdumont/submission_$(date '+%Y%m%d_%H%M%S')_$$.env"
fi

STATE_FILE_PATH="$(resolve_project_path "${STATE_FILE_INPUT}")"

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
: "${REMOTE_HF_HOME:=}"
: "${REMOTE_OUTPUT_DIR:=}"
: "${REMOTE_LOG_DIR:=}"
: "${REMOTE_TEMP_DIR:=}"

: "${MODULE_PURGE:=true}"
: "${CUDA_MODULE:=}"
: "${ADDITIONAL_MODULES:=}"
: "${MODULE_COMMAND:=module}"

: "${TRANSFORMERS_OFFLINE:=1}"
: "${HF_HUB_OFFLINE:=1}"
: "${HF_HUB_DISABLE_TELEMETRY:=1}"
: "${TOKENIZERS_PARALLELISM:=false}"

: "${SLURM_JOB_NAME:=financial-sentiment}"
: "${SLURM_TIME:=01:00:00}"
: "${SLURM_NODES:=1}"
: "${SLURM_NTASKS:=1}"
: "${SLURM_CPUS_PER_TASK:=4}"
: "${SLURM_GPUS:=1}"
: "${SLURM_GPU_TYPE:=}"
: "${SLURM_MEM:=32G}"
: "${SLURM_QOS:=}"
: "${SLURM_CONSTRAINT:=}"
: "${SLURM_RESERVATION:=}"
: "${SLURM_EXCLUSIVE:=false}"
: "${SLURM_DEPENDENCY:=}"
: "${SLURM_MAIL_TYPE:=NONE}"
: "${SLURM_MAIL_USER:=}"
: "${SLURM_EXPORT_EXTRA:=}"
: "${SLURM_ADDITIONAL_OPTIONS:=}"

: "${SBATCH_COMMAND:=sbatch}"
: "${SQUEUE_COMMAND:=squeue}"
: "${SACCT_COMMAND:=sacct}"
: "${SCONTROL_COMMAND:=scontrol}"
: "${SCANCEL_COMMAND:=scancel}"

: "${SLURM_STDOUT_PATTERN:=slurm/%x-%j.out}"
: "${SLURM_STDERR_PATTERN:=slurm/%x-%j.err}"
: "${SLURM_FAILURE_LOG_LINES:=200}"

: "${MONITOR_INTERVAL_SECONDS:=30}"
: "${MONITOR_TIMEOUT_SECONDS:=0}"
: "${MONITOR_ACCOUNTING_GRACE_SECONDS:=15}"
: "${MONITOR_ACCOUNTING_RETRIES:=10}"
: "${MONITOR_ACCOUNTING_RETRY_SECONDS:=10}"
: "${MONITOR_CANCEL_JOB_ON_SIGNAL:=false}"

: "${REQUIRE_ABSOLUTE_REMOTE_PATHS:=true}"
: "${REQUIRE_REMOTE_PATH_UNDER_SCRATCH:=true}"
: "${VALIDATE_REMOTE_PROJECT:=true}"

: "${SSH_COMMAND:=ssh}"
: "${REMOTE_SHELL:=bash}"


# ==============================================================================
# VALIDAÇÃO
# ==============================================================================

[[ "${SDUMONT_CONFIG_SCHEMA_VERSION}" == \
    "${EXPECTED_CONFIG_SCHEMA_VERSION}" ]] || die \
    "Versão de configuração incompatível. " \
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

require_positive_integer "${SLURM_NODES}" "SLURM_NODES"
require_positive_integer "${SLURM_NTASKS}" "SLURM_NTASKS"
require_positive_integer \
    "${SLURM_CPUS_PER_TASK}" \
    "SLURM_CPUS_PER_TASK"
require_non_negative_integer "${SLURM_GPUS}" "SLURM_GPUS"
require_positive_integer \
    "${SLURM_FAILURE_LOG_LINES}" \
    "SLURM_FAILURE_LOG_LINES"

require_positive_integer \
    "${MONITOR_INTERVAL_SECONDS}" \
    "MONITOR_INTERVAL_SECONDS"
require_non_negative_integer \
    "${MONITOR_TIMEOUT_SECONDS}" \
    "MONITOR_TIMEOUT_SECONDS"
require_non_negative_integer \
    "${MONITOR_ACCOUNTING_GRACE_SECONDS}" \
    "MONITOR_ACCOUNTING_GRACE_SECONDS"
require_positive_integer \
    "${MONITOR_ACCOUNTING_RETRIES}" \
    "MONITOR_ACCOUNTING_RETRIES"
require_positive_integer \
    "${MONITOR_ACCOUNTING_RETRY_SECONDS}" \
    "MONITOR_ACCOUNTING_RETRY_SECONDS"

SSH_BATCH_MODE="$(normalize_boolean "${SSH_BATCH_MODE}" "SSH_BATCH_MODE")"
MODULE_PURGE="$(normalize_boolean "${MODULE_PURGE}" "MODULE_PURGE")"
SLURM_EXCLUSIVE="$(
    normalize_boolean "${SLURM_EXCLUSIVE}" "SLURM_EXCLUSIVE"
)"
MONITOR_CANCEL_JOB_ON_SIGNAL="$(
    normalize_boolean \
        "${MONITOR_CANCEL_JOB_ON_SIGNAL}" \
        "MONITOR_CANCEL_JOB_ON_SIGNAL"
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
VALIDATE_REMOTE_PROJECT="$(
    normalize_boolean \
        "${VALIDATE_REMOTE_PROJECT}" \
        "VALIDATE_REMOTE_PROJECT"
)"

if [[ -n "${MONITOR_OVERRIDE}" ]]; then
    MONITOR_ENABLED="${MONITOR_OVERRIDE}"
else
    MONITOR_ENABLED="true"
fi

if [[ -n "${CANCEL_ON_SIGNAL_OVERRIDE}" ]]; then
    MONITOR_CANCEL_JOB_ON_SIGNAL_EFFECTIVE="$(
        normalize_boolean \
            "${CANCEL_ON_SIGNAL_OVERRIDE}" \
            "cancel-on-signal"
    )"
else
    MONITOR_CANCEL_JOB_ON_SIGNAL_EFFECTIVE="$(
        normalize_boolean \
            "${MONITOR_CANCEL_JOB_ON_SIGNAL}" \
            "MONITOR_CANCEL_JOB_ON_SIGNAL"
    )"
fi

if [[ -n "${MONITOR_TIMEOUT_OVERRIDE}" ]]; then
    require_non_negative_integer \
        "${MONITOR_TIMEOUT_OVERRIDE}" \
        "monitor-timeout"
    MONITOR_TIMEOUT_SECONDS_EFFECTIVE="${MONITOR_TIMEOUT_OVERRIDE}"
else
    MONITOR_TIMEOUT_SECONDS_EFFECTIVE="${MONITOR_TIMEOUT_SECONDS}"
fi

if [[ -n "${MONITOR_INTERVAL_OVERRIDE}" ]]; then
    require_positive_integer \
        "${MONITOR_INTERVAL_OVERRIDE}" \
        "monitor-interval"
    MONITOR_INTERVAL_SECONDS_EFFECTIVE="${MONITOR_INTERVAL_OVERRIDE}"
else
    MONITOR_INTERVAL_SECONDS_EFFECTIVE="${MONITOR_INTERVAL_SECONDS}"
fi

require_non_empty "${SLURM_JOB_NAME}" "SLURM_JOB_NAME"
require_non_empty "${SLURM_TIME}" "SLURM_TIME"

if [[ ! "${SLURM_JOB_NAME}" =~ ^[A-Za-z0-9._-]+$ ]]; then
    die \
        "SLURM_JOB_NAME possui caracteres inválidos: ${SLURM_JOB_NAME}"
fi

if [[ -n "${JOB_NAME_OVERRIDE}" ]]; then
    EFFECTIVE_JOB_NAME="${JOB_NAME_OVERRIDE}"
else
    EFFECTIVE_JOB_NAME="${SLURM_JOB_NAME}"
fi

[[ "${EFFECTIVE_JOB_NAME}" =~ ^[A-Za-z0-9._-]+$ ]] || die \
    "Nome do job inválido: ${EFFECTIVE_JOB_NAME}"

validate_remote_path "${SCRATCH_DIR}" "SCRATCH_DIR"

if [[ -z "${REMOTE_PROJECT_DIR}" ]]; then
    REMOTE_PROJECT_DIR="${SCRATCH_DIR%/}/${REMOTE_PROJECT_NAME}"
fi

if [[ -z "${REMOTE_VENV_DIR}" ]]; then
    REMOTE_VENV_DIR="${SCRATCH_DIR%/}/.venvs/${REMOTE_PROJECT_NAME}"
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
            "${field_name} precisa estar abaixo de SCRATCH_DIR."
    fi
done

REMOTE_JOB_SCRIPT="${REMOTE_PROJECT_DIR%/}/${JOB_SCRIPT_RELATIVE}"

validate_remote_path "${REMOTE_JOB_SCRIPT}" "REMOTE_JOB_SCRIPT"

if is_true "${REQUIRE_REMOTE_PATH_UNDER_SCRATCH}"; then
    path_is_under "${REMOTE_JOB_SCRIPT}" "${SCRATCH_DIR}" || die \
        "REMOTE_JOB_SCRIPT precisa estar abaixo de SCRATCH_DIR."
fi

if [[ -n "${SSH_IDENTITY_FILE}" ]]; then
    SSH_IDENTITY_FILE="$(resolve_project_path "${SSH_IDENTITY_FILE}")"

    [[ -f "${SSH_IDENTITY_FILE}" ]] || die \
        "Chave SSH não encontrada: ${SSH_IDENTITY_FILE}"
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
# SSH
# ==============================================================================

SSH_COMMAND_PATH="$(
    resolve_local_command "${SSH_COMMAND}" "SSH_COMMAND"
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


# ==============================================================================
# LOGS E ESTADO INICIAL
# ==============================================================================

REMOTE_STDOUT_PATTERN_ABSOLUTE="$(
    if [[ "${SLURM_STDOUT_PATTERN}" = /* ]]; then
        printf '%s\n' "${SLURM_STDOUT_PATTERN}"
    else
        printf '%s/%s\n' \
            "${REMOTE_LOG_DIR%/}" \
            "${SLURM_STDOUT_PATTERN}"
    fi
)"

REMOTE_STDERR_PATTERN_ABSOLUTE="$(
    if [[ "${SLURM_STDERR_PATTERN}" = /* ]]; then
        printf '%s\n' "${SLURM_STDERR_PATTERN}"
    else
        printf '%s/%s\n' \
            "${REMOTE_LOG_DIR%/}" \
            "${SLURM_STDERR_PATTERN}"
    fi
)"

RUN_ID="$(extract_runner_value "--run-id" || true)"
RUNNER_ARGUMENTS_JOINED="$(shell_join "${RUNNER_ARGUMENTS[@]}")"

set_state "STATE_SCHEMA_VERSION" "${STATE_SCHEMA_VERSION}"
set_state "STATUS" "INITIALIZED"
set_state "JOB_ID" ""
set_state "JOB_NAME" "${EFFECTIVE_JOB_NAME}"
set_state "SUBMITTED_AT" ""
set_state "COMPLETED_AT" ""
set_state "FINAL_STATE" ""
set_state "FINAL_EXIT_CODE" ""
set_state "MONITOR_ENABLED" "${MONITOR_ENABLED}"
set_state "CONFIG_FILE" "${CONFIG_PATH}"
set_state "SSH_TARGET" "${SSH_TARGET}"
set_state "ACCOUNT" "${ACCOUNT}"
set_state "PARTITION" "${PARTITION}"
set_state "REMOTE_PROJECT_DIR" "${REMOTE_PROJECT_DIR}"
set_state "REMOTE_OUTPUT_DIR" "${REMOTE_OUTPUT_DIR}"
set_state "REMOTE_LOG_DIR" "${REMOTE_LOG_DIR}"
set_state "REMOTE_TEMP_DIR" "${REMOTE_TEMP_DIR}"
set_state "REMOTE_JOB_SCRIPT" "${REMOTE_JOB_SCRIPT}"
set_state "REMOTE_STDOUT_FILE" ""
set_state "REMOTE_STDERR_FILE" ""
set_state "RUN_ID" "${RUN_ID}"
set_state "RUNNER_ARGUMENTS" "${RUNNER_ARGUMENTS_JOINED}"
set_state "SLURM_ELAPSED" ""
set_state "SLURM_START" ""
set_state "SLURM_END" ""
set_state "SLURM_NODELIST" ""
set_state "MESSAGE" "Configuração validada."
write_state_file


# ==============================================================================
# COMANDOS REMOTOS E SBATCH
# ==============================================================================

if [[ "${SKIP_CONNECTIVITY_CHECK}" == false ]]; then
    log "Validando a conexão SSH."

    run_ssh_no_capture \
        "printf '%s\n' 'Conexão SSH validada.'" || die \
        "Não foi possível conectar a ${SSH_TARGET}."
else
    warning "Teste de conectividade ignorado."
fi

PREPARE_REMOTE_COMMAND="$(
    printf \
        'set -Eeuo pipefail; mkdir -p -- %q %q %q %q; test -d %q' \
        "${REMOTE_OUTPUT_DIR}" \
        "${REMOTE_LOG_DIR}" \
        "${REMOTE_TEMP_DIR}" \
        "$(dirname -- "${REMOTE_STDOUT_PATTERN_ABSOLUTE}")" \
        "${REMOTE_PROJECT_DIR}"
)"

log "Preparando diretórios para a submissão."

run_ssh_no_capture "${PREPARE_REMOTE_COMMAND}" || die \
    "Não foi possível preparar os diretórios remotos."

if [[ "${SKIP_REMOTE_VALIDATION}" == false ]] && \
    [[ "${VALIDATE_REMOTE_PROJECT}" == true ]]
then
    REMOTE_VALIDATION_COMMAND="$(
        printf \
            'set -Eeuo pipefail; test -f %q; test -f %q; test -x %q; test -f %q' \
            "${REMOTE_PROJECT_DIR}/pipeline/runner.py" \
            "${REMOTE_PROJECT_DIR}/requirements.txt" \
            "${REMOTE_PROJECT_DIR}/scripts/run_service.sh" \
            "${REMOTE_JOB_SCRIPT}"
    )"

    log "Validando o projeto remoto."

    run_ssh_no_capture "${REMOTE_VALIDATION_COMMAND}" || die \
        "O projeto remoto não está pronto para submissão."
else
    warning "Validação do projeto remoto desativada."
fi

ENV_ASSIGNMENTS=(
    "FINANCIAL_SENTIMENT_PROJECT_DIR=${REMOTE_PROJECT_DIR}"
    "FINANCIAL_SENTIMENT_VENV_DIR=${REMOTE_VENV_DIR}"
    "FINANCIAL_SENTIMENT_OUTPUT_DIR=${REMOTE_OUTPUT_DIR}"
    "FINANCIAL_SENTIMENT_LOG_DIR=${REMOTE_LOG_DIR}"
    "FINANCIAL_SENTIMENT_TEMP_DIR=${REMOTE_TEMP_DIR}"
    "EXECUTION_ENVIRONMENT=sdumont"
    "VENV_DIR=${REMOTE_VENV_DIR}"
    "PYTHON_BIN=${REMOTE_VENV_DIR%/}/bin/python"
    "PYTHONUNBUFFERED=1"
    "PYTHONIOENCODING=utf-8"
    "PYTHONPATH=${REMOTE_PROJECT_DIR}"
    "PYTHON_MODULE=${PYTHON_MODULE}"
    "CUDA_MODULE=${CUDA_MODULE}"
    "ADDITIONAL_MODULES=${ADDITIONAL_MODULES}"
    "MODULE_PURGE=${MODULE_PURGE}"
    "MODULE_COMMAND=${MODULE_COMMAND}"
    "HF_HOME=${REMOTE_HF_HOME}"
    "TRANSFORMERS_OFFLINE=${TRANSFORMERS_OFFLINE}"
    "HF_HUB_OFFLINE=${HF_HUB_OFFLINE}"
    "HF_HUB_DISABLE_TELEMETRY=${HF_HUB_DISABLE_TELEMETRY}"
    "TOKENIZERS_PARALLELISM=${TOKENIZERS_PARALLELISM}"
    "OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK}"
    "MKL_NUM_THREADS=${SLURM_CPUS_PER_TASK}"
    "NUMEXPR_NUM_THREADS=${SLURM_CPUS_PER_TASK}"
)

parse_extra_exports \
    "${SLURM_EXPORT_EXTRA}" \
    "ENV_ASSIGNMENTS"

SBATCH_ARGUMENTS=(
    "--parsable"
    "--job-name=${EFFECTIVE_JOB_NAME}"
    "--account=${ACCOUNT}"
    "--partition=${PARTITION}"
    "--nodes=${SLURM_NODES}"
    "--ntasks=${SLURM_NTASKS}"
    "--cpus-per-task=${SLURM_CPUS_PER_TASK}"
    "--time=${SLURM_TIME}"
    "--output=${REMOTE_STDOUT_PATTERN_ABSOLUTE}"
    "--error=${REMOTE_STDERR_PATTERN_ABSOLUTE}"
    "--chdir=${REMOTE_PROJECT_DIR}"
    "--export=ALL"
)

if [[ -n "${SLURM_MEM}" ]]; then
    SBATCH_ARGUMENTS+=("--mem=${SLURM_MEM}")
fi

if (( SLURM_GPUS > 0 )); then
    if [[ -n "${SLURM_GPU_TYPE}" ]]; then
        SBATCH_ARGUMENTS+=(
            "--gres=gpu:${SLURM_GPU_TYPE}:${SLURM_GPUS}"
        )
    else
        SBATCH_ARGUMENTS+=("--gpus=${SLURM_GPUS}")
    fi
fi

if [[ -n "${SLURM_QOS}" ]]; then
    SBATCH_ARGUMENTS+=("--qos=${SLURM_QOS}")
fi

if [[ -n "${SLURM_CONSTRAINT}" ]]; then
    SBATCH_ARGUMENTS+=("--constraint=${SLURM_CONSTRAINT}")
fi

if [[ -n "${SLURM_RESERVATION}" ]]; then
    SBATCH_ARGUMENTS+=("--reservation=${SLURM_RESERVATION}")
fi

if [[ "${SLURM_EXCLUSIVE}" == true ]]; then
    SBATCH_ARGUMENTS+=("--exclusive")
fi

if [[ -n "${SLURM_DEPENDENCY}" ]]; then
    SBATCH_ARGUMENTS+=("--dependency=${SLURM_DEPENDENCY}")
fi

if [[ "$(normalize_lowercase "${SLURM_MAIL_TYPE}")" != "none" ]]; then
    require_non_empty "${SLURM_MAIL_USER}" "SLURM_MAIL_USER"

    SBATCH_ARGUMENTS+=(
        "--mail-user=${SLURM_MAIL_USER}"
        "--mail-type=${SLURM_MAIL_TYPE}"
    )
fi

split_literal_options \
    "${SLURM_ADDITIONAL_OPTIONS}" \
    "SBATCH_ARGUMENTS"

REMOTE_SUBMIT_ARRAY=(
    env
    "${ENV_ASSIGNMENTS[@]}"
    "${SBATCH_COMMAND}"
    "${SBATCH_ARGUMENTS[@]}"
    "${REMOTE_JOB_SCRIPT}"
    "${RUNNER_ARGUMENTS[@]}"
)

REMOTE_SUBMIT_COMMAND="$(
    shell_join "${REMOTE_SUBMIT_ARRAY[@]}"
)"

log "Resumo da submissão:"
printf '  Job: %s\n' "${EFFECTIVE_JOB_NAME}"
printf '  Conta: %s\n' "${ACCOUNT}"
printf '  Partição: %s\n' "${PARTITION}"
printf '  Tempo: %s\n' "${SLURM_TIME}"
printf '  Nós: %s\n' "${SLURM_NODES}"
printf '  Tarefas: %s\n' "${SLURM_NTASKS}"
printf '  CPUs/tarefa: %s\n' "${SLURM_CPUS_PER_TASK}"
printf '  GPUs: %s\n' "${SLURM_GPUS}"
printf '  Memória: %s\n' "${SLURM_MEM:-padrão da partição}"
printf '  Projeto: %s\n' "${REMOTE_PROJECT_DIR}"
printf '  Job script: %s\n' "${REMOTE_JOB_SCRIPT}"
printf '  Estado local: %s\n' "${STATE_FILE_PATH}"

if (( ${#RUNNER_ARGUMENTS[@]} > 0 )); then
    printf '  Argumentos do runner:'
    printf ' %q' "${RUNNER_ARGUMENTS[@]}"
    printf '\n'
else
    printf '  Argumentos do runner: definidos pelos YAMLs\n'
fi

if [[ "${PRINT_ONLY}" == true ]]; then
    warning "Modo print-only: nenhum job será submetido."
    print_command \
        "${SSH_COMMAND_PATH}" \
        "${SSH_ARGUMENTS[@]}" \
        "${SSH_TARGET}" \
        "${REMOTE_SHELL}" \
        "-lc" \
        "${REMOTE_SUBMIT_COMMAND}"

    set_state "STATUS" "PRINT_ONLY"
    set_state "FINAL_STATE" "PRINT_ONLY"
    set_state "FINAL_EXIT_CODE" "0"
    set_state "COMPLETED_AT" "$(utc_timestamp)"
    set_state "MESSAGE" "Comando sbatch apenas exibido."
    write_state_file

    exit 0
fi


# ==============================================================================
# SUBMISSÃO
# ==============================================================================

SUBMISSION_OUTPUT=""

log "Submetendo o job ao Slurm."

run_ssh_capture \
    "${REMOTE_SUBMIT_COMMAND}" \
    SUBMISSION_OUTPUT || die \
    "O comando sbatch terminou com falha."

JOB_ID="$(normalize_job_id "${SUBMISSION_OUTPUT}")"

REMOTE_STDOUT_FILE="$(
    replace_slurm_tokens \
        "${REMOTE_STDOUT_PATTERN_ABSOLUTE}" \
        "${EFFECTIVE_JOB_NAME}" \
        "${JOB_ID}"
)"

REMOTE_STDERR_FILE="$(
    replace_slurm_tokens \
        "${REMOTE_STDERR_PATTERN_ABSOLUTE}" \
        "${EFFECTIVE_JOB_NAME}" \
        "${JOB_ID}"
)"

set_state "STATUS" "SUBMITTED"
set_state "JOB_ID" "${JOB_ID}"
set_state "SUBMITTED_AT" "$(utc_timestamp)"
set_state "REMOTE_STDOUT_FILE" "${REMOTE_STDOUT_FILE}"
set_state "REMOTE_STDERR_FILE" "${REMOTE_STDERR_FILE}"
set_state "MESSAGE" "Job submetido ao Slurm."
write_state_file

log "Job submetido com ID ${JOB_ID}."
log "Saída Slurm: ${REMOTE_STDOUT_FILE}"
log "Erro Slurm: ${REMOTE_STDERR_FILE}"

if [[ "${MONITOR_ENABLED}" == false ]]; then
    set_state "STATUS" "SUBMITTED"
    set_state "MESSAGE" \
        "Job submetido sem monitoramento local."
    write_state_file

    log \
        "Monitoramento desativado. Consulte o job com: " \
        "${SQUEUE_COMMAND} -j ${JOB_ID}"

    exit 0
fi


# ==============================================================================
# MONITORAMENTO
# ==============================================================================

monitor_job