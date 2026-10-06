# Apendice Contrato Outputs

## Apêndice A — Contrato `outputs/`

Estrutura por run (`outputs/{run_id}/`):

```
outputs/{run_id}/
├── summary.json
├── resolved_config.yaml
├── models/{model_key}/{dataset_key}/
│   ├── predictions.csv
│   ├── aggregates.csv
│   └── classification_metrics.json   # se true_label presente
├── indices/{model_key}/{dataset_key}/
│   ├── iti_daily.csv
│   ├── baselines_daily.csv
│   ├── iti_sector_daily.csv        # opcional
│   └── iti_resampled_weekly.csv    # se resample habilitado
└── research/{model_key}/{dataset_key}/   # após run_research
    ├── aligned_panel.csv
    ├── incremental.csv
    ├── incremental_deltas.csv
    ├── market_metrics.csv
    └── research_summary.json
```

### Colunas principais

| Arquivo | Colunas essenciais |
| --- | --- |
| `predictions.csv` | `news_id`, `text`, `date`, `company`, `continuous_sentiment` (\(d\)), `confidence`, `prob_*`, `prediction_metadata` |
| `aggregates.csv` | `aggregation_level`, `date`, `company`/`sector`, `sentiment_mean`, `sentiment_count` |
| `iti_daily.csv` | `date`, `company`, `impacto_dia`, `risco_dia`, `iti_liquido`, `iti_risco`, `news_count` |
| `baselines_daily.csv` | `date`, `company`, `b0_news_count`, `b1_mean_sentiment`, `b2_confidence_weighted_sentiment` |
| `aligned_panel.csv` | `date`, `company`, `ticker`, `iti_liquido_last`, baselines B0–B3, `future_log_return_{h}` |
| `incremental_deltas.csv` | `horizon`, `baseline`, `metric`, `delta`, `p_value`, `significant` |
| `research_summary.json` | `conclusion`, `combinations[].predictor_stats` (wins, comparisons) |

Schema completo de `predictions.csv`: `OUTPUT_COLUMNS` em `modules/experiment/io/output_schema.py`. Testes: `tests/test_output_schema.py` (marker `contract`).

### Dry-run vs run completa

| Modo | Grava `outputs/{run_id}/`? | O que valida |
| --- | --- | --- |
| `dry_run: true` | **Não** — `ResultsManager.write_enabled` false | Preflight, contagem de linhas, combinações em `summary` em memória |
| Run normal | Sim — árvore abaixo | Inferência, ITI, CSVs |

Comando dry-run: `./scripts/run_service.sh --dry-run --model ... --dataset ...`. Ver [12_regras_de_negocio.md](12_regras_de_negocio.md) §12.7.

### Fixtures de teste (sem run GPU)

Research offline usa árvore mínima em `tests/fixtures/research/outputs/test_run/` (`iti_daily.csv`, `baselines_daily.csv`). Ver `tests/test_research_check.py`.
