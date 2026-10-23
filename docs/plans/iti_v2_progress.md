# Progresso ITI-v2 (P00–P12)

Atualizado pelo agente conforme `Plano_Mestre_ITI_v2_Cursor_Dissertacao_SDumont.md`.

| Etapa | Estado | Evidência |
|-------|--------|-----------|
| P00 Preservar histórico | **completed** | `docs/plans/`, branch de trabalho, este arquivo |
| P01 Auditoria consistência | **implemented** | `historical_reconciliation.csv`, `part-04-results.md`, README, bib |
| P02 Inventário corpus | **implemented** | P02 + `select-holdout` (12 semanas), `holdout_news_ids.csv` |
| P03 Contexto focal | **implemented** | `iti_v2_inference.py` (entity_context + cache + contrato CSV), `text_views`, SHA finbert |
| P04 ITI-v2 | **implemented** | `iti_v2.py` + `build_weekly_signals`, testes; orquestrador legado intacto |
| P05 Alinhamento/estatística | **implemented** | `alignment_audit.py`, bootstrap em bloco + Holm (`iti_v2_statistics.py`, `metrics_inference.json`) |
| P06 Avaliação humana | **implemented** | `export-blind` / `import-blind` em `manual_labels.py` |
| P07 Campanha | **implemented** | `iti_v2.sh`: prepare → lock-protocol → infer → indices → evaluate → report (`_SUCCESS`) |
| P08 Testes liberação | **implemented** | `iti_v2_acceptance.py`, `validate` / `iti_v2_acceptance_latest.md`, pytest offline |
| P09 Documentação | **implemented** | trilha §4.7, `08_dashboard`, `14_manual_annotation`, `iti_v2_checklist.md` (Parte VII) |
| P10 Manuscrito | **updated** | 7 capítulos + `generated/iti_v2_results_snippet.tex` em `06_resultados.tex` |
| P11 Congelar protocolo | **implemented** | `protocol_lock.json` + holdout em `split_manifest.json` (`select-holdout`) |
| P12 Execução | **completed (local)** | `iti_v2_prod_20261022` (1253 preds, `metrics_development.json` / `metrics_holdout.json`) |
| P12 SDumont | **pending (único passo operacional do plano)** | `gate-local` + `sdumont-preflight` OK no PC; submeter `jobs/sdumont/run_iti_v2.srm` |

**Situação (23/out/2026):** código, documentação, run local de produção e critérios de aceite (**20/20** em `iti_v2_prod_20261022`) concluídos. **Falta apenas** execução no cluster (replica GPU + `sdumont_job_metadata.txt`).

**Bloqueios externos (não bloqueiam submissão SDumont):** anotação humana independente (P06), análise **confirmatória** no holdout, build PDF LaTeX no ambiente do autor.

**Antes do `sbatch` no PC:**

```bash
./scripts/campaigns/iti_v2.sh gate-local    # ou: check + sdumont-preflight
```
