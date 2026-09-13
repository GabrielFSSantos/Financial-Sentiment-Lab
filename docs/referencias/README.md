# Referências bibliográficas — Financial Sentiment Lab

Índice de artigos usados para ancorar decisões em [trajetoria.md](../trajetoria.md). BibTeX: [bibliografia.bib](bibliografia.bib). Notas: [notas/](notas/). Download: `./scripts/download_referencias.sh`.

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
| RACEf, Neuenschwander, Barbieri | link only | ver notas |

Log de download: [pdfs/download.log](pdfs/download.log). Reexecutar: `./scripts/download_referencias.sh` (pula arquivos já presentes).

## Como citar na trajetória

1. Ler [nota](notas/) antes de citar numa fase.
2. Indicar **o que tomamos** e **o que é diferente** no caso Sabesp/saneamento.
3. Decisão metodológica: tabela Decisão | Alternativa | Fundamento (artigo + `run_id`).
