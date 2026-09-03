# Financial Sentiment Lab

Laboratório de **análise de sentimento em notícias financeiras** (PT e EN) para construir o **Índice Temporal Informacional (ITI)** e validar se sinais informacionais se associam a retornos de mercado.

A pesquisa parte de notícias (datasets versionados ou coletados por scraper), aplica modelos FinBERT, agrega impacto por empresa/setor/mercado e compara o ITI com baselines simples e preços B3 via validação estatística incremental.

- **Documento único da pesquisa (Trilha A):** [docs/trajetoria.md](docs/trajetoria.md) — Parte 4 = resultados oficiais
- **Referência técnica:** [docs/documentacao.md](docs/documentacao.md)
- **Bibliografia:** [docs/referencias/](docs/referencias/)

---

## Entendendo a pesquisa

A hipótese central é que o sentimento agregado em notícias sobre uma empresa, transformado em um índice com memória no tempo (ITI — *Information Trend Index*), pode se associar ao movimento futuro da ação melhor do que alternativas simples feitas com as mesmas notícias.

O fluxo usa três fontes de dado distintas. As **notícias** vêm do nosso scraper ou de datasets versionados. O **sentimento** é inferido por modelos FinBERT (probabilidades por notícia). Os **preços** da B3 são baixados da internet (yfinance) e salvos em `data/market/prices.csv`. O ITI e os baselines B0–B3 são calculados apenas a partir das notícias; o mercado entra como **alvo** — medimos se o índice da semana correlaciona com o retorno futuro da ação (ex.: SBSP3).

O índice é atualizado **todo dia** (EWMA — *Exponentially Weighted Moving Average*). Na validação semanal da campanha Sabesp, usamos um ponto por semana (valor do último dia útil, `iti_liquido_last`). Cada run da campanha gera 24 comparações: o ITI contra quatro baselines internos, em duas métricas de correlação (Pearson, Spearman) e três horizontes (1, 2 e 4 semanas). O **win rate** (taxa de vitória) indica em quantas dessas comparações o ITI supera o baseline.

