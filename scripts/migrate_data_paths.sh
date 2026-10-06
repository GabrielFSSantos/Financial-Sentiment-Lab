#!/usr/bin/env bash
# Migra data/saneamento_corpus (PT) → data/water_utilities_corpus (EN).
# Idempotente: pula arquivos que já existem no destino.
#
#   ./scripts/migrate_data_paths.sh
#   ./scripts/migrate_data_paths.sh --compat-symlinks   # atalhos nos paths legados

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd -P)"
OLD_DIR="${PROJECT_ROOT}/data/saneamento_corpus"
NEW_DIR="${PROJECT_ROOT}/data/water_utilities_corpus"
COMPAT=false

for arg in "$@"; do
    case "$arg" in
        --compat-symlinks) COMPAT=true ;;
        -h|--help)
            echo "Uso: $0 [--compat-symlinks]"
            exit 0
            ;;
        *)
            echo "Opção desconhecida: $arg" >&2
            exit 1
            ;;
    esac
done

declare -A FILE_MAP=(
    [noticias.csv]=articles.csv
    [noticias_pendentes.csv]=articles_pending.csv
    [noticias_strict.csv]=articles_strict.csv
    [noticias_strict_sabesp.csv]=articles_strict_sabesp.csv
    [noticias_strict_sabesp_event_filtered.csv]=articles_strict_sabesp_event_filtered.csv
    [rotulos_manual_100.csv]=manual_labels_100.csv
    [rotulos_manual_100_exploratorio.csv]=manual_labels_100_exploratorio.csv
    [rotulos_manual_100_eval.csv]=manual_labels_100_eval.csv
    [.scrape_state.json]=.scrape_state.json
)

if [[ ! -d "${OLD_DIR}" ]]; then
    if [[ -d "${NEW_DIR}" ]]; then
        echo "Destino já existe e origem legada ausente: ${NEW_DIR}"
        exit 0
    fi
    echo "Nada para migrar (sem ${OLD_DIR})."
    exit 0
fi

mkdir -p "${NEW_DIR}"

if [[ -d "${OLD_DIR}/raw" && ! -d "${NEW_DIR}/raw" ]]; then
    mv "${OLD_DIR}/raw" "${NEW_DIR}/raw"
elif [[ -d "${OLD_DIR}/raw" && -d "${NEW_DIR}/raw" ]]; then
    echo "raw/ já existe em ambos; mesclagem manual se necessário."
fi

for old_name in "${!FILE_MAP[@]}"; do
    new_name="${FILE_MAP[$old_name]}"
    src="${OLD_DIR}/${old_name}"
    dst="${NEW_DIR}/${new_name}"
    if [[ -f "${src}" && ! -e "${dst}" ]]; then
        mv "${src}" "${dst}"
        echo "mv ${old_name} → ${new_name}"
    fi
done

if [[ "${COMPAT}" == true ]]; then
    mkdir -p "${OLD_DIR}"
    for old_name in "${!FILE_MAP[@]}"; do
        new_name="${FILE_MAP[$old_name]}"
        dst="${NEW_DIR}/${new_name}"
        link="${OLD_DIR}/${old_name}"
        if [[ -e "${dst}" && ! -e "${link}" ]]; then
            ln -sf "../water_utilities_corpus/${new_name}" "${link}"
            echo "symlink ${link}"
        fi
    done
    if [[ -d "${NEW_DIR}/raw" && ! -e "${OLD_DIR}/raw" ]]; then
        ln -sf "../water_utilities_corpus/raw" "${OLD_DIR}/raw"
    fi
fi

if [[ -d "${OLD_DIR}" ]] && [[ -z "$(ls -A "${OLD_DIR}" 2>/dev/null || true)" ]]; then
    rmdir "${OLD_DIR}" 2>/dev/null || true
fi

echo "Migração concluída. Corpus canônico: ${NEW_DIR}"
