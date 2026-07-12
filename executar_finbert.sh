#!/bin/bash

# ============================================================
# CONFIGURAÇÕES DO SLURM / SANTOS DUMONT
#
# Para executar localmente, mantenha as linhas abaixo como estão.
#
# Para usar no SDumont:
# 1. altere os valores de conta e partição;
# 2. remova um "#" do início das diretivas ##SBATCH;
# 3. ajuste os módulos Python/CUDA mais abaixo;
# 4. execute:
#
#    sbatch executar_finbert.sh
# ============================================================

##SBATCH --job-name=finbert_ptbr
##SBATCH --output=logs/finbert_%j.out
##SBATCH --error=logs/finbert_%j.err
##SBATCH --account=SEU_PROJETO
##SBATCH --partition=SUA_PARTICAO
##SBATCH --nodes=1
##SBATCH --ntasks=1
##SBATCH --cpus-per-task=4
##SBATCH --gres=gpu:1
##SBATCH --mem=32G
##SBATCH --time=00:30:00

set -euo pipefail


# ============================================================
# LOCALIZAR O PROJETO
# ============================================================

PROJECT_DIR="$(
    cd "$(dirname "${BASH_SOURCE[0]}")"
    pwd
)"

SETUP_SCRIPT="$PROJECT_DIR/setup_env.sh"
PYTHON_SCRIPT="$PROJECT_DIR/finbert_inferencia.py"
VENV_DIR="$PROJECT_DIR/venv"


# ============================================================
# CONFIGURAÇÕES DO SDUMONT
#
# Descomente e ajuste somente quando souber os nomes exatos
# dos módulos disponíveis no ambiente do projeto.
#
# Consulte no SDumont:
#
#   module avail
#   module spider python
#   module spider cuda
# ============================================================

# module purge
# module load python
# module load cuda


# ============================================================
# CONVERTER CAMINHOS RELATIVOS EM CAMINHOS DO PROJETO
#
# Exemplos:
#
# MODEL_DIR=FinBERT-PT-BR
# será transformado em:
# /caminho/do/projeto/FinBERT-PT-BR
#
# Caminhos absolutos permanecem inalterados.
# ============================================================

