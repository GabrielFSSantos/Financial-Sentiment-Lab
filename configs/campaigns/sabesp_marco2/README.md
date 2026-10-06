# Marco 2 — janela expandida (mai/22–abr/24)

Script: [`../../scripts/campaigns/sabesp_marco2.sh`](../../scripts/campaigns/sabesp_marco2.sh)

Reutiliza experimentos em `../sabesp_2026/experiments/` e research em `../sabesp_2026/research_weekly.yaml`.

Dataset: `saneamento_sabesp_strict_expanded` (overlay em `../datasets.yaml`).

## Comandos manuais equivalentes

```bash
./modules/scrapers/scripts/run_scrape.sh historical --since 2022-05-01 --until 2022-10-31
./scripts/campaigns/sabesp_marco2.sh scrape-2023   # lacuna jan–abr/2023
./modules/scrapers/scripts/run_scrape.sh build-strict
python -m modules.scrapers filter-corpus --company Sabesp \
  --since 2022-05-01 --until 2024-04-30 \
  -o data/water_utilities_corpus/articles_strict_sabesp.csv

# Fechamento Trilha A (corpus 1.254, run_ids novos — não sobrescreve Marco 2)
./scripts/campaigns/sabesp_marco2.sh replay-gap2023
./scripts/campaigns/sabesp_marco2.sh replay-event-gap2023
./scripts/campaigns/sabesp_marco2.sh analyze-periods --run-id sabesp_gap2023_r1_alpha070
./scripts/campaigns/sabesp_marco2.sh significant-wins
./scripts/campaigns/classifier_eval_pt.sh run
./scripts/campaigns/classifier_eval_pt.sh error-analysis
# Só se contaminação roundup ≥25% na amostra manual:
./scripts/campaigns/sabesp_marco2.sh replay-event-filtered

./scripts/run_experiment.sh --skip-setup \
  --experiment-config configs/campaigns/sabesp_2026/experiments/r1_alpha070.yaml \
  --run-id sabesp_marco2_r1_alpha070 \
  --dataset saneamento_sabesp_strict_expanded \
  --model finbert_ptbr

./scripts/run_research.sh \
  --run-id sabesp_marco2_r1_alpha070 \
  --dataset saneamento_sabesp_strict_expanded \
  --model finbert_ptbr \
  --config configs/campaigns/sabesp_2026/research_weekly.yaml
```
