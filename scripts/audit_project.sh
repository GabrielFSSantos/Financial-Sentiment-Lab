#!/usr/bin/env bash

# ==============================================================================
# AUDITORIA COMPLETA DO FINANCIAL SENTIMENT LAB
# ==============================================================================
#
# Execute na raiz do projeto:
#
#   bash scripts/audit_project.sh
#
# Teste completo do modelo em CPU:
#
#   RUN_MODEL_SMOKE=1 bash scripts/audit_project.sh
#
# A auditoria não instala, atualiza ou remove dependências.
# ==============================================================================

set -uo pipefail
IFS=$'\n\t'

readonly SCRIPT_NAME="audit_project"
readonly RUN_MODEL_SMOKE="${RUN_MODEL_SMOKE:-1}"

PASS_COUNT=0
WARN_COUNT=0
FAIL_COUNT=0
INFO_COUNT=0

timestamp() {
    date '+%Y-%m-%d %H:%M:%S'
}

section() {
    printf '\n%s\n' "=============================================================================="
    printf '%s\n' "$1"
    printf '%s\n' "=============================================================================="
}

pass() {
    PASS_COUNT=$((PASS_COUNT + 1))
    printf '[PASS] %s\n' "$*"
}

warn() {
    WARN_COUNT=$((WARN_COUNT + 1))
    printf '[WARN] %s\n' "$*"
}

fail() {
    FAIL_COUNT=$((FAIL_COUNT + 1))
    printf '[FAIL] %s\n' "$*"
}

info() {
    INFO_COUNT=$((INFO_COUNT + 1))
    printf '[INFO] %s\n' "$*"
}

run_logged() {
    local label="$1"
    shift

    local temporary_output=""
    local exit_code=0

    temporary_output="$(mktemp)"

    "$@" >"${temporary_output}" 2>&1
    exit_code=$?

    if [[ "${exit_code}" -eq 0 ]]; then
        pass "${label}"
    else
        fail "${label} (código ${exit_code})"
    fi

    if [[ -s "${temporary_output}" ]]; then
        sed 's/^/       /' "${temporary_output}"
    fi

    rm -f -- "${temporary_output}"
    return 0
}

normalize_lowercase() {
    printf '%s' "${1:-}" | tr '[:upper:]' '[:lower:]'
}

