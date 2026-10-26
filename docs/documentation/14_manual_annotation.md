# Anotação manual e avaliação do classificador (PT)

Controla a **qualidade do sinal** (FinBERT-PT-BR e variantes), não o treino de um novo classificador.

## Dados canônicos

| Artefato | Caminho |
| --- | --- |
| Rótulos (wide) | `data/water_utilities_corpus/manual_labels_100.csv` |
| Rótulos (long, multianotador) | `data/water_utilities_corpus/annotations_long.csv` |
| Corpus | `data/water_utilities_corpus/articles_strict_sabesp.csv` |

**Pergunta de anotação:** com **título + texto**, o fato é favorável, desfavorável ou neutro **para a empresa-alvo** (Sabesp)? Classes: `POSITIVE`, `NEGATIVE`, `NEUTRAL`.

**Entrada dos modelos:** `text_compose` (`titulo` + `\n\n` + `noticia`) em `configs/campaigns/datasets.yaml`.

## Governança (DR-016)

| Regra | Descrição |
| --- | --- |
| Avaliadores | Meta de **≥3** especialistas em economia/finanças, avaliação independente e cega |
| Consenso | Maioria simples; empate 1-1-1 com três classes → adjudicação documentada |
| Subconjunto IAA | Mesmos `news_id` entre pares de especialistas quando aplicável |
| Rodadas do mestrando | Diagnóstico histórico — **não** gold definitivo |
| LLM juiz | Piloto opcional (DR-007); **não** integra consenso humano |

Importar exportações de planilha para os CSV canônicos preservando colunas por anotador e `annotations_long.csv`.

## Métricas

| Situação | Métrica | Referência |
|----------|---------|------------|
| 2 anotadores | Cohen κ, % acordo | Cohen (1960); Artstein e Poesio (2008) |
| ≥3 anotadores no mesmo item | κ de Fleiss | Fleiss (1971) — ver nota em `references/notas/fleiss1971.md` |
| Humano × FinBERT | Acurácia, κ (N explícito) | Gate operacional DR-006: ~70% ou κ≥0,40 no corpus de saneamento |

IAA humana ≠ concordância humano×modelo.

## Comandos

```bash
python -m modules.evaluation classifier-pt prepare
python -m modules.evaluation classifier-pt run
python -m modules.evaluation llm-judge-pilot --limit 10 --mock   # opcional
```

### ITI-v2 (pacote cego, P06)

```bash
./scripts/campaigns/iti_v2.sh export-annotation-blind
python -m modules.evaluation.manual_labels import-blind \
  --responses <planilha.csv> --manual data/water_utilities_corpus/manual_labels_100.csv \
  --output data/water_utilities_corpus/manual_labels_import.csv
```

Saída padrão: `outputs/campaigns/iti_v2/annotation_blind_pack/`.

Narrativa: [part-04 §4.4](../research_trail/part-04-results.md) · DRs: [decision-register.md](../research_trail/decision-register.md). **Créditos por nome:** [CONTRIBUTORS.md](../../CONTRIBUTORS.md) e manuscrito em `docs/Dissertacao_PPGCC/` (agradecimentos e apêndice de anotação).

## Próxima avaliação (recorte contextual)

A campanha ITI-v2 usa `entity_context_v1` como view primária; a amostra de κ reportada na qualificação segue **título + corpo** (`text_compose`). Após merge da referência independente (P06), recalcular FinBERT × humano **no mesmo recorte contextual** que alimenta o ITI-H7, com N e protocolo documentados, antes de usar κ como gate de validade do sinal temporal.
