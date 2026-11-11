# Qualificação — Índice Temporal Informacional — UFSJ

Roteiro gerado por `make pdf` em 2026-11-11 18:01 -0300. **Não editar à mão** — altere `dados/manifesto_slides.json`.

- Slides principais: 29
- Tempo-alvo somado: 30:00 (1800 s)
- Palavras (voz + transição, principais): ~3758

## Slides principais (defesa ~30 min)

## 01 — Índice temporal informacional a partir de notícias corporativas

*Alvo: 00:40 (40 s) · ~90 palavras (voz+transição) · Fonte: Dissertação, capa e §1.3 — dissertacao_ppgcc.tex; chapters/01_introducao.tex*

**Objetivo:** Apresentar o trabalho e delimitar o estudo de caso da Sabesp.

**Fala:**

Boa tarde. Apresento minha proposta de qualificação sobre a construção de um Índice Temporal Informacional a partir de notícias corporativas. O estudo de caso é a Sabesp. A ideia é transformar notícias em português em um sinal acompanhado no tempo e investigar sua associação com retornos posteriores da ação. Vou mostrar como esse sinal é construído, o que os resultados preliminares permitem concluir e quais avaliações ainda faltam para a dissertação final.

**O que apontar:**

Ler o título; indicar Sabesp/SBSP3; não ler toda a identificação institucional.

**Na tela:**
- EXAME DE QUALIFICAÇÃO · PPGCC
- Índice temporal informacional
- a partir de notícias corporativas
- Uma proposta para empresas brasileiras de saneamento
- Estudo de caso: Sabesp / SBSP3
- Gabriel Felipe Souza Santos
- Orientador: Prof. Dr. Michel Carlo Rodrigues Leles
- 2026

**Transição:**

Para começar, precisamos resolver uma pergunta que vem antes de qualquer fórmula: uma notícia é positiva para quem?

## 02 — Uma notícia pode ter perspectivas diferentes

*Alvo: 00:55 (55 s) · ~113 palavras (voz+transição) · Fonte: Dissertação, introdução — chapters/01_introducao.tex*

**Objetivo:** Distinguir a perspectiva do consumidor da perspectiva da empresa.

**Fala:**

Imagine uma notícia sobre reajuste na tarifa de água. Este é um exemplo hipotético. Para quem paga a conta, o reajuste pode significar uma despesa maior. Para a concessionária, pode representar uma possibilidade de receita maior. O mesmo acontecimento, portanto, admite perspectivas diferentes. Isso ainda não nos diz qual será o lucro da empresa, nem como sua ação vai reagir. Antes dessas perguntas, precisamos definir o alvo da classificação: favorável ou desfavorável para quem? Neste trabalho, o alvo é a Sabesp. Essa definição orienta a leitura humana e a preparação dos textos que serão apresentados ao classificador.

**O que apontar:**

Apontar primeiro consumidor, depois Sabesp e, ao terminar, a frase sobre o alvo.

**Na tela:**
- Exemplo hipotético: reajuste da tarifa de água
- CONSUMIDOR
- Possível aumento
- da despesa
- SABESP
- Possibilidade de
- aumento de receita
- A classificação precisa declarar o alvo: Sabesp.

**Transição:**

Mesmo depois de definir esse alvo, existe outra dificuldade: as notícias chegam em ritmos muito diferentes.

## 03 — A publicação de notícias é irregular

*Alvo: 00:50 (50 s) · ~113 palavras (voz+transição) · Fonte: Dissertação, §4.2 — exemplo ilustrativo, não dados da campanha*

**Objetivo:** Mostrar a irregularidade e distinguir zero observado de cobertura comprovada.

**Fala:**

Observe esta semana ilustrativa: quatro notícias na segunda, nenhuma observada na terça, uma na quarta, cinco na quinta e nenhuma na sexta. Essas contagens servem apenas para explicar o problema; não são dados do experimento. A coleção de textos é irregular, mas queremos acompanhá-la em uma sequência diária. Para isso, precisamos definir como reunir várias notícias no mesmo dia e como tratar dias sem registros. Repare nos dois zeros: eles descrevem o que aparece no inventário. Não comprovam que todos os veículos foram consultados com sucesso ou que nenhuma notícia foi publicada. A regra matemática precisa conservar essa distinção na interpretação.

**O que apontar:**

Percorrer Seg–Sex; apontar os marcadores de zero e a nota de dados ilustrativos.

**Na tela:**
- Dia
- Notícias observadas
- Seg | 4
- Ter | 0
- Qua | 1
- Qui | 5
- Sex | 0
- DADOS
- ILUSTRATIVOS
- Zero observado não comprova ausência de publicação.
- Precisamos definir uma regra para cada dia elegível.

**Transição:**

Alvo e calendário, portanto, precisam ser examinados junto da qualidade da classificação.

## 04 — O problema combina alvo, classificação e tempo

*Alvo: 00:55 (55 s) · ~122 palavras (voz+transição) · Fonte: Dissertação, §1.1 e §3.5 — chapters/01_introducao.tex; 03_trabalhos_relacionados.tex*

**Objetivo:** Explicitar o problema e a lacuna de avaliação no estudo de caso.

**Fala:**

As dificuldades se organizam em três camadas. Na primeira, precisamos identificar o conteúdo referente à Sabesp. Na segunda, verificar se a classificação automática corresponde à tarefa que definimos. Na terceira, decidir quais notícias e quanto histórico entram na comparação temporal. Essas camadas dependem umas das outras: uma agregação bem programada pode resumir um sinal cujo significado ainda não foi validado. A lacuna que este estudo procura enfrentar é essa avaliação integrada, no caso da Sabesp: verificar a entrada contextual e tornar comparáveis as regras temporais. Não estamos dizendo que faltam classificadores ou médias exponenciais na literatura. Estamos perguntando o que sua combinação representa e como avaliá-la de maneira defensável.

**O que apontar:**

Percorrer as três colunas; terminar na faixa Lacuna no estudo de caso.

**Na tela:**
- 1 · ALVO
- Que informação se refere à Sabesp?
- 2 · CLASSIFICAÇÃO
- O modelo responde à tarefa definida?
- 3 · TEMPO
- Que histórico entra na comparação?
- Lacuna no estudo de caso: validar a entrada contextual e comparar agregações sob informação equivalente.

**Transição:**

Essa delimitação nos permite formular a pergunta de pesquisa e o contraste inicial.

## 05 — A hipótese compara associações, sem presumir superioridade

*Alvo: 01:10 (70 s) · ~145 palavras (voz+transição) · Fonte: Dissertação, §§1.1–1.3 e Eq. iti-delta (§4.5)*

**Objetivo:** Enunciar pergunta, hipótese bilateral e objetivo sem antecipar resultado.

**Fala:**

A pergunta é como a representação das notícias e sua agregação no tempo afetam o indicador e a interpretação de sua associação com retornos posteriores. O objetivo é desenvolver e avaliar um procedimento reprodutível para o caso da Sabesp. O contraste inicial compara duas associações. Usamos Spearman, uma medida que compara a ordenação dos valores: quando o indicador aumenta, os retornos tendem a ocupar posições maiores ou menores? Calculamos essa correlação para o ITI com memória de sete dias e subtraímos a correlação do Soft, nosso sinal sem memória, sempre com o retorno da semana seguinte. Essa diferença é delta rô. A hipótese é bilateral: investigamos uma diferença em qualquer direção, sem antecipar superioridade. Mais adiante explicarei a construção dos dois sinais e a incerteza desse contraste exploratório.

**O que apontar:**

Pergunta superior; primeiro termo da equação; segundo termo; hipótese bilateral e objetivo.