find_python() {
    local candidate=""

    for candidate in \
        "${PYTHON_BIN:-}" \
        "venv/bin/python" \
        ".venv/bin/python" \
        "venv/Scripts/python.exe" \
        ".venv/Scripts/python.exe" \
        "python3" \
        "python"
    do
        [[ -n "${candidate}" ]] || continue

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

ROOT="$(pwd -P)"

if [[ ! -d "${ROOT}/pipeline" ]] || \
    [[ ! -d "${ROOT}/scripts" ]] || \
    [[ ! -f "${ROOT}/requirements.txt" ]]
then
    printf '[ERRO] Execute este diagnóstico na raiz do projeto.\n' >&2
    printf 'Diretório atual: %s\n' "${ROOT}" >&2
    exit 2
fi

REPORT_DIR="${ROOT}/.tmp/diagnostics"
mkdir -p -- "${REPORT_DIR}"

REPORT_PATH="${REPORT_DIR}/project_audit_$(date '+%Y%m%d_%H%M%S').txt"

exec > >(tee "${REPORT_PATH}") 2>&1

printf 'Auditoria iniciada em: %s\n' "$(timestamp)"
printf 'Raiz do projeto: %s\n' "${ROOT}"
printf 'Relatório: %s\n' "${REPORT_PATH}"
printf 'RUN_MODEL_SMOKE: %s\n' "${RUN_MODEL_SMOKE}"

PYTHON_EXECUTABLE="$(find_python || true)"

if [[ -n "${PYTHON_EXECUTABLE}" ]]; then
    info "Python selecionado: ${PYTHON_EXECUTABLE}"
else
    fail "Nenhum executável Python foi encontrado."
fi


# ==============================================================================
# 1. ESTRUTURA PLANEJADA
# ==============================================================================

section "1. ESTRUTURA PLANEJADA"

EXPECTED_FILES=(
    ".gitignore"
    "requirements.txt"
    "configs/experiment.yaml"
    "configs/models.yaml"
    "configs/datasets.yaml"
    "configs/sdumont.env.example"
    "scripts/run_experiment.sh"
    "scripts/run_service.sh"
    "scripts/setup_env.sh"
    "scripts/sync_to_scratch.sh"
    "scripts/setup_sdumont_env.sh"
    "scripts/submit_sdumont.sh"
    "scripts/download_sdumont_results.sh"
    "jobs/sdumont/run_experiment.srm"
    "models/__init__.py"
    "models/base_model.py"
    "models/finbert_ptbr.py"
    "pipeline/__init__.py"
    "pipeline/configuration.py"
    "pipeline/results.py"
    "pipeline/dataset_loader.py"
    "pipeline/registry.py"
    "pipeline/output_schema.py"
    "pipeline/metrics.py"
    "pipeline/aggregation.py"
    "pipeline/runner.py"
)

for relative_path in "${EXPECTED_FILES[@]}"; do
    if [[ -f "${ROOT}/${relative_path}" ]]; then
        pass "Arquivo presente: ${relative_path}"
    else
        fail "Arquivo ausente: ${relative_path}"
    fi
done

EXPECTED_DIRECTORIES=(
    "configs"
    "datasets"
    "datasets/raw"
    "datasets/processed"
    "jobs/sdumont"
    "model_store"
    "models"
    "outputs"
    "pipeline"
    "scripts"
)

for relative_path in "${EXPECTED_DIRECTORIES[@]}"; do
    if [[ -d "${ROOT}/${relative_path}" ]]; then
        pass "Diretório presente: ${relative_path}/"
    else
        fail "Diretório ausente: ${relative_path}/"
    fi
done

OBSOLETE_PATHS=(
    "jobs/local"
    "jobs/local/run_experiment.sh"
    "jobs/sdumont/run_array_models.srm"
    "jobs/sdumont/run_array_datasets.srm"
    "scripts/local/run_experiment.sh"
)

for relative_path in "${OBSOLETE_PATHS[@]}"; do
    if [[ -e "${ROOT}/${relative_path}" ]]; then
        fail "Estrutura antiga ainda presente: ${relative_path}"
    else
        pass "Estrutura antiga removida: ${relative_path}"
    fi
done

mapfile -t SDUMONT_JOBS < <(
    find "${ROOT}/jobs/sdumont" \
        -maxdepth 1 \
        -type f \
        -name '*.srm' \
        -printf '%f\n' \
        2>/dev/null |
        sort
)

if [[ "${#SDUMONT_JOBS[@]}" -eq 1 ]] && \
    [[ "${SDUMONT_JOBS[0]}" == "run_experiment.srm" ]]
then
    pass "Existe somente o job Slurm planejado."
else
    fail \
        "Jobs Slurm encontrados: ${SDUMONT_JOBS[*]:-nenhum}. " \
        "O esperado é somente run_experiment.srm."
fi

if [[ -f "${ROOT}/README.md" ]]; then
    info "README.md já existe e será verificado na seção 13."
else
    warn \
        "README.md ainda não existe. Isso é esperado nesta etapa, " \
        "mas deverá ser criado após a auditoria."
fi


# ==============================================================================
# 2. PERMISSÕES
# ==============================================================================

section "2. PERMISSÕES DOS EXECUTÁVEIS"

EXECUTABLE_FILES=(
    "scripts/run_experiment.sh"
    "scripts/run_service.sh"
    "scripts/setup_env.sh"
    "scripts/sync_to_scratch.sh"
    "scripts/setup_sdumont_env.sh"
    "scripts/submit_sdumont.sh"
    "scripts/download_sdumont_results.sh"
    "jobs/sdumont/run_experiment.srm"
)

for relative_path in "${EXECUTABLE_FILES[@]}"; do
    if [[ ! -e "${ROOT}/${relative_path}" ]]; then
        fail "Não foi possível validar permissão: ${relative_path}"
    elif [[ -x "${ROOT}/${relative_path}" ]]; then
        pass "Executável: ${relative_path}"
    else
        fail \
            "Sem permissão de execução: ${relative_path}. " \
            "Corrija com chmod +x."
    fi
done


# ==============================================================================
# 3. SINTAXE BASH E FORMATAÇÃO
# ==============================================================================

section "3. SINTAXE BASH E FORMATAÇÃO"

mapfile -d '' -t SHELL_FILES < <(
    find "${ROOT}/scripts" "${ROOT}/jobs" \
        -type f \
        \( -name '*.sh' -o -name '*.srm' \) \
        -print0 \
        2>/dev/null
)

if [[ "${#SHELL_FILES[@]}" -eq 0 ]]; then
    fail "Nenhum script Bash foi encontrado."
else
    for file_path in "${SHELL_FILES[@]}"; do
        relative_path="${file_path#"${ROOT}/"}"

        if bash -n "${file_path}"; then
            pass "Sintaxe Bash: ${relative_path}"
        else
            fail "Erro de sintaxe Bash: ${relative_path}"
        fi
    done
fi

if [[ -f "${ROOT}/configs/sdumont.env.example" ]]; then
    if bash -n "${ROOT}/configs/sdumont.env.example"; then
        pass "Sintaxe Bash: configs/sdumont.env.example"
    else
        fail "Erro de sintaxe: configs/sdumont.env.example"
    fi
fi

if [[ -f "${ROOT}/configs/sdumont.env" ]]; then
    if bash -n "${ROOT}/configs/sdumont.env"; then
        pass "Sintaxe Bash: configs/sdumont.env"
    else
        fail "Erro de sintaxe: configs/sdumont.env"
    fi
fi

CRLF_FOUND=false

while IFS= read -r -d '' file_path; do
    if LC_ALL=C grep -q $'\r' "${file_path}" 2>/dev/null; then
        fail "Arquivo com quebra de linha CRLF: ${file_path#"${ROOT}/"}"
        CRLF_FOUND=true
    fi
done < <(
    find "${ROOT}/scripts" "${ROOT}/jobs" "${ROOT}/pipeline" \
        "${ROOT}/models" "${ROOT}/configs" \
        -type f \
        \( -name '*.sh' -o -name '*.srm' -o -name '*.py' \
           -o -name '*.yaml' -o -name '*.yml' -o -name '*.env' \
           -o -name '*.example' \) \
        -print0 \
        2>/dev/null
)

if [[ "${CRLF_FOUND}" == false ]]; then
    pass "Nenhum CRLF foi encontrado nos arquivos principais."
fi

if grep -Eq '^[[:space:]]*#SBATCH' \
    "${ROOT}/jobs/sdumont/run_experiment.srm" 2>/dev/null
then
    fail \
        "run_experiment.srm contém diretivas #SBATCH. " \
        "Os recursos deveriam vir de submit_sdumont.sh."
else
    pass "run_experiment.srm não duplica diretivas #SBATCH."
fi

if grep -Eq -- '--array|SLURM_ARRAY' \
    "${ROOT}/jobs/sdumont/run_experiment.srm" \
    "${ROOT}/scripts/submit_sdumont.sh" \
    2>/dev/null
then
    fail "Ainda existem referências a arrays Slurm."
else
    pass "Não existem referências ativas a arrays Slurm."
fi

if command -v shellcheck >/dev/null 2>&1; then
    run_logged \
        "ShellCheck dos scripts" \
        shellcheck \
        -x \
        "${SHELL_FILES[@]}"
else
    warn "shellcheck não está instalado; validação opcional ignorada."
fi


# ==============================================================================
# 4. CONFIGURAÇÕES YAML
# ==============================================================================

section "4. CONFIGURAÇÕES YAML E CONSISTÊNCIA"

if [[ -n "${PYTHON_EXECUTABLE}" ]]; then
    YAML_CHECK_OUTPUT="$(mktemp)"

    PYTHONPATH="${ROOT}" \
        "${PYTHON_EXECUTABLE}" - \
        "${ROOT}" \
        >"${YAML_CHECK_OUTPUT}" 2>&1 <<'PYTHON_YAML_CHECK'
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

root = Path(sys.argv[1])

try:
    import yaml
except Exception as error:
    raise SystemExit(f"PyYAML indisponível: {error}")

paths = {
    "experiment": root / "configs" / "experiment.yaml",
    "models": root / "configs" / "models.yaml",
    "datasets": root / "configs" / "datasets.yaml",
}

documents: dict[str, dict[str, Any]] = {}

for name, path in paths.items():
    if not path.is_file():
        raise SystemExit(f"Arquivo ausente: {path}")

    with path.open("r", encoding="utf-8") as file:
        raw = yaml.safe_load(file)

    if not isinstance(raw, dict):
        raise SystemExit(f"{path.name} precisa conter um mapeamento.")

    documents[name] = raw
    print(f"{path.name}: YAML válido")
    print(f"  schema_version: {raw.get('schema_version', '<ausente>')}")
    print(f"  chaves: {sorted(str(key) for key in raw)}")

experiment = documents["experiment"]
execution = experiment.get("execution")

if not isinstance(execution, dict):
    raise SystemExit(
        "experiment.yaml precisa possuir a seção execution."
    )

environment = str(execution.get("environment", "")).strip().lower()

if environment not in {"local", "sdumont"}:
    raise SystemExit(
        "execution.environment precisa ser local ou sdumont. "
        f"Recebido: {environment!r}"
    )

print(f"execution.environment: {environment}")

def get_named_entries(
    document: dict[str, Any],
    section_name: str,
) -> dict[str, Any]:
    section = document.get(section_name)

    if not isinstance(section, dict):
        raise SystemExit(
            f"{section_name}.yaml precisa possuir a seção "
            f"{section_name!r}."
        )

    return section

models = get_named_entries(documents["models"], "models")
datasets = get_named_entries(documents["datasets"], "datasets")

enabled_models = [
    str(key)
    for key, value in models.items()
    if isinstance(value, dict)
    and bool(value.get("enabled", False))
]
enabled_datasets = [
    str(key)
    for key, value in datasets.items()
    if isinstance(value, dict)
    and bool(value.get("enabled", False))
]

if not enabled_models:
    raise SystemExit("Nenhum modelo está enabled=true.")

if not enabled_datasets:
    raise SystemExit("Nenhum dataset está enabled=true.")

print(f"modelos habilitados: {enabled_models}")
print(f"datasets habilitados: {enabled_datasets}")
print(
    "combinações padrão: "
    f"{len(enabled_models) * len(enabled_datasets)}"
)

finbert = models.get("finbert_ptbr")

if not isinstance(finbert, dict):
    raise SystemExit(
        "models.yaml não possui a entrada finbert_ptbr."
    )

labels = finbert.get("labels")

if isinstance(labels, dict):
    id2label = labels.get("id2label")

    if isinstance(id2label, dict):
        normalized = {
            int(index): str(label).strip().upper()
            for index, label in id2label.items()
        }

        expected = {
            0: "POSITIVE",
            1: "NEGATIVE",
            2: "NEUTRAL",
        }

        if normalized != expected:
            raise SystemExit(
                "finbert_ptbr.labels.id2label diverge do planejado. "
                f"Encontrado: {normalized}"
            )

        print(f"finbert_ptbr.id2label: {normalized}")

print("Validação cruzada básica dos YAMLs: aprovada")
PYTHON_YAML_CHECK

    YAML_EXIT=$?

    if [[ "${YAML_EXIT}" -eq 0 ]]; then
        pass "YAMLs válidos e configuração básica consistente."
    else
        fail "Falha na validação dos YAMLs."
    fi

    sed 's/^/       /' "${YAML_CHECK_OUTPUT}"
    rm -f -- "${YAML_CHECK_OUTPUT}"
else
    fail "YAMLs não puderam ser analisados sem Python."
fi


# ==============================================================================
# 5. SDUMONT.ENV
# ==============================================================================

section "5. CONFIGURAÇÃO DO SDUMONT"

FORBIDDEN_ENV_ASSIGNMENTS='^[[:space:]]*(MODEL_KEYS|DATASET_KEYS|BATCH_SIZE|MAX_LENGTH|MODEL_DEVICE|DEVICE)[[:space:]]*='

for relative_path in \
    "configs/sdumont.env.example" \
    "configs/sdumont.env"
do
    absolute_path="${ROOT}/${relative_path}"

    [[ -f "${absolute_path}" ]] || continue

    if grep -Eiq "${FORBIDDEN_ENV_ASSIGNMENTS}" "${absolute_path}"; then
        fail \
            "${relative_path} contém seleção científica ou parâmetros " \
            "de inferência que deveriam permanecer nos YAMLs."
    else
        pass \
            "${relative_path} não duplica modelo, dataset, batch ou device."
    fi
done

if [[ -f "${ROOT}/configs/sdumont.env" ]]; then
    PRIVATE_ENV_RESULT="$(mktemp)"

    bash -c '
        set -u
        source "$1"

        missing=()

        for name in \
            USERNAME \
            LOGIN_HOST \
            ACCOUNT \
            PARTITION \
            SCRATCH_DIR \
            PYTHON_MODULE
        do
            value="${!name:-}"

            if [[ -z "${value}" ]]; then
                missing+=("${name}")
            fi
        done

        if [[ "${#missing[@]}" -gt 0 ]]; then
            printf "PENDENTES:%s\n" "${missing[*]}"
            exit 3
        fi

        printf "Todos os campos obrigatórios estão preenchidos.\n"
    ' bash "${ROOT}/configs/sdumont.env" \
        >"${PRIVATE_ENV_RESULT}" 2>&1
    PRIVATE_ENV_EXIT=$?

    if [[ "${PRIVATE_ENV_EXIT}" -eq 0 ]]; then
        pass "Campos obrigatórios de configs/sdumont.env preenchidos."
    elif [[ "${PRIVATE_ENV_EXIT}" -eq 3 ]]; then
        warn \
            "configs/sdumont.env ainda possui campos obrigatórios " \
            "pendentes para o acesso real."
    else
        fail "Não foi possível carregar configs/sdumont.env."
    fi

    sed 's/^/       /' "${PRIVATE_ENV_RESULT}"
    rm -f -- "${PRIVATE_ENV_RESULT}"
else
    warn \
        "configs/sdumont.env privado não existe. " \
        "A execução local continua possível."
fi


# ==============================================================================
# 6. GIT E SEGREDOS
# ==============================================================================

section "6. GIT, ARQUIVOS PRIVADOS E RESULTADOS"

if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    pass "O diretório é um repositório Git."

    info "Branch: $(git branch --show-current 2>/dev/null || true)"
    info "Commit: $(git rev-parse --short HEAD 2>/dev/null || printf sem-commit)"

    printf '%s\n' "       git status --short:"
    git status --short 2>/dev/null | sed 's/^/       /' || true

    if git ls-files --error-unmatch \
        configs/sdumont.env >/dev/null 2>&1
    then
        fail "configs/sdumont.env está sendo rastreado pelo Git."
    else
        pass "configs/sdumont.env não está rastreado."
    fi

    if git check-ignore -q configs/sdumont.env; then
        pass ".gitignore protege configs/sdumont.env."
    else
        fail ".gitignore não protege configs/sdumont.env."
    fi

    if git check-ignore -q outputs/audit_test/summary.json; then
        pass ".gitignore protege outputs/."
    else
        fail ".gitignore não protege outputs/."
    fi

    if git check-ignore -q logs/audit_test.log; then
        pass ".gitignore protege logs/."
    else
        fail ".gitignore não protege logs/."
    fi

    if git check-ignore -q \
        model_store/FinBERT-PT-BR/model.safetensors
    then
        pass ".gitignore protege os pesos do modelo."
    else
        fail ".gitignore não protege os pesos do modelo."
    fi

    if git check-ignore -q \
        datasets/raw/noticias_exemplo/noticias.csv
    then
        fail \
            "O dataset noticias_exemplo está ignorado, mas deveria " \
            "permanecer versionável."
    else
        pass "O dataset noticias_exemplo permanece versionável."
    fi
else
    warn "A pasta ainda não é um repositório Git."
fi


# ==============================================================================
# 7. PYTHON, DEPENDÊNCIAS E COMPILAÇÃO
# ==============================================================================

section "7. PYTHON, DEPENDÊNCIAS E COMPILAÇÃO"

if [[ -n "${PYTHON_EXECUTABLE}" ]]; then
    run_logged \
        "Python 3.10 ou superior" \
        "${PYTHON_EXECUTABLE}" \
        -c \
        'import sys; assert sys.version_info >= (3, 10), sys.version'

    run_logged \
        "Compilação de pipeline/ e models/" \
        "${PYTHON_EXECUTABLE}" \
        -m \
        compileall \
        -q \
        "${ROOT}/pipeline" \
        "${ROOT}/models"

    run_logged \
        "Importação das dependências principais" \
        env PYTHONPATH="${ROOT}" \
        "${PYTHON_EXECUTABLE}" \
        -c \
        'import numpy, pandas, yaml, torch, transformers, sklearn; print("imports principais: OK")'

    run_logged \
        "Importação dos módulos internos" \
        env PYTHONPATH="${ROOT}" \
        "${PYTHON_EXECUTABLE}" \
        -c \
        'import pipeline.configuration, pipeline.dataset_loader, pipeline.registry, pipeline.output_schema, pipeline.metrics, pipeline.aggregation, pipeline.results, pipeline.runner, models.base_model, models.finbert_ptbr; print("módulos internos: OK")'

    run_logged \
        "Consistência das dependências com pip check" \
        "${PYTHON_EXECUTABLE}" \
        -m \
        pip \
        check

    printf '%s\n' "       Versões instaladas:"

    VERSIONS_OUTPUT="$(mktemp)"

    PYTHONPATH="${ROOT}" \
        "${PYTHON_EXECUTABLE}" - \
        >"${VERSIONS_OUTPUT}" 2>&1 <<'PYTHON_VERSIONS'
from __future__ import annotations

import platform

import numpy
import pandas
import sklearn
import torch
import transformers
import yaml

print(f"Python: {platform.python_version()}")
print(f"numpy: {numpy.__version__}")
print(f"pandas: {pandas.__version__}")
print(f"PyYAML: {yaml.__version__}")
print(f"torch: {torch.__version__}")
print(f"transformers: {transformers.__version__}")
print(f"scikit-learn: {sklearn.__version__}")
print(f"CUDA disponível: {torch.cuda.is_available()}")
print(f"CUDA do PyTorch: {torch.version.cuda}")
PYTHON_VERSIONS

    VERSIONS_EXIT=$?

    if [[ "${VERSIONS_EXIT}" -eq 0 ]]; then
        pass "Leitura das versões instaladas"
    else
        fail "Falha ao ler as versões instaladas"
    fi

    sed 's/^/       /' "${VERSIONS_OUTPUT}"
    rm -f -- "${VERSIONS_OUTPUT}"
else
    fail "As verificações Python foram ignoradas."
fi


# ==============================================================================
# 8. PYRIGHT
# ==============================================================================

section "8. ANÁLISE ESTÁTICA"

if [[ -n "${PYTHON_EXECUTABLE}" ]] && \
    "${PYTHON_EXECUTABLE}" -c \
        'import importlib.util; raise SystemExit(0 if importlib.util.find_spec("pyright") else 1)' \
        >/dev/null 2>&1
then
    run_logged \
        "Pyright em pipeline/ e models/" \
        "${PYTHON_EXECUTABLE}" \
        -m \
        pyright \
        "${ROOT}/pipeline" \
        "${ROOT}/models"
elif command -v pyright >/dev/null 2>&1; then
    run_logged \
        "Pyright em pipeline/ e models/" \
        pyright \
        "${ROOT}/pipeline" \
        "${ROOT}/models"
else
    warn "Pyright não está instalado; análise estática opcional ignorada."
fi


# ==============================================================================
# 9. INTERFACES DOS SCRIPTS
# ==============================================================================

section "9. INTERFACES DOS SCRIPTS"

HELP_SCRIPTS=(
    "scripts/run_experiment.sh"
    "scripts/run_service.sh"
    "scripts/setup_env.sh"
    "scripts/sync_to_scratch.sh"
    "scripts/setup_sdumont_env.sh"
    "scripts/submit_sdumont.sh"
    "scripts/download_sdumont_results.sh"
)

for relative_path in "${HELP_SCRIPTS[@]}"; do
    absolute_path="${ROOT}/${relative_path}"

    if [[ ! -x "${absolute_path}" ]]; then
        fail "Não foi possível executar --help: ${relative_path}"
        continue
    fi

    run_logged \
        "Interface --help: ${relative_path}" \
        "${absolute_path}" \
        --help
done


# ==============================================================================
# 10. DATASET DE EXEMPLO
# ==============================================================================

section "10. DATASET DE EXEMPLO"

EXAMPLE_DATASET="${ROOT}/datasets/raw/noticias_exemplo/noticias.csv"

if [[ -f "${EXAMPLE_DATASET}" ]]; then
    pass "Dataset de exemplo presente."

    if [[ -n "${PYTHON_EXECUTABLE}" ]]; then
        run_logged \
            "Leitura do dataset de exemplo" \
            "${PYTHON_EXECUTABLE}" \
            -c \
            'import pandas as pd, sys; frame = pd.read_csv(sys.argv[1]); assert len(frame) > 0; print(f"linhas={len(frame)} colunas={list(frame.columns)}")' \
            "${EXAMPLE_DATASET}"
    fi
else
    fail \
        "Dataset de exemplo ausente: " \
        "datasets/raw/noticias_exemplo/noticias.csv"
fi


# ==============================================================================
# 11. FINBERT-PT-BR
# ==============================================================================

section "11. MODELO FINBERT-PT-BR"

MODEL_DIR="${ROOT}/model_store/FinBERT-PT-BR"

if [[ ! -d "${MODEL_DIR}" ]]; then
    fail "Pasta do modelo ausente: model_store/FinBERT-PT-BR"
elif [[ -z "${PYTHON_EXECUTABLE}" ]]; then
    fail "Modelo não pôde ser validado sem Python."
else
    run_logged \
        "Validação estrutural dos arquivos do FinBERT-PT-BR" \
        env PYTHONPATH="${ROOT}" \
        "${PYTHON_EXECUTABLE}" \
        -c \
        'from models.finbert_ptbr import FinBertPtBrModel; import sys; model = FinBertPtBrModel(model_dir=sys.argv[1], batch_size=1, max_length=128, device="cpu"); model.validate_model_files(); print(model.get_metadata())' \
        "${MODEL_DIR}"

    case "$(normalize_lowercase "${RUN_MODEL_SMOKE}")" in
        1|true|yes|y|on|sim|s)
            run_logged \
                "Inferência real de uma notícia em CPU" \
                env PYTHONPATH="${ROOT}" \
                "${PYTHON_EXECUTABLE}" \
                -c \
                'from models.finbert_ptbr import FinBertPtBrModel; import sys; model = FinBertPtBrModel(model_dir=sys.argv[1], batch_size=1, max_length=128, device="cpu"); prediction = model.predict(["Lucro da empresa cresce acima do esperado."])[0]; print(prediction.to_dict()); model.unload()' \
                "${MODEL_DIR}"
            ;;
        *)
            warn \
                "Inferência real ignorada por RUN_MODEL_SMOKE=${RUN_MODEL_SMOKE}."
            ;;
    esac
