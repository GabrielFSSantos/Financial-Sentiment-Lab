# souza2020.md

# Souza, Nogueira & Lotufo (2020) — BERTimbau

**PDF local:** [pdfs/souza2020_bertimbau.pdf](../pdfs/souza2020_bertimbau.pdf)

**Citação:** Souza, F.; Nogueira, R.; Lotufo, R. BERTimbau: Pretrained BERT Models for Brazilian Portuguese. BRACIS 2020. DOI: [10.1007/978-3-030-61377-8_28](https://doi.org/10.1007/978-3-030-61377-8_28)

## Tese central

Modelos BERT pré-treinados em grande corpus de português brasileiro; base para fine-tunes de domínio.

## O que tomamos no lab

- FinBERT-PT-BR é fine-tune **financeiro** sobre BERTimbau — explicamos a cadeia linguística PT
- `bertimbau_sentiment` entrou como **controle** na bateria κ (Marco 3)

## Diferença no nosso caso

- Não usamos BERTimbau cru no ITI principal — apenas como baseline de classificação
- Controle não passou gate (κ=0,087)

## Fases que citam

- Parte 0 (âncora 2), F5
