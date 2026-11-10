# Respostas de apoio à banca — Qualificação PPGCC/UFSJ

**Pesquisa:** Índice Temporal Informacional (ITI), com aplicação empírica à Sabesp. **Etapa atual:** exploratória, sem demonstração de superioridade ou capacidade preditiva.

### 1. Qual é a contribuição científica, se as técnicas já existem?
A contribuição não é criar o FinBERT ou a suavização exponencial, mas especificar e avaliar um procedimento que conecta informação sobre uma empresa, escores de sentimento, agregação temporal e retornos. A pesquisa separa a validação da classificação textual da avaliação das associações financeiras e torna explícitas as escolhas do método. Mesmo com resultados inconclusivos, esse diagnóstico indica os controles necessários para o próximo experimento. **Seções:** 1.1, 1.3, 3.5 e 4.1.

### 2. Por que o Soft pontual é a comparação principal?
O Soft observa apenas o dia de corte e fornece uma referência simples sem memória, definida no desenho exploratório inicial. A comparação não isola exclusivamente os pesos exponenciais: o Soft foi zero em 36 das 94 semanas, embora 33 dessas semanas tivessem notícias anteriores. Por isso, acrescentei a média semanal como comparação complementar e prevejo uma avaliação futura com janelas idênticas e pesos distintos. **Seções:** 4.5 e 5.2.4.

### 3. Como interpretar a acurácia de 50% do classificador?
Esse valor mede concordância com uma anotação individual em cem notícias selecionadas para diagnóstico, não o desempenho em todas as 1.253 matérias. A classe neutra corresponde a 67 exemplos; por isso, a matriz de confusão e o F1 macro são necessários para interpretar os desacordos. Além disso, a avaliação usou título e corpo, enquanto o ITI utiliza recortes contextuais, cuja qualidade ainda precisa de anotação independente. **Seções:** 4.3, 4.4, 5.1 e 6.2.

### 4. Por que a meia-vida de sete dias?
Sete dias civis é uma escolha exploratória próxima à escala semanal, não um parâmetro ótimo extraído de outro artigo. Na fórmula utilizada, aproximadamente 90,57% do estado anterior permanece a cada dia, e uma contribuição sem novas entradas cai à metade após sete dias. As variantes com duas e quatorze dias verificam sensibilidade, mas não demonstram superioridade de uma configuração. **Seções:** 2.4, 4.5 e 5.2.2.

### 5. Como lidar com privatização, mercado e cobertura das notícias?
A pesquisa estima associações marginais, sem separar causalmente o efeito da privatização ou de movimentos gerais do mercado. A cobertura do corpus também possui lacunas, e um dia sem notícia observada não comprova que nada tenha sido publicado. O corte informacional reduz antecipação de dados futuros, mas essas ameaças continuam documentadas para avaliações posteriores. **Seções:** 4.2, 4.6, 5.3 e Apêndice B.

### 6. Qual é o experimento mínimo após a qualificação?
Primeiro, comparar as duas representações textuais nos mesmos itens, com anotadores independentes e registro das entradas efetivamente processadas. Depois, confrontar agregações que recebam exatamente a mesma janela, os mesmos escores e o mesmo corte, variando apenas os pesos. Os parâmetros devem ser definidos antes do teste em um período ainda não examinado, sem exigir inicialmente um novo modelo ou outras empresas. **Seções:** 5.3 e 6.2.

**Síntese para encerrar:** A qualificação documenta o procedimento e seus limites; a continuidade verificará a validade textual e a ponderação temporal em comparações controladas.