fi


# ==============================================================================
# 12. RUNNER E DRY-RUN INTEGRADO
# ==============================================================================

section "12. RUNNER E DRY-RUN INTEGRADO"

if [[ -n "${PYTHON_EXECUTABLE}" ]]; then
    run_logged \
        "Ajuda do pipeline.runner" \
        env PYTHONPATH="${ROOT}" \
        "${PYTHON_EXECUTABLE}" \
        -m \
        pipeline.runner \
        --help
fi

if [[ -x "${ROOT}/scripts/run_experiment.sh" ]]; then
    AUDIT_RUN_ID="audit_$(date '+%Y%m%d_%H%M%S')"

    run_logged \
        "Fluxo local completo em dry-run" \
        "${ROOT}/scripts/run_experiment.sh" \
        --environment \
        local \
        --skip-setup \
        --dry-run \
        --log-level \
        INFO \
        --run-id \
        "${AUDIT_RUN_ID}"
else
    fail "run_experiment.sh não está executável."
fi


# ==============================================================================
# 13. REFERÊNCIAS DO README ATUAL
# ==============================================================================

section "13. REFERÊNCIAS DO README ATUAL"

README_PATH="${ROOT}/README.md"

if [[ ! -f "${README_PATH}" ]]; then
    warn \
        "README.md ainda não foi criado. Use este relatório como base " \
        "para produzir o README final."
