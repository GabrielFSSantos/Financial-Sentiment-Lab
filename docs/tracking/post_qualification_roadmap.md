# Roadmap pós-qualificação (após 04/11/2026)

Itens **fora do escopo** da entrega de qualificação ([qualification_plan](qualification_plan_2026-11-04.md) §1.3), mas alinhados a [part-06](../research_trail/part-06-next-cycle.md).

## Prioridade sugerida

| # | Tema | Entregável | Docs / código |
| --- | --- | --- | --- |
| 1 | Gate κ / acurácia | Amostra ampliada ou estratificada; relatório fechado | `evaluation/classifier_eval_pt.py`, [12_regras](../documentation/12_regras_de_negocio.md) |
| 2 | LLM-as-judge batch | Substituir `LlmJudgeStub`; CSV piloto → produção | [annotation_protocol](annotation_protocol.md) §7, `evaluation/judges/` |
| 3 | Out-of-sample temporal | Janela futura pré-registrada vs B3 | [part-06](../research_trail/part-06-next-cycle.md), nova campanha YAML |
| 4 | Painel setorial | Copasa/Sanepar com protocolo idêntico | [06_configuracoes](../documentation/06_configuracoes.md), overlay `configs/campaigns/` |
| 5 | Controles de mercado | IBOV, volatilidade (H2 parcial) | `research` + `market` configs |
| 6 | Documentação viva | Atualizar [decision-register](../research_trail/decision-register.md) por ciclo | — |

## O que não reabrir sem novo protocolo

- Reinterpretar números da **Parte 4** como vitória definitiva de H1.
- Fine-tune / LoRA do FinBERT sem desenho pré-registrado.

## Sincronização

Marcos executados → checkbox em [qualification_schedule.md](qualification_schedule.md) (seção pós-quali, se criada) + linha em [decision-register](../research_trail/decision-register.md).
