# Parte 4 — Resultados consolidados Trilha A

*Números extraídos de `outputs/` — fonte de verdade para tabelas desta seção.*

## 4.1 Protocolo

Ver [Parte 2](#parte-2--protocolo-e-critérios-de-progresso). Research: `configs/campaigns/sabesp_2026/research_weekly.yaml`.

## 4.2 Resultado principal (janela evento)

> **Leitura obrigatória:** os duelos ITI são **exploratórios**, não confirmatórios. Interpretação substantiva do ITI como medida de choque informacional **condiciona-se** à validade do classificador — gate κ falhou (48%, κ=0,163; [§4.4](#44-qualidade-do-classificador)). Não inferir causalidade nem generalização fora da janela evento.

**Janela:** nov/2023–abr/2024 (`saneamento_sabesp_strict_event`, ~465 artigos).

| Run | run_id | Corpus (CSV) | Win rate R1 | Significativas |
|-----|--------|----------------|-------------|----------------|
| **Canônico out/2026** | `sabesp_r1_alpha070` | `data/water_utilities_corpus/articles_strict_sabesp.csv` | **25,0%** (6/24) | **0** |
| Marco 1 (ago/2024, legado) | `sabesp_r1_alpha070` | `data/saneamento_corpus/noticias_strict_sabesp.csv` | 41,7% (10/24) | 2 |
| Sanity corpus 1.254 | `sabesp_gap2023_event_r1_alpha070` | (run histórico) | 41,7% | 2 |
| Filtro roundups | `sabesp_event_r1_filtered` | — | 25,0% | 0 |

**Rodada canônica (qualificação, PC):** re-run local `r1-local-quali` em 21/10/2026, commit `20966dd`, `environment: local`. Replicação HPC (job Slurm **11621573**, `environment: sdumont`) reproduz os **mesmos** duelos (6/24, 0 sig.) sobre o corpus `water_utilities_corpus`; não substitui a linha legada acima.

**Vitórias significativas (somente run legado ago/2024)** — ver `significant_wins_r1_event.md`:

| Horizonte | Baseline | Métrica | Δ | p-value |
|-----------|----------|---------|---|---------|
| 4 sem. | B3 | Pearson | +0,133 | 0,040 |
| 4 sem. | B3 | Spearman | +0,221 | 0,046 |

*Caveat:* 2/24 comparações no run legado — compatível com busca múltipla (§4.5). No corpus atual, nenhuma comparação passa o critério bootstrap.

## 4.3 Robustez (janela expandida)

**Janela:** mai/2022–abr/2024 (`saneamento_sabesp_strict_expanded`).

| Corpus | Artigos | R1 win rate | Δ vs Marco 2 |
|--------|---------|-------------|--------------|
| Marco 2 (sem lacuna 2023) | 1.055 | 20,8% | — |
| Gap 2023 preenchido | **1.254** | **33,3%** | +12,5 pp |

| Run gap 2023 | R0 | R1 |
|--------------|----|----|
| Expandido | 4,2% (1/24) | **33,3%** (8/24) |

**Subperíodos** (`period_breakdown_gap2023.md`):

| Bucket | Semanas | Pearson | Spearman |
|--------|---------|---------|----------|
| `pre_evento_2022` | 25 | −0,148 | −0,110 |
| `interregno_2023q1` | 15 | +0,172 | +0,304 |
| `evento_nov23_abr24` | 50 | −0,030 | +0,054 |

**Leitura:** expandido = teste de limitação (“mais dados ≠ melhor sinal”).

## 4.4 Qualidade do classificador

### 4.4.1 Linha do tempo da anotação manual

| Fase | Período | Artefato | Leitura |
|------|---------|----------|---------|
| **Exploratório** | set.–out./2026 (anotador único) | `data/water_utilities_corpus/manual_labels_100_exploratorio.csv` | Critério simplificado (`rotulo_manual`); métricas abaixo (48%, κ=0,163) referem-se a **esta** fase — benchmark do fluxo, não referência especialista definitiva. |
| **Formal histórica (mestrando)** | out./2026 (pós 06/10) | `manual_labels_100.csv` | `impacto_alvo`, tipologia — diagnóstico FinBERT×mestrando; **não** gold especialista. |
| **Referência especialista** | em andamento | `annotations_long.csv`, `impacto_alvo_2`+ | Meta ≥3 especialistas economia/finanças; consenso DR-016; IAA em subconjunto fixo de ids. |

Decisões: [DR-006](decision-register.md), [DR-012](decision-register.md), [DR-016](decision-register.md).

### 4.4.2 Métricas na rodada exploratória (FinBERT × anotação solo)

| Métrica FinBERT (100 manual) | Valor | Gate |
|------------------------------|-------|------|
| Acurácia | 48% | < 70% |
| Cohen's κ | 0,163 | — |
| F1 macro | 0,42 | — |

**Benchmark literatura vs. corpus local** (não re-executado — números do artigo Santos, Bianchi e Costa, 2023):

| Fonte | Acurácia / F1 | Corpus | Implicação para Trilha A |
|-------|---------------|--------|--------------------------|
| Santos, Bianchi e Costa (2023) — artigo | ~76% / F1 0,73 | Notícias financeiras PT (treino) | Teto teórico se domínio coincidisse |
| FinBERT-PT-BR — **este lab** | 48% / F1 0,42 | Saneamento Sabesp (n=100) | Gate κ falhou — limita interpretação substantiva |
| BERTweet / BERTimbau — controles | 68% / 0,27; 53% / 0,33 | Mesma amostra | κ negativo ou baixo — problema não é só arquitetura |

| Modelo | F1 macro | κ (completa) | κ (focal) |
|--------|----------|--------------|-----------|
| `finbert_ptbr` | 0,42 | 0,163 | 0,217 |
| `bertweet_pt_sentiment` | 0,27 | −0,014 | 0,000 |
| `bertimbau_sentiment` | 0,33 | 0,087 | 0,032 |

### 4.4.3 Métricas na amostra formal (`impacto_alvo`, protocolo 2026-10-07)

Reanotação completa (n=100) em `manual_labels_100.csv`. Bateria: `classifier_eval_pt` + `error_analysis.md` (out./2026).

| Subconjunto | n | Acurácia FinBERT | κ |
|-------------|---|------------------|---|
| Completa | 100 | 50,0% | 0,197 |
| focal_sabesp | 74 | 52,7% | 0,260 |
| roundup_agenda | 26 | 42,3% | −0,032 |

F1 macro FinBERT na formal: 0,45. Gate (70% ou κ≥0,40): **não** atingido.

**Piloto LLM-judge:** 20 `news_id`; saída `outputs/campaigns/llm_judge_pilot/` (Mistral-7B-Instruct, `prompt_v1_quali`). Inferência GPU completa pendente; fluxo validado com saída simulada. IAA humano×humano (~30 ids): pendente anotador especialista principal.

**Tipologia de erro** (`error_analysis.md`, n=100):

| Tipologia | n | % |
|-----------|---|---|
| `focal_sabesp` | 74 | 74% |
| `roundup_agenda` | 26 | 26% |

κ sobe levemente no subconjunto focal do FinBERT (0,163 → 0,217), mas permanece abaixo do gate — contaminação de gênero jornalístico explica parte, não tudo, do desempenho fraco. Filtro de roundups no evento (**25,0%**, 0 sig.) confirma que o teto ~41,7% não é só “lixo textual”.

**Relatórios:** `outputs/campaigns/sabesp_2026/manual_label_report.md` · `outputs/campaigns/classifier_eval_pt/comparative_report.md` · `outputs/campaigns/classifier_eval_pt/error_analysis.md`

## 4.5 Limitações

- Evento único (privatização); overlap ~24 semanas (evento) a ~90 (expandido).
- Correlação ≠ causalidade; win rate = ITI vs baselines internos.
- 24 comparações não independentes; 2 sig. compatíveis com busca múltipla.
- Classificador abaixo do gate; roundups ~26% da amostra manual.
- n=100 para κ — instável em classes minoritárias.
- H2, volatilidade, volume, Granger, controles IBOV: **não executados**.

## 4.6 Conclusão operacional

1. **Resultado principal (corpus canônico, out./2026):** R1 sobre `articles_strict_sabesp.csv` — **6/24** confrontos favoráveis, **0** significativos no bootstrap (alinhado PC + job Slurm 11621573). Esta é a linha a citar na qualificação e na dissertação para o protocolo atual.
2. **Legado exploratório (ago./2024, `saneamento_corpus/`):** 10/24 e **duas** diferenças nominais significativas — **não** replicado no corpus canônico; tratar como histórico com multiplicidade e corpus distinto (`historical_reconciliation.csv`).
3. Janela ampliada / sanity 1.254: citar apenas como sensibilidade (ex.: 8/24, 33,3%, 0 sig. quando aplicável), nunca como substituto do canônico.
4. **Não** investir em fine-tune/LoRA neste ciclo sem referência humana independente.
5. Campanha ITI-v2 executada localmente (out./2026) — ver [§4.7](#47-campanha-iti-v2-out2026); legado R1 permanece linha histórica §4.2.

## 4.7 Campanha ITI-v2 (out./2026)

> **Modo:** exploratório (`protocol_lock.json`). **Não** substitui duelos R1 legados nem confirma hipótese. Inferência com `entity_context_v1` sobre corpus canônico P02 (`articles_canonical.csv`, 1 253 artigos).

| Item | Valor |
|------|--------|
| `run_id` | `iti_v2_prod_20261022` |
| Predições OK | 1 253 (`inference_manifest.json`) |
| Sinal principal | `iti_v2_h7` (meia-vida 7 d) |
| Painel alinhado (h=1) | n=92 semanas · Spearman ρ ≈ −0,043 · p≈0,69 · bootstrap 10 000 · IC95% [−0,22; 0,16] |
| Holdout (12 sem. calendário, notícias) | 199 artigos reservados · métrica semanal holdout n=12 · ρ ≈ −0,17 · p ≈ 0,60 |
| Artefatos | `outputs/campaigns/iti_v2/iti_v2_prod_20261022/` · `thesis_export/` |

Reprodução: `docs/plans/iti_v2_runbook.md` · aceite: `./scripts/campaigns/iti_v2.sh validate iti_v2_prod_20261022`. Números finais de bootstrap: `metrics_primary.json` (atualizar após `ITI_V2_BOOTSTRAP=10000`).

## 4.8 Redação da tese

**Figuras sugeridas** (extrair de `outputs/`):

- Série ITI vs retorno h=1: `outputs/sabesp_gap2023_event_r1_alpha070/.../aligned_panel.csv`
- Matriz confusão: `outputs/.../rotulos_manual_pt_100/confusion_matrix.csv`
- Win rate por janela: `gap2023_comparison.md`

**Bibliografia sugerida:** ver [Apêndice E](#apêndice-e--bibliografia-comentada).

## 4.9 Como reproduzir (dev)

Pré-requisitos: `./scripts/setup_env.sh --fetch-assets`, `./scripts/audit_project.sh` verde.

| Etapa | Comando (exemplo) |
| --- | --- |
| Experimento R1 evento | `./scripts/campaigns/sabesp_2026.sh` (subcomando da run desejada — ver script) |
| Research semanal | Após experiment: `./scripts/run_research.sh` com `run_id` da campanha |
| Manifest / relatórios | `outputs/campaigns/sabesp_2026/`, Marco 2 em `sabesp_marco2/` |
| κ manual | `./scripts/campaigns/classifier_eval_pt.sh` |
| Campanha ITI-v2 | `./scripts/campaigns/iti_v2.sh run-all <run_id>` (ver runbook) |

YAML: `configs/campaigns/sabesp_2026/research_weekly.yaml`, experiments em `configs/campaigns/sabesp_2026/experiments/`. Fluxo detalhado: [11_end_to_end_flow.md](../documentation/11_end_to_end_flow.md).

**Não** reexecutar números desta Parte 4 sem registrar novo `run_id` e atualizar tabelas aqui.

---

**Próximo:** [Parte 5 — Lacunas](part-05-gaps.md)
