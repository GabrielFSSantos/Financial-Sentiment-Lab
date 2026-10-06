# Cronograma para qualificação — pesquisa com notícias da Sabesp

**Aluno:** Gabriel Felipe Souza Santos  
**Programa:** Mestrado em Ciência da Computação — PPGCC/UFSJ  
**Prazo de envio:** 04 de novembro de 2026  

Documento de **acompanhamento vivo**: marque os checkboxes ao concluir e preencha a **entrega realizada** ao fim de cada semana. Detalhe técnico (código, cluster, dia a dia): [qualification_plan_2026-11-04.md](qualification_plan_2026-11-04.md).

---

## 1. Pesquisa

A pesquisa estuda **notícias sobre a Sabesp** (companhia de saneamento) e tenta construir um **índice ao longo do tempo** — chamado **Índice Temporal Informacional (ITI)** — que resume, dia a dia, o “clima” das notícias em relação à empresa.

O fluxo, em termos simples:

1. **Coleta** — reunir notícias de portais de economia e jornais (título, data, texto).  
2. **Classificação** — um **programa de computador** (modelo de inteligência artificial treinado para textos financeiros em português) sugere se cada notícia é mais **positiva**, **negativa** ou **neutra** para a empresa.  
3. **Índice** — as notícias de cada dia são combinadas em um número que **lembra o passado recente** (notícias de ontem ainda influenciam um pouco o índice de hoje).  
4. **Comparação** — só **depois** montamos o índice, comparamos com **medidas mais simples** e, em passo separado, verificamos se há **alguma relação estatística** com a **variação do preço da ação** na bolsa (estudo acadêmico, não recomendação de investimento).

**Até a qualificação**, o objetivo principal é:

* **Escrever** o texto da dissertação (problema, literatura, proposta, método, andamentos e próximos passos).  
* **Organizar** a validação do **procedimento** de classificação (anotação humana, eventual segundo anotador e **modelo de linguagem como juiz**), sem tratar a amostra como prova definitiva sobre o mercado.

---

## 2. Orientação do professor (06/10/2026) — o que priorizar

| Prioridade | Em prática |
|------------|------------|
| **Avenida de pesquisa** | Deixar claro no texto: problema, lacuna, perguntas, objetivos, hipótese e **desenho do experimento**. |
| **Revisão bibliográfica** | Bem feita, com **lacuna** destacada. |
| **Setup experimental** | Descrever como o estudo será avaliado (passo a passo reprodutível). |
| **Resultados iniciais** | O que já roda no computador e o que a amostra manual mostra — **sem** fechar conclusão sobre a bolsa. |
| **Anotação manual** | Importante, mas pode ser criticada (anotador não é especialista de mercado). Usar a amostra sobretudo para **validar o pipeline** (planilha → métricas → relatório), não para “provar” o índice. |
| **Mitigações** | Conversar com **Rafael** (ou outro) para anotar um subconjunto; testar **modelo de linguagem como juiz** (segunda opinião com prompt fixo). |
| **Formato** | Texto no **formato da dissertação** (PDF) até 04/11. |

### Modelo de linguagem como juiz (resumo)

* **O que é:** pedir a um modelo de linguagem grande (por exemplo, via API) que classifique a notícia **para a Sabesp**, com o mesmo critério positivo/negativo/neutro, usando um **texto de instrução fixo**.  
* **Para que serve na qualificação:** comparar com sua anotação e com o programa FinBERT em casos difíceis ou ambíguos (triangulação).  
* **O que não é:** não substitui especialista humano, não é “verdade de mercado” e não serve para treinar o índice como se fosse ouro.

Regras detalhadas: [annotation_protocol_v2.md](annotation_protocol_v2.md).

**Perguntas da banca sobre método/mercado:** responder com o protocolo fixo (24 duelos, semanal, sem causalidade) — [research_trail part-02](../research_trail/part-02-protocol.md) e limites em [12_regras_de_negocio §12.4](../documentation/12_regras_de_negocio.md).

---

## 3. Onde estamos hoje

* Já é possível ir da notícia coletada até o índice diário e até comparações com alternativas simples e com o retorno da ação, seguindo um **roteiro fixo de análise** (reprodutibilidade do **procedimento**).  
* Cerca de **100 notícias** já tiveram rótulo manual em versão anterior; vamos **revisar com regras novas** (impacto **para a Sabesp**, matérias com várias empresas).  
* O programa acertou cerca de **48%** em relação à anotação antiga; a concordância (*kappa de Cohen*) ficou **baixa**. Isso **não** autoriza conclusões sobre o mercado — só mostra que a etapa de classificação precisa melhorar.  
* Testes índice × ação já rodados servem para ver se o **protocolo de comparação** funciona, não para confirmar a hipótese principal.

---

## 4. Cronograma por semanas (07/10 a 04/11/2026)

### Visão geral

