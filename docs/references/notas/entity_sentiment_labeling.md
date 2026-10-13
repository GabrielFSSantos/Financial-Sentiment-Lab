# Rotulação orientada a entidade — base bibliográfica (qualificação)

Índice para responder ao pedido de precedentes (avaliadores, escopo, LLM) na conversa com Raphael e no capítulo de metodologia. Protocolo operacional: [`annotation_protocol.md`](../../tracking/annotation_protocol.md). Decisões: DR-006, DR-007, DR-012 em [`decision-register.md`](../../research_trail/decision-register.md).

**Âncora domínio PT:** [santos2023.md](santos2023.md) (503 notícias anotadas, FinBERT-PT-BR).

---

## Mapa decisão ↔ literatura

| Decisão no lab | Alternativa rejeitada | Fundamento |
|----------------|----------------------|------------|
| Unidade `(notícia, empresa-alvo)` e campo `impacto_alvo` | Sentimento global da manchete | [yuan2020](yuan2020.md), [sinha2022_sentfin](sinha2022_sentfin.md), [cortis2017_semeval5](cortis2017_semeval5.md) |
| n=100 notícias Sabesp (estratificada) | Gold definitivo de mercado na qualificação | Escala menor que corpora SEntFiN/Yuan; **validar pipeline** (DR-006); precedente de centenas em [santos2023](santos2023.md) |
| IAA: piloto ~30 → expandir com Raphael | Um único anotador sem concordância | Yuan (2+3º); SEntFiN (3+curador); [artstein2008](artstein2008.md) |
| κ de Cohen + acurácia vs modelos | Usar κ humano×FinBERT como “concordância entre humanos” | [cohen1960](cohen1960.md), [landis1977](landis1977.md) via Artstein; gate 0,40 em regras de negócio — diagnóstico |
| Anotador sem certificação CVM | Só analista profissional | SEntFiN, FinEntity, PhraseBank: formação/treinamento + protocolo ([malo2014_phrasebank](malo2014_phrasebank.md), [tang2023_finentity](tang2023_finentity.md)) |
| LLM piloto (prompt fixo) | LLM como gold ou único juiz | [aguda2024](aguda2024.md), [llm_judge](llm_judge.md); Zheng para juiz formal |
| FinBERT como referência automática | FinBERT = verdade | [santos2023](santos2023.md); desempenho no saneamento abaixo do artigo (48%, κ≈0,16 exploratório) |

---

## Quatro âncoras para Raphael

1. **[Yuan et al. 2020](yuan2020.md)** — target-based em notícias financeiras; 2 anotadores + 3º em divergência; κ reportado ~0,72.
2. **[SEntFiN (Sinha et al. 2022)](sinha2022_sentfin.md)** — manchetes multi-entidade; 3 anotadores + curador; ~2,8k headlines com entidades conflitantes.
3. **[FinLin (Daudert 2022)](daudert2022_finlin.md)** — sentimento por entidade, relevância e **trechos de evidência**; 3+1 especialistas.
4. **[Aguda et al. 2024](aguda2024.md)** — LLMs vs especialistas vs crowd em finanças; uso complementar, não substituto do humano.

Complementares: [malo2014_phrasebank](malo2014_phrasebank.md), [tang2023_finentity](tang2023_finentity.md), [artstein2008](artstein2008.md), [cohen1960](cohen1960.md).

---

## PDFs locais e download manual

Convenção: `docs/references/pdfs/autorANO_tema.pdf`. Script: `./scripts/download_references.sh`.

| Arquivo | Status após script | Se falhar, baixar manualmente |
|---------|-------------------|-------------------------------|
| `yuan2020_target_financial.pdf` | ACL | https://aclanthology.org/2020.lrec-1.620.pdf |
| `sinha2022_sentfin.pdf` | arXiv | https://arxiv.org/pdf/2305.12257.pdf |
| `daudert2022_finlin.pdf` | OK (manual Springer) | https://doi.org/10.1007/s10579-021-09555-3 |
| `aguda2024_llm_annotators.pdf` | ACL | https://aclanthology.org/2024.lrec-main.885.pdf |
| `malo2014_phrasebank.pdf` | ver script | https://arxiv.org/pdf/1307.5336.pdf (pré-print relacionado) |
| `artstein2008_intercoder.pdf` | ACL | https://aclanthology.org/J08-4004.pdf |
| `zheng2023_llm_judge.pdf` | arXiv | https://arxiv.org/pdf/2306.05685.pdf |
| `cortis2017_semeval5.pdf` | ACL | https://aclanthology.org/S17-2082.pdf |
| `tang2023_finentity.pdf` | ACL/arXiv | https://aclanthology.org/2023.emnlp-main.956.pdf |
| `cohen1960_kappa.pdf` | OK (manual Sage) | DOI 10.1177/001316446002000104 |
| `sinha2022_sentfin_jasist.pdf` | — | DOI 10.1002/asi.24634 (Wiley) |

---

## Parágrafo modelo (metodologia / e-mail)

> Para consolidar a amostra de referência, a unidade de anotação foi definida pelo par notícia–empresa-alvo (Sabesp). Cada notícia é avaliada segundo um protocolo comum de impacto informacional positivo, neutro ou negativo para a empresa-alvo, em linha com corpora de sentimento financeiro orientados a entidade (Yuan et al., 2020; Sinha et al., 2022). As instruções enfatizam o efeito descrito no texto para a Sabesp, e não o tom global da matéria. A concordância entre anotadores humanos é mensurada separadamente do desempenho do FinBERT-PT-BR e de um modelo de linguagem usado como anotador automatizado independente (Aguda et al., 2024), com prompt fixo e escopo de piloto na qualificação. A amostra de cem notícias serve, nesta fase, para validar o fluxo de anotação e avaliação do classificador, sem fechar o gate de κ como resultado final de mercado (DR-006).

---

## Perguntas abertas para alinhar com Raphael

- Piloto de **20–30** notícias para calibrar protocolo vs. IAA nas **100** completas?
- Quem pode atuar como **terceiro adjudicador** em divergências Gabriel × Raphael?
- LLM nas **100** ou manter **10–20** casos difíceis na qualificação (custo/GPU)?