**Na tela:**
- Como a representação textual e a agregação temporal afetam o indicador e sua associação com retornos posteriores da SBSP3?
- Δρ = correlação do ITI-H7 − correlação do Soft
- Spearman: associação entre ordenações · R¹: retorno da semana seguinte
- Hipótese bilateral: Δρ diferente de zero
- Objetivo: desenvolver e avaliar um procedimento reprodutível no caso Sabesp.

**Transição:**

As peças dessa construção têm antecedentes claros na literatura; a contribuição está em sua integração e avaliação.

## 06 — A literatura sustenta três decisões do procedimento

*Alvo: 01:00 (60 s) · ~134 palavras (voz+transição) · Fonte: Dissertação, caps. 2–3; tabela posicionamento — referências completas em A08*

**Objetivo:** Vincular antecedentes a decisões específicas, sem atribuir-lhes H=7.

**Fala:**

Três conjuntos de trabalhos orientam as decisões. Santos e colaboradores apresentam recursos de linguagem financeira em português, que sustentam a escolha inicial do classificador. SemEval, SEntFiN e FinEntity mostram a importância de associar sentimento a uma entidade específica. Já Shapiro e colaboradores e o índice diário de sentimento de notícias do Federal Reserve de São Francisco fornecem antecedentes para transformar notícias em séries com persistência. A coluna da direita delimita o que não podemos transferir desses estudos: desempenho em outra base, treinamento específico para a Sabesp ou uma meia-vida ideal de sete dias. Nossa contribuição é documentar a combinação dessas escolhas e avaliar seus limites. Ela não depende de afirmar que uma fórmula conhecida ou uma arquitetura de linguagem foi inventada aqui.

**O que apontar:**

Ler as linhas da tabela da esquerda para a direita; enfatizar a coluna Limite apenas na terceira linha.

**Na tela:**
- Antecedente | Decisão apoiada | Limite
- FinBERT-PT-BR
- Santos et al. (2023) | Classificador financeiro
- em português | Adequação à Sabesp
- ainda precisa de avaliação
- SemEval · SEntFiN · FinEntity | Definir o alvo
- do sentimento | Recorte não equivale
- a treinamento por entidade
- Shapiro et al. (2022) · DNSI | Agregar notícias
- com persistência | Não determinam
- H = 7 para a Sabesp
- Contribuição: integração documentada e avaliação crítica no caso Sabesp.

**Transição:**

Com essas decisões delimitadas, podemos olhar para a coleção de notícias utilizada.

## 07 — A campanha temporal reúne 1.253 notícias canônicas

*Alvo: 00:55 (55 s) · ~131 palavras (voz+transição) · Fonte: Dissertação, §4.2; Apêndice B, tabela corpus-p02*

**Objetivo:** Apresentar composição e consolidação do corpus sem confundir cobertura e universo.

**Fala:**

A campanha temporal começou com mil duzentos e cinquenta e quatro registros. Depois da identificação de uma duplicata, ficaram mil duzentas e cinquenta e três notícias canônicas. As barras mostram sua distribuição entre cinco veículos. Money Times contribui com trezentas e sessenta notícias; as demais fontes são InfoMoney, Valor Econômico, G1 Economia e Exame. O período informacional abrange aproximadamente maio de dois mil e vinte e dois a abril de dois mil e vinte e quatro. Foram reportadas probabilidades contextuais válidas para as notícias dessa coleção. O ponto importante é que estamos descrevendo um corpus inventariado, com composição conhecida, e não todas as publicações sobre a Sabesp. A reprodução exata depende dos textos e das saídas efetivamente usados.

**O que apontar:**

Equação de consolidação; barra Money Times; cinco nomes; período e ressalva inferior.

**Na tela:**
- 1.254 registros brutos − 1 duplicata = 1.253 notícias canônicas
- Notícias
- Money Times | 360
- InfoMoney | 328
- Valor Econômico | 251
- G1 Economia | 203
- Exame | 111
- 5 veículos
- Maio/2022
- a abril/2024
- (aproximadamente)
- O corpus inventariado não equivale à totalidade das publicações.

**Transição:**

Essa base participa da avaliação temporal, que precisa ser distinguida do diagnóstico textual.

## 08 — Duas avaliações respondem a perguntas diferentes

*Alvo: 00:55 (55 s) · ~120 palavras (voz+transição) · Fonte: Dissertação, §4.1, figura pipeline; §§5.1–5.2*

**Objetivo:** Separar as unidades, entradas e saídas das avaliações textual e temporal.

**Fala:**

O procedimento tem duas frentes, com perguntas diferentes. À esquerda está o diagnóstico textual: cem notícias documentais, classes previstas e rótulos atribuídos pelo autor. A unidade de análise é a notícia, e a saída é uma medida de concordância. À direita está a avaliação temporal: textos recortados em torno da Sabesp geram probabilidades, escores e indicadores, que depois são relacionados aos retornos da ação. Nessa avaliação, a unidade é a semana. As frentes são complementares, mas uma não substitui a outra. Os rótulos humanos não foram usados para treinar o modelo nem para corrigir automaticamente o ITI nesta campanha. Essa separação será importante quando interpretarmos a acurácia e as correlações.

**O que apontar:**

Ramo esquerdo ao falar em notícia; ramo direito ao falar em semana; nota inferior ao mencionar treinamento.

**Na tela:**
- Notícias relacionadas à Sabesp
- DIAGNÓSTICO TEXTUAL
- 100 notícias documentais
- Classes previstas × rótulos do autor
- Saída: concordância por notícia
- AVALIAÇÃO TEMPORAL
- Recorte Sabesp → probabilidades
- Escores → indicadores → retornos
- Saída: associação por semana
- Rótulos humanos não treinaram nem corrigiram automaticamente o ITI.

**Transição:**

Vou começar pela entrada textual utilizada na construção do índice.

## 09 — O recorte aproxima a entrada da menção à Sabesp

*Alvo: 00:55 (55 s) · ~126 palavras (voz+transição) · Fonte: Dissertação, §4.4 — sec:classificador-operacional*

**Objetivo:** Mostrar exatamente a regra contextual e seu limite.

**Fala:**

Para o ITI, a implementação procura sentenças que mencionam explicitamente a Sabesp. Quando disponíveis, inclui também uma sentença anterior e uma posterior. O esquema mostra posições de sentenças, não uma notícia real: a faixa central destaca a menção e suas vizinhas. Se houver várias menções, os trechos selecionados são reunidos em uma entrada contextual. A intenção é reduzir a influência de assuntos que não dizem respeito à empresa. Mas o recorte pode perder contexto ou preservar ambiguidades. Ele também não transforma o classificador em um modelo treinado especificamente para avaliar o par notícia e Sabesp. Essa preparação faz parte do procedimento; sua adequação ainda precisa ser medida com uma referência humana sobre as entradas efetivamente utilizadas.

**O que apontar:**

Linha Menção explícita; vizinhas anterior e posterior; seta para Entrada contextual.

**Na tela:**
- ESQUEMA ILUSTRATIVO · posições de sentenças, não uma notícia real
- Posição | Tratamento
- Anterior distante | Não selecionada neste esquema
- Vizinha anterior | Selecionada, quando disponível
- Menção explícita à Sabesp | Selecionada
- Vizinha posterior | Selecionada, quando disponível
- Posterior distante | Não selecionada neste esquema
- Entrada contextual
- 
- Reunir os trechos selecionados nas menções encontradas.
- Preparação da entrada não equivale a treinamento por entidade.

**Transição:**

Uma vez preparada a entrada, o classificador produz três probabilidades.

## 10 — O FinBERT atribui probabilidades a três classes

*Alvo: 00:55 (55 s) · ~126 palavras (voz+transição) · Fonte: Dissertação, §§2.2–2.3 e §4.4; Santos et al. (2023)*

