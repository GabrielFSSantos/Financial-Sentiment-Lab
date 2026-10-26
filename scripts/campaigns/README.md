# Scripts de campanha

| Script | Função |
|--------|--------|
| `iti_v2.sh` | ITI-v2: prepare → infer → evaluate → `postprocess` |
| `iti_v2_gate_local.sh` / `iti_v2_sdumont_preflight.sh` | Gates locais e SDumont |
| `classifier_eval_pt.sh` | κ FinBERT × rótulos manuais (PT) |

Runners gerais: `../run_experiment.sh`, `../run_research.sh`, `../audit_project.sh`.

## ITI-v2

```bash
./scripts/campaigns/iti_v2.sh postprocess iti_v2_prod_20261022
./scripts/campaigns/iti_v2.sh validate iti_v2_prod_20261022
```

`postprocess` executa evaluate/report/validate/export-thesis no repo. Exportação de snippets LaTeX e figuras requer `FSL_HARNESS_ROOT` apontando para o ambiente de desenvolvimento local (ver guia do desenvolvedor).

Estado canônico: `docs/research_trail/part-04-results.md` §4.7.
