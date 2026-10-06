# Parte 0 — Enquadramento da pesquisa

## Em uma frase

Construir e validar empiricamente um **Índice Temporal Informacional (ITI)** a partir de notícias corporativas de empresas brasileiras de saneamento de capital aberto, testando se esse índice traz informação incremental sobre retornos futuros além de medidas simples (contagem de notícias e sentimento médio).

## Problema de pesquisa

Notícias financeiras em português carregam informação que o mercado pode precificar (Tetlock, 2007), mas medir isso de forma reprodutível exige: corpus ligado à empresa certa; classificador de domínio (Santos et al., 2023); agregação temporal coerente; comparação honesta com alternativas simples (Loughran & McDonald, 2011). No **saneamento**, o Marco Legal e a privatização da Sabesp geram choques informacionais intensos (Gattai & Souza, 2025 — estudo de evento em EQTL3) — contexto favorável para testar H1, pouco explorado com NLP em PT.

A literatura brasileira motiva o teste, mas não garante resultado: Duarte et al. (2020) comparam horizontes diário, semanal e mensal em 64 ativos; Yoshinaga & Castro Junior (2012) encontram relação entre índice de sentimento e retornos que pode ser **negativa** (reversão), não direcional.

## 0.1 Ancoragem teórica

O lab testa **associação incremental exploratória** entre texto agregado e retorno futuro — não eficiência informacional plena nem estratégia de trading. As teorias abaixo orientam hipóteses e limites de interpretação:

| Teoria | Referência | O que sustenta no lab | O que **não** afirmamos |
|--------|------------|----------------------|-------------------------|
| Mídia informa preços | Tetlock (2007) | H1 — texto carrega informação testável | Direção positiva garantida |
| Finanças comportamentais / sentimento | Yoshinaga (2012); Baker-Wurgler via Yoshinaga | Índice × retorno; reversão possível | ITI replica índice PCA de mercado |
| EMH forma semiforte | Gattai & Souza (2025) FOCO | Choque institucional relevante (privatização) | Nosso desenho **não** é event study CAR |
| NLP domínio financeiro | Araci (2019); Santos (2023) | FinBERT-PT-BR + score \(d\) | Acurácia do artigo = corpus saneamento |
| Correlação defasada BR | Marquezan & Assunção (2025); Duarte (2020) | Horizontes 1/2/4 sem.; lags variam | Causalidade Granger |

*Posicionamento:* medimos se um índice com memória (ITI) correlaciona melhor que baselines simples no mesmo painel; qualquer leitura de “mercado eficiente” ou “sentimento move preço” permanece condicional ao classificador e ao caráter exploratório dos resultados.

## Objetivo geral

Construir e validar empiricamente um ITI baseado em notícias corporativas para empresas de saneamento de capital aberto (Sabesp, Copasa, Sanepar no desenho inicial; **Trilha A** focou Sabesp/SBSP3).

## Perguntas e hipóteses

### Pergunta principal (QP1) → H1

Em que medida um ITI derivado de notícias corporativas representa choques informacionais em empresas de saneamento de capital aberto e apresenta associação com retorno, volatilidade e volume **além** de medidas simples de sentimento e frequência? *(Volatilidade/volume: no desenho original do direcionamento; não fechados na Trilha A.)*

**H1:** o ITI em uma semana associa-se ao retorno acumulado nas semanas seguintes **mais fortemente** que B0–B3 sobre as mesmas notícias — não é previsão mecânica de alta/baixa.

