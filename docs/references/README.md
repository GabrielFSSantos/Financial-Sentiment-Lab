# Referências bibliográficas — Financial Sentiment Lab

Índice de artigos usados para ancorar decisões em [research_trail](../research_trail/README.md). BibTeX: [bibliografia.bib](bibliografia.bib). Notas: [notas/](notas/). PDFs versionados em [pdfs/](pdfs/) (sem script de download no repo).

Convenção de arquivo: `autorANO_tema-curto.pdf` (minúsculas, sem IDs de OJS, DOI ou working paper).

## Três referências âncora metodológicas (BR)

| # | Referência | Uso no lab | PDF local |
|---|------------|------------|-----------|
| 1 | **Santos, Bianchi & Costa (2023)** — FinBERT-PT-BR | Classificador + índice de sentimento PT | [pdfs/santos2023_finbert_ptbr.pdf](pdfs/santos2023_finbert_ptbr.pdf) · [nota](notas/santos2023.md) |
| 2 | **Yoshinaga & Castro Junior (2012)** — índice sentimento × retorno BR | Precedente BR de índice testado contra retornos | [pdfs/yoshinaga2012_bar.pdf](pdfs/yoshinaga2012_bar.pdf) · [nota](notas/yoshinaga2012.md) |
| 3 | **Duarte, González & Cruz (2020)** — notícias × quedas B3 | Múltiplos horizontes; persistência da informação | [pdfs/duarte2020_quedas_b3.pdf](pdfs/duarte2020_quedas_b3.pdf) · [nota](notas/duarte2020.md) |

## Referências de suporte

