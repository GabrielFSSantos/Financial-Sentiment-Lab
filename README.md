# Financial Sentiment Lab

Pipeline para **análise de sentimentos em notícias financeiras** (PT e EN), com execução local e no Supercomputador Santos Dumont.

Modelos, datasets e parâmetros são definidos em YAML.

```text
./scripts/setup_env.sh --fetch-assets   # venv + download HF (obrigatório na 1ª vez)
./scripts/audit_project.sh              # validar antes de rodar
./scripts/run_experiment.sh             # inferência (não baixa assets)
sbatch jobs/sdumont/run_experiment.srm  # HPC
```

Por padrão: **8 combinações** (4 modelos × 4 datasets, filtradas por idioma PT/EN).

---

## Objetivo

Construir o **Índice Temporal Informacional (ITI)** — séries diárias de impacto informacional por empresa, setor e mercado. O produto final está em `outputs/{run_id}/indices/`.

Classes: `POSITIVE`, `NEGATIVE`, `NEUTRAL`. Sentimento contínuo: `prob_positive - prob_negative`.

---

## Primeiro uso

```bash
git clone <repo>
cd financial-sentiment-lab
chmod +x scripts/*.sh jobs/sdumont/*.srm

./scripts/setup_env.sh --fetch-assets
./scripts/audit_project.sh
./scripts/run_experiment.sh
```

O `run_experiment.sh` **não baixa** modelos nem datasets. Se faltar peso ou arquivo, o preflight falha indicando `./scripts/setup_env.sh --fetch-assets`.

### Limites de linhas (`limits.max_rows`)

Em `[configs/datasets.yaml](configs/datasets.yaml)`:

- **Padrão:** `200` linhas (ajuste em `configs/datasets.yaml` para pilotos maiores)
- `max`**:** todas as linhas (exemplos versionados)
- Inteiro maior que o dataset disponível lê todas as linhas existentes
- Fetch completo quando `max`; fetch amostrado quando inteiro (via streaming no Hub)

---

## Comandos


| Comando                                   | Faz                                                       |
| ----------------------------------------- | --------------------------------------------------------- |
| `setup_env.sh`                            | Cria `venv/` e instala dependências                       |
| `setup_env.sh --fetch-assets`             | Instala deps **e baixa** modelos/datasets dos YAMLs       |
| `audit_project.sh`                        | Estrutura + YAML + pytest + dry-run (se assets presentes) |
| `run_experiment.sh`                       | Executa combinações `enabled: true`                       |
| `run_experiment.sh --model X --dataset Y` | Restringe a execução                                      |


---

## Configuração


| Arquivo                                              | Controla                                   |
| ---------------------------------------------------- | ------------------------------------------ |
| `[configs/experiment.yaml](configs/experiment.yaml)` | ITI, agregação, execução                   |
| `[configs/models.yaml](configs/models.yaml)`         | Modelos, `language`, `source`, adaptadores |
| `[configs/datasets.yaml](configs/datasets.yaml)`     | Datasets, `source`, `limits`, colunas      |


Adaptadores FinBERT em `[models/bert/](models/bert/)`: motor compartilhado (`finbert_hf.py`) e aliases por checkpoint. Ensembles têm adaptador dedicado.

---

## Saídas

```text
outputs/{run_id}/
├── summary.json
├── models/{model}/{dataset}/
└── indices/{model}/{dataset}/
```

Com ≥2 modelos no mesmo dataset: `indices/merged/{dataset}/iti_uncertainty_daily.csv`.

---

## Santos Dumont

Paths (confirme com `echo $SCRATCH` após login):

- `$HOME` → `/prj/ufsj/hpc4agents-br/<usuario>`
- `$SCRATCH` → `/scratch/ufsj/hpc4agents-br/<usuario>`
- Projeto → `$SCRATCH/financial-sentiment-lab`

```bash
mkdir -p "$SCRATCH/financial-sentiment-lab"
cd "$SCRATCH/financial-sentiment-lab"
git clone https://github.com/GabrielFSSantos/Financial-Sentiment-Lab.git .   # ou git pull

chmod +x scripts/*.sh jobs/sdumont/*.srm
module purge
module load cuda/12.6_sequana
module load anaconda3/2024.02_sequana

./scripts/setup_env.sh --fetch-assets
./scripts/audit_project.sh --sdumont
sbatch jobs/sdumont/run_experiment.srm
```

---

## Estrutura

```text
financial-sentiment-lab/
├── configs/
├── data/                  # exemplos versionados; demais via --fetch-assets
├── model_store/
├── models/
│   └── bert/
├── pipeline/
├── scripts/
├── tests/
├── outputs/
└── logs/
```

---

## Referências



### Modelos


| Chave YAML                           | Repositório                                                                                                           |
| ------------------------------------ | --------------------------------------------------------------------------------------------------------------------- |
| `finbert_ptbr`                       | [lucas-leme/FinBERT-PT-BR](https://huggingface.co/lucas-leme/FinBERT-PT-BR)                                           |
| `pt_br_financial_sentiment_analysis` | [lucasalmda/pt-br-financial-sentiment-analysis](https://huggingface.co/lucasalmda/pt-br-financial-sentiment-analysis) |
| `finbert_en`                         | [ProsusAI/finbert](https://huggingface.co/ProsusAI/finbert)                                                           |
| `finbert_tone_en`                    | [yiyanghkust/finbert-tone](https://huggingface.co/yiyanghkust/finbert-tone)                                           |




### Datasets


| Chave YAML                    | Repositório / origem                                                                                               |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| `noticias_exemplo`            | CSV versionado no repositório                                                                                      |
| `news_example_en`             | CSV versionado no repositório                                                                                      |
| `ptbr_financial_news_dataset` | [lucasalmda/pt-br-financial-news-dataset](https://huggingface.co/datasets/lucasalmda/pt-br-financial-news-dataset) |
| `en_financial_news_dataset`   | [Zihan1004/FNSPID](https://huggingface.co/datasets/Zihan1004/FNSPID)                                               |


