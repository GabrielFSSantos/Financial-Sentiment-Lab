.PHONY: all pdf verify clean

MAIN := dissertacao_ppgcc.tex
BUILD := build
OUTPUT := output
PDF := $(OUTPUT)/dissertacao_ppgcc.pdf
BASENAME := dissertacao_ppgcc
BBL := $(BUILD)/$(BASENAME).bbl
LOG := $(BUILD)/$(BASENAME).log

export TEXINPUTS := ./styles//:$(TEXINPUTS)
export BSTINPUTS := ./styles//:$(BSTINPUTS)
export BIBINPUTS := .:./styles//:$(BIBINPUTS)

LATEXMK := latexmk -pdf -interaction=nonstopmode \
	-output-directory=$(BUILD) -auxdir=$(BUILD) -emulate-aux-dir

all: pdf

pdf:
	@mkdir -p $(BUILD) $(OUTPUT)
	$(LATEXMK) $(MAIN)
	@test -s $(BBL) || (echo "ERRO: $(BBL) ausente — BibTeX não rodou." >&2; exit 1)
	@if grep -q 'Citation.*undefined' $(LOG); then \
		echo "ERRO: citações indefinidas no log — conferir $(LOG)." >&2; exit 1; \
	fi
	@cp -f $(BUILD)/$(BASENAME).pdf $(PDF)

# Regressão: 56 páginas; sem '??' no texto; bloco Referências presente.
BASELINE ?= $(FSL_BASELINE_PDF)
EXPECTED_PAGES ?= 56

verify: pdf
	@PAGES=$$(mutool info '$(PDF)' 2>/dev/null | awk '/^Pages:/ {print $$2}'); \
	if [ "$$PAGES" != "$(EXPECTED_PAGES)" ]; then \
		echo "ERRO: esperado $(EXPECTED_PAGES) páginas, obtido $$PAGES" >&2; exit 1; \
	fi
	@mutool convert -F txt -o /tmp/dissertacao_ppgcc-verify.txt '$(PDF)'
	@if grep -qE '\?\?(\)|\?)' /tmp/dissertacao_ppgcc-verify.txt; then \
		echo "ERRO: citações quebradas (??) no PDF." >&2; exit 1; \
	fi
	@if ! grep -q 'Referências' /tmp/dissertacao_ppgcc-verify.txt; then \
		echo "ERRO: seção Referências ausente no PDF." >&2; exit 1; \
	fi
	@if [ -n "$(BASELINE)" ] && [ -f "$(BASELINE)" ]; then \
		mutool convert -F txt -o /tmp/dissertacao_ppgcc-baseline.txt "$(BASELINE)"; \
		if grep -qE '\?\?(\)|\?)' /tmp/dissertacao_ppgcc-baseline.txt; then \
			echo "AVISO: baseline também contém ?? — diff pode ser ruidoso." >&2; \
		fi; \
	fi
	@echo "OK: verify ($(EXPECTED_PAGES) p., .bbl, Referências)"

clean:
	rm -rf $(BUILD) $(OUTPUT)
	rm -f dissertacao_ppgcc.aux dissertacao_ppgcc.bbl dissertacao_ppgcc.blg dissertacao_ppgcc.brf \
		dissertacao_ppgcc.fdb_latexmk dissertacao_ppgcc.fls dissertacao_ppgcc.idx dissertacao_ppgcc.ilg \
		dissertacao_ppgcc.ind dissertacao_ppgcc.log dissertacao_ppgcc.out dissertacao_ppgcc.toc \
		dissertacao_ppgcc.pdf ufsj-abntex2.* chapters/*.aux