| Referência | Uso | Acesso / PDF |
|------------|-----|--------------|
| Tetlock (2007) | Mídia e preços — H1 | [pdfs/tetlock2007_media.pdf](pdfs/tetlock2007_media.pdf) · [nota](notas/tetlock2007.md) |
| Loughran & McDonald (2011) | Baselines textuais | [pdfs/loughran2011_baselines.pdf](pdfs/loughran2011_baselines.pdf) · [nota](notas/loughran2011.md) |
| ERAMIARS (2025) — Marquezan & Assunção | Correlação emoções × preços B3 | [pdfs/marquezan2025_eramiars.pdf](pdfs/marquezan2025_eramiars.pdf) · [nota](notas/eramiars2025.md) |
| Baker et al. (2016) EPU | Índice textual temporal | [pdfs/baker2016_epu.pdf](pdfs/baker2016_epu.pdf) · [nota](notas/baker2016.md) |
| Shapiro et al. (2022) Fed | EWMA / decaimento | [pdfs/shapiro2022_news_sentiment.pdf](pdfs/shapiro2022_news_sentiment.pdf) · [nota](notas/shapiro2022.md) |
| RACEf (2022) | Sentimento × ciclos BR | [DOI](https://doi.org/10.13059/racef.v13i3.985) · link only · [nota](notas/racef2022.md) |
| UTFPR (2024) | Contraponto causalidade BERT | [pdfs/utfpr2024_noticias_acoes.pdf](pdfs/utfpr2024_noticias_acoes.pdf) · [nota](notas/utfpr2024.md) |
| FOCO (2025) — Gattai & Souza | Evento institucional Sabesp/EQTL3 | [pdfs/gattai2025_privatizacao_sabesp.pdf](pdfs/gattai2025_privatizacao_sabesp.pdf) · [nota](notas/foco2025.md) |
| Araci (2020) FinBERT EN | Contexto transformers | [pdfs/araci2020_finbert.pdf](pdfs/araci2020_finbert.pdf) · [nota](notas/araci2020.md) |
| Souza et al. (2020) BERTimbau | Base linguística PT | [pdfs/souza2020_bertimbau.pdf](pdfs/souza2020_bertimbau.pdf) · [nota](notas/souza2020.md) |
| Barbieri (2020) BERTweet | Controle κ | [nota](notas/barbieri2020.md) |
| Neuenschwander et al. (2014) | Scraping BR difícil | link only · [nota](notas/neuenschwander2014.md) |
| Lei 14.026/2020 | Marco legal do saneamento | [pdfs/brasil2020_lei_14026.pdf](pdfs/brasil2020_lei_14026.pdf) |

## Rotulação / entity sentiment

Mapa decisão ↔ literatura: notas abaixo + [14_manual_annotation.md](../documentation/14_manual_annotation.md).

| Referência | Nota | PDF |
|------------|------|-----|
| Yuan et al. (2020) target-based | [yuan2020.md](notas/yuan2020.md) | [yuan2020_target_financial.pdf](pdfs/yuan2020_target_financial.pdf) |
| Sinha et al. (2022) SEntFiN | [sinha2022_sentfin.md](notas/sinha2022_sentfin.md) | [sinha2022_sentfin.pdf](pdfs/sinha2022_sentfin.pdf) |
| Daudert (2022) FinLin | [daudert2022_finlin.md](notas/daudert2022_finlin.md) | [daudert2022_finlin.pdf](pdfs/daudert2022_finlin.pdf) ou [DOI Springer](https://doi.org/10.1007/s10579-021-09555-3) |
| Aguda et al. (2024) LLM anotador | [aguda2024.md](notas/aguda2024.md) | [aguda2024_llm_annotators.pdf](pdfs/aguda2024_llm_annotators.pdf) |
| Malo (2014) PhraseBank | [malo2014_phrasebank.md](notas/malo2014_phrasebank.md) | [malo2014_phrasebank.pdf](pdfs/malo2014_phrasebank.pdf) |
| Artstein & Poesio (2008) IAA | [artstein2008.md](notas/artstein2008.md) | [artstein2008_intercoder.pdf](pdfs/artstein2008_intercoder.pdf) |
| Cohen (1960) κ | [cohen1960.md](notas/cohen1960.md) | [cohen1960_kappa.pdf](pdfs/cohen1960_kappa.pdf) |
| Cortis et al. (2017) SemEval-5 | [cortis2017_semeval5.md](notas/cortis2017_semeval5.md) | [cortis2017_semeval5.pdf](pdfs/cortis2017_semeval5.pdf) |
| Tang et al. (2023) FinEntity | [tang2023_finentity.md](notas/tang2023_finentity.md) | [tang2023_finentity.pdf](pdfs/tang2023_finentity.pdf) |
| Zheng et al. (2023) LLM-judge | [zheng2023.md](notas/zheng2023.md) | [zheng2023_llm_judge.pdf](pdfs/zheng2023_llm_judge.pdf) |

## Status dos PDFs locais (`pdfs/`)

| Arquivo | Status | Referência |
|---------|--------|------------|
| `santos2023_finbert_ptbr.pdf` | OK | Santos et al. (2023) |
| `duarte2020_quedas_b3.pdf` | OK | Duarte et al. (2020) |
| `tetlock2007_media.pdf` | OK | Tetlock (2007) |
| `loughran2011_baselines.pdf` | OK | Loughran & McDonald (2011) |
| `yoshinaga2012_bar.pdf` | OK | Yoshinaga & Castro Junior (2012) |
| `gattai2025_privatizacao_sabesp.pdf` | OK | Gattai & Souza (2025) FOCO |
| `araci2020_finbert.pdf` | OK | Araci (2020) |
| `marquezan2025_eramiars.pdf` | OK | Marquezan & Assunção (2025) |
| `baker2016_epu.pdf` | OK | Baker, Bloom & Davis (2016) |
| `souza2020_bertimbau.pdf` | OK | Souza et al. (2020) |
| `brasil2020_lei_14026.pdf` | OK | Lei 14.026/2020 |
| `utfpr2024_noticias_acoes.pdf` | OK | UTFPR (2024) |
| `shapiro2022_news_sentiment.pdf` | OK | Shapiro et al. (working paper Fed; versão jornal 2022) |
| `yuan2020_target_financial.pdf` | OK | Yuan et al. (2020) |
| `sinha2022_sentfin.pdf` | OK | Sinha et al. (2022) pré-print |
| `daudert2022_finlin.pdf` | OK | Daudert (2022) FinLin |
| `cohen1960_kappa.pdf` | OK | Cohen (1960) |
| `aguda2024_llm_annotators.pdf` | OK | Aguda et al. (2024) |
| `malo2014_phrasebank.pdf` | OK | Malo et al. (2014) |
| `artstein2008_intercoder.pdf` | OK | Artstein & Poesio (2008) |
| `zheng2023_llm_judge.pdf` | OK | Zheng et al. (2023) |
| `cortis2017_semeval5.pdf` | OK | Cortis et al. (2017) |
| `tang2023_finentity.pdf` | OK | Tang et al. (2023) |
| RACEf, Neuenschwander, Barbieri | link only | ver notas |

## Como citar na trajetória

1. Ler [nota](notas/) antes de citar numa fase.
2. Indicar **o que tomamos** e **o que é diferente** no caso Sabesp/saneamento.
3. Decisão metodológica: tabela Decisão | Alternativa | Fundamento (artigo + `run_id`).

## Mapa artigo → fase → documentação

| Referência (nota) | Fase research_trail | Capítulo documentation |
| --- | --- | --- |
| Santos (2023) | F2 classificação, F0 corpus | [04_iti_formulas](../documentation/04_iti_formulas.md), [03_modules §3.1](../documentation/03_modules.md) |
| Yoshinaga (2012) | F1 protocolo | [05_research_validation](../documentation/05_research_validation.md), part-02 |
| Duarte (2020) | F1 horizontes | [05_research_validation](../documentation/05_research_validation.md), [12_business_rules §12.4](../documentation/12_business_rules.md) |
| Loughran (2011) | F2 baselines B0–B3 | [04_iti_formulas](../documentation/04_iti_formulas.md) §4.3 |
| Shapiro (2022) | F2 α EWMA | [04_iti_formulas](../documentation/04_iti_formulas.md), part-01 |
| Gattai (2025) | F4 evento | part-03 F4, [06_configuration](../documentation/06_configuration.md) |
| Tetlock (2007) | F0 enquadramento | part-00, [01_visao](../documentation/01_vision_and_concepts.md) |
| Marquezan (2025) | F1 lags | part-02, [05_validacao](../documentation/05_research_validation.md) |

Registro de decisões derivadas: [decision-register.md](../research_trail/decision-register.md).
