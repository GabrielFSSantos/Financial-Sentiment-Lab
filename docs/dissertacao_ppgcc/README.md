# Dissertação PPGCC/UFSJ — ITI / saneamento

```bash
cd docs/dissertacao_ppgcc
make pdf
```

**PDF:** única cópia de entrega em `output/dissertacao_ppgcc.pdf`. Artefatos LaTeX ficam em `build/` (inclui `dissertacao_ppgcc.bbl` após BibTeX); `make clean` remove tudo efêmero.

Volume completo (`\qualificacaoparcialfalse`): espere **~56 páginas**. `make pdf` falha se o `.bbl` não for gerado ou restarem citações indefinidas. Regressão opcional: `make verify` (variável `FSL_BASELINE_PDF` aponta para um PDF de referência).

## Estrutura

| Pasta / arquivo | Função |
|-----------------|--------|
| `dissertacao_ppgcc.tex` | Master do manuscrito |
| `chapters/` | Capítulos e pré-textual (`00_` … `99_`) |
| `styles/` | Classe UFSJ, pacotes abnTeX2, `.bst`, `.sty` |
| `referencias.bib` | Bibliografia |
| `generated/` | Snippets, tabelas e figuras exportadas da campanha |
| `build/` | LaTeX intermediário (não versionar) |
| `output/` | PDF final (não versionar) |

## Stack LaTeX (abnTeX2)

O master usa `\documentclass{ufsj-abntex2}` — classe institucional em `styles/ufsj-abntex2.cls`, derivada do **abnTeX2** (`styles/abntex2.cls`, `abntex2cite`, estilo `abntex2-alf`). Opções de citação ABNT ficam no preamble de `dissertacao_ppgcc.tex`.

`\qualificacaoparcialtrue` no master limita a caps. 1–2 + apêndice; o padrão é o volume completo.

## Regenerar números e figuras

Na raiz do lab:

```bash
./scripts/campaigns/iti_v2.sh postprocess iti_v2_prod_20261022
```

Com `FSL_HARNESS_ROOT`, o postprocess atualiza `generated/` e pode chamar `make pdf` nesta pasta.

Apresentação de qualificação (PDF): `docs/apresentacao_ppgcc/`.

## Artefatos auxiliares

Relatórios de revisão oral e checklists de defesa não ficam neste diretório — apenas o manuscrito e artefatos LaTeX gerados.

Números canônicos: `docs/research_trail/part-04-results.md` §4.7.
