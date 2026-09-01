# Síntese Trilha A — Sabesp (ITI × mercado)

Documento de fechamento da Trilha A após Marcos 1–3, atualização de corpus (lacuna 2023) e bateria de classificadores PT. Números extraídos de `outputs/` — não editar manualmente os CSVs de research.

**Relacionados:** [trajetoria.md](trajetoria.md) (histórico run a run), [documentacao.md](documentacao.md) (protocolo técnico).

---

## 1. Protocolo

| Item | Valor |
|------|-------|
| Empresa | Sabesp (`SBSP3.SA`) |
| Corpus strict | `data/saneamento_corpus/noticias_strict_sabesp.csv` |
| Classificador principal | `finbert_ptbr` |
| ITI | EWMA α configurável; agregação semanal `iti_liquido_last` |
| Baselines | B0–B3 (somente notícias) |
| Validação | Pearson + Spearman, horizontes 1/2/4 **semanas** (24 comparações) |
| Significância | Bootstrap em bloco (`block_size=2`, `n_bootstrap=500`) |
| Research | `configs/campaigns/sabesp_2026/research_weekly.yaml` |

Detalhes conceituais: [documentacao.md §1.5](documentacao.md#15-conceitos-em-linguagem-acessível).

---

## 2. Resultado principal (janela evento)

**Janela:** nov/2023–abr/2024 (`saneamento_sabesp_strict_event`, ~465 artigos).

| Run | run_id | Win rate R1 | Significativas |
|-----|--------|-------------|----------------|
| Marco 1 | `sabesp_r1_alpha070` | **41,7%** | **2** |
| Sanity corpus 1.254 | `sabesp_gap2023_event_r1_alpha070` | **41,7%** | **2** |
| Filtro roundups | `sabesp_event_r1_filtered` | 25,0% | 0 |

O sanity **reproduz** o Marco 1 após preencher a lacuna jan–abr/2023 no CSV expandido — a janela evento no arquivo não mudou.

**Vitórias significativas** (métricas de conclusão, `significant_wins_r1_event.md`):

| Horizonte | Baseline | Métrica | Δ | p-value |
|-----------|----------|---------|---|---------|
| 4 sem. | B3 | Pearson | +0,133 | 0,040 |
| 4 sem. | B3 | Spearman | +0,221 | 0,046 |

*Caveat:* 2/24 comparações — compatível com busca múltipla (ver §5).

**Leitura:** a privatização permanece a janela economicamente interpretável com o melhor desempenho do ITI neste desenho.

---

## 3. Robustez e limitação (janela expandida)

**Janela:** mai/2022–abr/2024 (`saneamento_sabesp_strict_expanded`).

| Corpus | Artigos | R1 win rate | Δ vs Marco 2 |
|--------|---------|-------------|--------------|
| Marco 2 (sem lacuna 2023) | 1.055 | 20,8% | — |
| Gap 2023 preenchido | **1.254** | **33,3%** | +12,5 pp |

| Run gap 2023 | R0 | R1 |
|--------------|----|----|
| Expandido | 4,2% (1/24) | **33,3%** (8/24) |

**Subperíodos** (`period_breakdown_gap2023.md`, R1 expandido, três buckets):

| Bucket | Semanas | Pearson | Spearman |
|--------|---------|---------|----------|
| `pre_evento_2022` | 25 | −0,148 | −0,110 |
| `interregno_2023q1` | 15 | +0,172 | +0,304 |
| `evento_nov23_abr24` | 50 | −0,030 | +0,054 |

O bucket antigo `evento_2023_2024` **misturava** jan–abr/2023 (lacuna) com nov/2023–abr/2024, inflando o “evento”. O interregno 2023Q1 tem correlação positiva exploratória, mas n=15 semanas — leitura cautelosa.

**Vitórias significativas R1 evento** (métricas de conclusão Pearson/Spearman): ver `outputs/campaigns/sabesp_marco2/significant_wins_r1_event.md`. As 2 vitórias (h=4 vs. B3) cabem em **busca múltipla** das 24 comparações — não tratar como confirmação forte isolada.

**Leitura para a tese:** expandido = robustez/limitação (“mais dados ≠ melhor sinal”); **não** vender como vitória do ITI.

---

## 4. Qualidade do classificador (Marco 3 + bateria PT)

### Marco 3 (FinBERT × humano, 100 notícias)

| Métrica | Valor | Gate |
|---------|-------|------|
| Acurácia | 48% | < 70% |
| Cohen's κ | 0,163 | — |

Relatório: `outputs/campaigns/sabesp_2026/manual_label_report.md`.

**Análise de erro** (`outputs/campaigns/classifier_eval_pt/error_analysis.md`):

| Tipologia | n | % |
|-----------|---|---|
| focal_sabesp | 74 | 74% |
| roundup_agenda | 26 | 26% |

| Modelo | F1 macro | κ (completa) | κ (focal) |
|--------|----------|--------------|-----------|
| `finbert_ptbr` | 0,42 | 0,163 | 0,217 |
| `bertweet_pt_sentiment` | 0,27 | −0,014 | 0,000 |
| `bertimbau_sentiment` | 0,33 | 0,087 | 0,032 |

κ sobe levemente no subconjunto focal do FinBERT (0,163 → 0,217), mas permanece abaixo do gate — contaminação de gênero jornalístico explica **parte**, não tudo, do desempenho fraco.

**Robustez filtro roundups** (`sabesp_event_r1_filtered`, 404 artigos, −61 roundups): win rate **25,0%** (6/24), **0 sig.** — remover roundups **não** melhora o ITI; o teto ~41,7% parece mais relação notícia–preço do que lixo textual.

### Bateria PT (mesmas 100 notícias)

Comando: `./scripts/campaigns/classifier_eval_pt.sh run`

| Modelo | Acurácia | κ | Passa gate (70% ou κ≥0,40)? |
|--------|----------|---|------------------------------|
| `finbert_ptbr` | 48,0% | 0,163 | não |
| `bertweet_pt_sentiment` | 68,0% | −0,014 | não |
| `bertimbau_sentiment` | 53,0% | 0,087 | não |

Relatório: `outputs/campaigns/classifier_eval_pt/comparative_report.md`.

**Decisão:** nenhum modelo passou o gate — **ITI condicional com controles PT não foi executado** (correto pelo protocolo).

O viés NEU/NEG do FinBERT não é resolvido pelos controles PT genéricos; BERTweet até acerta mais linhas, mas com κ negativo (desacordo sistemático vs. humano).

---

## 5. Limitações

- **Evento único** (privatização Sabesp); overlap ~24 semanas (evento) a ~90 semanas (expandido com painel alinhado).
- **Correlação ≠ causalidade**; win rate mede ITI vs baselines internos, não previsão direcional.
- **24 comparações** por run (4 baselines × Pearson/Spearman × 3 horizontes) — não são testes independentes; 2/24 significativas no R1 evento são compatíveis com busca múltipla (ver `significant_wins_r1_event.md`).
- **Classificador** abaixo do gate de 70% — F1 macro 0,42; viés NEU/NEG; roundups/agendas ~26% da amostra manual.
- **Amostra manual** pequena (n=100); κ instável para classes minoritárias.

---

## 6. Conclusão operacional da Trilha A

1. **Fechar a narrativa** com evento + R1 (41,7%, 2 sig.) como resultado principal.
2. **Citar expandido** como teste de robustez: lacuna 2023 preenchida, R1 sobe para 33,3%, sem significância.
3. **Não** investir em fine-tune/LoRA neste ciclo — classificadores PT (incl. controles) não passaram o gate.
4. Marcos 4–5 (FNSPID / FinMarBa) permanecem **opcionais** e não bloqueiam esta conclusão.

---

## Artefatos desta fase

| Artefato | Caminho |
|----------|---------|
| Comparação gap 2023 | `outputs/campaigns/sabesp_marco2/gap2023_comparison.md` |
| Subperíodos gap 2023 | `outputs/campaigns/sabesp_marco2/period_breakdown_gap2023.md` |
| Vitórias sig. R1 evento | `outputs/campaigns/sabesp_marco2/significant_wins_r1_event.md` |
| Análise de erro κ | `outputs/campaigns/classifier_eval_pt/error_analysis.md` |
| Runs expandidas | `outputs/sabesp_gap2023_r0_baseline/`, `outputs/sabesp_gap2023_r1_alpha070/` |
| Runs evento (sanity) | `outputs/sabesp_gap2023_event_r0_baseline/`, `outputs/sabesp_gap2023_event_r1_alpha070/` |
| Run evento filtrada | `outputs/sabesp_event_r1_filtered/` |
| Bateria κ PT | `outputs/campaigns/classifier_eval_pt/` |
| Scripts | `scripts/campaigns/sabesp_marco2.sh`, `scripts/campaigns/classifier_eval_pt.sh` |

---

## 7. Redação da tese (figuras e bibliografia)

### Figuras sugeridas (extrair de `outputs/`)

- Série ITI semanal vs. retorno futuro h=1: `outputs/sabesp_gap2023_event_r1_alpha070/.../aligned_panel.csv`
- Matriz de confusão (100 rotuladas): `outputs/eval_pt_*/models/*/rotulos_manual_pt_100/confusion_matrix.csv`
- Win rate R0/R1 por janela: tabelas deste documento ou `gap2023_comparison.md`

### Bibliografia sugerida

| Referência | Uso |
|------------|-----|
| Araci et al. — FinBERT | Motivação domínio financeiro |
| Souza et al. — FinBERT-PT-BR | Classificador principal |
| Barbieri et al. — BERTweet | Controle PT na bateria κ |
| Gururangan et al. (2020) | Contexto DAP; não executado (gate κ falhou) |
| Loughran & McDonald | Fundamentação baselines |
| Tetlock | Motivação ITI×retorno |

Fora de escopo neste capítulo (mencionar em trabalhos futuros): FNSPID, FinMarBa, PhraseBank/NOSIBLE no ITI Sabesp.

Histórico run a run e auditoria metodológica: [trajetoria.md](trajetoria.md). Comandos de reprodução: [configs/campaigns/sabesp_marco2/README.md](../configs/campaigns/sabesp_marco2/README.md).
