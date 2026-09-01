# Trajetória experimental — Financial Sentiment Lab

Registro versionado da evolução da pesquisa: decisões tomadas, escopo de cada rodada, resultados run a run e o que aprendemos. Este documento é a **narrativa** do projeto; conceitos e fórmulas estão em [documentacao.md](documentacao.md) e comandos em [README.md](../README.md). Índice geral: [docs/README.md](README.md).

---

## Como ler este documento

Cada **marco** agrupa uma fase metodológica ou campanha. Dentro dele, cada **run** (execução numerada) testa uma hipótese isolada. Os blocos seguem sempre a mesma estrutura:

- **Escopo dos dados** — de onde vieram as notícias, qual empresa, qual período, corpus broad ou strict.
- **Índice (ITI)** — como o Índice Temporal Informacional foi calculado e agregado.
- **Validação contra mercado** — como comparamos com a ação real (SBSP3) e com baselines internos.
- **Resultado** — win rate (taxa de vitória) e vitórias significativas.
- **ITI vs baselines** — tabela por horizonte; ✓ = ITI correlaciona melhor que o baseline; ★ = vitória significativa (bootstrap).
- **Relação com a ação** — correlação direta ITI × retorno futuro (não é aposta binária subiu/desceu).
- **Leitura** — interpretação para a próxima decisão.

Termos em inglês aparecem entre parênteses na primeira menção de cada seção.

---

## Glossário rápido

