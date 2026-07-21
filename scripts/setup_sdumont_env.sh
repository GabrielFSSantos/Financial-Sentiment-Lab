#!/usr/bin/env bash

# ==============================================================================
# PREPARAÇÃO DO AMBIENTE PYTHON NO SANTOS DUMONT
# ==============================================================================
#
# Cria, atualiza ou valida o ambiente virtual remoto utilizado pela pipeline.
#
# Uso normal:
#
#   ./scripts/setup_sdumont_env.sh \
#       --config configs/sdumont.env
#
# Reinstalar dependências:
#
#   ./scripts/setup_sdumont_env.sh \
#       --config configs/sdumont.env \
#       --force
#
# Recriar o ambiente remoto:
#
#   ./scripts/setup_sdumont_env.sh \
#       --config configs/sdumont.env \
#       --recreate
#
# Apenas validar:
#
#   ./scripts/setup_sdumont_env.sh \
#       --config configs/sdumont.env \
#       --check
#
# Este script:
#
# - valida a configuração privada;
# - conecta ao nó de login por SSH;
# - carrega os módulos configurados;
# - cria ou reutiliza o venv no Scratch;
# - instala requirements.txt somente quando necessário;
# - utiliza cache do Pip no Scratch;
# - valida importações e consistência das dependências;
# - registra o hash do requirements.txt no ambiente remoto;
# - informa a disponibilidade de CUDA no PyTorch.
#
# Ele não sincroniza arquivos e não submete jobs.
# Essas responsabilidades pertencem a:
#
#   scripts/sync_to_scratch.sh
#   scripts/submit_sdumont.sh
# ==============================================================================

set -Eeuo pipefail
IFS=$'\n\t'


# ==============================================================================
# CONSTANTES E ESTADO
# ==============================================================================

readonly SCRIPT_NAME="setup_sdumont_env"
readonly EXPECTED_CONFIG_SCHEMA_VERSION="2.0"
readonly REMOTE_SETUP_SCHEMA_VERSION="2"
readonly DEFAULT_CONFIG_FILE="configs/sdumont.env"
readonly MINIMUM_PYTHON_MAJOR="3"
readonly MINIMUM_PYTHON_MINOR="10"

CONFIG_INPUT="${SDUMONT_CONFIG:-${DEFAULT_CONFIG_FILE}}"

FORCE_OVERRIDE=""
RECREATE_OVERRIDE=""
CHECK_ONLY=false
PRINT_ONLY=false
VERBOSE=false
SKIP_CONNECTIVITY_CHECK=false
SKIP_REMOTE_PROJECT_VALIDATION=false

REMOTE_PROJECT_DIR_OVERRIDE=""
REMOTE_VENV_DIR_OVERRIDE=""
REQUIREMENTS_OVERRIDE=""

CHILD_PID=""
REMOTE_SCRIPT_FILE=""


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
    if [[ -n "${REMOTE_SCRIPT_FILE}" ]]; then
        rm -f -- "${REMOTE_SCRIPT_FILE}" 2>/dev/null || true
        REMOTE_SCRIPT_FILE=""
    fi
}