resolver_caminho() {
    local caminho="$1"

    if [[ "$caminho" = /* ]]; then
        printf "%s\n" "$caminho"
    else
        printf "%s/%s\n" "$PROJECT_DIR" "$caminho"
    fi
}


# ============================================================
# PARÂMETROS DA EXECUÇÃO
#
# Todos podem ser alterados sem editar este arquivo.
#
# Exemplos:
#
# BATCH_SIZE=64 ./executar_finbert.sh
#
# DEVICE=cpu ./executar_finbert.sh
#
# MODEL_DIR=OutroModelo \
# OUTPUT_FILE=resultados/outro_modelo.csv \
# ./executar_finbert.sh
# ============================================================

MODEL_DIR="$(
    resolver_caminho "${MODEL_DIR:-FinBERT-PT-BR}"
)"

INPUT_FILE="$(
    resolver_caminho "${INPUT_FILE:-dados/noticias.csv}"
)"

OUTPUT_FILE="$(
    resolver_caminho \
        "${OUTPUT_FILE:-resultados/noticias_classificadas.csv}"
)"

TEXT_COLUMN="${TEXT_COLUMN:-noticia}"
BATCH_SIZE="${BATCH_SIZE:-32}"
MAX_LENGTH="${MAX_LENGTH:-512}"
DEVICE="${DEVICE:-auto}"


# ============================================================
# FUNÇÃO DE ERRO
# ============================================================

erro() {
    echo "ERRO: $*" >&2
    exit 1
}


# ============================================================
# VALIDAR PARÂMETROS BÁSICOS
# ============================================================

if ! [[ "$BATCH_SIZE" =~ ^[1-9][0-9]*$ ]]; then
    erro "BATCH_SIZE deve ser um número inteiro maior que zero."
fi

if ! [[ "$MAX_LENGTH" =~ ^[1-9][0-9]*$ ]]; then
    erro "MAX_LENGTH deve ser um número inteiro maior que zero."
fi

case "$DEVICE" in
    auto|cpu|cuda)
        ;;
    *)
        erro "DEVICE deve ser: auto, cpu ou cuda."
        ;;
esac


# ============================================================
# CRIAR DIRETÓRIOS NECESSÁRIOS
# ============================================================

mkdir -p "$PROJECT_DIR/logs"
mkdir -p "$(dirname "$OUTPUT_FILE")"


# ============================================================
# VALIDAR ARQUIVOS DO PROJETO
# ============================================================

if [[ ! -f "$SETUP_SCRIPT" ]]; then
    erro "setup_env.sh não encontrado: $SETUP_SCRIPT"
fi

if [[ ! -f "$PYTHON_SCRIPT" ]]; then
    erro "finbert_inferencia.py não encontrado: $PYTHON_SCRIPT"
fi

if [[ ! -d "$MODEL_DIR" ]]; then
    erro "Pasta do modelo não encontrada: $MODEL_DIR"
fi

if [[ ! -f "$INPUT_FILE" ]]; then
    erro "Arquivo de entrada não encontrado: $INPUT_FILE"
fi


# ============================================================
# PREPARAR O AMBIENTE
#
# O setup_env.sh somente instala dependências quando:
#
# - o ambiente virtual ainda não existe;
# - alguma dependência está ausente;
# - o requirements.txt foi alterado.
# ============================================================

bash "$SETUP_SCRIPT" --quiet


# ============================================================
# ATIVAR O AMBIENTE VIRTUAL
# ============================================================

if [[ ! -f "$VENV_DIR/bin/activate" ]]; then
    erro "Ambiente virtual não encontrado: $VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"


# ============================================================
# CONFIGURAÇÃO DO TOKENIZER
#
# Evita mensagens sobre paralelismo durante a tokenização.
# Não interfere no carregamento local do modelo.
# ============================================================

export TOKENIZERS_PARALLELISM=false


# ============================================================
# IDENTIFICAR O TIPO DE EXECUÇÃO
# ============================================================

if [[ -n "${SLURM_JOB_ID:-}" ]]; then
    EXECUTION_MODE="Santos Dumont / Slurm"
else
    EXECUTION_MODE="Local"
fi


# ============================================================
# MOSTRAR CONFIGURAÇÕES DO TESTE
# ============================================================

echo "============================================================"
echo "Execução de análise de sentimentos"
echo "============================================================"
echo "Modo: $EXECUTION_MODE"

if [[ -n "${SLURM_JOB_ID:-}" ]]; then
    echo "Job Slurm: $SLURM_JOB_ID"
fi

echo "Máquina: $(hostname)"
echo "Modelo: $MODEL_DIR"
echo "Entrada: $INPUT_FILE"
echo "Saída: $OUTPUT_FILE"
echo "Coluna de texto: $TEXT_COLUMN"
echo "Batch size: $BATCH_SIZE"
echo "Máximo de tokens: $MAX_LENGTH"
echo "Dispositivo solicitado: $DEVICE"
echo "Início: $(date)"
echo


# ============================================================
# EXECUTAR O PROGRAMA
#
# O mesmo comando Python é utilizado localmente e no SDumont.
#
# Quando submetido com sbatch, o próprio script já está sendo
# executado dentro do nó e dos recursos reservados pelo Slurm.
# ============================================================

python "$PYTHON_SCRIPT" \
    --model-dir "$MODEL_DIR" \
    --input "$INPUT_FILE" \
    --output "$OUTPUT_FILE" \
    --text-column "$TEXT_COLUMN" \
    --batch-size "$BATCH_SIZE" \
    --max-length "$MAX_LENGTH" \
    --device "$DEVICE"


# ============================================================
# FINALIZAÇÃO
# ============================================================

echo
echo "============================================================"
echo "Execução finalizada"
echo "============================================================"
echo "Resultado: $OUTPUT_FILE"
echo "Fim: $(date)"