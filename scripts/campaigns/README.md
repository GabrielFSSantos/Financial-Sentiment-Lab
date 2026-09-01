# Scripts de campanha (descartáveis)

Atalhos que chamam `scripts/run_experiment.sh` e `scripts/run_research.sh` com configs em `configs/campaigns/`.

| Script | Marco | Uso |
|--------|-------|-----|
| `sabesp_2026.sh` | 1 | Campanha R0–R9 Sabesp |
| `sabesp_marco2.sh` | 2 | Coleta expandida + replay R0/R1 |
| `classifier_eval_en.sh` | 3 | PhraseBank + NOSIBLE (só classificação) |
| `fnspid_pilot.sh` | 4 | Piloto FNSPID US |
| `finmarba_diag.sh` | 5 | Concordância FinBERT × FinMarBa |

## Exemplo

```bash
./scripts/campaigns/sabesp_2026.sh init
./scripts/campaigns/sabesp_marco2.sh all
```

## Remoção

Após a tese: `rm -rf scripts/campaigns configs/campaigns` (ver `configs/campaigns/README.md`).
