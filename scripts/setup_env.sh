#!/usr/bin/env bash

# ==============================================================================
# PREPARAÇÃO DO AMBIENTE LOCAL
# ==============================================================================
#
# Cria, atualiza ou valida o ambiente virtual utilizado pela pipeline.
#
# Uso padrão:
#
#   ./scripts/setup_env.sh
#
# Reinstalar dependências:
#
#   ./scripts/setup_env.sh --force
#
# Recriar completamente o ambiente:
#
#   ./scripts/setup_env.sh --recreate
#
# Apenas validar o ambiente existente:
#
#   ./scripts/setup_env.sh --check
#
# Este script é destinado ao ambiente local. A preparação no Santos Dumont
# será feita por ``scripts/setup_sdumont_env.sh``.
# ==============================================================================

set -Eeuo pipefail
IFS=$'\n\t'


# ==============================================================================
# CONSTANTES E VALORES PADRÃO
# ==============================================================================

readonly SCRIPT_NAME="setup_env"
readonly SETUP_SCHEMA_VERSION="2"
readonly MINIMUM_PYTHON_MAJOR=3
readonly MINIMUM_PYTHON_MINOR=10
readonly DEFAULT_VENV_DIR="venv"
readonly DEFAULT_REQUIREMENTS_FILE="requirements.txt"

VENV_DIR_INPUT="${VENV_DIR:-${DEFAULT_VENV_DIR}}"
REQUIREMENTS_INPUT="${REQUIREMENTS_FILE:-${DEFAULT_REQUIREMENTS_FILE}}"
PYTHON_INPUT="${PYTHON_BIN:-python3}"

FORCE_INSTALL=false
RECREATE_ENV=false
CHECK_ONLY=false
UPGRADE_PACKAGING_TOOLS=true
VERBOSE=false


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


on_error() {
    local exit_code=$?
    local line_number="${BASH_LINENO[0]:-desconhecida}"
    local failed_command="${BASH_COMMAND:-desconhecido}"

    trap - ERR

    error "A preparação do ambiente foi interrompida."
    error "Código de saída: ${exit_code}"
    error "Linha aproximada: ${line_number}"
    error "Comando: ${failed_command}"

    exit "${exit_code}"
}


trap on_error ERR


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
  ./scripts/setup_env.sh [opções]

Opções:
  --venv-dir CAMINHO       Pasta do ambiente virtual.
                           Padrão: venv
  --python EXECUTÁVEL      Python usado para criar o ambiente.
                           Padrão: python3
  --requirements ARQUIVO   Arquivo de dependências.
                           Padrão: requirements.txt
  --force                  Executa novamente pip install -r.
  --recreate               Remove e recria o ambiente virtual.
  --check                  Apenas valida o ambiente existente.
  --no-upgrade-tools       Não atualiza pip, setuptools e wheel.
  --verbose                Mostra versões e informações adicionais.
  -h, --help               Exibe esta ajuda.

Variáveis de ambiente equivalentes:
  VENV_DIR
  PYTHON_BIN
  REQUIREMENTS_FILE
  PIP_INDEX_URL
  PIP_EXTRA_INDEX_URL
  PIP_CACHE_DIR
  PIP_NO_CACHE_DIR

Exemplos:
  ./scripts/setup_env.sh
  ./scripts/setup_env.sh --force
  ./scripts/setup_env.sh --recreate --python python3.11
  ./scripts/setup_env.sh --venv-dir .venv
  ./scripts/setup_env.sh --check
HELP
}


# ==============================================================================
# ARGUMENTOS
# ==============================================================================

