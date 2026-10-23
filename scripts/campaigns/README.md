# Scripts de campanha

Atalhos que chamam módulos do lab com configs em `configs/campaigns/`.

## Núcleo (qualificação e ITI-v2)

| Script | Função |
|--------|--------|
| `iti_v2.sh` | Campanha ITI-v2 normativa: P02 → inferência → índices → evaluate → `postprocess` (LaTeX + figuras) |
| `sabesp_2026.sh` | Campanha legado R0–R1 Sabesp (24 duelos semanais) |
| `classifier_eval_pt.sh` | κ e métricas FinBERT × referência manual (PT) |
| `iti_v2_gate_local.sh` / `iti_v2_sdumont_preflight.sh` | Gates antes de run pesado |

Runners gerais: `../run_experiment.sh`, `../run_research.sh`, `../audit_project.sh`.

## Histórico (marcos F3–F5 na trilha)

Mantidos para reproduzir resultados já citados em `docs/research_trail/` e apêndices; não são o foco do ITI-v2.

| Script | Marco | Uso |
|--------|-------|-----|
| `sabesp_marco2.sh` | 2 | Janela expandida, gap 2023, replay R1 |
| `classifier_eval_en.sh` | 3 | PhraseBank + NOSIBLE |
| `fnspid_pilot.sh` | 4 | Piloto FNSPID US |
| `finmarba_diag.sh` | 5 | FinBERT × FinMarBa |

## Exportação dissertação (ITI-v2)

Invocado por `iti_v2.sh postprocess`:

- `scripts/dissertation/iti_v2/export_iti_v2_latex.py`
- `scripts/dissertation/iti_v2/export_iti_v2_dissertation_tables.py`
- `scripts/dissertation/iti_v2/generate_iti_v2_figures.py`

## Exemplo ITI-v2

```bash
./scripts/campaigns/iti_v2.sh postprocess iti_v2_prod_20261022
./scripts/campaigns/iti_v2.sh validate iti_v2_prod_20261022
```

Estado canônico: `docs/research_trail/part-04-results.md` §4.7.
