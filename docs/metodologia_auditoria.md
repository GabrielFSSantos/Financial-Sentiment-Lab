# Auditoria metodológica — campanha Sabesp

Documento gerado na Fase 0 do plano experimental (strict, ITI semanal, 8+ runs).

## Lacunas identificadas (estado pré-correção)

| Lacuna | Impacto | Correção |
|--------|---------|----------|
| Research usava só `iti_daily.csv` | ITI semanal ignorado na validação | `index_frequency: weekly` + `weekly_align.py` |
| Baselines só diários | Comparação inválida com ITI semanal | `resample_baselines_weekly` |
| Sem filtro empresa/janela | Sabesp diluída com outras empresas | `companies_filter` + dataset `saneamento_sabesp_strict_event` |
| `strict` só na coleta | Ruído broad permanecia no raw | `build_strict_corpus()` offline |
| Sem `--experiment-config` | Grid alpha/ablação manual | Flag no CLI do runner |
| Horizontes em dias | Incompatível com ITI semanal | Horizontes `[1, 2, 4]` semanas |

## Decisões metodológicas

### ITI semanal

- Agregação padrão: `iti_liquido_last` — valor do último dia útil da semana (estado EWMA).
- Alternativa R8: `iti_liquido_mean` — média dos valores diários da semana.
- Retorno semanal: soma de `log_return` diários alinhada ao `period_end` do ITI.

### Corpus strict

- `noticias_strict.csv` preserva `noticias.csv` broad.
- Reaplica `match_entity(titulo + noticia)` em cada registro de `raw/`.
- Descarta registros sem entidade; não gera PENDENTE.

### Equação ITI

```
I_n = d × m × r × c × e × u
R_n = max(0, −d) × m × r × c × q
w_n = c × r × u
ITI_t = α_eff × ITI_{t−1} + (1 − α_eff) × impacto_dia
```

Ablações via `disabled_dimensions` ou `equation_mode: simplified_dc` (R6: `I_n = d·c`, `w_n = c`).

### Entidades

- Sabesp → `SBSP3.SA`
- Copasa → `CSMG3.SA`
- Sanepar → `SAPR4.SA`

### Gate scrape pré-evento

Avançar coleta mai–out/2022 somente se:

- ITI vence B1/B2 em ≥40% das comparações em alguma config R1–R8, **ou**
- FinBERT ≥70% concordância manual **e** correlação semanal ITI×retorno p<0.05 em h=2.

## Artefatos da campanha

- Configs: `configs/experiments/sabesp/r0..r9.yaml`
- Research: `configs/research_weekly_sabesp.yaml`
- Manifest: `outputs/campaigns/sabesp_2026/manifest.json`
- Orquestração: `scripts/run_sabesp_campaign.sh`