on_error() {
    local exit_code=$?
    local line_number="${BASH_LINENO[0]:-desconhecida}"
    local failed_command="${BASH_COMMAND:-desconhecido}"

    trap - ERR

    error "A preparação do ambiente remoto foi interrompida."
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
            "Encaminhando ${signal_name} ao processo SSH " \
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
  ./scripts/setup_sdumont_env.sh [opções]

Configuração:
  --config ARQUIVO              Configuração privada do SDumont.
  --remote-project-dir CAMINHO  Substitui REMOTE_PROJECT_DIR.
  --remote-venv-dir CAMINHO     Substitui REMOTE_VENV_DIR.
  --requirements ARQUIVO        requirements relativo ao projeto remoto.

Ações:
  --force                       Reinstala requirements.txt.
  --recreate                    Remove e recria o venv remoto.
  --check                       Apenas valida o ambiente existente.
  --skip-connectivity-check     Não executa o teste SSH inicial.
  --skip-project-validation     Não valida a cópia remota do projeto.
  --print-only                  Apenas imprime o comando remoto.
  --verbose                     Exibe informações adicionais.
  -h, --help                    Exibe esta ajuda.

Exemplos:
  ./scripts/setup_sdumont_env.sh \
    --config configs/sdumont.env

  ./scripts/setup_sdumont_env.sh \
    --config configs/sdumont.env \
    --check

  ./scripts/setup_sdumont_env.sh \
    --config configs/sdumont.env \
    --force

  ./scripts/setup_sdumont_env.sh \
    --config configs/sdumont.env \
    --recreate

  ./scripts/setup_sdumont_env.sh \
    --config configs/sdumont.env \
    --print-only
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


split_literal_options() {
    local raw="$1"
    local destination_name="$2"
    local -n destination="${destination_name}"
    local parsed=()

    [[ -n "$(trim_value "${raw}")" ]] || return 0

    # Divisão literal sem eval. Aspas internas não são reinterpretadas.
    read -r -a parsed <<< "${raw}"

    destination+=("${parsed[@]}")
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


run_child() {
    local command=("$@")
    local exit_code=0

    print_command "${command[@]}"

    if [[ "${PRINT_ONLY}" == true ]]; then
        return 0
    fi

    set +e

    "${command[@]}" < "${REMOTE_SCRIPT_FILE}" &
    CHILD_PID=$!

    wait "${CHILD_PID}"
    exit_code=$?

    CHILD_PID=""

    set -e

    return "${exit_code}"
}


run_ssh_simple() {
    local remote_command="$1"
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

    return "${exit_code}"
}


write_remote_script() {
    REMOTE_SCRIPT_FILE="$(
        mktemp \
            "${PROJECT_ROOT}/.tmp/sdumont/setup-remote.XXXXXX.sh"
    )"

    cat > "${REMOTE_SCRIPT_FILE}" <<'REMOTE_SCRIPT'
#!/usr/bin/env bash

set -Eeuo pipefail
IFS=$'\n\t'

REMOTE_PROJECT_DIR="$1"
REMOTE_VENV_DIR="$2"
REMOTE_PIP_CACHE_DIR="$3"
REMOTE_HF_HOME="$4"
REMOTE_REQUIREMENTS_FILE="$5"
PYTHON_MODULE="$6"
CUDA_MODULE="$7"
ADDITIONAL_MODULES="$8"
MODULE_PURGE="$9"
MODULE_COMMAND="${10}"
UPGRADE_PACKAGING_TOOLS="${11}"
FORCE_INSTALL="${12}"
RECREATE_VENV="${13}"
PIP_INDEX_URL_VALUE="${14}"
PIP_EXTRA_INDEX_URL_VALUE="${15}"
PIP_NO_CACHE_DIR_VALUE="${16}"
PIP_INSTALL_EXTRA_ARGS="${17}"
VALIDATE_IMPORTS="${18}"
CHECK_ONLY="${19}"
VALIDATE_REMOTE_PROJECT="${20}"
REMOTE_SETUP_SCHEMA_VERSION="${21}"
MINIMUM_PYTHON_MAJOR="${22}"
MINIMUM_PYTHON_MINOR="${23}"
VERBOSE="${24}"
REMOTE_TEMP_DIR="${25}"

log() {
    local message=""
    printf -v message '%s' "$@"

    printf '[remote setup] %s\n' "${message}"
}


warning() {
    local message=""
    printf -v message '%s' "$@"

    printf '[remote setup] AVISO: %s\n' "${message}" >&2
}


die() {
    printf '[remote setup] ERRO: %s\n' "$*" >&2
    exit 1
}


is_true() {
    local value=""

    value="$(printf '%s' "${1:-false}" | tr '[:upper:]' '[:lower:]')"

    case "${value}" in
        1|true|yes|y|on|sim|s)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}


initialize_modules() {
    if type module >/dev/null 2>&1; then
        return 0
    fi

    for initialization_file in \
        /etc/profile.d/modules.sh \
        /usr/share/Modules/init/bash \
        /etc/profile.d/lmod.sh \
        /usr/share/lmod/lmod/init/bash
    do
        if [[ -r "${initialization_file}" ]]; then
            # shellcheck disable=SC1090
            source "${initialization_file}"

            if type module >/dev/null 2>&1; then
                return 0
            fi
        fi
    done

    if [[ -r /etc/profile ]]; then
        # Alguns clusters inicializam Lmod somente pelo perfil global.
        set +u
        # shellcheck disable=SC1091
        source /etc/profile >/dev/null 2>&1 || true
        set -u
    fi

    if [[ "${MODULE_COMMAND}" == "module" ]]; then
        type module >/dev/null 2>&1 || die \
            "O comando module não está disponível no shell remoto."
    else
        command -v "${MODULE_COMMAND}" >/dev/null 2>&1 || die \
            "Comando de módulos não encontrado: ${MODULE_COMMAND}"
    fi
}


load_modules() {
    local additional=()
    local module_name=""

    initialize_modules

    if is_true "${MODULE_PURGE}"; then
        "${MODULE_COMMAND}" purge
    fi

    "${MODULE_COMMAND}" load "${PYTHON_MODULE}"

    if [[ -n "${CUDA_MODULE}" ]]; then
        "${MODULE_COMMAND}" load "${CUDA_MODULE}"
    fi

    if [[ -n "${ADDITIONAL_MODULES}" ]]; then
        read -r -a additional <<< "${ADDITIONAL_MODULES}"

        for module_name in "${additional[@]}"; do
            [[ -n "${module_name}" ]] || continue
            "${MODULE_COMMAND}" load "${module_name}"
        done
    fi

    if is_true "${VERBOSE}"; then
        "${MODULE_COMMAND}" list 2>&1 || true
    fi
}


resolve_python() {
    local candidate=""

    for candidate in python3 python; do
        if command -v "${candidate}" >/dev/null 2>&1; then
            command -v "${candidate}"
            return 0
        fi
    done

    die "Nenhum Python foi encontrado após carregar os módulos."
}


validate_python_version() {
    local python_executable="$1"

    "${python_executable}" - \
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
}


validate_venv_module() {
    local python_executable="$1"

    "${python_executable}" - <<'PYTHON_VENV_CHECK'
from __future__ import annotations

import importlib.util

if importlib.util.find_spec("venv") is None:
    raise SystemExit(
        "O módulo venv não está disponível no Python carregado."
    )
PYTHON_VENV_CHECK
}


requirements_hash() {
    local python_executable="$1"
    local requirements_path="$2"

    "${python_executable}" - \
        "${requirements_path}" \
        <<'PYTHON_REQUIREMENTS_HASH'
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

path = Path(sys.argv[1])
print(hashlib.sha256(path.read_bytes()).hexdigest())
PYTHON_REQUIREMENTS_HASH
}


python_major_minor() {
    local python_executable="$1"

    "${python_executable}" - <<'PYTHON_MAJOR_MINOR'
from __future__ import annotations

import sys

print(f"{sys.version_info.major}.{sys.version_info.minor}")
PYTHON_MAJOR_MINOR
}


stamp_matches() {
    local python_executable="$1"
    local stamp_path="$2"
    local expected_hash="$3"
    local expected_python="$4"

    "${python_executable}" - \
        "${stamp_path}" \
        "${REMOTE_SETUP_SCHEMA_VERSION}" \
        "${expected_hash}" \
        "${expected_python}" \
        <<'PYTHON_STAMP_CHECK'
from __future__ import annotations

import json
import sys
from pathlib import Path

stamp_path = Path(sys.argv[1])
expected_schema = sys.argv[2]
expected_hash = sys.argv[3]
expected_python = sys.argv[4]

if not stamp_path.is_file():
    raise SystemExit(1)

try:
    payload = json.loads(stamp_path.read_text(encoding="utf-8"))
except Exception:
    raise SystemExit(1)

valid = (
    str(payload.get("schema_version")) == expected_schema
    and payload.get("requirements_sha256") == expected_hash
    and payload.get("python_major_minor") == expected_python
)

raise SystemExit(0 if valid else 1)
PYTHON_STAMP_CHECK
}


write_stamp() {
    local python_executable="$1"
    local stamp_path="$2"
    local requirements_path="$3"
    local requirements_sha256="$4"
    local python_major_minor_value="$5"

    "${python_executable}" - \
        "${stamp_path}" \
        "${REMOTE_SETUP_SCHEMA_VERSION}" \
        "${requirements_path}" \
        "${requirements_sha256}" \
        "${python_major_minor_value}" \
        "${PYTHON_MODULE}" \
        "${CUDA_MODULE}" \
        <<'PYTHON_STAMP_WRITE'
from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

stamp_path = Path(sys.argv[1])
payload = {
    "schema_version": sys.argv[2],
    "requirements_file": sys.argv[3],
    "requirements_sha256": sys.argv[4],
    "python_major_minor": sys.argv[5],
    "python_module": sys.argv[6],
    "cuda_module": sys.argv[7],
    "updated_at": datetime.now(timezone.utc).isoformat(),
}

stamp_path.parent.mkdir(parents=True, exist_ok=True)

descriptor, temporary_name = tempfile.mkstemp(
    prefix=f".{stamp_path.name}.",
    suffix=".tmp",
    dir=str(stamp_path.parent),
)

try:
    with os.fdopen(descriptor, "w", encoding="utf-8") as file:
        json.dump(
            payload,
            file,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        file.write("\n")

    os.replace(temporary_name, stamp_path)
except Exception:
    try:
        os.unlink(temporary_name)
    except OSError:
        pass
    raise
PYTHON_STAMP_WRITE
}


dependency_check() {
    local python_executable="$1"

    PYTHONPATH="${REMOTE_PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}" \
    HF_HOME="${REMOTE_HF_HOME}" \
    TRANSFORMERS_OFFLINE="1" \
    HF_HUB_OFFLINE="1" \
    HF_HUB_DISABLE_TELEMETRY="1" \
    TOKENIZERS_PARALLELISM="false" \
        "${python_executable}" - \
        "${VERBOSE}" \
        <<'PYTHON_DEPENDENCY_CHECK'
from __future__ import annotations

import importlib
import importlib.util
import sys

verbose = sys.argv[1].lower() == "true"

required_modules = {
    "numpy": "numpy",
    "pandas": "pandas",
    "yaml": "PyYAML",
    "torch": "torch",
    "transformers": "transformers",
    "sklearn": "scikit-learn",
}

errors: list[str] = []
versions: dict[str, str] = {}

for module_name, package_name in required_modules.items():
    if importlib.util.find_spec(module_name) is None:
        errors.append(f"{package_name}: módulo {module_name!r} ausente")
        continue

    try:
        module = importlib.import_module(module_name)
    except Exception as error:
        errors.append(
            f"{package_name}: falha ao importar "
            f"({type(error).__name__}: {error})"
        )
        continue

    version = getattr(module, "__version__", None)
    if version is not None:
        versions[package_name] = str(version)

try:
    importlib.import_module("pipeline.runner")
except Exception as error:
    errors.append(
        "pipeline.runner: falha ao importar "
        f"({type(error).__name__}: {error})"
    )

if errors:
    print("Falhas de importação:", file=sys.stderr)
    for item in errors:
        print(f"  - {item}", file=sys.stderr)
    raise SystemExit(1)

if verbose:
    print("Dependências importadas:")
    for package_name in sorted(versions):
        print(f"  - {package_name}: {versions[package_name]}")
PYTHON_DEPENDENCY_CHECK
}


print_runtime_report() {
    local python_executable="$1"

    PYTHONPATH="${REMOTE_PROJECT_DIR}${PYTHONPATH:+:${PYTHONPATH}}" \
        "${python_executable}" - <<'PYTHON_RUNTIME_REPORT'
from __future__ import annotations

import os
import platform
import socket
import sys

import torch

print(f"Hostname: {socket.gethostname()}")
print(f"Python: {platform.python_version()}")
print(f"Executável: {sys.executable}")
print(f"PyTorch: {torch.__version__}")
print(f"CUDA disponível: {torch.cuda.is_available()}")
print(f"CUDA do PyTorch: {torch.version.cuda}")

if torch.cuda.is_available():
    print(f"GPUs visíveis: {torch.cuda.device_count()}")
    for index in range(torch.cuda.device_count()):
        print(f"GPU {index}: {torch.cuda.get_device_name(index)}")

print(f"Projeto: {os.environ.get('PYTHONPATH', '')}")
PYTHON_RUNTIME_REPORT
}


safe_remove_venv() {
    [[ -f "${REMOTE_VENV_DIR}/pyvenv.cfg" ]] || die \
        "O caminho existe, mas não parece ser um venv: " \
        "${REMOTE_VENV_DIR}"

    case "${REMOTE_VENV_DIR}" in
        "/"|"/home"|"/scratch"|"/tmp"|"${REMOTE_PROJECT_DIR}")
            die \
                "Recusa de segurança ao remover: ${REMOTE_VENV_DIR}"
            ;;
    esac

    rm -rf -- "${REMOTE_VENV_DIR}"
}


# ==============================================================================
# PREPARAÇÃO REMOTA
# ==============================================================================

load_modules

BASE_PYTHON="$(resolve_python)"
validate_python_version "${BASE_PYTHON}"
validate_venv_module "${BASE_PYTHON}"

REQUIREMENTS_PATH="${REMOTE_PROJECT_DIR%/}/${REMOTE_REQUIREMENTS_FILE}"
STAMP_FILE="${REMOTE_VENV_DIR%/}/.financial_sentiment_sdumont_env.json"
VENV_PYTHON="${REMOTE_VENV_DIR%/}/bin/python"

if is_true "${VALIDATE_REMOTE_PROJECT}"; then
    [[ -f "${REMOTE_PROJECT_DIR}/pipeline/runner.py" ]] || die \
        "pipeline/runner.py não foi encontrado no projeto remoto."

    [[ -f "${REMOTE_PROJECT_DIR}/scripts/run_service.sh" ]] || die \
        "scripts/run_service.sh não foi encontrado no projeto remoto."
fi

[[ -f "${REQUIREMENTS_PATH}" ]] || die \
    "Arquivo de dependências remoto não encontrado: ${REQUIREMENTS_PATH}"

mkdir -p -- \
    "${REMOTE_PIP_CACHE_DIR}" \
    "${REMOTE_HF_HOME}" \
    "${REMOTE_TEMP_DIR}" \
    "$(dirname -- "${REMOTE_VENV_DIR}")"

export PIP_CACHE_DIR="${REMOTE_PIP_CACHE_DIR}"
export HF_HOME="${REMOTE_HF_HOME}"

if [[ -n "${PIP_INDEX_URL_VALUE}" ]]; then
    export PIP_INDEX_URL="${PIP_INDEX_URL_VALUE}"
else
    unset PIP_INDEX_URL || true
fi

if [[ -n "${PIP_EXTRA_INDEX_URL_VALUE}" ]]; then
    export PIP_EXTRA_INDEX_URL="${PIP_EXTRA_INDEX_URL_VALUE}"
else
    unset PIP_EXTRA_INDEX_URL || true
fi

if is_true "${PIP_NO_CACHE_DIR_VALUE}"; then
    export PIP_NO_CACHE_DIR="1"
else
    unset PIP_NO_CACHE_DIR || true
fi

log "Projeto remoto: ${REMOTE_PROJECT_DIR}"
log "Ambiente virtual: ${REMOTE_VENV_DIR}"
log "Requirements: ${REQUIREMENTS_PATH}"
log "Python base: ${BASE_PYTHON}"
log "Versão base: $("${BASE_PYTHON}" --version 2>&1)"

if is_true "${CHECK_ONLY}"; then
    [[ -f "${REMOTE_VENV_DIR}/pyvenv.cfg" ]] || die \
        "Ambiente virtual remoto não encontrado."

    [[ -x "${VENV_PYTHON}" ]] || die \
        "Python do ambiente virtual não encontrado."

    validate_python_version "${VENV_PYTHON}"

    if is_true "${VALIDATE_IMPORTS}"; then
        dependency_check "${VENV_PYTHON}"
    fi

    "${VENV_PYTHON}" -m pip check
    print_runtime_report "${VENV_PYTHON}"

    log "Ambiente remoto validado com sucesso."
    exit 0
fi

if is_true "${RECREATE_VENV}" && [[ -e "${REMOTE_VENV_DIR}" ]]; then
    log "Removendo o ambiente virtual remoto."
    safe_remove_venv
fi

if [[ -e "${REMOTE_VENV_DIR}" ]] && \
    [[ ! -f "${REMOTE_VENV_DIR}/pyvenv.cfg" ]]
then
    die \
        "REMOTE_VENV_DIR existe, mas não é um ambiente virtual: " \
        "${REMOTE_VENV_DIR}"
fi

if [[ ! -f "${REMOTE_VENV_DIR}/pyvenv.cfg" ]]; then
    log "Criando o ambiente virtual remoto."
    "${BASE_PYTHON}" -m venv "${REMOTE_VENV_DIR}"
fi

[[ -x "${VENV_PYTHON}" ]] || die \
    "O Python do venv não foi criado: ${VENV_PYTHON}"

validate_python_version "${VENV_PYTHON}"

REQUIREMENTS_SHA256="$(
    requirements_hash "${VENV_PYTHON}" "${REQUIREMENTS_PATH}"
)"
PYTHON_MAJOR_MINOR="$(
    python_major_minor "${VENV_PYTHON}"
)"

