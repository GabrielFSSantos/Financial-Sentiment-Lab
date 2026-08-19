# Financial Sentiment Lab

Laboratório de **análise de sentimento em notícias financeiras** (PT e EN) para construir o **Índice Temporal Informacional (ITI)** e validar se sinais informacionais se associam a retornos de mercado.

A pesquisa parte de notícias (datasets versionados, filtrados ou coletados por scraper), aplica modelos FinBERT, agrega impacto por empresa/setor/mercado e compara o ITI com baselines simples e preços B3 via validação estatística incremental.

Documentação técnica completa (módulos, fluxos, fórmulas): **[DOCUMENTACAO.md](DOCUMENTACAO.md)**.

---

## O que a pesquisa produz

1. **Sentimento por notícia** — classes `POSITIVE`, `NEGATIVE`, `NEUTRAL` e score contínuo `d = P(pos) − P(neg)`.
2. **ITI diário** — séries `iti_liquido` e `iti_risco` com memória EWMA por empresa (e agregados setor/mercado).
3. **Baselines B0–B3** — contagem de notícias, sentimento médio, sentimento ponderado por confiança e impacto diário sem memória.
4. **Validação research** — correlação e deltas ITI vs baselines contra retornos futuros (horizontes 1, 5 e 21 dias), com bootstrap em bloco.

Saídas principais em `outputs/{run_id}/`:

```text
indices/{model}/{dataset}/iti_daily.csv      # ITI e baselines
research/.../aligned_panel.csv               # painel alinhado com mercado
research/research_summary.json               # conclusão estatística
```

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
./scripts/run_experiment.sh --run-id meu_experimento --model finbert_ptbr --dataset noticias_exemplo

# Sem recriar venv (útil após setup inicial)
./scripts/run_experiment.sh --skip-setup
```

### Scraper → corpus de saneamento

```bash
# Coleta (sites habilitados em configs/scrapers.yaml)
python -m modules.scrapers --since 2020-01-01 --until 2024-12-31
python -m modules.scrapers --since 2024-01-01 --site infomoney   # um portal

# Mescla raw/ → data/saneamento_corpus/noticias.csv
bash modules/scrapers/scripts/build_corpus.sh
```

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
bash modules/scrapers/scripts/build_corpus.sh
python -m modules.market fetch
./scripts/run_experiment.sh --model finbert_ptbr --dataset saneamento_corpus
python -m modules.research validate --run-id <run_id>
```

---

## Configuração (YAML)

| Arquivo | Controle |
| --- | --- |
| [configs/experiment.yaml](configs/experiment.yaml) | ITI, agregação, baselines, execução |
| [configs/models.yaml](configs/models.yaml) | Modelos FinBERT, adaptadores, HuggingFace |
| [configs/datasets.yaml](configs/datasets.yaml) | Datasets, colunas, `limits.max_rows` |
| [configs/market.yaml](configs/market.yaml) | Tickers B3, fetch yfinance |
| [configs/research.yaml](configs/research.yaml) | Horizontes, baselines, métricas, bootstrap |
| [configs/scrapers.yaml](configs/scrapers.yaml) | Portais, queries, corpus |

Downloads isolados: `python -m modules.models fetch`, `python -m modules.datasets fetch|check|validate`.

---

## Referências — modelos

| Chave YAML | Repositório Hugging Face |
| --- | --- |
| `finbert_ptbr` | [lucas-leme/FinBERT-PT-BR](https://huggingface.co/lucas-leme/FinBERT-PT-BR) |
| `pt_br_financial_sentiment_analysis` | [lucasalmda/pt-br-financial-sentiment-analysis](https://huggingface.co/lucasalmda/pt-br-financial-sentiment-analysis) |
| `finbert_en` | [ProsusAI/finbert](https://huggingface.co/ProsusAI/finbert) |
| `finbert_tone_en` | [yiyanghkust/finbert-tone](https://huggingface.co/yiyanghkust/finbert-tone) |

---

## Referências — datasets

| Chave YAML | Origem |
| --- | --- |
| `noticias_exemplo` | CSV versionado (`data/noticias_exemplo/`) — exemplo PT com rótulos |
| `news_example_en` | CSV versionado (`data/news_example_en/`) — exemplo EN com rótulos |
| `saneamento_ptbr_filtrado` | Notícias PT filtradas (HF); CSV local gitignored |
| `saneamento_en_filtrado` | Notícias EN filtradas (FNSPID); CSV local gitignored |
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