while [[ "$#" -gt 0 ]]; do
    case "$1" in
        --venv-dir)
            [[ "$#" -ge 2 ]] || die \
                "--venv-dir exige um caminho."

            VENV_DIR_INPUT="$2"
            shift 2
            ;;

        --venv-dir=*)
            VENV_DIR_INPUT="${1#*=}"
            shift
            ;;

        --python)
            [[ "$#" -ge 2 ]] || die \
                "--python exige um executável."

            PYTHON_INPUT="$2"
            shift 2
            ;;

        --python=*)
            PYTHON_INPUT="${1#*=}"
            shift
            ;;

        --requirements)
            [[ "$#" -ge 2 ]] || die \
                "--requirements exige um arquivo."

            REQUIREMENTS_INPUT="$2"
            shift 2
            ;;

        --requirements=*)
            REQUIREMENTS_INPUT="${1#*=}"
            shift
            ;;

        --force)
            FORCE_INSTALL=true
            shift
            ;;

        --recreate)
            RECREATE_ENV=true
            shift
            ;;

        --check)
            CHECK_ONLY=true
            shift
            ;;

        --no-upgrade-tools)
            UPGRADE_PACKAGING_TOOLS=false
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
                    "Argumentos posicionais não são suportados: $*"
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

if [[ "${CHECK_ONLY}" == true && "${RECREATE_ENV}" == true ]]; then
    die "--check e --recreate não podem ser usados juntos."
fi

if [[ "${CHECK_ONLY}" == true && "${FORCE_INSTALL}" == true ]]; then
    die "--check e --force não podem ser usados juntos."
fi


# ==============================================================================
# FUNÇÕES AUXILIARES
# ==============================================================================

