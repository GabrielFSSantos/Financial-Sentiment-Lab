# Parte 6 — Próximo ciclo

Perguntas que podem **mudar** a conclusão (não repetir fine-tune/LLM como prioridade deste ciclo):

1. **Validação humana maior** — estratificar por gênero, fonte, classe, período (n>100).
2. **Teste fora da janela** — ganho vs B3 em período futuro pré-definido (evidência out-of-sample).
3. **H2 separada** — assimetria neg/pos em retorno, volatilidade ou volume.
4. **Controles de mercado** — sinal residual após IBOV, setor, dia da semana, volatilidade.
5. **Generalização** — Copasa e Sanepar com protocolo idêntico.
6. **Parcimônia do índice** — cada dimensão melhora métrica pré-especificada ou só graus de liberdade?

**Formulação estreita atual:** pipeline funciona; ITI legado (R1) sem vitórias significativas no corpus canônico; campanha **ITI-v2** (`iti_v2_prod_20261022`) não detectou associação Spearman com retorno h=1 no painel exploratório — ver [part-04 §4.7](part-04-results.md); classificador e referência humana limitam interpretação substantiva.

Implementação futura (juiz, κ ampliado, out-of-sample) deve atualizar [decision-register.md](decision-register.md) e [part-03-phases.md](part-03-phases.md).

---

---

**Próximo:** [Apêndices](appendices.md)
