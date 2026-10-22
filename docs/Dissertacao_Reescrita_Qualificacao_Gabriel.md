# Reescrita da dissertação para qualificação — Gabriel Felipe Souza Santos

**Documento de trabalho para revisão autoral e implementação no LaTeX.**

**Fonte principal:** `ufsj-abntex2(5).pdf`, 30 páginas físicas, com numeração impressa até 29. A auditoria usa a numeração impressa quando existente. Consulta bibliográfica realizada em 21–22 de outubro de 2026; data editorial: 21 de outubro de 2026, horário de Brasília.

Este arquivo contém a reescrita integral do conteúdo acadêmico disponível, uma auditoria crítica e as instruções de implementação. Não é uma dissertação final validada: os resultados foram transcritos do PDF, sem acesso às planilhas, aos scripts, ao repositório LaTeX ou aos relatórios completos de execução. As correções de escrita e bibliografia não equivalem a uma nova execução experimental.

**Organização deste arquivo:**

- **Parte I:** auditoria do original e justificativa da reorganização; não inserir na dissertação.
- **Parte II:** texto acadêmico reescrito, dos elementos pré-textuais às considerações finais e aos apêndices.
- **Parte III:** referências e situação da verificação bibliográfica.
- **Parte IV:** instruções para o Cursor e pendências que dependem dos dados ou do autor; não inserir como capítulo.

Os comentários `<!-- CONFIRMAR ... -->` são pendências editoriais. Devem ser convertidos em comentários LaTeX e registrados em um arquivo de pendências, nunca apagados apenas para fazer o documento parecer concluído. As citações da Parte II usam autor e ano; a Parte III fornece chaves sugeridas para o arquivo `.bib`.

---

# PARTE I — AUDITORIA CRÍTICA DO ORIGINAL

## 1. Diagnóstico geral

A pesquisa tem uma questão pertinente: como transformar notícias em português sobre uma empresa de saneamento em uma medida temporal verificável, e como avaliar se a memória dessa medida acrescenta algo às agregações mais simples? O original já contém componentes úteis: uma aplicação delimitada à Sabesp, alternativas de comparação, anotação manual, resultados negativos do classificador e uma tentativa de preservar a sequência temporal na avaliação financeira.

O principal problema da versão recebida é a distância entre a extensão das afirmações e a especificação efetiva do estudo. O texto anuncia um índice informacional setorial, menciona retorno, volatilidade, volume, choques e informação incremental, mas apresenta principalmente um caso empresarial, um classificador com baixa concordância com o autor e comparações de correlações em uma janela curta. Isso não impede uma qualificação consistente. Exige definir uma contribuição proporcional ao estágio da pesquisa e explicar precisamente o que ainda será avaliado.

A revisão também precisa ir além de trocar palavras. O original repete muitas vezes que a hipótese está aberta e que o ITI não é um índice estrangeiro copiado. Essas ressalvas ocupam espaço que poderia ser usado para explicar a amostragem, a agregação diária, a política temporal, as métricas e os resultados. Uma limitação bem definida em seu lugar apropriado é mais convincente do que a repetição de advertências ao longo de todos os capítulos.

A proposta desta reescrita é manter o nome ITI, explicando que se trata de uma **medida textual operacional**, e apresentar a Sabesp como estudo de caso inicial. A ampliação para outras empresas permanece no plano de continuidade. A hipótese principal passa a ter formulação compatível com a comparação efetivamente descrita; uma avaliação de informação incremental condicionada a outros indicadores é apresentada como etapa posterior.

## 2. Dissertações do PPGCC/UFSJ consultadas

Foram consultados os registros institucionais, os sumários e trechos de introdução e organização dos seguintes trabalhos. A consulta foi direcionada à estrutura e à escrita, não uma revisão integral de todos os resultados desses autores. Não se trata de uma amostra representativa do programa nem de uma regra institucional obrigatória.

| Trabalho | Trechos utilizados na comparação | Decisão editorial aplicada |
|---|---|---|
| Rodrigo Ribeiro Caputo, *Deep learning aplicado a dados estruturados como cubos OLAP* (2020) | Sumário, pp. 11–12 do PDF; introdução e objetivos, pp. 13–15 | Separar conceitos, trabalhos relacionados, proposta e experimentos; explicitar a contribuição computacional. |
| Ygor Henrique de Paula Barros Baêta, *Recuperação de erros em derivação de gramáticas livres de contexto aplicado à correção de erros ortográficos e gramaticais* (2021) | Sumário, pp. 12–13 do PDF; organização da introdução e do método | Usar títulos informativos e reservar resultados e considerações finais para capítulos próprios. |
| Rafael José de Alencar Almeida, *Suporte à análise interativa de discussões online combinando técnicas de mineração de dados* (2020) | Sumário, pp. 20–21 do PDF; início da introdução, p. 22 do PDF | Explicar o problema antes da ferramenta e separar descrição do artefato de sua avaliação. |

Fontes institucionais:

- Caputo: https://repositorio.ufsj.edu.br/items/4775a814-ece3-44a4-8fd9-0bb89da34575
- Baêta: https://repositorio.ufsj.edu.br/items/c1a85d75-9097-4f27-87c4-7b1a68405ff0
- Almeida: https://repositorio.ufsj.edu.br/items/deab6946-4515-4dd8-8542-570b95697ae6

A estrutura adotada é: **Introdução; Fundamentação teórica; Trabalhos relacionados; Metodologia; Resultados preliminares e discussão; Considerações finais e plano de continuidade**. O capítulo isolado “Proposta do índice” foi incorporado à metodologia, eliminando a repetição entre a apresentação conceitual e o procedimento operacional. A separação entre fundamentação e trabalhos relacionados ajuda o leitor a distinguir a explicação de conceitos da comparação entre pesquisas.

Não foram copiados parágrafos, exemplos ou particularidades da voz de outro aluno. Também não foram reproduzidas imprecisões encontradas nos textos de referência. “Mais humano”, aqui, significa uma argumentação situada na pesquisa, com escolhas justificadas, frases claras e resultados discutidos sem dramatização.

## 3. Problemas científicos e editoriais encontrados

| Local do original | Problema | Encaminhamento na reescrita |
|---|---|---|
| Folhas iniciais | Documento de qualificação apresentado como versão para obtenção do título; folha de aprovação com campos provisórios | Sugerir texto de qualificação e manter adequação formal dependente do modelo adotado pelo programa. |
| Resumo e pp. 9–16 | Afirmação absoluta de inexistência de índice para saneamento, sem busca sistemática documentada | Delimitar a lacuna ao conjunto de trabalhos revisados. |
| pp. 8–18 | Tom de conversa em expressões como “não é decoração”, “régua clara”, “o gesto metodológico”, “no setor certo” | Substituir por descrições do problema, das escolhas e das evidências. |
| pp. 10–12 | Objetivo geral centrado em “fundamentar”, enquanto há implementação; H1 repetida | Formular objetivo de desenvolver e avaliar; apresentar hipótese uma vez. |
| p. 11 | QP1 inclui volatilidade e volume, mas o protocolo e as tabelas usam retorno | Retorno como desfecho principal; demais dimensões como extensões. |
| pp. 14 e 20–24 | Classificação de sentimento global comparada a rótulos orientados à empresa | Explicitar possível divergência entre tarefas, além de mudança de domínio. |
| pp. 17–20 | Uso de “impacto” como se o escore medisse efeito econômico observado | Definir o escore como saída textual; reservar impacto econômico para evidência específica. |
| p. 19 | `impacto_t` e `alpha_eff` não definidos integralmente | Representar a agregação por função explícita a recuperar do código; não inventar ponderações históricas. |
| pp. 19–22 | Faltam fontes do corpus, critérios exatos de coleta e exclusão, horário de corte e tratamento de dias sem pregão | Incluir especificação necessária e pendências rastreáveis. |
| p. 20 | B1, B2 e B3 podem se tornar redundantes, dependendo da fórmula do impacto e da agregação semanal | Exigir fórmulas efetivas e verificar equivalência. |
| p. 20 | “Correlaciona melhor” não define sinal, módulo ou diferença testada | Separar descrição histórica da proposta de critério formal para a próxima avaliação. |
| p. 20 | Comparação de correlações chamada de informação incremental | Explicar que ganho condicionado requer modelo conjunto ou avaliação fora da amostra. |
| p. 20 | Limiar de 70% ou kappa 0,40 atribuído indiretamente à literatura clássica | Identificar os valores como escolha operacional do projeto, não regra universal. |
| pp. 20–22 | Amostragem estratificada pela previsão do modelo sem pesos e tamanhos dos estratos | Distinguir desempenho na amostra de estimativa de desempenho no corpus. |
| p. 21 | Humanos leem título e corpo; modelo pode truncar. Igualdade de entrada é afirmada em excesso | Diferenciar texto de origem compartilhado e conteúdo efetivamente processado. |
| pp. 21, 24 e 26 | Três especialistas aparecem ora como execução, ora como plano; não há consenso concluído | Preservar resultados como comparação com anotação do mestrando. |
| pp. 22, 24 e 26 | Protocolo 2026-10-07 versus 2026-10-19 | Manter versões distintas e pedir relação documentada entre elas. |
| pp. 23–25 | IDs de jobs e diretórios interrompem a discussão científica | Mover detalhes operacionais para apêndice de rastreabilidade. |
| p. 24 | Desempenho menor em textos multiempresa tratado como explicação causal do erro | Tratar como indício e hipótese de diagnóstico. |
| p. 25 | “Cai para cerca de 33%” após taxa de 25% | Remover a comparação direcional; não inferir qual execução é referência. |
| p. 25 | Ausência de significância tratada como “robustez negativa” | Descrever falta de evidência de superioridade; não concluir equivalência ou ausência de relação. |
| pp. 23–25 | Reexecução em HPC chamada de confirmação de reprodutibilidade sem versões e tolerâncias | Registrar execução em dois ambientes, com verificação quantitativa ainda a documentar. |
| Texto completo | Ausência de encerramento que relacione objetivos, resultados e próximos passos | Acrescentar capítulo de considerações finais e plano de continuidade. |

## 4. Pontos de maior risco para a qualificação

**Coerência do construto.** A pergunta humana é “o fato é favorável ou desfavorável para a Sabesp?”. Um classificador de sentimento financeiro aplicado ao documento inteiro pode responder algo próximo de “qual é o tom financeiro dominante?”. São perguntas relacionadas, mas diferentes. Notícias com várias empresas tornam a divergência mais visível. Melhorar a amostra de referência e verificar a capacidade de classificação por entidade são prioridades anteriores à interpretação financeira do ITI.

**Definição incompleta da medida.** Uma equação de EWMA não define sozinha o índice. São necessários a função de agregação diária, os pesos, o tratamento de ausências, a inicialização, o calendário e a transformação de alfa em alfa efetivo. Sem isso, outro pesquisador não consegue reconstruir a série.

**Valor incremental.** Uma correlação maior do ITI com retorno não demonstra, isoladamente, informação adicional aos baselines. Como o ITI é construído a partir das mesmas notícias, ele pode apenas reexpressar um sinal já presente. Essa é uma diferença conceitual central para a defesa.

**Tamanho da série.** Cerca de 465 artigos não significam 465 observações financeiras independentes. Na comparação semanal de novembro de 2023 a abril de 2024, a quantidade de observações é da ordem de poucas dezenas, antes das perdas de horizonte e de dados ausentes. Retornos futuros de duas e quatro semanas se sobrepõem; as 24 comparações também compartilham dados. Não cabe interpretar seis resultados favoráveis como seis confirmações independentes.

**Referências.** Há erros verificáveis e registros incompletos. A revisão bibliográfica deve apoiar afirmações específicas; citar um trabalho de sentimento financeiro não o transforma em referência sobre bootstrap, causalidade ou testes múltiplos. A Parte III separa os registros corrigidos dos que ainda exigem conferência.

---

# PARTE II — TEXTO ACADÊMICO REESCRITO

<!-- INICIO_TEXTO_ACADEMICO -->

# Elementos pré-textuais

## Identificação

**Universidade Federal de São João del-Rei**  
**Programa de Pós-Graduação em Ciência da Computação**  
**Gabriel Felipe Souza Santos**

**Índice temporal informacional a partir de notícias corporativas: uma proposta para empresas brasileiras de saneamento**

Orientador: Michel Carlo Rodrigues Leles.

São João del-Rei — 2026.

### Texto proposto para a folha de rosto

Texto apresentado ao Programa de Pós-Graduação em Ciência da Computação da Universidade Federal de São João del-Rei, para exame de qualificação do Mestrado em Ciência da Computação.

<!-- CONFIRMAR P01: adequar a natureza do trabalho ao modelo efetivamente exigido pelo PPGCC e pelo orientador. Não inventar banca, data, aprovação, área de concentração ou financiamento. -->

## Agradecimentos

Agradeço ao professor Michel Carlo Rodrigues Leles pela orientação e pelo acompanhamento da pesquisa, e à Universidade Federal de São João del-Rei pelas condições oferecidas para o desenvolvimento deste trabalho.

Agradeço a Raphael Veloso pela disponibilidade para colaborar com a avaliação das notícias sob a perspectiva econômico-financeira.

<!-- CONFIRMAR P02: atualizar a descrição da colaboração de acordo com o que foi efetivamente concluído. O PDF informa que a anotação especializada ainda estava em andamento. -->

## Resumo

