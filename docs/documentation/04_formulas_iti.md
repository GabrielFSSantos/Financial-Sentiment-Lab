# 04 Formulas Iti

## 4. Fórmulas do ITI

Com os conceitos da [§1.5](#15-conceitos-em-linguagem-acessível) em mente, esta seção formaliza o cálculo implementado no código.

Implementação: `modules/experiment/indexing/temporal_index.py`  
Dimensões: `modules/experiment/indexing/dimensions.py`  
Parâmetros: `configs/experiment.yaml` → `temporal_index`

### 4.1 Variáveis por notícia

| Símbolo | Nome | Descrição |
| --- | --- | --- |
| \(d\) | sentimento contínuo | \(P_{pos} - P_{neg}\) |
| \(c\) | confiança | max(probabilidades) ou coluna `confidence` |
| \(m\) | magnitude | dimensão de escala do evento |
| \(r\) | relevância | peso de relevância editorial |
| \(e\) | event_weight | peso por tipo de evento (heurística) |
| \(u\) | novelty | novidade vs títulos já vistos |
| \(h\) | horizon | horizonte temporal inferido do texto |
| \(q\) | risk | peso de risco (eventos negativos) |

Dimensões resolvem-se na ordem `dataset_columns` → `prediction_metadata` → `heuristics` → `defaults`.

#### 4.1.1 Resolução de dimensões (`dimensions.py`)

Implementação: `resolve_dimensions()` com `provider_order` configurável em `temporal_index.dimensions`.

| Provider | Fonte | Comportamento |
| --- | --- | --- |
| `dataset_columns` | Colunas `m,r,e,c,u,q,h` no CSV | Valores numéricos diretos |
| `prediction_metadata` | JSON em `prediction_metadata` | Aliases por dimensão |
| `heuristics` | Título + corpo + metadados | Regras abaixo |
| `defaults` | YAML `dimensions.defaults` | Fallback constante |

**Heurísticas** (`_apply_heuristics`), por notícia:

| Dim | Regra |
| --- | --- |
| **r** (relevância) | Ticker no texto → 1,0; nome da empresa no texto → 0,85; só empresa no metadado → 0,65 |
| **m** (magnitude) | `min(2.0, \|d\|·c + 0.15)` |
| **e** (event_weight) | Match em `event_keywords` (regulacao, investimento, tarifa, privatizacao) → até 1,15 |
| **u** (novelty) | Título inédito no run (`seen_titles`) → 1,0; repetido → ≤ 0,75 |
| **q** (risk) | Palavras de risco (`multa`, `fraude`, `crise`, …) ou d &lt; 0 → 1,1 |
| **h** (horizon) | Keywords curto prazo → min 0,75; longo prazo → max 1,25 |

`disabled_dimensions` no YAML zera o efeito da dimensão (valor neutro 1,0 na multiplicação) — usado nas ablações R3–R5 (§4.7).

### 4.2 Impacto por notícia

**Impacto líquido:**

\[
I_n = d \cdot m \cdot r \cdot c \cdot e \cdot u
\]

**Impacto de risco** (só lado negativo do sentimento):

\[
R_n = \max(0,\,-d) \cdot m \cdot r \cdot c \cdot q
\]

**Peso da notícia:**

\[
w_n = c \cdot r \cdot u
\]

### 4.3 Agregação diária (empresa)

Para cada `(empresa, setor, data)`:

\[
\text{impacto\_dia} = \frac{\sum I_n w_n}{\sum w_n}
\quad\text{(ou média de } I_n \text{ se } \sum w_n = 0\text{)}
\]

\[
\text{risco\_dia} = \frac{\sum R_n w_n}{\sum w_n}
\quad\text{(ou média de } R_n \text{ se } \sum w_n = 0\text{)}
\]

### 4.4 Memória EWMA — `iti_liquido` e `iti_risco`

Parâmetro base \(\alpha\) (default `0.85`). A série é preenchida em **calendário contínuo** entre a primeira e a última data com notícia da empresa — dias sem notícia aplicam decay puro.

#### Modo `horizon_mode`

| Modo | Config | \(\alpha_{\text{eff}}\) em dia com notícia |
| --- | --- | --- |
| `ewma_alpha` | padrão (`experiment.yaml`) | \(\text{clip}(\alpha^{1/h},\ 0.01,\ 0.999)\) com `mean_horizon` do dia |
| `fixed` | R7 (`r7_horizon_fixed.yaml`) | \(\alpha_{\text{eff}} = \alpha\) — ignora h |

Com notícias no dia (`horizon_mode: ewma_alpha`):

\[
\alpha_{\text{eff}} = \text{clip}\left(\alpha^{1/h},\ 0.01,\ 0.999\right)
\]

**Dia com notícia:**

\[
\text{iti\_liquido}_t = \alpha_{\text{eff}} \cdot \text{iti\_liquido}_{t-1} + (1-\alpha_{\text{eff}}) \cdot \text{impacto\_dia}_t
\]

\[
\text{iti\_risco}_t = \alpha_{\text{eff}} \cdot \text{iti\_risco}_{t-1} + (1-\alpha_{\text{eff}}) \cdot \text{risco\_dia}_t
\]

**Dia sem notícia** (decay com α base):

\[
\text{iti\_liquido}_t = \alpha \cdot \text{iti\_liquido}_{t-1}, \quad \text{iti\_risco}_t = \alpha \cdot \text{iti\_risco}_{t-1}
\]

#### Resample (`temporal_index.resample`)

`resample_iti_series()` agrega `iti_daily` para W-FRI, mensal ou trimestral. Colunas geradas por período:

| Coluna | Significado |
| --- | --- |
| `iti_liquido_last` | Último valor diário da semana (padrão research semanal) |
| `iti_liquido_mean` | Média dos dias da semana (testado em R8) |
| `iti_liquido_min` / `max` / `std` | Estatísticas do período |
| `impacto_dia_mean` / `sum` | Agregados do impacto bruto |

#### Incerteza multi-modelo (`uncertainty`)

Quando `uncertainty.enabled: true` e ≥ `min_models` (default 2) modelos inferem o mesmo dataset:

1. Variância de \(d\) entre modelos por `news_id`.
2. Agregação diária → `iti_uncertainty_daily.csv` (`disagreement_mean`, `disagreement_max`).

Usado em análises complementares; **não** é predictor principal na Trilha A.

### 4.5 Agregação setor e mercado

Médias diárias de `impacto_dia`, `risco_dia`, `iti_liquido`, `iti_risco` entre empresas do nível.

### 4.6 Baselines (validação)

| Baseline | Coluna | Fórmula |
| --- | --- | --- |
| B0 | `b0_news_count` | contagem de notícias no dia |
| B1 | `b1_mean_sentiment` | média de \(d\) no dia |
| B2 | `b2_confidence_weighted_sentiment` | \(\sum(d \cdot c) / \sum c\) |
| B3 | `b3_daily_impact_no_memory` | `impacto_dia` (sem EWMA) |

B0–B2 são gerados no experimento; B3 é derivado no research. B0–B2 são avaliados **apenas em dias com notícia** (`baseline_news_only` em `configs/research.yaml`).

**Agregação semanal W-FRI** (`resample_baselines_weekly` em `indexing/baselines.py`):

| Baseline | Regra semanal |
| --- | --- |
| B0 | **soma** das contagens diárias |
| B1 | **média** do sentimento diário |
| B2 | **média** do ponderado diário |
| B3 | `impacto_dia` no painel alinhado (sem EWMA; derivado em `validation/baselines.py`) |

### 4.7 Ablações da equação

A equação completa usa todas as dimensões em \(I_n\), \(R_n\) e \(w_n\). Para testar hipóteses isoladas (campanha Sabesp R3–R6), o YAML de experimento aceita:

| Mecanismo | Efeito | Exemplo na campanha |
| --- | --- | --- |
| `disabled_dimensions` | Zera dimensões na fórmula (ex.: `novelty`, `event_weight`) | R3 sem `u`, R4 sem `e`, R5 sem `r` |
| `equation_mode: simplified_dc` | `I_n = d \cdot c`, `w_n = c` (sem m, r, e, u) | R6 |

O modo simplificado e as dimensões desabilitadas alteram apenas o cálculo de impacto por notícia; a memória EWMA (§4.4) permanece igual.

### 4.8 Mapa símbolo → código → CSV

| Conceito | Função Python | Colunas CSV |
| --- | --- | --- |
| \(I_n, R_n, w_n\) | `build_news_impact_frame()` | — (intermediário) |
| Dimensões m,r,e,u,h,q | `resolve_dimensions()` em `dimensions.py` | `prediction_metadata` |
| `impacto_dia`, `risco_dia` | `compute_daily_company_impact()` | `iti_daily.csv` |
| EWMA ITI | `compute_iti_daily_series()` | `iti_liquido`, `iti_risco` |
| Resample semanal | `resample_iti_series()` | `iti_resampled_weekly.csv`, `iti_weekly.csv` |
| B0–B2 | `build_baselines_daily()` | `baselines_daily.csv` |
| B3 | `add_b3_column()` em `research/validation/baselines.py` | `aligned_panel.csv` |
| Sentimento \(d\) | `calculate_continuous_sentiment()` | `continuous_sentiment` em `predictions.csv` |

Regras de negócio (24 duelos, modos diário/semanal): [12_regras_de_negocio.md](12_regras_de_negocio.md).

---
