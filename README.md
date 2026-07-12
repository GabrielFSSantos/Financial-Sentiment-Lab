# FinBERT-PT-BR — Inferência de Sentimentos Financeiros

Este repositório é uma adaptação experimental do **FinBERT-PT-BR** para executar análise de sentimentos em notícias financeiras em português.

O projeto foi organizado para que o mesmo código possa ser executado:

- localmente em Linux ou WSL;
- em CPU ou GPU NVIDIA;
- no Supercomputador Santos Dumont com Slurm;
- com diferentes parâmetros de teste;
- futuramente com outros modelos locais compatíveis.

O modelo e o tokenizer já ficam armazenados dentro do projeto. Durante a inferência, o código apenas carrega esses arquivos locais e executa a classificação.

---

## 1. O que é o FinBERT-PT-BR

O **FinBERT-PT-BR** é um modelo baseado na arquitetura BERT e adaptado para textos do mercado financeiro em português brasileiro.

Ele recebe um texto e retorna probabilidades para três classes:

- `POSITIVE`;
- `NEGATIVE`;
- `NEUTRAL`.

Exemplo:

```text
Notícia:
Petrobras anuncia lucro acima do esperado e aumento de dividendos.

Resultado:
POSITIVE = 0.8757
NEGATIVE = 0.0754
NEUTRAL  = 0.0488
```

A classe com maior probabilidade é usada como sentimento final:

```text
sentimento = POSITIVE
confianca  = 0.8757
```

O funcionamento depende da combinação entre:

```text
Tokenizer
+
Arquitetura BERT da biblioteca Transformers
+
Execução matemática pelo PyTorch
+
Configuração do modelo
+
Pesos treinados
```

Os principais arquivos locais são:

| Arquivo | Função |
|---|---|
| `config.json` | Define a arquitetura, dimensões e classes do modelo |
| `pytorch_model.bin` | Contém os pesos aprendidos no treinamento |
| `tokenizer.json` | Define a tokenização |
| `tokenizer_config.json` | Contém configurações do tokenizer |
| `vocab.txt` | Contém o vocabulário |
| `special_tokens_map.json` | Define tokens especiais como `[CLS]`, `[SEP]` e `[PAD]` |

O código usa `local_files_only=True`, portanto o modelo é carregado diretamente da pasta informada em `MODEL_DIR`.

---

## 2. O que este projeto adiciona

Este projeto não treina o FinBERT-PT-BR novamente.

Ele cria uma estrutura de execução para:

- ler notícias de um arquivo CSV;
- processar os textos em lotes;
- usar automaticamente CPU ou GPU;
- permitir testes com diferentes parâmetros;
- calcular probabilidades e um índice contínuo de sentimento;
- salvar resultados e metadados;
- executar o mesmo experimento localmente e no SDumont.

---

## 3. Estrutura do projeto

```text
finbert-sdumont/
├── dados/
│   └── noticias.csv
├── FinBERT-PT-BR/
│   ├── config.json
│   ├── pytorch_model.bin
│   ├── special_tokens_map.json
│   ├── tokenizer_config.json
│   ├── tokenizer.json
│   └── vocab.txt
├── logs/
├── resultados/
├── executar_finbert.sh
├── finbert_inferencia.py
├── requirements.txt
├── setup_env.sh
└── README.md
```

---

## 4. Função dos arquivos principais

### `setup_env.sh`

Prepara o ambiente Python.

Ele:

1. localiza o Python disponível;
2. cria o ambiente virtual `venv` caso ainda não exista;
3. verifica se as dependências estão instaladas;
4. verifica se o `requirements.txt` foi alterado;
5. instala dependências apenas quando necessário;
6. valida PyTorch, Transformers, pandas, NumPy e CUDA.

Esse script não executa o modelo.

### `executar_finbert.sh`

É o comando principal do projeto.

Ele:

1. localiza a pasta do projeto;
2. chama o `setup_env.sh`;
3. ativa o ambiente virtual;
4. valida o modelo e o arquivo de entrada;
5. lê os parâmetros da execução;
6. chama o `finbert_inferencia.py`;
7. funciona localmente e também dentro de um job Slurm.

### `finbert_inferencia.py`

É o programa que executa a inferência.

Ele:

1. lê o arquivo CSV;
2. seleciona a coluna de texto;
3. ignora linhas vazias;
4. identifica CPU ou GPU;
5. carrega o tokenizer;
6. carrega a arquitetura do modelo;
7. carrega os pesos treinados;
8. processa os textos em lotes;
9. calcula as probabilidades;
10. define a classe final;
11. calcula o índice contínuo;
12. salva os resultados em CSV;
13. salva os metadados em JSON.

### `requirements.txt`

Contém as dependências do projeto:

```text
torch
transformers
pandas
numpy
```

---

## 5. Fluxo de execução

