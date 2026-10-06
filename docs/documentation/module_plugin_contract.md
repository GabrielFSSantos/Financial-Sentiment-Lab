# Contrato de plugin — modelos, juízes e extensões

Texto em PT; **nomes de código e config em inglês**.

## Objetivo

Permitir que um pesquisador adicione um **modelo de sentimento**, um **juiz de rótulos** (ex.: LLM) ou um **portal de notícias** sem alterar o núcleo do pipeline ITI → research.

## Checklist de um plugin

| # | Entrega | Exemplo |
| --- | --- | --- |
| 1 | Entrada YAML | `configs/models.yaml` ou `configs/evaluation.yaml` |
| 2 | Classe adapter | `BaseSentimentModel` ou `BaseLabelJudge` |
| 3 | Assets locais ou API | `model_store/`; secrets em `.env` (nunca no Git) |
| 4 | CLI | `python -m modules.<pkg> check` + subcomando batch |
| 5 | Schema de saída | CSV/JSON em `outputs/{run_id}/` ou `outputs/campaigns/` |
| 6 | Teste mínimo | `tests/test_*.py` com fixture pequena |

## Modelo de sentimento (existente)

- Interface: [`modules/models/base.py`](../../modules/models/base.py) — `BaseSentimentModel`
- Registro: [`modules/models/registry.py`](../../modules/models/registry.py)
- Config: `adapter:` apontando para classe Python

## Juiz de rótulos (LLM — futuro)

- Interface: [`modules/evaluation/judges/base.py`](../../modules/evaluation/judges/base.py) — `BaseLabelJudge`
- Stub: [`modules/evaluation/judges/llm_stub.py`](../../modules/evaluation/judges/llm_stub.py)
- Protocolo de pesquisa: [annotation_protocol.md](../tracking/annotation_protocol.md) §7
- Saída piloto: `outputs/campaigns/llm_judge_pilot/llm_judge_pilot.csv`

Comportamento esperado: processar apenas `news_id` **sem** rótulo de juiz; idempotente (pular já julgados).

## Scraper / entidades

- Entidades listadas em [`configs/entities.yaml`](../../configs/entities.yaml)
- Match em [`modules/scrapers/schema/entities.py`](../../modules/scrapers/schema/entities.py)

## O que não fazer

- Lógica de ITI ou research dentro de `evaluation/` ou `scrapers/`
- Paths absolutos hardcoded — usar `modules.common.paths` ou config YAML
