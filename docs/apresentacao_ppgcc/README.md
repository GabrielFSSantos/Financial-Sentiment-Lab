# Apresentação de qualificação PPGCC/UFSJ (PDF)

Pacote de build local: **29 slides principais + 8 de apoio** (30 min), alinhado à dissertação em `docs/dissertacao_ppgcc/`.

## Compilar

```bash
cd docs/apresentacao_ppgcc
make pdf
```

Saída em `output/`:

- `apresentacao_ppgcc.pdf` — slides
- `apresentacao_ppgcc_roteiro.md` — fala completa (29 principais + 8 apoio), gerada do manifesto

Artefatos LaTeX ficam em `build/` (efêmeros; `make clean` remove tudo). **Editar o roteiro** em `dados/manifesto_slides.json` (`objective`, `voice`, `on_screen`, `transition`), não no `.md` gerado.

Passos: `validar_manifesto.py` → `render_beamer.py` (campo `layout` no manifesto) + `export_roteiro_fala.py` → `latexmk` com `-output-directory=build`.

Cada slide principal define `layout` (ex.: `CAPA`, `CORPUS_BARRAS`, `FORMULA_DESTAQUE`); o renderer gera o frame Beamer correspondente. O campo `visual` orienta desenho/Slides e **não** entra no PDF.

## Estrutura (espelha `docs/dissertacao_ppgcc`)

| Pasta / arquivo | Função |
|-----------------|--------|
| `dados/` | `manifesto_slides.json` (conteúdo, layout, roteiro), `fatos_cientificos.json` |
| `assets/` | Figuras dissertação + logos (`logo_dcomp.png`, `logo_ufsj_ppgcc.png`) |
| `fonts/` | Notas sobre fontes |
| `scripts/` | Validação e render Beamer |
| `apresentacao_ppgcc.tex` | Master Beamer 16:9 |
| `build/` | Gerado (não versionar) |
| `output/` | PDF + roteiro `.md` (não versionar) |

## Conteúdo editável

Manifesto (`dados/manifesto_slides.json`) é a fonte única de texto de tela e roteiro de fala; regenere com `make pdf`.