NEEDS_INSTALL=false
INSTALL_REASON=""

if is_true "${FORCE_INSTALL}"; then
    NEEDS_INSTALL=true
    INSTALL_REASON="instalação forçada"
elif ! stamp_matches \
    "${VENV_PYTHON}" \
    "${STAMP_FILE}" \
    "${REQUIREMENTS_SHA256}" \
    "${PYTHON_MAJOR_MINOR}"
then
    NEEDS_INSTALL=true
    INSTALL_REASON="requirements, Python ou configuração mudaram"
elif is_true "${VALIDATE_IMPORTS}" && \
    ! dependency_check "${VENV_PYTHON}" >/dev/null 2>&1
then
    NEEDS_INSTALL=true
    INSTALL_REASON="uma ou mais importações falharam"
elif ! "${VENV_PYTHON}" -m pip check >/dev/null 2>&1; then
    NEEDS_INSTALL=true
    INSTALL_REASON="pip check encontrou incompatibilidades"
fi

if [[ "${NEEDS_INSTALL}" == true ]]; then
    log "Instalação necessária: ${INSTALL_REASON}."

    if is_true "${UPGRADE_PACKAGING_TOOLS}"; then
        log "Atualizando pip, setuptools e wheel."

        "${VENV_PYTHON}" -m pip install \
            --disable-pip-version-check \
            --upgrade \
            pip \
            setuptools \
            wheel
    fi

    PIP_ARGUMENTS=(
        "--disable-pip-version-check"
        "--requirement"
        "${REQUIREMENTS_PATH}"
    )

    if [[ -n "${PIP_INSTALL_EXTRA_ARGS}" ]]; then
        read -r -a EXTRA_PIP_ARGUMENTS <<< "${PIP_INSTALL_EXTRA_ARGS}"
        PIP_ARGUMENTS+=("${EXTRA_PIP_ARGUMENTS[@]}")
    fi

    log "Instalando as dependências do projeto."

    "${VENV_PYTHON}" -m pip install \
        "${PIP_ARGUMENTS[@]}"
