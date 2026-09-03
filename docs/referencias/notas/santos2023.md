# santos2023.md

# Santos, Bianchi & Costa (2023) — FinBERT-PT-BR

**Citação:** Santos, L. L.; Bianchi, R. A. C.; Costa, A. H. R. FinBERT-PT-BR: Análise de Sentimentos de Textos em Português do Mercado Financeiro. BWAIF 2023. DOI: [10.5753/bwaif.2023.231151](https://doi.org/10.5753/bwaif.2023.231151)

**PDF local:** [pdfs/santos2023_finbert_ptbr.pdf](../pdfs/santos2023_finbert_ptbr.pdf)

## Tese central

Modelo BERT fine-tuned em ~1,4 milhão de notícias financeiras em português, com classificador de sentimento treinado em 503 notícias anotadas (concordância humana alta: ~90%). Supera baselines de domínio geral e demonstra **aplicações em índices de sentimento** e análise macro.

## O que tomamos no lab

- **Classificador principal:** `finbert_ptbr` (Hugging Face: `lucas-leme/FinBERT-PT-BR`)
- **Score contínuo:** \(d = P(\text{pos}) - P(\text{neg})\) — alinhado ao pipeline do ITI
- **Justificativa:** textos financeiros em PT exigem modelo de domínio, não BERT genérico

## Diferença no nosso caso

- Corpus **saneamento/Sabesp**, não o corpus de treino dos autores
- ITI adiciona dimensões \(m,r,e,c,u\) e EWMA — além do índice agregado simples do artigo
- Acurácia no nosso domínio (48%, κ=0,163) **abaixo** das métricas reportadas no artigo (~76%)

## Fases que citam

- F2 (escolha do modelo), F5 (gate κ), Parte 0 (âncora 1)

## Trecho usado (paráfrase)

> O modelo pode ser usado para construir índices de sentimento, estratégias de investimento e análise de dados macroeconômicos — validando a escolha de FinBERT como entrada do ITI, com ressalva de que o desempenho depende do corpus de aplicação.
