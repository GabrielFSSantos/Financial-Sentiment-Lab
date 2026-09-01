# Configurações de campanha (descartáveis)

YAMLs e receitas **específicas da tese Sabesp** e pilotos opcionais (Marcos 1–5). Não fazem parte do núcleo reutilizável do lab.

## Estrutura

| Pasta / arquivo | Conteúdo |
|-----------------|----------|
| `datasets.yaml` | Datasets Sabesp, PhraseBank, NOSIBLE, FNSPID, FinMarBa (overlay mesclado em `configs/datasets.yaml`) |
| `sabesp_2026/` | Marco 1 — R0–R9, research semanal |
| `sabesp_marco2/` | Notas do Marco 2 (janela expandida) |
| `trilha_b/` | Experimento só classificação (`classifier_diag.yaml`) |
| `fnspid_pilot/` | Piloto US (Marco 4) |
| `finmarba/` | Notas do diagnóstico FinMarBa (Marco 5) |

## Como rodar

Use os scripts em [`scripts/campaigns/`](../scripts/campaigns/README.md):

```bash
./scripts/campaigns/sabesp_2026.sh all
./scripts/campaigns/sabesp_marco2.sh replay
```

Ou manualmente com `run_experiment.sh` / `run_research.sh` apontando para os YAMLs desta pasta.

## Remoção segura (após consolidar resultados)

Quando os números estiverem em `docs/trajetoria.md` e `outputs/` arquivados:

```bash
rm -rf configs/campaigns scripts/campaigns
```

O pipeline base (`configs/datasets.yaml` com exemplos + `saneamento_corpus`, `run_experiment.sh`, `modules/evaluation`) continua funcionando.

**Runs antigas** podem referenciar `configs/experiments/sabesp/` — caminho histórico do Marco 1.
