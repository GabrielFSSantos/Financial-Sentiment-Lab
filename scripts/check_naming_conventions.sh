#!/usr/bin/env bash
# DR-014: avisos de paths com slug PT fora das exceções documentadas.

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd -P)"

VIOLATIONS=0

report() {
    printf '[VIOLACAO] %s\n' "$1"
    VIOLATIONS=$((VIOLATIONS + 1))
}

# Basenames legados proibidos em docs/ (exceto Dissertacao_PPGCC).
FORBIDDEN_DOC_BASENAMES=(
    '01_visao_e_conceitos.md'
    '03_modulos.md'
    '04_formulas_iti.md'
    '05_validacao_research.md'
    '06_configuracoes.md'
    '09_testes.md'
    '10_arquitetura_e_manutencao.md'
    '11_fluxo_ponta_a_ponta.md'
    '12_regras_de_negocio.md'
    '13_guia_leitura_dev_e_agente.md'
    'rotulacao_entity_sentiment.md'
)

for base in "${FORBIDDEN_DOC_BASENAMES[@]}"; do
    while IFS= read -r -d '' path; do
        report "arquivo legado ainda presente: ${path#"${PROJECT_ROOT}/"}"
    done < <(find "${PROJECT_ROOT}/docs" -name "${base}" ! -path '*/Dissertacao_PPGCC/*' -print0 2>/dev/null)
done

# Tokens PT em nomes de arquivo sob docs/ (heurística).
while IFS= read -r -d '' path; do
    base="$(basename "$path")"
    case "$base" in
        *_ptbr.*|*_pt.*|pt_br.*|*metodologia*|*introducao*|*revisao*|*proposta*|*andamentos*|*pretextual*|*anexos*|*apendices*)
            continue
            ;;
    esac
    if [[ "$base" =~ (regras|visao|rotulacao|configuracoes|testes|modulos|fluxo_ponta|validacao_) ]]; then
        report "slug PT em docs: ${path#"${PROJECT_ROOT}/"}"
    fi
done < <(find "${PROJECT_ROOT}/docs" -type f \( -name '*.md' -o -name '*.yaml' \) ! -path '*/Dissertacao_PPGCC/*' -print0 2>/dev/null)

# Módulos Python com tokens PT no nome (exceto classifier_eval_pt, pt_br).
while IFS= read -r -d '' path; do
    base="$(basename "$path")"
    case "$base" in
        classifier_eval_pt.py|pt_br.py|*_ptbr.py)
            continue
            ;;
    esac
    if [[ "$base" =~ (noticia|rotulo|anotador|regras|visao) ]]; then
        report "módulo Python com slug PT: ${path#"${PROJECT_ROOT}/"}"
    fi
done < <(find "${PROJECT_ROOT}/modules" "${PROJECT_ROOT}/tests" -type f -name '*.py' -print0 2>/dev/null)

if [[ "${VIOLATIONS}" -gt 0 ]]; then
    printf '\nTotal: %d violação(ões). Ver CONTRIBUTING.md e DR-014.\n' "${VIOLATIONS}"
    exit 1
fi

printf 'Nomenclatura: nenhuma violação detectada.\n'
exit 0
