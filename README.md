# Financial Sentiment Lab

Pipeline para **análise de sentimentos em notícias do mercado financeiro brasileiro**, com execução local e no Supercomputador Santos Dumont.

Modelos, datasets e parâmetros são definidos em arquivos YAML. O comando principal do projeto é:

```bash
./scripts/run_experiment.sh
```

Por padrão, a pipeline executa:

```text
modelos com enabled: true
            ×
datasets com enabled: true
```

Cada combinação `modelo × dataset` gera previsões, métricas, agregações, logs e metadados próprios.

---

## 1. Objetivo

O projeto busca construir um indicador contínuo de sentimento informacional para empresas, setores e o mercado financeiro brasileiro.

Fluxo científico:

1. carregar notícias financeiras;
2. classificar cada notícia como positiva, negativa ou neutra;
3. registrar as probabilidades das classes;
4. calcular um sentimento contínuo;
5. agregar os resultados por data, empresa, setor e mercado;
6. comparar modelos e datasets;
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

Interpretação:

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
| `scripts/run_experiment.sh` | Ponto de entrada do projeto |
| `scripts/setup_env.sh` | Criação e atualização do ambiente virtual |
| `scripts/run_service.sh` | Execução do `pipeline.runner` |
| `scripts/audit_project.sh` | Auditoria da estrutura, ambiente e pipeline |
| `jobs/sdumont/run_experiment.srm` | Job Slurm para execução no Santos Dumont |

Fluxo principal:

```text
configurações
      ↓
preflight
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

O ambiente é identificado em `configs/experiment.yaml`:

```yaml
execution:
  environment: local
```

Valores aceitos:

```text
local
sdumont
```

Esse campo identifica o ambiente registrado nos resultados. A execução local é iniciada diretamente pelo script principal. No Santos Dumont, a submissão é feita pelo arquivo `.srm`.

---

## 3. Início rápido

### Requisitos

- Linux, WSL ou outro ambiente Bash compatível;
- Python 3.10 ou superior;
- pesos locais dos modelos em `model_store/`;
- datasets disponíveis nos caminhos cadastrados;
- acesso ao Scratch e ao Slurm para execução no Santos Dumont.

Dependências principais:

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

### Preparar o ambiente

```bash
./scripts/setup_env.sh
```

### Auditar o projeto

```bash
./scripts/audit_project.sh
```

### Validar a pipeline sem inferência

```bash
./scripts/run_experiment.sh --dry-run
```

### Executar localmente

```bash
./scripts/run_experiment.sh
```

---

## 4. Comando principal

O script:

```bash
./scripts/run_experiment.sh
```

prepara o ambiente virtual quando necessário, ativa o `venv` e chama o runner Python.

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
  --model pt_br_financial_sentiment_analysis \
  --dataset noticias_exemplo \
  --dataset ptbr_financial_news_dataset
```

A execução utiliza todas as combinações informadas:

```text
finbert_ptbr × noticias_exemplo
finbert_ptbr × ptbr_financial_news_dataset
pt_br_financial_sentiment_analysis × noticias_exemplo
pt_br_financial_sentiment_analysis × ptbr_financial_news_dataset
```

As opções da linha de comando valem somente para a execução atual e não alteram os YAMLs.

### Definir o run ID

```bash
./scripts/run_experiment.sh \
  --run-id experimento_001
```

### Escolher o ambiente registrado

```bash
./scripts/run_experiment.sh --environment local
```

```bash
./scripts/run_experiment.sh --environment sdumont
```

### Executar um dry-run

```bash
./scripts/run_experiment.sh \
  --dry-run \
  --log-level INFO
```

O dry-run valida configurações, modelos, datasets, caminhos e combinações sem executar inferência.

### Forçar execução real

```bash
./scripts/run_experiment.sh --no-dry-run
```

### Mostrar tracebacks completos

```bash
./scripts/run_experiment.sh --traceback
```

### Imprimir o resumo final em JSON

```bash
./scripts/run_experiment.sh --print-summary-json
```

### Exibir as opções

```bash
./scripts/run_experiment.sh --help
```

---

# Configuração