**Objetivo:** Explicar a saída probabilística sem confundi-la com retorno ou acerto calibrado.

**Fala:**

O FinBERT é um classificador de linguagem aplicado aqui ao domínio financeiro em português. Ele recebe o texto e atribui probabilidades a três classes: positiva, negativa e neutra. Na barra ilustrativa, sessenta por cento foram atribuídos à positiva, dez à negativa e trinta à neutra. As parcelas somam cem por cento. Probabilidade, aqui, descreve a distribuição produzida pelo modelo entre as classes; não é uma chance de valorização da ação nem uma garantia de acerto. A entrada aceita até quinhentos e doze tokens, unidades que podem ser palavras ou partes de palavras. Textos maiores podem ser truncados. Por isso, precisamos registrar não apenas o nome do modelo, mas também qual texto ele efetivamente recebeu.

**O que apontar:**

Segmentos e legenda na ordem positiva, negativa, neutra; soma; limite de tokens.

**Na tela:**
- FinBERT-PT-BR · classificador financeiro em português
- Probabilidade atribuída pelo modelo
- Positiva · p⁺ | 0,6
- Negativa · p⁻ | 0,1
- Neutra · p⁰ | 0,3
- Positiva: 0,60
- Negativa: 0,10
- Neutra: 0,30
- As três probabilidades somam 1
- Entrada: até 512 tokens
- Exemplo ilustrativo · probabilidades de classes, não de valorização.

**Transição:**

Para construir a série, resumimos essas probabilidades em um escore por notícia.

## 11 — O escore resume o balanço entre positivo e negativo

*Alvo: 01:15 (75 s) · ~138 palavras (voz+transição) · Fonte: Dissertação, §4.5, Eq. iti-escore; §2.3 e Apêndice C*

**Objetivo:** Derivar e interpretar o escore da notícia.

**Fala:**

O escore da notícia é a probabilidade positiva menos a negativa. A letra i identifica cada notícia. No exemplo que acabamos de ver, zero vírgula sessenta menos zero vírgula dez resulta em mais zero vírgula cinquenta. A escala à direita vai de menos um a mais um. O sinal positivo indica que a probabilidade positiva superou a negativa na saída do modelo; não representa um retorno de cinquenta por cento. Há uma perda de informação nesse resumo. Um escore zero pode ocorrer porque a classe neutra domina, mas também porque as probabilidades positiva e negativa se equilibram. São situações diferentes que chegam ao mesmo número. Por isso, preservar as três probabilidades é importante para inspecionar o sinal, mesmo quando a agregação utiliza apenas o escore.

**O que apontar:**

Regra à esquerda; conta à direita; posição +0,50 na escala; nota sobre zero.

**Na tela:**
- sᵢ = pᵢ⁺ − pᵢ⁻
- i: notícia
- sᵢ: escore da notícia
- pᵢ⁺ e pᵢ⁻: probabilidades positiva e negativa
- 0,60 − 0,10 = +0,50
- Escore · sem unidade
- 0,5
- Exemplo ilustrativo · escore zero não identifica sozinho a classe neutra.

**Transição:**

O próximo passo é reunir os escores das notícias observadas em cada dia.

## 12 — A entrada diária é a média dos escores observados

*Alvo: 01:15 (75 s) · ~139 palavras (voz+transição) · Fonte: Dissertação, §4.5, Eq. iti-entrada-diaria; Apêndice C*

**Objetivo:** Definir média diária, conjunto de notícias e política de ausências.

**Fala:**

Em cada dia civil elegível, calculamos a média dos escores observados. A letra d indica o dia, n indica quantas notícias foram observadas e o conjunto N reúne essas notícias. No exemplo, os três escores são mais zero vírgula cinquenta, menos zero vírgula vinte e mais zero vírgula dez. A soma é zero vírgula quarenta; dividindo por três, obtemos aproximadamente zero vírgula treze três três. Cada notícia recebe o mesmo peso, sem ponderação por audiência ou importância econômica. Se o dia é elegível e não há matéria observada, a entrada é zero. Fora da cobertura delimitada, não criamos um sinal. São regras diferentes. Dentro do inventário, o zero ainda pode esconder falhas de coleta; ele não comprova que o noticiário tenha sido neutro.

**O que apontar:**

Fórmula; glossário; numerador e denominador; duas regras de ausência à direita.

**Na tela:**
- X_d = soma dos escores do dia dividida por n_d, quando n_d > 0
- d: dia civil · X_d: entrada diária
- N_d: notícias elegíveis observadas no dia
- n_d: quantidade dessas notícias
- sᵢ: escore de cada notícia
- Exemplo: (0,50 − 0,20 + 0,10) / 3 ≈ 0,1333
- Dia elegível sem notícia: X_d = 0
- Fora da cobertura: não criar sinal
- Exemplo ilustrativo · pesos iguais; zero não comprova neutralidade.

**Transição:**

A partir dessa mesma entrada diária, podemos observar só o presente ou conservar parte do passado.

## 13 — Soft observa o dia; ITI conserva parte do histórico

*Alvo: 01:00 (60 s) · ~125 palavras (voz+transição) · Fonte: Dissertação, §4.5 — indicadores de referência*

**Objetivo:** Introduzir o ITI e o baseline Soft por suas operações.

**Fala:**

O Soft é o sinal diário sem memória. Na comparação semanal, observamos a entrada do dia de corte. Se esse dia não tem notícia observada, o Soft vale zero, mesmo que tenham ocorrido publicações antes. Ele funciona como baseline, isto é, uma referência simples para a comparação. O Índice Temporal Informacional, ou ITI, acrescenta um estado que carrega contribuições anteriores. A cada dia, uma parte desse estado é conservada e outra parte vem da entrada atual. Sem entrada nova, o estado decai, mas não precisa zerar imediatamente. Essa é uma memória definida por uma regra matemática. Não estamos medindo diretamente quanto tempo os investidores se lembram de uma notícia ou quanto dura seu efeito econômico.

**O que apontar:**

Coluna Soft; coluna ITI; seta de continuidade do estado; ressalva inferior.

**Na tela:**
- SOFT · SEM MEMÓRIA
- Entrada diária no corte
- 
- Sem notícia nesse dia: zero
- ITI · COM MEMÓRIA
- Estado anterior + entrada diária
- 
- Sem entrada: o estado decai
- O estado segue para o dia seguinte
- Memória do indicador não é memória comprovada dos investidores.

**Transição:**

Precisamos, então, definir de forma interpretável a velocidade desse decaimento.

## 14 — Sete dias definem a meia-vida, não um ótimo

*Alvo: 01:25 (85 s) · ~148 palavras (voz+transição) · Fonte: Dissertação, §4.5, Eqs. iti-lambda e iti-recorrencia; Apêndice C*

**Objetivo:** Explicar a recorrência correta e a meia-vida em dias civis.

**Fala:**

A meia-vida, representada por H, informa quantos dias civis são necessários para reduzir à metade a contribuição remanescente de um estado, quando não chegam novas entradas. Para obter essa propriedade, calculamos lambda como dois elevado a menos um dividido por H. Com sete dias, lambda vale aproximadamente zero vírgula nove zero cinco sete. Observe agora os dois termos da atualização: o estado de ontem é multiplicado por lambda, e a entrada de hoje é multiplicada por um menos lambda. Assim, conservamos aproximadamente noventa vírgula cinquenta e sete por cento do estado anterior e incorporamos nove vírgula quarenta e três por cento da entrada atual. Os pesos somam um. Sete dias é a configuração principal, escolhida para investigar uma escala semanal; não é um parâmetro ótimo demonstrado nem uma constante de reação do mercado.

**O que apontar:**

H=7; fator lambda; dois termos da recorrência; pesos e definição inferior de meia-vida.

