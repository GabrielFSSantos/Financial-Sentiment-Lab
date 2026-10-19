# Santos, Bianchi e Costa (2023) — FinBERT-PT-BR

**Chave BibTeX:** `santos2023finbert`  
**PDF:** `docs/references/pdfs/` (BWAIF/SBC)

## Uso neste laboratório

- Modelo candidato ao escore \(d = P(+)-P(-)\) por notícia.
- **Antecedente metodológico:** três anotadores, ≥2 labels por texto, exclusão por discordância/inaplicabilidade, alta concordância no conjunto final filtrado.
- **Índice dos autores:** diferença normalizada entre contagens de notícias positivas e negativas — genealogia conceitual distinta do ITI (escore probabilístico + EWMA por empresa).

## Diferenças do nosso desenho

| Aspecto | Santos et al. | Financial Sentiment Lab |
|---------|---------------|-------------------------|
| Domínio | Notícias financeiras PT (treino) | Saneamento / Sabesp |
| Unidade textual | Sentenças curtas | Notícia (título + corpo, `text_compose`; limite 512 tokens BERT) |
| Referência humana | Equipe de anotação do artigo | Especialistas economia/finanças (DR-016) |
| Objetivo do gold | Treinar/avaliar classificador | Controlar qualidade do sinal do **ITI** |

## Citação na dissertação

Cap. revisão (NLP PT), cap. metodologia (entrada textual e limitação de truncamento), cap. proposta (contraste índice contagem vs ITI).
