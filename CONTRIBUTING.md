# Como contribuir — Financial Sentiment Lab

## Idioma e nomenclatura

| Camada | Regra |
| --- | --- |
| **Nomes de arquivo e pasta** (todo o repo) | Inglês |
| **Código** (módulos, testes, identificadores, chaves YAML, flags CLI, paths) | Inglês |
| **Prosa** — README, este arquivo, `docs/README.md`, `docs/documentation/*`, `research_trail/`, `references/notas/`, erros voltados ao pesquisador | Português (BR) |
| **Dashboard (UI)** | Português em `modules/dashboard/content/pt_br.py` |
| **Prompts de juiz / anotador** | Português quando o leitor é humano no fluxo de rotulação |

Não traduzir identificadores YAML (`finbert_ptbr`, `water_utilities_corpus`) nem nomes canônicos de colunas legadas (`impacto_alvo`, `rotulo_finbert`) sem DR + migração.

### Exceções documentadas

- `docs/Dissertacao_PPGCC/` — manuscrito ABNT (nomes de capítulo `.tex` em português).
- Módulos com sufixo de idioma/domínio: `classifier_eval_pt.py`, `pt_br.py`.
- Aliases em `configs/evaluation.yaml` e `dataset_aliases` até renomeação completa (ver [06_configuration.md](docs/documentation/06_configuration.md#nomenclatura-e-paths)).
Autoria do repositório: [AUTHORS.md](AUTHORS.md).

## Princípios de engenharia

- Preferir **YAML + reexecução** em vez de novos scripts shell quando o comportamento é dirigido por config.
- Novo modelo de sentimento ou juiz de rótulo: **config + adapter + CLI check/run + schema de saída** (ver contrato de plugin).
- Renomeações destrutivas: usar **aliases** no YAML (`dataset_aliases`, `column_aliases` em evaluation) enquanto chaves legadas de campanha existirem.

## Arquitetura

Referência técnica: [docs/documentation/README.md](docs/documentation/README.md). Contrato de extensão: [docs/documentation/module_plugin_contract.md](docs/documentation/module_plugin_contract.md). Itens em aberto: [docs/documentation/engineering_backlog.md](docs/documentation/engineering_backlog.md).

## Fluxo de trabalho

1. `./scripts/setup_env.sh --fetch-assets` (primeira vez)
2. Alterar **YAML** quando possível em vez de adicionar scripts shell
3. `./scripts/audit_project.sh` antes de abrir um PR

## Adicionar um modelo de sentimento

1. Entrada em `configs/models.yaml`
2. Classe adapter em `modules/models/adapters/`
3. Testes em `tests/`
4. Evitar mudar `experiment/pipeline/runner.py` a menos que o contrato mude

## Adicionar um dataset

1. Entrada em `configs/datasets.yaml` (ou overlay de campanha)
2. Mapeamento de colunas para campos canônicos (`news_id`, `text`, …)
3. Alias opcional via `dataset_aliases` (ex.: `saneamento_corpus` → `water_utilities_corpus`); mapa completo em [docs/documentation/06_configuration.md](docs/documentation/06_configuration.md#nomenclatura-e-paths)
