# Documentação técnica — Financial Sentiment Lab

Referência para **código**, **fluxos**, **fórmulas**, **configs**, **dashboard** e **testes**. Pesquisa: [research_trail](../research_trail/README.md). Bibliografia: [references](../references/).

## Ordem sugerida

| # | Arquivo | Conteúdo |
| --- | --- | --- |
| 0 | [00_quickstart_researcher.md](00_quickstart_researcher.md) | Fluxo mínimo pesquisador |
| — | [13_guia_leitura_dev_e_agente.md](13_guia_leitura_dev_e_agente.md) | Rotas dev / agente / gates |
| — | [module_plugin_contract.md](module_plugin_contract.md) | Modelo, juiz, scraper |
| 1 | [01_visao_e_conceitos.md](01_visao_e_conceitos.md) | Pipeline, glossário |
| 2 | [02_entrypoints_scripts.md](02_entrypoints_scripts.md) | Scripts, CLI, campanhas |
| 3 | [03_modulos.md](03_modulos.md) | `modules/*` |
| 4 | [04_formulas_iti.md](04_formulas_iti.md) | Fórmulas ↔ código |
| 5 | [05_validacao_research.md](05_validacao_research.md) | Research, bootstrap, semanal |
| 6 | [06_configuracoes.md](06_configuracoes.md) | YAML, merge campanha |
| 7 | [07_santos_dumont.md](07_santos_dumont.md) | SDumont |
| 8 | [08_dashboard_streamlit.md](08_dashboard_streamlit.md) | Streamlit · [chart_inventory.md](chart_inventory.md) |
| 9 | [09_testes.md](09_testes.md) | Pytest, markers |
| 10 | [10_arquitetura_e_manutencao.md](10_arquitetura_e_manutencao.md) | DDD, dependências, onde editar |
| 11 | [11_fluxo_ponta_a_ponta.md](11_fluxo_ponta_a_ponta.md) | Coleta → dashboard |
| 12 | [12_regras_de_negocio.md](12_regras_de_negocio.md) | 24 duelos, gates, escopo |
| — | [engineering_backlog.md](engineering_backlog.md) | Backlog engenharia |
| — | [appendix_output_contract.md](appendix_output_contract.md) | Layout `outputs/` |

Índice geral: [docs/README.md](../README.md).

## Manutenção

- Módulo ou contrato → seção em `03_` / `appendix_output_contract`.
- Regra de negócio → `12_regras_de_negocio.md`.
- Decisão experimental → [research_trail](../research_trail/decision-register.md).