A análise de notícias financeiras permite organizar informações textuais sobre empresas e investigar sua relação com o mercado acionário. Entretanto, a construção de uma medida temporal a partir desses textos depende da identificação da empresa mencionada, da qualidade da classificação e do alinhamento entre a publicação das notícias e os dados de mercado. Este trabalho propõe um Índice Temporal Informacional (ITI) para notícias corporativas em português, com aplicação inicial à Sabesp e perspectiva de extensão a outras empresas brasileiras de saneamento. O método compreende a organização de um corpus de notícias, a obtenção de escores de sentimento financeiro, a agregação diária desses escores e a incorporação de memória por média móvel exponencial. A avaliação é organizada em duas etapas: comparação das classificações com anotação humana orientada à empresa-alvo e comparação do índice com medidas simples derivadas do mesmo corpus, considerando retornos futuros em horizontes de uma, duas e quatro semanas. Nos resultados preliminares, o classificador financeiro em português apresentou acurácia de 50% e kappa de aproximadamente 0,20 em uma amostra de cem notícias anotadas pelo autor. Na configuração temporal R1, seis das 24 comparações favoreceram o ITI, sem diferenças estatisticamente significativas segundo o procedimento de reamostragem reportado. Esses resultados permitem identificar limitações da classificação e do protocolo de avaliação, mas não demonstram superioridade do índice. A continuidade da pesquisa compreende a consolidação da referência humana, a análise dos erros por tipo de notícia e a avaliação temporal com maior controle das escolhas experimentais.

**Palavras-chave:** análise de sentimentos; notícias financeiras; séries temporais; processamento de linguagem natural; saneamento.

## Abstract

Financial news analysis provides a way to organize textual information about companies and investigate its relationship with stock market behavior. However, constructing a time series from news requires identifying the target company, assessing classification quality, and aligning publication times with market data. This work proposes an Informational Temporal Index (ITI) for corporate news written in Portuguese, with an initial application to Sabesp and potential extension to other Brazilian sanitation companies. The method includes building a news corpus, obtaining financial sentiment scores, aggregating these scores daily, and introducing temporal memory through an exponentially weighted moving average. Evaluation comprises two stages: comparing model predictions with target-oriented human annotations and comparing the index with simpler measures derived from the same corpus, considering future returns over one-, two-, and four-week horizons. Preliminary results show an accuracy of 50% and a kappa of approximately 0.20 for the Portuguese financial sentiment classifier on a sample of 100 news articles annotated by the author. In temporal configuration R1, six of the 24 comparisons favored the ITI, with no statistically significant differences under the reported resampling procedure. These findings identify limitations in classification and experimental evaluation but do not establish the index's superiority. Further work includes consolidating the human reference annotations, analyzing errors by news type, and conducting temporal evaluation with tighter control over experimental choices.

**Keywords:** sentiment analysis; financial news; time series; natural language processing; sanitation.

## Siglas utilizadas

| Sigla | Significado |
|---|---|
| BERT | Bidirectional Encoder Representations from Transformers |
| EWMA | Exponentially Weighted Moving Average — média móvel exponencialmente ponderada |
| ITI | Índice Temporal Informacional |
| PLN | Processamento de Linguagem Natural |
| SBSP3 | Código de negociação da ação utilizado no estudo de caso da Sabesp |
| GPU | Graphics Processing Unit — unidade de processamento gráfico |
| HPC | High-Performance Computing — computação de alto desempenho |

# 1 Introdução

Notícias sobre empresas reúnem informações de naturezas distintas, como divulgação de resultados, decisões regulatórias, investimentos e mudanças de controle societário. A análise desse material pode ajudar a caracterizar a cobertura de uma companhia e a investigar sua relação com o comportamento do mercado. Entretanto, transformar um conjunto de notícias em uma medida quantitativa exige definir quais textos pertencem ao estudo, que informação será extraída deles e como essa informação será organizada no tempo.

A literatura apresenta diferentes formas de aproximar texto e dados econômicos. Tetlock (2007) investiga a relação entre o conteúdo da imprensa e o mercado acionário. Baker, Bloom e Davis (2016) constroem uma medida de incerteza de política econômica a partir da cobertura jornalística. Esses trabalhos mostram que o texto pode ser tratado como fonte de dados, mas também que a interpretação de um índice depende do fenômeno que ele foi construído para representar.

Nesta pesquisa, o interesse está nas notícias corporativas em português sobre empresas brasileiras de saneamento. O setor reúne questões operacionais, financeiras e regulatórias que podem aparecer simultaneamente em uma mesma matéria. Uma notícia sobre alteração tarifária, por exemplo, pode discutir seus efeitos para a empresa, para os usuários e para a administração pública. A interpretação relevante para cada um desses agentes não é necessariamente a mesma.

Propõe-se um Índice Temporal Informacional (ITI), calculado por empresa a partir de escores textuais agregados ao longo do tempo. A aplicação inicial utiliza notícias sobre a Sabesp. O termo “informacional” identifica a origem textual da medida; não significa que o índice já quantifique informação nova incorporada aos preços. Essa interpretação depende da avaliação empírica.

## 1.1 Contexto e delimitação

O desenvolvimento de modelos de linguagem em português ampliou as possibilidades de análise automática de textos. No domínio financeiro, Santos, Bianchi e Costa (2023) apresentam modelos adaptados ao vocabulário do mercado brasileiro. A disponibilidade dessas ferramentas permite estudar a classificação de notícias sem iniciar o treinamento de um modelo de linguagem a partir do zero. Sua aplicação a um recorte específico, contudo, exige avaliação própria.

O saneamento constitui o domínio desta pesquisa por reunir empresas com cobertura jornalística e acontecimentos regulatórios relevantes. A Lei nº 14.026/2020 atualizou o marco legal do saneamento e alterou dispositivos relacionados à regulação e à prestação dos serviços (Brasil, 2020). Esse contexto motiva a organização de um corpus setorial, mas não determina antecipadamente como as notícias se relacionam com os retornos das ações.

O estudo de caso concentra-se na Sabesp. O corpus descrito nos experimentos inclui uma janela de novembro de 2023 a abril de 2024, além de uma análise exploratória em período ampliado, de maio de 2022 a abril de 2024. Essas janelas são tratadas como recortes de observação. Sua interpretação como janela de um evento específico depende da identificação do acontecimento, de sua data e dos critérios usados para selecionar o intervalo.

Copasa e Sanepar integram a perspectiva de ampliação do estudo, mas não compõem os resultados apresentados nesta qualificação. Da mesma forma, o retorno acionário é o desfecho principal da avaliação descrita. Análises de volatilidade, volume e assimetria entre notícias positivas e negativas constituem possíveis extensões.

## 1.2 Problema de pesquisa

A construção do ITI envolve três dificuldades principais. A primeira é identificar a informação referente à empresa-alvo. Notícias sobre o mercado podem mencionar a Sabesp sem apresentar um fato relevante para a companhia, ou podem reunir acontecimentos favoráveis e desfavoráveis para empresas diferentes. A presença do nome da empresa, portanto, não basta para definir a pertinência do texto.

A segunda dificuldade está na classificação. Um modelo treinado para reconhecer sentimento financeiro não necessariamente avalia o efeito de um fato para uma empresa específica. Mesmo quando a linguagem é financeira, o gênero da notícia, seu tamanho e a presença de múltiplas entidades podem alterar o desempenho. A avaliação humana precisa considerar a mesma tarefa que se pretende atribuir ao modelo.

A terceira dificuldade é temporal. Notícias são publicadas em horários distintos, podem permanecer relevantes por mais de um dia e não aparecem com frequência uniforme. Ao mesmo tempo, preços e retornos seguem o calendário de negociação. A combinação dessas fontes requer regras explícitas para evitar que uma informação publicada depois do instante de referência seja usada para explicar um retorno que já estava em formação.

Diante dessas dificuldades, formula-se a questão principal:

> Em que condições um índice construído a partir de notícias corporativas em português, com agregação temporal e memória, apresenta associação com retornos futuros superior à de medidas mais simples obtidas das mesmas notícias, no estudo de caso da Sabesp?

Duas questões auxiliares orientam a avaliação: em que medida o classificador concorda com a anotação humana orientada à empresa-alvo e como a inclusão de memória altera o comportamento da medida em relação à agregação sem memória.

## 1.3 Objetivos

O objetivo geral é desenvolver e avaliar um índice temporal baseado em notícias corporativas em português para empresas brasileiras de saneamento, utilizando a Sabesp como estudo de caso inicial.

Os objetivos específicos são:

1. Organizar um corpus de notícias com identificação da empresa, origem, data de publicação e conteúdo textual, acompanhado de critérios de inclusão, exclusão e deduplicação.
2. Avaliar a adequação de um classificador de sentimento financeiro em português à tarefa de identificar a polaridade da informação referente à empresa-alvo.
3. Definir e implementar a agregação dos escores textuais em uma série temporal, tornando explícita a contribuição da memória.
4. Comparar o ITI com medidas simples de frequência e sentimento calculadas a partir do mesmo corpus.
5. Investigar a associação dessas medidas com retornos futuros em diferentes horizontes, respeitando a ordem temporal e as limitações da amostra.
6. Documentar os dados, as configurações e as execuções necessárias à reprodução dos resultados.

## 1.4 Justificativa e contribuição esperada

A contribuição computacional do trabalho está na integração entre organização de dados textuais, classificação de linguagem natural, representação temporal e avaliação experimental. A proposta não se limita a aplicar um classificador pronto: busca verificar se a saída desse classificador é adequada à tarefa e se sua agregação produz uma medida útil para a análise pretendida.

No conjunto de trabalhos revisados, há índices textuais agregados, modelos financeiros para o português e estudos que relacionam notícias ao mercado brasileiro. A combinação desses componentes no recorte empresarial do saneamento ainda requer investigação. Essa delimitação sustenta a proposta sem pressupor que todos os estudos sobre o tema tenham sido identificados.

Espera-se contribuir com um procedimento documentado de construção do índice, uma avaliação dos limites da classificação por empresa e uma comparação temporal com alternativas simples. A utilidade desses resultados não depende de confirmar uma relação positiva com os retornos. A identificação de erros de classificação, de redundância entre indicadores ou de ausência de superioridade também ajuda a delimitar o alcance do método.

## 1.5 Hipótese e organização do trabalho

A hipótese principal é que a incorporação de memória aos escores textuais permite obter, em condições de avaliação previamente definidas, associação com retornos futuros de maior magnitude que a das medidas sem essa memória. Não se pressupõe o sinal da associação. Uma notícia classificada como positiva não implica necessariamente retorno posterior positivo, pois o preço pode refletir expectativas anteriores e outros fatores.

A hipótese é avaliada em duas etapas complementares: qualidade da representação textual e relação temporal com o mercado. A primeira verifica a adequação da classificação; a segunda examina o comportamento das séries. Evidência favorável em uma etapa não substitui a outra.

O Capítulo 2 apresenta os conceitos necessários à pesquisa. O Capítulo 3 discute os trabalhos relacionados e situa a proposta. O Capítulo 4 descreve o método e o protocolo de avaliação. O Capítulo 5 apresenta os resultados preliminares e suas limitações. O Capítulo 6 sintetiza as contribuições desta etapa e organiza a continuidade da pesquisa. Os apêndices detalham a anotação e a rastreabilidade experimental.

<!-- CONFIRMAR P03: a formulação por magnitude é proposta para a próxima avaliação. As contagens históricas de comparações favoráveis só podem ser interpretadas segundo a regra realmente implementada. Não recalcular ou renomear resultados sem consultar os scripts. -->

# 2 Fundamentação teórica

## 2.1 Sentimento financeiro e empresa-alvo

A análise de sentimentos atribui uma orientação a um texto ou a uma parte dele. No contexto desta pesquisa, são consideradas as classes positiva, negativa e neutra. O significado dessas classes depende do alvo da análise. Uma classificação do documento inteiro resume seu conteúdo dominante; uma classificação orientada à empresa procura identificar a polaridade da informação relativa à companhia indicada.

Essa distinção é relevante em notícias financeiras. Considere, como exemplo hipotético, uma matéria que relate aumento das despesas da empresa A e expansão das receitas da empresa B. Um único rótulo para a matéria não representa adequadamente as duas empresas. A unidade de análise precisa incluir o vínculo entre o texto e a entidade a que o rótulo se refere. Tarefas orientadas a empresas e ativos aparecem em Cortis et al. (2017), Yuan et al. (2020) e Sinha et al. (2022).

Neste trabalho, o rótulo humano expressa se o fato descrito é favorável, desfavorável ou neutro para a Sabesp, conforme as informações disponíveis no próprio texto. Esse julgamento não é uma previsão da ação. Também não utiliza o retorno posterior como evidência para escolher a classe.

É necessário distinguir neutralidade de falta de informação. Uma notícia pode ser neutra por não apresentar direcionamento identificável para a empresa; outra pode ser impossível de avaliar porque o conteúdo está incompleto. Reunir essas situações em uma única classe esconderia problemas de extração ou de pertinência do corpus. Por isso, o protocolo de continuidade prevê campos separados para a classe, a possibilidade de avaliação e a ambiguidade.

## 2.2 Modelos de linguagem e adaptação ao domínio

BERT é uma arquitetura de representação da linguagem que utiliza o contexto à esquerda e à direita dos termos durante o pré-treinamento e pode ser adaptada a tarefas supervisionadas, como classificação de textos (Devlin et al., 2019). Na classificação de sentimentos, uma camada de saída produz escores para as classes consideradas. O aprendizado linguístico prévio reduz a necessidade de construir manualmente todas as características textuais.

O BERTimbau disponibiliza modelos pré-treinados para o português brasileiro (Souza, Nogueira e Lotufo, 2020). Um modelo desse tipo fornece representações da linguagem, mas não deve ser confundido com um classificador de sentimentos já ajustado. Para realizar a tarefa, é necessário especificar a etapa supervisionada ou utilizar um checkpoint que já contenha a cabeça de classificação correspondente.

