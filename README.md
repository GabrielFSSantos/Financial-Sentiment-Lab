# Financial Sentiment Lab

Pipeline para **análise de sentimentos em notícias do mercado financeiro brasileiro**, com execução local e no Supercomputador Santos Dumont.

Modelos, datasets e parâmetros são definidos em arquivos de configuração. A execução é iniciada por um único comando:

```bash
./scripts/run_experiment.sh
```

Por padrão, a pipeline executa:

```text
modelos com enabled: true
            ×
datasets com enabled: true
```

Cada combinação `modelo × dataset` gera previsões, métricas, agregações e metadados próprios.

---

## 1. Objetivo

O projeto busca construir um indicador contínuo de sentimento informacional para empresas, setores e o mercado financeiro brasileiro.

Fluxo científico:

1. carregar notícias financeiras;
2. classificar cada notícia como positiva, negativa ou neutra;
3. registrar as probabilidades das classes;
4. calcular um sentimento contínuo;
5. agregar os resultados por data, empresa, setor e mercado;
6. comparar modelos, datasets e parâmetros;
7. relacionar o sentimento com retorno, volatilidade, volume e eventos financeiros.

Classes padronizadas:

```text
POSITIVE
NEGATIVE
NEUTRAL
```

Sentimento contínuo:

```text
continuous_sentiment = prob_positive - prob_negative
```

```text
próximo de -1  → sentimento negativo
próximo de  0  → equilíbrio
próximo de  1  → sentimento positivo
```

---

## 2. Funcionamento

Arquivos principais:

| Arquivo | Responsabilidade |
|---|---|
| `configs/experiment.yaml` | Configuração geral do experimento |
| `configs/models.yaml` | Cadastro e parâmetros dos modelos |
| `configs/datasets.yaml` | Cadastro e mapeamento dos datasets |
| `configs/sdumont.env` | Acesso, caminhos, módulos e recursos do Santos Dumont |

Fluxo:

```text
configurações
      ↓
preflight e validações
      ↓
modelos habilitados × datasets habilitados
      ↓
inferência
      ↓
métricas
      ↓
agregações
      ↓
outputs/{run_id}/
```

O ambiente é definido em `configs/experiment.yaml`:

```yaml
execution:
  environment: local
```

ou:

```yaml
execution:
  environment: sdumont
```

Nos dois ambientes, o comando de entrada é:

```bash
./scripts/run_experiment.sh
```

---

## 3. Início rápido

### Requisitos

- Linux, WSL ou outro ambiente Bash compatível;
- Python 3.10 ou superior;
- pesos locais dos modelos em `model_store/`;
- acesso SSH ao Santos Dumont para execução remota.

Dependências:

```text
numpy
pandas
PyYAML
scikit-learn
torch
transformers
safetensors
```

### Permissões

```bash
chmod +x scripts/*.sh
chmod +x jobs/sdumont/*.srm
```

### Preparar o ambiente local

```bash
./scripts/setup_env.sh
```

Validar o ambiente existente:

```bash
./scripts/setup_env.sh --check
```

### Validar sem executar inferência

```bash
./scripts/run_experiment.sh --dry-run
```

### Executar

```bash
./scripts/run_experiment.sh
```

---

## 4. Comando principal

### Selecionar um modelo e um dataset

```bash
./scripts/run_experiment.sh \
  --model finbert_ptbr \
  --dataset noticias_exemplo
```

### Selecionar vários modelos e datasets

```bash
./scripts/run_experiment.sh \
  --model finbert_ptbr \
  --model outro_modelo \
  --dataset noticias_exemplo \
  --dataset outro_dataset
```

A execução utiliza todas as combinações informadas:

```text
finbert_ptbr × noticias_exemplo
finbert_ptbr × outro_dataset
outro_modelo × noticias_exemplo
outro_modelo × outro_dataset
```

As opções da linha de comando valem somente para a execução atual e não alteram os YAMLs.

### Definir o run ID

```bash
./scripts/run_experiment.sh \
  --run-id experimento_001
```

### Escolher o ambiente

```bash
./scripts/run_experiment.sh --environment local
```

```bash
./scripts/run_experiment.sh --environment sdumont
```

### Exibir todas as opções

```bash
./scripts/run_experiment.sh --help
```

---

# Configuração

## 5. `configs/experiment.yaml`

Centraliza as configurações gerais da execução.

```yaml
schema_version: "2.0"

experiment:
  run_id: null
  run_id_prefix: financial_sentiment
  random_seed: 42
  timezone: America/Sao_Paulo

execution:
  environment: local
  dry_run: false
  log_level: INFO
  fail_fast: true
  save_partial_results: true
  overwrite_existing_run: false

configuration_files:
  models: configs/models.yaml
  datasets: configs/datasets.yaml

outputs:
  save_predictions: true
  save_metrics: true
  save_aggregates: true
  save_metadata: true

classification_metrics:
  enabled: true

aggregation:
  enabled: true
  minimum_news_per_group: 1
  levels:
    - company_day
    - sector_day
    - market_day
```

