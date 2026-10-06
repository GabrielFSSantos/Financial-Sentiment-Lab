# LLM-as-judge (modelo de linguagem como juiz)

## Uso no Financial Sentiment Lab (qualificação)

**Objetivo:** segunda opinião automatizada na classificação de notícias **para a Sabesp** (POSITIVE / NEGATIVE / NEUTRAL), com **prompt fixo** e registro em CSV — triangulação com anotação humana e FinBERT, **não** substituto de especialista nem gold standard de mercado.

**Onde está operacionalizado:** [annotation_protocol.md](../../tracking/annotation_protocol.md) §7 · cronograma em [qualification_schedule.md](../../tracking/qualification_schedule.md).

**Saída:** `outputs/campaigns/llm_judge_pilot/llm_judge_pilot.csv`

**Comando (piloto):**

```bash
python -m modules.evaluation llm-judge-pilot --limit 10 --mock   # demonstração sem GPU
python -m modules.evaluation llm-judge-pilot --limit 10          # modelo em configs/evaluation.yaml
```

## Metodologia (citar na dissertação)

- Zheng, L. et al. (2023). *Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena.* NeurIPS 2023 Datasets & Benchmarks. [arXiv:2306.05685](https://arxiv.org/abs/2306.05685) — enquadra o uso de modelo grande como avaliador; alerta para vieses (posição, verbosidade).
- Artstein & Poesio (2008) — concordância entre anotadores humanos (complementar ao juiz automático).

## Candidatos a juiz (piloto qualificação)

Modelos com pesos abertos ou artigo que sustente uso em texto financeiro / português. **Papel:** segunda opinião com o mesmo prompt (`prompt_v1_quali`); não substituem FinBERT no ITI.

| # | Modelo | Tipo | Licença / uso | Artigo / evidência | Link | Encaixe |
|---|--------|------|---------------|-------------------|------|---------|
| 1 | FinBERT-PT-BR | Classificador | Pesos abertos (HF) | Santos et al., BWAIF 2023; concordância κ≈0,88 no corpus do artigo | [HF](https://huggingface.co/lucas-leme/FinBERT-PT-BR) · [SBC](https://sol.sbc.org.br/index.php/bwaif/article/view/24960) | Domínio financeiro PT; já no pipeline |
| 2 | BERTimbau Base | Codificador PT | Aberto | Souza et al., BRACIS 2020 | [HF](https://huggingface.co/neuralmind/bert-base-portuguese-cased) | Base PT; bateria em `evaluation.yaml` |
| 3 | Llama 3.1 8B Instruct | Modelo de linguagem | Pesos abertos (termos Meta) | Relatório Llama 3; metodologia juiz: Zheng 2023 | [HF](https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct) | Prompt em português |
| 4 | Mistral 7B Instruct v0.3 | Modelo de linguagem | Apache 2.0 | Jiang et al., Mistral 7B (relatório técnico) | [HF](https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.3) | **Padrão em** `evaluation.yaml` |
| 5 | Qwen2.5 7B Instruct | Modelo de linguagem | Apache 2.0 | Relatório Qwen2.5 (multilíngue) | [HF](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct) | Alternativa multilíngue forte em PT |
| 6 | Sabiá-7B | Modelo de linguagem PT | Pesquisa (licença Llama-1) | Pires et al., *Intelligent Systems* 2023 / [arXiv:2304.07880](https://arxiv.org/abs/2304.07880) | [HF](https://huggingface.co/maritaca-ai/sabia-7b) | Pré-treino monolíngue PT |
| ref. | Marquezan & Assunção (2025) | LLM + emoções × B3 | Artigo no lab | [nota eramiars2025.md](eramiars2025.md) | ver `references/README` | Precedente BR texto + modelo grande + mercado |

**Escolha operacional (semana 1):** um generativo local (Mistral ou Qwen por licença permissiva) + FinBERT; documentar `modelo` no CSV do piloto.

## O que tomamos / o que não tomamos

| Tomamos | Não tomamos |
|---------|-------------|
| Prompt reprodutível em português | LLM como única verdade |
| Subconjunto pequeno (5–10 sem. 1; 10–20 sem. 2) | Treinar ou calibrar ITI só com juiz LLM |
| Discordâncias como material qualitativo | Afirmar κ “bom” na qualificação |

## Decisão

| Decisão | Alternativa | Fundamento |
|---------|-------------|------------|
| Piloto LLM-judge na qualificação | Só humano solo | Orientador 06/10/2026 |
| Prompt fixo `prompt_v1_quali` | Prompt ad hoc por notícia | Reprodutibilidade |
| Implementação `HfCausalLabelJudge` + CLI | Só planilha manual | DR-011 em [decision-register.md](../../research_trail/decision-register.md) |