A adaptação ao domínio financeiro responde a diferenças de vocabulário e de uso das palavras. Loughran e McDonald (2011) demonstram problemas na aplicação de listas de palavras de uso geral a documentos financeiros. Araci (2019) investiga a adaptação de BERT à análise de sentimento financeiro em inglês. Essas contribuições justificam a atenção ao domínio, sem estabelecer que qualquer modelo financeiro seja adequado a qualquer gênero de notícia.

Na aplicação desta pesquisa, a adequação linguística, financeira e empresarial precisa ser examinada separadamente. Um modelo pode compreender português e vocabulário financeiro, mas ainda apresentar dificuldade quando a matéria contém vários alvos ou quando o julgamento esperado exige distinguir consequências favoráveis e desfavoráveis para uma companhia específica.

## 2.3 Escores probabilísticos

Seja uma notícia associada a uma empresa. O classificador retorna três probabilidades, representadas por \(p^{+}\), \(p^{-}\) e \(p^{0}\), correspondentes às classes positiva, negativa e neutra. Em uma saída normalizada, a soma é igual a um. O escore utilizado no projeto é definido pela diferença

\[
d = p^{+} - p^{-}.
\]

O valor de \(d\) pertence ao intervalo \([-1,1]\). Valores próximos de um indicam predominância da classe positiva; valores próximos de menos um indicam predominância da classe negativa. A classe neutra participa da distribuição de probabilidades e não é excluída do cálculo por renormalização.

Um escore próximo de zero não identifica uma única situação. Pode resultar de alta probabilidade de neutralidade ou de probabilidades semelhantes para as classes positiva e negativa. Por exemplo, as distribuições \((0{,}05;0{,}05;0{,}90)\) e \((0{,}45;0{,}45;0{,}10)\), na ordem positivo, negativo e neutro, produzem o mesmo escore zero, embora representem saídas distintas. Assim, as três probabilidades devem ser preservadas nos dados de inferência.

A maior probabilidade de saída também não deve ser interpretada automaticamente como probabilidade de acerto. Sua utilização como peso depende da calibração do classificador e da relação entre confiança e erro no corpus estudado. Uma ponderação pode amplificar previsões equivocadas se o modelo estiver excessivamente confiante.

## 2.4 Agregação temporal e memória

A classificação de uma notícia descreve uma observação textual. Para investigar relações ao longo do tempo, é necessário combinar observações em intervalos definidos. A contagem de matérias descreve a frequência da cobertura; a média dos escores resume sua orientação. Essas medidas têm interpretações diferentes e podem variar de forma independente.

A introdução de memória permite que observações anteriores continuem contribuindo para o estado do índice. Uma forma de representar esse comportamento é a média móvel exponencial:

\[
z_t = \alpha z_{t-1} + (1-\alpha)x_t, \qquad 0 \leq \alpha < 1,
\]

em que \(x_t\) é o valor agregado no instante atual e \(z_{t-1}\) é o estado anterior. Nesta convenção, valores maiores de \(\alpha\) preservam uma parcela maior do passado. O parâmetro deve ser interpretado em relação à unidade temporal utilizada.

A memória introduz uma escolha de modelagem: uma observação passada perde peso de forma gradual. Isso não demonstra que o mercado processe notícias segundo a mesma função. A pertinência dessa representação deve ser avaliada por comparação com uma versão sem memória e por análise de sensibilidade do parâmetro.

Também é preciso diferenciar ausência de notícia e ausência de coleta. No primeiro caso, o procedimento pode aplicar decaimento ao estado anterior. No segundo, a cobertura do corpus é desconhecida. Tratar uma falha de coleta como dia sem notícia produziria uma alteração artificial do índice.

## 2.5 Anotação humana e avaliação de classificação

A anotação humana define uma referência operacional para avaliar as previsões. Sua qualidade depende da clareza das instruções e da consistência entre participantes. A concordância não torna o rótulo uma verdade econômica absoluta, mas informa se o critério pode ser aplicado de maneira relativamente estável.

A acurácia corresponde à proporção de classificações corretas. Como pode ser influenciada pela classe mais frequente, deve ser acompanhada de métricas por classe e de uma matriz de confusão. O F1 combina precisão e revocação; sua média macro atribui o mesmo peso a cada classe, tornando visíveis dificuldades que poderiam ser ocultadas pela acurácia global.

O kappa de Cohen considera a concordância observada e aquela esperada a partir das distribuições marginais de duas classificações (Cohen, 1960):

\[
\kappa = \frac{p_o-p_e}{1-p_e}.
\]

A interpretação de \(\kappa\) depende da tarefa, das frequências das classes e do desenho da anotação. Não há, para esta pesquisa, um limiar universal que substitua a inspeção dos erros. Artstein e Poesio (2008) discutem as escolhas envolvidas na avaliação de concordância em tarefas linguísticas.

Quando há mais de dois anotadores, a medida deve corresponder ao esquema de participação. O kappa de Fleiss é uma possibilidade para avaliações nominais com desenho compatível (Fleiss, 1971). A concordância entre humanos será calculada antes da formação do consenso, para que a consolidação não apague a divergência original.

## 2.6 Associação temporal e interpretação dos resultados

A correlação de Pearson resume associação linear entre variáveis. A correlação de Spearman considera sua ordenação e permite examinar relações monotônicas. Nenhuma das duas demonstra, isoladamente, que uma variável cause a outra ou que forneça ganho preditivo fora da amostra.

Na pesquisa, o índice é observado antes do intervalo de retorno utilizado como desfecho. Essa separação temporal é necessária, mas insuficiente para demonstrar causalidade. Tanto as notícias quanto os preços podem responder a acontecimentos comuns. Além disso, notícias podem descrever movimentos de mercado já ocorridos.

Há ainda uma diferença entre comparar correlações e demonstrar informação incremental. Se o ITI e a média dos escores expressam componentes semelhantes da cobertura, o índice pode apresentar correlação maior sem acrescentar informação quando ambos entram em um mesmo modelo. A avaliação incremental exige verificar a contribuição do ITI condicionada às medidas de comparação, ou examinar o ganho em previsões realizadas em períodos não utilizados no ajuste.

# 3 Trabalhos relacionados

## 3.1 Notícias e indicadores econômicos

Tetlock (2007) analisa o conteúdo de uma coluna jornalística nos Estados Unidos e sua relação com o mercado acionário, utilizando uma medida textual de pessimismo. Sua contribuição para esta pesquisa está em tratar a linguagem da imprensa como variável observável, cuja relação com preços e volume pode ser investigada empiricamente. O estudo não determina a direção esperada para o ITI nem substitui a avaliação no mercado brasileiro.

Baker, Bloom e Davis (2016) propõem o índice de incerteza de política econômica a partir da frequência de cobertura jornalística relacionada ao tema. A medida é submetida a verificações e relacionada a variáveis econômicas. O aspecto relevante para o presente trabalho é a necessidade de definir o conteúdo representado pelo índice e de verificar sua validade com evidências externas. Incerteza econômica e polaridade de notícias corporativas, entretanto, são objetos distintos.

Shapiro, Sudhof e Wilson (2022) desenvolvem medidas temporais de sentimento a partir de notícias econômicas e financeiras e avaliam procedimentos textuais com referência humana. Na documentação do índice diário do Federal Reserve Bank of San Francisco, a suavização utiliza pesos que diminuem geometricamente com a antiguidade das notícias (Federal Reserve Bank of San Francisco, s.d.). Essa documentação oferece um antecedente para o uso de decaimento temporal; a recorrência, o calendário e os parâmetros do ITI são escolhas próprias do presente estudo.

Os trabalhos dessa linha sustentam a construção e a avaliação de medidas textuais temporais. Eles não permitem presumir que toda agregação de sentimento contenha informação adicional sobre retornos ou que a persistência observada em um índice macroeconômico seja adequada a uma empresa específica.

## 3.2 Modelos financeiros em português

Santos, Bianchi e Costa (2023) distinguem o FinBERT-PT-BR, adaptado à linguagem financeira, do SentFinBERT-PT-BR, ajustado para classificação de sentimentos. O artigo informa uma etapa de modelagem de linguagem com aproximadamente 1,4 milhão de sentenças e uma base final de 503 textos rotulados após filtragem. No teste reportado, o classificador de sentimentos alcança acurácia de 0,76 e F1 de 0,73.

Os autores também apresentam um índice baseado na diferença entre as contagens de textos positivos e negativos, dividida pela quantidade total de textos classificados, incluindo os neutros. Portanto, esse trabalho constitui antecedente tanto para a classificação em português quanto para a agregação de sentimento. A proposta aqui investigada se distingue pelo recorte empresarial, pela avaliação orientada à entidade e pelo uso explícito de memória sobre escores contínuos.

No restante desta dissertação, a expressão “classificador financeiro em português” designa o modelo utilizado nos experimentos. O identificador exato de seu checkpoint deverá acompanhar os registros de execução, pois o nome da família não identifica, por si só, os pesos, a configuração e o mapeamento das classes.

<!-- CONFIRMAR P04: conferir no código se foi utilizado o checkpoint supervisionado SentFinBERT-PT-BR, ou outra distribuição do modelo. Preservar as métricas históricas e não atribuí-las automaticamente a um checkpoint apenas com base no nome empregado no PDF. -->

## 3.3 Sentimento orientado a entidades financeiras

Cortis et al. (2017) apresentam uma tarefa de análise de sentimento financeiro em microtextos e notícias, com escores associados às empresas ou aos ativos mencionados. Esse desenho evidencia que a unidade de classificação pode ser o par texto–entidade, e não somente o documento.

Yuan et al. (2020) descrevem um corpus de notícias financeiras em chinês com anotação orientada a alvos. Empresas, marcas e outras entidades financeiras são consideradas na definição da polaridade. O estudo oferece uma referência para a necessidade de instruções de anotação que explicitem o alvo e os trechos que sustentam a decisão.

Sinha et al. (2022) apresentam o SEntFiN 1.0, conjunto de manchetes com anotações de sentimento por entidade, incluindo exemplos com múltiplas entidades e polaridades diferentes. A existência desses casos reforça a limitação de atribuir uma única polaridade a textos que descrevem empresas distintas.

Esses trabalhos motivam a avaliação da classificação orientada à Sabesp. As diferenças de idioma, gênero textual e extensão dos documentos impedem a transferência direta de seus resultados para o corpus desta pesquisa. A contribuição metodológica aproveitada é a explicitação do alvo, acompanhada da preservação dos julgamentos individuais e da análise dos desacordos.

## 3.4 Evidências no mercado brasileiro

Yoshinaga e Castro Junior (2012) investigam a relação entre um índice de sentimento de mercado e retornos futuros no Brasil. O índice é construído por análise de componentes principais a partir de variáveis de mercado, e o estudo reporta uma relação negativa com os retornos subsequentes. Trata-se de um objeto diferente do ITI, mas o resultado mostra por que não se deve impor uma correspondência automática entre sentimento positivo e retorno futuro positivo.

Duarte, Montenegro González e Cruz Junior (2021) estudam a previsão de quedas de preços com notícias em português. O trabalho aproxima dados textuais e resultados financeiros por meio de uma tarefa preditiva. Sua relação com esta pesquisa está na avaliação empírica do texto no mercado brasileiro; seu desenho não equivale à comparação entre um índice suavizado e medidas agregadas do mesmo corpus.

Brito et al. (2022) analisam a associação entre sentimento do investidor e ciclos de mercado, utilizando dados de empresas listadas e considerando períodos de crise. Os resultados reforçam a necessidade de distinguir recortes temporais. Na presente pesquisa, uma relação observada em uma janela de cobertura intensa precisa ser confrontada com outros períodos antes de ser generalizada.

A literatura brasileira, portanto, oferece evidências de associação e aplicações preditivas, mas com medidas, unidades e desenhos diferentes. As escolhas do ITI devem ser justificadas pelo problema desta pesquisa e avaliadas no conjunto de dados utilizado, sem apresentar resultados de outros estudos como garantia de desempenho.

## 3.5 Síntese e posicionamento da proposta

O Quadro 1 resume as principais aproximações e diferenças entre os trabalhos revisados e a proposta.

**Quadro 1 — Relação entre a literatura e o ITI.**

| Linha | Referências principais | Contribuição para a pesquisa | Diferença em relação ao ITI |
|---|---|---|---|
| Texto e mercado acionário | Tetlock (2007) | Avaliação quantitativa do conteúdo jornalístico | Outro mercado, corpus e método textual |
| Índices textuais | Baker, Bloom e Davis (2016); Shapiro, Sudhof e Wilson (2022) | Construção temporal e validação da medida | Objetos predominantemente agregados, distintos de uma empresa de saneamento |
| Sentimento financeiro em português | Santos, Bianchi e Costa (2023) | Modelos adaptados e agregação de classificações | Não dispensa validação empresarial e análise da memória proposta |
| Sentimento por entidade | Cortis et al. (2017); Yuan et al. (2020); Sinha et al. (2022) | Definição explícita do alvo da classificação | Outros idiomas, corpora e unidades textuais |
| Sentimento e mercado brasileiro | Yoshinaga e Castro Junior (2012); Duarte et al. (2021); Brito et al. (2022) | Referências para avaliação empírica no Brasil | Indicadores e tarefas distintos do estudo de caso |

Fonte: elaboração própria a partir dos trabalhos citados.

A lacuna delimitada nesta revisão é a avaliação integrada da classificação por empresa, da agregação temporal e da comparação com medidas simples no recorte de notícias sobre saneamento. A contribuição pretendida está no desenho e na avaliação dessa integração. A alegação de ineditismo absoluto exigiria uma busca bibliográfica mais abrangente e documentada, que não integra os resultados desta etapa.

