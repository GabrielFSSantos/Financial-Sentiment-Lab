# Inventário de gráficos — Dashboard FSL

Mapeamento `help_key` → página → artefato de dados. Textos completos em `modules/dashboard/content/chart_help.py`.

| help_key | Página | Gráfico / bloco | Artefato |
| --- | --- | --- | --- |
| `pipeline_journey` | Visão Geral, Trilha | Fluxo Coleta → FinBERT → ITI → Research | — |
| `corpus_by_company` | Visão Geral, Datasets | Barras horizontais por empresa | `data/water_utilities_corpus/*.csv` |
| `corpus_by_source` | Datasets | Barras por portal/fonte | corpus filtrado |
| `corpus_time_series` | Visão Geral, Datasets | Volume temporal | `compute_stats().time_series` |
| `corpus_heatmap` | Datasets | Empresa × mês | `company_month_heatmap()` |
| `class_distribution` | Modelos, Runs | POS/NEG/NEU previstos | `classification_metrics` / agregados |
| `sentiment_by_company` | Modelos | Sentimento médio por empresa | `aggregates.csv` |
| `sentiment_time_series` | Modelos | Série de \(d\) médio | `predictions.csv` |
| `kappa_gate` | Modelos (aba Qualidade) | Gate κ/acurácia + matriz | `outputs/campaigns/classifier_eval_pt/` |
| `iti_daily` | Runs, Research | ITI líquido diário | `indices/*/iti_daily.csv` |
| `iti_vs_return` | Research | Scatter ITI × retorno | `research/*/aligned_panel.csv` |
| `incremental_delta` | Research | Barras Δ ITI − baseline | `incremental_deltas.csv` |
| `market_metrics_heatmap` | Research | Baseline × métrica × horizonte | `market_metrics.csv` |
| `win_rate_by_run` | Comparação | Barras win rate | `research_summary.json` |
| `win_rate_heatmap` | Comparação | Heatmap win rate | `compare_runs()` |
| `alpha_vs_winrate` | Experimentos | Scatter α × win rate | `manifest.json` campanha |
| `ablation_bars` | Experimentos | Ablações R3–R6 | `manifest.json` |
| `sentiment_compare_runs` | Comparação | Sentimento × run × empresa | `aggregates.csv` (multi-run) |
| `param_diff_table` | Runs, Comparação | Diff parâmetros ITI | `resolved_config.yaml` |

## Componentes UX

| Módulo | Função |
| --- | --- |
| `content/pt_br.py` | Rótulos, abas, callouts |
| `content/chart_help.py` | Textos "O que isto mostra?" |
| `content/value_labels.py` | B0–B3, horizontes, runs |
| `components/chart_block.py` | Título + expander + gráfico |
| `components/section_block.py` | Seção com intro/ajuda |
| `components/metric_card.py` | KPI com catálogo e bands |
| `metrics/catalog.py` | Definições win_rate, κ, overlap, etc. |
