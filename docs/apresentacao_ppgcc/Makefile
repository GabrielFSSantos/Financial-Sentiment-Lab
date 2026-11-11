.PHONY: all pdf validate render clean

MAIN := apresentacao_ppgcc.tex
BUILD := build
OUTPUT := output
PDF := $(OUTPUT)/apresentacao_ppgcc.pdf

all: pdf

validate:
	python3 scripts/validar_manifesto.py

render: validate
	@mkdir -p $(BUILD) $(OUTPUT)
	python3 scripts/render_beamer.py
	python3 scripts/export_roteiro_fala.py

pdf: render
	@mkdir -p $(BUILD) $(OUTPUT)
	latexmk -pdf -interaction=nonstopmode -output-directory=$(BUILD) $(MAIN) || \
		latexmk -pdf -f -interaction=nonstopmode -output-directory=$(BUILD) $(MAIN)
	@cp -f $(BUILD)/apresentacao_ppgcc.pdf $(PDF)

clean:
	rm -rf $(BUILD) $(OUTPUT)
	rm -f qualificacao.* apresentacao_ppgcc.aux apresentacao_ppgcc.fdb_latexmk \
		apresentacao_ppgcc.fls apresentacao_ppgcc.log apresentacao_ppgcc.nav \
		apresentacao_ppgcc.out apresentacao_ppgcc.snm apresentacao_ppgcc.toc \
		apresentacao_ppgcc.vrb apresentacao_ppgcc.pdf qualificacao.pdf
	rm -rf generated
