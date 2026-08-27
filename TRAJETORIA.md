# Trajetória experimental — Financial Sentiment Lab

Registro versionado da evolução da pesquisa: decisões tomadas, escopo de cada rodada, resultados run a run e o que aprendemos. Este documento é a **narrativa** do projeto; conceitos e fórmulas estão em [DOCUMENTACAO.md](DOCUMENTACAO.md) e comandos em [README.md](README.md).

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
| **B0–B3** | Quatro baselines internos — ver [DOCUMENTACAO.md §1.5](DOCUMENTACAO.md#15-conceitos-em-linguagem-acessível) |

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

- Lacunas metodológicas documentadas em [docs/metodologia_auditoria.md](docs/metodologia_auditoria.md) motivaram a campanha corrigida (Marco 1).
- Win rate baixo (~0–12%) refletia tanto sinal fraco quanto **comparação inválida** (frequências misturadas).

### Artefatos

- Saída: `outputs/saneamento_pt_20260824/`

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

> As 24 comparações por run resultam de 4 baselines × 2 métricas de conclusão (Pearson, Spearman) × 3 horizontes semanais. Detalhe em [DOCUMENTACAO.md §5](DOCUMENTACAO.md#50-modos-diário-e-semanal).

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

- Config: `configs/experiments/sabesp/r0_baseline.yaml`
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

- Config: `configs/experiments/sabesp/r1_alpha070.yaml`
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

- Config: `configs/experiments/sabesp/r2_alpha095.yaml`
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

- Config: `configs/experiments/sabesp/r3_no_novelty.yaml`
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

- Config: `configs/experiments/sabesp/r4_no_event.yaml`
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

- Config: `configs/experiments/sabesp/r5_no_relevance.yaml`
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

- Config: `configs/experiments/sabesp/r6_simplified.yaml`
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

- Config: `configs/experiments/sabesp/r7_horizon_fixed.yaml`
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

- Config: `configs/experiments/sabesp/r8_weekly_mean.yaml`
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

- Config: `configs/experiments/sabesp/r9_ensemble.yaml`
- Saída: `outputs/sabesp_r9_ensemble/`
- Research: `outputs/sabesp_r9_ensemble/research/pt_br_financial_sentiment_analysis/saneamento_sabesp_strict_event/`

---

### Síntese do Marco 1

**O que funcionou**

1. Correção metodológica — strict + semanal + filtro Sabesp elevou win rate de ~12,5% (broad) para 20,8% (R0).
2. **α = 0,70** (R1) — único eixo com ganho robusto; win rate 41,7% com 2 vitórias significativas.
3. **`iti_liquido_last`** — último dia útil da semana vence média semanal (R8).
4. Infraestrutura de campanha — manifest, configs por run, `scripts/run_sabesp_campaign.sh`.

**O que não funcionou**

1. ITI ainda perde para baselines na maioria das comparações (exceto R1).
2. Ablações de dimensões (R3–R6) quase não movem o resultado.
3. α alto (0,95) degrada fortemente o sinal (R2).
4. Trocar modelo BERT (R9) não resolve o problema estrutural.

**Limitações**

- Evento único (privatização Sabesp); ~24 semanas de overlap; correlação ≠ causalidade.
- Rótulos manuais (100 notícias) ainda pendentes.

### Decisões tomadas

| Decisão | Motivo |
|---------|--------|
| Avançar coleta pré-evento (mai–out/2022) | R1 atingiu 41,7% ≥ 40% (gate atendido) |
| Usar α = 0,70 como default na próxima rodada | Melhor resultado + significância |
| Manter `iti_liquido_last` | R8 provou que média semanal é pior |
| Não investir em ablações de dimensões por ora | R3–R6 não moveram o resultado |

### Artefatos do marco

| Artefato | Caminho |
|----------|---------|
| Manifest | `outputs/campaigns/sabesp_2026/manifest.json` |
| Análise automática | `outputs/campaigns/sabesp_2026/comparative_analysis.md` |
| Corpus strict Sabesp | `data/saneamento_corpus/noticias_strict_sabesp.csv` |
| Research semanal | `configs/research_weekly_sabesp.yaml` |
| Script campanha | `scripts/run_sabesp_campaign.sh` |

---

## Como atualizar este documento

1. Ao concluir uma campanha, adicione um novo **Marco** no final (antes desta seção).
2. Para cada run, copie o [template](#template-para-novas-runs) e preencha com dados de `outputs/campaigns/{campanha}/manifest.json` e `incremental_deltas.csv`.
3. Atualize a tabela resumo do marco e a síntese (o que funcionou / não funcionou / decisões).
4. Rode `./scripts/run_sabesp_campaign.sh` (ou equivalente) e confira no dashboard (páginas **Experimentos** e **Research**) antes de commitar.
5. Mantenha números consistentes com o manifest — não editar `outputs/` manualmente.
