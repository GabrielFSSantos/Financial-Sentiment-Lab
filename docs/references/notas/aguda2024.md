# Aguda et al. (2024) — LLMs como anotadores financeiros

**Citação:** Aguda, T. D. et al. Large Language Models as Financial Data Annotators. LREC-COLING 2024. [ACL Anthology](https://aclanthology.org/2024.lrec-main.885/) · [arXiv:2403.18152](https://arxiv.org/abs/2403.18152)

**PDF local:** [pdfs/aguda2024_llm_annotators.pdf](../pdfs/aguda2024_llm_annotators.pdf)

## Tese central

Compara GPT-4, PaLM 2 e MPT com **especialistas** e *crowdworkers* em anotação de relações em documentos financeiros. LLMs podem substituir **não especialistas**, mas não os especialistas de forma geral; índice de confiabilidade (LLM-RelIndex) para casos que exigem revisão humana.

## O que tomamos no lab

- Fundamenta **LLM-as-annotator** (piloto `llm-judge-pilot`, DR-007/011), **não** como gold automático.
- Prompt adaptado à tarefa + exemplos — alinhado a `prompt_v1_quali`.

## Diferença

- Nossa tarefa é **sentimento/impacto por empresa** (3 classes), não extração de relações REFinD; uso é **triangulação** com humanos e FinBERT.