| Termo | Significado |
|-------|-------------|
| **ITI** (Information Trend Index) | Índice de sentimento acumulado no tempo a partir das notícias |
| **α (alpha)** | Parâmetro de memória do EWMA — quanto do passado o índice retém (não é alpha de mercado) |
| **Baseline** | Alternativa simples calculada só com notícias, para comparar com o ITI |
| **Win rate** | Proporção de comparações em que o ITI supera um baseline em Pearson ou Spearman |
| **Overlap** | Semanas em que há simultaneamente ITI, baselines e preço da ação alinhados |
| **B0–B3** | Quatro baselines internos — ver [documentacao.md §1.5](documentacao.md#15-conceitos-em-linguagem-acessível) |

---

## Template para novas runs

Ao adicionar um marco futuro, copie o esqueleto abaixo e preencha com dados do `manifest.json` e de `outputs/{run_id}/research/.../incremental_deltas.csv`.

```markdown
### Run {id} — {título}

**Hipótese** — ...

#### Escopo dos dados
...

#### Índice (ITI)
...

#### Validação contra mercado
...

#### Resultado
...

#### ITI vs baselines
(tabela)

#### Relação com a ação
...

#### Leitura
- ...

#### Artefatos
- Config: ...
- Saída: outputs/...
```

---

## Marco 0 — Rodada broad (pré-correção)

**Data:** 24/08/2026  
**Run:** `saneamento_pt_20260824`  
**Status:** superada pela campanha Sabesp 2026

Primeira execução completa do pipeline com corpus **broad** (amplo) de saneamento: múltiplas empresas (Sabesp, Copasa, Sanepar), coleta multiportal sem filtro strict rigoroso. O research (validação) rodou em frequência **diária**, enquanto o ITI semanal era gerado mas **não usado** na comparação — baselines diários foram confrontados com séries incompatíveis. Os números desta rodada servem como linha de base histórica, mas **não devem ser interpretados como conclusão científica**.

### Escopo dos dados

| Campo | Valor |
|-------|-------|
| Empresa(s) | Sabesp, Copasa, Sanepar (multi-empresa) |
| Período das notícias | janela ampla do corpus `saneamento_corpus` |
| Modo do corpus | **broad** — inclui ruído e registros sem entidade clara |
| Dataset YAML | `saneamento_corpus` |
| Overlap diário | ~380 dias |

### Resultado

| Modelo | Vitórias | Win rate | Significativas |
|--------|----------|----------|----------------|
| `finbert_ptbr` | 0/24 | 0% | 0 |
| `pt_br_financial_sentiment_analysis` | 3/24 | 12,5% | 0 |

### O que aprendemos

- Lacunas metodológicas documentadas na [auditoria metodológica](#auditoria-metodológica--por-que-o-marco-1-existiu) motivaram a campanha corrigida (Marco 1).
- Win rate baixo (~0–12%) refletia tanto sinal fraco quanto **comparação inválida** (frequências misturadas).

### Artefatos

- Saída: `outputs/saneamento_pt_20260824/`

---

## Auditoria metodológica — por que o Marco 1 existiu

Antes da campanha Sabesp 2026 (Marco 1), revisamos o protocolo da rodada broad e listamos lacunas que tornavam os números difíceis de interpretar. A tabela abaixo resume o estado **pré-correção** e o que mudou no código e nos YAMLs. Detalhes técnicos das correções estão em [documentacao.md §5.0](documentacao.md#50-modos-diário-e-semanal) e [§6](documentacao.md#6-configurações-principais).

| Lacuna | Impacto | Correção |
|--------|---------|----------|
| Research usava só `iti_daily.csv` | ITI semanal ignorado na validação | `index_frequency: weekly` + `weekly_align.py` |
| Baselines só diários | Comparação inválida com ITI semanal | `resample_baselines_weekly` |
| Sem filtro empresa/janela | Sabesp diluída com outras empresas | `companies_filter` + dataset `saneamento_sabesp_strict_event` |
| `strict` só na coleta | Ruído broad permanecia no raw | `build_strict_corpus()` offline |
| Sem `--experiment-config` | Grid alpha/ablação manual | Flag no CLI do runner |
| Horizontes em dias | Incompatível com ITI semanal | Horizontes `[1, 2, 4]` semanas |

### Decisões fixadas na campanha

**ITI semanal.** Agregação padrão `iti_liquido_last` (estado EWMA no último dia útil da semana). A run R8 testou `iti_liquido_mean` (média dos dias da semana) e performou pior. Retorno semanal = soma dos `log_return` diários alinhada ao `period_end` do ITI.

**Corpus strict.** `noticias_strict.csv` preserva `noticias.csv` broad; reaplica `match_entity(titulo + noticia)` em cada registro de `raw/` e descarta registros sem entidade (sem gerar PENDENTE).

**Equação ITI.** Forma completa documentada em [documentacao.md §4](documentacao.md#4-fórmulas-do-iti). Ablações via `disabled_dimensions` ou `equation_mode: simplified_dc` (R6: `I_n = d·c`, `w_n = c`).

**Entidades e tickers.** Sabesp → `SBSP3.SA`; Copasa → `CSMG3.SA`; Sanepar → `SAPR4.SA`.

### Gate de coleta pré-evento (mai–out/2022)

Avançar a coleta para o período pré-privatização somente se **uma** das condições for atendida:

- ITI vence B1/B2 em ≥40% das comparações em alguma config R1–R8, **ou**
- FinBERT ≥70% concordância manual **e** correlação semanal ITI×retorno p < 0,05 em h = 2.

A run **R1** atingiu 41,7% de win rate (≥ 40%) — gate atendido. Ver [Decisões tomadas](#decisões-tomadas) no Marco 1.

### Artefatos da auditoria e campanha

- Configs por run: `configs/campaigns/sabesp_2026/experiments/r0..r9.yaml` (antes: `configs/experiments/sabesp/`)
- Research semanal: `configs/campaigns/sabesp_2026/research_weekly.yaml`
- Manifest: `outputs/campaigns/sabesp_2026/manifest.json`
- Orquestração: `scripts/campaigns/sabesp_2026.sh`

---

## Marco 1 — Campanha Sabesp 2026 (R0–R9)

**Data:** 24/08/2026  
**Campanha:** `sabesp_2026`  
**Status:** concluída

Correção metodológica antes de expandir a coleta: corpus **strict** só Sabesp, ITI calculado diariamente mas validado em frequência **semanal** alinhada ao mercado, horizontes em semanas (1, 2, 4), filtro de empresa no research. Dez runs (R0–R9) testam α, ablações da equação, agregação semanal e modelo alternativo.

### Resumo comparativo

| Run | ID | Mudança | Vitórias | Win rate | Δ vs R0 | Significativas |
|-----|-----|---------|----------|----------|---------|----------------|
| R0 | `sabesp_r0_baseline` | Referência corrigida | 5/24 | 20,8% | — | 0 |
| R1 | `sabesp_r1_alpha070` | α = 0,70 | 10/24 | **41,7%** | +20,8 pp | **2** |
| R2 | `sabesp_r2_alpha095` | α = 0,95 | 2/24 | 8,3% | −12,5 pp | 0 |
| R3 | `sabesp_r3_no_novelty` | sem novelty `u` | 5/24 | 20,8% | 0 | 0 |
| R4 | `sabesp_r4_no_event` | sem evento `e` | 6/24 | 25,0% | +4,2 pp | 0 |
| R5 | `sabesp_r5_no_relevance` | sem relevance `r` | 5/24 | 20,8% | 0 | 0 |
| R6 | `sabesp_r6_simplified` | equação `d·c` | 5/24 | 20,8% | 0 | 0 |
| R7 | `sabesp_r7_horizon_fixed` | α fixo por h | 6/24 | 25,0% | +4,2 pp | 0 |
| R8 | `sabesp_r8_weekly_mean` | média semanal ITI | 1/24 | 4,2% | −16,7 pp | 0 |
| R9 | `sabesp_r9_ensemble` | modelo PT-BR alt. | 6/24 | 25,0% | +4,2 pp | 0 |

> As 24 comparações por run resultam de 4 baselines × 2 métricas de conclusão (Pearson, Spearman) × 3 horizontes semanais. Detalhe em [documentacao.md §5](documentacao.md#50-modos-diário-e-semanal).

### Run R0 BASELINE — Baseline corrigido

**Hipótese** — Com corpus strict, ITI semanal e escopo Sabesp, o pipeline reproduz resultados interpretáveis.

**Mudança em relação ao R0** — Referência da campanha: α=0,85, equação full, `iti_liquido_last`.

#### Escopo dos dados

| Campo | Valor |
|-------|-------|
| Empresa(s) | Sabesp apenas |
| Período das notícias | nov/2023 – abr/2024 (evento de privatização) |
| Modo do corpus | **strict** — só artigos com entidade Sabesp confirmada |
| Filtro de entidade | sim — descartados registros sem match de empresa |
| Artigos | 465 |
| Dataset YAML | `saneamento_sabesp_strict_event` |

#### Índice (ITI)

| Campo | Valor |
|-------|-------|
| Cálculo do índice | **diário** — EWMA (Exponentially Weighted Moving Average) recalculado a cada dia |
| Frequência na validação | **semanal** — um ponto por semana (sexta-feira, W-FRI) |
| Coluna na validação | `iti_liquido_last` |
| α (alpha) | 0,85 |
| Equação | full (`I_n = d·m·r·c·e·u`) |
| Modelo de sentimento | `finbert_ptbr` |

#### Validação contra mercado

| Campo | Valor |
|-------|-------|
| Ticker | `SBSP3.SA` — preços reais via yfinance, cache em `data/market/prices.csv` |
| Retorno alvo | log-return (retorno logarítmico) acumulado nas próximas 1, 2 ou 4 **semanas** |
| Baselines comparados | B0–B3 — todos derivados das **nossas notícias**, não do mercado |
| Comparações por run | 24 (= 4 baselines × 2 métricas Pearson/Spearman × 3 horizontes) |
| Semanas com dados alinhados | ~24 (`overlap_days`) |

#### Resultado

- Win rate: **5/24 (20.8%)**
- Vitórias significativas: **0/24**
- Δ vs R0: —
- Conclusão automática: _iti_liquido (pearson, spearman): 5/24 vitórias (20.8%), 0 significativas (0.0%)_

#### ITI vs baselines (Pearson / Spearman)

Legenda: ✓ vitória do ITI · ★ vitória significativa · ✗ derrota

| Baseline | 1 sem (P / S) | 2 sem (P / S) | 4 sem (P / S) |
|----------|---------------|---------------|---------------|
| **B0** | ✗ / ✗ | ✗ / ✗ | ✗ / ✗ |
| **B1** | ✗ / ✗ | ✗ / ✗ | ✗ / ✗ |
| **B2** | ✗ / ✗ | ✗ / ✗ | ✗ / ✗ |
| **B3** | ✓ / ✓ | ✗ / ✓ | ✓ / ✓ |

#### Relação com a ação

Mesma lógica do R1: o ITI semanal é confrontado com log-returns futuros da `SBSP3.SA` (dados de mercado via yfinance). Métricas brutas em `outputs/sabesp_r0_baseline/research/finbert_ptbr/saneamento_sabesp_strict_event/market_metrics.csv`.

#### Leitura

- A correção metodológica elevou o win rate em relação à rodada broad (~12,5%), mas o ITI ainda perde para baselines na maioria das comparações.
- Vitórias concentradas em B3 no horizonte de 4 semanas — o impacto diário sem memória às vezes supera o EWMA com α alto.

#### Artefatos

- Config: `configs/campaigns/sabesp_2026/experiments/r0_baseline.yaml`
- Saída: `outputs/sabesp_r0_baseline/`
- Research: `outputs/sabesp_r0_baseline/research/finbert_ptbr/saneamento_sabesp_strict_event/`

### Run R1 ALPHA070 — Alpha 0,70 (mais reativo)

**Hipótese** — Um EWMA (Exponentially Weighted Moving Average) mais reativo captura melhor o choque da privatização.

**Mudança em relação ao R0** — `alpha: 0.70` (demais parâmetros iguais ao R0).

#### Escopo dos dados

| Campo | Valor |
|-------|-------|
| Empresa(s) | Sabesp apenas |
| Período das notícias | nov/2023 – abr/2024 (evento de privatização) |
| Modo do corpus | **strict** — só artigos com entidade Sabesp confirmada |
| Filtro de entidade | sim — descartados registros sem match de empresa |
| Artigos | 465 |
| Dataset YAML | `saneamento_sabesp_strict_event` |

#### Índice (ITI)

| Campo | Valor |
|-------|-------|
| Cálculo do índice | **diário** — EWMA (Exponentially Weighted Moving Average) recalculado a cada dia |
| Frequência na validação | **semanal** — um ponto por semana (sexta-feira, W-FRI) |
| Coluna na validação | `iti_liquido_last` |
| α (alpha) | 0,70 |
| Equação | full |
| Modelo de sentimento | `finbert_ptbr` |

#### Validação contra mercado

| Campo | Valor |
|-------|-------|
| Ticker | `SBSP3.SA` — preços reais via yfinance, cache em `data/market/prices.csv` |
| Retorno alvo | log-return (retorno logarítmico) acumulado nas próximas 1, 2 ou 4 **semanas** |
| Baselines comparados | B0–B3 — todos derivados das **nossas notícias**, não do mercado |
| Comparações por run | 24 (= 4 baselines × 2 métricas Pearson/Spearman × 3 horizontes) |
| Semanas com dados alinhados | ~24 (`overlap_days`) |

#### Resultado

- Win rate: **10/24 (41.7%)**
- Vitórias significativas: **2/24**
- Δ vs R0: +20.8 pp
- Conclusão automática: _iti_liquido (pearson, spearman): 10/24 vitórias (41.7%), 2 significativas (8.3%)_

#### ITI vs baselines (Pearson / Spearman)

Legenda: ✓ vitória do ITI · ★ vitória significativa · ✗ derrota

| Baseline | 1 sem (P / S) | 2 sem (P / S) | 4 sem (P / S) |
|----------|---------------|---------------|---------------|
| **B0** | ✗ / ✓ | ✗ / ✗ | ✗ / ✗ |
| **B1** | ✗ / ✗ | ✗ / ✗ | ✗ / ✓ |
| **B2** | ✗ / ✗ | ✗ / ✓ | ✗ / ✓ |
| **B3** | ✓ / ✓ | ✓ / ✓ | ★ / ★ |

#### Relação com a ação

A validação mede se o ITI da semana **correlaciona** com o retorno futuro acumulado da `SBSP3.SA` — não se o índice “acerta” direção como aposta. Na melhor run (R1), as correlações diretas ITI×mercado permanecem fracas e não significativas (ex.: Pearson h=4 semanas ≈ −0,21, p≈0,38; Spearman ≈ −0,12, p≈0,60). O ganho do R1 aparece sobretudo **em relação aos baselines de notícias**, não como correlação isolada forte com o preço.

#### Leitura

- Melhor run da campanha: win rate 41,7%, o dobro do R0.
- Única run com vitórias estatisticamente significativas (2/24): horizonte 4 semanas vs B3.
- α menor deixa o índice esquecer mais rápido e reagir ao fluxo de notícias do evento.

#### Artefatos

- Config: `configs/campaigns/sabesp_2026/experiments/r1_alpha070.yaml`
- Saída: `outputs/sabesp_r1_alpha070/`
- Research: `outputs/sabesp_r1_alpha070/research/finbert_ptbr/saneamento_sabesp_strict_event/`

### Run R2 ALPHA095 — Alpha 0,95 (mais memória)

**Hipótese** — Mais memória no EWMA suaviza ruído semanal.

**Mudança em relação ao R0** — `alpha: 0.95`.

#### Escopo dos dados

| Campo | Valor |
|-------|-------|
| Empresa(s) | Sabesp apenas |
| Período das notícias | nov/2023 – abr/2024 (evento de privatização) |
| Modo do corpus | **strict** — só artigos com entidade Sabesp confirmada |
| Filtro de entidade | sim — descartados registros sem match de empresa |
| Artigos | 465 |
| Dataset YAML | `saneamento_sabesp_strict_event` |

#### Índice (ITI)

| Campo | Valor |
|-------|-------|
| Cálculo do índice | **diário** — EWMA (Exponentially Weighted Moving Average) recalculado a cada dia |
| Frequência na validação | **semanal** — um ponto por semana (sexta-feira, W-FRI) |
| Coluna na validação | `iti_liquido_last` |
| α (alpha) | 0,95 |
| Equação | full |
| Modelo de sentimento | `finbert_ptbr` |

#### Validação contra mercado

| Campo | Valor |
|-------|-------|
| Ticker | `SBSP3.SA` — preços reais via yfinance, cache em `data/market/prices.csv` |
| Retorno alvo | log-return (retorno logarítmico) acumulado nas próximas 1, 2 ou 4 **semanas** |
| Baselines comparados | B0–B3 — todos derivados das **nossas notícias**, não do mercado |
| Comparações por run | 24 (= 4 baselines × 2 métricas Pearson/Spearman × 3 horizontes) |
| Semanas com dados alinhados | ~24 (`overlap_days`) |

#### Resultado

- Win rate: **2/24 (8.3%)**
- Vitórias significativas: **0/24**
- Δ vs R0: -12.5 pp
- Conclusão automática: _iti_liquido (pearson, spearman): 2/24 vitórias (8.3%), 0 significativas (0.0%)_

#### ITI vs baselines (Pearson / Spearman)

Legenda: ✓ vitória do ITI · ★ vitória significativa · ✗ derrota

| Baseline | 1 sem (P / S) | 2 sem (P / S) | 4 sem (P / S) |
|----------|---------------|---------------|---------------|
| **B0** | ✗ / ✗ | ✗ / ✗ | ✗ / ✗ |
| **B1** | ✗ / ✗ | ✗ / ✗ | ✗ / ✗ |
| **B2** | ✗ / ✗ | ✗ / ✗ | ✗ / ✗ |
| **B3** | ✓ / ✓ | ✗ / ✗ | ✗ / ✗ |

#### Relação com a ação

Mesma lógica do R1: o ITI semanal é confrontado com log-returns futuros da `SBSP3.SA` (dados de mercado via yfinance). Métricas brutas em `outputs/sabesp_r2_alpha095/research/finbert_ptbr/saneamento_sabesp_strict_event/market_metrics.csv`.

#### Leitura

- Pior run da campanha (8,3%): memória longa apaga o sinal do evento.
- Confirma que α ≥ 0,95 não é adequado para esta janela Sabesp.

#### Artefatos

- Config: `configs/campaigns/sabesp_2026/experiments/r2_alpha095.yaml`
- Saída: `outputs/sabesp_r2_alpha095/`
- Research: `outputs/sabesp_r2_alpha095/research/finbert_ptbr/saneamento_sabesp_strict_event/`

### Run R3 NO NOVELTY — Sem novelty (u)

**Hipótese** — Penalizar títulos repetidos (novelty) agrega informação.

**Mudança em relação ao R0** — `disabled_dimensions: [novelty]`.

#### Escopo dos dados

| Campo | Valor |
|-------|-------|
| Empresa(s) | Sabesp apenas |
| Período das notícias | nov/2023 – abr/2024 (evento de privatização) |
| Modo do corpus | **strict** — só artigos com entidade Sabesp confirmada |
| Filtro de entidade | sim — descartados registros sem match de empresa |
| Artigos | 465 |
| Dataset YAML | `saneamento_sabesp_strict_event` |

#### Índice (ITI)

| Campo | Valor |
|-------|-------|
| Cálculo do índice | **diário** — EWMA (Exponentially Weighted Moving Average) recalculado a cada dia |
| Frequência na validação | **semanal** — um ponto por semana (sexta-feira, W-FRI) |
| Coluna na validação | `iti_liquido_last` |
| α (alpha) | 0,85 |
| Equação | full sem `u` |
| Modelo de sentimento | `finbert_ptbr` |

#### Validação contra mercado

| Campo | Valor |
|-------|-------|
| Ticker | `SBSP3.SA` — preços reais via yfinance, cache em `data/market/prices.csv` |
| Retorno alvo | log-return (retorno logarítmico) acumulado nas próximas 1, 2 ou 4 **semanas** |
| Baselines comparados | B0–B3 — todos derivados das **nossas notícias**, não do mercado |
| Comparações por run | 24 (= 4 baselines × 2 métricas Pearson/Spearman × 3 horizontes) |
| Semanas com dados alinhados | ~24 (`overlap_days`) |

#### Resultado

- Win rate: **5/24 (20.8%)**
- Vitórias significativas: **0/24**
- Δ vs R0: +0.0 pp
- Conclusão automática: _iti_liquido (pearson, spearman): 5/24 vitórias (20.8%), 0 significativas (0.0%)_

#### ITI vs baselines (Pearson / Spearman)

Legenda: ✓ vitória do ITI · ★ vitória significativa · ✗ derrota

_Vitórias: h=1 vs B3 (pearson) ✓, h=1 vs B3 (spearman) ✓, h=2 vs B3 (spearman) ✓, h=4 vs B3 (pearson) ✓, h=4 vs B3 (spearman) ✓._

Tabela completa em `outputs/sabesp_r3_no_novelty/research/finbert_ptbr/saneamento_sabesp_strict_event/incremental_deltas.csv`.

#### Relação com a ação

Mesma lógica do R1: o ITI semanal é confrontado com log-returns futuros da `SBSP3.SA` (dados de mercado via yfinance). Métricas brutas em `outputs/sabesp_r3_no_novelty/research/finbert_ptbr/saneamento_sabesp_strict_event/market_metrics.csv`.

#### Leitura

- Resultado idêntico ao R0 — novelty não move o sinal nesta janela.

#### Artefatos

- Config: `configs/campaigns/sabesp_2026/experiments/r3_no_novelty.yaml`
- Saída: `outputs/sabesp_r3_no_novelty/`
- Research: `outputs/sabesp_r3_no_novelty/research/finbert_ptbr/saneamento_sabesp_strict_event/`

### Run R4 NO EVENT — Sem evento (e)

**Hipótese** — Heurísticas de evento melhoram o sinal.

**Mudança em relação ao R0** — `disabled_dimensions: [event_weight]`, heurísticas desligadas.

#### Escopo dos dados

| Campo | Valor |
|-------|-------|
| Empresa(s) | Sabesp apenas |
| Período das notícias | nov/2023 – abr/2024 (evento de privatização) |
| Modo do corpus | **strict** — só artigos com entidade Sabesp confirmada |
| Filtro de entidade | sim — descartados registros sem match de empresa |
| Artigos | 465 |
| Dataset YAML | `saneamento_sabesp_strict_event` |

#### Índice (ITI)

| Campo | Valor |
|-------|-------|
| Cálculo do índice | **diário** — EWMA (Exponentially Weighted Moving Average) recalculado a cada dia |
| Frequência na validação | **semanal** — um ponto por semana (sexta-feira, W-FRI) |
| Coluna na validação | `iti_liquido_last` |
| α (alpha) | 0,85 |
| Equação | full sem `e` |
| Modelo de sentimento | `finbert_ptbr` |

#### Validação contra mercado

| Campo | Valor |
|-------|-------|
| Ticker | `SBSP3.SA` — preços reais via yfinance, cache em `data/market/prices.csv` |
| Retorno alvo | log-return (retorno logarítmico) acumulado nas próximas 1, 2 ou 4 **semanas** |
| Baselines comparados | B0–B3 — todos derivados das **nossas notícias**, não do mercado |
| Comparações por run | 24 (= 4 baselines × 2 métricas Pearson/Spearman × 3 horizontes) |
| Semanas com dados alinhados | ~24 (`overlap_days`) |

#### Resultado

- Win rate: **6/24 (25.0%)**
- Vitórias significativas: **0/24**
- Δ vs R0: +4.2 pp
- Conclusão automática: _iti_liquido (pearson, spearman): 6/24 vitórias (25.0%), 0 significativas (0.0%)_

#### ITI vs baselines (Pearson / Spearman)

Legenda: ✓ vitória do ITI · ★ vitória significativa · ✗ derrota

_Vitórias: h=1 vs B3 (pearson) ✓, h=1 vs B3 (spearman) ✓, h=2 vs B3 (pearson) ✓, h=2 vs B3 (spearman) ✓, h=4 vs B3 (pearson) ✓, h=4 vs B3 (spearman) ✓._

Tabela completa em `outputs/sabesp_r4_no_event/research/finbert_ptbr/saneamento_sabesp_strict_event/incremental_deltas.csv`.

#### Relação com a ação

Mesma lógica do R1: o ITI semanal é confrontado com log-returns futuros da `SBSP3.SA` (dados de mercado via yfinance). Métricas brutas em `outputs/sabesp_r4_no_event/research/finbert_ptbr/saneamento_sabesp_strict_event/market_metrics.csv`.

#### Leitura

- Leve melhora (+4,2 pp) sem significância — peso de evento pode adicionar ruído.

#### Artefatos

- Config: `configs/campaigns/sabesp_2026/experiments/r4_no_event.yaml`
- Saída: `outputs/sabesp_r4_no_event/`
- Research: `outputs/sabesp_r4_no_event/research/finbert_ptbr/saneamento_sabesp_strict_event/`

### Run R5 NO RELEVANCE — Sem relevance (r)

**Hipótese** — Relevance estabiliza pesos entre notícias.

**Mudança em relação ao R0** — `disabled_dimensions: [relevance]`.

#### Escopo dos dados

| Campo | Valor |
|-------|-------|
| Empresa(s) | Sabesp apenas |
| Período das notícias | nov/2023 – abr/2024 (evento de privatização) |
| Modo do corpus | **strict** — só artigos com entidade Sabesp confirmada |
| Filtro de entidade | sim — descartados registros sem match de empresa |
| Artigos | 465 |
| Dataset YAML | `saneamento_sabesp_strict_event` |

#### Índice (ITI)

| Campo | Valor |
|-------|-------|
| Cálculo do índice | **diário** — EWMA (Exponentially Weighted Moving Average) recalculado a cada dia |
| Frequência na validação | **semanal** — um ponto por semana (sexta-feira, W-FRI) |
| Coluna na validação | `iti_liquido_last` |
| α (alpha) | 0,85 |
| Equação | full sem `r` |
| Modelo de sentimento | `finbert_ptbr` |

#### Validação contra mercado

| Campo | Valor |
|-------|-------|
| Ticker | `SBSP3.SA` — preços reais via yfinance, cache em `data/market/prices.csv` |
| Retorno alvo | log-return (retorno logarítmico) acumulado nas próximas 1, 2 ou 4 **semanas** |
| Baselines comparados | B0–B3 — todos derivados das **nossas notícias**, não do mercado |
| Comparações por run | 24 (= 4 baselines × 2 métricas Pearson/Spearman × 3 horizontes) |
| Semanas com dados alinhados | ~24 (`overlap_days`) |

#### Resultado

- Win rate: **5/24 (20.8%)**
- Vitórias significativas: **0/24**
- Δ vs R0: +0.0 pp
- Conclusão automática: _iti_liquido (pearson, spearman): 5/24 vitórias (20.8%), 0 significativas (0.0%)_

#### ITI vs baselines (Pearson / Spearman)

Legenda: ✓ vitória do ITI · ★ vitória significativa · ✗ derrota

_Vitórias: h=1 vs B3 (pearson) ✓, h=1 vs B3 (spearman) ✓, h=2 vs B3 (spearman) ✓, h=4 vs B3 (pearson) ✓, h=4 vs B3 (spearman) ✓._

Tabela completa em `outputs/sabesp_r5_no_relevance/research/finbert_ptbr/saneamento_sabesp_strict_event/incremental_deltas.csv`.

#### Relação com a ação

Mesma lógica do R1: o ITI semanal é confrontado com log-returns futuros da `SBSP3.SA` (dados de mercado via yfinance). Métricas brutas em `outputs/sabesp_r5_no_relevance/research/finbert_ptbr/saneamento_sabesp_strict_event/market_metrics.csv`.

#### Leitura

- Idêntico ao R0 — sem efeito mensurável.

#### Artefatos

- Config: `configs/campaigns/sabesp_2026/experiments/r5_no_relevance.yaml`
- Saída: `outputs/sabesp_r5_no_relevance/`
- Research: `outputs/sabesp_r5_no_relevance/research/finbert_ptbr/saneamento_sabesp_strict_event/`

### Run R6 SIMPLIFIED — Equação simplificada (d·c)

**Hipótese** — Dimensões extras são ruído.

**Mudança em relação ao R0** — `equation_mode: simplified_dc` (`I_n = d·c`, `w_n = c`).

#### Escopo dos dados

| Campo | Valor |
|-------|-------|
| Empresa(s) | Sabesp apenas |
| Período das notícias | nov/2023 – abr/2024 (evento de privatização) |
| Modo do corpus | **strict** — só artigos com entidade Sabesp confirmada |
| Filtro de entidade | sim — descartados registros sem match de empresa |
| Artigos | 465 |
| Dataset YAML | `saneamento_sabesp_strict_event` |

#### Índice (ITI)

| Campo | Valor |
|-------|-------|
| Cálculo do índice | **diário** — EWMA (Exponentially Weighted Moving Average) recalculado a cada dia |
| Frequência na validação | **semanal** — um ponto por semana (sexta-feira, W-FRI) |
| Coluna na validação | `iti_liquido_last` |
| α (alpha) | 0,85 |
| Equação | simplified_dc |
| Modelo de sentimento | `finbert_ptbr` |

#### Validação contra mercado

| Campo | Valor |
|-------|-------|
| Ticker | `SBSP3.SA` — preços reais via yfinance, cache em `data/market/prices.csv` |
| Retorno alvo | log-return (retorno logarítmico) acumulado nas próximas 1, 2 ou 4 **semanas** |
| Baselines comparados | B0–B3 — todos derivados das **nossas notícias**, não do mercado |
| Comparações por run | 24 (= 4 baselines × 2 métricas Pearson/Spearman × 3 horizontes) |
| Semanas com dados alinhados | ~24 (`overlap_days`) |

#### Resultado

- Win rate: **5/24 (20.8%)**
- Vitórias significativas: **0/24**
- Δ vs R0: +0.0 pp
- Conclusão automática: _iti_liquido (pearson, spearman): 5/24 vitórias (20.8%), 0 significativas (0.0%)_

#### ITI vs baselines (Pearson / Spearman)

Legenda: ✓ vitória do ITI · ★ vitória significativa · ✗ derrota

_Vitórias: h=1 vs B3 (pearson) ✓, h=1 vs B3 (spearman) ✓, h=2 vs B3 (spearman) ✓, h=4 vs B3 (pearson) ✓, h=4 vs B3 (spearman) ✓._

Tabela completa em `outputs/sabesp_r6_simplified/research/finbert_ptbr/saneamento_sabesp_strict_event/incremental_deltas.csv`.

#### Relação com a ação

Mesma lógica do R1: o ITI semanal é confrontado com log-returns futuros da `SBSP3.SA` (dados de mercado via yfinance). Métricas brutas em `outputs/sabesp_r6_simplified/research/finbert_ptbr/saneamento_sabesp_strict_event/market_metrics.csv`.

#### Leitura

- Simplificar a equação não melhora nem piora — gargalo não está nas dimensões extras.

#### Artefatos

- Config: `configs/campaigns/sabesp_2026/experiments/r6_simplified.yaml`
- Saída: `outputs/sabesp_r6_simplified/`
- Research: `outputs/sabesp_r6_simplified/research/finbert_ptbr/saneamento_sabesp_strict_event/`

### Run R7 HORIZON FIXED — Horizonte fixo

**Hipótese** — Modulação de α por horizonte inferido (h) confunde a validação.

**Mudança em relação ao R0** — `horizon.mode: fixed`.

#### Escopo dos dados

| Campo | Valor |
|-------|-------|
| Empresa(s) | Sabesp apenas |
| Período das notícias | nov/2023 – abr/2024 (evento de privatização) |
| Modo do corpus | **strict** — só artigos com entidade Sabesp confirmada |
| Filtro de entidade | sim — descartados registros sem match de empresa |
| Artigos | 465 |
| Dataset YAML | `saneamento_sabesp_strict_event` |

#### Índice (ITI)

| Campo | Valor |
|-------|-------|
| Cálculo do índice | **diário** — EWMA (Exponentially Weighted Moving Average) recalculado a cada dia |
| Frequência na validação | **semanal** — um ponto por semana (sexta-feira, W-FRI) |
| Coluna na validação | `iti_liquido_last` |
| α (alpha) | 0,85 |
| Equação | full |
| Modelo de sentimento | `finbert_ptbr` |

#### Validação contra mercado

| Campo | Valor |
|-------|-------|
| Ticker | `SBSP3.SA` — preços reais via yfinance, cache em `data/market/prices.csv` |
| Retorno alvo | log-return (retorno logarítmico) acumulado nas próximas 1, 2 ou 4 **semanas** |
| Baselines comparados | B0–B3 — todos derivados das **nossas notícias**, não do mercado |
| Comparações por run | 24 (= 4 baselines × 2 métricas Pearson/Spearman × 3 horizontes) |
| Semanas com dados alinhados | ~24 (`overlap_days`) |

#### Resultado

- Win rate: **6/24 (25.0%)**
- Vitórias significativas: **0/24**
- Δ vs R0: +4.2 pp
- Conclusão automática: _iti_liquido (pearson, spearman): 6/24 vitórias (25.0%), 0 significativas (0.0%)_

#### ITI vs baselines (Pearson / Spearman)

Legenda: ✓ vitória do ITI · ★ vitória significativa · ✗ derrota

_Vitórias: h=1 vs B3 (pearson) ✓, h=1 vs B3 (spearman) ✓, h=2 vs B3 (pearson) ✓, h=2 vs B3 (spearman) ✓, h=4 vs B3 (pearson) ✓, h=4 vs B3 (spearman) ✓._

Tabela completa em `outputs/sabesp_r7_horizon_fixed/research/finbert_ptbr/saneamento_sabesp_strict_event/incremental_deltas.csv`.

#### Relação com a ação

Mesma lógica do R1: o ITI semanal é confrontado com log-returns futuros da `SBSP3.SA` (dados de mercado via yfinance). Métricas brutas em `outputs/sabesp_r7_horizon_fixed/research/finbert_ptbr/saneamento_sabesp_strict_event/market_metrics.csv`.

#### Leitura

- Leve ganho (+4,2 pp) — modulação por h não é o principal problema.

#### Artefatos

- Config: `configs/campaigns/sabesp_2026/experiments/r7_horizon_fixed.yaml`
- Saída: `outputs/sabesp_r7_horizon_fixed/`
- Research: `outputs/sabesp_r7_horizon_fixed/research/finbert_ptbr/saneamento_sabesp_strict_event/`

### Run R8 WEEKLY MEAN — ITI = média semanal

**Hipótese** — Média dos valores diários da semana é mais estável que o último dia.

**Mudança em relação ao R0** — `iti_weekly_column: iti_liquido_mean` (em vez de `iti_liquido_last`).

#### Escopo dos dados

| Campo | Valor |
|-------|-------|
| Empresa(s) | Sabesp apenas |
| Período das notícias | nov/2023 – abr/2024 (evento de privatização) |
| Modo do corpus | **strict** — só artigos com entidade Sabesp confirmada |
| Filtro de entidade | sim — descartados registros sem match de empresa |
| Artigos | 465 |
| Dataset YAML | `saneamento_sabesp_strict_event` |

#### Índice (ITI)

| Campo | Valor |
|-------|-------|
| Cálculo do índice | **diário** — EWMA (Exponentially Weighted Moving Average) recalculado a cada dia |
| Frequência na validação | **semanal** — um ponto por semana (sexta-feira, W-FRI) |
| Coluna na validação | `iti_liquido_mean` |
| α (alpha) | 0,85 |
| Equação | full |
| Modelo de sentimento | `finbert_ptbr` |

#### Validação contra mercado

| Campo | Valor |
|-------|-------|
| Ticker | `SBSP3.SA` — preços reais via yfinance, cache em `data/market/prices.csv` |
| Retorno alvo | log-return (retorno logarítmico) acumulado nas próximas 1, 2 ou 4 **semanas** |
| Baselines comparados | B0–B3 — todos derivados das **nossas notícias**, não do mercado |
| Comparações por run | 24 (= 4 baselines × 2 métricas Pearson/Spearman × 3 horizontes) |
| Semanas com dados alinhados | ~24 (`overlap_days`) |

#### Resultado

- Win rate: **1/24 (4.2%)**
- Vitórias significativas: **0/24**
- Δ vs R0: -16.7 pp
- Conclusão automática: _iti_liquido (pearson, spearman): 1/24 vitórias (4.2%), 0 significativas (0.0%)_

#### ITI vs baselines (Pearson / Spearman)

Legenda: ✓ vitória do ITI · ★ vitória significativa · ✗ derrota

| Baseline | 1 sem (P / S) | 2 sem (P / S) | 4 sem (P / S) |
|----------|---------------|---------------|---------------|
| **B0** | ✗ / ✗ | ✗ / ✗ | ✗ / ✗ |
| **B1** | ✗ / ✗ | ✗ / ✗ | ✗ / ✗ |
| **B2** | ✗ / ✗ | ✗ / ✗ | ✗ / ✗ |
| **B3** | ✗ / ✓ | ✗ / ✗ | ✗ / ✗ |

#### Relação com a ação

Mesma lógica do R1: o ITI semanal é confrontado com log-returns futuros da `SBSP3.SA` (dados de mercado via yfinance). Métricas brutas em `outputs/sabesp_r8_weekly_mean/research/finbert_ptbr/saneamento_sabesp_strict_event/market_metrics.csv`.

#### Leitura

- Pior que R0 (4,2%): agregar por média semanal destrói o estado EWMA do fim da semana.
- Confirma `iti_liquido_last` como padrão para validação semanal.

#### Artefatos

- Config: `configs/campaigns/sabesp_2026/experiments/r8_weekly_mean.yaml`
- Saída: `outputs/sabesp_r8_weekly_mean/`
- Research: `outputs/sabesp_r8_weekly_mean/research/finbert_ptbr/saneamento_sabesp_strict_event/`

### Run R9 ENSEMBLE — Modelo alternativo PT-BR

**Hipótese** — Outro BERT muda o sinal de sentimento.

**Mudança em relação ao R0** — Modelo `pt_br_financial_sentiment_analysis` (demais parâmetros como R0).

#### Escopo dos dados

| Campo | Valor |
|-------|-------|
| Empresa(s) | Sabesp apenas |
| Período das notícias | nov/2023 – abr/2024 (evento de privatização) |
| Modo do corpus | **strict** — só artigos com entidade Sabesp confirmada |
| Filtro de entidade | sim — descartados registros sem match de empresa |
| Artigos | 465 |
| Dataset YAML | `saneamento_sabesp_strict_event` |

#### Índice (ITI)

| Campo | Valor |
|-------|-------|
| Cálculo do índice | **diário** — EWMA (Exponentially Weighted Moving Average) recalculado a cada dia |
| Frequência na validação | **semanal** — um ponto por semana (sexta-feira, W-FRI) |
| Coluna na validação | `iti_liquido_last` |
| α (alpha) | 0,85 |
| Equação | full |
| Modelo de sentimento | `pt_br_financial_sentiment_analysis` |

#### Validação contra mercado

| Campo | Valor |
|-------|-------|
| Ticker | `SBSP3.SA` — preços reais via yfinance, cache em `data/market/prices.csv` |
| Retorno alvo | log-return (retorno logarítmico) acumulado nas próximas 1, 2 ou 4 **semanas** |
| Baselines comparados | B0–B3 — todos derivados das **nossas notícias**, não do mercado |
| Comparações por run | 24 (= 4 baselines × 2 métricas Pearson/Spearman × 3 horizontes) |
| Semanas com dados alinhados | ~24 (`overlap_days`) |

#### Resultado

- Win rate: **6/24 (25.0%)**
- Vitórias significativas: **0/24**
- Δ vs R0: +4.2 pp
- Conclusão automática: _iti_liquido (pearson, spearman): 6/24 vitórias (25.0%), 0 significativas (0.0%)_

#### ITI vs baselines (Pearson / Spearman)

Legenda: ✓ vitória do ITI · ★ vitória significativa · ✗ derrota

_Vitórias: h=1 vs B3 (pearson) ✓, h=1 vs B3 (spearman) ✓, h=2 vs B3 (pearson) ✓, h=2 vs B3 (spearman) ✓, h=4 vs B3 (pearson) ✓, h=4 vs B3 (spearman) ✓._

Tabela completa em `outputs/sabesp_r9_ensemble/research/pt_br_financial_sentiment_analysis/saneamento_sabesp_strict_event/incremental_deltas.csv`.

#### Relação com a ação

Mesma lógica do R1: o ITI semanal é confrontado com log-returns futuros da `SBSP3.SA` (dados de mercado via yfinance). Métricas brutas em `outputs/sabesp_r9_ensemble/research/pt_br_financial_sentiment_analysis/saneamento_sabesp_strict_event/market_metrics.csv`.

#### Leitura

- 25,0% (+4,2 pp vs R0) — trocar modelo não resolve o problema estrutural.

#### Artefatos

- Config: `configs/campaigns/sabesp_2026/experiments/r9_ensemble.yaml`
- Saída: `outputs/sabesp_r9_ensemble/`
- Research: `outputs/sabesp_r9_ensemble/research/pt_br_financial_sentiment_analysis/saneamento_sabesp_strict_event/`

---

### Síntese do Marco 1

**O que funcionou**

1. Correção metodológica — strict + semanal + filtro Sabesp elevou win rate de ~12,5% (broad) para 20,8% (R0).
2. **α = 0,70** (R1) — único eixo com ganho robusto; win rate 41,7% com 2 vitórias significativas.
3. **`iti_liquido_last`** — último dia útil da semana vence média semanal (R8).
4. Infraestrutura de campanha — manifest, configs por run, `scripts/campaigns/sabesp_2026.sh`.

**O que não funcionou**

1. ITI ainda perde para baselines na maioria das comparações (exceto R1).
2. Ablações de dimensões (R3–R6) quase não movem o resultado.
3. α alto (0,95) degrada fortemente o sinal (R2).
4. Trocar modelo BERT (R9) não resolve o problema estrutural.

**Limitações**

- Evento único (privatização Sabesp); ~24 semanas de overlap; correlação ≠ causalidade.
- Rótulos manuais (100 notícias) — ver [Marco 3](#marco-3--qualidade-do-sentimento-trilha-b).

### Decisões tomadas

| Decisão | Motivo |
|---------|--------|
| Avançar coleta pré-evento (mai–out/2022) | R1 atingiu 41,7% ≥ 40% (gate atendido); **executado no Marco 2** |
| Usar α = 0,70 como default na próxima rodada | Melhor resultado + significância |
| Manter `iti_liquido_last` | R8 provou que média semanal é pior |
| Não investir em ablações de dimensões por ora | R3–R6 não moveram o resultado |

### Artefatos do marco

| Artefato | Caminho |
|----------|---------|
| Manifest | `outputs/campaigns/sabesp_2026/manifest.json` |
| Análise automática | `outputs/campaigns/sabesp_2026/comparative_analysis.md` |
| Corpus strict Sabesp | `data/saneamento_corpus/noticias_strict_sabesp.csv` |
| Research semanal | `configs/campaigns/sabesp_2026/research_weekly.yaml` |
| Script campanha | `scripts/campaigns/sabesp_2026.sh` |

---

## Marco 2 — Amostra PT expandida (Sabesp)

**Data:** 31/08/2026  
**Status:** concluído (coleta + corpus + replay GPU)

**Objetivo:** aumentar overlap semanal (meta **≥ 40 semanas**) incorporando notícias **mai–out/2022** (pré-evento) à janela do evento (nov/2023–abr/2024), sem misturar trilhas EN nem trocar preços B3.

### Protocolo

| Etapa | Comando |
|-------|---------|
| Coleta pré-evento | `./scripts/campaigns/sabesp_marco2.sh scrape` |
| Coleta lacuna 2023 (depois do Marco 2) | `./scripts/campaigns/sabesp_marco2.sh scrape-2023` |
| Corpus strict expandido | `./scripts/campaigns/sabesp_marco2.sh corpus` |
| Replay R0 + R1 | `./scripts/campaigns/sabesp_marco2.sh replay` |
| Sanity check janela evento | `./scripts/campaigns/sabesp_marco2.sh replay-event` |
| Análise por subperíodo | `./scripts/campaigns/sabesp_marco2.sh analyze-periods` |

### Escopo dos dados

| Campo | Valor |
|-------|-------|
| Empresa | Sabesp |
| Período | 2022-05-01 — 2024-04-30 |
| Artigos no corpus filtrado | **1.055** no replay ITI (256 em 2022; lacuna jan–abr/2023). Depois: **1.254** — [atualização de corpus](#atualização-de-corpus-31082026-sem-replay-iti) |
| Dataset YAML | `saneamento_sabesp_strict_expanded` |
| Corpus | `data/saneamento_corpus/noticias_strict_sabesp.csv` |
| Research | `configs/campaigns/sabesp_2026/research_weekly.yaml` |

### Resumo comparativo

| Run | run_id | α | Vitórias | Win rate | Δ vs R0 | Significativas |
|-----|--------|---|----------|----------|---------|----------------|
| R0 | `sabesp_marco2_r0_baseline` | 0,85 | 0/24 | 0,0% | — | 0 |
| R1 | `sabesp_marco2_r1_alpha070` | 0,70 | 5/24 | 20,8% | +20,8 pp | 0 |

Métrica: `iti_liquido` × baselines B0–B3, Pearson + Spearman, horizontes 1/2/4 semanas (24 comparações).

### Overlap

| Campo | Valor |
|-------|-------|
| Semanas alinhadas (ITI + baselines + preço) | **76** (`aligned_panel.csv`) |
| Meta do marco | ≥ 40 semanas — **atingida** |
| Marco 1 (janela evento) | ~24 semanas |

### Marco 1 vs Marco 2 (janela expandida)

| Run | Marco 1 (nov/23–abr/24, 465 artigos) | Marco 2 expandido (1.055 artigos) | Δ win rate |
|-----|--------------------------------------|-----------------------------------|------------|
| R0 | 20,8% | 0,0% | −20,8 pp |
| R1 | **41,7%** (2 sig.) | 20,8% | −20,9 pp |

Expandir a janela **não reforçou** o sinal ITI×mercado; α=0,70 continua melhor que 0,85 dentro do Marco 2, mas abaixo do Marco 1.

### Leitura

- O pré-evento (mai–out/2022) dilui o ITI semanal: notícias fora do choque de privatização não se alinham ao retorno da `SBSP3.SA` da mesma forma que o evento nov/2023–abr/2024.
- A janela **interpretável** para a tese permanece o evento de privatização; ver [sanity check janela evento](#sanity-check-janela-evento) e [análise por subperíodo](#análise-por-subperíodo).
- O gate de coleta pré-evento (Marco 1) foi cumprido metodologicamente; o resultado científico é que **mais dados ≠ melhor correlação** neste desenho.

### Decisões do Marco 2

| Decisão | Motivo |
|---------|--------|
| Manter α = 0,70 como hipótese preferida | Melhor run dentro do corpus expandido (5/24 vs 0/24) |
| Não assumir 41,7% do Marco 1 no corpus expandido | Win rate caiu para 20,8% |
| Priorizar validação de sentimento (Marco 3) | Separar qualidade do classificador de sinal fraco ITI×mercado |
| Documentar subperíodos 2022 vs evento | Explicar diluição sem reescrever histórico do Marco 1 |

### Sanity check janela evento

Replay R0+R1 só no dataset `saneamento_sabesp_strict_event` (nov/2023–abr/2024, mesmo CSV) para verificar se o corpus atualizado reproduz o Marco 1.

| Run | Marco 1 | Marco 2 event replay | Δ |
|-----|---------|----------------------|---|
| R0 | 20,8% | **20,8%** (`sabesp_marco2_event_r0_baseline`) | 0 pp |
| R1 | 41,7% (2 sig.) | **41,7%** (2 sig., `sabesp_marco2_event_r1_alpha070`) | 0 pp |

O corpus evento no CSV expandido ainda filtra **465 artigos** (nov/2023–abr/2024) — mesma contagem do Marco 1. A divergência aparece **somente** quando o ITI incorpora 2022 (`saneamento_sabesp_strict_expanded`).

### Análise por subperíodo

Correlação exploratória ITI×retorno futuro (h=1 semana) no painel do R1 expandido gap2023 (`analyze-periods`, três buckets):

| Subperíodo | Semanas | Pearson | Spearman |
|------------|---------|---------|----------|
| `pre_evento_2022` | 25 | −0,148 | −0,110 |
| `interregno_2023q1` | 15 | +0,172 | +0,304 |
| `evento_nov23_abr24` | 50 | −0,030 | +0,054 |

Relatório: `outputs/campaigns/sabesp_marco2/period_breakdown_gap2023.md`. O bucket antigo `evento_2023_2024` misturava a lacuna 2023 com o evento — leitura corrigida acima.

### Artefatos

| Artefato | Caminho |
|----------|---------|
| Script Marco 2 | `scripts/campaigns/sabesp_marco2.sh` |
| Dataset expandido | `configs/campaigns/datasets.yaml` → `saneamento_sabesp_strict_expanded` |
| Saída R0 | `outputs/sabesp_marco2_r0_baseline/` |
| Saída R1 | `outputs/sabesp_marco2_r1_alpha070/` |
| Research | `outputs/sabesp_marco2_r*/research/finbert_ptbr/saneamento_sabesp_strict_expanded/` |

### Atualização de corpus (31/08/2026, sem replay ITI)

Coleta histórica da lacuna **jan–abr/2023** (`./scripts/campaigns/sabesp_marco2.sh scrape-2023`) + `corpus` (build-strict + filtro Sabesp mai/22–abr/24). **Não** houve replay R0–R9: os números do Marco 2 acima continuam válidos para o CSV de 1.055 artigos.

| Campo | Antes (Marco 2 / ITI) | Depois da coleta 2023 |
|-------|----------------------|------------------------|
| Strict Sabesp (`noticias_strict_sabesp.csv`) | 1.055 | **1.254** |
| 2022 (mai–out) | 256 | **256** (janela intacta) |
| jan–abr/2023 | 0 (lacuna) | **199** (jan 50, fev 56, mar 44, abr 49) |
| Duplicatas de URL | — | 0 |
| Pendentes | 1.026 | 1.248 |
| Falsos PENDENTE com Sabesp/SBSP3 no título ou corpo | — | **0/1.248** |

Fontes na janela jan–abr/2023 (Sabesp strict): Money Times 60, InfoMoney 52, G1 44, Valor 32, Exame 11. Portais ativos inalterados: Valor, InfoMoney, Money Times, G1, Exame.

**Pendentes.** Amostra confirma PENDENTE = saneamento setorial sem empresa B3 no texto (PPPs, Enel, Veolia, censo, tarifa social genérica). Não há ganho claro em endurecer `match_entity` além do alias já existente da razão social da Sabesp. Não rotular os 1.248 à mão.

**Estadão / Folha.** Permanecem `enabled: false` em `configs/scrapers.yaml`. A busca Playwright do Estadão devolve páginas de marketing; a da Folha exige login/paywall. O `SiteScraper` atual cobre o padrão, mas sem smoke live confiável — sem adapter novo.

**Controles PT (inferência, `enabled: false`).** `bertweet_pt_sentiment` e `bertimbau_sentiment` entram no YAML para a próxima bateria; fetch/dry-run em [documentacao.md §3.3.1](documentacao.md#331-higiene-do-pipeline-estado-atual). Bateria κ executada — ver [síntese Trilha A](sintese_trilha_a.md#4-qualidade-do-classificador-marco-3--bateria-pt).

### Fechamento Trilha A (gap 2023 + κ PT)

Runs novas no corpus **1.254** (`sabesp_gap2023_*`) — runs Marco 2 (`sabesp_marco2_*`) **intactas**.

| Pergunta | Resposta |
|----------|----------|
| Lacuna 2023 muda Marco 2 expandido? | R1 sobe **20,8% → 33,3%**; ainda **0 sig.** |
| Sanity evento reproduz Marco 1? | **Sim** — R1 **41,7%**, **2 sig.** (`sabesp_gap2023_event_r1_alpha070`) |
| Janela na tese | **Evento** = principal; **expandido** = robustez/limitação |
| Controles PT passam gate (70% ou κ≥0,40)? | **Não** — ITI condicional omitido |

Comandos: `./scripts/campaigns/sabesp_marco2.sh replay-gap2023`, `replay-event-gap2023`, `analyze-periods`; `./scripts/campaigns/classifier_eval_pt.sh run`.

Relatórios: `outputs/campaigns/sabesp_marco2/gap2023_comparison.md`, `outputs/campaigns/classifier_eval_pt/comparative_report.md`, [docs/sintese_trilha_a.md](sintese_trilha_a.md).

---

## Marco 3 — Qualidade do sentimento (Trilha B)

**Data:** 31/08/2026  
**Status:** concluído (100 rótulos manuais + compare)

### Rótulos manuais PT

| Etapa | Comando |
|-------|---------|
| Amostra (já gerada) | `./scripts/campaigns/sabesp_2026.sh manual-sample` |
| Preencher CSV | coluna `rotulo_manual` (POS / NEG / NEU) em `data/saneamento_corpus/rotulos_manual_100.csv` |
| Comparar com FinBERT | `./scripts/campaigns/sabesp_2026.sh manual-compare` |

Predictions usadas: `outputs/sabesp_marco2_r0_baseline/.../predictions.csv` (fallback se Marco 1 R0 ausente).

### Distribuição da amostra

| Fonte | POS | NEU | NEG |
|-------|-----|-----|-----|
| FinBERT (estratificação) | 19 | 43 | 38 |
| Rótulo manual | 19 | 69 | 12 |

### Resultado concordância manual

| Métrica | Valor | Gate (auditoria) |
|---------|-------|------------------|
| Amostra rotulada | 100 | — |
| Acurácia | **48,0%** | ≥ 70% — **não atingido** |
| Cohen's kappa | **0,163** | — |

Matriz de confusão (manual × FinBERT):

| manual \\ finbert | NEG | NEU | POS |
|-------------------|-----|-----|-----|
| NEG | 11 | 1 | 0 |
| NEU | 23 | 32 | 14 |
| POS | 4 | 10 | 5 |

Relatório completo: `outputs/campaigns/sabesp_2026/manual_label_report.md`.

### Leitura

- FinBERT classifica como **NEG** muitas menções neutras (roundups de ibovespa, agendas de mercado) — principal fonte de erro.
- Notícias claramente positivas (aprovação Alesp, analistas otimistas) frequentemente saem como **NEU**.
- Acurácia abaixo de 70% indica **limitação do classificador** como componente do ITI; não invalida sozinha o sinal fraco ITI×mercado, mas reforça cautela na interpretação.

### Avaliação EN opcional (sem ITI)

| Dataset | Uso | Comando |
|---------|-----|---------|
| PhraseBank | Rótulo humano EN | `./scripts/campaigns/classifier_eval_en.sh phrasebank` |
| NOSIBLE (amostra) | Rótulo LLM EN | `./scripts/campaigns/classifier_eval_en.sh nosible` |

**Não** fine-tunar FinBERT-PT no NOSIBLE. **Não** alimentar research semanal com esses datasets.

---

## Síntese Marcos 1–3

### Linha do tempo

1. **Marco 1** — protocolo corrigido (strict, semanal, Sabesp); R1 com 41,7% win rate e 2 vitórias significativas na janela do evento.
2. **Marco 2** — gate pré-evento executado; overlap 76 semanas; **sinal enfraquece** no corpus expandido original (R1: 20,8%). Com lacuna 2023 preenchida (gap2023), R1 expandido sobe para **33,3%** (8/24), ainda **0 sig.**
3. **Marco 3** — FinBERT vs humano: 48% acurácia, κ=0,163; classificador não atinge gate de 70%. Bateria PT (BERTweet/BERTimbau) também falha o gate.

### O que funcionou

- Infraestrutura reprodutível (configs/campaigns, scripts, research semanal).
- α=0,70 consistentemente melhor que 0,85 (Marcos 1 e 2).
- Sanity check `replay-event-gap2023` **reproduz** Marco 1 na janela evento (41,7% / 2 sig. no R1).

### O que não funcionou

- ITI×mercado no corpus **expandido** (R1: 20,8% Marco 2 → 33,3% gap2023; nenhuma sig.).
- Concordância FinBERT×humano (48% < 70%; F1 macro 0,42).
- Pré-evento 2022 correlaciona negativamente com retorno futuro no painel expandido.
- Filtro de roundups no evento (`sabesp_event_r1_filtered`): win rate cai para **25,0%**, 0 sig.

### Narrativa para a tese

O gate metodológico do Marco 1 autorizou a coleta pré-evento, mas o **re-teste com janela expandida não reforçou** a hipótese ITI×mercado (melhora parcial com lacuna 2023, sem significância). A privatização (nov/2023–abr/2024) permanece a janela economicamente interpretável; o ruído de 2022 dilui o índice semanal. A baixa concordância manual e a run filtrada (25%) sugerem que o teto ~41,7% reflete mais **relação notícia–preço no evento** do que apenas ruído de roundups ou erro do classificador.

### Próximos passos opcionais

- **Marco 4** — `./scripts/campaigns/fnspid_pilot.sh run` (réplica US, CC-BY-NC).
- **Marco 5** — `./scripts/campaigns/finmarba_diag.sh run` (sentimento × mercado D+1).
- Não bloqueiam conclusão da Trilha A Sabesp.

---

## Marco 4 — Piloto FNSPID (Trilha C, opcional)

**Status:** configs e script prontos; execução opcional (licença **CC-BY-NC**).

Replica o protocolo ITI (α=0,70, `iti_liquido_last`, B0–B3) em **painel US separado** — não mistura com Sabesp.

| Etapa | Comando |
|-------|---------|
| Fetch + run | `./scripts/campaigns/fnspid_pilot.sh run` |

| Campo | Valor |
|-------|-------|
| Dataset | `fnspid_pilot` (5 tickers, ~2000 linhas) |
| Modelo | `finbert_en` |
| Preços | `configs/campaigns/fnspid_pilot/market.yaml` |
| Research | `configs/campaigns/fnspid_pilot/research_weekly.yaml` |
| run_id | `fnspid_r0_pilot` |

### Resultado

_A preencher após execução do piloto._

---

## Marco 5 — Diagnóstico FinMarBa (Trilha C, opcional)

**Status:** script pronto; execução opcional.

Mede concordância **FinBERT × rótulo de mercado** (retorno D+1). O rótulo FinMarBa **não** entra no ITI Sabesp nem no research B3 — evita vazamento de alvo.

| Etapa | Comando |
|-------|---------|
| Inferência + relatório | `./scripts/campaigns/finmarba_diag.sh run` |

| Campo | Valor |
|-------|-------|
| Dataset | `finmarba_headlines_en` |
| Experimento | `configs/campaigns/trilha_b/classifier_diag.yaml` (`temporal_index.enabled: false`) |
| Relatório | `outputs/campaigns/finmarba_diag/concordance_report.md` |

**Leitura didática:** discordância não prova que o FinBERT está “errado” — prova que sentimento textual ≠ reação de mercado no dia seguinte.

### Resultado

_A preencher após execução._

---

## Como atualizar este documento

1. Ao concluir uma campanha, adicione um novo **Marco** no final (antes desta seção).
2. Para cada run, copie o [template](#template-para-novas-runs) e preencha com dados de `outputs/campaigns/{campanha}/manifest.json` e `incremental_deltas.csv`.
3. Atualize a tabela resumo do marco e a síntese (o que funcionou / não funcionou / decisões).
4. Se o protocolo mudar (frequência, filtros, equação), atualize também [documentacao.md](documentacao.md) nas seções §4–§6.
5. Rode `./scripts/campaigns/sabesp_2026.sh` (ou equivalente) e confira no dashboard (páginas **Experimentos** e **Research**) antes de commitar.
6. Mantenha números consistentes com o manifest — não editar `outputs/` manualmente.