Principais campos:

| Campo | Função |
|---|---|
| `experiment.run_id` | Identificador manual ou automático da execução |
| `execution.environment` | `local` ou `sdumont` |
| `execution.dry_run` | Valida sem executar inferência |
| `execution.fail_fast` | Interrompe no primeiro erro quando `true` |
| `execution.overwrite_existing_run` | Controla a substituição de resultados |
| `outputs` | Define quais arquivos serão salvos |
| `classification_metrics` | Habilita métricas supervisionadas |
| `aggregation` | Define níveis e regras de agregação |

---

## 6. `configs/models.yaml`

Centraliza os modelos disponíveis.

```yaml
schema_version: "2.0"

defaults:
  batch_size: 32
  max_length: 512
  device: auto
  unload_after_run: true

models:
  finbert_ptbr:
    enabled: true
    order: 1
    model_name: finbert_ptbr
    display_name: FinBERT-PT-BR
    adapter: models.finbert_ptbr.FinBertPtBrModel
    model_dir: model_store/FinBERT-PT-BR

    parameters:
      batch_size: 32
      max_length: 512
      device: auto
      probability_function: softmax

    loading:
      local_files_only: true
      trust_remote_code: false
      use_fast_tokenizer: true

    labels:
      id2label:
        0: POSITIVE
        1: NEGATIVE
        2: NEUTRAL

  pt_br_financial_sentiment_analysis:
    enabled: true
    order: 2
    model_name: pt_br_financial_sentiment_analysis
    display_name: PT-BR Financial Sentiment Analysis
    adapter: >-
      models.pt_br_financial_sentiment_analysis.PtBrFinancialSentimentAnalysisModel
    model_dir: model_store/pt-br-financial-sentiment-analysis

    parameters:
      checkpoint_directories:
        - seed-789
        - seed-123
        - seed-456

    loading:
      local_files_only: true
      trust_remote_code: false
      use_safetensors: true
```

Ativação:

```yaml
enabled: true
```

Um modelo com `enabled: false` pode ser executado diretamente por `--model`.

Dispositivo:

```text
auto  → CUDA quando disponível; caso contrário, CPU
cpu   → força CPU
cuda  → exige GPU CUDA
```

Funções de probabilidade aceitas pelo adaptador do FinBERT-PT-BR:

```text
softmax
sigmoid
model_config
```

O modelo `pt_br_financial_sentiment_analysis` reproduz o ensemble
publicado: carrega os checkpoints `seed-789`, `seed-123` e `seed-456`,
calcula a média dos logits e aplica `softmax` ao resultado. Os pesos
`model.safetensors` precisam estar materializados; ponteiros Git LFS não
são aceitos como pesos válidos.

Diretório esperado:

```text
model_store/
├── FinBERT-PT-BR/
│   ├── config.json
│   ├── tokenizer.json
│   ├── vocab.txt
│   └── pytorch_model.bin
└── pt-br-financial-sentiment-analysis/
    ├── training_strategy.json
    ├── seed-123/
    ├── seed-456/
    └── seed-789/
```

---

## 7. `configs/datasets.yaml`

Centraliza os datasets e o mapeamento para o schema interno.

```yaml
schema_version: "2.0"

datasets:
  noticias_exemplo:
    enabled: true
    order: 1
    dataset_name: noticias_exemplo
    display_name: Notícias de exemplo
    path: datasets/raw/noticias_exemplo/noticias.csv
    format: csv

    reader:
      encoding: utf-8
      delimiter: ","
      quotechar: '"'

    columns:
      news_id: id
      text: noticia
      date: data
      company: empresa
      sector: setor
      ticker: ticker
      title: titulo
      true_label: sentimento
      source: fonte
      url: url
```

A coluna interna obrigatória para inferência é:

```text
text
```

Exemplo de mapeamento para nomes diferentes:

```yaml
columns:
  news_id: codigo
  text: conteudo
  date: data_publicacao
  company: companhia
  true_label: classificacao
```

Um dataset com `enabled: false` pode ser executado diretamente por `--dataset`.

Sem `true_label`, a pipeline continua gerando previsões, probabilidades, sentimento contínuo, métricas de execução e agregações. As métricas supervisionadas são calculadas somente quando existem rótulos verdadeiros.

---

## 8. `configs/sdumont.env`

Contém as configurações de infraestrutura do Santos Dumont.

Criação:

```bash
cp configs/sdumont.env.example configs/sdumont.env
chmod 600 configs/sdumont.env
```

Campos obrigatórios:

```bash
USERNAME=""
LOGIN_HOST=""
ACCOUNT=""
PARTITION=""
SCRATCH_DIR=""
PYTHON_MODULE=""
```

Recursos principais:

```bash
SLURM_JOB_NAME="financial-sentiment"
SLURM_TIME="01:00:00"
SLURM_NODES="1"
SLURM_NTASKS="1"
SLURM_CPUS_PER_TASK="4"
SLURM_GPUS="1"
SLURM_GPU_TYPE=""
SLURM_MEM="32G"
```

Módulos e opções adicionais:

```bash
CUDA_MODULE=""
ADDITIONAL_MODULES=""
SLURM_QOS=""
SLURM_CONSTRAINT=""
SLURM_RESERVATION=""
```

O arquivo `configs/sdumont.env` é privado e protegido pelo `.gitignore`.

---

# Execução

## 9. Execução local

Com:

```yaml
execution:
  environment: local
```

execute:

```bash
./scripts/run_experiment.sh
```

Fluxo:

```text
valida o Python
      ↓
cria ou reutiliza venv/
      ↓
instala dependências quando necessário
      ↓
executa o preflight
      ↓
carrega modelos e datasets
      ↓
executa as combinações selecionadas
      ↓
salva em outputs/{run_id}/
```

Comandos úteis:

```bash
./scripts/run_experiment.sh --force-setup
```

```bash
./scripts/run_experiment.sh --recreate-env
```

```bash
./scripts/run_experiment.sh --skip-setup
```

---

## 10. Execução no Santos Dumont

Com:

```yaml
execution:
  environment: sdumont
```

execute:

```bash
./scripts/run_experiment.sh
```

Fluxo:

```text
valida configs/sdumont.env
      ↓
sincroniza o projeto com o Scratch
      ↓
prepara ou reutiliza o ambiente remoto
      ↓
submete um job ao Slurm
      ↓
jobs/sdumont/run_experiment.srm
      ↓
scripts/run_service.sh
      ↓
python -m pipeline.runner
      ↓
monitora o job
      ↓
baixa outputs e logs
```

O projeto utiliza um único job:

```text
jobs/sdumont/run_experiment.srm
```

As combinações selecionadas são executadas sequencialmente pelo runner dentro desse job.

Comandos úteis:

```bash
./scripts/run_experiment.sh \
  --environment sdumont \
  --print-only
```

```bash
./scripts/run_experiment.sh \
  --environment sdumont \
  --no-monitor \
  --no-download
```

```bash
./scripts/run_experiment.sh \
  --environment sdumont \
  --no-sync
```

```bash
./scripts/run_experiment.sh \
  --environment sdumont \
  --no-remote-setup
```

```bash
./scripts/run_experiment.sh \
  --environment sdumont \
  --no-download
```

---

## 11. Scripts do projeto

| Arquivo | Responsabilidade |
|---|---|
| `scripts/run_experiment.sh` | Entrada principal |
| `scripts/setup_env.sh` | Prepara ou valida o ambiente local |
| `scripts/run_service.sh` | Executa `python -m pipeline.runner` |
| `scripts/sync_to_scratch.sh` | Sincroniza o projeto com o Scratch |
| `scripts/setup_sdumont_env.sh` | Prepara o ambiente remoto |
| `scripts/submit_sdumont.sh` | Submete e monitora o job Slurm |
| `scripts/download_sdumont_results.sh` | Baixa outputs e logs |
| `scripts/audit_project.sh` | Audita a estrutura e a execução |
| `jobs/sdumont/run_experiment.srm` | Executa a pipeline no nó alocado |

---

# Modelos e datasets

## 12. Adicionar um dataset

1. Coloque o arquivo em:

```text
datasets/raw/novo_dataset/noticias.csv
```

2. Cadastre em `configs/datasets.yaml`:

```yaml
datasets:
  novo_dataset:
    enabled: true
    order: 2
    dataset_name: novo_dataset
    display_name: Novo Dataset
    path: datasets/raw/novo_dataset/noticias.csv
    format: csv

    reader:
      encoding: utf-8
      delimiter: ","
      quotechar: '"'

    columns:
      news_id: id
      text: texto
      date: data
      company: empresa
      sector: setor
      ticker: ticker
      title: titulo
      true_label: sentimento
```

Na execução seguinte, o dataset será combinado com todos os modelos habilitados.

---

## 13. Adicionar um modelo

1. Crie o adaptador:

```text
models/novo_modelo.py
```

2. Implemente o contrato definido em:

```text
models/base_model.py
```

3. Coloque os arquivos do modelo em:

```text
model_store/Novo-Modelo/
```

4. Cadastre em `configs/models.yaml`:

```yaml
models:
  novo_modelo:
    enabled: true
    order: 2
    model_name: novo_modelo
    display_name: Novo Modelo
    adapter: models.novo_modelo.NovoModelo
    model_dir: model_store/Novo-Modelo

    parameters:
      batch_size: 16
      max_length: 512
      device: auto
```

O adaptador deve retornar objetos `ModelPrediction` na mesma ordem dos textos recebidos.

---

# Resultados

## 14. Organização das saídas

Cada experimento possui um `run_id`.

```text
outputs/
└── {run_id}/
    ├── summary.json
    ├── resolved_config.yaml
    └── models/
        └── {model}/
            └── {dataset}/
                ├── predictions.csv
                ├── classification_metrics.csv
                ├── per_class_metrics.csv
                ├── confusion_matrix.csv
                ├── class_distribution.csv
                ├── execution_metrics.csv
                ├── aggregates.csv
                └── metadata.json
```

### Arquivos do experimento

| Arquivo | Conteúdo |
|---|---|
| `summary.json` | Resumo das combinações, status e arquivos produzidos |
| `resolved_config.yaml` | Configuração efetivamente utilizada |

### Arquivos de cada combinação

| Arquivo | Conteúdo |
|---|---|
| `predictions.csv` | Previsão de cada notícia |
| `classification_metrics.csv` | Métricas gerais de classificação |
| `per_class_metrics.csv` | Métricas por classe |
| `confusion_matrix.csv` | Matriz de confusão |
| `class_distribution.csv` | Distribuição das classes |
| `execution_metrics.csv` | Métricas de desempenho |
| `aggregates.csv` | Agregações de sentimento |
| `metadata.json` | Modelo, dataset, parâmetros, ambiente e status |

Principais campos de `predictions.csv`:

```text
run_id
environment
dataset_name
model_name
news_id
date
company
sector
ticker
title
text
true_label
predicted_label
confidence
prob_positive
prob_negative
prob_neutral
continuous_sentiment
processing_time_ms
device_used
```

Métricas supervisionadas:

```text
accuracy
precision
recall
macro_f1
weighted_f1
métricas por classe
matriz de confusão
```

Métricas de execução:

```text
tempo de carregamento
tempo de inferência
tempo total
textos por segundo
dispositivo utilizado
batch_size
max_length
quantidade de textos
status
```

Níveis de agregação:

```text
company_day
sector_day
market_day
```

Estatísticas principais:

```text
quantidade de notícias
média
mediana
soma
contagem de classes
confiança média
```

---

## 15. Estrutura do projeto

```text
financial-sentiment-lab/
├── configs/
│   ├── datasets.yaml
│   ├── experiment.yaml
│   ├── models.yaml
│   ├── sdumont.env
│   └── sdumont.env.example
├── datasets/
│   ├── processed/
│   └── raw/
│       └── noticias_exemplo/
│           └── noticias.csv
├── jobs/
│   └── sdumont/
│       └── run_experiment.srm
├── logs/
├── model_store/
│   ├── FinBERT-PT-BR/
│   └── pt-br-financial-sentiment-analysis/
├── models/
│   ├── __init__.py
│   ├── base_model.py
│   ├── finbert_ptbr.py
│   └── pt_br_financial_sentiment_analysis.py
├── outputs/
├── pipeline/
│   ├── __init__.py
│   ├── aggregation.py
│   ├── configuration.py
│   ├── dataset_loader.py
│   ├── metrics.py
│   ├── output_schema.py
│   ├── registry.py
│   ├── results.py
│   └── runner.py
├── scripts/
│   ├── audit_project.sh
│   ├── download_sdumont_results.sh
│   ├── run_experiment.sh
│   ├── run_service.sh
│   ├── setup_env.sh
│   ├── setup_sdumont_env.sh
│   ├── submit_sdumont.sh
│   └── sync_to_scratch.sh
├── .gitignore
├── README.md
└── requirements.txt
```

Responsabilidades:

| Caminho | Responsabilidade |
|---|---|
| `configs/` | Configurações do experimento, modelos, datasets e SDumont |
| `datasets/` | Dados brutos e processados |
| `model_store/` | Pesos, configurações e tokenizers |
| `models/` | Contrato comum e adaptadores |
| `pipeline/configuration.py` | Carrega e valida os YAMLs |
| `pipeline/dataset_loader.py` | Lê, valida e normaliza datasets |
| `pipeline/registry.py` | Localiza e instancia adaptadores |
| `pipeline/output_schema.py` | Padroniza as previsões |
| `pipeline/metrics.py` | Calcula métricas |
| `pipeline/aggregation.py` | Gera agregações |
| `pipeline/results.py` | Organiza e salva resultados |
| `pipeline/runner.py` | Orquestra o experimento |
| `scripts/` | Entrada principal e automações |
| `jobs/sdumont/` | Job executado pelo Slurm |
| `outputs/` | Resultados separados por `run_id` |
