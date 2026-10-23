# Checklist Parte VII — ITI-v2

Legenda: `[x]` verificado no repo · `[~]` parcial · `[ ]` pendente externo

## 21. Antes da execução completa

- [x] Arquitetura v1/v2 distinguíveis (`iti_v2.py` vs `temporal_index.py` legacy)
- [x] Corpus, protocolo, checkpoint SHA em `protocol_lock.json`
- [x] Holdout por calendário (`select-holdout`); status exploratório no lock
- [x] Contexto focal + `predictions.csv` com `view_id` / `view_hash`
- [x] Deduplicação P02 auditável (`dedup_map.csv`)
- [x] Fórmula v2 testada (`test_iti_v2.py`)
- [x] Retornos no calendário antes do join (`market_weekly_returns.py`)
- [x] Pacote anotação cega (`export-annotation-blind`)
- [x] Campanha `iti_v2.sh` + cache/retomada inferência
- [x] Job `run_iti_v2.srm` encadeado
- [x] Documentação + trilha §4.7 ITI-v2
- [~] Dashboard — leitura de runs legado; campanha ITI-v2 via CSV em `outputs/campaigns/iti_v2/` (sem página dedicada)
- [x] Manuscrito com `\input{generated/iti_v2_results_snippet.tex}`

## 22. Após execução local (`iti_v2_prod_20261022`)

- [x] Artefatos completos + `_SUCCESS`
- [x] 1253 predições, probabilidades validadas (`validate`)
- [~] Referência humana — pacote cego gerado; respostas pendentes
- [x] Métrica principal + Holm + splits dev/holdout
- [x] Modo exploratório explícito
- [x] `thesis_export/` + `export_iti_v2_latex.py`
- [x] Bootstrap 10 000 (`ITI_V2_BOOTSTRAP=10000 evaluate iti_v2_prod_20261022`)
- [x] Preflight SDumont (`iti_v2.sh sdumont-preflight`) + job `run_iti_v2.srm` (validate + export-thesis no fim)
- [ ] **Único pendente do plano:** `sbatch jobs/sdumont/run_iti_v2.srm` no login LNCC
- [ ] Build LaTeX PDF conferido no ambiente do autor

## Comandos de verificação

```bash
./scripts/campaigns/iti_v2.sh gate-local
./scripts/campaigns/iti_v2.sh validate iti_v2_prod_20261022
./scripts/audit_project.sh
```
