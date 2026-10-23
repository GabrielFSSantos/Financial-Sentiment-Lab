# Dissertação PPGCC/UFSJ — ITI / saneamento

```bash
cd docs/Dissertacao_PPGCC
latexmk -pdf ufsj-abntex2.tex
# ou: make pdf
```

Exportar números e figuras da campanha (raiz do lab):

```bash
./scripts/campaigns/iti_v2.sh postprocess iti_v2_prod_20261022
```

Isso atualiza `generated/iti_v2_results_snippet.tex`, `generated/tables/`, `generated/figures/iti_v2/` e tenta `latexmk` nesta pasta.

## Estrutura ativa

`ufsj-abntex2.tex` inclui: `01_introducao` … `04_metodologia`, `06_resultados`, `07_consideracoes_finais`, `99_apendices`.

`\qualificacaoparcialtrue` limita a caps. 1–2 + apêndice; o padrão é o volume completo (`\qualificacaoparcialfalse`).

## Fora deste diretório

Relatórios de auditoria editorial, planos Cursor e capítulos LaTeX legados ficam no meta-workspace `Workspaces/financial-sentiment-lab/` (`harness/qualification/reports/`, `plans/`, `archive/`). Não adicionar `REVISAO*.md` aqui.

Números canônicos da campanha: `docs/research_trail/part-04-results.md`.
