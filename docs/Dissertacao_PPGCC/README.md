# Dissertação PPGCC/UFSJ — ITI / saneamento

```bash
cd docs/Dissertacao_PPGCC
latexmk -pdf ufsj-abntex2.tex
```

Em `ufsj-abntex2.tex`, `\qualificacaoparcialtrue` compila apenas capítulos 1–2, apêndice e bibliografia; `\qualificacaoparcialfalse` (padrão) inclui proposta, metodologia e andamentos.

`06_proximos_passos.tex` não entra na compilação oficial.

## Tom do manuscrito (qualificação → defesa)

O PDF é tratado como **documento final em evolução**: redação no tempo presente do desenho; resultados só do que já foi medido; subseções sem dados podem existir com **corpo vazio** (acréscimo futuro, sem remover texto).

No LaTeX **não** entram: pendências operacionais, justificativas de etapas futuras, paths de `outputs/`, identificadores internos de decisão (DR-xxx), piloto LLM-as-judge ou narrativa de infraestrutura (WSL, GPU, mock). Cronograma de qualificação e roadmap operacional ficam fora do manuscrito; números canônicos em `docs/research_trail/part-04-results.md`.
