# Backlog de engenharia

Itens de melhoria **não bloqueantes** para o uso diário do lab (pipeline, audit e testes offline já são o gate padrão).

**Gate diário:** [`./scripts/audit_project.sh`](../../scripts/audit_project.sh)

**Testes com rede / Playwright:** [`09_testes.md`](09_testes.md) (`SCRAPERS_LIVE=1`).

## Itens em aberto

| Área | Descrição |
| --- | --- |
| LLM judge | Implementação batch do juiz de rótulos (contrato coberto por `tests/test_label_judges.py`; substituir `LlmJudgeStub`); ver [module_plugin_contract.md](module_plugin_contract.md) e [tracking/annotation_protocol_v2.md](../tracking/annotation_protocol_v2.md) §7 |
| Experiment loader | Reduzir duplicação em `modules/experiment/config/loader.py` (reuso com `modules/datasets/config/loader.py`) |
| Paths compartilhados | Adotar `modules/common/paths.py` nos pacotes core em vez de paths ad hoc |
| Campanhas | Aliases EN para dataset keys `saneamento_sabesp_*` (se renomear; manter compat via `dataset_aliases`) |
| CLI | `run_experiment.sh --campaign-with-research` (paridade com `run_single` em `scripts/campaigns/sabesp_2026.sh`) |

Atualize esta lista quando um item for concluído; não duplique o mesmo backlog em `research_trail/` ou `tracking/`.
