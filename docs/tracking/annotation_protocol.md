# Protocolo de anotação — amostra Sabesp (Trilha A)

**Versão do protocolo:** 2026-10-07  
**Status:** em uso na qualificação (pós-orientação 06/10/2026)  
**Amostra canônica:** 100 notícias em `data/water_utilities_corpus/manual_labels_100.csv`  
**Acompanhamento:** [qualification_schedule.md](qualification_schedule.md) · **Detalhe operacional:** [qualification_plan_2026-11-04.md](qualification_plan_2026-11-04.md)

---

## 0. Finalidade na qualificação (orientador, 06/10/2026)

| Pergunta | Resposta |
|----------|----------|
| Para que serve esta amostra? | **Validar o pipeline**: planilha anotada → junção com corpus → métricas (`classifier_eval_pt`) → relatório. |
| É “verdade absoluta” sobre o mercado? | **Não.** O anotador principal não é especialista em mercado financeiro; a amostra é **referência operacional** para testar o fluxo. |
| O que não fazer na qualificação? | Não apresentar κ ou acurácia como prova de que o índice explica a ação; não fechar hipótese H1. |
| Mitigações | (1) **Segundo anotador humano** (ex.: Rafael) em **subconjunto** (~30 notícias); (2) **Segunda classificação automatizada** com instrução fixa em 10–20 casos — triangulação, não substituto do humano. |

---

## Referência exploratória (arquivo)