**Na tela:**
- λ_H = 2^(−1/H); H = 7 → λ₇ ≈ 0,9057
- ITI_d = λ_H ITI_(d−1) + (1−λ_H) X_d
- H: meia-vida em dias civis
- λ_H: fração diária retida
- ITI_(d−1): estado anterior · X_d: entrada atual
- 90,57% do estado anterior
- 9,43% da entrada atual
- Sem novas entradas: metade do estado remanescente após 7 dias.

**Transição:**

Vamos aplicar esses dois pesos a uma conta simples para enxergar o movimento do índice.

## 15 — Uma atualização leva o ITI de 0,20 a 0,2283

*Alvo: 01:15 (75 s) · ~148 palavras (voz+transição) · Fonte: Dissertação, §4.5 — exemplo ilustrativo da recorrência*

**Objetivo:** Decompor um passo da atualização em duas parcelas e uma soma.

**Fala:**

Esta conta é uma simulação didática, não um dia observado da Sabesp. Suponha que o estado anterior seja zero vírgula vinte e que a entrada diária atual seja zero vírgula cinquenta. Primeiro, multiplicamos o estado anterior por zero vírgula nove zero cinco sete. Isso produz aproximadamente zero vírgula um oito um um. Na outra parcela, multiplicamos a entrada de hoje por zero vírgula zero nove quatro três, obtendo aproximadamente zero vírgula zero quatro sete dois. Somando as parcelas, o novo ITI chega a zero vírgula dois dois oito três. Repare que ele aumentou, mas permaneceu entre o estado anterior e a entrada atual. A conta torna concreta a ideia de memória: o sinal novo altera o índice sem substituir integralmente o histórico. Se a próxima entrada for zero, permanece apenas a parcela de retenção.

**O que apontar:**

Dados superiores; parcela esquerda; parcela direita; soma inferior; pausa de leitura na soma.

**Na tela:**
- SIMULAÇÃO DIDÁTICA · estado anterior 0,20 · entrada atual 0,50
- 0,9057 × 0,20 ≈ 0,1811
- Contribuição do estado anterior
- 0,0943 × 0,50 ≈ 0,0472
- Contribuição da entrada atual
- Novo ITI ≈ 0,1811 + 0,0472 = 0,2283

**Transição:**

Esse histórico é justamente o que precisamos considerar ao escolher as referências de comparação.

## 16 — As referências usam históricos e pesos diferentes

*Alvo: 01:10 (70 s) · ~141 palavras (voz+transição) · Fonte: Dissertação, §4.5, tabela baselines-temporais*

**Objetivo:** Comparar os três indicadores e explicitar o confundimento entre janela e ponderação.

**Fala:**

As três referências partem das mesmas probabilidades contextuais, mas usam o tempo de maneiras diferentes. O Soft pontual considera a entrada do dia de corte. A média semanal reúne os sinais diários desde o sábado da janela até esse corte e atribui peso igual a cada dia elegível, inclusive àqueles com entrada zero. Ela não é a média direta de todas as notícias da semana. O ITI com meia-vida de sete dias conserva contribuições anteriores, inclusive de outras semanas, com pesos decrescentes. Portanto, dois fatores mudam entre as referências: a extensão do histórico e a forma de ponderá-lo. Uma diferença de correlação não pode ser atribuída exclusivamente aos pesos exponenciais. Para isolar esse efeito, o experimento futuro terá de usar exatamente os mesmos dias, escores e corte.

**O que apontar:**

Cada linha da tabela; sábado até corte; histórico anterior do ITI; mensagem inferior.

**Na tela:**
- Indicador | Informação considerada | Ponderação
- Soft pontual | Entrada do dia de corte | Sem histórico
- Média semanal | Sábado até o corte
- Dias elegíveis, inclusive zeros | Mesmo peso por dia
- ITI-H7 | Até o corte, incluindo
- semanas anteriores | Memória exponencial
- Mesmas probabilidades de origem; janelas de informação não idênticas.

**Transição:**

O corte informacional também precisa ser definido antes de olhar para o retorno financeiro.

## 17 — O corte textual antecede o último pregão

*Alvo: 01:05 (65 s) · ~135 palavras (voz+transição) · Fonte: Dissertação, §4.6, Eq. iti-retorno*

**Objetivo:** Explicar corte informacional e retorno futuro sem antecipação.

**Fala:**

Em cada semana, identificamos o último pregão e limitamos as notícias ao fim do dia civil anterior. O exemplo mostra uma semana comum: corte na quinta à noite, fechamento financeiro na sexta e fechamento futuro na semana seguinte. O retorno é o logaritmo da razão entre esses dois preços ajustados. Assim, a janela de retorno começa depois do corte textual. Se a sexta-feira for feriado e o último pregão ocorrer na quinta, o corte recua para a quarta à noite. Essa regra é conservadora: deixa de incorporar notícias do próprio último pregão. Ela reduz o risco de usar informação futura, mas não reconstitui horários de publicação que não foram preservados. O retorno vem dos preços da SBSP3; não é uma saída do classificador.

**O que apontar:**

Corte; P_w; P_(w+1); fórmula; caso de feriado.

**Na tela:**
- Corte: fim do dia civil anterior ao último pregão da semana
- QUINTA · noite
- Sinal textual no corte
- SEXTA · semana w
- Fechamento ajustado P_w
- SEMANA w+1
- Fechamento P_(w+1)
- R_w¹ = ln(P_(w+1) / P_w)
- Sexta feriado?
- Último pregão na quinta;
- corte na quarta à noite.
- Exemplo de calendário · w: semana · R: retorno logarítmico futuro

**Transição:**

Com a construção temporal definida, podemos examinar o diagnóstico da classificação textual.

## 18 — Cem notícias formam um diagnóstico exploratório

*Alvo: 01:00 (60 s) · ~131 palavras (voz+transição) · Fonte: Dissertação, §4.3 e §5.1.1 — protocolo de 07/10/2026*

**Objetivo:** Descrever seleção, referência humana e conteúdo documental da amostra.

**Fala:**

O diagnóstico utiliza cem notícias relacionadas à Sabesp. Elas foram selecionadas com apoio nas classes previstas pelo modelo, para permitir a inspeção de diferentes casos. Portanto, não constituem uma amostra aleatória do corpus temporal. Os rótulos de referência foram atribuídos por mim, segundo o protocolo de sete de outubro de dois mil e vinte e seis. Essa referência individual é provisória; ainda não representa consenso de anotadores independentes. O conteúdo disponível também varia: em quinze registros, o campo de conteúdo apenas repete o título. Nos demais, existe texto distinto, mas isso não permite reconstruir integralmente a entrada tokenizada da inferência original. Esses limites acompanham todas as métricas seguintes, que descrevem os cem pares de classes preservados.

**O que apontar:**

100; linhas Seleção e Referência; número 15; Validação independente pendente.

**Na tela:**
- 100
- notícias
- documentais
- Aspecto | Condição
- Seleção | Não aleatória; apoiada em classes previstas
- Referência | Autor · protocolo de 07/10/2026
- Conteúdo | Em 15 registros, repete o título
- Validação independente | Ainda pendente
- As métricas descrevem esta amostra; não estimam todo o corpus temporal.

**Transição:**

A matriz de confusão permite ver esses pares sem esconder as diferenças entre as classes.

## 19 — A matriz revela os padrões de discordância

*Alvo: 01:15 (75 s) · ~138 palavras (voz+transição) · Fonte: Dissertação, §5.1.1, tabela confusao-100*

**Objetivo:** Mostrar todos os pares autor/modelo e o padrão entre neutras.

**Fala:**

