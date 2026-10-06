# Parte 3 — Trajetória por fases

Padronização: [phase-template.md](phase-template.md). Decisões resumidas: [decision-register.md](decision-register.md).

## Transições entre fases

| De → Para | Gatilho (critério de saída) |
| --- | --- |
| F0 → F1 | Pipeline executa, mas comparação ITI×mercado inválida (frequências mistas) — auditoria obrigatória |
| F1 → F2 | Protocolo semanal + campanha `sabesp_2026` + YAML research_weekly implementados |
| F2 → F3 | Runs R0/R1 interpretáveis; manifest e research no modo semanal |
| F3 → F4 | Necessidade de corpus evento filtrado (roundups) e janelas expandidas |
| F4 → F5 | Gate κ não atingido — pivot para validação de classificador, não fine-tune |
| F5 → F6 | Bateria PT documentada; síntese para qualificação |

| Fase | run_id (exemplo) | Config principal |
| --- | --- | --- |
| F0 | `saneamento_pt_20260824` | core + corpus multi-empresa |
| F1–F2 | `sabesp_r0_baseline`, `sabesp_r1_event` | `configs/campaigns/sabesp_2026/` |
| F4 | `sabesp_event_r1_filtered` | filtro + `event_corpus_filter.py` |

Números oficiais: sempre [part-04-results.md](part-04-results.md).

## F0 — Marco amplo: provar que o pipeline roda

### Pergunta
É possível executar scraping → CSV → inferência → índices → research antes de validade estatística?

### Base bibliográfica
Neuenschwander et al. (2014): extração de sinal de fluxos web é difícil no BR. Duarte et al. (2020): horizontes múltiplos são necessários. UTFPR (2024): causalidade pode ser fraca — expectativa realista. Araci (2019) → Santos (2023): cadeia FinBERT domínio EN→PT.

### Literatura → resultado

Neuenschwander (2014) e UTFPR (2024) sustentam que extrair sinal de texto web no BR é difícil e a associação com preços pode ser fraca; Duarte (2020) sustenta testar múltiplos horizontes. **Nosso resultado confirma** que o pipeline executa (SO1), mas **nega** comparação válida com mercado (0% win, frequências incompatíveis).

### Entradas e decisões

| Item | Valor |
|------|-------|
| Run | `saneamento_pt_20260824` |
| Corpus | `saneamento_corpus` multi-empresa (Sabesp, Copasa, Sanepar) |
| Research | Frequência **diária** (ITI semanal gerado mas não usado na validação) |
| Modelos | `finbert_ptbr`, `pt_br_financial_sentiment_analysis` |

FinBERT-PT-BR escolhido por domínio financeiro PT (Santos et al., 2023) — modelos especializados superam genéricos para jargão econômico; validação externa via preços é prática recomendada na literatura de sentimento.

### Resultados

| Modelo | Win rate | Significativas |
|--------|----------|----------------|
| `finbert_ptbr` | 0% (0/24) | 0 |
| `pt_br_financial_sentiment_analysis` | 12,5% (3/24) | 0 |

### Obtidas / não obtidas / direcionamento

- **Obtido:** SO1 — pipeline executável.
- **Não obtido:** H1; comparação inválida (frequências misturadas).
- **Direcionamento:** auditoria F1.

**Artefatos:** `outputs/saneamento_pt_20260824/`

**Código tocado:** `scrapers/`, `datasets/`, `experiment/runner`, `research/` (modo diário legado).

**Gatilho F0→F1:** win rate 0% com frequências ITI×mercado incompatíveis — ver tabela de transições no topo.

---

## F1 — Auditoria e protocolo comparável

### Pergunta
Quais erros impedem comparação defensável ITI × mercado?

### Base bibliográfica
Duarte et al. (2020): lags variam no tempo. Yoshinaga (2012): associação pode ser reversão — não fixar direção a priori. Tetlock (2007): alinhamento temporal correto.

### Literatura → resultado

Duarte (2020) sustenta múltiplas janelas; Yoshinaga (2012) sustenta não fixar direção; Tetlock (2007) sustenta alinhamento temporal correto; Loughran (2011) sustenta baselines simples pré-definidos. **Nosso resultado confirma** o protocolo semanal comparável; **ainda não confirma** H1.

### Decisões

| Decisão | Alternativa rejeitada | Fundamento |
|---------|----------------------|------------|
| Sabesp focal (Trilha A) | Multi-empresa no resultado | Evento institucional específico |
| Frequência semanal | ITI semanal vs alvo diário | Incompatibilidade eliminada |
| B0–B3 ex ante | Baselines pós-hoc | Loughran: controles simples pré-definidos |
| Pearson + Spearman | Só Pearson | Associação linear e monotônica |
| Horizontes 1/2/4 sem | Lag único | Duarte: múltiplas janelas |
| Gate pré-evento ≥40% win | Expansão automática | Só expandir com sinal mínimo |