Qualquer associação ITI×retorno permanece **hipótese a testar**, não conclusão prévia: o mérito do classificador (FinBERT-PT-BR) limita o canal notícia→índice — ver gate κ em [§4.4](#44-qualidade-do-classificador).

### Perguntas secundárias

| ID | Pergunta | Hipótese | Status Trilha A |
|----|----------|----------|-----------------|
| QP2 | Notícias negativas associam-se mais a volatilidade/retorno? | **H2** (assimetria) | Não testada formalmente |
| QP3 | EWMA melhora validade vs impacto sem memória? | **H3** | Parcial — R1 vs B3, 2 sig. em h=4 |
| QP4 | Discordância entre modelos informa volatilidade? | Extensão | Não executada |

### Pergunta empírica central

**ITI/B3 acrescentam informação sobre retorno futuro além de B0, B1 e B2?** — medida pelo win rate em 24 duelos por run.

## Subobjetivos operacionais

| Subobjetivo | Pergunta operacional | Saída esperada | Status |
|-------------|---------------------|----------------|--------|
| SO1 — coleta | Scraper produz notícias deduplicadas e alinháveis? | Corpus tabular (título, data, link, empresa, texto) | Executado; qualidade residual documentada |
| SO2 — classificação | FinBERT PT produz sinal utilizável em saneamento? | Probabilidades e score \(d\) | Executado; **gate falhou** |
| SO3 — índice | Agregação e memória sem misturar frequências? | ITI diário/semanal, líquido e risco | Executado |
| SO4 — comparação | ITI vence B0–B3? | 24 duelos/run | Executado |
| SO5 — mercado | Sinal associa-se a retorno em frequência compatível? | Painel semanal Pearson/Spearman | Executado, exploratório |
| SO6 — ablação | Desempenho depende de α e componentes? | R0–R9 | Executado ([Apêndice A](appendices.md)) |
| SO7 — robustez | Resultado sobrevive expansão e lacuna 2023? | Evento vs expandido | Executado — **não generaliza** |
| SO8 — validade modelo | FinBERT concorda com humanos? | Acurácia, F1, κ (n=100) | Executado — κ=0,163 |
| SO9 — transparência | Evidência, decisão e lacuna distinguíveis? | Este documento | Executado |
| SO10 — literatura | Decisões ancoradas em refs BR | `references/` | Executado |

### SO → módulos (rastreio técnico)

| SO | Módulos principais | Docs |
| --- | --- | --- |
| SO1 | `scrapers`, `datasets` | [03_modulos §3.2/3.6](../documentation/03_modulos.md) |
| SO2 | `models`, `evaluation` | [04_formulas](../documentation/04_formulas_iti.md), κ em Parte 4 |
| SO3 | `experiment` | [04_formulas](../documentation/04_formulas_iti.md) |
| SO4–SO5 | `research`, `market` | [05_validacao](../documentation/05_validacao_research.md) |
| SO6–SO7 | `experiment`, campanhas | [part-03 F2/F4](part-03-phases.md), [appendices](appendices.md) |
| SO8 | `evaluation` | [annotation_protocol](../tracking/annotation_protocol.md) |
| SO9–SO10 | `docs/` | [research_trail](README.md), [references](../references/README.md) |

Pós-qualificação: [post_qualification_roadmap.md](../tracking/post_qualification_roadmap.md).

## 0.2 Matriz de ancoragem bibliográfica

Cada referência abaixo liga decisão metodológica a justificativa e à avaliação no contexto Sabesp.

| Referência | Decisão que sustenta | Justificativa | Avaliação |
|------------|---------------------|---------------|-----------|
| Santos (2023) | Classificador `finbert_ptbr` | Domínio PT + índice de sentimento | Justifica escolha; **não** garante κ no saneamento |
| Araci (2019) | Cadeia FinBERT | Pré-treino domínio EN → adaptação PT | Justifica família de modelos |
| Loughran (2011) | B0–B3 internos | Baselines simples antes de índice complexo | Parcial — usamos FinBERT, não léxico |
| Yoshinaga (2012) | Não fixar direção; precedente BR | Relação pode ser negativa (reversão) | Justifica cautela em H1 |
| Duarte (2020) | Múltiplos horizontes | Persistência da informação varia | Justifica protocolo semanal 1/2/4 |
| Marquezan & Assunção (2025) | Lags + tipo de notícia | Correlação cruzada BR com LLM | Justifica horizontes; método diferente (emoções LLM) |
| Gattai & Souza (2025) | Janela evento | Choque Sabesp/privatização | **Parcial** — EQTL3, não SBSP3; não é NLP |
| Tetlock (2007) | Validação texto×mercado | Mídia não é ruído puro | Inspiracional (métrica diferente) |

## Referências bibliográficas de base (direcionamento 20/08)

| Referência | Contribuição |
|------------|--------------|
| Baker, Bloom & Davis — EPU | Texto → índice → validação externa |
| Caldara & Iacoviello — GPR | Índice de risco jornalístico |
| Shapiro et al. — Fed News Sentiment | Sentimento diário com decaimento (analogia EWMA) |
| Araci — FinBERT; Santos et al. — FinBERT-PT-BR | NLP financeiro |
| FNSPID, FUNNEL | Escala notícia–preço; mapeamento notícia→empresa |
| Estudos de evento | Choques informacionais |
| Marco Legal do Saneamento; índices UTIL/ISE B3 | Contexto setorial BR |

## Mapa fase → pergunta → artefato

| Fase | Pergunta | Artefato |
|------|----------|----------|
| F0 | Pipeline roda? | `outputs/saneamento_pt_20260824/` |
| F1 | Protocolo interpretável? | `configs/campaigns/sabesp_2026/` |
| F2 | ITI vence baselines no evento? | `sabesp_r1_alpha070` |
| F3 | Sinal generaliza? | `sabesp_gap2023_*`, `period_breakdown_gap2023.md` |
| F4 | Roundups explicam teto? | `sabesp_event_r1_filtered` |
| F5 | Classificador confiável? | `manual_label_report.md`, `classifier_eval_pt/` |
| F6 | O que concluir? | **Parte 4** abaixo |

---

---

**Próximo:** [Parte 1 — ITI](part-01-iti.md)
