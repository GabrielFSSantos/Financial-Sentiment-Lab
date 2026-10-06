# Quickstart — pesquisador

Fluxo mínimo para rodar o lab em um PC (sem cluster).

## 1. Ambiente

```bash
./scripts/setup_env.sh --fetch-assets
./scripts/audit_project.sh
```

## 2. Corpus

- Exemplo com rótulos: dataset `noticias_exemplo_ptbr` em `configs/datasets.yaml`
- Corpus do scraper: `saneamento_corpus` (alias EN: `water_utilities_corpus`) — ver [`modules/scrapers/scripts/run_scrape.sh`](../../modules/scrapers/scripts/run_scrape.sh)

## 3. Experimento (sentimento + ITI)

```bash
./scripts/run_experiment.sh --model finbert_ptbr --dataset noticias_exemplo_ptbr
```

Saída: `outputs/{run_id}/indices/...`

## 4. Mercado + research

```bash
python -m modules.market fetch
python -m modules.research validate --run-id <run_id> --model finbert_ptbr --dataset noticias_exemplo_ptbr
```

## 5. Próximos passos

- Contrato de plugins: [module_plugin_contract.md](module_plugin_contract.md)
- Detalhe técnico: [README.md](README.md)
- Nova campanha: copiar [`configs/campaigns/_template/`](../../configs/campaigns/_template/README.md)

## Adaptar a outro setor

1. Editar [`configs/entities.yaml`](../../configs/entities.yaml) (empresas/tickers)
2. Ajustar `configs/scrapers.yaml` (portais, queries)
3. Novo dataset em `configs/datasets.yaml` com mapeamento de colunas
4. Manter o mesmo `run_experiment.sh` / `run_research.sh`