### Obtidas / direcionamento

- **Obtido:** campanha `sabesp_2026`, protocolo semanal, 24 duelos.
- **Não obtido:** evidência de H1 (ainda).
- **Direcionamento:** F2 primeira execução interpretável.

**Artefatos:** `configs/campaigns/sabesp_2026/`, `noticias_strict_sabesp.csv`

---

## F2 — Campanha Sabesp evento (R0 / R1)

### Pergunta
Na janela da privatização, EWMA (α=0,70) acrescenta informação além de B0–B3? (H3)

### Base bibliográfica
Gattai & Souza (2025): anúncio privatização → retornos anormais EQTL3 (não prova canal notícia→SBSP3). Santos (2023): FinBERT + índice. Yoshinaga (2012): “vencer” ≠ retorno positivo futuro.

### Literatura → resultado

Gattai & Souza (2025) sustentam relevância institucional do evento (EQTL3, não SBSP3); Santos (2023) sustenta FinBERT+índice em PT; Yoshinaga (2012) sustenta cautela com direção. **Nosso resultado confirma parcialmente** H3 (2 sig. vs B3, h=4) e melhor α=0,70; **não confirma** H1 forte nem causalidade — leitura exploratória.

**Distinção metodológica FOCO:** Gattai & Souza (2025) aplicam EMH semiforte com **CAR** em EQTL3 no anúncio da privatização; nós medimos **correlação semanal** ITI×retorno futuro em SBSP3 no mesmo período institucional. Os desenhos são **complementares** (contexto vs canal notícia→índice), não replicáveis um pelo outro.

### Entradas

| Item | Valor |
|------|-------|
| Dataset | `saneamento_sabesp_strict_event` |
| Período | nov/2023 – abr/2024 (~465 artigos) |
| Runs | R0 `sabesp_r0_baseline` (α=0,85); R1 `sabesp_r1_alpha070` (α=0,70) |

### Resultados

| Run | α | Win rate | Significativas |
|-----|---|----------|----------------|
| R0 | 0,85 | 20,8% (5/24) | 0 |
| **R1** | **0,70** | **41,7% (10/24)** | **2** |

**Vitórias significativas R1:** h=4 vs B3 — Pearson Δ=+0,133 (p=0,040); Spearman Δ=+0,221 (p=0,046).

**ITI vs baselines R1:**

| Baseline | 1 sem (P/S) | 2 sem (P/S) | 4 sem (P/S) |
|----------|-------------|-------------|-------------|
| B0 | ✗/✓ | ✗/✗ | ✗/✗ |
| B1 | ✗/✗ | ✗/✗ | ✗/✓ |
| B2 | ✗/✗ | ✗/✓ | ✗/✓ |
| B3 | ✓/✓ | ✓/✓ | **★/★** |

★ = significativa (bootstrap).

### Obtidas / não obtidas / direcionamento

- **Obtido:** melhor config (α=0,70, `iti_liquido_last`); gate ≥40% → autoriza F3; H3 parcial (2 sig. vs B3).
- **Não obtido:** H1 forte; causalidade; H2; ITI não domina todas as comparações.
- **Direcionamento:** F3 robustez temporal; F5 qualidade classificador.

**Artefatos:** `outputs/sabesp_r0_baseline/`, `outputs/sabesp_r1_alpha070/`

---

## F3 — Expansão temporal e lacuna 2023

### Pergunta
O sinal sobrevive mai/2022–abr/2024 com lacuna jan–abr/2023 preenchida?

### Base bibliográfica
Duarte et al. (2020): persistência da informação varia. RACEf (2022): associação sentimento–mercado mais forte em crises/eventos.

### Literatura → resultado

Duarte (2020) sustenta que persistência varia por horizonte; RACEf (2022) sustenta sensibilidade em períodos de crise/evento. **Nosso resultado confirma** reprodução do evento no sanity; **nega** robustez no expandido (33,3%, 0 sig.).

### Resultados (resumo — detalhe na Parte 4)

| Contexto | R1 win rate | Sig. |
|----------|-------------|------|
| Evento (referência) | **41,7%** | **2** |
| Marco 2 expandido (1.055 art.) | 20,8% | 0 |
| Gap 2023 (1.254 art.) | 33,3% | 0 |
| Sanity evento pós-gap | **41,7%** | **2** |

