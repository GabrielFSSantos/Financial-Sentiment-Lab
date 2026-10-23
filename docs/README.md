# Documentação — Financial Sentiment Lab

Entrada na raiz: [README.md](../README.md).

## Pilares

| Pasta | Papel |
| --- | --- |
| [research_trail/](research_trail/README.md) | Pesquisa — fases F0–F6, decisões, Parte 4 = números oficiais |
| [documentation/](documentation/README.md) | Código — módulos, ITI, regras, testes |
| [references/](references/) | BibTeX, PDFs, notas por obra |
| [Dissertacao_PPGCC/](Dissertacao_PPGCC/) | Manuscrito LaTeX |

## Por onde começar

| Leitor | Rota |
| --- | --- |
| Desenvolvedor | [13_dev_reading_guide](documentation/13_dev_reading_guide.md) → [11_end_to_end_flow](documentation/11_end_to_end_flow.md) |
| Pesquisador / banca | [research_trail](research_trail/README.md) · dissertação |
| Cluster SDumont | [07_santos_dumont](documentation/07_santos_dumont.md) |

Prosa em PT-BR; paths e código em inglês — [CONTRIBUTING.md](../CONTRIBUTING.md).

## Manutenção

| Mudança | Onde |
| --- | --- |
| Fase F*, decisão metodológica | [decision-register](research_trail/decision-register.md) + [part-03](research_trail/part-03-phases.md) |
| Regra de negócio | [12_business_rules](documentation/12_business_rules.md) |
| Módulo / config | [documentation/](documentation/README.md) |
| Anotação manual | [14_manual_annotation](documentation/14_manual_annotation.md) |
| Campanha ITI-v2 | [part-04 §4.7](research_trail/part-04-results.md) · `configs/campaigns/iti_v2/` · `./scripts/campaigns/iti_v2.sh` · aceite `logs/iti_v2/acceptance_latest.md` |

Artefatos numéricos e logs de cluster: `outputs/` (gitignored). Export LaTeX da dissertação: `scripts/dissertation/iti_v2/` (via `iti_v2.sh postprocess`).
