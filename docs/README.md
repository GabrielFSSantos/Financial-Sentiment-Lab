# Documentação — Financial Sentiment Lab

Entrada rápida na raiz: [README.md](../README.md).

## Documentos

| Arquivo | Conteúdo |
| --- | --- |
| [documentacao.md](documentacao.md) | Referência técnica: módulos, ITI, configs, research, testes |
| [trajetoria.md](trajetoria.md) | Histórico experimental run a run (Marcos 0–5) |
| [sintese_trilha_a.md](sintese_trilha_a.md) | **Fechamento Trilha A** — resultados, limitações, redação da tese |

## Ordem de leitura

1. [README § Entendendo a pesquisa](../README.md#entendendo-a-pesquisa) — visão em 2 minutos
2. [sintese_trilha_a.md](sintese_trilha_a.md) — onde a pesquisa chegou e o que concluir
3. [documentacao.md §1.5](documentacao.md#15-conceitos-em-linguagem-acessível) — ITI, baselines, 24 comparações
4. [trajetoria.md](trajetoria.md) — detalhe por run, quando precisar auditar números

## Artefatos numéricos

Resultados versionados em `outputs/{run_id}/`. Resumos de campanha em `outputs/campaigns/`. Configs descartáveis pós-tese: `configs/campaigns/`, `scripts/campaigns/`.

Ao mudar protocolo, atualize [documentacao.md](documentacao.md) e [trajetoria.md](trajetoria.md). Ao fechar uma fase, atualize [sintese_trilha_a.md](sintese_trilha_a.md).