Subperíodos R1 expandido (h=1): pré-evento 2022 Pearson −0,148; interregno 2023Q1 +0,172 (n=15); evento isolado no expandido −0,030.

### Obtidas / direcionamento

- **Obtido:** mais dados ≠ melhor sinal; sanity reproduz evento.
- **Não obtido:** vitória robusta no expandido.
- **Direcionamento:** F4 filtro roundups.

**Artefatos:** `outputs/sabesp_gap2023_*`, `gap2023_comparison.md`, `period_breakdown_gap2023.md`

---

## F4 — Robustez textual e múltiplas comparações

### Pergunta
Remover roundups/agendas melhora o sinal? As 2 sig. resistem à leitura de busca múltipla?

### Base bibliográfica
Neuenschwander (2014): pré-processamento não trivial. Marquezan & Assunção (2025): sinal varia por tipo de notícia e **lag** — heterogeneidade por defasagem é precedente BR direto.

### Literatura → resultado

Neuenschwander (2014) e Marquezan & Assunção (2025) sustentam que tipo de notícia e pré-processamento afetam o sinal; ERAMIARS prevê heterogeneidade por lag — coerente com vitórias significativas **apenas** em h=4 (não em h=1 ou h=2). **Nosso resultado nega** que roundups expliquem o teto (filtro piora para 25%, 0 sig.); 2/24 sig. permanecem exploratórias.

### Resultado

| Run | Artigos | R1 win rate | Sig. |
|-----|---------|-------------|------|
| Evento base | 465 | 41,7% | 2 |
| Evento filtrado | 404 (−61 roundups) | **25,0%** | **0** |

### Obtidas / direcionamento

- Filtro **piora** ITI — teto ~41,7% não é só “lixo textual”.
- 2/24 sig. permanecem leitura exploratória cautelosa.
- **Direcionamento:** F5 validade FinBERT.

**Artefatos:** `outputs/sabesp_event_r1_filtered/`, `significant_wins_r1_event.md`

**Código tocado:** `modules/evaluation/event_corpus_filter.py`, overlay datasets em `configs/campaigns/sabesp_2026/`.

**Gatilho F4→F5:** filtro de roundups não explica vitórias significativas; próximo passo é gate κ (SO8).

---

## F5 — Validade do classificador

### Pergunta
FinBERT concorda com humanos o suficiente (gate 70% / κ≥0,40)?

### Base bibliográfica
Santos et al. (2023): FinBERT de domínio financeiro PT; desempenho depende do corpus de aplicação.

### Literatura → resultado

Santos (2023) sustenta FinBERT de domínio, com ressalva de corpus de aplicação. **Nosso resultado nega** transferência ao saneamento (κ=0,163; nenhum modelo passa gate) — **limita interpretação substantiva** de todo resultado de mercado anterior.

### Resultado (n=100)

| Modelo | Acurácia | κ | Passa gate? |
|--------|----------|---|-------------|
| `finbert_ptbr` | 48,0% | 0,163 | não |
| `bertweet_pt_sentiment` | 68,0% | −0,014 | não |
| `bertimbau_sentiment` | 53,0% | 0,087 | não |

κ focal FinBERT: 0,217 (ainda abaixo do gate). Tipologia: 74% focal_sabesp, 26% roundup_agenda.

### Obtidas / direcionamento

- Transferência FinBERT→saneamento **não demonstrada** nesta amostra.
- ITI condicional com controles PT **não executado** (correto).
- **Direcionamento:** F6 síntese; sem fine-tune neste ciclo.

**Artefatos:** `manual_label_report.md`, `classifier_eval_pt/`

---

## F6 — Síntese processual da Trilha A

### Literatura → resultado

Literatura BR (Yoshinaga, Duarte, UTFPR) sustenta a **pergunta** e o desenho; não garante resultado positivo. **Nosso resultado confirma** prova de conceito de engenharia; **nega** validação confirmatória de H1/H3 fora do patamar exploratório do evento.

Prova de conceito de engenharia + resultado exploratório localizado no evento — **não** validação confirmatória. A interpretação substantiva de qualquer associação ITI×mercado fica **limitada** pelo gate κ do classificador ([§4.4](#44-qualidade-do-classificador)). Direção estratégica: (i) preservar evento como exploratório; (ii) não vender expandido como robustez; (iii) sem fine-tune sem ampliar anotação; (iv) separar H2/volatilidade do resultado principal; (v) literatura BR como comparação de desenho, não prova do ITI.

Números fechados: **Parte 4**.

---

---

**Próximo:** [Parte 4 — Resultados](part-04-results.md)
