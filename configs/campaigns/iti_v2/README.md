# Campanha ITI-v2 (Sabesp piloto)

- `protocol.yaml` — decisões normativas (meia-vida, cutoff, bootstrap).
- `analysis_plan.yaml` — especificação estatística (loader estrito).
- `research_weekly.yaml` — mapeamento empresa→ticker e métricas.

Fluxo local:

```bash
./scripts/campaigns/iti_v2.sh prepare data/water_utilities_corpus/articles_strict_sabesp.csv
./scripts/campaigns/iti_v2.sh lock-protocol
./scripts/campaigns/iti_v2.sh indices <run_id> <predictions.csv>
./scripts/campaigns/iti_v2.sh evaluate <run_id>
./scripts/campaigns/iti_v2.sh report <run_id>
```

Invólucro: `scripts/campaigns/iti_v2.sh`. Estado da campanha: `docs/research_trail/part-04-results.md` (§4.7) · aceite: `logs/iti_v2/acceptance_latest.md`.