Cada linha corresponde ao rótulo do autor e cada coluna à previsão do modelo. Os acertos em relação à referência estão na diagonal: treze negativas, trinta e duas neutras e cinco positivas, somando cinquenta notícias. Observe agora a linha neutra. Além das trinta e duas concordâncias, vinte e uma notícias foram previstas como negativas e catorze como positivas. São trinta e cinco casos em que a referência neutra recebeu uma previsão com polaridade. Na última linha, cinco das dezenove positivas foram identificadas como positivas; as outras se distribuíram entre negativa e neutra. A matriz mostra padrões que um percentual geral esconderia. Ainda assim, desacordo não prova automaticamente erro do modelo: a referência é individual, e textos ambíguos podem exigir revisão do próprio julgamento humano.

**O que apontar:**

Cabeçalhos autor/modelo; diagonal 13/32/5; células 21 e 14; última linha 4/10/5.

**Na tela:**
- Linhas: autor · Colunas: modelo · Unidade: notícia
- Autor / Modelo | Negativa | Neutra | Positiva
- Negativa | 13 | 1 | 0
- Neutra | 21 | 32 | 14
- Positiva | 4 | 10 | 5
- 50 / 100
- na diagonal
- 35 neutras
- receberam polaridade
- 21 + 14
- Desacordo com a referência individual não é prova isolada de erro do modelo.

**Transição:**

Podemos resumir esses padrões em métricas, desde que não percamos a distribuição das classes.

## 20 — Acurácia isolada favorece a classe majoritária

*Alvo: 01:05 (65 s) · ~152 palavras (voz+transição) · Fonte: Dissertação, §5.1.1, tabelas avaliacao-texto e metricas-classe-100*

**Objetivo:** Comparar a acurácia com a regra trivial e mostrar F1 por classe.

**Fala:**

A acurácia de cinquenta por cento significa concordância em cinquenta dos cem casos. Compare as duas barras: prever sempre neutro alcançaria sessenta e sete por cento nesta amostra, porque essa é a classe majoritária. Isso não torna a regra trivial um bom classificador das três classes; ela não reconhece nenhum exemplo positivo ou negativo. O F1 combina precisão e revocação, isto é, a qualidade das previsões de uma classe e a capacidade de recuperar seus exemplos. O F1 macro faz a média dando o mesmo peso às três classes; aqui, vale zero vírgula quatro quatro oito. O kappa, zero vírgula um nove sete, considera também a concordância esperada pelas frequências das classes. A tabela mostra a dificuldade especial na classe positiva. O diagnóstico pede revisão da tarefa e da referência, não apenas um percentual maior.

**O que apontar:**

Barras de 50 e 67; distribuição 14/67/19; F1 positivo; macro e kappa.

**Na tela:**
- Acurácia (%)
- FinBERT | 50
- Sempre neutro | 67
- Classe | Referência | F1
- Negativa | 14 | 0,500
- Neutra | 67 | 0,582
- Positiva | 19 | 0,263
- F1 macro: 0,448 · Kappa: 0,197
- Sempre prever neutro acerta 67 casos, mas não reconhece as outras classes.

**Transição:**

Existe, porém, um limite ainda mais importante: essas métricas não avaliaram a mesma entrada usada pelo ITI.

## 21 — O diagnóstico documental não valida o recorte do ITI

*Alvo: 01:00 (60 s) · ~129 palavras (voz+transição) · Fonte: Dissertação, §4.4 e §5.1.2*

**Objetivo:** Separar a evidência existente da validação contextual pendente.

**Fala:**

Os cinquenta por cento se referem à representação documental preservada, formada por título e conteúdo disponível. O ITI foi construído com recortes próximos às menções à Sabesp. Mesmo quando a notícia de origem é a mesma, entradas diferentes podem produzir saídas diferentes, inclusive por efeitos de truncamento. Portanto, não podemos chamar esse percentual de acurácia do ITI, nem transferi-lo automaticamente para suas probabilidades contextuais. Também não seria correto presumir que o recorte melhora o desempenho apenas porque parece mais focado. A avaliação necessária deve usar as mesmas notícias, comparar as duas representações e conservar as entradas e saídas efetivas. Uma referência independente e uma tarefa de anotação constante permitirão interpretar as diferenças com muito mais segurança.

**O que apontar:**

Comparar os dois títulos e representações; 50% apenas à esquerda; pendência apenas à direita.

**Na tela:**
- AVALIADO
- Título + conteúdo disponível
- 100 pares de classes
- Concordância: 50%
- UTILIZADO NO ITI
- Trechos próximos à Sabesp
- Probabilidades contextuais
- Validação independente pendente
- Próxima avaliação: mesmas notícias, duas entradas e referência independente.

**Transição:**

Essa ressalva acompanha a leitura das séries temporais que o procedimento já produziu.

## 22 — As séries mostram a persistência produzida pelo ITI

*Alvo: 00:55 (55 s) · ~127 palavras (voz+transição) · Fonte: Dissertação, §5.2.3, figura iti-campanha-1 — asset figura_2_soft_iti_noticias.png*

**Objetivo:** Interpretar as séries observadas sem transformar suavidade em capacidade preditiva.

**Fala:**

Estas são séries observadas na campanha, não uma simulação. No painel superior, a linha azul representa o Soft diário e a laranja, o ITI com meia-vida de sete dias. O painel inferior mostra a quantidade de notícias elegíveis observadas. Repare como o Soft apresenta variações rápidas, enquanto o ITI conserva parte do histórico e responde de maneira mais gradual. Esse comportamento é compatível com a regra que acabamos de calcular. Ele demonstra uma propriedade da transformação temporal, mas a linha mais suave não é, por isso, mais útil para explicar preços ou prever retornos. Para investigar a associação financeira, precisamos observar os sinais nos mesmos cortes semanais e examinar a diferença com sua incerteza.

**O que apontar:**

Legenda; linhas azul e laranja; barras inferiores; não atribuir movimentos a eventos não identificados na fonte.

**Na tela:**
- Soft diário: azul · ITI-H7 diário: laranja
- Séries empíricas Soft e ITI-H7; eixo vertical: sinal; eixo horizontal: data.
- Contagem empírica de notícias por dia; eixo horizontal: data.
- Séries observadas · suavidade não demonstra capacidade preditiva.

**Transição:**

No contraste principal, essa comparação utiliza noventa e quatro semanas após o aquecimento.

## 23 — O ITI tem correlação de menor magnitude absoluta

*Alvo: 01:15 (75 s) · ~142 palavras (voz+transição) · Fonte: Dissertação, §5.2.1, tabela iti-primary*

**Objetivo:** Interpretar o sinal e a magnitude das duas correlações e sua diferença.

**Fala:**

O painel alinhado tem cento e quatro semanas. Excluindo dez semanas iniciais de aquecimento, restam noventa e quatro para o contraste principal. A correlação de Spearman do Soft com o retorno da semana seguinte é menos zero vírgula duzentos e três. Para o ITI, é menos zero vírgula cento e sessenta e três. As duas são negativas e de magnitude relativamente pequena. Observe a posição dos pontos: o ITI está mais perto do zero. Ao subtrair a correlação do Soft da correlação do ITI, a diferença é mais zero vírgula zero quarenta. Esse delta é positivo porque menos zero vírgula cento e sessenta e três é numericamente maior. Mas sua magnitude absoluta é menor. Portanto, não podemos apresentar o resultado como correlação mais forte, superioridade ou ganho de previsão.

**O que apontar:**

Contagem 104−10; ponto Soft; ponto ITI; linha zero; subtração e interpretação.

**Na tela:**
- 104 semanas alinhadas − 10 de aquecimento = 94 semanas
- Correlação de Spearman com o retorno da semana seguinte
- Soft | -0,203
- ITI-H7 | -0,163
- Δρ = (−0,163) − (−0,203) = +0,040
- Mais próximo de zero = menor magnitude absoluta.

