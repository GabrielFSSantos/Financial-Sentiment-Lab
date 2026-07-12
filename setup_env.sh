#!/bin/bash

set -euo pipefail


# ============================================================
# DIRETÓRIOS
# ============================================================

SCRIPT_DIR="$(
    cd "$(dirname "${BASH_SOURCE[0]}")"
    pwd
)"

VENV_DIR="$SCRIPT_DIR/venv"
REQUIREMENTS_FILE="$SCRIPT_DIR/requirements.txt"
REQUIREMENTS_HASH_FILE="$VENV_DIR/.requirements.sha256"


# ============================================================
# MODO DE SAÍDA
#
# O executar_finbert.sh chama:
#
#   setup_env.sh --quiet
#
# Assim, informações repetidas não são exibidas em todas as
# execuções.
# ============================================================

QUIET=false

if [[ "${1:-}" == "--quiet" ]]; then
    QUIET=true
fi

log() {
    if [[ "$QUIET" == false ]]; then
        echo "$@"
    fi
}

erro() {
    echo "ERRO: $*" >&2
    exit 1
}


# ============================================================
# VALIDAR requirements.txt
# ============================================================

if [[ ! -f "$REQUIREMENTS_FILE" ]]; then
    erro "requirements.txt não encontrado: $REQUIREMENTS_FILE"
fi


# ============================================================
# LOCALIZAR O PYTHON
#
# No SDumont, o módulo Python deve ser carregado pelo
# executar_finbert.sh antes deste script ser chamado.
# ============================================================

if command -v python3 >/dev/null 2>&1; then
    PYTHON_BASE="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_BASE="python"
else
    erro "Python 3 não foi encontrado.

No Ubuntu ou WSL:
  sudo apt update
  sudo apt install python3 python3-venv python3-pip

No SDumont:
  carregue o módulo Python no executar_finbert.sh."
fi


# ============================================================
# VALIDAR OU CRIAR O AMBIENTE VIRTUAL
# ============================================================

AMBIENTE_NOVO=false

if [[ -x "$VENV_DIR/bin/python" ]]; then
    if ! "$VENV_DIR/bin/python" \
        -c "import sys" >/dev/null 2>&1; then

        log "O ambiente virtual existente está inválido."
        log "Recriando o ambiente..."

        rm -rf "$VENV_DIR"
    fi
fi

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
    log "Criando ambiente virtual em: $VENV_DIR"

    if ! "$PYTHON_BASE" -m venv "$VENV_DIR"; then
        erro "Não foi possível criar o ambiente virtual.

No Ubuntu ou WSL, verifique:
  sudo apt install python3-venv"
    fi

    AMBIENTE_NOVO=true
fi


# ============================================================
# ATIVAR O AMBIENTE
# ============================================================

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"


# ============================================================
# CALCULAR O HASH DO requirements.txt
#
# O hash permite identificar se o arquivo foi modificado desde
# a última instalação.
# ============================================================

CURRENT_REQUIREMENTS_HASH="$(
    sha256sum "$REQUIREMENTS_FILE" | awk '{print $1}'
)"

SAVED_REQUIREMENTS_HASH=""

if [[ -f "$REQUIREMENTS_HASH_FILE" ]]; then
    SAVED_REQUIREMENTS_HASH="$(
        cat "$REQUIREMENTS_HASH_FILE"
    )"
fi


# ============================================================
# VERIFICAR AS DEPENDÊNCIAS
# ============================================================

DEPENDENCIAS_VALIDAS=true

if ! python - <<'PY' >/dev/null 2>&1
import numpy
import pandas
import torch
import transformers
PY
then
    DEPENDENCIAS_VALIDAS=false
fi


# ============================================================
# DECIDIR SE É NECESSÁRIO INSTALAR
# ============================================================

INSTALAR=false

if [[ "$AMBIENTE_NOVO" == true ]]; then
    INSTALAR=true
elif [[ "$DEPENDENCIAS_VALIDAS" == false ]]; then
    INSTALAR=true
elif [[ "$CURRENT_REQUIREMENTS_HASH" \
    != "$SAVED_REQUIREMENTS_HASH" ]]; then

    INSTALAR=true
fi


# ============================================================
# INSTALAR SOMENTE QUANDO NECESSÁRIO
# ============================================================

if [[ "$INSTALAR" == true ]]; then
    echo "Instalando dependências do projeto..."

    if [[ "$AMBIENTE_NOVO" == true ]]; then
        python -m pip install --upgrade pip
    fi

    python -m pip install \
        -r "$REQUIREMENTS_FILE"

    printf "%s" \
        "$CURRENT_REQUIREMENTS_HASH" \
        > "$REQUIREMENTS_HASH_FILE"

    echo "Dependências instaladas com sucesso."
else
    log "Ambiente Python já está configurado."
fi


# ============================================================
# VALIDAÇÃO FINAL
# ============================================================

if ! python - <<'PY' >/dev/null 2>&1
import numpy
import pandas
import torch
import transformers
PY
then
    erro "Não foi possível importar todas as dependências."
fi


# ============================================================
# MOSTRAR INFORMAÇÕES QUANDO EXECUTADO DIRETAMENTE
# ============================================================

if [[ "$QUIET" == false ]]; then
    python - <<'PY'
import sys

import numpy
import pandas
import torch
import transformers

print()
print("Ambiente configurado:")
print("Python:", sys.version.split()[0])
print("PyTorch:", torch.__version__)
print("Transformers:", transformers.__version__)
print("Pandas:", pandas.__version__)
print("NumPy:", numpy.__version__)
print("CUDA disponível:", torch.cuda.is_available())

if torch.cuda.is_available():
    print("GPU:", torch.cuda.get_device_name(0))
else:
    print("Dispositivo disponível: CPU")
PY
fi