else
    log \
        "O ambiente já corresponde ao requirements.txt; " \
        "a instalação foi ignorada."
fi

if is_true "${VALIDATE_IMPORTS}"; then
    log "Validando importações."
    dependency_check "${VENV_PYTHON}"
fi

log "Executando pip check."
"${VENV_PYTHON}" -m pip check

write_stamp \
    "${VENV_PYTHON}" \
    "${STAMP_FILE}" \
    "${REQUIREMENTS_PATH}" \
    "${REQUIREMENTS_SHA256}" \
    "${PYTHON_MAJOR_MINOR}"

print_runtime_report "${VENV_PYTHON}"

log "Ambiente remoto preparado com sucesso."
log "Python da pipeline: ${VENV_PYTHON}"
log "Arquivo de controle: ${STAMP_FILE}"
REMOTE_SCRIPT
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

        --remote-venv-dir)
            [[ "$#" -ge 2 ]] || die \
                "--remote-venv-dir exige um caminho."

            REMOTE_VENV_DIR_OVERRIDE="$2"
            shift 2
            ;;

        --remote-venv-dir=*)
            REMOTE_VENV_DIR_OVERRIDE="${1#*=}"
            shift
            ;;

        --requirements)
            [[ "$#" -ge 2 ]] || die \
                "--requirements exige um arquivo relativo."

            REQUIREMENTS_OVERRIDE="$2"
            shift 2
            ;;

        --requirements=*)
            REQUIREMENTS_OVERRIDE="${1#*=}"
            shift
            ;;

        --force)
            FORCE_OVERRIDE="true"
            shift
            ;;

        --recreate)
            RECREATE_OVERRIDE="true"
            shift
            ;;

        --check)
            CHECK_ONLY=true
            shift
            ;;

        --skip-connectivity-check)
            SKIP_CONNECTIVITY_CHECK=true
            shift
            ;;

        --skip-project-validation)
            SKIP_REMOTE_PROJECT_VALIDATION=true
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

