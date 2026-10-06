# LLM-as-judge (modelo de linguagem como juiz)

## Uso no Financial Sentiment Lab (qualificação)

**Objetivo:** segunda opinião automatizada na classificação de notícias **para a Sabesp** (POSITIVE / NEGATIVE / NEUTRAL), com **prompt fixo** e registro em CSV — triangulação com anotação humana e FinBERT, **não** substituto de especialista nem gold standard de mercado.

**Onde está operacionalizado:** [annotation_protocol_v2.md](../../tracking/annotation_protocol_v2.md) §7 · piloto semana 2 no [qualification_schedule.md](../../tracking/qualification_schedule.md).

**Saída sugerida:** `outputs/campaigns/llm_judge_pilot/llm_judge_pilot.csv`

## Ideia geral (literatura)

Em avaliação de sistemas de linguagem natural, é comum usar um **modelo grande** para julgar saídas ou rótulos (por exemplo, comparar duas classificações ou verificar critérios em texto). Na qualificação usamos essa ideia de forma **exploratória** e **documentada**, ciente de vieses e alucinações.

Referências para incluir na dissertação posteriormente (buscar versão final e página):

- Zheng, L. et al. — *Judging LLM-as-a-Judge* (arXiv, 2023) — enquadramento de LLM como avaliador.
- Artstein & Poesio (2008) — concordância entre anotadores humanos (complementar, não é LLM).

## O que tomamos / o que não tomamos

| Tomamos | Não tomamos |
|---------|-------------|
| Prompt reprodutível em português | LLM como única verdade |
| Subconjunto pequeno (10–20 notícias) | Treinar ou calibrar ITI só com juiz LLM |
| Discordâncias como material qualitativo | Afirmar κ “bom” na qualificação |

## Decisão

| Decisão | Alternativa | Fundamento |
|---------|-------------|------------|
| Piloto LLM-judge na qualificação | Só humano solo | Orientador 06/10/2026 — mitigar crítica a anotador não especialista |
| Prompt fixo `prompt_v1_quali` | Prompt ad hoc por notícia | Reprodutibilidade |
