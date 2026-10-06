# Registro de decisões (ADR-lite)

Decisões metodológicas e de engenharia que **não** precisam ser repetidas em texto longo nas Partes 2–3. Formato: **ID**, data, decisão, alternativas, artefatos, código/config.

Template de fase: [phase-template.md](phase-template.md).

| ID | Data | Decisão | Alternativas rejeitadas | Artefatos | Código / config |
| --- | --- | --- | --- | --- | --- |
| DR-001 | 2026-08 | F0: provar pipeline end-to-end antes de H1 | Pular direto para evento Sabesp | `outputs/saneamento_pt_20260824/` | Matriz diária mista (deprecada) |
| DR-002 | 2026-09 | F1: Trilha A Sabesp + research **semanal** W-FRI | Multi-empresa no resultado principal; ITI semanal vs alvo diário | `configs/campaigns/sabesp_2026/`, `research_weekly.yaml` | `research/io/weekly_align.py` |
| DR-003 | 2026-09 | Protocolo: 4 baselines × 2 métricas × 3 horizontes = **24 duelos** | Baselines pós-hoc; só Pearson | [part-02-protocol.md](part-02-protocol.md) | `configs/research.yaml`, campanha semanal |
| DR-004 | 2026-09 | FinBERT-PT-BR como modelo principal PT | Só modelo genérico PT | Runs R0+ | `configs/models.yaml` → `finbert_ptbr` |
| DR-005 | 2026-10 | Corpus evento: filtrar roundups/agendas (F4) | Corpus bruto só por data | `articles_strict_sabesp_event_filtered.csv` | `modules/evaluation/event_corpus_filter.py` |
| DR-010 | 2026-09 | α=0,70 (R1) melhor win rate que α=0,85 (R0) no evento | α fixo por horizonte (R7); média semanal (R8) | `outputs/sabesp_r1_alpha070/` | `configs/campaigns/sabesp_2026/experiments/r1_*.yaml` |
| DR-006 | 2026-10 | Qualificação: amostra manual para **validar pipeline**, não fechar κ | Prometer gate κ≥0,40 na qualificação | [annotation_protocol.md](../tracking/annotation_protocol.md) · [part-04 §4.4.1](part-04-results.md#441-linha-do-tempo-da-anotação-manual) | `modules/evaluation/manual_labels.py` |
| DR-012 | 2026-10 | Amostra formal pós-orientação (06/10): mesmo n=100 `news_id`, critério impacto Sabesp; exploratório solo arquivado | Descartar rodada exploratória; relabel das 100 em par com Rafael | `manual_labels_100_exploratorio.csv` (referência) · `manual_labels_100.csv` (canônico) | IAA ~30 no subconjunto; piloto LLM 10–20 (DR-007) |
| DR-007 | 2026-10 | LLM-as-judge: piloto 10–20, prompt fixo | Juiz em produção antes do protocolo | `outputs/campaigns/llm_judge_pilot/` | `evaluation/judges/` (stub → implementação) |
| DR-008 | 2026-10 | Dry-run: valida preflight, **não grava** `outputs/` | Dry-run escrever árvore parcial | — | `experiment/io/results.py` `write_enabled` |
| DR-009 | 2026-10 | Docs canônicas no repo; harness meta só índice | Duplicar arquitetura só no meta-workspace | `docs/documentation/10_`, `13_` | — |
| DR-011 | 2026-10 | Piloto juiz: `HfCausalLabelJudge` + CLI `llm-judge-pilot`; Mistral 7B padrão em YAML | Só CSV manual sem código | `outputs/campaigns/llm_judge_pilot/` | `modules/evaluation/judges/hf_causal_judge.py`, `configs/evaluation.yaml` |

Ao registrar nova decisão: uma linha na tabela + parágrafo curto na fase correspondente em [part-03-phases.md](part-03-phases.md).