resolve_project_path() {
    local value="$1"

    [[ -n "${value}" ]] || return 1

    if [[ "${value}" = /* ]]; then
        printf '%s\n' "${value}"
    else
        printf '%s\n' "${PROJECT_ROOT}/${value}"
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

        (
            cd -- "$(dirname -- "${candidate}")" >/dev/null 2>&1
            printf '%s/%s\n' \
                "$(pwd -P)" \
                "$(basename -- "${candidate}")"
        )
        return 0
    fi

    command -v "${value}" 2>/dev/null
}


is_safe_recreate_target() {
    local target="$1"

    case "${target}" in
        ""|"/"|"/home"|"/usr"|"/usr/local"|"/opt"|"/tmp"|"${HOME}"|"${PROJECT_ROOT}")
            return 1
            ;;
    esac

    return 0
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
digest = hashlib.sha256(path.read_bytes()).hexdigest()
print(digest)
PYTHON_REQUIREMENTS_HASH
}


python_version() {
    local python_executable="$1"

    "${python_executable}" - <<'PYTHON_VERSION'
from __future__ import annotations

import platform

print(platform.python_version())
PYTHON_VERSION
}


python_major_minor() {
    local python_executable="$1"

    "${python_executable}" - <<'PYTHON_MAJOR_MINOR'
from __future__ import annotations

import sys

print(f"{sys.version_info.major}.{sys.version_info.minor}")
PYTHON_MAJOR_MINOR
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
        "O módulo venv não está disponível neste Python. "
        "Em distribuições Debian/Ubuntu, instale o pacote python3-venv "
        "correspondente à versão utilizada."
    )
PYTHON_VENV_CHECK
}


dependency_check() {
    local python_executable="$1"

    PYTHONPATH="${PROJECT_ROOT}${PYTHONPATH:+:${PYTHONPATH}}" \
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
    print(
        "Falhas encontradas na validação do ambiente:",
        file=sys.stderr,
    )
    for item in errors:
        print(f"  - {item}", file=sys.stderr)
    raise SystemExit(1)

if verbose:
    print("Dependências importadas:")
    for package_name in sorted(versions):
        print(f"  - {package_name}: {versions[package_name]}")
PYTHON_DEPENDENCY_CHECK
}


stamp_matches() {
    local python_executable="$1"
    local stamp_path="$2"
    local expected_hash="$3"
    local expected_python="$4"

    "${python_executable}" - \
        "${stamp_path}" \
        "${SETUP_SCHEMA_VERSION}" \
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
    content = json.loads(stamp_path.read_text(encoding="utf-8"))
except Exception:
    raise SystemExit(1)

valid = (
    str(content.get("schema_version")) == expected_schema
    and content.get("requirements_sha256") == expected_hash
    and content.get("python_major_minor") == expected_python
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
        "${SETUP_SCHEMA_VERSION}" \
        "${requirements_path}" \
        "${requirements_sha256}" \
        "${python_major_minor_value}" \
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


run_pip_check() {
    local python_executable="$1"

    "${python_executable}" -m pip check
}


# ==============================================================================
# RESOLUÇÃO DOS CAMINHOS
# ==============================================================================

VENV_DIR="$(resolve_project_path "${VENV_DIR_INPUT}")" || die \
    "VENV_DIR não pode ficar vazio."

REQUIREMENTS_FILE_PATH="$(
    resolve_project_path "${REQUIREMENTS_INPUT}"
)" || die "REQUIREMENTS_FILE não pode ficar vazio."

STAMP_FILE="${VENV_DIR}/.financial_sentiment_env.json"
VENV_PYTHON="${VENV_DIR}/bin/python"
VENV_PIP="${VENV_DIR}/bin/pip"

[[ -f "${REQUIREMENTS_FILE_PATH}" ]] || die \
    "Arquivo de dependências não encontrado: ${REQUIREMENTS_FILE_PATH}"

[[ -r "${REQUIREMENTS_FILE_PATH}" ]] || die \
    "Arquivo de dependências sem permissão de leitura: " \
    "${REQUIREMENTS_FILE_PATH}"


# ==============================================================================
# MODO DE VALIDAÇÃO
# ==============================================================================

if [[ "${CHECK_ONLY}" == true ]]; then
    [[ -f "${VENV_DIR}/pyvenv.cfg" ]] || die \
        "Ambiente virtual não encontrado em ${VENV_DIR}."

    [[ -x "${VENV_PYTHON}" ]] || die \
        "Python do ambiente virtual não encontrado: ${VENV_PYTHON}"

    validate_python_version "${VENV_PYTHON}"

    log "Validando ambiente virtual existente: ${VENV_DIR}"
    log "Python: ${VENV_PYTHON}"
    log "Versão: $(python_version "${VENV_PYTHON}")"

    dependency_check "${VENV_PYTHON}"
    run_pip_check "${VENV_PYTHON}"

    log "Ambiente validado com sucesso."
    exit 0
fi


# ==============================================================================
# PYTHON BASE
# ==============================================================================

BASE_PYTHON="$(resolve_executable "${PYTHON_INPUT}")" || die \
    "Python base não encontrado ou não executável: ${PYTHON_INPUT}"

validate_python_version "${BASE_PYTHON}"
validate_venv_module "${BASE_PYTHON}"

log "Raiz do projeto: ${PROJECT_ROOT}"
log "Ambiente virtual: ${VENV_DIR}"
log "Arquivo de dependências: ${REQUIREMENTS_FILE_PATH}"
log "Python base: ${BASE_PYTHON}"
log "Versão do Python base: $(python_version "${BASE_PYTHON}")"


# ==============================================================================
# RECRIAÇÃO OU CRIAÇÃO DO VENV
# ==============================================================================

if [[ "${RECREATE_ENV}" == true && -e "${VENV_DIR}" ]]; then
    is_safe_recreate_target "${VENV_DIR}" || die \
        "Recusa de segurança ao remover o caminho: ${VENV_DIR}"

    if [[ ! -f "${VENV_DIR}/pyvenv.cfg" ]]; then
        die \
            "O caminho existe, mas não parece ser um ambiente virtual: " \
            "${VENV_DIR}. Remova-o manualmente após conferir seu conteúdo."
    fi

    log "Removendo ambiente virtual existente."
    rm -rf -- "${VENV_DIR}"
fi

if [[ -e "${VENV_DIR}" && ! -f "${VENV_DIR}/pyvenv.cfg" ]]; then
    die \
        "O caminho ${VENV_DIR} já existe e não é um ambiente virtual."
fi

if [[ ! -f "${VENV_DIR}/pyvenv.cfg" ]]; then
    log "Criando ambiente virtual."

    mkdir -p -- "$(dirname -- "${VENV_DIR}")"
    "${BASE_PYTHON}" -m venv "${VENV_DIR}"
fi

[[ -x "${VENV_PYTHON}" ]] || die \
    "O ambiente foi criado, mas o Python não está disponível: " \
    "${VENV_PYTHON}"

[[ -x "${VENV_PIP}" ]] || die \
    "O ambiente foi criado, mas o pip não está disponível: ${VENV_PIP}"

validate_python_version "${VENV_PYTHON}"

VENV_PYTHON_VERSION="$(python_version "${VENV_PYTHON}")"
VENV_PYTHON_MAJOR_MINOR="$(python_major_minor "${VENV_PYTHON}")"
REQUIREMENTS_SHA256="$(
    requirements_hash \
        "${VENV_PYTHON}" \
        "${REQUIREMENTS_FILE_PATH}"
)"

log "Python do ambiente: ${VENV_PYTHON}"
log "Versão do ambiente: ${VENV_PYTHON_VERSION}"


# ==============================================================================
# DECISÃO DE INSTALAÇÃO
# ==============================================================================

NEEDS_INSTALL=false
INSTALL_REASON=""

if [[ "${FORCE_INSTALL}" == true ]]; then
    NEEDS_INSTALL=true
    INSTALL_REASON="--force foi informado"
elif ! stamp_matches \
    "${VENV_PYTHON}" \
    "${STAMP_FILE}" \
    "${REQUIREMENTS_SHA256}" \
    "${VENV_PYTHON_MAJOR_MINOR}"
then
    NEEDS_INSTALL=true
    INSTALL_REASON="o arquivo de dependências ou o Python mudou"
elif ! dependency_check "${VENV_PYTHON}" >/dev/null 2>&1; then
    NEEDS_INSTALL=true
    INSTALL_REASON="uma ou mais dependências não podem ser importadas"
elif ! run_pip_check "${VENV_PYTHON}" >/dev/null 2>&1; then
    NEEDS_INSTALL=true
    INSTALL_REASON="pip check encontrou inconsistências"
fi


# ==============================================================================
# INSTALAÇÃO
# ==============================================================================

if [[ "${NEEDS_INSTALL}" == true ]]; then
    log "Instalação necessária: ${INSTALL_REASON}."

    if [[ "${UPGRADE_PACKAGING_TOOLS}" == true ]]; then
        log "Atualizando pip, setuptools e wheel."

        "${VENV_PYTHON}" -m pip install \
            --disable-pip-version-check \
            --upgrade \
            pip \
            setuptools \
            wheel
    fi

    log "Instalando dependências de ${REQUIREMENTS_FILE_PATH}."

    "${VENV_PYTHON}" -m pip install \
        --disable-pip-version-check \
        --requirement \
        "${REQUIREMENTS_FILE_PATH}"
else
    log \
        "As dependências já estão compatíveis com requirements.txt; " \
        "a instalação foi ignorada."
fi


# ==============================================================================
# VALIDAÇÃO FINAL
# ==============================================================================

log "Validando importações."
dependency_check "${VENV_PYTHON}"

log "Validando consistência das dependências."
run_pip_check "${VENV_PYTHON}"

write_stamp \
    "${VENV_PYTHON}" \
    "${STAMP_FILE}" \
    "${REQUIREMENTS_FILE_PATH}" \
    "${REQUIREMENTS_SHA256}" \
    "${VENV_PYTHON_MAJOR_MINOR}"


# ==============================================================================
# RESUMO
# ==============================================================================

log "Ambiente local preparado com sucesso."
log "Python da pipeline: ${VENV_PYTHON}"
log "Arquivo de controle: ${STAMP_FILE}"

printf '\n'
printf 'Próximos comandos:\n'
printf '  %q --check\n' "${PROJECT_ROOT}/scripts/setup_env.sh"
printf '  %q --dry-run\n' "${PROJECT_ROOT}/scripts/run_service.sh"
printf '  %q\n' "${PROJECT_ROOT}/scripts/run_experiment.sh"
printf '\n'
printf 'Ativação manual opcional:\n'
printf '  source %q\n' "${VENV_DIR}/bin/activate"
