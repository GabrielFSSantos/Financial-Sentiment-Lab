# Parte 6 — Próximo ciclo

Perguntas que podem **mudar** a conclusão (não repetir fine-tune/LLM como prioridade deste ciclo):

1. **Validação humana maior** — estratificar por gênero, fonte, classe, período (n>100).
2. **Teste fora da janela** — ganho vs B3 em período futuro pré-definido (evidência out-of-sample).
3. **H2 separada** — assimetria neg/pos em retorno, volatilidade ou volume.
4. **Controles de mercado** — sinal residual após IBOV, setor, dia da semana, volatilidade.
5. **Generalização** — Copasa e Sanepar com protocolo idêntico.
6. **Parcimônia do índice** — cada dimensão melhora métrica pré-especificada ou só graus de liberdade?

**Formulação estreita atual:** pipeline funciona; ITI teve vantagem exploratória localizada sobre B3 no evento; vantagem não robusta na expansão; classificador limita interpretação substantiva.

Roadmap operacional pós-04/11: [post_qualification_roadmap.md](../tracking/post_qualification_roadmap.md). Implementação futura (juiz, κ, out-of-sample) deve atualizar [decision-register.md](decision-register.md).

---

---

**Próximo:** [Apêndices](appendices.md)
