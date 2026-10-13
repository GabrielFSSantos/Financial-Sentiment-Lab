# Anotação manual e avaliação do classificador (PT)

Amostra formal para validar o pipeline de rótulos (DR-006, DR-012): **não** é gold de mercado nem meta fechada de κ na qualificação.

## Dados canônicos

| Artefato | Caminho |
| --- | --- |
| Rótulos | `data/water_utilities_corpus/manual_labels_100.csv` |
| Corpus (contexto) | `data/water_utilities_corpus/articles_strict_sabesp.csv` |
| Config | `configs/evaluation.yaml` |

Colunas principais: `news_id`, `empresa_alvo`, `tipologia`, `impacto_alvo` (positivo/neutro/negativo para a empresa-alvo), `rotulo_finbert`, `rotulo_llm_juiz` (piloto), `versao_protocolo`, `caso_ambiguo`, `notas`.

Aliases de coluna para métricas: `column_aliases` em `configs/evaluation.yaml`.

## Comandos

```bash
# Bateria PT (prepare → run → gate opcional)
python -m modules.evaluation classifier-pt prepare
python -m modules.evaluation classifier-pt run

# Comparar amostra manual vs predictions (via módulo manual_labels)
python -m modules.evaluation.manual_labels compare --predictions CAMINHO_PRED.csv

# Piloto LLM-as-judge (mock ou GPU)
python -m modules.evaluation llm-judge-pilot --limit 10 --mock
```

Saídas típicas: `outputs/campaigns/classifier_eval_pt/`, `outputs/campaigns/llm_judge_pilot/`.

## Fundamentação bibliográfica

Notas por artigo em [`references/notas/`](../references/notas/) (Yuan, SEntFiN, Aguda, Cohen, Artstein, etc.). Índice: [`references/README.md`](../references/README.md).

## Narrativa e números

Linha do tempo e resultados: [part-04 §4.4](../research_trail/part-04-results.md). Regras de gate: [12_business_rules.md](12_business_rules.md) §12.6.
