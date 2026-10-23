# Relatório P12 — implementação ITI-v2 (pré-cluster completo)

**Data:** 2026-10-22  
**Gate:** `./scripts/audit_project.sh` OK · pytest offline OK · aceite 18+ critérios em `iti_v2_acceptance_latest.md`

## Arquivos / módulos principais

| Área | Artefato |
|------|----------|
| P02 | `modules/datasets/corpus_prepare.py`, `corpus_inventory.py` |
| P03 | `modules/datasets/text_views.py`, `modules/experiment/campaign/iti_v2_inference.py` |
| P04 | `modules/experiment/indexing/iti_v2.py` |
| P05 | `modules/research/io/alignment_audit.py`, `iti_v2_statistics.py` (bootstrap + Holm) |
| P06 | `modules/evaluation/manual_labels.py` (export/import cego) |
| P07–P11 | `iti_v2_pipeline.py`, `protocol_lock.py`, `iti_v2_acceptance.py`, `scripts/campaigns/iti_v2.sh` |
| P12 | `jobs/sdumont/run_iti_v2.srm`, `docs/plans/iti_v2_runbook.md` |

## Comandos validados

```bash
./scripts/campaigns/iti_v2.sh check
ITI_V2_INFER_LIMIT=40 ITI_V2_BOOTSTRAP=200 ./scripts/campaigns/iti_v2.sh run-all iti_v2_auto_20261022
./scripts/campaigns/iti_v2.sh validate iti_v2_auto_20261022
```

## Hashes / lock

Ver `outputs/corpus_inventory/iti_v2_p02/protocol_lock.json` após `lock-protocol`.

## Run de produção local (2026-10-22)

- **run_id:** `iti_v2_prod_20261022`
- **Corpus:** 1253 artigos canônicos (`articles_strict_sabesp.csv` → P02)
- **Aceite:** 20/20 em `./scripts/campaigns/iti_v2.sh validate iti_v2_prod_20261022`
- **Pacote tese:** `outputs/campaigns/iti_v2/iti_v2_prod_20261022/thesis_export/`

## Holdout e splits (pós-seleção)

- `select-holdout 12` → 1054 desenvolvimento / 199 holdout (notícias)
- `metrics_holdout.json` no run de produção (exploratório; não abrir como confirmatório sem referência humana)

## Pendente operacional

1. **Replica SDumont** — único passo operacional pendente: `sbatch jobs/sdumont/run_iti_v2.srm` após `gate-local` / `sdumont-preflight` no PC.
2. **Anotação cega** — `./scripts/campaigns/iti_v2.sh export-annotation-blind`.
3. **Env SDumont** — `outputs/campaigns/iti_v2/env_lock/requirements-frozen.txt` (`iti_v2.sh pin-env`).

## Dependências do autor

- Submissão job SDumont com `ITI_PROJECT_DIR` e credenciais LNCC.
- Decisão formal de janela holdout quando inventário estiver fechado.
