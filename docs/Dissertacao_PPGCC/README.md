# Dissertação PPGCC (abnTeX2 / UFSJ)

Manuscrito: problema, revisão, lacuna, proposta do ITI, metodologia operacional e andamentos experimentais (sem conclusão de desempenho).

## Qualificação parcial vs. tese completa

Em `ufsj-abntex2.tex`, a flag `\qualificacaoparcialtrue` (padrão atual) compila **somente** os capítulos 1–2, o apêndice (`99_apendices.tex`) e a bibliografia — versão para envio à qualificação.

Para o manuscrito completo, comente `\qualificacaoparcialtrue` (ou use `\qualificacaoparcialfalse`) para incluir também `03_proposta`, `04_metodologia` e `05_andamentos`. O arquivo `06_proximos_passos.tex` permanece fora da compilação oficial (rascunho interno).

## Compilar

```bash
cd docs/Dissertacao_PPGCC
latexmk -pdf ufsj-abntex2.tex
```

PDF: `ufsj-abntex2.pdf`

## Arquivos de conteúdo

| Arquivo | Função |
| --- | --- |
| `ufsj-abntex2.tex` | Documento principal |
| `00_pretextual.tex` | Folha de aprovação, agradecimentos, resumos |
| `01_introducao.tex` | Problema, justificativa, objetivos, H1 |
| `02_revisao.tex` | Revisão por linhas de literatura e lacuna |
| `03_proposta.tex` | O que é o ITI e o que não replica |
| `04_metodologia.tex` | Protocolo operacional (corpus, EWMA, B0–B3, 24 duelos) |
| `05_andamentos.tex` | O que já rodou, com ressalvas (gate κ, exercício R0/R1) |
| `06_proximos_passos.tex` | O que falta para avaliação de desempenho |
| `referencias.bib` | Symlink → `../references/bibliografia.bib` |
| `abntex2-options.bib` | Opções abnTeX2 (BibTeX) |
| `abntex2-alf.bst` | Estilo autor-data ABNT |

Não restaurar `memoir.cls.bak`: o `memoir.cls` de 2015 quebra o TeX Live 2025.

PDFs das referências: `docs/references/pdfs/`, nomes no padrão `autorANO_tema.pdf` (ver `docs/references/README.md`).