| Semana | Período | Escrita e estudo | Trabalho prático | Entrega prevista |
| :---: | ----- | ----- | ----- | ----- |
| **1** | 07 a 13/out | Introdução e revisão (lacuna, referências); **perguntas de pesquisa** explícitas; objetivos e hipótese; roteiro de anotação | Iniciar `rotulos_manual_100_v2.csv`; revisar **25 a 35** notícias; **contatar Rafael** | PDF parcial (intro + revisão) + roteiro de anotação |
| **2** | 14 a 20/out | **Metodologia** e **setup experimental** (como avaliar a hipótese) | Anotação até **~80** notícias; **piloto LLM-juiz** (10–20 notícias); IAA com Rafael se confirmado (~30 itens) | Rascunho metodologia + planilha atualizada |
| **3** | 21 a 27/out | **Andamentos** (pipeline, amostra, limitações) e **próximos passos** | Reprocessar no computador só se classificação estável; senão, texto e anotação | **PDF intermediário** para o orientador |
| **4** | 28/out a 04/nov | Revisão final, resumo, folha de rosto | Conferir números do texto com planilhas | **02/11** texto fechado · **04/11** envio |

---

### Semana 1 (07 a 13/out)

**Checklist**

- [ ] PDF parcial: introdução + revisão da literatura  
- [ ] Subseção **perguntas de pesquisa** no texto da dissertação  
- [ ] Lacuna, objetivos e hipótese alinhados ao orientador  
- [ ] Roteiro de anotação (1–2 páginas) — ver [annotation_protocol_v2.md](annotation_protocol_v2.md)  
- [ ] Arquivo `data/water_utilities_corpus/rotulos_manual_100_v2.csv` criado  
- [ ] **25 a 35** notícias revisadas com protocolo v2  
- [ ] **Rafael** contatado (registrar abaixo)  
- [ ] Itens acima refletidos em “Entrega realizada”

#### Semana 1 — entrega realizada (preencher ao fim de 13/out)

- Data envio ao orientador:  
- O que foi entregue:  
- Rafael (data do contato / combinado):  
- Pendências para semana 2:  

---

### Semana 2 (14 a 20/out)

**Checklist**

- [ ] Rascunho da **metodologia** + descrição do **setup experimental**  
- [ ] **~80** notícias revisadas na planilha v2  
- [ ] **Piloto LLM-juiz:** prompt documentado + 10–20 `news_id` com saída salva (ver protocolo §7)  
- [ ] Se Rafael confirmar: **~30** notícias com segunda anotação humana  
- [ ] Parágrafo no texto sobre limitação do anotador + mitigações (IAA / LLM)  
- [ ] Entrega realizada preenchida  

#### Semana 2 — entrega realizada (preencher ao fim de 20/out)

- Data envio ao orientador:  
- O que foi entregue:  
- Piloto LLM (quantas notícias / onde salvou o CSV):  
- Pendências para semana 3:  

---

### Semana 3 (21 a 27/out)

**Checklist**

- [ ] Capítulo (ou seção) de **andamentos** com tom honesto (pipeline ok; κ como diagnóstico)  
- [ ] **Próximos passos** pós-qualificação  
- [ ] **PDF intermediário** completo enviado ao orientador  
- [ ] Checkboxes do plano mestre espelhados no [plano](qualification_plan_2026-11-04.md) (status rápido)  
- [ ] Entrega realizada preenchida  

#### Semana 3 — entrega realizada (preencher ao fim de 27/out)

- Data envio ao orientador:  
- O que foi entregue:  
- Pendências para semana 4:  

---

### Semana 4 (28/out a 04/nov)

**Checklist**

- [ ] Revisão integral do PDF  
- [ ] Resumo e folha de rosto  
- [ ] Correções pedidas pelo orientador incorporadas  
- [ ] **02/11:** congelamento de conteúdo  
- [ ] **04/11:** envio formal  
- [ ] Entrega realizada preenchida  

#### Semana 4 — entrega realizada (preencher em 04/nov)

- Data envio à banca:  
- Versão final (observações):  

---

## 5. Documentação no repositório (`docs/`)

Marcos do enriquecimento técnico (pilares A–G). Detalhe: [docs/README.md](../README.md) · guia dev/agente: [13_guia_leitura_dev_e_agente.md](../documentation/13_guia_leitura_dev_e_agente.md).

| Pilar | Conteúdo | Concluído |
| --- | --- | --- |
| A | Navegação, `10_`/`13_`, decision-register | [x] |
| B | Corpus, scrapers, datasets (`03`/`06`/`11`) | [x] |
| C | ITI, fórmulas, outputs (`04`/`12`/appendix) | [x] |
| D | Research semanal, protocolo (`05`/`12`, part-02/04) | [x] |
| E | Evaluation, κ, LLM-judge (`03` §3.7, annotation §7) | [x] |
| F | Campanhas, dashboard, testes (`02`/`07`/`08`/`09`) | [x] |
| G | Referências ↔ fases, glossário, links | [x] |

Atualizar esta tabela só quando um pilar mudar de escopo (não semanalmente).

---

## 6. Depois da qualificação

Nos dois meses seguintes (se a mensuração evoluir):

1. Consolidar amostra anotada e concordância entre anotadores (quando houver par).  
2. Fixar classificação por empresa (humano + programa + eventual LLM-juiz como apoio).  
3. Regerar índice e repetir comparações no caso Sabesp.  
4. Discutir resultados com mais firmeza; depois, ampliar para outras empresas do setor.

---

*Última atualização estrutural do cronograma: 06/10/2026 (seção documentação).*