# 4 Metodologia

## 4.1 Desenho da pesquisa

A pesquisa é experimental e quantitativa, com desenvolvimento de um procedimento computacional e aplicação inicial a um estudo de caso. O fluxo compreende organização do corpus, anotação humana, classificação automática, construção das séries e avaliação temporal.

Há duas unidades de análise. Na avaliação textual, a unidade é uma notícia associada à Sabesp. Na avaliação financeira, a unidade é uma semana com um indicador calculado até seu instante de referência e um retorno observado em período posterior. A passagem entre essas unidades ocorre pela agregação diária e pela extração do estado semanal do índice.

O procedimento separa as etapas já executadas das etapas de aperfeiçoamento. Os resultados disponíveis utilizam a anotação do autor e configurações exploratórias do índice. A consolidação por especialistas, a análise completa de erros e a avaliação temporal confirmatória permanecem no plano de continuidade.

**Figura 1 — Organização metodológica proposta.**

Descrição para implementação gráfica: representar o corpus como entrada comum de dois caminhos. No primeiro, a amostra segue para anotação humana e avaliação do classificador. No segundo, as probabilidades do classificador alimentam o escore e a agregação diária; dessa agregação derivam o ITI e sua versão sem memória. As medidas de referência são calculadas a partir do mesmo corpus. ITI e referências convergem para a avaliação semanal, que recebe os retornos futuros por uma entrada separada. Não desenhar B0–B3 como uma etapa posterior à EWMA.

Fonte: elaboração própria.

## 4.2 Corpus e critérios de seleção

O corpus de aplicação é formado por notícias corporativas em português vinculadas à Sabesp. Nos registros experimentais, o conjunto filtrado é denominado corpus estrito. Essa denominação identifica uma versão dos dados, mas não substitui a descrição dos critérios de seleção.

O registro de uma notícia deve permitir recuperar seu identificador, endereço de origem, veículo, título, corpo, data e, quando disponível, horário de publicação. Também devem ser preservados a data de coleta, a versão do texto processado e o vínculo com a empresa. Essas informações permitem distinguir atualização da página, republicação e ocorrência de notícias semelhantes em veículos diferentes.

A inclusão exige pertinência à empresa e conteúdo suficiente para a classificação. A simples ocorrência de “Sabesp” em listas, menus ou referências laterais não caracteriza uma notícia sobre a companhia. Textos incompletos e páginas sem data confiável precisam de tratamento próprio. As exclusões e seus motivos devem ser registradas, permitindo apresentar as quantidades antes e depois de cada filtro.

A deduplicação deve considerar tanto repetições exatas quanto republicações. Notícias diferentes sobre um mesmo acontecimento não são necessariamente duplicatas: podem acrescentar informações ou representar cobertura editorial independente. A regra adotada precisa preservar essa distinção. Também é necessário avaliar se uma ampla reprodução da mesma matéria está aumentando artificialmente seu peso na série.

O recorte experimental principal informado no material desta qualificação compreende aproximadamente 465 artigos entre novembro de 2023 e abril de 2024. O valor é aproximado porque o inventário definitivo do corpus e as contagens por etapa não foram incorporados à versão disponível. A análise ampliada utiliza o intervalo de maio de 2022 a abril de 2024.

<!-- CONFIRMAR P05: obter contagem exata, fontes, termos de busca, datas de coleta, critérios implementados, quantidades excluídas e cobertura por mês. As regras de registro acima são a especificação metodológica necessária, não evidência de que todos os campos já existam. -->

## 4.3 Anotação de referência

A amostra descrita no estudo contém cem notícias. Sua seleção foi estratificada segundo as classes previstas pelo classificador, com o objetivo de contemplar diferentes saídas automáticas. Esse desenho favorece a inspeção dos tipos de erro, mas não implica que as proporções da amostra reproduzam as do corpus.

Cada notícia recebe um rótulo de polaridade orientado à Sabesp e uma identificação de seu tipo. São distinguidas matérias focais, em que a empresa constitui o assunto principal; notícias multiempresa ou de agenda, em que diferentes companhias aparecem no mesmo texto; e menções tangenciais. Na amostra reportada, foram identificadas 74 matérias focais e 26 de agenda ou multiempresa.

A pergunta de anotação é: considerando apenas as informações da notícia, o fato relatado apresenta orientação favorável, desfavorável ou neutra para a Sabesp? O anotador deve registrar o trecho que fundamenta a decisão e indicar ambiguidades. O retorno posterior da ação não participa da definição do rótulo.

A avaliação preliminar utiliza a anotação realizada pelo autor. O desenho de continuidade prevê a participação independente de pelo menos três avaliadores com conhecimento econômico-financeiro. Um subconjunto comum de aproximadamente trinta notícias foi proposto para examinar concordância entre participantes. Caso apenas esse subconjunto receba avaliações múltiplas, a concordância e o consenso obtidos não serão atribuídos às cem notícias.

As anotações individuais serão preservadas antes da discussão dos casos. A referência consolidada poderá utilizar maioria entre os participantes, com adjudicação documentada quando houver empate ou desacordo não resolvido. O Apêndice A apresenta as instruções propostas para essa etapa.

As métricas da amostra estratificada devem ser interpretadas como desempenho no conjunto avaliado. Para estimar a acurácia no corpus, serão necessários o tamanho dos estratos e as probabilidades de inclusão, ou uma nova amostra representativa. O protocolo também deverá distinguir a amostra usada para aperfeiçoar as instruções daquela reservada à avaliação final.

<!-- CONFIRMAR P06: recuperar semente, lista de IDs, tamanhos dos estratos e contagens por classe humana. Verificar se as cem notícias da etapa exploratória são exatamente as mesmas da etapa reanotada. -->

## 4.4 Classificação automática e tratamento do texto

A entrada textual utilizada nos experimentos é a concatenação do título e do corpo da notícia, nessa ordem. A mesma fonte textual é disponibilizada aos anotadores. Contudo, isso não assegura igualdade entre o conteúdo lido pelo humano e o conteúdo processado pelo modelo.

O limite de entrada exige atenção a documentos longos. Na implementação descrita, utiliza-se um modelo da família BERT com limite de 512 tokens. Se a sequência exceder o limite, o truncamento pode remover trechos relevantes, inclusive a parte referente à Sabesp. O relatório de inferência precisa registrar o comprimento original, o comprimento processado, a política de truncamento e a quantidade de notícias afetadas.

A primeira comparação mede o desempenho do procedimento efetivamente usado, incluindo suas limitações de entrada. Em uma análise complementar, poderá ser oferecido aos anotadores o trecho efetivamente processado pelo modelo. Essa comparação ajuda a separar dificuldades de classificação da perda de conteúdo. Alternativas como seleção de sentenças relacionadas à empresa ou processamento por segmentos deverão ser avaliadas como novas configurações, com registros próprios.

Para cada notícia, serão preservadas as probabilidades das três classes, a classe escolhida e o escore contínuo. O mapeamento entre índices numéricos e rótulos precisa ser lido da configuração do checkpoint. A inversão entre positivo e negativo comprometeria toda a série, mesmo que a execução computacional terminasse sem erros.

O classificador será avaliado com matriz de confusão, acurácia, precisão, revocação e F1 por classe, F1 macro e kappa. Os resultados deverão ser comparados a uma classificação majoritária simples. O desempenho será examinado também por tipo de notícia e pela presença de truncamento.

O protocolo inicial estabeleceu, como referência operacional, acurácia da ordem de 70% ou kappa de pelo menos 0,40. Esses valores são escolhas do projeto e não critérios universais derivados de Cohen (1960). Na continuidade, a decisão de utilizar o modelo na interpretação substantiva do índice deverá considerar conjuntamente erros por classe, estabilidade da referência humana e incerteza das estimativas.

## 4.5 Construção do ITI

### 4.5.1 Escore por notícia

Seja \(\mathcal{N}_{c,t}\) o conjunto de notícias vinculadas à empresa \(c\) e atribuídas ao dia \(t\). Para cada notícia \(i\), define-se

\[
d_i = p_i^{+} - p_i^{-}.
\]

O escore expressa a diferença entre as saídas positiva e negativa do classificador. Não representa uma variação percentual de preço nem a probabilidade de que a ação suba.

### 4.5.2 Agregação diária

O valor diário é representado por

\[
x_{c,t}=g\left(\{d_i,\mathbf{p}_i:i\in\mathcal{N}_{c,t}\}\right),
\]

em que \(g\) é a regra de agregação e \(\mathbf{p}_i\) contém as probabilidades das classes. Essa representação explicita que a construção diária depende de uma escolha adicional à classificação. A função precisa ser recuperada da implementação utilizada em cada campanha para que os resultados históricos possam ser reproduzidos.

Como referência metodológica simples, uma opção é a média aritmética dos escores:

\[
\bar d_{c,t}=\frac{1}{n_{c,t}}\sum_{i\in\mathcal{N}_{c,t}}d_i,
\qquad n_{c,t}>0.
\]

Essa expressão é uma especificação candidata para comparação, e não a identificação retroativa da função usada nos experimentos R0 e R1. Se a implementação tiver pesos por confiança, relevância ou outro atributo, suas definições e normalizações deverão constar da descrição final.

### 4.5.3 Memória temporal

A atualização do índice segue a forma recorrente apresentada no projeto:

\[
ITI_{c,t}=\alpha_{\mathrm{eff},t}\,ITI_{c,t-1}
+\left(1-\alpha_{\mathrm{eff},t}\right)x_{c,t}.
\]

O parâmetro \(\alpha_{\mathrm{eff},t}\) controla a retenção do estado anterior. Na configuração R1, o parâmetro nominal reportado é \(\alpha=0{,}70\). A relação entre o parâmetro nominal e o efetivo precisa ser explicitada, especialmente se a atualização considerar intervalos variáveis ou propriedades das notícias.

Em uma grade diária regular com coeficiente constante, a notação pode ser simplificada para \(\alpha_{\mathrm{eff},t}=\alpha\). Se houver intervalos irregulares, uma alternativa é usar retenção \(\alpha^{\Delta_t}\), mas essa opção não será atribuída às execuções existentes sem verificação. Também precisam ser especificados o valor inicial e a eventual exclusão de um período de aquecimento.

Para dias sem notícias e com coleta confirmada, o projeto prevê decaimento do estado anterior. Em uma implementação com grade regular e entrada nula, a atualização fica

\[
ITI_{c,t}=\alpha\,ITI_{c,t-1}.
\]

O zero, nesse caso, representa ausência de nova entrada no procedimento. Não equivale a uma observação de notícia neutra. A quantidade de notícias e a disponibilidade da coleta devem permanecer registradas como variáveis auxiliares.

A escala final do índice depende de \(g\). Se a agregação diária for uma combinação convexa dos escores e o estado inicial pertencer a \([-1,1]\), a recorrência com pesos válidos preserva esse intervalo. Uma soma não normalizada não oferece a mesma propriedade. Portanto, não se atribui ao ITI um intervalo fixo sem definir a agregação.

<!-- CONFIRMAR P07: recuperar g, alfa efetivo, inicialização, calendário, regra de ausência, pesos e eventuais componentes positivos/negativos da implementação. As expressões candidatas não autorizam substituir a fórmula usada e manter as mesmas tabelas. -->

## 4.6 Medidas de comparação

As medidas de referência utilizam as mesmas notícias do índice. Essa restrição permite investigar o efeito da agregação e da memória sem confundi-lo com diferenças de cobertura.

**Quadro 2 — Medidas de referência do protocolo.**

| Código | Definição conceitual | Especificação necessária |
|---|---|---|
| B0 | Quantidade de notícias | Intervalo de contagem e regras de deduplicação |
| B1 | Média dos escores por notícia | Média de todas as notícias da semana ou média das médias diárias |
| B2 | Média ponderada dos escores | Definição da confiança, dos pesos e do denominador |
| B3 | Agregação diária sem memória | Mesma função diária do ITI e regra de representação semanal |

Fonte: elaboração própria.

Para uma semana \(w\), a contagem pode ser expressa por \(B0_{c,w}=|\mathcal{N}_{c,w}|\). A média por notícia, quando houver observações, é

\[
B1_{c,w}=\frac{1}{|\mathcal{N}_{c,w}|}
\sum_{i\in\mathcal{N}_{c,w}}d_i.
\]

Uma média ponderada assume a forma

\[
B2_{c,w}=\frac{\sum_{i\in\mathcal{N}_{c,w}}q_i d_i}
{\sum_{i\in\mathcal{N}_{c,w}}q_i},
\]

com pesos \(q_i\) não negativos e denominador positivo. A escolha de \(q_i\) deve ser identificada no código. Usar a maior probabilidade do classificador é uma opção possível, mas não pode ser apresentada como fato histórico sem essa conferência.

B3 deve permitir isolar a memória. Para isso, utiliza a mesma agregação diária do ITI, retirando apenas a recorrência temporal. Se outras transformações forem alteradas ao mesmo tempo, a comparação não identifica o efeito específico da memória.

Há risco de redundância entre B1, B2 e B3. Se a função diária for a média simples e a agregação semanal reproduzir a média por notícia, B1 e B3 poderão coincidir. O procedimento final deverá verificar essa possibilidade e evitar contar indicadores idênticos como evidências independentes. Semanas sem notícias exigem regra declarada: a média é indefinida, enquanto a contagem é zero. A imputação de zero para médias deve ser identificada como convenção e avaliada separadamente.

## 4.7 Alinhamento temporal e retornos

O preditor principal descrito no projeto é o estado do ITI no último dia útil da semana. Esse ponto de referência deve estar associado a um horário de corte. Notícias publicadas após esse horário não podem compor o indicador utilizado para o retorno que começa imediatamente naquele fechamento.

