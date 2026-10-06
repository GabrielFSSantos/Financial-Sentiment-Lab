# Apêndice A — Runs R0–R9

Campanha `sabesp_2026`, dataset evento (465 artigos nas ablações R2–R9). Manifest: `configs/campaigns/sabesp_2026/manifest.yaml`.

| Run | ID | Mudança | Win rate (ref. Parte 4) | Notas |
| --- | --- | --- | --- | --- |
| R0 | `sabesp_r0_baseline` | ITI completo, α=0,85 (referência ablação) | 20,8% | Baseline de ablação |
| R1 | `sabesp_r1_alpha070` | α=0,70 (run principal evento) | 37,5% | Melhor win rate na Trilha A |
| R2–R9 | ver tabela abaixo | Ablações | — | |

## R2–R9 condensadas

| Run | ID | Mudança | Win rate | Δ vs R0 | Sig. |
|-----|-----|---------|----------|---------|------|
| R2 | `sabesp_r2_alpha095` | α=0,95 | 8,3% | −12,5 pp | 0 |
| R3 | `sabesp_r3_no_novelty` | sem u | 20,8% | 0 | 0 |
| R4 | `sabesp_r4_no_event` | sem e | 25,0% | +4,2 pp | 0 |
| R5 | `sabesp_r5_no_relevance` | sem r | 20,8% | 0 | 0 |
| R6 | `sabesp_r6_simplified` | d·c | 20,8% | 0 | 0 |
| R7 | `sabesp_r7_horizon_fixed` | α por h | 25,0% | +4,2 pp | 0 |
| R8 | `sabesp_r8_weekly_mean` | média semanal | 4,2% | −16,7 pp | 0 |
| R9 | `sabesp_r9_ensemble` | modelo PT alt. | 25,0% | +4,2 pp | 0 |

Só **α=0,70** (R1) produz ganho relevante. R8 confirma `iti_liquido_last`.

Configs: `configs/campaigns/sabesp_2026/experiments/r*.yaml`

---

# Apêndice B — Glossário e ordem de leitura

| Termo | Significado |
|-------|-------------|
| ITI | Índice Temporal Informacional |
| α | Memória EWMA (não alpha de mercado) |
| B0–B3 | Baselines internos — Parte 1 |
| Win rate | % vitórias em 24 duelos |
| Significativa | Bootstrap apoia diferença vs baseline |

**Ordem:** Parte 0 → 1 → 2 → 3 → **4** (números) → 5 → 6 → [documentation](../documentation/README.md) para fórmulas.

---

# Apêndice C — Direcionamento da pesquisa (20/08)

Texto integral do direcionamento inicial da pesquisa (agosto/2025).

## Em uma frase

Construir e validar empiricamente um **Índice Temporal Informacional (ITI)** a partir de notícias corporativas de empresas brasileiras de saneamento de capital aberto (Sabesp, Copasa, Sanepar), testando se esse índice traz informação incremental sobre retornos futuros além de medidas simples (contagem de notícias e sentimento médio).

## Objetivo principal

Construir e validar empiricamente um Índice Temporal Informacional baseado em notícias corporativas para empresas brasileiras de saneamento de capital aberto.

## Pergunta de pesquisa

### Pergunta principal (H1)

Em que medida um Índice Temporal Informacional derivado de notícias corporativas é capaz de representar choques informacionais em empresas de saneamento de capital aberto e apresentar associação com retorno, volatilidade e volume negociado, além de medidas simples de sentimento e frequência de notícias?

*Notas de escopo do direcionamento:* janela de dados de 2–3 meses; definir fontes e construir base de dados; avaliar impacto do modelo em relação às ações; matriz de correlação com IBOV para medir valor incremental da notícia além do movimento macro. Unidade notícia: header, link e sentimento.

### Perguntas secundárias

| ID | Pergunta | Hipótese / extensão |
|----|----------|---------------------|
| QP2 | Notícias negativas associam-se mais a volatilidade/retorno? | **H2** — assimetria |
| QP3 | Persistência temporal (EWMA) melhora validade vs agregação sem memória? | **H3** |
| QP4 | Discordância entre modelos (`iti_risco`/incerteza) informa volatilidade? | Extensão futura |

## Metodologia

### Unidade de análise

Empresa × dia, depois agregação setorial.

**Empresas-alvo:** Sabesp (SBSP3), Copasa (CSMG3), Sanepar (SAPR4).

### Pipeline científico

scraping → classificação NLP (FinBERT-PT-BR) → score contínuo \(d = P(pos) - P(neg)\) → impacto por notícia (dimensões \(m,r,e,c,u,q,h\)) → agregação diária (`impacto_dia`, `risco_dia`) → ITI com memória EWMA (`iti_liquido`, `iti_risco`) → alinhamento com preços B3 → validação vs baselines B0–B3.

### Baselines

| Baseline | O que é |
|----------|---------|
| B0 | Número de notícias no dia |
| B1 | Sentimento médio diário |
| B2 | Sentimento ponderado por confiança |
| B3 | Impacto diário sem memória |
| ITI | Impacto com persistência EWMA |

**Pergunta empírica central:** B3/ITI acrescentam informação sobre retorno futuro além de B0, B1 e B2?

