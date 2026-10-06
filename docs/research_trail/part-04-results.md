# Parte 4 — Resultados consolidados Trilha A

*Números extraídos de `outputs/` — fonte de verdade para tabelas desta seção.*

## 4.1 Protocolo

Ver [Parte 2](#parte-2--protocolo-e-critérios-de-progresso). Research: `configs/campaigns/sabesp_2026/research_weekly.yaml`.

## 4.2 Resultado principal (janela evento)

> **Leitura obrigatória:** o resultado principal (41,7%, 2 sig.) é **exploratório**, não confirmatório. Interpretação substantiva do ITI como medida de choque informacional **condiciona-se** à validade do classificador — gate κ falhou (48%, κ=0,163; [§4.4](#44-qualidade-do-classificador)). Não inferir causalidade nem generalização fora da janela evento.

**Janela:** nov/2023–abr/2024 (`saneamento_sabesp_strict_event`, ~465 artigos).

| Run | run_id | Win rate R1 | Significativas |
|-----|--------|-------------|----------------|
| Marco 1 | `sabesp_r1_alpha070` | **41,7%** | **2** |
| Sanity corpus 1.254 | `sabesp_gap2023_event_r1_alpha070` | **41,7%** | **2** |
| Filtro roundups | `sabesp_event_r1_filtered` | 25,0% | 0 |

**Vitórias significativas** (`significant_wins_r1_event.md`):

| Horizonte | Baseline | Métrica | Δ | p-value |
|-----------|----------|---------|---|---------|
| 4 sem. | B3 | Pearson | +0,133 | 0,040 |
| 4 sem. | B3 | Spearman | +0,221 | 0,046 |

*Caveat:* 2/24 comparações — compatível com busca múltipla (§4.5).

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
| **Exploratório** | set.–out./2026 (anotador único) | `data/water_utilities_corpus/manual_labels_100_exploratorio.csv` | Critério simplificado (`rotulo_manual`); métricas abaixo (48%, κ=0,163) referem-se a **esta** fase — benchmark do fluxo, não gold da qualificação. |
| **Amostra formal** | out./2026+ (pós reunião 06/10) | `data/water_utilities_corpus/manual_labels_100.csv` | Protocolo em [annotation_protocol.md](../tracking/annotation_protocol.md): `impacto_alvo`, tipologia, triangulação (segundo humano em subconjunto ~30; segunda classificação automatizada 10–20 casos). |

Decisões: [DR-006](decision-register.md), [DR-012](decision-register.md). Acompanhamento com orientador: [qualification_schedule.md](../tracking/qualification_schedule.md).

### 4.4.2 Métricas na rodada exploratória (FinBERT × anotação solo)

| Métrica FinBERT (100 manual) | Valor | Gate |
|------------------------------|-------|------|
| Acurácia | 48% | < 70% |
| Cohen's κ | 0,163 | — |
| F1 macro | 0,42 | — |

**Benchmark literatura vs. corpus local** (não re-executado — números do artigo Santos et al., 2023):

| Fonte | Acurácia / F1 | Corpus | Implicação para Trilha A |
|-------|---------------|--------|--------------------------|
| Santos et al. (2023) — artigo | ~76% / F1 0,73 | Notícias financeiras PT (treino) | Teto teórico se domínio coincidisse |
| FinBERT-PT-BR — **este lab** | 48% / F1 0,42 | Saneamento Sabesp (n=100) | Gate κ falhou — limita interpretação substantiva |
| BERTweet / BERTimbau — controles | 68% / 0,27; 53% / 0,33 | Mesma amostra | κ negativo ou baixo — problema não é só arquitetura |

| Modelo | F1 macro | κ (completa) | κ (focal) |
|--------|----------|--------------|-----------|
| `finbert_ptbr` | 0,42 | 0,163 | 0,217 |
| `bertweet_pt_sentiment` | 0,27 | −0,014 | 0,000 |
| `bertimbau_sentiment` | 0,33 | 0,087 | 0,032 |

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

1. **Exploratório e condicionado ao κ:** fechar narrativa com evento + R1 (41,7%, 2 sig.) como resultado principal exploratório.
2. Citar expandido como robustez/limitação (33,3%, 0 sig.).
3. **Não** investir em fine-tune/LoRA neste ciclo.
4. Marcos 4–5 (FNSPID / FinMarBa) opcionais.

## 4.7 Redação da tese

**Figuras sugeridas** (extrair de `outputs/`):

- Série ITI vs retorno h=1: `outputs/sabesp_gap2023_event_r1_alpha070/.../aligned_panel.csv`
- Matriz confusão: `outputs/.../rotulos_manual_pt_100/confusion_matrix.csv`
- Win rate por janela: `gap2023_comparison.md`

**Bibliografia sugerida:** ver [Apêndice E](#apêndice-e--bibliografia-comentada).

## 4.8 Como reproduzir (dev)

Pré-requisitos: `./scripts/setup_env.sh --fetch-assets`, `./scripts/audit_project.sh` verde.

| Etapa | Comando (exemplo) |
| --- | --- |
| Experimento R1 evento | `./scripts/campaigns/sabesp_2026.sh` (subcomando da run desejada — ver script) |
| Research semanal | Após experiment: `./scripts/run_research.sh` com `run_id` da campanha |
| Manifest / relatórios | `outputs/campaigns/sabesp_2026/`, Marco 2 em `sabesp_marco2/` |
| κ manual | `./scripts/campaigns/classifier_eval_pt.sh` |

YAML: `configs/campaigns/sabesp_2026/research_weekly.yaml`, experiments em `configs/campaigns/sabesp_2026/experiments/`. Fluxo detalhado: [11_fluxo_ponta_a_ponta.md](../documentation/11_fluxo_ponta_a_ponta.md).

**Não** reexecutar números desta Parte 4 sem registrar novo `run_id` e atualizar tabelas aqui.

---

**Próximo:** [Parte 5 — Lacunas](part-05-gaps.md)
