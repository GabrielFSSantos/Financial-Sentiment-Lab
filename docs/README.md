# Documentação — Financial Sentiment Lab

Entrada na raiz do repositório: [README.md](../README.md).

## Dois pilares

| Pasta | Papel |
| --- | --- |
| **[research_trail/](research_trail/README.md)** | Histórico da pesquisa — decisões (`decision-register`), fases F0–F6, **Parte 4 = números oficiais** |
| **[documentation/](documentation/README.md)** | Código e operação — módulos, fórmulas ITI, regras de negócio, fluxos, testes |

## Acadêmico e bibliografia

| Caminho | Conteúdo |
| --- | --- |
| [references/](references/) | BibTeX, PDFs versionados, notas por artigo |
| [Dissertacao_PPGCC/](Dissertacao_PPGCC/) | Manuscrito LaTeX (qualificação / defesa) |

## Público-alvo

| Leitor | Começar por |
| --- | --- |
| **Desenvolvedor** | [documentation/13_dev_and_agent_reading_guide.md](documentation/13_dev_and_agent_reading_guide.md) → [11_end_to_end_flow.md](documentation/11_end_to_end_flow.md) |
| **Agente (IA)** | [13_dev_and_agent_reading_guide.md](documentation/13_dev_and_agent_reading_guide.md) → [10_architecture_and_maintenance.md](documentation/10_architecture_and_maintenance.md) |
| **Pesquisador / banca** | [research_trail/](research_trail/README.md) Partes 0–4 · [Dissertacao_PPGCC/](Dissertacao_PPGCC/) |
| **Operação cluster** | [documentation/07_santos_dumont.md](documentation/07_santos_dumont.md) |

**Idioma:** código e paths em inglês; prosa em PT-BR — [CONTRIBUTING.md](../CONTRIBUTING.md).

## Manutenção

| Tipo de mudança | Onde documentar |
| --- | --- |
| Fase F*, run oficial, decisão metodológica | [research_trail/part-03](research_trail/part-03-phases.md) + [decision-register](research_trail/decision-register.md) |
| Regra de negócio | [documentation/12_business_rules.md](documentation/12_business_rules.md) |
| Módulo / config / teste | [documentation/](documentation/README.md) |
| Anotação manual / κ / juiz piloto | [documentation/14_manual_annotation.md](documentation/14_manual_annotation.md) |
| Literatura | [references/](references/) |

Artefatos numéricos: `outputs/{run_id}/`, `outputs/campaigns/` (local, gitignored).