Quando a hora de publicação não estiver disponível, a análise deverá adotar uma regra conservadora e apresentar sua sensibilidade. Uma opção é atribuir a informação ao próximo pregão elegível. O tratamento de fins de semana e feriados precisa acompanhar o calendário de negociação, sem eliminar notícias apenas porque foram publicadas em dias sem mercado.

Seja \(P_{c,w}\) o preço de referência no encerramento da semana \(w\). Para \(h\in\{1,2,4\}\), o retorno logarítmico acumulado futuro é

\[
R^{(h)}_{c,w}=\log\left(\frac{P_{c,w+h}}{P_{c,w}}\right).
\]

A mesma quantidade pode ser obtida pela soma dos log-retornos diários do intervalo, desde que os preços e o calendário sejam consistentes. A fonte e a política de ajustes precisam ser documentadas: fechamento bruto, ajuste por desdobramento e ajuste por proventos não são intercambiáveis. A nomenclatura do retorno deve corresponder ao dado efetivamente utilizado.

ITI e medidas de referência serão comparados nas mesmas semanas válidas, para cada horizonte. As últimas semanas sem retorno futuro completo serão excluídas daquela avaliação. A quantidade efetiva de pares deve ser apresentada por horizonte, pois determina a informação estatística disponível.

<!-- CONFIRMAR P08: identificar provedor, campo de preço, ajustes, fuso, horário de corte, calendário, tratamento de publicação sem hora e número de semanas úteis. A política conservadora descrita é proposta para a continuidade se não estiver implementada. -->

## 4.8 Comparação estatística

O protocolo exploratório combina quatro referências, duas medidas de associação e três horizontes, totalizando 24 comparações por configuração. Pearson e Spearman são calculados para o ITI e para cada referência com o mesmo retorno futuro.

Para a próxima avaliação, propõe-se declarar previamente a estatística

\[
\Delta_{b,h,m}=
\left|\rho_m(ITI_w,R_w^{(h)})\right|
-\left|\rho_m(Bb_w,R_w^{(h)})\right|,
\]

em que \(b\) identifica a referência e \(m\) a medida de correlação. Uma diferença positiva indica maior magnitude de associação do ITI naquela comparação. Os sinais das correlações também serão reportados, pois relações de sentidos opostos não devem ser ocultadas pelo uso do módulo.

Essa definição é uma proposta de explicitação da hipótese sem direção prévia. Não altera a interpretação dos registros históricos até que se confira se o código utilizou módulo, correlação assinada ou outro critério. A mudança da estatística exige nova execução e nova identificação dos resultados.

As séries apresentam dependência temporal, e os retornos de horizontes maiores se sobrepõem. O procedimento de reamostragem deve preservar parte dessa dependência e a correspondência entre ITI, referências e retornos. O bootstrap em blocos oferece uma abordagem para observações dependentes, sob condições apropriadas de estacionariedade (Künsch, 1989). Seu uso não elimina a necessidade de avaliar a adequação de uma janela marcada por mudanças institucionais.

Na implementação final, serão registrados o tipo de bloco, o comprimento, a quantidade de reamostragens, a semente e o método de construção dos intervalos de confiança. Cada bloco deverá reamostrar conjuntamente as variáveis utilizadas na diferença de correlações. Reamostrar o ITI e a referência independentemente destruiria a estrutura pareada da comparação.

A multiplicidade também será considerada. As 24 comparações compartilham dados e não representam experimentos independentes. A continuidade prevê uma comparação principal previamente definida e o tratamento das demais como análises secundárias; se forem realizados testes de uma família de hipóteses, será adotada uma correção declarada, como a de Holm (1979). Nenhum ajuste desse tipo é presumido para os resultados já apresentados.

## 4.9 Avaliação de informação incremental

A comparação de correlações responde se uma medida apresenta associação mais forte que outra no recorte avaliado. Uma etapa adicional poderá investigar se o ITI contribui quando as referências já estão presentes no modelo.

Uma especificação candidata é

\[
R_w^{(h)}=\beta_0+\boldsymbol{\beta}^{\mathsf T}\mathbf{B}_w
+\gamma ITI_w+\boldsymbol{\theta}^{\mathsf T}\mathbf{Z}_w+\varepsilon_w,
\]

em que \(\mathbf{B}_w\) contém referências não redundantes e \(\mathbf{Z}_w\) reúne controles disponíveis no instante de previsão. O modelo com ITI seria comparado ao modelo sem esse termo. A escolha dos controles, a capacidade da amostra e a dependência dos resíduos precisariam ser examinadas antes da estimação.

Essa etapa será realizada apenas com dados suficientes e separação temporal entre ajuste e avaliação. A seleção do parâmetro de memória, das variáveis e dos modelos não poderá utilizar os retornos do período reservado ao teste. Janelas de validação cronológicas deverão respeitar também o intervalo futuro utilizado nos rótulos, evitando sobreposição entre alvos de treinamento e teste nas fronteiras.

Essa formulação não constitui resultado desta qualificação. Ela explicita o procedimento necessário para que uma afirmação futura de contribuição incremental seja sustentada por algo além de correlações isoladas.

## 4.10 Registro experimental

Cada execução deverá estar associada à versão do corpus, ao checkpoint, ao tokenizador, às configurações de classificação e agregação e à revisão do código. Os resultados precisam incluir as séries intermediárias e finais, permitindo localizar a etapa responsável por uma diferença.

A execução em máquinas distintas é útil para verificar a estabilidade operacional, mas a comparação exige mais que a contagem final de resultados favoráveis. Devem ser verificadas diferenças nos escores, nas séries e nas estatísticas, com tolerância numérica declarada. O Apêndice B organiza os registros disponíveis e os campos ainda necessários.

# 5 Resultados preliminares e discussão

## 5.1 Estado da implementação

O procedimento foi executado no estudo de caso da Sabesp, incluindo organização do corpus, inferência do classificador, construção das séries e comparação com retornos futuros. A execução demonstra que as etapas foram integradas operacionalmente. A qualidade da medida e sua relação com o mercado, entretanto, dependem das avaliações apresentadas a seguir.

Em outubro de 2026, a configuração R1 foi executada no supercomputador Santos Dumont e posteriormente no ambiente local. Os registros reportam seis comparações favoráveis ao ITI entre 24, sem diferenças significativas pelo bootstrap empregado. Os identificadores operacionais são apresentados no Apêndice B.

O estudo passou por mudanças de corpus e de protocolo de anotação. Por esse motivo, os resultados são organizados por etapa. As comparações textuais utilizam inicialmente a anotação do autor; a referência consolidada por especialistas ainda não estava disponível na versão examinada para esta qualificação.

## 5.2 Avaliação exploratória do classificador

A primeira avaliação utilizou cem notícias com um critério simplificado de anotação. O classificador apresentou acurácia de 48%, kappa de 0,163 e F1 macro de 0,42, conforme a Tabela 1.

**Tabela 1 — Avaliação exploratória do classificador financeiro em português.**

| Métrica | Resultado |
|---|---:|
| Número de notícias | 100 |
| Acurácia | 48% |
| Kappa de Cohen | 0,163 |
| F1 macro | 0,42 |

Fonte: resultados preliminares da pesquisa, registrados no manuscrito de qualificação.

Os valores indicam concordância limitada com a referência utilizada nessa etapa. A ausência de uma matriz de confusão e da distribuição de classes impede identificar, apenas por esses números, quais classes concentraram os erros ou quanto a acurácia difere de uma previsão majoritária.

Também foram reportadas avaliações com um modelo de tweets em português e um modelo baseado em BERT para português. Como seus identificadores, configurações de ajuste e métricas completas não constam dos registros apresentados, eles não são usados nesta versão para concluir que a escolha do modelo seja irrelevante. Uma comparação entre classificadores exige entradas, referências e condições de avaliação equivalentes.

## 5.3 Avaliação orientada à Sabesp

Após a reunião de orientação de 6 de outubro de 2026, o critério de anotação passou a enfatizar o efeito da informação para a Sabesp. A rodada associada ao protocolo de 7 de outubro de 2026 apresentou acurácia de 50% e kappa de aproximadamente 0,20 na amostra de cem notícias.

A separação por tipo de notícia mostra resultados distintos, apresentados na Tabela 2.

**Tabela 2 — Comparação com a anotação do autor orientada à Sabesp.**

| Subconjunto | Notícias | Acurácia | Kappa de Cohen |
|---|---:|---:|---:|
| Amostra completa | 100 | 50,0% | 0,20 |
| Matérias focais sobre a Sabesp | 74 | 52,7% | 0,26 |
| Notícias multiempresa ou de agenda | 26 | 42,3% | −0,03 |

Fonte: resultados preliminares da pesquisa, protocolo identificado como 2026-10-07. Valores de kappa arredondados conforme o registro disponível.

O desempenho é numericamente maior nas matérias focais. Nas notícias multiempresa ou de agenda, o kappa próximo de zero indica concordância numericamente próxima daquela esperada pelas distribuições marginais nessa amostra. O resultado é compatível com a hipótese de que a classificação do documento inteiro tenha dificuldade para representar a polaridade de uma entidade específica.

Essa interpretação ainda não identifica a causa dos erros. Os subconjuntos diferem em tamanho e podem diferir em distribuição de classes, extensão dos textos e ambiguidade. A análise deverá verificar se o conteúdo referente à Sabesp foi preservado após o truncamento, se o modelo privilegiou outra empresa e se os critérios humanos foram aplicados consistentemente.

A diferença entre 48% e 50% também não demonstra melhoria do modelo, pois a referência de anotação mudou. Comparações entre rodadas com critérios diferentes devem ser tratadas como diagnóstico de versões do protocolo, não como evolução de desempenho sob uma tarefa fixa.

## 5.4 Consolidação da referência humana

A participação de avaliadores com conhecimento em economia e finanças foi prevista para ampliar a avaliação da tarefa. Entre os colaboradores convidados está Raphael Veloso, cuja participação é registrada nos agradecimentos. A proposta inclui um subconjunto comum de aproximadamente trinta notícias, avaliado independentemente.

Até o estágio descrito nesta qualificação, não havia uma referência consolidada com múltiplos especialistas acompanhada de métricas de concordância. Assim, os resultados das Tabelas 1 e 2 expressam comparação com a anotação do mestrando. Não serão apresentados como desempenho contra consenso especializado.

A consolidação dessa referência tem duas funções. A primeira é verificar se o critério de polaridade por empresa pode ser aplicado de forma consistente. A segunda é permitir uma avaliação mais independente do classificador. Caso a concordância humana seja baixa, será necessário revisar as instruções e a definição das classes antes de atribuir toda a divergência ao modelo.

## 5.5 Comparação temporal entre o ITI e as referências

As configurações R0 e R1 foram avaliadas no recorte de novembro de 2023 a abril de 2024, com aproximadamente 465 artigos. R0 corresponde à configuração inicial registrada no projeto; R1 utiliza parâmetro nominal de memória igual a 0,70. O valor de memória e as demais configurações de R0 precisam ser apresentados para que a comparação seja integralmente reproduzível.

O protocolo utiliza 24 combinações de medida de referência, correlação e horizonte. A Tabela 3 preserva os resultados reportados para o corpus adotado na rodada canônica.

**Tabela 3 — Resumo das comparações exploratórias por configuração.**

| Configuração | Comparações reportadas como favoráveis ao ITI | Proporção | Comparações com diferença significativa no procedimento reportado |
|---|---:|---:|---:|
| R0 | 5 de 24 | 20,8% | 0 |
| R1, parâmetro nominal de memória 0,70 | 6 de 24 | 25,0% | 0 |

Fonte: resultados preliminares da pesquisa. A regra histórica de comparação e os parâmetros do bootstrap deverão acompanhar a tabela definitiva.

Na configuração R1, seis comparações favoreceram o ITI segundo o critério implementado. Nenhuma apresentou diferença estatisticamente significativa pelo procedimento de reamostragem utilizado. Esse resultado não sustenta uma afirmação de superioridade do ITI no recorte analisado.

A contagem de comparações favoráveis é apenas um resumo. Ela não informa a magnitude das diferenças, o sinal das correlações ou a incerteza de cada estimativa. Uma diferença pequena e outra grande contribuem igualmente para a contagem. Além disso, as comparações compartilham semanas, notícias e retornos. A apresentação final deverá incluir os coeficientes e os intervalos de confiança por referência e horizonte.

A ausência de diferença significativa também não demonstra equivalência entre o ITI e as referências. A janela semanal é curta e os retornos de múltiplas semanas se sobrepõem. O poder de identificar diferenças pode ser limitado, especialmente quando o sinal textual apresenta erro de classificação. A interpretação adequada é a ausência de evidência de superioridade nas condições examinadas.

## 5.6 Sensibilidade à versão do corpus e ao período

Uma execução anterior sobre o corpus legado registrou dez comparações favoráveis ao ITI, com duas diferenças significativas. Após a migração do corpus, a rodada canônica apresentou seis comparações favoráveis e nenhuma significativa. A divergência mostra que as conclusões dependem da versão dos dados e precisam ser rastreadas até as alterações responsáveis.

Essa observação não permite atribuir a mudança exclusivamente à quantidade de notícias, ao modelo ou à memória. É necessário comparar os identificadores dos artigos, as datas, os textos extraídos e os critérios de inclusão entre as versões. Também devem ser verificadas mudanças no alinhamento semanal e no tratamento de dados ausentes.

