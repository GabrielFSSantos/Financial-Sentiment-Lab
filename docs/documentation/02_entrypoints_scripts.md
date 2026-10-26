# 02 Entrypoints Scripts

## 2. Entrypoints e scripts

```mermaid
flowchart TB
  subgraph scripts [scripts/]
    setup[setup_env.sh --fetch-assets]
    audit[audit_project.sh]
    runExp[run_experiment.sh]
    runRes[run_research.sh]
  end

  subgraph experimentMod [modules/experiment]
    expAssets[config/assets.py]
    expRunner[pipeline/runner.py]
    expLoader[config/loader.py]
    indexing[indexing/*]
  end

  subgraph modelsMod [modules/models]
    mdlLoader[config/loader.py]
    mdlAssets[assets.py]
    registry[registry.py]
    adapters[adapters/bert/*]
  end

  setup --> expAssets
  setup --> mdlAssets
  runExp --> expRunner
  expRunner --> indexing
  expLoader --> mdlLoader
  mdlLoader --> registry
  registry --> adapters
  runRes --> researchCLI[modules.research validate]
```

| Script | Função |
| --- | --- |
| `scripts/setup_env.sh` | Cria `venv/`, instala deps; `--fetch-assets` baixa modelos, datasets e mercado |
| `scripts/audit_project.sh` | Estrutura, YAML, pytest, dry-run |
| `scripts/run_experiment.sh` | Chama `python -m modules.experiment`; use `--experiment-config` e `--run-id` explícitos |
| `scripts/run_research.sh` | Chama `python -m modules.research validate` |
| `scripts/run_dashboard.sh` | Dashboard Streamlit de exploração da pesquisa |
| `modules/scrapers/scripts/scrape.sh` | Wrapper de coleta |
| `modules/scrapers/scripts/build_corpus.sh` | Mescla `raw/` → corpus |
| `modules/market/scripts/fetch.sh` | Wrapper de preços |
| `modules/models/scripts/fetch.sh` | Download isolado de modelos |
| `modules/datasets/scripts/fetch.sh` | Download isolado de datasets |

### Scripts de campanha

Ver [`scripts/campaigns/README.md`](../../scripts/campaigns/README.md) e [`configs/campaigns/README.md`](../../configs/campaigns/README.md).

| Script | Função |
| --- | --- |
| `scripts/campaigns/iti_v2.sh` | Campanha ITI-v2: `prepare` → `lock-protocol` → `infer` → `indices` → `evaluate` → `report` → `validate`; `postprocess` com `FSL_HARNESS_ROOT` opcional para LaTeX |
| `scripts/campaigns/classifier_eval_pt.sh` | κ bateria PT (FinBERT vs controles) |

Campanhas históricas (Sabesp R0–R9, pilotos) foram retiradas do repo; resultados na trilha §4.

### CLIs `python -m modules.*`

| Módulo | Comandos úteis |
| --- | --- |
| `modules.experiment` | `--dry-run`, `--model`, `--dataset`, `run_id` |
| `modules.research` | `validate`, `check` |
| `modules.models` | `check`, `fetch --model KEY` |
| `modules.datasets` | `check`, `validate`, `fetch` |
| `modules.market` | `check`, fetch via script |
| `modules.scrapers` | subcomandos em `cli/main.py` |
| `modules.evaluation` | campanhas manuais / relatórios |

Detalhe de flags: `--help` em cada módulo; campanhas encapsulam sequências em `scripts/campaigns/`.

### Variáveis de ambiente

| Variável | Efeito |
| --- | --- |
| `SCRAPERS_LIVE=1` | Habilita `pytest` de scrapers com rede/Playwright |
| `TRANSFORMERS_OFFLINE=1` / `HF_HUB_OFFLINE=1` | Inferência offline (padrão em `run_service.sh`) |
| `PYTHONPATH` | Raiz do repo (scripts já exportam) |
| Secrets (API juiz) | `.env` — nunca commitar |

Fluxo completo: [11_end_to_end_flow.md](11_end_to_end_flow.md).

---
