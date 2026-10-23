# Runbook ITI-v2 (autônomo)

Ordem normativa (plano mestre P02→P12):

```bash
cd ~/GitHub/Financial-Sentiment-Lab

# Cadeia completa (amostra: ITI_V2_INFER_LIMIT=40; produção: =0)
ITI_V2_INFER_LIMIT=0 ./scripts/campaigns/iti_v2.sh run-all iti_v2_prod_YYYYMMDD

# Ou passo a passo
./scripts/campaigns/iti_v2.sh prepare
./scripts/campaigns/iti_v2.sh select-holdout 12   # holdout temporal (sem retornos)
./scripts/campaigns/iti_v2.sh lock-protocol
ITI_V2_INFER_LIMIT=0 ./scripts/campaigns/iti_v2.sh infer iti_v2_prod_YYYYMMDD
./scripts/campaigns/iti_v2.sh indices iti_v2_prod_YYYYMMDD
./scripts/campaigns/iti_v2.sh evaluate iti_v2_prod_YYYYMMDD
./scripts/campaigns/iti_v2.sh report iti_v2_prod_YYYYMMDD
./scripts/campaigns/iti_v2.sh validate iti_v2_prod_YYYYMMDD
./scripts/campaigns/iti_v2.sh export-thesis iti_v2_prod_YYYYMMDD
```

**Aceite:** `docs/plans/iti_v2_acceptance_latest.md` (20 critérios) + `_SUCCESS` no run.

**Gate local (antes de qualquer submissão HPC):**

```bash
./scripts/campaigns/iti_v2.sh gate-local
# log: docs/plans/iti_v2_validation_latest.log
```

**SDumont (único passo pendente após gate local):**

1. No PC: `./scripts/campaigns/iti_v2.sh sdumont-preflight`
2. No login: sync repo + `model_store/FinBERT-PT-BR`, venv com torch CUDA (ver `docs/documentation/07_santos_dumont.md` §7.10)
3. `export ITI_PROJECT_DIR ITI_RUN_ID`; `sbatch jobs/sdumont/run_iti_v2.srm`
4. Após o job: `validate` + `scp` de `outputs/campaigns/iti_v2/<run_id>/`

Deps: `./scripts/campaigns/iti_v2.sh pin-env` → `outputs/campaigns/iti_v2/env_lock/requirements-frozen.txt`.

**Modo:** `ITI_V2_MODE=exploratory` até holdout formal (`split_manifest`).

**Retomada inferência:** reexecutar `infer` com mesmo `run_id` — ignora `news_id` já em `predictions.csv`.

**Bootstrap:** `analysis_plan.yaml` usa 10 000 réplicas; dev rápido: `ITI_V2_BOOTSTRAP=200` no `evaluate`/`run-all`.