Na análise ampliada de maio de 2022 a abril de 2024, o registro disponível informa aproximadamente 33% de comparações favoráveis, sem diferenças significativas. Esse percentual é mantido como descrição exploratória. Não se afirma que tenha ocorrido queda em relação aos 25% da rodada canônica, pois 33% é numericamente maior e a configuração de referência da comparação histórica não está suficientemente documentada.

As duas análises sugerem a necessidade de controlar a seleção da janela e a versão do corpus. A ampliação do período aumenta a quantidade potencial de observações, mas também altera a composição da cobertura e pode reunir contextos diferentes. Por isso, mais dados não implicam automaticamente evidência mais forte, nem evidência mais fraca.

<!-- CONFIRMAR P09: recuperar o relatório da janela ampliada, seu denominador, corpus, configuração e datas. Não converter “cerca de 33%” em 8/24 sem evidência. A data “agosto/2024” da execução legada também precisa ser verificada. -->

## 5.7 Discussão das questões de pesquisa

A avaliação textual indica que o classificador ainda apresenta concordância limitada com a tarefa orientada à Sabesp. Os resultados por tipo de notícia apontam uma direção concreta para a análise de erros: investigar a identificação da entidade e a relação entre o conteúdo completo e o trecho processado pelo modelo.

A avaliação temporal mostra que a integração entre coleta, classificação, agregação e comparação foi executada. Contudo, as configurações apresentadas não oferecem evidência estatística de superioridade do ITI sobre as referências. A hipótese principal permanece sem confirmação no recorte e no procedimento reportados.

A investigação da memória está parcialmente implementada, mas sua interpretação depende da descrição completa de R0, da agregação diária e do parâmetro efetivo. Sem esses elementos, não é possível atribuir a diferença entre cinco e seis comparações favoráveis exclusivamente à retenção temporal.

Até esta etapa, a contribuição mais claramente sustentada é a identificação dos requisitos e das limitações para construir o índice no domínio estudado. A avaliação de informação incremental, a generalização para outras empresas e a análise de outros desfechos permanecem como atividades futuras.

## 5.8 Ameaças à validade

A principal ameaça à validade de construto é a diferença entre o sentimento reconhecido pelo modelo e a orientação da informação para a empresa-alvo. A denominação ITI também pode induzir uma interpretação mais ampla que a medida disponível. Por isso, os resultados são descritos como evidência sobre uma representação textual, sem equivalência automática com impacto econômico.

A validade interna depende da qualidade da coleta, da identificação temporal e da correspondência entre notícias e empresa. Duplicatas, atualizações posteriores do texto, datas incorretas e falhas de extração podem alterar o sinal. A utilização de preços futuros na seleção de janelas ou parâmetros também produziria uma avaliação excessivamente favorável.

A validade estatística é limitada pela quantidade de semanas, pela dependência temporal, pela sobreposição dos retornos e pelas comparações múltiplas. Os 24 confrontos não compensam uma série curta. A anotação de cem notícias, por sua vez, oferece uma base inicial de diagnóstico, mas seus estratos e sua referência ainda precisam ser caracterizados.

A validade externa está restrita à Sabesp e aos períodos observados. Os resultados não são automaticamente transferíveis a outras empresas de saneamento ou a outros setores. A ampliação deverá considerar diferenças de cobertura jornalística, liquidez e acontecimentos institucionais.

# 6 Considerações finais e plano de continuidade

## 6.1 Síntese da etapa de qualificação

Este trabalho apresentou uma proposta de índice temporal construído a partir de notícias corporativas em português, com aplicação inicial à Sabesp. O método integra classificação financeira, agregação diária, memória temporal e comparação com medidas simples obtidas das mesmas notícias.

Os experimentos preliminares permitiram executar o fluxo computacional e identificar dificuldades relevantes. Na amostra orientada à empresa, o classificador apresentou acurácia de 50% e kappa de aproximadamente 0,20. Os resultados foram numericamente inferiores nas notícias multiempresa ou de agenda, o que orienta a investigação da adequação entre a tarefa do modelo e a referência humana.

Na avaliação temporal, a configuração R1 apresentou seis comparações favoráveis em 24, sem diferenças significativas no procedimento reportado. Portanto, os dados disponíveis não demonstram a superioridade do índice. A variação dos resultados entre versões do corpus também evidencia a necessidade de rastrear as transformações dos dados e tornar o protocolo mais preciso.

A pesquisa avança, nesta etapa, ao delimitar o problema e demonstrar a viabilidade operacional de sua investigação. A consolidação da contribuição científica dependerá da validação da representação textual e de uma avaliação temporal que controle as escolhas experimentais.

## 6.2 Atividades previstas

A continuidade será organizada em etapas dependentes. Primeiro, será consolidado o inventário do corpus, com fontes, critérios de seleção, contagens e histórico de versões. Em seguida, serão concluídas as anotações independentes e analisados os desacordos, distinguindo neutralidade, ambiguidade e impossibilidade de avaliação.

A terceira etapa será a análise dos erros do classificador. Serão examinados tipo de notícia, extensão do texto, truncamento e presença de múltiplas entidades. Conforme os resultados, poderão ser avaliadas alternativas de seleção de trechos ou de classificação orientada ao alvo. Essas mudanças serão comparadas sob uma referência fixa e sem reutilizar o conjunto final de teste para ajuste.

Depois da avaliação textual, serão consolidadas as fórmulas do ITI e das referências, a regra de atualização temporal e as configurações de memória. A etapa financeira utilizará instantes de corte explícitos, quantidades efetivas de observações e estatísticas acompanhadas de incerteza.

Por fim, será avaliada a possibilidade de ampliar os períodos e incluir outras empresas. Essa ampliação dependerá da cobertura e da qualidade dos dados. Análises de volatilidade, volume, assimetria e informação incremental serão incorporadas apenas quando houver condições para avaliá-las de forma consistente.

**Quadro 3 — Plano de continuidade e entregas verificáveis.**

| Etapa | Entrega | Condição para avanço |
|---|---|---|
| Consolidação do corpus | Inventário, filtros, contagens e versões | Notícias e datas rastreáveis |
| Referência humana | Anotações individuais, concordância e consenso documentado | Critério de classificação estável |
| Diagnóstico do modelo | Matriz de confusão e análise de erros | Adequação da tarefa e limitações conhecidas |
| Especificação do índice | Fórmulas, parâmetros e regras temporais | Reprodução da série a partir das saídas textuais |
| Avaliação temporal | Coeficientes, diferenças, incerteza e análise de sensibilidade | Ausência de uso indevido de dados futuros |
| Ampliação e redação final | Novos recortes e síntese das contribuições | Evidências compatíveis com as conclusões |

Fonte: elaboração própria.

O cronograma calendarizado será definido conforme o prazo de defesa e o andamento das anotações. A sequência prioriza a qualidade dos dados e da tarefa antes da ampliação do número de modelos ou de testes.

<!-- CONFIRMAR P10: preencher datas reais do cronograma com o autor e o orientador. Não deduzir prazo de defesa a partir do ano da capa. -->

# Apêndice A — Protocolo de anotação orientada à empresa

## A.1 Finalidade e situação do protocolo

O protocolo orienta a classificação da informação referente à Sabesp em notícias financeiras. A tarefa considera o efeito descrito no texto para a empresa e não a reação posteriormente observada no preço da ação.

A rodada quantitativa apresentada no Capítulo 5 está identificada com a versão de 7 de outubro de 2026. O apêndice do manuscrito anterior menciona a versão de 19 de outubro de 2026. Essas versões devem permanecer distintas até que se documente se houve alteração nas instruções ou apenas na apresentação. As orientações detalhadas a seguir constituem uma proposta consolidada para a continuidade e não devem ser atribuídas retroativamente aos rótulos existentes.

## A.2 Material apresentado ao anotador

Cada item deve conter um identificador, a empresa-alvo, o título e o corpo da notícia, além dos campos de resposta. O texto processado deve ser preservado para que uma atualização posterior da página não altere o material avaliado.

O anotador não terá acesso às previsões do classificador, às respostas de outros participantes ou aos retornos posteriores da ação durante a etapa independente. “Anotação cega” refere-se a essas restrições; não significa impedir acesso às informações necessárias à compreensão da própria notícia.

## A.3 Pergunta e classes

**Pergunta:** considerando as informações apresentadas no título e no corpo, o fato descrito é favorável, desfavorável ou neutro para a Sabesp?

- **Positiva:** o texto apresenta um efeito favorável identificável para a empresa, sustentado pelas informações da matéria.
- **Negativa:** o texto apresenta um efeito desfavorável identificável para a empresa, sustentado pelas informações da matéria.
- **Neutra:** o conteúdo referente à empresa não apresenta uma orientação favorável ou desfavorável suficientemente definida.

A classificação deve considerar o contexto. Aumento de receita, investimento ou alteração tarifária não recebem automaticamente uma classe: o texto pode apresentar contrapartidas, custos ou condições que modifiquem sua interpretação.

Se o item não puder ser avaliado por falta de conteúdo ou ausência de relação efetiva com a empresa, o anotador marcará essa condição em campo próprio. A impossibilidade de avaliação não deverá ser convertida silenciosamente em neutralidade.

## A.4 Tipo de notícia

| Tipo | Regra de identificação |
|---|---|
| Focal | A Sabesp constitui o assunto principal ou ocupa parcela substantiva da notícia. |
| Multiempresa/agenda | A Sabesp é discutida ao lado de outras empresas ou de uma agenda ampla de mercado. |
| Tangencial | A empresa aparece de passagem, sem desenvolvimento suficiente para a tarefa. |

O tipo da notícia não determina a classe. Uma notícia multiempresa pode conter informação claramente favorável à Sabesp; uma matéria focal pode ser neutra.

## A.5 Regras para casos difíceis

Em matérias com várias empresas, o julgamento deve se restringir à Sabesp. Quando houver efeitos de sinais diferentes, o anotador deverá explicar a ambiguidade e indicar se o texto permite identificar uma orientação predominante. A decisão não será baseada em conhecimento do comportamento futuro da ação.

Uma notícia de aumento de custos e expansão de receitas, sem elementos para avaliar qual efeito predomina, deve receber justificativa de ambiguidade. Uma nota sobre outro ativo que apenas enumere a Sabesp pode ser classificada como menção tangencial e não avaliável. Esses são exemplos hipotéticos de aplicação das regras, não observações do corpus.

O protocolo deverá definir, antes da etapa final, como tratar informações que descrevem valorização ou queda já ocorrida. Esses textos podem estar relacionados à empresa, mas também podem repetir o próprio fenômeno financeiro que se pretende analisar. Sua identificação permite uma análise de sensibilidade separada.

## A.6 Campos propostos

| Campo lógico | Conteúdo |
|---|---|
| Identificador da notícia | Chave estável para junção com o corpus |
| Identificador do anotador | Código do participante |
| Versão do protocolo | Instruções utilizadas na avaliação |
| Classe | Positiva, negativa ou neutra |
| Avaliável | Indicação de suficiência e pertinência do conteúdo |
| Tipo | Focal, multiempresa/agenda ou tangencial |
| Ambiguidade | Presença de elementos conflitantes |
| Evidência | Trecho ou descrição que fundamenta o rótulo |
| Observações | Justificativa complementar |
| Data da anotação | Registro da execução |

Os nomes físicos das colunas deverão ser compatibilizados com a planilha existente. A troca de nomes não deverá eliminar rótulos individuais ou impedir a recuperação de versões anteriores.

## A.7 Concordância e consolidação

As métricas de concordância serão calculadas sobre os itens efetivamente compartilhados entre anotadores, antes da discussão conjunta. O relatório deverá informar quantos participantes avaliaram cada item e quais notícias ficaram sem avaliação completa.

Quando houver maioria, a classe majoritária poderá formar a referência consolidada. Empates serão examinados por adjudicação, com registro das justificativas e da decisão final. Os rótulos originais serão preservados. A concordância entre humanos e o desempenho do modelo serão apresentados separadamente.

# Apêndice B — Rastreabilidade experimental

## B.1 Registros disponíveis

| Registro | Informação preservada |
|---|---|
| Estudo de caso | Sabesp; ação SBSP3 |
| Janela principal | Novembro de 2023 a abril de 2024 |
| Quantidade aproximada | 465 artigos, conforme o original |
| Janela ampliada | Maio de 2022 a abril de 2024 |
| Amostra textual | 100 notícias; 74 focais e 26 de agenda/multiempresa |
| Protocolo da rodada reanotada | 2026-10-07 |
| Versão mencionada no apêndice anterior | 2026-10-19 |
| Identificador R1 | `sabesp_r1_alpha070` |
| Ambiente HPC reportado | Santos Dumont; fila de desenvolvimento GPU Sequana |
| Job Slurm reportado | `11621573` |
| Corpus canônico referido | `water_utilities_corpus` |
| Corpus legado referido | `saneamento_corpus` |
| Resultado R1 canônico | 6/24 comparações favoráveis; nenhuma significativa |
| Resultado histórico legado | 10/24 favoráveis; duas significativas |

Fonte: registros apresentados no manuscrito original. Os identificadores não substituem os arquivos de saída e as configurações completas.

## B.2 Manifesto necessário por execução

O manifesto deverá reunir revisão do código, versão ou hash do corpus, quantidade de notícias, período de coleta, checkpoint e revisão dos pesos, configuração do tokenizador, ordem das classes, política de truncamento, regra de agregação diária, pesos, alfa nominal e efetivo, estado inicial, calendário, horário de corte, fonte dos preços, construção dos retornos e exclusões de semanas.

Para a avaliação, deverão ser incluídos a regra de comparação entre correlações, as estatísticas completas, o método de bootstrap, os parâmetros de reamostragem, a semente e o eventual tratamento de testes múltiplos. A comparação entre ambientes deverá registrar tolerâncias e diferenças quantitativas, além da indicação de que a execução terminou.

