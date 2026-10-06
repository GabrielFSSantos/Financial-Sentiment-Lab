# Documentação — Financial Sentiment Lab

Entrada na raiz do repositório: [README.md](../README.md).

## Três pilares

| Pasta | Papel |
| --- | --- |
| **[research_trail/](research_trail/README.md)** | Histórico completo — decisões, fases F0–F6, runs, **Parte 4 = números oficiais** |
| **[documentation/](documentation/README.md)** | Código e operação — módulos, fórmulas, regras de negócio, fluxos, testes |
| **[tracking/](tracking/README.md)** | Qualificação (04/11/2026), protocolo de anotação, pós-qualificação |

## Público-alvo

| Leitor | Começar por |
| --- | --- |
| **Desenvolvedor** | [documentation/13_guia_leitura_dev_e_agente.md](documentation/13_guia_leitura_dev_e_agente.md) → [11_fluxo_ponta_a_ponta.md](documentation/11_fluxo_ponta_a_ponta.md) |
| **Agente (IA)** | [13_guia_leitura_dev_e_agente.md](documentation/13_guia_leitura_dev_e_agente.md) → [10_arquitetura_e_manutencao.md](documentation/10_arquitetura_e_manutencao.md) → [12_regras_de_negocio.md](documentation/12_regras_de_negocio.md) |
| **Pesquisador / banca** | [research_trail/](research_trail/README.md) Partes 0–4 · [tracking/qualification_schedule.md](tracking/qualification_schedule.md) |
| **Operação cluster** | [documentation/07_santos_dumont.md](documentation/07_santos_dumont.md) |

**Entrada rápida:** [Parte 4 (números)](research_trail/part-04-results.md) · [quickstart](documentation/00_quickstart_researcher.md) · [decision-register](research_trail/decision-register.md)

**Idioma:** código e paths em inglês; documentação ao pesquisador em PT-BR — [CONTRIBUTING.md](../CONTRIBUTING.md#idioma).

## Outros

| Caminho | Conteúdo |
| --- | --- |
| [references/](references/) | Bibliografia, BibTeX, notas por artigo |
| [Dissertacao_PPGCC/](Dissertacao_PPGCC/) | Manuscrito LaTeX (qualificação / defesa) |

## Ordem de leitura sugerida (pesquisa)

1. [README § Entendendo a pesquisa](../README.md#entendendo-a-pesquisa)
2. [research_trail Partes 0–2](research_trail/part-00-framing.md)
3. [research_trail Parte 4](research_trail/part-04-results.md)
4. [research_trail Parte 3](research_trail/part-03-phases.md)
5. [documentation §1.5](documentation/01_visao_e_conceitos.md#15-conceitos-em-linguagem-acessível)
6. [references/README.md](references/README.md)

## Manutenção (matriz ampliada)

| Tipo de mudança | Onde documentar |
| --- | --- |
| Fase F*, run oficial, decisão metodológica | [research_trail/part-03](research_trail/part-03-phases.md) + [decision-register](research_trail/decision-register.md) |
| Regra de negócio (duelos, gates, dry-run) | [documentation/12_regras_de_negocio.md](documentation/12_regras_de_negocio.md) |
| Módulo, fluxo, contrato CSV | [documentation/03_modulos.md](documentation/03_modulos.md), [appendix_output_contract](documentation/appendix_output_contract.md) |
| Fórmula ITI ↔ código | [documentation/04_formulas_iti.md](documentation/04_formulas_iti.md) |
| YAML / campanha | [documentation/06_configuracoes.md](documentation/06_configuracoes.md) |
| Teste novo | [documentation/09_testes.md](documentation/09_testes.md) |
| Marco qualificação / anotação | [tracking/](tracking/qualification_schedule.md) |
| Literatura | [references/](references/) |

Artefatos numéricos: `outputs/{run_id}/`, `outputs/campaigns/`.
