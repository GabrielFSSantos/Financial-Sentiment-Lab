# Concordância entre anotadores (IAA)

## Métricas

| Situação | Métrica sugerida | Referência |
|----------|-----------------|------------|
| 2 anotadores, mesmas notícias | % acordo, κ de Cohen | Cohen (1960); Artstein e Poesio (2008) |
| ≥3 anotadores, mesmas notícias | κ de Fleiss | Fleiss (1971) — [nota](fleiss1971.md); **sem PDF local** (só DOI no `.bib`) |
| Avaliadores com taxas de erro distintas | Modelos latentes (discussão) | Dawid e Skene (1979) — [nota](dawidskene1979.md); não implementado nesta fase |

## Separação obrigatória

- **IAA humana** ≠ concordância humano × FinBERT ≠ concordância humano × LLM.
- Gate operacional 70% / κ≥0,40 (DR-006) é critério do projeto, não “padrão ouro” universal.

## Consolidação de rótulo (DR-016)

1. Avaliações independentes e cegas.
2. Maioria simples quando houver ≥2 votos na mesma classe.
3. Empate 1-1-1 com três avaliadores → adjudicação humana documentada.
4. Preservar rótulos individuais em `annotations_long.csv`.
5. Não usar média aritmética de códigos {-1,0,+1} como classe final.

## Implementação

Ver [14_manual_annotation.md](../../documentation/14_manual_annotation.md) e `python -m modules.evaluation classifier-pt`.
