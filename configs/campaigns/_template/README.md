# Template de campanha

Copie esta pasta para `configs/campaigns/<sua_campanha>/` e ajuste:

1. `experiments/*.yaml` — overlay sobre `configs/experiment.yaml` (run_id, α do ITI, chave do dataset)
2. `research_weekly.yaml` — horizontes e tickers para `modules.research`
3. Registre datasets em `configs/campaigns/datasets.yaml` (mesclado automaticamente)

Fluxo de execução:

```bash
./scripts/run_experiment.sh --run-id <run_id> --model <model> --dataset <dataset>
./scripts/run_research.sh --run-id <run_id> --model <model> --dataset <dataset>
```

Ver [docs/documentation/00_quickstart_researcher.md](../../../docs/documentation/00_quickstart_researcher.md).
