# Documentação — Financial Sentiment Lab

Toda a documentação do projeto vive nesta pasta. O [README.md](../README.md) na raiz do repositório é a **entrada rápida** para GitHub (instalação, comandos e visão geral). Aqui estão os dois documentos principais da pesquisa.

---

## Documentos

| Arquivo | Para quem | Conteúdo |
| --- | --- | --- |
| [documentacao.md](documentacao.md) | Desenvolvedores e revisores técnicos | Módulos, fluxos, fórmulas do ITI, configs YAML, research, dashboard, testes |
| [trajetoria.md](trajetoria.md) | Pesquisa e apresentações | Histórico run a run, marcos experimentais, resultados da campanha Sabesp, decisões |

---

## Ordem de leitura sugerida

1. [README.md § Entendendo a pesquisa](../README.md#entendendo-a-pesquisa) — visão em 2 minutos
2. [documentacao.md §1.5 — Conceitos em linguagem acessível](documentacao.md#15-conceitos-em-linguagem-acessível) — ITI, α, baselines, 24 comparações
3. [trajetoria.md — Marco 1 (campanha Sabesp R0–R9)](trajetoria.md#marco-1--campanha-sabesp-2026-r0r9) — melhor resultado e síntese
4. [documentacao.md §3–§5](documentacao.md#3-módulos) — aprofundamento técnico conforme necessidade

---

## Seções mais usadas

### Conceitos e metodologia

- [Conceitos acessíveis (ITI, baselines, validação)](documentacao.md#15-conceitos-em-linguagem-acessível)
- [Fórmulas do ITI e ablações](documentacao.md#4-fórmulas-do-iti)
- [Modos diário e semanal no research](documentacao.md#50-modos-diário-e-semanal)
- [Auditoria metodológica — por que o Marco 1 existiu](trajetoria.md#auditoria-metodológica--por-que-o-marco-1-existiu)

### Resultados experimentais

- [Resumo comparativo R0–R9](trajetoria.md#resumo-comparativo)
- [Síntese do Marco 1 — o que funcionou e limitações](trajetoria.md#síntese-do-marco-1)
- [Como atualizar a trajetória após novas runs](trajetoria.md#como-atualizar-este-documento)

### Operação

- [Entrypoints e scripts](documentacao.md#2-entrypoints-e-scripts)
- [Configurações principais (YAML)](documentacao.md#6-configurações-principais)
- [Dashboard Streamlit](documentacao.md#8-dashboard-streamlit)
- [Testes](documentacao.md#9-testes)

---

## Artefatos estruturados (fora da documentação)

Dados e resultados numéricos permanecem em:

- `outputs/campaigns/{campanha}/manifest.json` — resumo da campanha
- `outputs/{run_id}/research/.../incremental_deltas.csv` — comparações ITI vs baselines
- `configs/experiments/` — YAML por run

Ao documentar uma nova campanha, extraia números desses artefatos e atualize [trajetoria.md](trajetoria.md); se o protocolo mudar, atualize também [documentacao.md](documentacao.md).