```text
./executar_finbert.sh
        ↓
setup_env.sh verifica o ambiente
        ↓
venv é criada ou reutilizada
        ↓
finbert_inferencia.py é executado
        ↓
noticias.csv é lido
        ↓
os textos são tokenizados
        ↓
o modelo usa os pesos locais
        ↓
logits são gerados
        ↓
softmax converte logits em probabilidades
        ↓
sentimento e índice contínuo são calculados
        ↓
CSV e JSON de resultados são salvos
```

---

## 6. Arquivo de entrada

O arquivo padrão é:

```text
dados/noticias.csv
```

Ele deve possuir uma coluna chamada `noticia`.

Exemplo:

```csv
id,empresa,setor,noticia
1,Petrobras,Óleo e Gás,"Petrobras anuncia lucro acima do esperado e aumento no pagamento de dividendos."
2,Vale,Mineração,"Vale registra queda na produção de minério e preocupa investidores."
3,Banco Central,Macroeconomia,"Banco Central mantém a taxa Selic inalterada."
```

As outras colunas são preservadas no arquivo final.

---

## 7. Execução local

### Requisitos

Em Linux ou WSL:

```bash
sudo apt update
sudo apt install python3 python3-venv python3-pip
```

### Permissão dos scripts

Execute uma vez:

```bash
chmod +x setup_env.sh executar_finbert.sh
```

### Comando principal

```bash
./executar_finbert.sh
```

Na primeira execução, o ambiente virtual é criado e as dependências são instaladas.

Nas próximas execuções, o ambiente é reutilizado e as dependências não são reinstaladas se continuarem válidas.

---

## 8. Parâmetros de teste

Os parâmetros podem ser alterados antes do comando, sem editar os arquivos.

### `BATCH_SIZE`

Quantidade de textos processados por lote.

Padrão:

```text
32
```

Exemplo:

```bash
BATCH_SIZE=64 ./executar_finbert.sh
```

Efeito esperado:

- valores maiores podem aumentar a velocidade em GPU;
- valores maiores usam mais memória;
- valores menores reduzem o consumo de memória;
- o batch size normalmente altera desempenho, não a lógica da classificação.

Em caso de falta de memória:

```bash
BATCH_SIZE=8 ./executar_finbert.sh
```

### `MAX_LENGTH`

Quantidade máxima de tokens por texto.

Padrão:

```text
512
```

Exemplo:

```bash
MAX_LENGTH=256 ./executar_finbert.sh
```

Efeito esperado:

- valores menores reduzem tempo e memória;
- textos acima do limite são truncados;
- valores menores podem remover partes importantes do texto;
- o FinBERT-PT-BR aceita no máximo 512 tokens.

### `TEXT_COLUMN`

Nome da coluna do CSV que contém o texto.

Padrão:

```text
noticia
```

Exemplo:

```bash
TEXT_COLUMN=texto ./executar_finbert.sh
```

### `DEVICE`

Define o dispositivo da execução.

Valores aceitos:

```text
auto
cpu
cuda
```

Padrão:

```text
auto
```

Exemplos:

```bash
DEVICE=cpu ./executar_finbert.sh
```

```bash
DEVICE=cuda ./executar_finbert.sh
```

Em `auto`, o código usa GPU quando CUDA está disponível. Caso contrário, usa CPU.

### `MODEL_DIR`

Define a pasta local do modelo.

Padrão:

```text
FinBERT-PT-BR
```

Exemplo:

```bash
MODEL_DIR=OutroModelo ./executar_finbert.sh
```

O outro modelo precisa ser compatível com `AutoModelForSequenceClassification` e possuir as classes:

```text
POSITIVE
NEGATIVE
NEUTRAL
```

### `INPUT_FILE`

Define outro CSV de entrada.

Exemplo:

```bash
INPUT_FILE=dados/noticias_teste.csv ./executar_finbert.sh
```

### `OUTPUT_FILE`

Define outro arquivo de saída.

Exemplo:

```bash
OUTPUT_FILE=resultados/teste_batch64.csv ./executar_finbert.sh
```

### Exemplo completo

```bash
MODEL_DIR=FinBERT-PT-BR INPUT_FILE=dados/noticias.csv OUTPUT_FILE=resultados/teste_gpu_batch64.csv TEXT_COLUMN=noticia BATCH_SIZE=64 MAX_LENGTH=512 DEVICE=cuda ./executar_finbert.sh
```

---

## 9. Como comparar experimentos

Altere um parâmetro por vez.

Exemplo para batch size:

```bash
BATCH_SIZE=8 OUTPUT_FILE=resultados/batch8.csv ./executar_finbert.sh

BATCH_SIZE=32 OUTPUT_FILE=resultados/batch32.csv ./executar_finbert.sh

BATCH_SIZE=64 OUTPUT_FILE=resultados/batch64.csv ./executar_finbert.sh
```

Exemplo para tamanho máximo:

