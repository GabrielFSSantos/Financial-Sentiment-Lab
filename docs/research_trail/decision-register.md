# Registro de decisões (ADR-lite)

Decisões metodológicas e de engenharia que **não** precisam ser repetidas em texto longo nas Partes 2–3. Formato: **ID**, data, decisão, alternativas, artefatos, código/config.

Template de fase: [phase-template.md](phase-template.md).

| ID | Data | Decisão | Alternativas rejeitadas | Artefatos | Código / config |
| --- | --- | --- | --- | --- | --- |
| DR-001 | 2026-08 | F0: provar pipeline end-to-end antes de H1 | Pular direto para evento Sabesp | `outputs/saneamento_pt_20260824/` | Matriz diária mista (deprecada) |
| DR-002 | 2026-09 | F1: Trilha A Sabesp + research **semanal** W-FRI | Multi-empresa no resultado principal; ITI semanal vs alvo diário | `configs/campaigns/sabesp_2026/`, `research_weekly.yaml` | `research/io/weekly_align.py` |
| DR-003 | 2026-09 | Protocolo: 4 baselines × 2 métricas × 3 horizontes = **24 duelos** | Baselines pós-hoc; só Pearson | [part-02-protocol.md](part-02-protocol.md) | `configs/research.yaml`, campanha semanal |
| DR-004 | 2026-09 | FinBERT-PT-BR como modelo principal PT | Só modelo genérico PT | Runs R0+ | `configs/models.yaml` → `finbert_ptbr` |
| DR-005 | 2026-10 | Corpus evento: filtrar roundups/agendas (F4) | Corpus bruto só por data | `articles_strict_sabesp_event_filtered.csv` | `modules/evaluation/campaigns/event_corpus_filter.py` |
| DR-010 | 2026-09 | α=0,70 (R1) melhor win rate que α=0,85 (R0) no evento | α fixo por horizonte (R7); média semanal (R8) | `outputs/sabesp_r1_alpha070/` | `configs/campaigns/sabesp_2026/experiments/r1_*.yaml` |
| DR-006 | 2026-10 | Amostra manual para **validar pipeline** de anotação e eval, sem fechar κ como prova de mercado | Prometer gate κ≥0,40 como resultado fechado nesta fase | [14_manual_annotation.md](../documentation/14_manual_annotation.md) · [part-04 §4.4.1](part-04-results.md#441-linha-do-tempo-da-anotação-manual) | `modules/evaluation/manual_labels.py` |
| DR-012 | 2026-10 | Amostra formal pós-orientação (06/10): mesmo n=100 `news_id`, critério impacto Sabesp; exploratório solo arquivado | Descartar rodada exploratória | `manual_labels_100_exploratorio.csv` (referência) · `manual_labels_100.csv` (histórico formal mestrando) | Ver DR-016 para referência especialista |
| DR-016 | 2026-10 | Referência humana: **≥3 especialistas** economia/finanças; consenso por maioria + adjudicação em empate 1-1-1; entrada classificador **título+corpo** (`text_compose`); **crédito nominal** na dissertação a quem anotar (lista em CONTRIBUTORS + apêndice) | Mestrando como gold; LLM como voto; média numérica de classes | `manual_labels_100.csv` · `annotations_long.csv` · [CONTRIBUTORS.md](../../CONTRIBUTORS.md) · `Dissertacao_PPGCC/` | `configs/campaigns/datasets.yaml` text_compose |
| DR-017 | 2026-10 | Citação narrativa em markdown: até 3 sobrenomes do `.bib`, sem abreviação latina de coautores | `et al.` em prosa de `docs/` | [citation-conventions.md](citation-conventions.md) | `@ABNT-options` em `bibliografia.bib` |
| DR-007 | 2026-10 | LLM-as-judge: piloto 10–20, prompt fixo | Juiz em produção antes do protocolo | `outputs/campaigns/llm_judge_pilot/` | `evaluation/judges/` (stub → implementação) |
| DR-008 | 2026-10 | Dry-run: valida preflight, **não grava** `outputs/` | Dry-run escrever árvore parcial | — | `experiment/io/results.py` `write_enabled` |
| DR-009 | 2026-10 | Docs canônicas no repo | Duplicar arquitetura fora do git | `docs/documentation/10_`, `13_dev_reading_guide` | — |
| DR-011 | 2026-10 | Piloto juiz: `HfCausalLabelJudge` + CLI `llm-judge-pilot`; Mistral 7B padrão em YAML | Só CSV manual sem código | `outputs/campaigns/llm_judge_pilot/` | `modules/evaluation/judges/hf_causal_judge.py`, `configs/evaluation.yaml` |
| DR-013 | 2026-10 | Base bib. rotulação entity/target (Yuan, SEntFiN, FinLin, Aguda + κ/IAA) | Anotação só por intuição / só FinBERT | `references/notas/` · PDFs `docs/references/pdfs/` · [14_manual_annotation.md](../documentation/14_manual_annotation.md) | `bibliografia.bib` |
| DR-014 | 2026-10 | Nomenclatura: paths EN; prosa PT-BR; `AUTHORS.md` | Copyright em cada `.py` | [AUTHORS.md](../../AUTHORS.md) · [CONTRIBUTING.md](../../CONTRIBUTING.md) | — |
| DR-015 | 2026-10 | Slimming: docs operacionais fora do git; sem download script; CLI evaluation mínima | Duplicar cronograma no repo | [14_manual_annotation.md](../documentation/14_manual_annotation.md) | removidos shims `evaluation/*.py`, `scripts/download_references.sh` |
| DR-018 | 2026-10-22 | **ITI-v2**: meia-vida em dias civis (H=7 principal), soft mean, sem pesos heurísticos; legado `legacy_v1` congelado | Continuar só EWMA α adaptativo | `Plano_Mestre_ITI_v2_*.md`, `docs/plans/iti_v2_progress.md` | `modules/experiment/indexing/iti_v2.py`, `configs/campaigns/iti_v2/` |

Ao registrar nova decisão: uma linha na tabela + parágrafo curto na fase correspondente em [part-03-phases.md](part-03-phases.md).