## 5. `configs/experiment.yaml`

Centraliza as configurações gerais do experimento.

Exemplo simplificado:

```yaml
schema_version: "2.0"

experiment:
  name: financial_sentiment
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
  unload_model_after_combination: true

configuration_files:
  models: configs/models.yaml
  datasets: configs/datasets.yaml

paths:
  output_root: outputs
  log_root: logs
  temp_root: .tmp

outputs:
  save_predictions: true
  save_metrics: true
  save_aggregates: true
  save_metadata: true
  save_experiment_summary: true
  save_resolved_config: true

classification_metrics:
  enabled: true
  allow_unlabeled_datasets: true

aggregation:
  enabled: true
  sentiment_column: continuous_sentiment
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
| `experiment.random_seed` | Semente de reprodutibilidade |
| `execution.environment` | Ambiente registrado: `local` ou `sdumont` |
| `execution.dry_run` | Valida a pipeline sem executar inferência |
| `execution.fail_fast` | Interrompe no primeiro erro quando `true` |
| `execution.save_partial_results` | Preserva combinações já concluídas |
| `execution.overwrite_existing_run` | Controla a substituição de resultados |
| `execution.unload_model_after_combination` | Libera memória entre combinações |
| `paths` | Define diretórios de saída, logs e arquivos temporários |
| `outputs` | Define os artefatos produzidos |
| `classification_metrics` | Controla as métricas supervisionadas |
| `aggregation` | Define níveis e regras de agregação |

Quando `experiment.run_id` é `null`, o identificador é gerado automaticamente.

---

## 6. `configs/models.yaml`

Centraliza os modelos disponíveis, seus adaptadores, pesos, parâmetros e classes.

Estrutura principal:

```yaml
schema_version: "2.0"

defaults:
  parameters:
    batch_size: 32
    max_length: 512
    device: auto

  loading:
    local_files_only: true
    trust_remote_code: false
    use_fast_tokenizer: true

  validation:
    require_model_directory: true
    require_required_files: true
    validate_label_mapping: true

models:
  finbert_ptbr:
    enabled: true
    order: 1
    model_name: finbert_ptbr
    display_name: FinBERT-PT-BR
    adapter: models.finbert_ptbr.FinBertPtBrModel
    model_dir: model_store/FinBERT-PT-BR

  pt_br_financial_sentiment_analysis:
    enabled: true
    order: 2
    model_name: pt_br_financial_sentiment_analysis
    display_name: PT-BR Financial Sentiment Analysis
    adapter: >-
      models.pt_br_financial_sentiment_analysis.PtBrFinancialSentimentAnalysisModel
    model_dir: model_store/pt-br-financial-sentiment-analysis
```

Ativação:

```yaml
enabled: true
```

Um modelo com `enabled: false` ainda pode ser selecionado diretamente:

```bash
./scripts/run_experiment.sh --model nome_do_modelo
```

Dispositivo:

```text
auto  → usa CUDA quando disponível; caso contrário, CPU
cpu   → força CPU
cuda  → exige GPU CUDA
```

Parâmetros podem ser sobrescritos por modelo:

```yaml
parameters:
  batch_size: 16
  max_length: 256
  device: cuda
```

### FinBERT-PT-BR

O adaptador padroniza as classes do modelo para:

```text
0 → POSITIVE
1 → NEGATIVE
2 → NEUTRAL
```

Diretório esperado:

```text
model_store/FinBERT-PT-BR/
├── config.json
├── tokenizer.json
├── tokenizer_config.json
├── special_tokens_map.json
├── vocab.txt
└── pytorch_model.bin
```

### PT-BR Financial Sentiment Analysis

O modelo utiliza um ensemble com três checkpoints:

```text
seed-123
seed-456
seed-789
```

A inferência calcula a média dos logits dos checkpoints e aplica `softmax` ao resultado.

Diretório esperado:

```text
model_store/pt-br-financial-sentiment-analysis/
├── training_strategy.json
├── seed-123/
│   ├── config.json
│   └── model.safetensors
├── seed-456/
│   ├── config.json
│   └── model.safetensors
└── seed-789/
    ├── config.json
    └── model.safetensors
