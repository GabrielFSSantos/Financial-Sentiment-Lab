# 13 Guia de leitura — desenvolvedor

## Roteiro mínimo

1. [README.md](../../README.md)
2. [00_quickstart_researcher.md](00_quickstart_researcher.md)
3. [11_end_to_end_flow.md](11_end_to_end_flow.md)
4. [06_configuration.md](06_configuration.md)
5. [09_tests.md](09_tests.md)

Antes de alterar comportamento científico: [12_business_rules.md](12_business_rules.md) e [research_trail](../research_trail/README.md).

## Export LaTeX (dissertação ITI)

O repositório versiona o pipeline e `export-thesis` (JSON). Snippets e figuras em `docs/Dissertacao_PPGCC/generated/` são gerados no ambiente local do pesquisador:

```bash
export FSL_HARNESS_ROOT=/caminho/para/harness   # pasta com scripts/dissertation/iti_v2/
export FSL_REPO_ROOT="$PWD"
./scripts/campaigns/iti_v2.sh postprocess iti_v2_prod_20261022
```

Alternativa: `$FSL_HARNESS_ROOT/scripts/dissertation/iti_v2/run_thesis_export.sh <run_id>`.

## Gate após mudanças

```bash
./scripts/audit_project.sh
./venv/bin/python -m pytest -m "not network"
```

Extensões (modelo, campanha, juiz): [module_plugin_contract.md](module_plugin_contract.md) · [10_architecture_and_maintenance.md](10_architecture_and_maintenance.md).

## Matriz doc ↔ teste (resumo)

| Invariante | Documentação | Teste |
| --- | --- | --- |
| Schema `predictions.csv` | [appendix_output_contract](appendix_output_contract.md) | `test_output_schema.py` |
| Dry-run | [12_business_rules](12_business_rules.md) | `test_experiment_dry_run_outputs.py` |
| ITI / EWMA | [04_iti_formulas](04_iti_formulas.md) | `test_temporal_index.py` |
| Research semanal | [05_research_validation](05_research_validation.md) | `test_research_weekly_align.py` |

Prosa em PT-BR; código e paths em inglês — [CONTRIBUTING.md](../../CONTRIBUTING.md).
