# 05 Validacao Research

## 5. Validação research — métricas e retornos

Config padrão: `configs/research.yaml`. Campanha Sabesp semanal: `configs/campaigns/sabesp_2026/research_weekly.yaml`.

### 5.0 Modos diário e semanal

**Correções que habilitam o modo semanal.** A rodada broad (Marco 0) misturava frequências: o ITI semanal era gerado mas o research lia só `iti_daily.csv` com baselines diários. A auditoria metodológica (detalhe em [trajetoria F1](../research_trail/part-03-phases.md#f1--auditoria-e-protocolo-comparável)) mapeou seis lacunas; as correções no código incluem `index_frequency: weekly`, alinhamento em `io/weekly_align.py`, `resample_baselines_weekly`, `companies_filter`, dataset strict por evento e horizontes em semanas.

O módulo research suporta dois modos de alinhamento, selecionados por `index_frequency` no YAML de research:

| Modo | Config | `index_frequency` | Horizontes | Coluna ITI | Alinhamento |
| --- | --- | --- | --- | --- | --- |
| **Diário** (padrão) | `configs/research.yaml` | `daily` (implícito) | 1, 5, 21 **dias** | `iti_liquido` diário | `io/align.py` |
| **Semanal** (campanha Sabesp) | `configs/campaigns/sabesp_2026/research_weekly.yaml` | `weekly` | 1, 2, 4 **semanas** | `iti_liquido_last` | `io/weekly_align.py` |

No modo semanal:

- ITI e baselines são agregados para W-FRI (sexta-feira).
- Retornos de mercado são a soma dos log-returns diários da semana.
- Retornos futuros somam as semanas seguintes (horizonte em semanas).
- Filtro `companies_filter: [Sabesp]` restringe o painel à empresa do evento.

As **24 comparações** por run no modo semanal vêm de 4 baselines × 2 métricas de conclusão (Pearson, Spearman) × 3 horizontes. Resultados e interpretação: [research_trail](../research_trail/README.md).

### 5.1 Retorno alvo

Modo default `return_mode: cumulative`. Para horizonte \(h\), retorno futuro a partir do dia \(t\):

- **log_return:** soma dos log-retornos em \([t+1, t+h]\)
- **simple_return:** \(\prod_{i=1}^{h}(1+r_i) - 1\)

Colunas geradas: `future_log_return_1`, `future_log_return_5`, `future_log_return_21`.

### 5.2 Métricas predictor × retorno

| Métrica | Uso | Observação |
| --- | --- | --- |
| Pearson | correlação linear | p paramétrico + bootstrap |
| Spearman | correlação de ranks | idem |
| R² | `sklearn.r2_score(y, x)` | omitido se \(n < 30\) |
| MSE | erro quadrático médio | predictor vs retorno |

Para `iti_risco`, o alvo é \(|\text{retorno}|\) (`abs_return_predictors`).

### 5.3 Delta incremental ITI vs baseline

Para cada horizonte e baseline:

\[
\Delta = \text{metric}_{ITI} - \text{metric}_{baseline}
\]

(MSE usa \(\Delta = \text{MSE}_{baseline} - \text{MSE}_{ITI}\) — redução de erro favorece ITI.)

**Bootstrap em bloco** (`block_size=5` no research diário; `block_size=2` na campanha Sabesp semanal; `n_bootstrap=500`): reamostra índices contíguos, recalcula \(\Delta\), estima IC 95% e p-value. A conclusão CLI usa **apenas Pearson e Spearman** (`conclusion_metrics`).

### 5.4 Alinhamento semanal (`io/weekly_align.py`)

Algoritmo usado quando `index_frequency: weekly`:

1. **`_week_end_key`** — converte datas para fim de semana W-FRI.
2. **ITI e baselines** — colapsa painel diário: `groupby(company, sector, week_end).last()` → valor de sexta.
3. **`_weekly_market_returns`** — por ticker, soma `log_return` (ou produto de simple returns) na semana.
4. **`_add_future_weekly_returns`** — para horizonte h em semanas, soma retornos das h semanas seguintes → `future_log_return_{h}`.
5. **Merge** — ITI + baselines + mercado por `(company, period_end)`.
6. **`add_b3_column`** — B3 = `impacto_dia` numérico (sem memória EWMA).

Coluna ITI usada no research: `iti_weekly_column` (padrão `iti_liquido_last`; R8 testou `iti_liquido_mean`).

### 5.5 Critério de vitória e significância

**Vitória incremental** (`validation/incremental.py`):

\[
\Delta = \text{metric}_{ITI} - \text{metric}_{baseline}
\]

(MSE: \(\Delta = \text{MSE}_{baseline} - \text{MSE}_{ITI}\).)

**Filtro `baseline_news_only`:** para B0–B2, o painel é restrito a semanas/dias com `news_count > 0` antes de correlacionar.

**Bootstrap em bloco** (`validation/inference.py`):

- `_block_bootstrap_indices` — amostra blocos contíguos de tamanho `block_size`.
- `compute_delta_inference` — reamostra ITI, baseline e retorno **juntos** (pares preservados).
- `is_significant_favorable_delta` — vitória **significativa** se \(\Delta > 0\) **e** (p &lt; 0,05 **ou** IC 95% não cruza zero).

Win rate = proporção de comparações com \(\Delta > 0\) entre as 24 (4 baselines × 2 métricas × 3 horizontes). Interpretação narrativa: [trajetoria Parte 4](../research_trail/part-04-results.md).

### 5.6 Colunas de `incremental_deltas.csv`

| Coluna | Significado |
| --- | --- |
| `horizon` | Horizonte futuro (dias ou semanas conforme `index_frequency`) |
| `baseline` | `b0` … `b3` |
| `metric` | `pearson`, `spearman`, `r2`, `mse` (conclusão usa subset em YAML) |
| `delta` | \(\Delta\) ITI − baseline (ver §5.3) |
| `p_value` | Bootstrap em bloco |
| `significant` | `true` se favorável e regra em `is_significant_favorable_delta` |

Exemplo mínimo (ilustrativo): se Pearson ITI = 0,20 e Pearson B3 = 0,07 no horizonte 4, \(\Delta = 0{,}13\); significância depende do bootstrap com `block_size=2` na campanha semanal.

Regras de negócio consolidadas: [12_regras_de_negocio.md](12_regras_de_negocio.md).

---