Rodada anterior solo, critério simplificado, métricas históricas (48%, κ≈0,16): `data/water_utilities_corpus/manual_labels_100_exploratorio.csv`. Linha do tempo: [research_trail part-04 §4.4.1](../research_trail/part-04-results.md#441-linha-do-tempo-da-anotação-manual) · [DR-012](../research_trail/decision-register.md).

---

## 1. Escopo

- **Empresa-alvo padrão:** Sabesp (`SBSP3`).
- **Texto:** usar o mesmo `news_id` do corpus strict; não reescrever IDs.
- **Classes de impacto:** `POSITIVE`, `NEGATIVE`, `NEUTRAL` (campo `impacto_alvo`).
- **Campos opcionais de triangulação:** `rotulo_llm_juiz`, `notas_llm` (piloto semana 2).

---

## 2. Definições de `impacto_alvo`

| Classe | Critério |
|--------|----------|
| POSITIVE | Fato que melhora perspectiva da empresa-alvo (resultado, contrato, decisão regulatória favorável, etc.) |
| NEGATIVE | Prejuízo, multa, atraso, risco ou crítica direta à empresa-alvo |
| NEUTRAL | Menção sem valência clara para a empresa-alvo, ou agenda setorial sem efeito direto identificável |

**Não** usar o tom da manchete se o corpo do texto for neutro para a Sabesp.

---

## 3. Tipologia (`tipologia`)

| Valor | Quando usar |
|-------|-------------|
| `focal_sabesp` | A Sabesp é protagonista do fato |
| `roundup_agenda` | Várias empresas ou visão de mercado; julgar só o impacto na empresa-alvo |
| `mencao_tangencial` | Sabesp citada de passagem, sem evento próprio |

---

## 4. Campos do CSV (amostra formal)

| Coluna | Obrigatório | Descrição |
|--------|-------------|-----------|
| `news_id` | sim | Chave do corpus |
| `empresa_alvo` | sim | Ex.: `Sabesp` |
| `tipologia` | sim | Ver §3 |
| `impacto_alvo` | sim | POSITIVE / NEGATIVE / NEUTRAL (rótulo humano principal) |
| `sentimento_global` | não | Tom da matéria inteira (opcional, diagnóstico) |
| `ambiguo` | não | `true` se houver dúvida persistente |
| `rotulo_finbert` | não | Saída do classificador (referência) |
| `rotulo_llm_juiz` | não | Piloto segunda classificação (§7) |
| `notas` | não | Casos limite, multiempresa |
| `notas_llm` | não | Justificativa curta retornada pelo modelo (piloto) |
| `anotador` | sim | Identificador do anotador |
| `anotador_2` | não | Segundo humano (IAA) |
| `impacto_alvo_2` | não | Rótulo do segundo anotador |
| `versao_protocolo` | sim | Ex.: `2026-10-07` |

---

## 5. Fluxo do anotador

1. Abrir notícia pelo `news_id` em `noticias_strict_sabesp.csv` (ou `articles_strict_sabesp.csv`).
2. Preencher `empresa_alvo` e `tipologia`.
3. Atribuir `impacto_alvo` com foco na empresa-alvo.
4. Se incerto: `ambiguo=true` e descrever em `notas`.
5. Salvar incrementalmente em `data/water_utilities_corpus/manual_labels_100.csv`.

Avaliação do pipeline (quando houver linhas suficientes):

```bash
python -m modules.evaluation.classifier_eval_pt prepare
python -m modules.evaluation.classifier_eval_pt run
```

Interpretar métricas como **diagnóstico do fluxo**, não como conclusão de pesquisa na qualificação.

---

## 6. Concordância entre anotadores (IAA) — Rafael ou outro

**Meta (semana 2):** segundo anotador em **~30** notícias estratificadas (misturar `focal_sabesp` e `roundup_agenda`).

1. Escolher `news_id` fixos; preencher `anotador_2` / `impacto_alvo_2` na mesma linha.
2. Calcular concordância (kappa de Cohen) **entre humanos**, separado de humano × FinBERT.
3. Divergências → revisar instruções deste protocolo (não “forçar” consenso sem registrar).

Registrar no [qualification_schedule.md](qualification_schedule.md) se o apoio foi confirmado e em que datas.

---

## 7. Segunda classificação automatizada (piloto — semana 2)

### 7.1 Objetivo

Obter **segunda opinião automatizada** em notícias difíceis; comparar com `impacto_alvo` e com `rotulo_finbert`.

### 7.2 Escopo do piloto

Contrato técnico: [module_plugin_contract.md](../documentation/module_plugin_contract.md) · regras κ: [12_regras_de_negocio.md](../documentation/12_regras_de_negocio.md) §12.6 · código: `modules/evaluation/judges/` · config: `configs/evaluation.yaml` · teste: `tests/test_label_judges.py`.

- **10 a 20** `news_id` (priorizar `ambiguo=true` ou `roundup_agenda`).
- **Não** commitar chaves de API no repositório.
- Salvar saída sugerida: `outputs/campaigns/llm_judge_pilot/llm_judge_pilot.csv`.

### 7.3 Prompt template (versão `prompt_v1_quali`)

Copiar o bloco abaixo como instrução do sistema ou prefixo da mensagem. Substituir `{TITULO}` e `{TEXTO}`.

```text
Você avalia o impacto de uma notícia financeira/jornalística APENAS para a empresa-alvo: Sabesp (saneamento, Brasil).

Classes (responda exatamente uma): POSITIVE, NEGATIVE, NEUTRAL.

- POSITIVE: fato favorável à Sabesp.
- NEGATIVE: fato desfavorável à Sabesp.
- NEUTRAL: sem efeito claro para a Sabesp, ou menção tangencial.

Se a matéria menciona várias empresas, ignore o tom geral do mercado e julgue só a Sabesp.

Responda em duas linhas:
CLASSE: <POSITIVE|NEGATIVE|NEUTRAL>
JUSTIFICATIVA: <uma frase curta em português>

Título: {TITULO}
Texto: {TEXTO}
```

### 7.4 Critérios de sucesso do piloto (qualificação)

- Prompt e modelo usados **documentados** no CSV ou em nota de 1 parágrafo no texto (metodologia/andamentos).
- Lista de discordâncias humano × modelo × FinBERT para discussão qualitativa.

Implementação: `python -m modules.evaluation llm-judge-pilot` (opcional na semana 2; prioridade = CSV + prompt reprodutível).

---

## 8. Limitações declaradas na qualificação

- Amostra n=100; anotação principalmente individual até IAA no subconjunto.
- Gate operacional (acurácia ~70% ou κ ≥ 0,40 vs gold) **não** é meta da entrega de 04/11/2026.
- Classificação automatizada auxiliar pode repetir vieses do modelo; uso **exploratório** apenas.

---

## 9. Referências

- Cronograma vivo: [qualification_schedule.md](qualification_schedule.md)
- Plano mestre: [qualification_plan_2026-11-04.md](qualification_plan_2026-11-04.md)
- Nota bibliográfica: [references/notas/llm_judge.md](../references/notas/llm_judge.md)
- Metodologia no manuscrito: [Dissertacao_PPGCC/04_metodologia.tex](../Dissertacao_PPGCC/04_metodologia.tex)