**Transição:**

E uma diferença observada ainda precisa ser acompanhada por uma estimativa de incerteza.

## 24 — O intervalo da diferença atravessa zero

*Alvo: 01:30 (90 s) · ~157 palavras (voz+transição) · Fonte: Dissertação, §4.5 e §5.2.1, tabela iti-primary*

**Objetivo:** Mostrar a incerteza do contraste e o caráter exploratório da inferência.

**Fala:**

Bootstrap é um procedimento que reamostra os dados para examinar a variabilidade de uma estimativa. Como semanas próximas podem ser dependentes, reamostramos blocos contíguos de quatro semanas. Em cada repetição, ITI, Soft e retorno permanecem emparelhados. Foram dez mil reamostragens. O ponto marca a diferença observada de mais zero vírgula zero quarenta. A linha vai de menos zero vírgula cento e vinte e sete a mais zero vírgula duzentos e quarenta e um: é o intervalo bootstrap nominal de noventa e cinco por cento. Observe que ele atravessa zero e admite diferenças nos dois sentidos. A comparação permanece inconclusiva; isso não prova equivalência entre os indicadores. O valor p é zero vírgula quinhentos e doze e deve ser lido como exploratório. O procedimento não construiu explicitamente uma distribuição sob a hipótese nula, de modo que não apresentamos esse número como teste confirmatório calibrado.

**O que apontar:**

Ponto +0,040; limite esquerdo; limite direito; travessia do zero; nota p exploratório.

**Na tela:**
- Bootstrap em blocos: 4 semanas · 10.000 reamostragens pareadas
- Diferença assinada de correlações (Δρ)
- IC bootstrap nominal de 95%
- 0,04 | -0,127 | 0,241 | ITI-H7 − Soft
- p exploratório = 0,512 · sem distribuição nula explicitamente construída
- Resultado inconclusivo: não demonstra superioridade nem equivalência.

**Transição:**

Além da incerteza, a comparação revelou uma diferença concreta na informação conservada pelo Soft.

## 25 — Zero no corte não significa uma semana sem notícias

*Alvo: 01:05 (65 s) · ~141 palavras (voz+transição) · Fonte: Dissertação, §5.2.4, tabela contrastes-baselines*

**Objetivo:** Mostrar a perda de histórico do Soft e o contraste complementar.

**Fala:**

Em trinta e seis das noventa e quatro semanas, o Soft era zero no dia de corte. Em trinta e três dessas trinta e seis, porém, havia notícia anterior dentro da janela semanal. O zero, portanto, frequentemente descreve só aquele dia, enquanto o ITI ainda conserva contribuições próximas. Por isso, examinamos também a média semanal, que reúne as entradas diárias até o corte. A diferença entre ITI e essa referência foi menos zero vírgula zero sessenta e dois. O intervalo vai de menos zero vírgula cento e sessenta e cinco a mais zero vírgula zero sessenta e também atravessa zero; o p exploratório é zero vírgula trezentos e quarenta. O contraste é inconclusivo e não isola os pesos, porque o ITI pode carregar história anterior à semana.

**O que apontar:**

36/94; 33 dentro das 36; contraste complementar; intervalo atravessando zero.

**Na tela:**
- 36 de 94 semanas
- com Soft = 0 no corte
- Em 33 dessas 36, havia notícia anterior na janela semanal.
- ITI-H7 − média semanal
- Δρ · IC nominal de 95%
- -0,062 | -0,165 | 0,06 | Δρ
- p exploratório = 0,340
- Comparação complementar ainda muda janela e pesos ao mesmo tempo.

**Transição:**

Também examinamos o que acontece com a série quando mudamos a duração dessa memória.

## 26 — A meia-vida controla a velocidade de resposta

*Alvo: 00:50 (50 s) · ~123 palavras (voz+transição) · Fonte: Dissertação, §5.2.3, figura iti-campanha-2 — asset figura_3_meias_vidas.png*

**Objetivo:** Interpretar H=2,7,14 como sensibilidade, sem seleção de ótimo.

**Fala:**

As três séries foram calculadas a partir das mesmas probabilidades, mudando a meia-vida. A linha azul contínua usa dois dias e responde mais rapidamente às entradas. A laranja tracejada usa sete dias, nossa configuração principal. A verde pontilhada usa quatorze dias e conserva o histórico por mais tempo. O gráfico mostra o ITI observado nos cortes semanais, embora sua atualização aconteça diariamente. Essas diferenças são coerentes com a regra matemática. Não constituem uma competição visual para escolher a curva mais suave. Sete dias foi adotado para investigar uma escala próxima de uma semana civil, e não porque tenha sido encontrado como ótimo nos resultados. A sensibilidade ajuda a delimitar o próximo experimento.

**O que apontar:**

Legenda por cor e padrão; oscilações mais rápidas de H2; H7; H14; ressalva inferior.

**Na tela:**
- H=2: azul contínuo · H=7: laranja tracejado · H=14: verde pontilhado
- Séries empíricas ITI-H2, ITI-H7 e ITI-H14 observadas no corte semanal; eixos: ITI no corte e data.
- H=7 é a configuração principal; não foi demonstrado como ótimo.

**Transição:**

Com isso, podemos reunir as limitações que precisam orientar a continuidade.

## 27 — As limitações definem o próximo experimento

*Alvo: 01:00 (60 s) · ~124 palavras (voz+transição) · Fonte: Dissertação, §5.3, tabela ameacas*

**Objetivo:** Conectar cada ameaça a uma consequência e uma providência.

**Fala:**

As limitações apontam o que precisa ser feito, e não apenas o que falta mencionar na defesa. Primeiro, o construto: precisamos avaliar a entrada contextual com referência independente. Segundo, a comparabilidade: as referências atuais mudam histórico e pesos ao mesmo tempo. Terceiro, cobertura e reprodução: é necessário documentar lacunas e reunir as versões exatas dos textos, probabilidades e preços. Por fim, a inferência está restrita a noventa e quatro semanas e ao caso da Sabesp. Mudanças regulatórias, societárias e fatores gerais de mercado não foram isolados pela análise. Isso limita qualquer interpretação causal ou generalização. O encaminhamento é um protocolo mais controlado e uma avaliação em período novo, preservando também resultados que permaneçam inconclusivos.

**O que apontar:**

Ler dimensão e encaminhamento de cada linha; terminar na restrição de escopo.

**Na tela:**
- Dimensão | Limitação | Encaminhamento
- Construto | Recorte sem referência independente | Avaliar as duas entradas
- Comparabilidade | Histórico e pesos variam juntos | Fixar a janela; variar pesos
- Cobertura e reprodução | Lacunas e versões incompletas | Preservar dados e registros
- Inferência e escopo | 94 semanas; caso Sabesp | Protocolo fixo e período novo
- Associação exploratória não demonstra previsão, causalidade ou generalização.

**Transição:**

O plano de continuidade organiza essas providências em cinco etapas.

## 28 — Cinco etapas para consolidar a dissertação

*Alvo: 00:55 (55 s) · ~122 palavras (voz+transição) · Fonte: Dissertação, §6.2, tabela plano-continuidade*

**Objetivo:** Apresentar sequência de produtos e critérios de conclusão, não promessa de significância.

**Fala:**

O plano é indicativo e organiza cinco meses após a qualificação. No primeiro, documentar corpus, versões e cobertura. No segundo, obter rótulos independentes e avaliar as duas entradas textuais nos mesmos itens. No terceiro, construir agregações com janela e corte iguais, variando apenas os pesos. No quarto, aplicar um protocolo fixado previamente a um período ainda não examinado. A reserva temporal já analisada não volta a ser um teste inédito só porque recebe outro nome. No quinto, consolidar a dissertação e preparar o artigo com o orientador. Os produtos esperados são dados rastreáveis, avaliações bem definidas e conclusões proporcionais à evidência. O cumprimento do plano não depende de encontrar significância estatística.