if [[ "${CHECK_ONLY}" == true && -n "${FORCE_OVERRIDE}" ]]; then
    die "--check e --force não podem ser usados juntos."
fi

if [[ "${CHECK_ONLY}" == true && -n "${RECREATE_OVERRIDE}" ]]; then
    die "--check e --recreate não podem ser usados juntos."
fi


# ==============================================================================
# CARREGAMENTO DA CONFIGURAÇÃO
# ==============================================================================

CONFIG_PATH="$(canonical_existing_file "${CONFIG_INPUT}")" || die \
    "Configuração do SDumont não encontrada: ${CONFIG_INPUT}"

# shellcheck disable=SC1090
source "${CONFIG_PATH}"

: "${SDUMONT_CONFIG_SCHEMA_VERSION:=}"
: "${USERNAME:=}"
: "${LOGIN_HOST:=}"
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
: "${REMOTE_TEMP_DIR:=}"

: "${MODULE_PURGE:=true}"
: "${CUDA_MODULE:=}"
: "${ADDITIONAL_MODULES:=}"
: "${MODULE_COMMAND:=module}"

: "${REMOTE_REQUIREMENTS_FILE:=requirements.txt}"
: "${REMOTE_UPGRADE_PACKAGING_TOOLS:=true}"
: "${REMOTE_FORCE_INSTALL:=false}"
: "${REMOTE_RECREATE_VENV:=false}"
: "${PIP_INDEX_URL:=}"
: "${PIP_EXTRA_INDEX_URL:=}"
: "${PIP_NO_CACHE_DIR:=false}"
: "${PIP_INSTALL_EXTRA_ARGS:=}"
: "${VALIDATE_REMOTE_PYTHON_IMPORTS:=true}"
: "${VALIDATE_REMOTE_PROJECT:=true}"

