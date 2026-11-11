.PHONY: all pdf validate render clean check_log qa

MAIN := apresentacao_ppgcc.tex
BUILD := build
OUTPUT := output
PDF := $(OUTPUT)/apresentacao_ppgcc.pdf
BUILD_PDF := $(BUILD)/apresentacao_ppgcc.pdf

all: pdf

PYTHON ?= python3
ifneq ($(wildcard .venv-render/bin/python),)
PYTHON := .venv-render/bin/python
endif

validate:
	python3 scripts/validar_manifesto.py

render: validate
	@mkdir -p $(BUILD) $(OUTPUT) $(BUILD)/raster_cache
	$(PYTHON) scripts/render_beamer.py
	python3 scripts/export_roteiro_fala.py

pdf: render
	latexmk -pdf -interaction=nonstopmode -halt-on-error -file-line-error -output-directory=$(BUILD) $(MAIN)
	@test -s $(BUILD_PDF)
	@$(MAKE) check_log
	@grep -Eq 'Output written on .*apresentacao_ppgcc\.pdf \(37 pages' $(BUILD)/apresentacao_ppgcc.log
	@cp -f $(BUILD_PDF) $(PDF)

check_log:
	@grep -E '^(! LaTeX Error|! Undefined control sequence|! Package ufsjdeck|! Missing character|! Emergency stop|! Fatal error)' \
		$(BUILD)/apresentacao_ppgcc.log && exit 1 || true

qa: pdf
	@test -x .venv-qa/bin/python || (echo "Crie .venv-qa com pymupdf e pillow; veja README." && exit 1)
	.venv-qa/bin/python scripts/qa_slides_ppgcc.py $(PDF) --out build/qa --dpi 180

qa-strict: pdf
	@test -x .venv-qa/bin/python || (echo "Crie .venv-qa com pymupdf e pillow; veja README." && exit 1)
	.venv-qa/bin/python scripts/qa_slides_ppgcc.py $(PDF) --out build/qa --dpi 200 --strict

clean:
	rm -rf $(BUILD) $(OUTPUT)
	rm -f qualificacao.* apresentacao_ppgcc.aux apresentacao_ppgcc.fdb_latexmk \
		apresentacao_ppgcc.fls apresentacao_ppgcc.log apresentacao_ppgcc.nav \
		apresentacao_ppgcc.out apresentacao_ppgcc.snm apresentacao_ppgcc.toc \
		apresentacao_ppgcc.vrb apresentacao_ppgcc.pdf qualificacao.pdf
	rm -rf generated