**O que apontar:**

Percorrer os cinco meses; destacar período novo no mês 4; nota final.

**Na tela:**
- MÊS 1
- MÊS 2
- MÊS 3
- MÊS 4
- MÊS 5
- Corpus
- Versões e
- cobertura
- Validação
- Duas entradas;
- rótulos
- independentes
- Controle
- Mesma janela;
- pesos distintos
- Teste
- Período novo;
- protocolo fixo
- Síntese
- Dissertação
- e artigo
- Prazos indicativos após a qualificação; conclusão não depende de significância.

**Transição:**

A contribuição desta qualificação pode, então, ser resumida em três pontos.

## 29 — Procedimento implementado; validação em continuidade

*Alvo: 00:35 (35 s) · ~78 palavras (voz+transição) · Fonte: Dissertação, §6.1 — chapters/07_consideracoes_finais.tex*

**Objetivo:** Encerrar com contribuição, evidência e próximo passo claramente separados.

**Fala:**

Esta qualificação entrega um procedimento implementado e inspecionável para transformar notícias em uma série temporal. O diagnóstico identificou limitações textuais, e os contrastes financeiros permaneceram inconclusivos. A contribuição está também em mostrar quais controles faltam para interpretar melhor essas comparações. A continuidade prioriza validar as entradas do índice e comparar pesos sob a mesma janela de informação. Esse é o caminho proposto para consolidar a dissertação.

**O que apontar:**

Três linhas implementado/evidência/continuidade; manter a tela durante as perguntas.

**Na tela:**
- IMPLEMENTADO
- Notícias → probabilidades → escores → ITI → alinhamento
- EVIDÊNCIA
- Diagnóstico textual e contrastes temporais exploratórios
- CONTINUIDADE
- Validar entradas e comparar pesos sob a mesma janela
- Obrigado. Perguntas e contribuições da banca são bem-vindas.

**Transição:**

Muito obrigado; fico à disposição para as perguntas e contribuições da banca.

## Slides de apoio (fora dos 30 min)

Material de reserva para perguntas; não compõe o tempo-alvo da qualificação.

## A01 — Ficha técnica da campanha temporal

*Fonte: Dissertação, §4.4–4.7; Apêndice B, tabela rastreabilidade*

**Objetivo:** Responder sobre configurações e condições de reprodução.

**Fala:**

Esta ficha reúne a configuração reportada pela campanha. O classificador é identificado como lucas-leme, FinBERT-PT-BR, com entrada contextual e limite de quinhentos e doze tokens. O ITI é atualizado em dias civis, e o contraste principal usa noventa e quatro semanas depois do aquecimento. Para repetir exatamente os resultados, não basta conhecer esses nomes e parâmetros: também precisamos das versões dos textos, probabilidades, pesos do modelo, tokenizador e preços ajustados efetivamente utilizados. A documentação do procedimento não deve ser confundida com reprodução numérica independente já concluída.

**O que apontar:**

Linha correspondente à pergunta da banca; encerrar no limite de reprodução, sem ler a tabela inteira.

**Na tela:**
- Parâmetro | Registro
- Caso e período | Sabesp / SBSP3 · maio/2022 a abril/2024
- Corpus | 1.253 notícias canônicas · 5 fontes
- Classificador | lucas-leme/FinBERT-PT-BR · limite: 512 tokens
- Entrada temporal | Menção à Sabesp e até 1 vizinha por lado
- Meia-vida | 7 dias civis; sensibilidades: 2 e 14
- Aquecimento e painel | 70 dias · 104 semanas alinhadas · 94 no contraste
- Reamostragem | 10.000 réplicas · blocos de 4 semanas

**Transição:**

Esses são os parâmetros reportados; podemos retomar a questão metodológica em discussão.

## A02 — Métricas por classe no diagnóstico documental

*Fonte: Dissertação, §5.1.1, tabela metricas-classe-100*

**Objetivo:** Detalhar precisão, revocação, F1 e suporte na mesma amostra.

**Fala:**

Precisão pergunta quantas previsões de uma classe concordam com a referência. Revocação pergunta quantos exemplos daquela classe foram encontrados. Na negativa, o modelo encontra treze dos catorze exemplos, por isso a revocação é alta. Mas prevê negativo em trinta e oito notícias, reduzindo a precisão. O F1 combina as duas medidas. A média macro dá peso igual às classes, e o suporte registra quantas notícias cada uma possui na referência. Todos esses números pertencem ao mesmo diagnóstico documental; não são estimativas da qualidade das probabilidades contextuais do ITI.

**O que apontar:**

Negativa: revocação 0,929 e precisão 0,342; suporte 14; linha macro.

**Na tela:**
- Classe | Precisão | Revocação | F1 | Suporte
- Negativa | 0,342 | 0,929 | 0,500 | 14
- Neutra | 0,744 | 0,478 | 0,582 | 67
- Positiva | 0,263 | 0,263 | 0,263 | 19
- Média macro | 0,450 | 0,556 | 0,448 | 100
- Precisão: acertos entre as previsões da classe.
- Revocação: exemplos da classe recuperados. Suporte: quantidade na referência.

**Transição:**

A matriz do slide 19 mostra os pares que originam essas métricas.

## A03 — Oito sensibilidades permanecem exploratórias

*Fonte: Dissertação, §5.2.2, tabela iti-secondary — generated/tables/iti_v2_table_secondary.tex*

**Objetivo:** Distinguir intervalos nominais de p ajustado por Holm.

**Fala:**

Esta tabela apresenta a família de oito sensibilidades, com a primeira correlação menos a segunda em cada contraste. O ajuste de Holm foi aplicado aos valores p, não aos intervalos. A linha do recorte contextual versus texto integral é um bom exemplo: o intervalo nominal não inclui zero, mas o p ajustado é zero vírgula duzentos. Não podemos selecionar esse intervalo isoladamente como confirmação depois de examinar várias comparações. Além disso, a inferência de origem é exploratória. As sensibilidades ajudam a identificar escolhas relevantes para o protocolo seguinte; não demonstram um parâmetro ótimo nem superioridade confirmada.

**O que apontar:**

Cabeçalhos IC e p Holm; linha contextual/integral; demais sete p=1,000.

**Na tela:**
- Comparação | Δρ | IC inf. | IC sup. | p Holm
- H=2 − Soft | +0,067 | −0,081 | +0,236 | 1,000
- H=14 − Soft | +0,035 | −0,135 | +0,245 | 1,000
- ITI-H7 − Soft · Pearson | +0,038 | −0,127 | +0,224 | 1,000
- ITI-H7 − Soft · 2 semanas | −0,103 | −0,296 | +0,150 | 1,000
- ITI-H7 − Soft · 4 semanas | −0,177 | −0,368 | +0,084 | 1,000
- ITI-H7 − escore discreto | −0,078 | −0,337 | +0,275 | 1,000
- Recorte contextual − integral | −0,061 | −0,195 | −0,013 | 0,200
- ITI-H7 − suavização alternativa | −0,031 | −0,078 | +0,079 | 1,000
- Holm ajusta os valores p da família; os intervalos continuam nominais.

**Transição:**

A interpretação principal continua sendo de sensibilidade exploratória, com controles adicionais ainda necessários.

## A04 — Os grupos heurísticos têm composições diferentes

*Fonte: Dissertação, §5.1.1 e §5.1.3, tabela avaliacao-texto*

**Objetivo:** Interpretar diferenças entre grupos sem atribuição causal.

**Fala:**