: "${REQUIRE_ABSOLUTE_REMOTE_PATHS:=true}"
: "${REQUIRE_REMOTE_PATH_UNDER_SCRATCH:=true}"

: "${SSH_COMMAND:=ssh}"
: "${REMOTE_SHELL:=bash}"


# ==============================================================================
# VALIDAÇÃO E RESOLUÇÃO
# ==============================================================================

[[ "${SDUMONT_CONFIG_SCHEMA_VERSION}" == \
    "${EXPECTED_CONFIG_SCHEMA_VERSION}" ]] || die \
    "Versão de configuração incompatível. " \
    "Esperada: ${EXPECTED_CONFIG_SCHEMA_VERSION}; " \
    "recebida: ${SDUMONT_CONFIG_SCHEMA_VERSION:-vazia}."

for required_pair in \
    "USERNAME:${USERNAME}" \
    "LOGIN_HOST:${LOGIN_HOST}" \
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

SSH_BATCH_MODE="$(normalize_boolean "${SSH_BATCH_MODE}" "SSH_BATCH_MODE")"
MODULE_PURGE="$(normalize_boolean "${MODULE_PURGE}" "MODULE_PURGE")"
REMOTE_UPGRADE_PACKAGING_TOOLS="$(
    normalize_boolean \
        "${REMOTE_UPGRADE_PACKAGING_TOOLS}" \
        "REMOTE_UPGRADE_PACKAGING_TOOLS"
)"
REMOTE_FORCE_INSTALL="$(
    normalize_boolean \
        "${REMOTE_FORCE_INSTALL}" \
        "REMOTE_FORCE_INSTALL"
)"
REMOTE_RECREATE_VENV="$(
    normalize_boolean \
        "${REMOTE_RECREATE_VENV}" \
        "REMOTE_RECREATE_VENV"
)"
PIP_NO_CACHE_DIR="$(
    normalize_boolean "${PIP_NO_CACHE_DIR}" "PIP_NO_CACHE_DIR"
)"
VALIDATE_REMOTE_PYTHON_IMPORTS="$(
    normalize_boolean \
        "${VALIDATE_REMOTE_PYTHON_IMPORTS}" \
        "VALIDATE_REMOTE_PYTHON_IMPORTS"
)"
VALIDATE_REMOTE_PROJECT="$(
    normalize_boolean \
        "${VALIDATE_REMOTE_PROJECT}" \
        "VALIDATE_REMOTE_PROJECT"
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

