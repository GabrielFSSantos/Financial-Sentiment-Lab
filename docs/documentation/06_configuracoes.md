# 06 Configuracoes

## 6. Configurações principais

### ITI (`configs/experiment.yaml`)

```yaml
temporal_index:
  alpha: 0.85
  initial_value: 0.0
  horizon:
    mode: ewma_alpha
  baselines:
    enabled: true
  resample:
    frequencies: [weekly, monthly, quarterly]
  uncertainty:
    enabled: true
    min_models: 2
```

### Preflight (`configs/experiment.yaml`)

```yaml
preflight_checks:
  enabled: true
  validate_model_files: true
  validate_dataset_files: true
  validate_output_directory: true
```

Invariantes (schema YAML, matriz não vazia, colunas mínimas) não são desligáveis. `enabled: false` só pula o I/O de `run_preflight`.

### Research (`configs/research.yaml`)

```yaml
validation:
  horizons: [1, 5, 21]
  baselines: [b0, b1, b2, b3]
  conclusion_metrics: [pearson, spearman]
  baseline_news_only: [b0, b1, b2]
  min_samples_for_r2: 30
  return_mode: cumulative
```

### Research semanal Sabesp (`configs/campaigns/sabesp_2026/research_weekly.yaml`)

Usado pela campanha `sabesp_2026` (runs R0–R9). Diferenças principais em relação ao research diário:

```yaml
defaults:
  horizons: [1, 2, 4]              # semanas, não dias
  index_frequency: weekly
  iti_weekly_column: iti_liquido_last   # R8 testou iti_liquido_mean
  companies_filter: [Sabesp]
  return_column: log_return
  return_mode: cumulative

validation:
  inference:
    block_size: 2                  # ajustado para série semanal curta
    n_bootstrap: 500
```

**Mapeamento entidade → ticker** (também em `configs/market.yaml` e `mapping.company_to_ticker`):

| Empresa | Ticker B3 |
| --- | --- |
| Sabesp | `SBSP3.SA` |
| Copasa | `CSMG3.SA` |
| Sanepar | `SAPR4.SA` |

**Corpus strict.** `build_strict_corpus()` gera `noticias_strict.csv` (ou variantes por evento) reaplicando `match_entity(titulo + noticia)` nos registros de `raw/`, sem gerar PENDENTE — preserva o corpus broad em `noticias.csv`.

**Cobertura Sabesp (filtro mai/2022–abr/2024).** Após `scrape-2023` + `corpus`, `data/water_utilities_corpus/articles_strict_sabesp.csv` tem **1.254** artigos (256 em 2022; **199** em jan–abr/2023; resto mai/2023–abr/2024). Sem duplicatas de URL. A lacuna jan–abr/2023 foi preenchida sem replay ITI — ver [trajetoria §4.3](../research_trail/part-04-results.md#43-robustez-janela-expandida). Estadão e Folha ficam desligados (marketing / paywall).

### Merge de overlay de campanha (datasets)

Implementação: `modules/datasets/config/loader.py` → `_merge_campaign_datasets_overlay()`.

| Regra | Comportamento |
| --- | --- |
| Arquivo | `configs/campaigns/datasets.yaml` (opcional) |
| Chaves novas | Adicionadas ao mapa `datasets` do core |
| Chaves existentes no core | **Não** sobrescritas pelo overlay |
| `defaults` | Merge profundo com defaults do core |
| Aliases | `dataset_aliases` aplicados após merge (`saneamento_corpus` → `water_utilities_corpus`) |

Teste: `tests/test_campaign_config_merge.py`.

### Core vs campaigns (`configs/`)

| Camada | Caminho | Papel |
| --- | --- | --- |
| **Core** | `configs/experiment.yaml`, `models.yaml`, `datasets.yaml`, `market.yaml`, `research.yaml` | Pipeline genérico reutilizável |
| **Campaigns** | `configs/campaigns/<nome>/` | Overlays por hipótese (Sabesp R0–R9, pilotos) |
| **Campaign datasets** | `configs/campaigns/datasets.yaml` | Datasets só de campanha (merge) |

Template nova campanha: `configs/campaigns/_template/README.md`.

### Datasets por trilha

| Chave | Trilha | Onde | Uso |
| --- | --- | --- | --- |
| `noticias_exemplo_ptbr`, `news_example_en`, `saneamento_corpus` | core | `configs/datasets.yaml` | Validação e scraper |
| `saneamento_sabesp_strict_event`, `saneamento_sabesp_strict_expanded` | A | overlay campaigns | ITI Sabesp |
| `financial_phrasebank_en`, `nosible_financial_sentiment_en` | B | overlay campaigns | Eval `finbert_en` |
| `fnspid_pilot` | C | overlay campaigns | Piloto ITI US (`configs/campaigns/fnspid_pilot/market.yaml`) |
| `finmarba_headlines_en` | C | overlay campaigns | Diagnóstico classificador |

Fetch de dataset `enabled: false`: `python -m modules.datasets fetch --dataset CHAVE` ou via experimento com `--dataset`.

### Avaliação de rótulos (`modules/evaluation`)

Ver [§3.7](#37-modulesevaluation--métricas-auxiliares) para a lista completa dos 9 módulos e scripts de campanha.

### Nomenclatura e paths

Identificadores de **código, pastas e arquivos de config** em inglês; **conteúdo** de pesquisa e UI do dashboard em PT-BR. CSVs legados podem manter colunas em português — loaders aplicam aliases.

| Legado (PT) | Canônico (EN) | Onde |
| --- | --- | --- |
| `saneamento_corpus` | `water_utilities_corpus` | `dataset_aliases` em `configs/datasets.yaml` |
| `data/saneamento_corpus/` | `data/water_utilities_corpus/` | [`scripts/migrate_data_paths.sh`](../../scripts/migrate_data_paths.sh) |
| `noticias.csv` | `articles.csv` | Idem |
| `noticias_strict_sabesp.csv` | `articles_strict_sabesp.csv` | Idem |
| `rotulos_manual_100.csv` | `manual_labels_100.csv` | Amostra formal (qualificação); `configs/evaluation.yaml` |
| `rotulos_manual_100_exploratorio.csv` | `manual_labels_100_exploratorio.csv` | Rodada exploratória arquivada (referência κ histórico) |
| `rotulo_manual`, `rotulo_finbert` | `human_label`, `model_label` | `column_aliases` em `configs/evaluation.yaml` |
| `visao_geral.py`, … | `overview.py`, `research_trail.py`, … | `modules/dashboard/pages/` (URLs Streamlit em PT — [08_dashboard_streamlit.md](08_dashboard_streamlit.md)) |
| Estrutura `docs/` | `README.md` (índice) + `tracking/`, `documentation/`, `research_trail/`, `references/` | Pastas canônicas |

Melhorias de engenharia pendentes: [engineering_backlog.md](engineering_backlog.md).

---
