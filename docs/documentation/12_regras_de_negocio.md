# 12 Regras de negócio

O que o sistema **calcula**, **compara** e **o que não deve ser inferido** fora do protocolo.

## 12.1 Hipóteses e escopo

| Item | Significado no código |
| --- | --- |
| **H1** (associação ITI × retorno) | Medida por correlação incremental no `research` — **não** é previsão de preço nem recomendação |
| **H2** (volatilidade/volume) | Fora do escopo da qualificação — ver [part-06](../research_trail/part-06-next-cycle.md) |
| **H3** (EWMA vs baselines) | Ablação α e duelos ITI vs B0–B3 na campanha Sabesp |
| **Trilha A** | Sabesp focal; `companies_filter` na research semanal |

Não afirmar **causalidade** nem **eficiência de mercado** — estudo exploratório de correlação.

## 12.2 Sentimento e ITI

- \(d = P_{pos} - P_{neg}\) por notícia — [04_formulas_iti.md](04_formulas_iti.md).
- **ITI líquido** (`iti_liquido`): EWMA de `impacto_dia` com α configurável.
- **ITI risco** (`iti_risco`): lado negativo; alvo pode ser \|retorno\|.
- **B3**: impacto diário **sem** memória EWMA — derivado no research, não no experiment.

## 12.3 Baselines B0–B3

| Baseline | Coluna | Onde calculado |
| --- | --- | --- |
| B0 | `b0_news_count` | experiment |
| B1 | `b1_mean_sentiment` | experiment |
| B2 | `b2_confidence_weighted_sentiment` | experiment |
| B3 | `b3_daily_impact_no_memory` | research (`validation/baselines.py`) |

B0–B2 em dias/semanas com notícia quando `baseline_news_only` ativo.

## 12.4 Protocolo dos 24 duelos (modo semanal Sabesp)

Por run de campanha:

- 4 baselines × 2 métricas de conclusão (Pearson, Spearman) × 3 horizontes semanais (1, 2, 4) = **24 comparações** ITI vs cada baseline.

Config: `conclusion_metrics`, `horizons` em `research_weekly.yaml`. Detalhe: [05_validacao_research.md](05_validacao_research.md), [part-02-protocol](../research_trail/part-02-protocol.md).

**Win** (vitória ITI): δ incremental favorável ao ITI com significância conforme bootstrap — ver `incremental_deltas.csv` e relatórios de campanha.

## 12.5 Modos diário vs semanal

| Modo | `index_frequency` | Coluna ITI típica | Alinhamento |
| --- | --- | --- | --- |
| Diário | `daily` (default) | `iti_liquido` | `io/align.py` |
| Semanal | `weekly` | `iti_liquido_last` | `io/weekly_align.py`, W-FRI |

Retorno futuro: soma de log-returns na janela de horizonte (semanas ou dias conforme modo).

## 12.6 Gates de classificador (avaliação offline)

Em `configs/evaluation.yaml` (não bloqueiam experiment):

| Gate | Valor típico | Uso |
| --- | --- | --- |
| Acurácia | 0,70 | `classifier_gate` |
| Cohen κ | 0,40 | bateria PT (`classifier_eval_pt.py`) |

Amostra n=100: **validar procedimento** até a qualificação — ver [tracking](../tracking/annotation_protocol.md).

## 12.7 Dry-run vs run completa

| Modo | `dry_run: true` | Grava `outputs/{run_id}/`? |
| --- | --- | --- |
| Dry-run | Sim | **Não** (`write_enabled` false) |
| Run normal | Não | Sim (predictions, indices, summary) |

Dry-run ainda executa preflight e valida contagem de linhas do dataset.

## 12.8 Campanha R0–R9

Runs nomeados `sabesp_r*_...` com hipóteses no manifest `outputs/campaigns/sabesp_2026/`. α e dimensões desabilitadas variam por R — [appendices](../research_trail/appendices.md).

## 12.9 O que plugins devem respeitar

- Modelos: saída `ModelPrediction` → schema em `output_schema.py`.
- Juiz: só `news_id` sem rótulo de juiz; idempotente — [module_plugin_contract.md](module_plugin_contract.md).

## 12.10 Manutenção deste documento

Mudou regra em YAML ou métrica de conclusão → atualizar §12.4–12.6 e [decision-register](../research_trail/decision-register.md).