## Referências bibliográficas de base

### Índices textuais macro (metodologia)

| Referência | Contribuição |
|------------|--------------|
| Baker, Bloom & Davis — Economic Policy Uncertainty | Frequência/cobertura jornalística → índice → validação externa |
| Caldara & Iacoviello — Geopolitical Risk Index | Índice de risco a partir de jornais |
| Shapiro, Sudhof & Wilson — Daily News Sentiment Index (Fed) | Sentimento diário com decaimento temporal — próximo da lógica EWMA do ITI |

### Sentimento financeiro e NLP

| Referência | Contribuição |
|------------|--------------|
| Araci et al. — FinBERT (ProsusAI) | Vocabulário financeiro; baseline para modelos EN |
| FinBERT-PT-BR (Santos et al.) | Modelo usado no projeto para notícias em português |
| FNSPID (2024) | Integração notícia–preço em escala; infraestrutura de dados |
| FUNNEL (2025) | Mapear notícia → empresa corretamente; deduplicação |

### Mercado e validação empírica

| Referência | Contribuição |
|------------|--------------|
| Estudos de evento (event study) | Metodologia clássica para reação a choques informacionais |
| Literatura ESG + mercado | Assimetria: notícias negativas reagem mais |
| Trabalhos petróleo + sentimento | Referência comparativa (mostra o que não repetir como foco principal) |

### Contexto setorial Brasil

| Referência / fonte | Contribuição |
|--------------------|--------------|
| Marco Legal do Saneamento | Justificativa regulatória e volume de notícias |
| Índice UTIL B3 | Controle setorial amplo (energia + saneamento + gás) |
| ISE B3 | Referência de sustentabilidade, não de sentimento |

---

# Apêndice D — Índice de artefatos `outputs/`

| Artefato | Caminho |
|----------|---------|
| Comparação gap 2023 | `outputs/campaigns/sabesp_marco2/gap2023_comparison.md` |
| Subperíodos | `outputs/campaigns/sabesp_marco2/period_breakdown_gap2023.md` |
| Vitórias sig. R1 | `outputs/campaigns/sabesp_marco2/significant_wins_r1_event.md` |
| Erro classificador | `outputs/campaigns/classifier_eval_pt/error_analysis.md` |
| Runs expandidas | `outputs/sabesp_gap2023_r0_baseline/`, `sabesp_gap2023_r1_alpha070/` |
| Runs evento sanity | `outputs/sabesp_gap2023_event_r0_baseline/`, `sabesp_gap2023_event_r1_alpha070/` |
| Run filtrada | `outputs/sabesp_event_r1_filtered/` |
| Bateria κ | `outputs/campaigns/classifier_eval_pt/` |
| Scripts | `scripts/campaigns/sabesp_marco2.sh`, `classifier_eval_pt.sh` |
| Manifest Marco 1 | `outputs/campaigns/sabesp_2026/manifest.json` |

Reprodução: [configs/campaigns/sabesp_marco2/README.md](../../configs/campaigns/sabesp_marco2/README.md)

---

# Apêndice E — Bibliografia comentada

| Referência | Uso | PDF local | Nota |
|------------|-----|-----------|------|
| Santos et al. (2023) | FinBERT-PT-BR, índice | [pdfs/santos2023_finbert_ptbr.pdf](../references/pdfs/santos2023_finbert_ptbr.pdf) | [notas/santos2023.md](../references/notas/santos2023.md) |
| Yoshinaga & Castro Junior (2012) | Índice BR × retorno | [pdfs/yoshinaga2012_bar.pdf](../references/pdfs/yoshinaga2012_bar.pdf) | [notas/yoshinaga2012.md](../references/notas/yoshinaga2012.md) |
| Duarte et al. (2020) | Horizontes BR | [pdfs/duarte2020_quedas_b3.pdf](../references/pdfs/duarte2020_quedas_b3.pdf) | [notas/duarte2020.md](../references/notas/duarte2020.md) |
| Tetlock (2007) | Mídia × mercado | [pdfs/tetlock2007_media.pdf](../references/pdfs/tetlock2007_media.pdf) | [notas/tetlock2007.md](../references/notas/tetlock2007.md) |
| Loughran & McDonald (2011) | Baselines | [pdfs/loughran2011_baselines.pdf](../references/pdfs/loughran2011_baselines.pdf) | [notas/loughran2011.md](../references/notas/loughran2011.md) |
| Gattai & Souza (2025) FOCO | Evento Sabesp | [pdfs/gattai2025_privatizacao_sabesp.pdf](../references/pdfs/gattai2025_privatizacao_sabesp.pdf) | [notas/foco2025.md](../references/notas/foco2025.md) |
| Araci (2020) | FinBERT EN | [pdfs/araci2020_finbert.pdf](../references/pdfs/araci2020_finbert.pdf) | [notas/araci2020.md](../references/notas/araci2020.md) |
| Demais | Ver [references/README.md](../references/README.md) | link only | `bibliografia.bib` |

Fora de escopo Trilha A (trabalhos futuros): FNSPID, FinMarBa, PhraseBank/NOSIBLE.

---

*Última consolidação: documento único Trilha A — Financial Sentiment Lab.*