```

Os pesos precisam estar materializados no sistema de arquivos. Ponteiros Git LFS não substituem os arquivos reais.

---

## 7. `configs/datasets.yaml`

Centraliza os datasets e o mapeamento de suas colunas para o schema interno da pipeline.

A execução padrão usa todos os datasets com:

```yaml
enabled: true
```

Um dataset com `enabled: false` pode ser selecionado diretamente:

```bash
./scripts/run_experiment.sh --dataset nome_do_dataset
```

### Dataset de exemplo

```yaml
datasets:
  noticias_exemplo:
    enabled: true
    order: 1
    dataset_name: noticias_exemplo
    display_name: Notícias financeiras de exemplo
    path: datasets/raw/noticias_exemplo/noticias.csv
    format: csv

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

    required_fields:
      - news_id
      - text

    labels:
      available: true

    dates:
      available: true
      format: "%Y-%m-%d"
```

O dataset `noticias_exemplo` é pequeno e serve para testes técnicos da pipeline.

### PT-BR Financial News Dataset

```yaml
datasets:
  ptbr_financial_news_dataset:
    enabled: false
    order: 2
    dataset_name: ptbr_financial_news_dataset
    display_name: PT-BR Financial News Dataset
    path: >-
      datasets/raw/ptbr_financial_news_dataset/ptbr_financial_news_dataset.jsonl
    format: jsonl

    reader:
      encoding: utf-8
      lines: true

    columns:
      news_id: url
      text: sentiment_text
      date: published_at
      company: null
      sector: null
      ticker: null
      title: title
      true_label: null
      source: source
      url: url

    required_fields:
      - news_id
      - text

    labels:
      available: false

    dates:
      available: true
      format: ISO8601
```

O corpus completo não possui rótulos verdadeiros estruturados para todas as notícias. Nesse caso, a pipeline continua produzindo:

```text
previsões
probabilidades
sentimento contínuo
métricas computacionais
agregações
metadados
```

Métricas supervisionadas são calculadas apenas quando o dataset possui `true_label`.

Formatos aceitos:

```text
csv
jsonl
```

A coluna interna necessária para inferência é:

```text
text
```

---

# Execução

## 8. Execução local

Na raiz do projeto:

```bash
./scripts/run_experiment.sh
```

Na primeira execução, o fluxo é:

```text
cria venv/
      ↓
instala requirements.txt
      ↓
ativa o ambiente
      ↓
executa o pipeline.runner
```

Nas execuções seguintes, o ambiente existente é reutilizado. As dependências são instaladas novamente quando necessário.

### Executar somente o FinBERT-PT-BR

```bash
./scripts/run_experiment.sh \
  --model finbert_ptbr \
  --dataset noticias_exemplo \
  --run-id local_finbert_01
```

### Executar somente o ensemble

```bash
./scripts/run_experiment.sh \
  --model pt_br_financial_sentiment_analysis \
  --dataset noticias_exemplo \
  --run-id local_ensemble_01
```

### Executar todos os itens habilitados

```bash
./scripts/run_experiment.sh
```

### Executar o corpus completo

```bash
./scripts/run_experiment.sh \
  --model finbert_ptbr \
  --dataset ptbr_financial_news_dataset \
  --run-id local_finbert_full_01
```

### Reinstalar as dependências

```bash
./scripts/run_experiment.sh --force-setup
```

### Recriar o ambiente virtual

```bash
./scripts/run_experiment.sh --recreate-env
```

### Usar um ambiente já preparado

```bash
./scripts/run_experiment.sh --skip-setup
```

### Informar outro Python

```bash
./scripts/run_experiment.sh \
  --python python3.11
```

### Forçar CPU

```bash
CUDA_VISIBLE_DEVICES="" \
./scripts/run_experiment.sh \
  --model finbert_ptbr \
  --dataset noticias_exemplo