<!-- FIM_TEXTO_ACADEMICO -->

# PARTE III — REFERÊNCIAS E AUDITORIA BIBLIOGRÁFICA

## 1. Referências para o texto reescrito

As chaves entre colchetes são sugestões para o `.bib`, não parte da referência impressa. Preservar as chaves existentes quando estiverem corretas e houver dependências no projeto. A lista abaixo reúne os trabalhos citados na Parte II. A verificação variou entre texto completo, página editorial e registro institucional, conforme indicado na auditoria; não se afirma que todos os artigos tenham sido integralmente relidos.

**[araci2019finbert]** ARACI, Dogu. *FinBERT: Financial Sentiment Analysis with Pre-trained Language Models*. arXiv:1908.10063, 2019. Disponível em: https://arxiv.org/abs/1908.10063. DOI: https://doi.org/10.48550/arXiv.1908.10063.

**[artstein2008agreement]** ARTSTEIN, Ron; POESIO, Massimo. Survey Article: Inter-Coder Agreement for Computational Linguistics. *Computational Linguistics*, v. 34, n. 4, p. 555–596, 2008. DOI: https://doi.org/10.1162/coli.07-034-R2. Disponível em: https://aclanthology.org/J08-4004/.

**[baker2016uncertainty]** BAKER, Scott R.; BLOOM, Nicholas; DAVIS, Steven J. Measuring Economic Policy Uncertainty. *The Quarterly Journal of Economics*, v. 131, n. 4, p. 1593–1636, 2016. Versão de trabalho consultada: https://www.policyuncertainty.com/media/EPU_BBD_Mar2016.pdf. Registro editorial: https://academic.oup.com/qje/article/131/4/1593/2468873. Não atribuir a paginação do periódico à versão de trabalho em uma citação direta.

**[brasil2020saneamento]** BRASIL. Lei nº 14.026, de 15 de julho de 2020. Atualiza o marco legal do saneamento básico e altera a legislação correlata. Brasília, DF, 2020. Disponível em: https://www.planalto.gov.br/ccivil_03/_ato2019-2022/2020/lei/l14026.htm. No `.bib`, utilizar autor institucional protegido: `author = {{Brasil}}`.

**[brito2022sentimento]** BRITO, Anderson Dias; SANTOS, Allisson Silva dos; MOURA FILHO, Gerson Borges de; MARTINS, Orleans Silva. Associação do sentimento do investidor com ciclos de mercado: evidências brasileiras. *Revista de Administração, Contabilidade e Economia da Fundace*, v. 13, n. 3, 2022. DOI: https://doi.org/10.13059/racef.v13i3.985. Disponível em: https://racef.fundace.org.br/index.php/racef/article/view/985. A paginação 165–180 presente no original precisa ser conferida no PDF editorial antes de ser reintroduzida.

**[cohen1960agreement]** COHEN, Jacob. A Coefficient of Agreement for Nominal Scales. *Educational and Psychological Measurement*, v. 20, n. 1, p. 37–46, 1960. DOI: https://doi.org/10.1177/001316446002000104.

**[cortis2017semeval]** CORTIS, Keith; FREITAS, André; DAUDERT, Tobias; HUERLIMANN, Manuela; ZARROUK, Manel; HANDSCHUH, Siegfried; DAVIS, Brian. SemEval-2017 Task 5: Fine-Grained Sentiment Analysis on Financial Microblogs and News. In: *Proceedings of the 11th International Workshop on Semantic Evaluation (SemEval-2017)*. Vancouver: Association for Computational Linguistics, 2017. p. 519–535. DOI: https://doi.org/10.18653/v1/S17-2089. Disponível em: https://aclanthology.org/S17-2089/.

**[devlin2019bert]** DEVLIN, Jacob; CHANG, Ming-Wei; LEE, Kenton; TOUTANOVA, Kristina. BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding. In: *Proceedings of the 2019 Conference of the North American Chapter of the Association for Computational Linguistics: Human Language Technologies, Volume 1*. Minneapolis: Association for Computational Linguistics, 2019. p. 4171–4186. Disponível em: https://aclanthology.org/N19-1423/.

**[duarte2021falls]** DUARTE, Juvenal José; MONTENEGRO GONZÁLEZ, Sahudy; CRUZ JUNIOR, José César. Predicting Stock Price Falls Using News Data: Evidence from the Brazilian Market. *Computational Economics*, v. 57, n. 1, p. 311–340, 2021. DOI: https://doi.org/10.1007/s10614-020-10060-y. Publicação eletrônica inicial em 2020. Conferir a representação dos sobrenomes compostos no registro exportado da editora; não usar apenas “Cruz” ou “González” por simplificação automática.

**[fleiss1971agreement]** FLEISS, Joseph L. Measuring Nominal Scale Agreement among Many Raters. *Psychological Bulletin*, v. 76, n. 5, p. 378–382, 1971. DOI: https://doi.org/10.1037/h0031619.

**[frbsfNewsSentiment]** FEDERAL RESERVE BANK OF SAN FRANCISCO. *Daily News Sentiment Index*. [s.d.]. Disponível em: https://www.frbsf.org/research-and-insights/data-and-indicators/daily-news-sentiment-index/. Documentação da série consultada em outubro de 2026. Registrar no `.bib` a data real de acesso da implementação final, sem inventar data de publicação da página.

**[holm1979multiple]** HOLM, Sture. A Simple Sequentially Rejective Multiple Test Procedure. *Scandinavian Journal of Statistics*, v. 6, n. 2, p. 65–70, 1979. Cópia acadêmica localizada: https://www.ime.usp.br/~abe/lista/pdf4R8xPVzCnX.pdf. Referência adicionada para o plano de tratamento da multiplicidade; não implica aplicação retrospectiva do procedimento aos resultados R0/R1.

**[kunsch1989bootstrap]** KÜNSCH, Hans R. The Jackknife and the Bootstrap for General Stationary Observations. *The Annals of Statistics*, v. 17, n. 3, p. 1217–1241, 1989. DOI: https://doi.org/10.1214/aos/1176347265. Referência adicionada para a discussão de dependência temporal; conferir condições e variante de bootstrap na implementação, sem atribuir ao artigo uma regra específica de comprimento de bloco não consultada.

**[loughran2011liability]** LOUGHRAN, Tim; MCDONALD, Bill. When Is a Liability Not a Liability? Textual Analysis, Dictionaries, and 10-Ks. *The Journal of Finance*, v. 66, n. 1, p. 35–65, 2011. DOI: https://doi.org/10.1111/j.1540-6261.2010.01625.x.

**[santos2023finbert]** SANTOS, Lucas L.; BIANCHI, Reinaldo A. C.; COSTA, Anna H. R. FinBERT-PT-BR: Análise de Sentimentos de Textos em Português do Mercado Financeiro. In: *Anais do II Brazilian Workshop on Artificial Intelligence in Finance*. Sociedade Brasileira de Computação, 2023. p. 144–155. DOI informado no original: https://doi.org/10.5753/bwaif.2023.231151. Texto completo consultado: https://sol.sbc.org.br/index.php/bwaif/article/download/24960/24781/. Página editorial: https://sol.sbc.org.br/index.php/bwaif/article/view/24960. Conferir o DOI e a paginação no exportador editorial antes de consolidar o `.bib`; a leitura do PDF confirmou autoria, ano e conteúdo metodológico.

**[shapiro2022news]** SHAPIRO, Adam Hale; SUDHOF, Moritz; WILSON, Daniel J. Measuring News Sentiment. *Journal of Econometrics*, v. 228, n. 2, p. 221–243, 2022. Versão de trabalho consultada: https://www.frbsf.org/wp-content/uploads/wp2017-01.pdf, revisada em março de 2020, Working Paper 2017-01, DOI https://doi.org/10.24148/wp2017-01. Não utilizar o DOI do working paper como DOI da publicação de 2022. Manter identificadas as duas versões no acervo bibliográfico.

**[sinha2022sentfin]** SINHA, Ankur; KEDAS, Satishwar; KUMAR, Rishu; MALO, Pekka. SEntFiN 1.0: Entity-aware sentiment analysis for financial news. *Journal of the Association for Information Science and Technology*, v. 73, n. 9, p. 1314–1335, 2022. DOI: https://doi.org/10.1002/asi.24634. Registro institucional consultado: https://research.aalto.fi/en/publications/sentfin-10-entity-aware-sentiment-analysis-for-financial-news/.

**[souza2020bertimbau]** SOUZA, Fábio; NOGUEIRA, Rodrigo; LOTUFO, Roberto. BERTimbau: Pretrained BERT Models for Brazilian Portuguese. In: *Brazilian Conference on Intelligent Systems — BRACIS*. Springer, 2020. p. 403–417. Registro institucional localizado: https://repositorio.unicamp.br/acervo/detalhe/1161906. Não associar essa referência, por si só, a um classificador supervisionado específico utilizado nos experimentos.

**[tetlock2007media]** TETLOCK, Paul C. Giving Content to Investor Sentiment: The Role of Media in the Stock Market. *The Journal of Finance*, v. 62, n. 3, p. 1139–1168, 2007. DOI: https://doi.org/10.1111/j.1540-6261.2007.01232.x.

**[yoshinaga2012sentiment]** YOSHINAGA, Claudia Emiko; CASTRO JUNIOR, Francisco Henrique Figueiredo de. The Relationship between Market Sentiment Index and Stock Rates of Return: A Panel Data Analysis. *Brazilian Administration Review*, v. 9, n. 2, p. 189–210, 2012. DOI: https://doi.org/10.1590/S1807-76922012000200005. Disponível em: https://bar.anpad.org.br/index.php/bar/article/view/177.

**[yuan2020target]** YUAN, Chaofa; LIU, Yuhan; YIN, Rongdi; ZHANG, Jun; ZHU, Qinling; MAO, Ruibin; XU, Ruifeng. Target-based Sentiment Annotation in Chinese Financial News. In: *Proceedings of the Twelfth Language Resources and Evaluation Conference*. Marseille: European Language Resources Association, 2020. p. 5040–5045. Disponível em: https://aclanthology.org/2020.lrec-1.620/.

As observações de verificação desta seção são editoriais. Não devem aparecer no campo `note` de referências impressas. Devem permanecer no relatório de auditoria ou em comentários do `.bib`.

## 2. Auditoria das 21 referências presentes no PDF original

| Referência original | Verificação e problema identificado | Tratamento |
|---|---|---|
| Araci (2020) | O registro arXiv 1908.10063 informa submissão em 27/08/2019 e uma versão de 2019. | Corrigido para 2019 na versão correspondente. |
| Artstein e Poesio (2008) | Autoria, periódico, volume e páginas confirmados na ACL Anthology. | Mantida; não usada para estabelecer limiar universal de qualidade. |
| “AUTOR, U.” (2024) | O registro associado ao endereço informado identifica Luiz Fernando Menegazzo Ferreyra como `dc.creator`; apresenta datas de 2025/2026 e vínculo com Engenharia de Produção, não sustenta “dissertação de mestrado de 2024”. | Removida do texto acadêmico; preservar registro em quarentena até conferir folha de rosto, natureza e data no PDF. |
| Baker, Bloom e Davis (2016) | Texto de trabalho localizado no site do projeto; referência da publicação é distinta da versão de trabalho. | Mantida com distinção entre versões. |
| Brasil (2020) | Lei confirmada em fonte oficial. URL do PDF original sofre quebras tipográficas na extração. | URL normalizada; autor institucional protegido. |
| Brito (2022) | Página da revista apresenta quatro autores, e não autoria individual. | Corrigido para Brito et al.; paginação ainda a confirmar no PDF. |
| Cohen (1960) | Título e DOI localizados em registro editorial. | Mantida para definição de concordância, não como fonte de “70% ou 0,40”. |
| Cortis (2017) | Primeiro autor é Keith Cortis, não “A. Cortis”; sete autores listados na ACL Anthology. | Autoria completa corrigida e citação como Cortis et al. |
| Duarte, González e Cruz (2021) | Registro editorial e índices apontam v. 57(1), p. 311–340, não p. 1381–1405. | Paginação corrigida; atenção aos sobrenomes compostos. |
| Fleiss (1971) | Dados bibliográficos compatíveis com o registro localizado; nota “Sem PDF local no repositório; ver nota fleiss1971.md” não pertence à bibliografia. | Nota interna removida. |
| Gattai e Souza (2025) | Página/edição da revista localizada como v. 19, n. 7 (2026); conflito com o ano 2025 do original. Acesso integral bloqueado nesta consulta. | Não utilizada na sustentação do texto reescrito; conferir ano e artigo integral antes de reinserir. |
| Loughran e McDonald (2011) | Autoria, ano e páginas confirmados na editora. | Mantida para adequação de medidas textuais ao domínio; removida como suposta fonte específica de todo o protocolo B0–B3. |
| Marquezan e Assunção (2025) | Registro da SBC localizado; primeiro autor aparece como Gabriel Marquezan Pozzati da Luz. O acesso integral não foi concluído. | Não repetir conclusões sobre porte, atrasos e heterogeneidade sem leitura integral; normalizar autoria pelo registro editorial. |
| Neuenschwander (2014) | Página de coautor identifica Bruna Neuenschwander e coautores; a inicial “R.” e autoria individual do original são inadequadas. | Retirada da argumentação detalhada sobre coleta até conferir texto integral e ligação editorial correta. |
| Santos, Bianchi e Costa (2023) | PDF integral acessado; distingue modelo de linguagem de classificador supervisionado. | Mantida com nomenclatura corrigida; conferir checkpoint local e exportação bibliográfica. |
| Shapiro, Sudhof e Wilson (2022) | Localizadas versão de trabalho e documentação do índice diário. | Mantida; separar artigo, working paper e documentação da suavização diária. |
| Sinha (2022) | Registro institucional confirma quatro autores, volume e páginas. | Autoria completa e citação “Sinha et al.”. |
| Souza, Nogueira e Lotufo (2020) | Registro institucional do BERTimbau localizado; compatível com referência da arquitetura em português. | Mantida como base linguística; não como identificação suficiente do controle experimental. |
| Tetlock (2007) | Página editorial confirma autoria, ano, volume e páginas. | Mantida com afirmações limitadas ao papel da análise textual no estudo de mercado. |
| Yoshinaga e “Junior” (2012) | Página editorial confirma Castro Junior; v. 9(2), p. 189–210, e não v. 9(4), p. 390–408. | Autoria, fascículo e páginas corrigidos. |
| Yuan (2020) | ACL Anthology lista sete autores e confirma título e páginas. | Autoria completa e citação “Yuan et al.”. |

