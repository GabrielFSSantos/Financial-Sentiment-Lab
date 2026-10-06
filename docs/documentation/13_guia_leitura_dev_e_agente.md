# 13 Guia de leitura — desenvolvedor e agente

## 13.1 Público

| Leitor | Objetivo | Rota |
| --- | --- | --- |
| **Dev novo** | Rodar pipeline e manter módulo | §13.2 → [00_quickstart](00_quickstart_researcher.md) → [11_fluxo](11_fluxo_ponta_a_ponta.md) → [03_modulos](03_modulos.md) |
| **Agente (Cursor)** | Patch seguro, plugins, gates | §13.3 → [10_arquitetura](10_arquitetura_e_manutencao.md) → [12_regras](12_regras_de_negocio.md) → [module_plugin_contract](module_plugin_contract.md) |
| **Pesquisador / banca** | Método e números | [research_trail](../research_trail/README.md) Partes 0–4, [tracking](../tracking/README.md) |

Documentação canônica fica **neste repositório**. O meta-workspace do lab (fora do repo) pode ter harness com prompts e matriz de testes — use apenas como atalho operacional, não como fonte duplicada de arquitetura.

## 13.2 Roteiro mínimo (dev)

1. [README.md](../../README.md) — visão e comandos
2. [00_quickstart_researcher.md](00_quickstart_researcher.md)
3. [11_fluxo_ponta_a_ponta.md](11_fluxo_ponta_a_ponta.md)
4. [06_configuracoes.md](06_configuracoes.md) — YAML
5. [09_testes.md](09_testes.md)

## 13.3 Roteiro agente (antes de editar código)

1. Confirmar escopo: só Financial Sentiment Lab (não misturar outros projetos).
2. Ler [12_regras_de_negocio.md](12_regras_de_negocio.md) — o que o sistema **afirma** vs **não afirma**.
3. Ler [10_arquitetura_e_manutencao.md](10_arquitetura_e_manutencao.md) — dependências entre `modules/`.
4. Extensão (modelo, campanha, juiz): [module_plugin_contract.md](module_plugin_contract.md).
5. Contrato de arquivos: [appendix_output_contract.md](appendix_output_contract.md).
6. Rodar gate após mudanças:

```bash
./scripts/audit_project.sh
./venv/bin/python -m pytest -m "not network"
```

Marcadores úteis: `contract`, `pipeline`, `slow` — ver [09_testes.md](09_testes.md).

## 13.4 Matriz doc ↔ teste (resumo)

| Invariante | Documentação | Teste |
| --- | --- | --- |
| Schema `predictions.csv` | [appendix_output_contract](appendix_output_contract.md), [04](04_formulas_iti.md) | `test_output_schema.py` |
| Dry-run valida sem gravar | [12_regras](12_regras_de_negocio.md) | `test_experiment_dry_run_outputs.py` |
| ITI / EWMA | [04_formulas_iti.md](04_formulas_iti.md) | `test_temporal_index.py` |
| Research semanal W-FRI | [05_validacao_research.md](05_validacao_research.md) | `test_research_weekly_align.py` |
| Overlay campanha datasets | [06_configuracoes.md](06_configuracoes.md) | `test_campaign_config_merge.py` |
| Juiz LLM (stub) | [module_plugin_contract](module_plugin_contract.md) | `test_label_judges.py` |

Detalhe expandido da suíte: matriz `test-traceability-matrix` no meta-workspace do lab (pasta harness/quality).

## 13.5 Idioma e commits

- Prosa para pesquisador: **PT-BR** em `docs/`.
- Código, YAML, paths, CLI: **inglês** — [CONTRIBUTING.md](../../CONTRIBUTING.md).

## 13.6 Pesquisa vs código

| Tipo de mudança | Documentar em |
| --- | --- |
| Run oficial, fase F*, decisão metodológica | [research_trail](../research_trail/README.md), [decision-register](../research_trail/decision-register.md) |
| Módulo, config, teste | [documentation/](README.md) |
| Prazo qualificação, protocolo anotação | [tracking](../tracking/README.md) |