Os grupos foram separados por uma heurística, não por anotação independente do foco. A acurácia é maior no grupo focal, mas os grupos também diferem em tamanho e composição. No grupo agenda, há vinte e quatro neutras e duas positivas na referência, sem exemplos negativos. O F1 macro foi calculado mantendo as três classes fixas, inclusive a classe sem suporte. Por isso, esses números não demonstram que o tipo de notícia causou a diferença. Eles indicam uma dimensão que merece avaliação com critérios e amostragem definidos previamente.

**O que apontar:**

Linhas focal e agenda; n; composição 24/2/0; nota causal.

**Na tela:**
- Grupo | n | Acurácia | Kappa | F1 macro
- Completo | 100 | 50,0% | 0,197 | 0,448
- Focal (heurística) | 74 | 52,7% | 0,260 | 0,498
- Agenda/multiempresa | 26 | 42,3% | −0,032 | 0,204
- Grupo agenda: 24 neutras, 2 positivas e nenhuma negativa na referência.
- A diferença é descritiva; não isola o efeito do tipo de notícia.

**Transição:**

Uma avaliação futura precisa registrar o foco da notícia sem confundi-lo com sua polaridade.

## A05 — Bootstrap: reamostrar semanas mantendo o pareamento

*Fonte: Dissertação, §4.5, parágrafo Contraste e incerteza; Künsch (1989)*

**Objetivo:** Explicar unidades, blocos, pareamento e saída estatística.

**Fala:**

A unidade reamostrada contém os sinais e o retorno da mesma semana. Eles não são embaralhados separadamente. Os blocos contíguos de quatro semanas procuram conservar parte da dependência temporal e respeitam os segmentos elegíveis, sem atravessar lacunas identificadas. Em cada réplica, recalculamos as duas correlações e sua diferença. Os percentis dois vírgula cinco e noventa e sete vírgula cinco produzem o intervalo nominal. O p exploratório é obtido pela proporção de diferenças no lado oposto ao sinal observado, duplicada e limitada a um. Esse cálculo não constrói explicitamente a hipótese nula; quatro semanas também não foi demonstrado como comprimento ótimo.

**O que apontar:**

Unidade pareada; tamanho de bloco; 10.000; percentis; nota sobre p.

**Na tela:**
- Passo | Operação
- 1 · Unidade | Semana com ITI, referência e retorno juntos
- 2 · Bloco | Selecionar 4 semanas contíguas; respeitar lacunas
- 3 · Réplica | Reamostrar blocos e recalcular a diferença
- 4 · Repetição | 10.000 réplicas; IC nos percentis 2,5 e 97,5
- p exploratório: duas vezes a proporção no lado oposto ao sinal observado, limitado a 1. Não é uma distribuição nula explícita.

**Transição:**

Por isso, tratamos o intervalo e o valor p como resultados exploratórios do procedimento utilizado.

## A06 — H controla a persistência; o aquecimento também importa

*Fonte: Dissertação, §4.5 e Apêndice C; figura iti-campanha-2*

**Objetivo:** Responder sobre meia-vida e efeito residual da inicialização.

**Fala:**

A meia-vida é uma parametrização interpretável do decaimento. O gráfico compara dois, sete e quatorze dias com as mesmas probabilidades. Outro efeito aparece no aquecimento: depois de setenta dias, a contribuição residual da inicialização é dois elevado a menos setenta dividido por H. Com H igual a sete, resta aproximadamente um milésimo; com quatorze, restam três vírgula cento e vinte e cinco por cento. Assim, o mesmo aquecimento não reduz igualmente a influência inicial em todas as configurações. A escolha de sete dias permanece uma configuração de estudo, não uma estimativa do tempo de reação do mercado.

**O que apontar:**

Legenda H2/H7/H14; fórmula 2^(−70/H); valores residuais, sem chamá-los de retorno.

**Na tela:**
- Séries empíricas ITI-H2, ITI-H7 e ITI-H14 observadas no corte semanal; eixos: ITI no corte e data.
- H2: azul contínuo · H7: laranja tracejado · H14: verde pontilhado
- Peso inicial após 70 dias = 2^(−70/H)
- H7: ≈ 0,001
- H14: 0,03125

**Transição:**

Para estudar apenas a forma dos pesos, precisamos também manter a janela informacional fixa.

## A07 — Experimento futuro: mesma janela, pesos diferentes

*Fonte: Dissertação, §6.2 — novo experimento controlado, ainda não executado*

**Objetivo:** Definir o princípio de comparação controlada e suas duas agregações.

**Fala:**

O controle proposto mantém a mesma informação nas duas agregações: janela, dias elegíveis, escores e instante de corte. A primeira faz uma média uniforme. A segunda usa pesos exponenciais e os normaliza dentro da mesma janela. Nas fórmulas, m é a quantidade de dias e j representa a idade de cada entrada em relação ao corte. Só os pesos mudam. Essa média exponencial de janela finita é um novo experimento; não deve ser apresentada como se fosse exatamente a recorrência histórica do ITI, que pode conservar informação anterior à janela. O tamanho da janela e os parâmetros serão fixados no desenvolvimento, antes de observar o período final.

**O que apontar:**

Regras fixas; fórmulas uniforme e exponencial; normalização no denominador; status planejado.

**Na tela:**
- Fixar antes do teste: janela, dias elegíveis, escores e corte.
- Uniforme: U_w = média dos mesmos m dias
- Exponencial: E_w = soma ponderada normalizada dos mesmos m dias
- m: número de dias da janela · d_w: dia de corte · j: idade em dias
- U_w: agregação uniforme · E_w: exponencial normalizada · X: entrada diária
- Planejado: E_w tem janela finita; não é a recorrência histórica do ITI.

**Transição:**

Esse controle permitirá separar a pergunta sobre histórico da pergunta sobre ponderação.

## A08 — Referências que sustentam os componentes

*Fonte: Dissertação, docs/references/bibliografia.bib; caps. 2–3 e §4.5*

**Objetivo:** Disponibilizar referências específicas por componente.

**Fala:**

Estas referências sustentam componentes distintos. O trabalho de Santos e colaboradores fundamenta os recursos financeiros em português. SemEval, SEntFiN e FinEntity sustentam a importância do alvo. Shapiro e o trabalho sobre o índice diário de notícias fornecem antecedentes de agregação temporal. Künsch e Holm apoiam a discussão sobre dependência e múltiplas comparações. Nenhuma dessas referências demonstra antecipadamente que sete dias seja ideal para a Sabesp ou que o ITI supere suas referências. Os localizadores permitem consultar os trabalhos, e a dissertação discute como cada um se relaciona com a proposta.

**O que apontar:**

Linha do componente perguntado; não ler oito referências em sequência.

**Na tela:**
- Santos, Bianchi e Costa (2023)
- FinBERT-PT-BR
- 10.5753/bwaif.2023.231151
- Cortis et al. (2017)
- SemEval-2017 Task 5
- 10.18653/v1/S17-2089
- Sinha et al. (2022)
- SEntFiN 1.0
- 10.1002/asi.24634
- Tang et al. (2023)
- FinEntity
- 10.18653/v1/2023.emnlp-main.956
- Shapiro, Sudhof e Wilson (2022)
- Measuring News Sentiment
- 10.1016/j.jeconom.2020.07.053
- Buckman et al. (2020)
- News Sentiment in the Time of COVID-19
- FRBSF Economic Letter 2020-08
- Künsch (1989)
- Bootstrap em séries
- 10.1214/aos/1176347265
- Holm (1979)
- Comparações múltiplas
- Scand. J. Stat. 6(2), 65–70
- Fundamentos dos componentes; não prova de H=7 ou superioridade.

**Transição:**

Podemos retornar ao ponto da metodologia que a banca desejar aprofundar.

---

*Total de slides: 29 + 8 apoio.*