# Como contribuir — Financial Sentiment Lab

## Idioma

| Camada | Idioma |
| --- | --- |
| Código, paths, CLI, nomes de módulos e arquivos em `docs/` | Inglês |
| README do projeto, este arquivo, `docs/README.md`, `docs/documentation/*`, `research_trail/`, `tracking/`, mensagens de erro voltadas ao pesquisador | Português (BR) |
| Dashboard (UI) | Português em `modules/dashboard/content/pt_br.py` |

Não traduzir identificadores YAML (`finbert_ptbr`, `water_utilities_corpus`) nem docstrings técnicas longas em código — só o que o pesquisador lê fora do IDE.

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
3. Alias opcional via `dataset_aliases` (ex.: `saneamento_corpus` → `water_utilities_corpus`); mapa completo em [docs/documentation/06_configuracoes.md](docs/documentation/06_configuracoes.md#nomenclatura-e-paths)
