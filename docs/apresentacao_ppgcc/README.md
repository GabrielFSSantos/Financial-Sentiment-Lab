# Apresentação de qualificação PPGCC/UFSJ (PDF v4)

Pacote local: **29 slides principais + 8 de apoio** (30 min), manifesto `qualificacao-ufsj-presentation-v4`.

## Compilar

```bash
cd docs/apresentacao_ppgcc
python3 -m venv .venv-render && .venv-render/bin/pip install pillow
python3 scripts/validar_manifesto.py --self-test
make pdf
```

O `make render` usa `.venv-render` quando existir (recorte opcional de figuras com Pillow). Sem Pillow, figuras entram via `graphicx` em tamanho integral.

Saída em `output/`:

- `apresentacao_ppgcc.pdf` — 37 páginas (29 + 8 apoio)
- `apresentacao_ppgcc_roteiro.md` — fala, apontamento, transição e fonte por slide

Pipeline: `validar_manifesto.py` → `render_beamer.py` (composição só via `elements`) → `export_roteiro_fala.py` → `latexmk` (sem fallback `-f`).

## QA visual (opcional)

```bash
python3 -m venv .venv-qa
.venv-qa/bin/pip install pymupdf pillow
make qa
```

Gera `build/qa/alertas.csv` e imagens de contato por slide. Requer PDF já compilado (`make pdf`).

## Contrato v4

| Campo | Papel |
|-------|--------|
| `elements` | Única fonte do desenho no PDF (text, formula, table, chart, raster_chart, …) |
| `screen` / `on_screen` | Espelho textual completo (acessibilidade e roteiro) |
| `voice` / `transition` / `pointing` | Roteiro oral |
| `layout` | Família semântica registrada no renderer |
| `visual` / `objective` | Metadados — não entram automaticamente no PDF |

Edite **`dados/manifesto_slides.json`**; não altere `output/*.md` ou `build/slides_content.tex` à mão.

Relatório de geometria: `build/layout_geometry.json` (gerado em cada `render`).

## Estrutura

| Pasta / arquivo | Função |
|-----------------|--------|
| `dados/` | Manifesto v4 + `fatos_cientificos.json` |
| `assets/` | Figuras empíricas + logos |
| `scripts/` | Validação, render tipado, exportação do roteiro |
| `apresentacao_ppgcc.tex` | Master Beamer 16:9, frames `[plain]` |
| `build/` | LaTeX, caches raster, roteiro intermediário |
| `output/` | PDF e roteiro finais |
