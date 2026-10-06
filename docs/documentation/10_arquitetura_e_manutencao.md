# 10 Arquitetura e manutenção

Guia para **onde colocar código** e **o que não misturar** entre pacotes. Complementa [module_plugin_contract.md](module_plugin_contract.md).

## 10.1 Bounded contexts (`modules/*`)

| Contexto | Pacote | Responsabilidade |
| --- | --- | --- |
| Coleta | `scrapers` | Portais → CSV bruto / corpus |
| Corpus | `datasets` | Leitura YAML → `LoadedDataset` |
| Inferência | `models` | `ModelPrediction` por notícia |
| Experimento | `experiment` | ITI, baselines B0–B2, `outputs/{run_id}/` |
| Mercado | `market` | Preços yfinance → retornos |
| Validação | `research` | ITI × retorno futuro, B3, bootstrap |
| Avaliação offline | `evaluation` | κ, amostra manual, juiz LLM (piloto) |
| UI | `dashboard` | Streamlit — **somente leitura** de `outputs/` |
| Utilitários | `common` | `paths.py` — mínimo |

Fluxo de dados: [11_fluxo_ponta_a_ponta.md](11_fluxo_ponta_a_ponta.md).

## 10.2 Regras de dependência

| Permitido | Proibido |
| --- | --- |
| `experiment` → `models`, `datasets` | `research` → `scrapers` |
| `research` → arquivos em `outputs/` | `evaluation` calcular EWMA/ITI |
| `dashboard` → `outputs/`, configs de leitura | `dashboard` recalcular ITI |
| Qualquer → `common.paths` | Paths absolutos hardcoded |

## 10.3 SOLID (aplicação prática)

| Princípio | No lab |
| --- | --- |
| **S** | `preflight.py`, `combination_executor.py`, `weekly_align.py` — um papel por módulo |
| **O** | Novo modelo = YAML + adapter; evitar ramos no `runner.py` |
| **L** | Adapters BERT e futuros juízes substituíveis |
| **I** | `BaseSentimentModel` ≠ `BaseLabelJudge` |
| **D** | Pipeline depende de loaders YAML e registry |

## 10.4 Onde mudar o quê

| Objetivo | Onde editar | Verify |
| --- | --- | --- |
| Novo FinBERT / checkpoint | `configs/models.yaml`, `modules/models/adapters/` | `pytest tests/test_models_config.py` |
| Novo dataset | `configs/datasets.yaml` ou overlay campanha | `pytest tests/test_datasets_config.py` |
| α ITI, dimensões | `configs/experiment.yaml` ou overlay `configs/campaigns/*/experiments/` | `pytest tests/test_temporal_index.py` |
| Horizontes / semanal | `configs/research.yaml` ou `research_weekly.yaml` | `pytest tests/test_research_config.py` |
| Nova campanha | Copiar `configs/campaigns/_template/` | [06_configuracoes.md](06_configuracoes.md) |
| Contrato CSV saída | `modules/experiment/io/output_schema.py` | `pytest tests/test_output_schema.py` |
| Plugin juiz LLM | `modules/evaluation/judges/`, `configs/evaluation.yaml` | `pytest tests/test_label_judges.py` |

## 10.5 Anti-padrões

- Lógica de ITI em `evaluation/` ou `dashboard/`
- Script shell novo quando YAML + `run_experiment.sh` resolve
- Duplicar merge de `datasets.yaml` fora de `modules/datasets/config/loader.py`
- Commitar `model_store/`, `.env`, outputs de produção

## 10.6 Gate antes de PR

```bash
./scripts/audit_project.sh
./venv/bin/python -m pytest -m "not network"
```

Ordem de leitura para agentes: [13_guia_leitura_dev_e_agente.md](13_guia_leitura_dev_e_agente.md).