```bash
MAX_LENGTH=128 OUTPUT_FILE=resultados/max128.csv ./executar_finbert.sh

MAX_LENGTH=256 OUTPUT_FILE=resultados/max256.csv ./executar_finbert.sh

MAX_LENGTH=512 OUTPUT_FILE=resultados/max512.csv ./executar_finbert.sh
```

Compare:

- tempo de carregamento;
- tempo de inferência;
- tempo total;
- textos processados por segundo;
- memória máxima da GPU;
- classes obtidas;
- probabilidades;
- índice contínuo.

Os tempos e informações do ambiente são registrados no arquivo `.metadata.json`.

---

## 10. Resultados

O arquivo padrão de saída é:

```text
resultados/noticias_classificadas.csv
```

Ele preserva as colunas originais e adiciona:

| Coluna | Significado |
|---|---|
| `sentimento` | Classe com maior probabilidade |
| `confianca` | Probabilidade da classe escolhida |
| `positivo` | Probabilidade positiva |
| `negativo` | Probabilidade negativa |
| `neutro` | Probabilidade neutra |
| `indice_sentimento` | Diferença entre positivo e negativo |

Exemplo:

```csv
id,empresa,setor,noticia,sentimento,confianca,positivo,negativo,neutro,indice_sentimento
1,Petrobras,Óleo e Gás,"Petrobras anuncia lucro...",POSITIVE,0.8757,0.8757,0.0754,0.0488,0.8003
```

Também é criado:

```text
resultados/noticias_classificadas.metadata.json
```

Esse arquivo registra:

- modelo utilizado;
- arquitetura;
- classes;
- entrada e saída;
- batch size;
- máximo de tokens;
- dispositivo solicitado;
- CPU ou GPU utilizada;
- nome da GPU;
- versão do CUDA;
- memória máxima da GPU;
- tempo de carregamento;
- tempo de inferência;
- tempo total;
- textos por segundo;
- versões das bibliotecas.

---

## 11. Índice contínuo de sentimento

O índice é calculado para cada notícia:

```text
indice_sentimento = positivo - negativo
```

Ele varia aproximadamente entre `-1` e `+1`.

```text
próximo de -1  → tendência fortemente negativa
próximo de  0  → equilíbrio entre positivo e negativo
próximo de +1  → tendência fortemente positiva
```

Exemplo positivo:

```text
positivo = 0.90
negativo = 0.05

indice_sentimento = 0.85
```

Exemplo negativo:

```text
positivo = 0.10
negativo = 0.80

indice_sentimento = -0.70
```

Uma notícia pode ser classificada como `NEUTRAL` e ainda possuir tendência positiva ou negativa.

Exemplo:

```text
positivo = 0.35
negativo = 0.05
neutro = 0.60

sentimento = NEUTRAL
indice_sentimento = 0.30
```

No estado atual, o código calcula apenas o índice individual de cada notícia.

Agregações por data, empresa, setor ou indicador acumulado ainda não fazem parte desta versão.

---

## 12. Execução no Santos Dumont

O código Python não precisa ser alterado.

A diferença principal está na configuração do `executar_finbert.sh`.

### 12.1. Copiar o projeto

A pasta enviada ao SDumont deve conter:

```text
dados/
FinBERT-PT-BR/
executar_finbert.sh
finbert_inferencia.py
requirements.txt
setup_env.sh
README.md
```

O modelo já deve estar dentro da pasta do projeto.

### 12.2. Verificar os módulos disponíveis

No SDumont:

```bash
module avail
module spider python
module spider cuda
```

No `executar_finbert.sh`, ajuste estas linhas quando necessário:

```bash
# module purge
# module load python
# module load cuda
```

Use os nomes exatos dos módulos disponíveis para o projeto.

### 12.3. Configurar o Slurm

No início do `executar_finbert.sh`, remova um `#` das diretivas `##SBATCH` e ajuste os valores:

```bash
#SBATCH --job-name=finbert_ptbr
#SBATCH --output=logs/finbert_%j.out
#SBATCH --error=logs/finbert_%j.err
#SBATCH --account=SEU_PROJETO
#SBATCH --partition=SUA_PARTICAO
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --gres=gpu:1
#SBATCH --mem=32G
#SBATCH --time=00:30:00
```

Substitua:

```text
SEU_PROJETO
SUA_PARTICAO
```

pelos valores fornecidos no acesso ao SDumont.

### 12.4. Submeter

```bash
chmod +x setup_env.sh executar_finbert.sh
sbatch executar_finbert.sh
```

### 12.5. Acompanhar

```bash
squeue -u "$USER"
```

### 12.6. Consultar os logs

```text
logs/finbert_ID_DO_JOB.out
logs/finbert_ID_DO_JOB.err
```

Exemplo:

```bash
cat logs/finbert_123456.out
cat logs/finbert_123456.err
```

### 12.7. Consultar os resultados

```bash
head resultados/noticias_classificadas.csv
```

---

## 13. Comandos principais

Execução local:

```bash
./executar_finbert.sh
```

Execução no SDumont:

```bash
sbatch executar_finbert.sh
```