# Dissertação PPGCC/UFSJ — ITI / saneamento

```bash
cd docs/Dissertacao_PPGCC
latexmk -pdf ufsj-abntex2.tex
# ou: make pdf
```

**PDF:** manter somente `ufsj-abntex2.pdf` nesta pasta (saída da compilação). Não criar cópias datadas (`ufsj-abntex2(…).pdf`), `novo.pdf` nem outros aliases — o `.gitignore` já ignora `*.pdf`.

O repositório versiona `generated/*.tex` e figuras em `generated/figures/iti_v2/` para compilação offline do PDF.

## Regenerar números e figuras a partir da campanha

Na raiz do lab:

```bash
./scripts/campaigns/iti_v2.sh postprocess iti_v2_prod_20261022
```

O passo `postprocess` reexecuta métricas e, quando a variável de ambiente **`FSL_HARNESS_ROOT`** aponta para os scripts de exportação LaTeX ITI (ambiente de desenvolvimento do autor), atualiza `generated/` e opcionalmente recompila o PDF. Sem essa variável, apenas os artefatos JSON da campanha são atualizados; o PDF ainda pode ser gerado a partir dos `.tex` versionados.

Alternativa mínima no repo: `export-thesis` (JSON/manifestos) via o mesmo script de campanha.

## Estrutura ativa

`ufsj-abntex2.tex` inclui: `01_introducao` … `04_metodologia`, `06_resultados`, `07_consideracoes_finais`, `99_apendices`.

`\qualificacaoparcialtrue` limita a caps. 1–2 + apêndice; o padrão é o volume completo (`\qualificacaoparcialfalse`).

## Artefatos auxiliares

Não versionar nesta pasta rascunhos de revisão editorial (`REVISAO*.md`) nem capítulos LaTeX legados retirados da compilação.

Números canônicos da campanha: `docs/research_trail/part-04-results.md` §4.7.