if [[ -n "${FORCE_OVERRIDE}" ]]; then
    REMOTE_FORCE_INSTALL="${FORCE_OVERRIDE}"
fi

if [[ -n "${RECREATE_OVERRIDE}" ]]; then
    REMOTE_RECREATE_VENV="${RECREATE_OVERRIDE}"
fi

if [[ "${SKIP_REMOTE_PROJECT_VALIDATION}" == true ]]; then
    VALIDATE_REMOTE_PROJECT="false"
fi

if [[ -n "${REQUIREMENTS_OVERRIDE}" ]]; then
    REMOTE_REQUIREMENTS_FILE="${REQUIREMENTS_OVERRIDE}"
fi

[[ -n "${REMOTE_REQUIREMENTS_FILE}" ]] || die \
    "REMOTE_REQUIREMENTS_FILE não pode ficar vazio."

[[ "${REMOTE_REQUIREMENTS_FILE}" != /* ]] || die \
    "REMOTE_REQUIREMENTS_FILE precisa ser relativo ao projeto remoto."

[[ "${REMOTE_REQUIREMENTS_FILE}" != *".."* ]] || die \
    "REMOTE_REQUIREMENTS_FILE não pode conter '..'."

require_non_empty "${REMOTE_PROJECT_NAME}" "REMOTE_PROJECT_NAME"

[[ "${REMOTE_PROJECT_NAME}" =~ ^[A-Za-z0-9._-]+$ ]] || die \
    "REMOTE_PROJECT_NAME possui caracteres inválidos."

validate_remote_path "${SCRATCH_DIR}" "SCRATCH_DIR"

if [[ -n "${REMOTE_PROJECT_DIR_OVERRIDE}" ]]; then
    REMOTE_PROJECT_DIR="${REMOTE_PROJECT_DIR_OVERRIDE}"
fi

if [[ -n "${REMOTE_VENV_DIR_OVERRIDE}" ]]; then
    REMOTE_VENV_DIR="${REMOTE_VENV_DIR_OVERRIDE}"
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

if [[ -z "${REMOTE_TEMP_DIR}" ]]; then
    REMOTE_TEMP_DIR="${REMOTE_PROJECT_DIR%/}/.tmp"
fi

for remote_pair in \
    "REMOTE_PROJECT_DIR:${REMOTE_PROJECT_DIR}" \
    "REMOTE_VENV_DIR:${REMOTE_VENV_DIR}" \
    "REMOTE_PIP_CACHE_DIR:${REMOTE_PIP_CACHE_DIR}" \
    "REMOTE_HF_HOME:${REMOTE_HF_HOME}" \
    "REMOTE_TEMP_DIR:${REMOTE_TEMP_DIR}"
do
    field_name="${remote_pair%%:*}"
    field_value="${remote_pair#*:}"

    validate_remote_path "${field_value}" "${field_name}"

    if is_true "${REQUIRE_REMOTE_PATH_UNDER_SCRATCH}"; then
        path_is_under "${field_value}" "${SCRATCH_DIR}" || die \
            "${field_name} precisa estar abaixo de SCRATCH_DIR. " \
            "Valor: ${field_value}"
    fi
done

if [[ "${REMOTE_VENV_DIR}" == "${REMOTE_PROJECT_DIR}" ]]; then
    die \
        "REMOTE_VENV_DIR não pode ser igual a REMOTE_PROJECT_DIR."
fi

if [[ -n "${SSH_IDENTITY_FILE}" ]]; then
    SSH_IDENTITY_FILE="$(
        resolve_project_path "${SSH_IDENTITY_FILE}"
    )"

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
    resolve_command_path "${SSH_COMMAND}" "SSH_COMMAND"
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
# RESUMO
# ==============================================================================

log "Destino SSH: ${SSH_TARGET}"
log "Projeto remoto: ${REMOTE_PROJECT_DIR}"
log "Ambiente virtual remoto: ${REMOTE_VENV_DIR}"
log "Requirements remoto: ${REMOTE_REQUIREMENTS_FILE}"
log "Módulo Python: ${PYTHON_MODULE}"
log "Módulo CUDA: ${CUDA_MODULE:-não configurado}"
log "Reinstalação forçada: ${REMOTE_FORCE_INSTALL}"
log "Recriação do venv: ${REMOTE_RECREATE_VENV}"
log "Somente validação: ${CHECK_ONLY}"

if [[ "${PRINT_ONLY}" == true ]]; then
    warning "Modo print-only: nenhuma conexão será realizada."
fi


# ==============================================================================
# CONECTIVIDADE
# ==============================================================================

if [[ "${SKIP_CONNECTIVITY_CHECK}" == false ]]; then
    log "Validando a conexão SSH."

    run_ssh_simple \
        "printf '%s\n' 'Conexão SSH validada.'" || die \
        "Não foi possível conectar a ${SSH_TARGET}."
else
    warning "Teste de conectividade ignorado."
fi


# ==============================================================================
# EXECUÇÃO REMOTA
# ==============================================================================

write_remote_script

REMOTE_COMMAND=(
    "${SSH_COMMAND_PATH}"
    "${SSH_ARGUMENTS[@]}"
    "${SSH_TARGET}"
    "${REMOTE_SHELL}"
    "-s"
    "--"
    "${REMOTE_PROJECT_DIR}"
    "${REMOTE_VENV_DIR}"
    "${REMOTE_PIP_CACHE_DIR}"
    "${REMOTE_HF_HOME}"
    "${REMOTE_REQUIREMENTS_FILE}"
    "${PYTHON_MODULE}"
    "${CUDA_MODULE}"
    "${ADDITIONAL_MODULES}"
    "${MODULE_PURGE}"
    "${MODULE_COMMAND}"
    "${REMOTE_UPGRADE_PACKAGING_TOOLS}"
    "${REMOTE_FORCE_INSTALL}"
    "${REMOTE_RECREATE_VENV}"
    "${PIP_INDEX_URL}"
    "${PIP_EXTRA_INDEX_URL}"
    "${PIP_NO_CACHE_DIR}"
    "${PIP_INSTALL_EXTRA_ARGS}"
    "${VALIDATE_REMOTE_PYTHON_IMPORTS}"
    "${CHECK_ONLY}"
    "${VALIDATE_REMOTE_PROJECT}"
    "${REMOTE_SETUP_SCHEMA_VERSION}"
    "${MINIMUM_PYTHON_MAJOR}"
    "${MINIMUM_PYTHON_MINOR}"
    "${VERBOSE}"
    "${REMOTE_TEMP_DIR}"
)

log "Executando a preparação do ambiente no SDumont."

STARTED_AT="$(date +%s)"

run_child "${REMOTE_COMMAND[@]}" || die \
    "A preparação remota terminou com falha."

FINISHED_AT="$(date +%s)"
DURATION_SECONDS=$((FINISHED_AT - STARTED_AT))

if [[ "${PRINT_ONLY}" == true ]]; then
    log "Comando remoto montado com sucesso."
else
    log \
        "Ambiente remoto preparado em " \
        "${DURATION_SECONDS} segundo(s)."
fi

log "Próxima etapa:"
printf '  ./scripts/submit_sdumont.sh --config %q\n' \
    "${CONFIG_PATH}"