```

Resultados:

```text
outputs/{run_id}/
```

Log da execução:

```text
logs/{run_id}.log
```

---

## 9. Execução no Santos Dumont

A execução no Santos Dumont utiliza:

```text
jobs/sdumont/run_experiment.srm
```

O projeto, os pesos e os datasets devem estar disponíveis no Scratch antes da submissão.

### Diretório do projeto

O caminho utilizado pelo job é definido em:

```bash
WORKING_DIR="/scratch/..."
```

Ajuste esse valor no `.srm` quando o diretório do projeto for diferente.

### Módulos

O `.srm` carrega os módulos necessários ao ambiente. Exemplo:

```bash
module purge
module load cuda/12.6_sequana
module load anaconda3/2024.02_sequana
```

Os nomes precisam corresponder aos módulos disponíveis no SDumont.

### Preparação inicial

A preparação do ambiente é feita uma vez no nó de login.

```bash
cd /scratch/...

module purge
module load cuda/12.6_sequana
module load anaconda3/2024.02_sequana

./scripts/setup_env.sh \
  --python python \
  --recreate
```

O ambiente será criado em:

```text
financial-sentiment-lab/venv/
```

O `venv` deve ser criado no próprio SDumont com os mesmos módulos utilizados pelo job.

### Submissão

```bash
sbatch jobs/sdumont/run_experiment.srm
```

O job:

```text
solicita recursos ao Slurm
      ↓
entra no diretório do projeto
      ↓
carrega os módulos
      ↓
ativa venv/
      ↓
executa a pipeline com srun
```

Comando executado pelo job:

```bash
srun ./scripts/run_experiment.sh \
  --environment sdumont \
  --skip-setup
```

Por padrão, são processados os modelos e datasets com `enabled: true`.

### Restringir o primeiro teste

A linha final do `.srm` pode selecionar explicitamente um modelo e um dataset:

```bash
srun ./scripts/run_experiment.sh \
  --environment sdumont \
  --skip-setup \
  --model finbert_ptbr \
  --dataset noticias_exemplo \
  --run-id "sdumont_finbert_${SLURM_JOB_ID}"
```

### Acompanhar o job

```bash
squeue -u "$USER"
```

Consultar o histórico:

```bash
sacct -j JOB_ID \
  --format=JobID,JobName,Partition,State,Elapsed,ExitCode,MaxRSS
```

Acompanhar a saída:

```bash
tail -f job_financial_JOB_ID.out
```

Acompanhar erros:

```bash
tail -f job_financial_JOB_ID.err
```

### Resultados

Os resultados permanecem no projeto dentro do Scratch:

```text
outputs/{run_id}/
```

Os logs da pipeline ficam em:

```text
logs/{run_id}.log
```

Os arquivos gerados pelo Slurm ficam nos caminhos definidos por `#SBATCH --output` e `#SBATCH --error`.

### Ajustar recursos

Os recursos são definidos diretamente no `.srm`:

```bash
#SBATCH --partition=sequana_gpu_dev
#SBATCH --cpus-per-task=4
#SBATCH --gres=gpu:1
#SBATCH --mem=32G
#SBATCH --time=00:20:00
```

Para uma execução maior, ajuste a partição, o tempo, a memória e os recursos conforme as filas disponíveis.

---

## 10. Auditoria

O script:

```bash
./scripts/audit_project.sh
```

verifica:

```text
estrutura do projeto
permissões
sintaxe Bash
configurações YAML
Python e _ctypes
dependências e versões
imports internos
CUDA
Git e .gitignore
dry-run da pipeline
referências desatualizadas
```

O relatório é salvo em:

```text
logs/audit/audit_project_<data>_<hora>.log
```

A auditoria executa o dry-run da pipeline por padrão.

### Auditar sem dry-run

```bash
./scripts/audit_project.sh --skip-dry-run
```

### Executar uma inferência curta em CPU

```bash
./scripts/audit_project.sh --model-smoke
```

### Exigir CUDA

```bash
./scripts/audit_project.sh --require-cuda
```

### Auditar no contexto do SDumont

```bash
./scripts/audit_project.sh \
  --environment sdumont \
  --require-cuda
```

O `--dry-run` é implementado pelo `pipeline.runner`. A auditoria apenas o utiliza como uma de suas verificações.

---

## 11. Scripts do projeto

