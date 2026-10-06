# Parte 1 — ITI: origem metodológica

O ITI **não é um índice publicado nem homônimo importado**. É construção operacional em [temporal_index.py](../modules/experiment/indexing/temporal_index.py) para saneamento: sentimento por notícia → impacto informacional → agregação diária → memória EWMA.

| Elemento | Base bibliográfica | Transferido | Adaptado (Sabesp) |
|----------|-------------------|-------------|-------------------|
| Texto → mercado | Tetlock (2007) | Mídia carrega informação | Multiportal PT, NLP |
| Índice textual temporal | Baker et al. (2016) EPU | Agregação + validação | Microíndice empresa |
| Sentimento PT | Santos et al. (2023) | FinBERT-PT-BR, \(d=P(pos)-P(neg)\) | Corpus saneamento |
| Precedente índice BR | Yoshinaga (2012) | Índice sentimento × retorno | ITI não usa PCA agregado |
| Horizontes múltiplos | Duarte et al. (2020) | Lags diário/semanal/mensal | 1/2/4 semanas |
| Persistência | Shapiro et al. (2022) | Decaimento temporal | α por ablação (R0 vs R1) |
| Controles simples | Loughran & McDonald (2011) | Medidas textuais simples | B0–B3 internos |
| Evento | Gattai & Souza (2025) | Reação a privatização | Alvo SBSP3, não EQTL3 |

**Mensagem:** se ITI não supera B0–B3 no mesmo painel, memória e dimensões extras não demonstram valor incremental. Yoshinaga mostra alternativa (PCA); ITI preserva interpretação operacional empresa×dia.

## 1.1 Definições sem ambiguidade

- **Score por notícia:** \(d = P(\text{pos}) - P(\text{neg})\). Neutro permanece nas probabilidades.
- **Impacto diário:** combinação de scores e dimensões (`m,r,e,c,u,q,h`) — ver [documentacao §4](../documentation/04_formulas_iti.md).
- **ITI líquido:** estado EWMA do impacto líquido — predictor principal (`iti_liquido_last` na validação semanal).
- **ITI risco:** componente negativo/risco — complementar, não usado no resultado principal.
- **B0:** contagem de notícias; **B1:** média de \(d\); **B2:** média ponderada por confiança; **B3:** impacto diário **sem** memória.
- **α:** memória EWMA — **não** é alpha de excesso de retorno. α alto = mais passado; α baixo = mais reativo. Escolha operacional α=0,70 (R1) vs 0,85 (R0): ablação F2 em [part-03](part-03-phases.md) e [appendices](appendices.md); fórmulas e colunas: [04_formulas_iti §4.2](../documentation/04_formulas_iti.md).
- **Vitória:** ITI correlaciona melhor que baseline (mesmo horizonte e métrica).
- **Significância:** bootstrap em bloco apoia a diferença — **não** implica causalidade.

## 1.2 Por que FinBERT e não léxico/LSTM

- **Araci → Santos:** Araci (2019) estabelece FinBERT em inglês com vocabulário de domínio; Santos et al. (2023) estendem a português com Gradual Unfreezing e validam índice de sentimento — cadeia que justifica `finbert_ptbr` como classificador principal.
- **Loughran & McDonald (2011):** dicionários genéricos falham em finanças (polissemia de “liability”, “risk” etc.) — evitamos léxico fixo; B0–B3 derivam do **mesmo** classificador para comparação justa.
- **LSTM (Araújo et al., 2021):** precedente BR em Twitter com redes recorrentes — **não adotado**: corpus multiportal de notícias + estado da arte BERT (Santos supera baselines no artigo de origem).

## 1.3 Tensões na literatura (o que esperar)

A literatura BR não converge em direção única. Yoshinaga & Castro Junior (2012) encontram relação **negativa** entre índice de sentimento agregado e retorno futuro (padrão de reversão). Marquezan & Assunção (2025), com emoções via LLM e correlação cruzada, reportam lags heterogêneos — sentimento pode **anteceder** preço em alguns ativos e defasagens. **Leitura para Trilha A:** direção e magnitude são empíricas; subperíodos mistos na janela expandido ([§4.3](#43-robustez-janela-expandida)) são compatíveis com ambos os quadros, não prova de inconsistência metodológica.

---

---

**Próximo:** [Parte 2 — Protocolo](part-02-protocol.md)
