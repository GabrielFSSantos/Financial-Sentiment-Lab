# Documentação técnica — Financial Sentiment Lab

Referência para **código**, **fluxos**, **fórmulas**, **configs**, **dashboard** e **testes**. Pesquisa: [research_trail](../research_trail/README.md). Bibliografia: [references](../references/).

## Ordem sugerida

| # | Arquivo | Conteúdo |
| --- | --- | --- |
| 0 | [00_quickstart_researcher.md](00_quickstart_researcher.md) | Fluxo mínimo pesquisador |
| — | [13_dev_and_agent_reading_guide.md](13_dev_and_agent_reading_guide.md) | Rotas dev / agente / gates |
| — | [module_plugin_contract.md](module_plugin_contract.md) | Modelo, juiz, scraper |
| 1 | [01_vision_and_concepts.md](01_vision_and_concepts.md) | Pipeline, glossário |
| 2 | [02_entrypoints_scripts.md](02_entrypoints_scripts.md) | Scripts, CLI, campanhas |
| 3 | [03_modules.md](03_modules.md) | `modules/*` |
| 4 | [04_iti_formulas.md](04_iti_formulas.md) | Fórmulas ↔ código |
| 5 | [05_research_validation.md](05_research_validation.md) | Research, bootstrap, semanal |
| 6 | [06_configuration.md](06_configuration.md) | YAML, merge campanha |
| 7 | [07_santos_dumont.md](07_santos_dumont.md) | SDumont |
| 8 | [08_dashboard_streamlit.md](08_dashboard_streamlit.md) | Streamlit · [chart_inventory.md](chart_inventory.md) |
| 9 | [09_tests.md](09_tests.md) | Pytest, markers |
| 10 | [10_architecture_and_maintenance.md](10_architecture_and_maintenance.md) | DDD, dependências, onde editar |
| 11 | [11_end_to_end_flow.md](11_end_to_end_flow.md) | Coleta → dashboard |
| 12 | [12_business_rules.md](12_business_rules.md) | 24 duelos, gates, escopo |
| — | [engineering_backlog.md](engineering_backlog.md) | Backlog engenharia |
| — | [appendix_output_contract.md](appendix_output_contract.md) | Layout `outputs/` |

Índice geral: [docs/README.md](../README.md).

## Manutenção

- Módulo ou contrato → seção em `03_` / `appendix_output_contract`.
- Regra de negócio → `12_business_rules.md`.
- Decisão experimental → [research_trail](../research_trail/decision-register.md).
