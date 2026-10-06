# 09 Testes

## 9. Testes

```bash
pytest -m "not network"
./scripts/audit_project.sh
```

**Scrapers live (rede + Playwright):** desabilitados por padrão. Para rodar:

```bash
playwright install chromium   # uma vez, no venv
SCRAPERS_LIVE=1 pytest tests/test_scrapers_live.py
```

Sem `SCRAPERS_LIVE=1`, testes `@pytest.mark.network` / `playwright` são ignorados (ver `tests/conftest.py`).

**Marcadores pytest** (`pytest.ini`):

| Marker | Uso |
| --- | --- |
| `contract` | Schema de `predictions.csv`, juízes, filtros de corpus, W-FRI |
| `pipeline` | Integração offline (executor, dry-run) |
| `slow` | Dry-run completo do runner — opcional no gate rápido |
| `network` / `playwright` | Scrapers live (excluídos do audit padrão) |

Exemplos:

```bash
pytest -m "contract" -q
pytest -m "pipeline and not slow" -q
pytest -m "not network and not slow" -q   # equivalente ao audit, sem dry-run lento
```

Fixtures em `tests/fixtures/` cobrem mercado, research e experimento dry-run.

**Testes de higiene do pipeline** (comportamento do runner e preflight):

| Arquivo | O que valida |
| --- | --- |
| `tests/test_preflight.py` | Flags de `preflight_checks`, bypass com `enabled: false`, inspeção JSONL com `nrows=1` |
| `tests/test_performance_monitor.py` | `CombinationPerformanceMonitor` como no-op quando `performance_metrics.enabled: false` |
| `tests/test_runner_lifecycle.py` | Restauração de signal handlers em falha cedo; unload de modelo só ao trocar `model_key`; cache de `texts`; unload entre datasets do mesmo modelo |

**Contrato e pipeline (novos):**

| Arquivo | O que valida |
| --- | --- |
| `tests/test_output_schema.py` | `OUTPUT_COLUMNS`, normalização `ModelPrediction`, `OutputSchemaBuilder` |
| `tests/test_experiment_dry_run_outputs.py` | Dry-run: `summary` em memória, sem gravar `outputs/` |
| `tests/test_combination_executor.py` | `execute_combination` persiste resultados e ITI (mock) |
| `tests/test_label_judges.py` | `JudgePrediction`, `LlmJudgeStub` |
| `tests/test_evaluation_config.py` | `configs/evaluation.yaml` |
| `tests/test_campaign_config_merge.py` | Overlay `configs/campaigns/datasets.yaml` |
| `tests/test_event_corpus_filter.py` | Janela de evento e filtro de roundups |

Outros testes relevantes: `test_research_weekly_align.py` (alinhamento semanal), `test_temporal_index.py` (EWMA), `test_experiment_baselines.py` (B0–B2), `test_dashboard_compare.py` (diffs Arrow-safe), `test_dashboard_catalog.py`, `test_dashboard_corpus.py`, `test_dashboard_insights.py`.

### Doc ↔ teste (resumo)

| Doc | Invariante | Teste(s) |
| --- | --- | --- |
| [04_formulas_iti](04_formulas_iti.md) | EWMA, baselines B0–B2 | `test_temporal_index.py`, `test_experiment_baselines.py` |
| [05_validacao_research](05_validacao_research.md) | Alinhamento semanal W-FRI | `test_research_weekly_align.py` |
| [appendix_output_contract](appendix_output_contract.md) | Schema `predictions.csv`, dry-run sem disco | `test_output_schema.py`, `test_experiment_dry_run_outputs.py` |
| [06_configuracoes](06_configuracoes.md) | Merge overlay campanha | `test_campaign_config_merge.py` |
| [12_regras_de_negocio](12_regras_de_negocio.md) §corpus evento | Filtro roundups | `test_event_corpus_filter.py` |
| [module_plugin_contract](module_plugin_contract.md) | Juízes LLM | `test_label_judges.py` |
| [03_modulos](03_modulos.md) §executor | Combinação modelo×dataset | `test_combination_executor.py` |

Ordem de leitura antes de novos testes: [13_guia_leitura_dev_e_agente](13_guia_leitura_dev_e_agente.md).

Matriz completa: `harness/quality/test-traceability-matrix.md` no **meta-workspace** do lab (abrir o `workspace.code-workspace` focado do Financial Sentiment Lab).

Para rodar só a higiene do pipeline:

```bash
pytest tests/test_preflight.py tests/test_performance_monitor.py tests/test_runner_lifecycle.py -q
```

---
