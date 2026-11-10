# Relatório — revisão direcionada (pendências) — 09/11/2026

## Escopo

Aplicação fiel de `CURSOR_PENDENCIAS_QUALIFICACAO_2026-11-09.md` sobre o estado local pós-revisão editorial, preservando resultados e o estudo de caso da Sabesp no corpo do texto.

## Arquivos alterados

| Arquivo | Alteração |
|---------|-----------|
| `ufsj-abntex2.tex` | Título restaurado conforme decisão do autor (Seção 2) |
| `02_fundamentacao.tex` | Parágrafo FinBERT/SentFinBERT (Seção 4.1) |
| `03_trabalhos_relacionados.tex` | Tabela 1 com cinco colunas (Seção 3) |
| `04_metodologia.tex` | `\label{sec:classificador-operacional}` + parágrafo operacional do checkpoint (Seção 4.2) |
| `99_apendices.tex` | Apêndice A (seções A.4–A.5 + Tabela 11); Apêndice B (Tabelas 14–15); Apêndice D integral (Seção 7) |
| `ROTEIRO_ORAL_QUALIFICACAO.md` | Criado (Seção 8) |
| `RELATORIO_REVISAO_QUALIFICACAO.md` | Este arquivo (Seção 11) |

Arquivos da revisão editorial anterior (`00_pretextual.tex`, capítulos 1, 6, 7, bibliografia) permanecem no working tree; não foram revertidos.

## Respostas obrigatórias (Seção 11)

### 1. Título `\titulo{...}`

```latex
\titulo{Índice temporal informacional a partir de notícias corporativas: uma proposta para empresas brasileiras de saneamento}
```

- Comando `\titulo{um estudo de caso sobre a Sabesp}`: **ausente** nos `.tex`.
- Metadados: o PDF compilado exibe o mesmo título no objeto `Title` do `mutool info` (UTF-16 equivalente ao texto acima).
- Páginas pré-textuais: título localizado no texto extraído na **página 2** (capa/folha de rosto no fluxo do PDF); sem menção a alteração futura de título.

### 2. Tabela 1

- Cinco colunas: sentimento financeiro, orientação à entidade, agregação temporal, papel nesta pesquisa (+ coluna Estudo).
- Localização no PDF recompilado: **página 21** (extração `mutool draw -F txt`, separador de páginas `\f`).

### 3. Tabelas 11 e 15 — paginação

| Tabela | Página no PDF (mutool) | Observação |
|--------|------------------------|------------|
| Tabela 11 (`tab:campos-anotacao`) | 8 | Ambiente `[H]`; texto da Seção A.5 na mesma página |
| Tabela 14 (`tab:ficha-corpus`) | 46 | Juntamente com Tabela 15 |
| Tabela 15 (`tab:artefatos-reproducao`) | 46 | Compactação; **não** há página isolada só com a Tabela 15 nesta compilação |

Página quase vazia dedicada apenas à Tabela 11 ou 15: **não identificada** nesta build (55 páginas totais no log).

### 4. Apêndice D — 12 casos

- IDs e pares autor/modelo: conferidos com `manual_labels_100_eval.csv` e inventário (revisão anterior).
- Casos **3, 6 e 8**: texto declara explicitamente registro restrito ao título (campo `noticia` = título no CSV).
- Caso **7**: responsabilidade da Sabesp em localidades citadas, conforme corpo preservado no CSV.
- Marcador `{discussion}`: **ausente** nos `.tex`.
- Apêndice D: **páginas 48–55** aproximadamente (índice no sumário; texto longo contínuo).

### 5. FinBERT / checkpoint

- Distinção FinBERT-PT-BR (linguagem) vs SentFinBERT-PT-BR (classificador no artigo) na Seção 2.2.
- Convenção de projeto para o classificador carregado; remissão a `sec:classificador-operacional`.
- `configs/models.yaml` (`finbert_ptbr`): `repo_id: lucas-leme/FinBERT-PT-BR`, `revision: main`, `BertForSequenceClassification`, mapeamento `0=POSITIVE`, `1=NEGATIVE`, `2=NEUTRAL` — **coincide** com o parágrafo inserido; **sem conflito** a reportar.
- Não se afirma identidade entre checkpoint da campanha e avaliação do artigo original.

### 6. Resultados e fórmulas

- Capítulos 5–6, tabelas geradas (`\input{generated/tables/...}`) e métricas: **não editados** nesta rodada.
- Valores obrigatórios (1.253, 100, 50%, κ, 94 semanas, Δρ, etc.): preservados no LaTeX existente.

### 7. Compilação e QA visual

| Item | Resultado |
|------|-----------|
| Comando | `latexmk -pdf -interaction=nonstopmode -halt-on-error -file-line-error ufsj-abntex2.tex` |
| Saída | `ufsj-abntex2.pdf`, **55 páginas**, ~1,76 MB |
| Erros LaTeX / citações `undefined` | Nenhum no `.log` |
| `pdfinfo` / `pdftotext` | Indisponíveis no WSL; substituídos por `mutool info` e `mutool draw -F txt` |
| Overfull `\hbox` | Avisos pontuais (ex.: Apêndice D, metodologia); sem erro de compilação |

### 8. Verificações adicionais

- `git diff --check`: OK.
- Branch de segurança: `backup/pre-pendencias-2026-11-09`.
- **Não** executados: nova inferência, campanha financeira, alteração de `configs/models.yaml` ou código ITI.

## Limitações / itens não executados

- Inspeção visual pixel a pixel das tabelas (layout fino) depende de leitura humana do PDF; a paginação foi verificada por extração de texto.
- Reauditoria linha a linha do P02 e probabilidades da campanha: permanecem fora do escopo, conforme texto das Tabelas 14–15.

## Decisão do autor registrada

- Título fixo: *uma proposta para empresas brasileiras de saneamento* (empírico continua no estudo de caso Sabesp no corpo).
- Apoio oral: `ROTEIRO_ORAL_QUALIFICACAO.md`.

## Diff (resumo)

```
9 arquivos .tex/.bib alterados nesta sessão acumulada; +2 arquivos .md novos (roteiro e relatório).
```

**Commit/push:** não executado.
