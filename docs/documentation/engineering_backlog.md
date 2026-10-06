# Backlog de engenharia

Itens de melhoria **não bloqueantes** para o uso diário do lab (pipeline, audit e testes offline já são o gate padrão).

**Gate diário:** [`./scripts/audit_project.sh`](../../scripts/audit_project.sh)

**Testes com rede / Playwright:** [`09_testes.md`](09_testes.md) (`SCRAPERS_LIVE=1`).

## Itens em aberto

| Área | Descrição |
| --- | --- |
| LLM judge | Piloto CLI + `HfCausalLabelJudge` (mock/GPU); expandir para API e batch completo pós-quali; ver [llm_judge.md](../references/notas/llm_judge.md) |
| Experiment loader | Reduzir duplicação em `modules/experiment/config/loader.py` (reuso com `modules/datasets/config/loader.py`) |
| Paths compartilhados | Adotar `modules/common/paths.py` nos pacotes core em vez de paths ad hoc |
| Campanhas | Aliases EN para dataset keys `saneamento_sabesp_*` (se renomear; manter compat via `dataset_aliases`) |
| CLI | `run_experiment.sh --campaign-with-research` (paridade com `run_single` em `scripts/campaigns/sabesp_2026.sh`) |

Atualize esta lista quando um item for concluído; não duplique o mesmo backlog em `research_trail/` ou `tracking/`.