| Arquivo | Responsabilidade |
|---|---|
| `scripts/run_experiment.sh` | Entrada principal e preparação opcional do ambiente |
| `scripts/setup_env.sh` | Cria o `venv` e instala `requirements.txt` |
| `scripts/run_service.sh` | Configura o runtime e executa `python -m pipeline.runner` |
| `scripts/audit_project.sh` | Audita a estrutura, ambiente e pipeline |
| `jobs/sdumont/run_experiment.srm` | Solicita recursos e executa o projeto pelo Slurm |

Fluxo local:

```text
run_experiment.sh
      ↓
setup_env.sh
      ↓
run_service.sh
      ↓
pipeline.runner
```

Fluxo no Santos Dumont:

```text
sbatch run_experiment.srm
      ↓
ativa venv
      ↓
srun run_experiment.sh --skip-setup
      ↓
run_service.sh
      ↓
pipeline.runner
```

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
    order: 3
    dataset_name: novo_dataset
    display_name: Novo Dataset
    path: datasets/raw/novo_dataset/noticias.csv
    format: csv

    columns:
      news_id: id
      text: texto
      date: data
      company: empresa
      sector: setor
      ticker: ticker
      title: titulo
      true_label: sentimento
      source: fonte
      url: url

    required_fields:
      - news_id
      - text

    labels:
      available: true

    dates:
      available: true
      format: "%Y-%m-%d"

    validation:
      strip_text: true
      drop_empty_texts: true
      fail_on_duplicate_ids: true
      preserve_extra_columns: true
```

Na execução seguinte, o dataset será combinado com todos os modelos habilitados.

Para JSON Lines:

```yaml
format: jsonl

reader:
  encoding: utf-8
  lines: true
```

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
    order: 3
    model_name: novo_modelo
    display_name: Novo Modelo
    adapter: models.novo_modelo.NovoModelo
    model_dir: model_store/Novo-Modelo

    parameters:
      batch_size: 16
      max_length: 512
      device: auto

    loading:
      local_files_only: true
      trust_remote_code: false
      use_fast_tokenizer: true

    validation:
      require_model_directory: true
      require_required_files: true
      validate_label_mapping: true

    files:
      required:
        - config.json
        - tokenizer.json
        - model.safetensors

    labels:
      id2label:
        0: POSITIVE
        1: NEGATIVE
        2: NEUTRAL

      canonical:
        positive: POSITIVE
        negative: NEGATIVE
        neutral: NEUTRAL
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

Métricas computacionais:

```text
tempo de carregamento
tempo de inferência
tempo total
textos por segundo
pico de memória da GPU
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
│   └── models.yaml
├── datasets/
│   ├── processed/
│   └── raw/
│       ├── noticias_exemplo/
│       │   └── noticias.csv
│       └── ptbr_financial_news_dataset/
│           └── ptbr_financial_news_dataset.jsonl
├── jobs/
│   └── sdumont/
│       └── run_experiment.srm
├── logs/
│   └── audit/
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
│   ├── run_experiment.sh
│   ├── run_service.sh
│   └── setup_env.sh
├── .gitignore
├── README.md
└── requirements.txt
```

Responsabilidades:

| Caminho | Responsabilidade |
|---|---|
| `configs/` | Configurações do experimento, modelos e datasets |
| `datasets/` | Dados brutos e processados |
| `jobs/sdumont/` | Job Slurm |
| `logs/` | Logs das execuções e auditorias |
| `model_store/` | Pesos, configurações e tokenizers |
| `models/` | Contrato comum e adaptadores |
| `pipeline/configuration.py` | Carrega e valida os YAMLs |
| `pipeline/dataset_loader.py` | Lê, valida e normaliza CSV e JSONL |
| `pipeline/registry.py` | Localiza e instancia adaptadores |
| `pipeline/output_schema.py` | Padroniza previsões |
| `pipeline/metrics.py` | Calcula métricas |
| `pipeline/aggregation.py` | Gera agregações |
| `pipeline/results.py` | Organiza e salva resultados |
| `pipeline/runner.py` | Orquestra o experimento |
| `scripts/` | Preparação, execução e auditoria |
| `outputs/` | Resultados separados por `run_id` |