else
    STALE_PATTERNS=(
        "pipeline/environment.py"
        "datasets/manifests"
        "outputs/summaries"
        "jobs/local"
        "run_array_models"
        "run_array_datasets"
    )

    for pattern in "${STALE_PATTERNS[@]}"; do
        if grep -Fn "${pattern}" "${README_PATH}" >/dev/null 2>&1; then
            fail \
                "README.md contém referência antiga: ${pattern}"
            grep -Fn "${pattern}" "${README_PATH}" |
                sed 's/^/       /'
        else
            pass \
                "README.md não contém referência antiga: ${pattern}"
        fi
    done

    EXPECTED_README_REFERENCES=(
        "./scripts/run_experiment.sh"
        "configs/models.yaml"
        "configs/datasets.yaml"
        "configs/experiment.yaml"
        "jobs/sdumont/run_experiment.srm"
        "outputs/{run_id}"
    )

    for pattern in "${EXPECTED_README_REFERENCES[@]}"; do
        if grep -Fq "${pattern}" "${README_PATH}"; then
            pass "README.md menciona: ${pattern}"
        else
            warn "README.md ainda não menciona: ${pattern}"
        fi
    done
fi


# ==============================================================================
# 14. RESUMO
# ==============================================================================

section "14. RESUMO FINAL"

printf 'PASS: %s\n' "${PASS_COUNT}"
printf 'WARN: %s\n' "${WARN_COUNT}"
printf 'FAIL: %s\n' "${FAIL_COUNT}"
printf 'INFO: %s\n' "${INFO_COUNT}"
printf 'Relatório salvo em: %s\n' "${REPORT_PATH}"

if [[ "${FAIL_COUNT}" -eq 0 ]]; then
    printf '\nRESULTADO GERAL: APROVADO COM %s AVISO(S).\n' \
        "${WARN_COUNT}"
    exit 0
fi

printf '\nRESULTADO GERAL: REVISÃO NECESSÁRIA — %s FALHA(S).\n' \
    "${FAIL_COUNT}"
exit 1