Para conceitos detalhados e fórmulas, veja [docs/documentacao.md §1.5](docs/documentacao.md#15-conceitos-em-linguagem-acessível). Para o histórico run a run, veja [docs/trajetoria.md](docs/trajetoria.md).

---

## O que a pesquisa produz

1. **Sentimento por notícia** — classes `POSITIVE`, `NEGATIVE`, `NEUTRAL` e score contínuo `d = P(pos) − P(neg)`.
2. **ITI diário** — séries `iti_liquido` e `iti_risco` com memória EWMA por empresa (e agregados setor/mercado).
3. **Baselines B0–B3** — contagem de notícias, sentimento médio, sentimento ponderado por confiança e impacto diário sem memória.
4. **Validação research** — correlação e deltas ITI vs baselines contra retornos futuros, com bootstrap em bloco. Modo padrão: horizontes **1, 5 e 21 dias** (`configs/research.yaml`). Campanhas semanais (ex.: Sabesp): horizontes **1, 2 e 4 semanas** (`configs/campaigns/sabesp_2026/research_weekly.yaml`).

Saídas principais em `outputs/{run_id}/`:

```text
indices/{model}/{dataset}/iti_daily.csv      # ITI e baselines
research/.../aligned_panel.csv               # painel alinhado com mercado
research/research_summary.json               # conclusão estatística
```

---

## Requisitos

- **Python 3.10 a 3.14** (o `setup_env.sh` escolhe automaticamente o melhor disponível)
- Opcional: variável `PYTHON` para fixar o interpretador (ex.: `PYTHON=/usr/bin/python3.12 ./scripts/setup_env.sh`)
- PyTorch **CPU ou CUDA** é instalado automaticamente conforme detecção de GPU NVIDIA

---

## Primeira execução

```bash
git clone <repo>
cd financial-sentiment-lab
chmod +x scripts/*.sh modules/*/scripts/*.sh

./scripts/setup_env.sh --fetch-assets   # venv + modelos/datasets dos YAMLs
./scripts/audit_project.sh              # pytest + dry-run
./scripts/run_experiment.sh               # todas as combinações enabled
```

O `run_experiment.sh` **não baixa assets** em runtime. Se faltar modelo ou dataset, o preflight indica `./scripts/setup_env.sh --fetch-assets`.

Por padrão roda **combinações `enabled: true`** em `configs/models.yaml` × `configs/datasets.yaml`, respeitando idioma (PT/EN).

---

## Comandos essenciais

### Experimento (inferência + ITI)

```bash
# Todas as combinações enabled
./scripts/run_experiment.sh

# Uma combinação específica
./scripts/run_experiment.sh --model finbert_ptbr --dataset saneamento_corpus

# Run ID fixo
./scripts/run_experiment.sh --run-id meu_experimento --model finbert_ptbr --dataset noticias_exemplo_ptbr

# Sem recriar venv (útil após setup inicial)
./scripts/run_experiment.sh --skip-setup
```

### Scraper → corpus de saneamento

```bash
# Ponto de entrada unificado do módulo
./modules/scrapers/scripts/run_scrape.sh historical --since 2023-11-01 --until 2024-04-30
./modules/scrapers/scripts/run_scrape.sh smoke --site valor --since 2023-11-01 --until 2023-11-30
./modules/scrapers/scripts/run_scrape.sh once --since 2024-01-01 --until 2024-03-31 --use-state
./modules/scrapers/scripts/run_scrape.sh build-corpus
./modules/scrapers/scripts/run_scrape.sh report
./modules/scrapers/scripts/run_scrape.sh debug-search --site valor --since 2023-11-01 --until 2023-11-30 --query Sabesp

# Wrappers de compatibilidade na raiz (delegam ao run_scrape.sh)
./scripts/scrape_historical.sh --since 2023-11-01 --until 2024-04-30
./scripts/scrape_smoke_site.sh exame 2023-11-01 2023-11-30
```

Saídas: `data/saneamento_corpus/noticias.csv` (empresa + ticker) e `noticias_pendentes.csv` (modo `broad`, revisão manual). Config: `configs/scrapers.yaml` (`collection_mode: broad`, 6 portais).

Nas primeiras coletas é comum o corpus ser dominado por uma empresa; ampliar Copasa/Sanepar exige janela temporal maior e múltiplos portais.

### Mercado (preços para research)

```bash
python -m modules.market fetch          # baixa tickers de configs/market.yaml
python -m modules.market fetch --force  # refetch
python -m modules.market check
```

### Research (validação científica)

```bash
# Verificar pré-requisitos (run + CSV de mercado válido)
python -m modules.research check --run-id <run_id>

# Validar (usa o run mais recente se --run-id omitido)
./scripts/run_research.sh --run-id <run_id>
python -m modules.research validate --run-id <run_id> --model finbert_ptbr --dataset saneamento_corpus
```

### Pipeline operacional (corpus próprio)

```bash
python -m modules.scrapers --since 2020-01-01 --until 2024-12-31
./modules/scrapers/scripts/run_scrape.sh build-corpus
python -m modules.market fetch
./scripts/run_experiment.sh --model finbert_ptbr --dataset saneamento_corpus
python -m modules.research validate --run-id <run_id>
```

---

## Configuração (YAML)

| Arquivo | Controle |
| --- | --- |
| [configs/experiment.yaml](configs/experiment.yaml) | ITI, agregação, baselines, execução. Preflight (`enabled` + validação de arquivos/diretório). `unload_model_after_combination` libera o modelo ao trocar de modelo ou ao terminar. |
| [configs/models.yaml](configs/models.yaml) | Modelos FinBERT, adaptadores, HuggingFace |
| [configs/datasets.yaml](configs/datasets.yaml) | Datasets, colunas, `limits.max_rows` |
| [configs/market.yaml](configs/market.yaml) | Tickers B3, fetch yfinance |
| [configs/research.yaml](configs/research.yaml) | Horizontes, baselines, métricas, bootstrap |
| [configs/scrapers.yaml](configs/scrapers.yaml) | Portais, queries, corpus |

Downloads isolados: `python -m modules.models fetch`, `python -m modules.datasets fetch|check|validate`.

Controles PT (`enabled: false`): `python -m modules.models fetch --model bertweet_pt_sentiment --model bertimbau_sentiment`. Dry-run sem baixar a matriz: `./scripts/run_experiment.sh --skip-setup --dry-run --model bertweet_pt_sentiment --dataset noticias_exemplo_ptbr` (idem `bertimbau_sentiment`).

---

## Referências — modelos

| Chave YAML | Repositório Hugging Face |
| --- | --- |
| `finbert_ptbr` | [lucas-leme/FinBERT-PT-BR](https://huggingface.co/lucas-leme/FinBERT-PT-BR) |
| `pt_br_financial_sentiment_analysis` | [lucasalmda/pt-br-financial-sentiment-analysis](https://huggingface.co/lucasalmda/pt-br-financial-sentiment-analysis) |
| `finbert_en` | [ProsusAI/finbert](https://huggingface.co/ProsusAI/finbert) |
| `finbert_tone_en` | [yiyanghkust/finbert-tone](https://huggingface.co/yiyanghkust/finbert-tone) |
| `bertweet_pt_sentiment` | [pysentimiento/bertweet-pt-sentiment](https://huggingface.co/pysentimiento/bertweet-pt-sentiment) (controle PT, `enabled: false`) |
| `bertimbau_sentiment` | [lipaoMai/bert-sentiment-model-portuguese](https://huggingface.co/lipaoMai/bert-sentiment-model-portuguese) (BERTimbau geral, `enabled: false`) |

---

## Referências — datasets

| Chave YAML | Origem |
| --- | --- |
| `noticias_exemplo_ptbr` | CSV versionado (`data/noticias_exemplo_ptbr/`) — exemplo PT com rótulos |
| `news_example_en` | CSV versionado (`data/news_example_en/`) — exemplo EN com rótulos |
| `saneamento_corpus` | Corpus multiportal gerado por `modules/scrapers` |

Tickers de mercado (research): Sabesp `SBSP3.SA`, Copasa `CSMG3.SA`, Sanepar `SAPR4.SA` — ver [configs/market.yaml](configs/market.yaml) e [configs/research.yaml](configs/research.yaml).

---

## Estrutura do repositório

```text
financial-sentiment-lab/
├── configs/           # YAML declarativo
├── data/              # exemplos versionados; demais via fetch/scraper
├── model_store/       # checkpoints locais
├── modules/
│   ├── experiment/    # inferência + ITI
│   ├── models/        # FinBERT e registry
│   ├── datasets/      # leitura e fetch de datasets
│   ├── market/        # preços yfinance
│   ├── research/      # validação ITI vs mercado
│   └── scrapers/      # coleta multiportal
├── scripts/           # entrypoints shell
├── outputs/           # runs do experimento e research
└── tests/
```
