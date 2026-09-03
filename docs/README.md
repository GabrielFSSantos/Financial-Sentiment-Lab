# Documentação — Financial Sentiment Lab

Entrada rápida na raiz: [README.md](../README.md).

## Documento principal

| Arquivo | Conteúdo |
| --- | --- |
| **[trajetoria.md](trajetoria.md)** | **Documento único da pesquisa** — enquadramento, ITI, fases F0–F6, **resultados (Parte 4)**, lacunas, próximo ciclo, apêndices |
| [documentacao.md](documentacao.md) | Referência técnica: módulos, fórmulas ITI, configs, research |
| [referencias/](referencias/) | Bibliografia, BibTeX, notas por artigo, PDFs |

## Ordem de leitura

1. [README § Entendendo a pesquisa](../README.md#entendendo-a-pesquisa)
2. [trajetoria.md](trajetoria.md) Partes 0–2 — problema, ITI, protocolo
3. [trajetoria.md Parte 4](trajetoria.md#parte-4--resultados-consolidados-trilha-a) — números oficiais Trilha A
4. [trajetoria.md Parte 3](trajetoria.md#parte-3--trajetória-por-fases) — storytelling por fase
5. [documentacao.md §1.5](documentacao.md#15-conceitos-em-linguagem-acessível) — fórmulas e baselines
6. [referencias/README.md](referencias/README.md) — artigos âncora

## Manutenção

- Novo protocolo ou fase → atualizar `trajetoria.md` (Partes 3 e 4) + `documentacao.md` se necessário
- Nova literatura → `referencias/` + citação na fase correspondente
- PDFs → `./scripts/download_referencias.sh` (ou colocar manualmente em `referencias/pdfs/`)

Artefatos numéricos em `outputs/{run_id}/` e `outputs/campaigns/`.