## 3. Referências em quarentena e caminhos de conferência

“Quarentena” significa que a referência foi mantida no registro de auditoria, mas não sustenta uma afirmação na reescrita. Não significa que o trabalho seja inválido. A restrição decorre de metadados conflitantes ou acesso insuficiente ao conteúdo necessário.

### 3.1 Trabalho citado como “AUTOR, U.”

Título: *Os impactos de notícias na performance das ações de empresas de capital aberto no Brasil*.

- Autor identificado no campo de autoria: **Luiz Fernando Menegazzo Ferreyra**.
- Registro original informado: http://repositorio.utfpr.edu.br/jspui/handle/1/40390.
- Registro espelhado consultado: https://educapes.capes.gov.br/handle/capes/1183059?mode=full.
- Catálogo da UTFPR localiza o trabalho em Engenharia de Produção e em listagem de trabalhos de graduação; o registro de referência não confirma a descrição de mestrado de 2024.

O resumo localizado associa uma conclusão de falta de causalidade ao insucesso de previsões de retorno. Sem examinar o desenho, não é adequado transformar isso em evidência geral de ausência de causalidade ou em fundamento metodológico para o ITI. A relação entre causalidade e desempenho de estratégias deve ser discutida com precisão.

### 3.2 Gattai e Souza

Título: *Privatização da Sabesp e reação do mercado: um estudo de evento sobre as ações da Equatorial Energia (EQTL3)*.

- Autores localizados: Natália Ilha Gattai e João Carlos Félix Souza.
- Artigo: https://ojs.focopublicacoes.com.br/foco/article/view/12166.
- Edição: https://ojs.focopublicacoes.com.br/foco/issue/view/80.

A edição localizada é de 2026. Não manter “publicado online 2025” sem comprovação. Se reinserido, usar somente para a questão específica estudada em EQTL3, após confirmar datas e método. O título do artigo não permite tratar o recorte de novembro/2023 a abril/2024 como se incluísse automaticamente o evento específico examinado pelos autores.

### 3.3 Luz e Assunção

Título: *Análise de Correlação Cruzada entre Emoções de Notícias e Preços de Ações com Grandes Modelos de Linguagem*.

- Registro editorial: https://sol.sbc.org.br/index.php/eramiars/article/view/39420.
- DOI localizado: https://doi.org/10.5753/eramiars.2025.16502.
- Primeiro autor registrado: Gabriel Marquezan Pozzati da Luz.

Conferir exportação de autoria e texto completo antes de citar resultados específicos. O artigo pode ser retomado como trabalho relacionado, mas não deve sustentar, sem essa conferência, a afirmação geral de que heterogeneidade de atrasos “é a regra”.

### 3.4 Neuenschwander e colaboradores

Título: *Sentiment Analysis for Streams of Web Data: A Case Study of Brazilian Financial Markets*.

A página acadêmica de Denilson Barbosa localiza o trabalho com Bruna Neuenschwander, Adriano César Machado Pereira e Wagner Meira Jr., além do coautor responsável pela página: https://sites.ualberta.ca/~denilson/publications/.

O registro do original não deve continuar como “NEUENSCHWANDER, R.”. A referência completa, o endereço editorial e as afirmações sobre coleta e alinhamento devem ser conferidos no artigo antes da reinserção. Nesta reescrita, as exigências de documentação do corpus são apresentadas como requisitos do próprio procedimento, sem atribuição indevida a essa fonte.

## 4. Referências acrescentadas

Devlin et al. (2019) foi acrescentado para fundamentar a explicação de BERT. A documentação do Federal Reserve Bank of San Francisco foi acrescentada para identificar a fonte específica da suavização do índice diário. Künsch (1989) e Holm (1979) foram acrescentados para orientar, respectivamente, a discussão da reamostragem temporal e da multiplicidade. As dissertações da UFSJ foram utilizadas para comparação editorial, não como evidência dos resultados financeiros; por isso, não precisam integrar a bibliografia científica do manuscrito se não forem citadas no texto final.

---

# PARTE IV — IMPLEMENTAÇÃO NO CURSOR E PENDÊNCIAS

## 1. Instrução pronta para o Cursor

> Use este Markdown como documento mestre para revisar o projeto LaTeX da qualificação de Gabriel Felipe Souza Santos. Leia o arquivo inteiro antes de editar. A Parte II contém o texto acadêmico completo a implementar; a Parte III contém referências e decisões bibliográficas. As Partes I e IV são instruções editoriais e não devem virar capítulos da dissertação.
>
> Primeiro, identifique o arquivo principal, a classe utilizada, os arquivos incluídos, o sistema bibliográfico e as entradas existentes. Preserve o template institucional e o mecanismo de compilação. Aplique o texto nos arquivos de capítulos, resumo, abstract, agradecimentos e apêndices. Não reduza o conteúdo a um roteiro nem faça nova reescrita genérica: preserve os argumentos, as distinções metodológicas e os resultados desta versão.
>
> Organize o corpo em seis capítulos: Introdução; Fundamentação teórica; Trabalhos relacionados; Metodologia; Resultados preliminares e discussão; Considerações finais e plano de continuidade. Elimine a duplicação do antigo capítulo de proposta e atualize as referências internas.
>
> Converta as citações de autor e ano em comandos compatíveis com o projeto. Use a Parte III para corrigir metadados e completar autores. Preserve chaves já utilizadas sempre que possível; se precisar renomeá-las, atualize todas as chamadas. Não copie comentários de auditoria para campos `note` que apareçam na bibliografia impressa. Não mantenha “AUTOR, U.” nem crie dados bibliográficos faltantes.
>
> Mantenha exatamente os resultados numéricos informados. As métricas foram extraídas do PDF e não foram recalculadas nesta revisão. Não converta análises propostas em análises concluídas. Não atribua os resultados à anotação de especialistas, porque a versão disponível usa anotação do autor. Não trate as fórmulas candidatas como descrição confirmada das execuções históricas.
>
> Procure no repositório os scripts, relatórios e configurações correspondentes às pendências P01–P10. Resolva automaticamente apenas o que tiver evidência inequívoca nos arquivos. Registre arquivo de origem e valor encontrado em `PENDENCIAS_QUALIFICACAO.md`. Se não houver evidência, mantenha a observação em comentário LaTeX e no relatório de pendências; não invente nem apague a limitação.
>
> Não altere código experimental, fórmulas históricas ou tabelas para fazer os resultados parecerem melhores. Se identificar incompatibilidade entre esta formalização e a implementação, preserve o histórico, documente o conflito e ajuste apenas as afirmações sustentadas. Propostas de novos experimentos devem continuar no futuro e não receber resultados fabricados.
>
> Use ambientes de equações, tabelas e quadros do projeto. Crie labels sem duplicação e remissões automáticas. A descrição da Figura 1 deve ser convertida em diagrama vetorial legível, com a validação textual e a avaliação financeira em caminhos próprios. Não transforme os baselines em etapa posterior à EWMA. Se os dados experimentais não estiverem disponíveis, não invente curvas, matrizes de confusão ou gráficos de desempenho.
>
> Adeque a natureza do trabalho à qualificação, conforme o template e as instruções locais. Não invente banca, data, aprovação, financiamento ou área de concentração. Preserve os nomes do autor e do orientador. O sumário e as listas devem ser gerados automaticamente.
>
> Compile com a ferramenta já utilizada pelo projeto, resolva erros e referências indefinidas e confira o PDF. Evite tabelas com cabeçalhos quebrados, caminhos extensos fora das margens e títulos sem conteúdo suficiente. Ao terminar, entregue um resumo dos arquivos alterados, das referências corrigidas, das pendências não resolvidas e do resultado da compilação. Não declare a dissertação cientificamente validada apenas porque compilou.

## 2. Pendências documentais e experimentais

| ID | Informação necessária | Onde procurar primeiro | Consequência se continuar ausente |
|---|---|---|---|
| P01 | Natureza formal do texto e elementos exigidos na qualificação | Template do projeto e orientações do programa | Manter texto de apresentação como proposta editorial |
| P02 | Situação efetiva da participação dos colaboradores | Planilha de anotação e histórico do projeto | Agradecimento por disponibilidade, sem afirmar anotação concluída |
| P03 | Critério histórico de comparação: sinal, módulo ou outra estatística | Script que gera os 24 confrontos | Não reinterpretar as contagens como diferença de módulos |
| P04 | Checkpoint, revisão, cabeça supervisionada, ordem das classes, tokenizador e controles | Arquivos de configuração e logs de inferência | Não identificar automaticamente o modelo apenas pelo artigo |
| P05 | Corpus exato, fontes, datas, filtros, exclusões, duplicatas e cobertura | Manifesto, CSV/Parquet e código de coleta | Quantidade permanece aproximada; reprodução incompleta |
| P06 | IDs e estratos da amostra, semente, classes humanas, anotadores e versões | Planilhas originais e scripts de amostragem | Sem generalizar acurácia da amostra para o corpus |
| P07 | Agregação diária, pesos, alfa efetivo, inicialização, R0 e dias sem notícia | Implementação do ITI e configurações R0/R1 | Equação permanece formalização parcial, sem alegação de especificação completa |
| P08 | Fonte e ajustes de preços, calendário, horários, fuso, bootstrap e semanas por horizonte | Rotina de séries e relatórios estatísticos | Avaliação financeira segue exploratória |
| P09 | Configuração da janela ampliada, denominador de 33%, corpus legado e datas reais | Relatórios versionados de cada campanha | Não comparar taxas de execuções não equivalentes |
| P10 | Prazos reais de qualificação, anotações, experimentos e defesa | Planejamento com orientador | Plano permanece sequencial, sem datas inventadas |

A lista não exige suspender a revisão textual. O Cursor pode implementar o texto, corrigir a bibliografia e deixar as pendências rastreáveis. O que não pode fazer é preencher lacunas experimentais com escolhas plausíveis e apresentá-las como fatos do estudo.

## 3. Verificações de consistência para a versão final

- [ ] Todas as citações correspondem a entradas reais no `.bib`, com autoria e ano compatíveis.
- [ ] Não aparece a referência “AUTOR, U.”.
- [ ] O texto distingue modelo de linguagem e classificador supervisionado.
- [ ] O rótulo humano, a tarefa do modelo e a empresa-alvo estão definidos.
- [ ] O número de notícias da amostra fecha em 100: 74 + 26.
- [ ] As tabelas preservam 48%, 0,163 e 0,42 para a rodada exploratória.
- [ ] A rodada orientada à Sabesp preserva 50%, 0,20; 52,7%, 0,26; 42,3%, −0,03.
- [ ] R0 e R1 preservam 5/24 e 6/24, respectivamente, sem diferenças significativas na rodada canônica reportada.
- [ ] Os 10/24 e as duas diferenças significativas ficam identificados como resultado legado, não atual.
- [ ] “Cerca de 33%” não é chamado de queda em relação a 25% nem convertido em uma fração não documentada.
- [ ] As versões 2026-10-07 e 2026-10-19 não são fundidas sem registro.
- [ ] As fórmulas do índice e dos baselines correspondem à implementação ou permanecem explicitamente como propostas.
- [ ] O instante de corte das notícias antecede o retorno usado como desfecho.
- [ ] Não se confundem neutralidade, ausência de notícias e falha de coleta.
- [ ] A comparação de correlações não é descrita como prova de causalidade ou de ganho incremental condicionado.
- [ ] A anotação especializada é apresentada de acordo com sua situação efetiva.
- [ ] As conclusões respondem ao que foi executado e não pressupõem confirmação da hipótese.
- [ ] O PDF compilado não inclui instruções ao Cursor nem notas da auditoria como texto acadêmico.

## 4. Decisões que exigem revisão do autor

A reescrita mantém o título original para não alterar unilateralmente a identidade do projeto. Caso a dissertação permaneça restrita à Sabesp, um título mais delimitado seria: **“Índice temporal de sentimento em notícias corporativas: um estudo de caso da Sabesp”**. A troca de “informacional” por “de sentimento” reduziria a distância entre o nome e a medida observada, mas depende da decisão do autor e do orientador.

A hipótese foi concentrada na comparação temporal com retorno, e a discussão de volatilidade, volume e outras empresas foi deslocada para a continuidade. Isso torna a narrativa compatível com os resultados disponíveis. Se houver experimentos adicionais no repositório, eles podem ser incorporados com seus métodos e resultados, em vez de permanecerem apenas mencionados na pergunta principal.

A nova versão detalha condições de reprodução e de avaliação que faltavam no original. Essa ampliação não deve ser confundida com a afirmação de que todas as condições já foram atendidas. Os trechos de proposta, os tempos verbais e os comentários de confirmação fazem parte da integridade da reescrita.

**Fim do documento.**
