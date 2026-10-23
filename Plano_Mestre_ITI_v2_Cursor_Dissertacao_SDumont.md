# Plano mestre — ITI-v2, implementação, SDumont e dissertação

**Autor da pesquisa:** Gabriel Felipe Souza Santos. **Orientador:** Michel Carlo Rodrigues Leles. **Instituição:** PPGCC/UFSJ. **Data de preparação:** 22/10/2026.

**Destinatário operacional:** Cursor. Executar este documento em sequência, preservando a arquitetura do Financial-Sentiment-Lab. Este arquivo reúne especificação científica, tarefas de engenharia, critérios de aceite, manuscrito substitutivo e bibliografia. Não é um relatório de novos experimentos: nenhuma execução do ITI-v2 foi realizada na preparação deste plano.

**Base inspecionada:** branch `main`, commit `328a3f496c3fdb17ec9bd8bf643c430a3b3c2878`, do [Financial-Sentiment-Lab](https://github.com/GabrielFSSantos/Financial-Sentiment-Lab/tree/328a3f496c3fdb17ec9bd8bf643c430a3b3c2878); anexos `Documento(1).pdf` e `deep-research-report(4).md`. Caso o checkout tenha avançado, comparar as mudanças antes de aplicar o plano. Não regredir correções posteriores.

## Como usar este documento

1. Ler integralmente as Partes I–IV antes de editar. As decisões de calendário, construto e validação afetam vários módulos.
2. Implementar as etapas P00–P12 em ordem. Cada etapa deve terminar com seus artefatos, verificações e atualização documental.
3. Aplicar a Parte V ao LaTeX: ela contém a redação acadêmica proposta, não apenas uma lista de tópicos.
4. Incorporar as referências e links da Parte VI ao acervo do projeto; manter um único arquivo bibliográfico canônico.
5. Concluir tudo que independe de acesso ao cluster e de novas anotações. Não apresentar esses insumos externos como concluídos. Preparar instruções executáveis para Gabriel.
6. Após os experimentos, seguir a Parte IV. Substituir os resultados pendentes, atualizar o resumo e o abstract, e preencher os fatos de execução no capítulo computacional a partir dos manifestos. Fórmulas e hipóteses não devem ser reescritas para favorecer os resultados.

**Limite honesto do pedido “só mudar os resultados”:** o texto conceitual está pronto; quantidades do corpus, partições de dados, checkpoint fixado e hardware efetivo são fatos que o Cursor precisa extrair automaticamente da implementação e dos manifestos. Não podem ser inventados agora. Esses campos terão preenchimento mecânico; a interpretação substantiva nova ficará concentrada no capítulo de resultados e nas sínteses que dependem dele.

## Sumário operacional

- Parte I: decisões científicas fechadas e ressalvas do diagnóstico.
- Parte II: roteiro cronológico de implementação, documentação e teste.
- Parte III: preparação e execução no SDumont.
- Parte IV: processamento posterior e atualização da dissertação.
- Parte V: texto acadêmico completo proposto.
- Parte VI: bibliografia, BibTeX e links de artigos.
- Parte VII: checklist final e instrução de execução ao Cursor.

# Parte I — Especificação científica

## 1. Decisão principal

Preservar o nome **Índice Temporal Informacional (ITI)**. Identificar a implementação nova como `iti_v2`; congelar a anterior como `legacy_v1`. O construto operacional é **polaridade textual referente a uma empresa, agregada no tempo com persistência explicitamente definida**. Não chamar o escore de impacto financeiro observado, valor econômico da informação, risco de investimento ou previsão de retorno.

A genealogia é uma síntese metodológica, não uma fórmula publicada integralmente por outro autor:

| Componente | Referência | Aproveitamento e limite |
|---|---|---|
| Alvo corporativo | Cortis et al. (2017); Tang et al. (2023) | A unidade é texto–entidade; extrair contexto não equivale a treinar um classificador condicionado à entidade. |
| Sinal em português financeiro | Santos, Bianchi e Costa (2023) | Modelo inicial de domínio. O desempenho no artigo não é teto teórico nem garantia no corpus Sabesp. |
| Agregação direcional | Hiew et al. (2019, versão 2 de 2022) | Balanço de classes por empresa. O estudo original usa Weibo e empresas de Hong Kong; o baseline aqui é uma adaptação a notícias brasileiras. |
| Memória | Shapiro, Sudhof e Wilson (2022); Buckman et al. (2020) | Antecedente para sentimento e decaimento geométrico. A EWMA de médias diárias com entrada zero é decisão deste projeto, não reprodução exata do DNSI. |
| Validade do indicador | Baker, Bloom e Davis (2016); Caldara e Iacoviello (2022) | Definir construto, corpus e validação. EPU e GPR não validam os pesos nem a fórmula específica do ITI. |
| Probabilidades | Guo et al. (2017) | Avaliar calibração localmente. Softmax e confiança declarada não são prova de acerto. |

Não adicionar pesos de confiança, magnitude, evento, relevância ou novidade à fórmula principal. Relevância e duplicação pertencem à seleção do corpus; evento, cobertura, neutralidade e entropia são diagnósticos.

## 2. Fórmulas e convenções

Para cada par notícia–empresa elegível, armazenar a distribuição canônica `p_negative`, `p_neutral`, `p_positive` e definir:

\[
s_{i,c}=p^+_{i,c}-p^-_{i,c},\qquad -1\le s_{i,c}\le1.
\]

Essa é a esperança da codificação ordinal (-1,0,+1) **sob a distribuição do modelo**. Sua interpretação como esperança do sentimento real exige validade e calibração; não é expectativa de retorno nem intensidade monetária.

Com \(n_{c,d}>0\) documentos únicos elegíveis no dia civil \(d\):

\[
S_{c,d}=\frac{1}{n_{c,d}}\sum_i s_{i,c},\qquad
B^{hard}_{c,d}=\frac{N^+_{c,d}-N^-_{c,d}}{n_{c,d}}.
\]

No armazenamento, `soft_mean` e `hard_bsi` ficam **nulos** quando não há notícia. Separadamente, a entrada operacional da recorrência é:

\[
X_{c,d}=\begin{cases}S_{c,d},&n_{c,d}>0\\0,&n_{c,d}=0.\end{cases}
\]

\[
\lambda_H=2^{-1/H},\qquad
ITI^{(H)}_{c,d}=\lambda_H ITI^{(H)}_{c,d-1}+(1-\lambda_H)X_{c,d}.
\]

- Unidade de H: **dias civis**, incluindo fins de semana e feriados.
- Estado inicial: zero; `adjust=False` se pandas for usado; implementação recursiva é a referência normativa.
- Grade previamente fixada: H = 2, 7 e 14. **H=7 é a especificação principal**, pela interpretação de uma semana, sem seleção por retorno; H=2 e H=14 são sensibilidades secundárias. A recomendação exploratória de H=2 fica preservada como hipótese, sem transformá-la em vencedora.
- Valores aproximados: λ₂=0,70710678; λ₇=0,90572366; λ₁₄=0,95169515.
- H=14 aproxima a retenção diária 0,95, cuja meia-vida é aproximadamente 13,51 dias; não afirmar igualdade.
- Aquecimento: iniciar o calendário pelo menos 70 dias antes da primeira observação avaliada, equivalente a cinco meias-vidas máximas. Se faltar histórico, começar no primeiro dia disponível e excluir os primeiros 70 dias de todas as comparações correspondentes. Informar perda amostral.
- Construir calendário completo até o último cutoff de avaliação, mesmo que a última notícia anteceda esse cutoff. O código legado termina na última notícia; não herdar esse encerramento.
- Sem notícia observada não significa neutralidade. A entrada zero significa ausência de novo impulso no corpus observado e faz o estado decair.
- Registrar cobertura conhecida, desconhecida e falha comprovada. Não inventar dias de coleta completa em corpus histórico recuperado retrospectivamente. Produzir também `days_since_last_news` e `coverage_status`.
- Na análise temporal estrita, cobertura desconhecida ou falha comprovada de coleta não é dia silencioso válido: manter entrada e estado estritos ausentes, marcar período inelegível para avaliação principal. Se não for possível reconstruí-lo, reiniciar o estado no primeiro trecho novamente elegível e cumprir novo aquecimento. Não interpolar sentimento usando dados futuros. Uma série adicional `observed_corpus_only` pode aplicar ausência de impulso aos dias vazios do arquivo, mas deve ser denominada exploratória e condicionada à cobertura observada. Ela não substitui silenciosamente a série estrita. Se a cobertura histórica for toda desconhecida, entregar essa análise exploratória e registrar a avaliação estrita como indisponível. A equação principal é aplicada somente nos segmentos elegíveis; desconhecimento não é um quarto valor de sentimento.

Séries auxiliares: `volume=n`, `negative_mean=mean(p_negative)` e entropia normalizada `-sum(p*log(p))/log(3)` por documento, com `0*log(0)=0`. `1-p_neutral` é massa não neutra, **não uma métrica geral de incerteza**. Negatividade não é risco financeiro. O índice de negatividade com memória é secundário, fora do teste principal.


### 2.1 Ajustes explícitos em relação ao relatório de pesquisa

Este plano preserva a fórmula recomendada e explicita escolhas que o relatório deixava abertas. H=7 é o candidato principal por decisão anterior ao novo teste; H=2 continua hipótese secundária. O cutoff principal é conservador, anterior ao último pregão, porque um valor diário de sexta pode incorporar notícias posteriores ao fechamento. A deduplicação principal é literal e auditável; agrupamento semântico fica secundário. Cobertura desconhecida mantém estado ausente na análise estrita; resultados condicionados apenas ao arquivo observado recebem identificação exploratória. Essas escolhas precisam constar do registro de decisões para que o Cursor não misture variantes.

Outro cuidado: a meia-vida calculada a partir do alfa nominal legado não descreve exatamente o legado quando o código altera o alfa por horizonte textual. A correspondência H≈1,94 para alfa 0,70 vale para retenção constante; o modelo antigo possui adaptações que impedem tratá-lo como equivalente ao novo H=2.

## 3. Corpus, entidade e texto

### 3.1 Conjunto canônico

Unidade de identificação: `news_id` estável, `article_version_id`, `company_id`. Uma matéria pode ter duas empresas e dois contextos; nunca copiar o mesmo rótulo para ambas automaticamente. Preservar texto original, URL, título, veículo, datas brutas, fuso, data de coleta, hash do texto, justificativas de inclusão/exclusão e vínculo com duplicatas.

Corpus piloto: novembro/2023–abril/2024; janela ampliada maio/2022–abril/2024 também já explorada. **Nenhuma delas constitui teste intocado.** Antes de olhar resultados novos, inventariar períodos nunca usados em escolha de regras e reservar um intervalo temporal externo. Não denominar uma janela “holdout” apenas porque o arquivo foi renomeado. Registrar a história de inspeção e o hash da partição.

Definir as datas exatas no inventário P02, usando cobertura real e sem consultar retornos ou novas previsões. Preferir pelo menos 52 semanas externas elegíveis; isso é meta operacional, não garantia de poder estatístico. Caso não haja janela independente, concluir engenharia e diagnóstico, mas publicar o estudo como exploratório e planejar coleta prospectiva. Não expandir automaticamente a lista de empresas ou fontes para fabricar tamanho amostral.

### 3.2 Deduplicação reproduzível

V1 obrigatória: URL canônica, hash do corpo normalizado e título+corpo idênticos normalizados. Manter a primeira versão temporalmente disponível como representante; preservação de versões atualizadas em tabela separada. Não substituir o texto histórico pelo texto corrigido posteriormente.

Não deduplicar só por título: “Sabesp divulga resultados” pode ocorrer em vários trimestres. Semelhança semântica e agrupamento de acontecimentos ficam para sensibilidade futura com auditoria humana; não são pré-requisito da campanha principal. Reportagens independentes sobre o mesmo acontecimento permanecem. Logo, `volume` mede documentos únicos observados, não número garantido de fatos econômicos independentes.

Aplicar deduplicação de forma causal: um documento futuro não pode mudar retrospectivamente o representante nem excluir um documento já usado no índice. Mesmos grupos duplicados não podem aparecer nos conjuntos de desenvolvimento e avaliação textual.

### 3.3 Contexto focal

Usar aliases versionados em `configs/entities.yaml`, incluindo nome, razão social e ticker, com fronteiras de palavra. O encontro de alias é candidato; não é comprovação de conteúdo substantivo.

Construir `entity_context_v1`: segmentar sentenças; selecionar cada sentença com menção explícita e uma sentença anterior/posterior; unir intervalos sobrepostos; manter ordem original; preservar negação, números e orações de contraste. Incluir título uma única vez se ele mencionar o alvo. Não resolver pronomes com uma heurística invisível: marcar `coreference_unresolved` para revisão/diagnóstico. Guardar offsets dos trechos e versão do segmentador.

Se não houver contexto recuperável, emitir `not_evaluable`, não classe neutra. Para comparação documento versus contexto, usar exatamente a interseção dos pares elegíveis, informando exclusões. O modelo atual recebe texto, não um parâmetro nativo de entidade: chamar o procedimento de **classificação de contexto focal**, com validade orientada à entidade a verificar.

Entrada máxima inicial: 512 tokens, incluindo especiais, conferida com o tokenizador fixado. Selecionar sentenças focais em ordem até o orçamento; truncar somente se uma sentença exceder o limite; registrar taxa de truncamento e se alguma menção permaneceu. Registrar `token_count_original`, `token_count_used`, `truncated`, `target_visible`. Modo `document_v1`: título+corpo com mesmo tokenizador e orçamento. Não alegar que o modelo leu o documento completo quando houve corte.

## 4. Calendário e ausência de vazamento temporal

### 4.1 Política principal conservadora

O corpus contém horários incompletos. Para manter a fórmula diária simples e não usar notícias posteriores ao fechamento, a campanha principal calcula estados ao fim de **dias civis completos** em `America/Sao_Paulo` e amostra o estado do dia anterior ao último pregão de cada semana.

Definições:

- `week_id`: sexta-feira civil da semana, apenas chave de agrupamento.
- `market_close_at`: instante real do encerramento do último pregão daquela semana, obtido de calendário histórico versionado; quinta-feira em semana com sexta feriado, por exemplo.
- `signal_cutoff_at`: fim do dia civil anterior à data desse pregão. É estritamente anterior ao preço inicial do retorno.
- `signal_day`: dia civil de `signal_cutoff_at`.
- `ITI_week = ITI_daily[signal_day]`.
- Baseline principal sem memória: `soft_input_week = X_daily[signal_day]`. Não usar média semanal nesse duelo, pois ela acrescentaria outra agregação temporal.

Exemplo: fechamento semanal na sexta; ITI e Soft são os estados da quinta encerrada. Notícias de sexta não entram no sinal daquela semana. Se o último pregão foi quinta, usar quarta. Essa perda de atualidade é o custo explícito da política conservadora; não apresentar o sinal como disponível com todas as notícias até o fechamento. Uma implementação intradiária, mais eficiente informacionalmente, será sensibilidade separada, nunca mudança silenciosa.

Para artigos com apenas data, assumir disponibilidade ao final da data declarada, com `timestamp_precision=date` e `availability_assumed=true`. Para horário conhecido, converter para fuso local e usar data local. Data sem evidência e texto atualizado sem versão histórica verificável exigem exclusão do painel temporal estrito; podem permanecer no diagnóstico textual. Em coleta retrospectiva, registrar que o texto recuperado hoje pode não coincidir com o publicado no passado; a regra temporal reduz vazamento de calendário, mas não elimina viés de revisão de conteúdo.

### 4.2 Retornos no calendário completo

Construir primeiro a série de preços de fechamento semanal ajustados a partir do calendário de mercado completo. Para horizonte h:

\[
R^{(h)}_{c,w}=\log(P^{adj}_{c,w+h}/P^{adj}_{c,w}),\quad h\in\{1,2,4\}.
\]

Calcular isso **antes** de juntar com notícias, índices e máscaras. `w+h` é h semanas de calendário; não h linhas sobreviventes à junção. Se faltar um preço necessário, retorno nulo com motivo. Não somar ignorando NaNs; não preencher preço ausente silenciosamente. Registrar origem, instante de download, coluna usada, política de proventos e ajustes corporativos. Se a fonte oferece apenas uma série ajustada retrospectiva, documentar a limitação de disponibilidade histórica, sem vendê-la como base point-in-time.

Na versão consultada, `weekly_align.py` faz merge com mercado antes de `_add_future_weekly_returns`, usa `period_end` real em um lado e chave normalizada em outro e utiliza `np.nansum`. Corrigir esses três riscos conjuntamente. O resample isolado `W-FRI` não resolve disponibilidade intradiária nem feriados.

Manter uma chave canônica `company_id, week_id`, uma data real do pregão e um cutoff separados. Nenhuma função deve trocar a chave pela data do último registro disponível. Exportar `alignment_audit.csv` com notícias admitidas, cutoffs, preços e razões de perda de cada semana.

## 5. Hipóteses, matriz e análise estatística

### 5.1 Campanha pequena

| ID lógico | Entrada | Índice | Papel |
|---|---|---|---|
| V2-C-SOFT | contexto focal | X diário sem memória | baseline principal |
| V2-C-H7 | contexto focal | ITI, H=7 | candidato principal |
| V2-C-H2 / H14 | contexto focal | ITI, H=2 / 14 | sensibilidade |
| V2-C-HARD | contexto focal | Hard-BSI diário, zero operacional no vazio | baseline de agregação rígida |
| V2-D-SOFT / H7 | documento | Soft / ITI H=7 | ablação textual pareada |
| LEGACY-C | contexto focal | fórmula legada congelada | comparação da fórmula, mesma entrada |
| LEGACY-HIST | entrada e protocolo históricos | legado | reprodução histórica, fora dos duelos controlados |

Volume semanal e média de todos os documentos da semana são comparadores descritivos adicionais. Não os misturar com a ablação isolada da memória. A inferência é feita uma vez por modelo, corpus e modo textual; H=2,7,14 reaproveitam as mesmas probabilidades, sem três passagens pela GPU.

### 5.2 Teste principal

Pergunta: no período externo, a memória semanal H=7 aumenta a associação **positiva** com retorno logarítmico de uma semana, em comparação ao mesmo sinal diário sem memória?

\[
\Delta=\rho_{Spearman}(ITI^{(7)}_w,R^{(1)}_w)-\rho_{Spearman}(X_w,R^{(1)}_w).
\]

Teste bilateral de Δ=0, nível 0,05; hipótese substantiva de benefício exige Δ>0. Intervalo inteiramente positivo e correlação do candidato positiva sustentam benefício no critério definido. Δ positivo entre duas correlações negativas significa associação menos negativa, não sucesso preditivo. Publicar coeficientes individuais, Δ, n e IC, inclusive quando o intervalo cruza zero. Não usar valor absoluto como métrica principal; associação negativa pode ser discutida exploratoriamente.

Bootstrap móvel pareado em blocos contíguos, 10.000 replicações, semente 20261022; comprimento principal de 4 semanas, sensibilidades 2 e 8. Esses tamanhos são decisões operacionais e não ótimos universais. Reamostrar as tuplas (ITI,Soft,retorno), mantendo dependência e pareamento. IC percentil de 95%; p bilateral centrado na hipótese nula, por `(|Δ*−Δ_obs| >= |Δ_obs|)` com correção `(1+contagem)/(B_valido+1)`. Não interpretar a mera fração de réplicas positivas como p-valor clássico. Documentar aproximação finito-amostral e estacionariedade local assumida.

Não comprimir semanas ausentes: formar blocos apenas dentro de trechos contíguos elegíveis identificados pelo calendário; reportar distribuição dos comprimentos. Se não houver blocos ou variabilidade suficientes, emitir `insufficient_data`, sem p-valor. Piso operacional: 30 pares e 8 blocos de tamanho principal disponíveis, com sensibilidades explicitamente limitadas quando não sustentadas. Atingir esse piso não prova poder adequado. Pré-execução: simular séries nulas autocorrelacionadas e alternativas para quantificar cobertura, erro tipo I e poder aproximado no tamanho esperado; registrar sem otimizar a análise para a significância empírica.

Família secundária: 8 contrastes predefinidos — H2 e H14 versus Soft (Spearman,h1); H7 versus Soft (Pearson,h1); H7 versus Soft (Spearman,h2 e h4); H7 versus Hard (Spearman,h1); contexto-H7 versus documento-H7 (Spearman,h1); H7 versus LEGACY-C (Spearman,h1). Aplicar Holm aos oito p-valores válidos, explicitando tratamento dos indisponíveis conservadoramente como 1 para controle da família planejada. Sensibilidades de bloco reportadas separadamente, sem selecionar a que gera menor p.

Cada contraste usa máscara comum entre seus participantes; exportar máscara e perdas. A tabela comparativa geral deve incluir também uma interseção global para inspeção. Bootstrap não corrige corpus enviesado, seleção retrospectiva, poucos eventos ou classificador inválido. Não concluir equivalência pela ausência de significância.

### 5.3 Avaliação humana

Preservar a amostra histórica de 100 notícias como desenvolvimento e análise de erros. Ela foi selecionada em função de classes previstas; suas métricas não estimam automaticamente o desempenho populacional. Preparar referência nova com no mínimo dois anotadores independentes e terceiro adjudicador; objetivo de três avaliações independentes nos itens de teste quando viável. Reportar quem realmente anotou, sem transformar meta em fato.

Plano executável: inventariar pool independente, reservar amostra aleatória de até 300 pares notícia–empresa, semente registrada, separada por grupos de duplicatas e períodos. Se houver menos itens, usar os elegíveis e reportar n. Divisão inicial 100 para desenvolvimento/calibração e 200 para teste apenas quando houver 300; caso contrário manter maior parte como teste e não calibrar se faltarem classes. Um painel adicional proposital de casos difíceis pode ser usado para erro, nunca fundido ao teste aleatório para estimar acurácia.

Rótulos: positivo, neutro, negativo; `avaliavel` e `ambiguo` são campos separados. Critério: direção da informação relatada para perspectivas econômicas/operacionais da empresa, baseada no texto, sem consultar retorno posterior. Tarifas, investimentos e privatização não têm rótulo fixo. Em conflito sem direção dominante, neutro+ambíguo, com evidência; texto insuficiente é não avaliável.

Calcular concordância humana antes da adjudicação: percentual bruto e Cohen para dois avaliadores; Fleiss quando houver painel completo de ≥3; se incompleto, indicar subconjunto comum ou usar métrica apropriada claramente documentada. Não comparar modelo versus autor e chamar isso de concordância interespecialistas.

Métricas de modelo: macro-F1 primário textual, F1/precisão/recall por classe, acurácia, balanced accuracy, kappa, matriz e IC por reamostragem de grupos de notícia. Baseline de classe majoritária definida no desenvolvimento, não aprendida no teste. Na amostra histórica descrita no PDF, prever sempre neutro dá 67% de acurácia: isso ajuda a interpretar os 50% do modelo, mas não dispensa macro-F1.

Gate de interpretação: sem referência independente, ou sem benefício textual frente ao baseline acompanhado de IC e erro qualitativo, as associações de mercado permanecem exploratórias e limitadas ao escore do modelo. Não bloquear desenvolvimento de software nem suprimir resultados negativos. Remover a apresentação de 70% de acurácia ou κ=0,40 como lei científica; se mantidos como marcos históricos, identificá-los como escolhas operacionais antigas.

Calibração opcional, fora do núcleo inicial: avaliar Brier multiclasse `mean(sum_k (p_k-y_k)^2)`, NLL e ECE top-label com 10 bins fixos e contagens; ajustar temperatura somente no conjunto de calibração. Se ele for insuficiente, manter probabilidades originais e declarar limitação. Não calibrar no teste. Nunca chamar `1-p_neutral` de confiança no acerto.

# Parte II — Implementação sequencial para o Cursor

## P00. Preservar histórico e registrar escopo

Ler `README.md`, `CONTRIBUTING.md`, eventuais `AGENTS.md`, `docs/README.md`, os índices de `documentation` e `research_trail`. Registrar `git status`, commit de base e mudanças locais. Criar branch própria sem sobrescrever trabalho do usuário. Não usar `git reset --hard` como rotina de atualização do cluster.

Criar `docs/plans/iti_v2_execution_plan.md` com este documento e `docs/plans/iti_v2_progress.md` com estado por etapa: pending/implemented/tested/blocked/completed. No registro, separar bloqueio de dados humanos, acesso HPC e falha técnica. Criar decisões novas em `decision-register.md` sem reescrever datas antigas.

**Aceite:** snapshot histórico identificado; plano versionado; nenhum resultado legado sobrescrito; todo comando futuro identificado como existente ou proposto.

## P01. Auditoria de consistência já identificada

Corrigir de imediato:

1. `docs/research_trail/part-04-results.md`: a seção 4.2 já informa 6/24 e zero significativas no corpus canônico; 4.6 ainda recomenda 41,7% e duas significativas como resultado principal. Marcar a segunda como legado e retirar a recomendação contraditória.
2. Separar a anotação exploratória 48%, κ=0,163 da formal histórica 50%, κ=0,197, F1≈0,45. A amostra formal não é referência especialista consolidada.
3. Não repetir do relatório antigo que o arquivo atual necessariamente contém 37,5%: a versão consultada já evoluiu. Reconciliar a partir do commit e dos outputs presentes.
4. Retirar a expressão “teto teórico” do desempenho do artigo FinBERT. Benchmark externo não limita matematicamente nem prevê desempenho local.
5. Revisar explicações do nome inglês do ITI: o README usa `Information Trend Index`, o abstract usa `Informational Temporal Index`. Adotar um único nome: **Informational Temporal Index**, preservando o acrônimo ITI e o nome português.
6. Corrigir SemEval: Keith Cortis (não Adrian), incluir Brian Davis; FinEntity: páginas 15465–15471; Shapiro: DOI `10.1016/j.jeconom.2020.07.053` (o `.bib` contém outro DOI).
7. Quarentenar `utfpr2024bert` com autor provisório e outras entradas incertas. A entrada BERTweet atribuída a Barbieri não deve ser usada como descrição confiável do checkpoint português sem conferir artigo/model card.
8. No texto legado, registrar que multiplicar dimensões no impacto e novamente na ponderação amplifica fatores; preservar a fórmula apenas no histórico.
9. Auditar `%`, `_`, `&`, `#` e links ao converter Markdown para LaTeX. Não presumir que o defeito anterior ainda exista em todas as páginas: o PDF anexado já contém vários percentuais corretamente renderizados.

**Aceite:** tabela `historical_reconciliation.csv` com origem, commit, run, corpus, protocolo, métrica, valor e status de verificabilidade; não harmonizar valores incompatíveis por substituição manual.

## P02. Inventário e congelamento do corpus

Estender `modules/datasets` e a preparação de corpus; manter coleta em `modules/scrapers`, sem importar scraper no núcleo experimental. Criar os arquivos novos somente onde não existir implementação equivalente.

| Artefato | Conteúdo |
|---|---|
| `corpus_manifest.json` | hashes dos insumos, contagens por etapa, período, regras, timezone, fontes e versão |
| `articles_canonical.parquet` ou CSV | notícia e versões preservadas |
| `article_company.parquet` | pares artigo–alvo e elegibilidade |
| `dedup_map.csv` | representante, duplicata, regra e ordem temporal |
| `coverage_daily.csv` | contagens por fonte/dia e disponibilidade conhecida |
| `split_manifest.json` | desenvolvimento/teste/calibração, datas e grupos imutáveis |
| `exclusions.csv` | motivo único principal e flags auxiliares |

Validar IDs, datas, fusos, texto vazio, duplicatas e aliases. Não assumir existência de um arquivo só porque documentação antiga o menciona; a árvore consultada expõe `manual_labels_100_eval.csv`, enquanto a trilha cita outros nomes. Resolver o arquivo real e registrar equivalência ou indisponibilidade.

Separar metadados bibliográficos de arquivos de notícias. Guardar cópias originais em área somente de leitura lógica. Proibir scripts da campanha de modificar corpus canônico; qualquer correção exige nova versão, não edição in-place.

**Aceite:** relatório de seleção permite reconstruir cada exclusão; manifestos reexecutados sobre o mesmo input produzem os mesmos IDs/hashes; teste externo escolhido sem olhar resultados.

## P03. Contexto focal e contrato de predição

Reaproveitar `modules/models/base.py`, `registry.py`, `adapters/bert/finbert_hf.py`, `modules/datasets/loader.py` e `modules/experiment/io/output_schema.py`.

Adicionar módulo puro de preparação de entrada, por exemplo `modules/datasets/text_views.py`, com `build_document_view` e `build_entity_context_view`. Ele recebe texto+alvo e retorna texto, spans, elegibilidade e diagnóstico. Não carregar modelo nem fazer rede ali.

Fixar revisão SHA do checkpoint em `configs/models.yaml`; `revision: main` não basta para reprodução. Ler config e model card; validar `id2label` sem adivinhar ordem. Registrar SHA dos pesos, tokenizer e config, licença e arquitetura. O repositório `lucas-leme/FinBERT-PT-BR` pode nomear seu classificador de modo diferente do artigo: explicar FinBERT-PT-BR/SentFinBERT-PT-BR, sem trocar checkpoint por semelhança de nome.

Contrato adicional de saída: `news_id, article_version_id, company_id, view_id, view_hash, model_key, model_revision, p_negative, p_neutral, p_positive, predicted_label, continuous_sentiment, token_count_original, token_count_used, truncated, target_visible, status`.

`ModelPrediction` atualmente aceita probabilidades opcionais e tolerância de soma relativamente ampla. Para ITI-v2 exigir três números finitos em [0,1], soma com tolerância explícita 1e-5 e erro diante de probabilidades ausentes. Não transformar confiança em distribuição one-hot para preencher campos. Guardar logits se disponibilizados para futura calibração.

Cache por hash de texto efetivo+alvo+view+checkpoint+tokenizador+config relevante+dtype; H e h não entram na chave de inferência. Invalidar cache quando qualquer componente mudar. Persistir lotes atomicamente e permitir retomada por chave, sem duplicar linhas.

**Aceite:** casos multiempresa sintéticos produzem contextos diferentes; permutar ordem de entrada não troca IDs; falha de inferência não vira neutro; nenhum input sem alvo visível passa silenciosamente como contexto válido.

## P04. ITI-v2 com estratégia explícita

Pontos existentes: `modules/experiment/indexing/temporal_index.py`, `dimensions.py`, `baselines.py`, `stages/aggregation.py`, `pipeline/combination_executor.py`, `config/loader.py`.

Adicionar estratégia `temporal_index.version: iti_v2`. Manter caminho legado isolado com testes de regressão. Preferir novo `indexing/iti_v2.py` para funções puras; o orquestrador seleciona estratégia. Não alterar significado de `iti_liquido` antigo sem campo de versão; criar `iti_v2` e adaptador explícito para research/dashboard.

Funções previstas:

```python
validate_probabilities(frame) -> frame
aggregate_company_day(predictions, calendar, corpus_manifest) -> daily_frame
compute_half_life_index(daily_frame, half_life_days, initial_value=0.0) -> daily_frame
build_weekly_signals(daily_frame, market_calendar) -> weekly_frame
```

Não criar dependência circular: `experiment` não lê retornos para gerar índices. `market` produz calendário/preços; `research` faz junção e avaliação. O índice diário pode existir antes de haver preços. O seletor semanal pode viver em `research` para consumir cutoffs de mercado.

Schema diário: `date, company_id, index_version, input_view, n_articles, soft_mean, soft_input, hard_bsi, hard_input, iti_v2_h2, iti_v2_h7, iti_v2_h14, negative_mean, mean_entropy, coverage_status, warmup, days_since_last_news`.

Exemplo aritmético obrigatório: com H=2, estado 0 e X₁=1, ITI₁≈0,29289322; dois dias seguintes sem notícia dão ITI₃≈0,14644661. Misturar p=(neg 0,1;neu 0,2;pos 0,7) com (neg 0,6;neu 0,3;pos 0,1) resulta S=0,05. Replicar cada documento após deduplicação não pode mudar a série.

**Aceite:** domínio [-1,1], recorrência, aquecimento e silêncio testados; nenhum multiplicador legado influencia v2; calendário termina no cutoff configurado; fórmula da documentação coincide com implementação.

## P05. Alinhamento, retornos e inferência estatística

Modificar `modules/research/io/weekly_align.py`, `io/align.py`, `validation/incremental.py`, `validation/inference.py` e loaders de configuração. Retornos futuros nascem do calendário de preços completo, antes das máscaras. Separar `week_id` de `market_close_at`.

Não recuperar valor ausente de risco, baseline ou impacto com zero silencioso. `not_available` não é dado observado. Correlação de constante é indefinida: emitir status, n e motivo, não 0. Não fabricar vitórias na comparação de NaNs.

Implementar arquivo de especificação `analysis_plan.yaml`, hash no manifesto e validação de esquema estrita. Campos desconhecidos devem gerar erro, evitando YAML aparentemente configurado mas ignorado. Relatórios precisam mostrar candidato, baseline, view, H, h, métrica, universo, n, estimativa, IC, p bruto/ajustado e status.

**Aceite:** excluir uma semana de notícias não muda os retornos futuros das semanas preservadas; sexta feriado não elimina a semana; news após cutoff nunca entram; quatro semanas significam quatro semanas de calendário; não há uso de NaN como zero financeiro.

## P06. Avaliação textual independente

Estender `modules/evaluation/manual_labels.py`, `classifier_eval_pt.py`, `classifier_error_analysis.py` e contratos de anotação. Criar exportação cega e importação validada, preservando respostas individuais. Arquivos de teste humano não devem ser lidos por scripts de seleção de prompts ou pesos.

Comparar documento/contexto nos mesmos itens e com a mesma referência. Medir retenção de contexto correto separadamente da polaridade. Tipologias: multiempresa, menção tangencial, negação, informação mista, atualização de página, truncamento, ação atribuída a outra empresa, evento econômico ambíguo e erro de rótulo humano.

Revisão qualitativa usa desenvolvimento; depois de abrir teste, alterações criam nova versão e novo teste externo, ou recebem etiqueta exploratória. Não transformar discordâncias em correções para forçar concordância com modelo.

**Aceite:** n real e cobertura por anotador explícitos; nenhum juiz automático é contado como humano; relatórios distinguem protocolo histórico e novo.

## P07. Campanha, configuração e execução reutilizável

Criar `configs/campaigns/iti_v2/`, com `protocol.yaml`, `datasets.yaml`, `experiments/`, `research_weekly.yaml` e README; integrar aos overlays existentes, sem duplicar loaders. Usar `modules/experiment/campaign` e gerar configurações resolvidas com hash.

Modelo de esquema a implementar, não um YAML já aceito pelo código atual:

```yaml
protocol_version: iti_v2_1
timezone: America/Sao_Paulo
index:
  version: iti_v2
  half_life_days: [2, 7, 14]
  primary_half_life_days: 7
  calendar: calendar_day
  initial_value: 0.0
  missing_news_input: zero_only_when_coverage_eligible
  unknown_coverage: missing_state_restart_warmup
  exploratory_observed_corpus: separately_labeled
  warmup_days: 70
text:
  primary_view: entity_context_v1
  comparison_view: document_v1
  max_length: 512
  context_neighbors: 1
temporal:
  week_anchor: W-FRI
  cutoff_policy: previous_calendar_day_end_before_last_session
  returns_before_join: true
analysis:
  primary_metric: spearman
  primary_horizon_weeks: 1
  horizons_weeks: [1, 2, 4]
  bootstrap_replicates: 10000
  block_length_weeks: 4
  block_sensitivity_weeks: [2, 8]
  seed: 20261022
  alpha: 0.05
  secondary_correction: holm
```

Adicionar datas e hashes concretos a partir de P02; impedir execução confirmatória com campos não resolvidos. `run_id` deve ser único, incluindo campanha, versão, commit curto e timestamp; não reutilizar `sabesp_r1_alpha070`. Salvar `parent_run_id` quando derivar índices de predições existentes.

Saídas mínimas por run: manifesto, configuração resolvida, inventário do ambiente, predições, série diária, sinais semanais, painel alinhado, auditoria temporal, métricas textuais, métricas/deltas financeiros, logs e relatório de recursos. Escrever `_SUCCESS` apenas depois de validar os artefatos obrigatórios; falha produz `status=failed` e lista de etapas concluídas.

**Aceite:** rodar de novo com mesmos insumos em outro diretório reproduz resultados dentro da tolerância declarada; retomar não repete inferência concluída; reexecução não substitui artefatos históricos.

## P08. Testes de liberação

| Grupo | Casos mínimos e resultado esperado |
|---|---|
| Probabilidades | classe invertida, NaN, soma inválida e ausente → erro; probabilidades válidas → escore exato |
| Entidade | Sabesp/Copasa com polaridades opostas; ticker como substring; negação; sem alias; truncamento antes do alvo |
| Deduplicação | URL com tracking; título igual com corpo diferente; republicação posterior; versão atualizada; estabilidade ao adicionar futuro |
| Índice | impulso, entrada constante, silêncio, H inválido, datas fora de ordem, duas empresas, calendário até fim |
| Semanas | sexta feriado, fim de semana, horário posterior ao cutoff, data sem hora e mudança de fuso |
| Retorno | janela incompleta, preço ausente, feriado, semana sem notícias e h=4 com lacuna |
| Estatística | séries constantes, blocos contíguos, máscaras pareadas, semente, oito testes Holm, insuficiência amostral |
| Cache | mesmo input reutiliza; checkpoint/view alterados invalidam; lote interrompido não duplica |
| Legado | fixture congelada mantém resultado; v2 ignora dimensões heurísticas |
| Artefatos | manifesto incompleto impede `_SUCCESS`; erro Slurm preserva status não zero |
| Documentação | links locais, citações resolvidas, tabelas geradas e nenhum marcador silencioso em PDF de entrega |

Reaproveitar `tests/test_temporal_index.py`, `test_research_weekly_align.py`, `test_research_align.py`, `test_output_schema.py`, `test_performance_monitor.py`, `test_preflight.py` e testes de campanha. Acrescentar testes de propriedades com geração determinística, sem depender de rede. Fazer smoke com modelo real e corpus pequeno somente após testes offline.

**Não exigir que testes sintéticos validem mérito científico.** Eles validam implementação; referência humana e estudo temporal avaliam a medida.

## P09. Atualizar documentação e dashboard antes de rerodar

| Arquivo/área existente | Atualização obrigatória |
|---|---|
| `README.md` | construto, v2/legado, comando principal, limite de interpretação e nome inglês |
| `documentation/01_vision_and_concepts.md` | separar sentimento, impacto, cobertura, persistência e retorno |
| `02_entrypoints_scripts.md` | comandos reais e flags após implementação |
| `03_modules.md` | novas funções e fluxo de cache/contexto/índice |
| `04_iti_formulas.md` | equações normativas, unidades, vazio, estado e aquecimento |
| `05_research_validation.md` | teste principal, máscaras, calendário e multiplicidade |
| `06_configuration.md` | schema e campos obrigatórios |
| `07_santos_dumont.md` | runbook seguro, pinning, alocação e monitoramento |
| `08_dashboard_streamlit.md` | indicação de versão e comparabilidade |
| `09_tests.md` | mapa das invariantes e comandos |
| `10_architecture_and_maintenance.md` | responsabilidades e proibição de duplicar lógica |
| `11_end_to_end_flow.md` | ordem dados→inferência→índice→research→texto |
| `12_business_rules.md` | cutoff, dedup, neutralidade, human reference |
| `13_dev_reading_guide.md` | caminho de leitura atualizado |
| `14_manual_annotation.md` | protocolo e versão, cego/adjudicação |
| `appendix_output_contract.md` | schemas v2, nulidade e status |
| `module_plugin_contract.md` | adaptadores futuros e capacidades de saída |
| `research_trail/part-00..06` | enquadramento, fórmula, protocolo, fases, histórico, lacunas e próximo ciclo |
| `research_trail/decision-register.md` | decisões novas com motivação e data |
| `references/README.md`, `bibliografia.bib`, `notas/` | links, correções e matriz afirmação–fonte |

Dashboard permanece leitor de artefatos: mostrar H, view, versão do corpus, qualidade temporal, referência humana, n e status. Substituir destaque de taxa de vitórias por efeito principal com intervalo. Não comparar barras de runs com corpus/protocolo diferentes sem aviso de não comparabilidade. Não recalcular fórmulas dentro das páginas.

## P10. Manuscrito e bibliografia antes da execução

Aplicar Parte V aos capítulos ativos, ajustar includes do arquivo principal e conservar o template UFSJ. Há arquivos antigos como `02_revisao.tex`, `03_proposta.tex`, `05_andamentos.tex` e `06_proximos_passos.tex`; verificar includes antes de editar. Não reintroduzi-los junto com capítulos equivalentes.

Estrutura final sugerida:

1. Introdução (`01_introducao.tex`).
2. Fundamentação teórica (`02_fundamentacao.tex`).
3. Construção de índices e trabalhos relacionados (`03_trabalhos_relacionados.tex`).
4. Metodologia (`04_metodologia.tex`).
5. Ambiente computacional e reprodutibilidade (`05_ambiente_computacional.tex`, novo).
6. Resultados preliminares e discussão (`06_resultados.tex`, migração do capítulo ativo).
7. Considerações finais e continuidade (`07_consideracoes_finais.tex`, migração).
8. Apêndices (`99_apendices.tex`).

Manter objetivo de concisão, sem impor contagem artificial de páginas. O capítulo computacional deve conter escolhas e evidência, não um manual de comandos; comandos ficam na documentação/apêndice.

Fonte bibliográfica canônica: `docs/references/bibliografia.bib`. Inspecionar o `referencias.bib` de 30 bytes e a compilação atual antes de alterar: pode ser redirecionamento/symlink. Adotar referência direta ao arquivo canônico ou geração determinística; não manter duas cópias manuais divergentes.

Se `tools/import_reescrita_quali.py` for usado, validar primeiro em cópia temporária; não executar importador antigo cegamente sobre arquivos atuais. Converter as marcações de citação para comandos abnTeX2, equações para ambientes LaTeX e tabelas longas para `longtable` quando necessário. Escapar percentuais sem escapar comentários reais indiscriminadamente.

**Aceite:** compilar com Makefile/latexmk, conferir log sem citações indefinidas, extrair texto e renderizar páginas com fórmulas/tabelas. A versão pré-execução informa “avaliação do ITI-v2 pendente”, sem números simulados.

## P11. Congelar protocolo e liberar campanha

Executar testes e auditoria do projeto; gerar relatório pré-execução. Registrar commit de código, hash de configuração, corpus, preços, split, modelo, calendário e protocolo humano. Arquivo `protocol_lock.json` contém esses hashes, hipótese principal e data. Qualquer alteração posterior que afete resultado cria nova versão e classifica a análise como exploratória se usar teste já consultado.

Condições para rodar: software consistente, insumos verificados e ambiente preparado. Condições para denominar resultado confirmatório: além disso, janela independente e referência textual adequada. Se apenas a primeira condição estiver satisfeita, executar a campanha exploratória com rótulo explícito; não desperdiçar a implementação nem maquiar o status.

## P12. Execução e fechamento

Seguir Partes III–IV. Produzir relatório final de implementação com arquivos alterados, testes executados, comandos validados, hashes, o que depende de Gabriel e o que permanece futuro. Não encerrar dizendo somente “implementei o plano” sem demonstrar os critérios de aceite.

# Parte III — SDumont: preparação, execução e medição

## 6. O que já está documentado e o que precisa ser observado

O job existente em `jobs/sdumont/run_experiment.srm` solicita **1 nó, 1 tarefa, 30 CPUs por tarefa, 1 GPU, 32G de RAM e 20 minutos**, na partição `sequana_gpu_dev`. Carrega `cuda/12.6_sequana` e `anaconda3/2024.02_sequana`. Isso é **configuração solicitada**, não comprovação de uso efetivo. A trilha registra execução anterior no job 11621573; este plano não acessou os logs desse job nem mediu sua máquina.

A página institucional do LNCC identifica nós com CPUs Intel Xeon Cascade Lake Gold 6252 e GPUs NVIDIA Volta V100. A abertura integral dessa página falhou durante a consulta; não transpor automaticamente número de GPUs, memória do nó ou capacidade total para o experimento. O SDumont tem diferentes configurações e gerações. O capítulo usará uma descrição institucional curta e a configuração **capturada no nó alocado** como dado principal.

Fontes operacionais: [SDumont/LNCC](https://sdumont.lncc.br/), [configuração institucional](https://sdumont.lncc.br/machine.php?pg=machine), [manual oficial Slurm: sbatch](https://slurm.schedmd.com/sbatch.html) e [sacct](https://slurm.schedmd.com/sacct.html). O Cursor deve conferir a documentação da partição acessível ao projeto antes da submissão; os nomes existentes são referência de migração, não promessa de disponibilidade futura.

## 7. Preparação local obrigatória

1. Manter o setup existente, mas produzir locks de dependências separados para ambiente local e CUDA escolhido. Fixar Python efetivamente usado, PyTorch, transformers, tokenizers, numpy, pandas, scipy, scikit-learn e bibliotecas de monitoramento; não afirmar compatibilidade ampla só porque o README a declara.
2. Baixar previamente modelo/tokenizer por revisão SHA e todos os datasets necessários; rodar verificação de hashes.
3. Preparar pacotes em wheelhouse/ambiente reproduzível se o nó computacional não tiver rede. Não baixar pesos no job.
4. Executar testes offline, smoke CPU e smoke GPU local quando disponível. Comparar probabilidades em fixture com tolerâncias `atol=1e-5, rtol=1e-4` para FP32; registrar diferenças e rótulos próximos de empate. Tolerância é objetivo de validação, não garantia universal entre arquiteturas.
5. CPU e GPU devem usar mesmo texto, ordem, pesos, dtype e batch para comparação científica de equivalência. Otimização de batch/precision é benchmark separado.
6. Criar pacote de execução com commit, configs resolvidas, assets, hashes e script. Não carregar credenciais ou venv local incompatível como se fosse portável.
7. `git pull --ff-only` em checkout limpo ou checkout dedicado ao commit. Se houver alterações, parar a atualização daquele checkout; não apagar outputs nem aplicar reset destrutivo.

## 8. Interface de campanha a implementar e testar

Criar `scripts/campaigns/iti_v2.sh` como invólucro fino dos módulos existentes. Subcomandos novos:

```bash
# Estes comandos são contrato futuro: o Cursor deve implementá-los e testá-los.
./scripts/campaigns/iti_v2.sh prepare --config configs/campaigns/iti_v2/protocol.yaml
./scripts/campaigns/iti_v2.sh check --config configs/campaigns/iti_v2/protocol.yaml
./scripts/campaigns/iti_v2.sh smoke --run-id iti_v2_smoke_001
./scripts/campaigns/iti_v2.sh infer --run-id <RUN_ID>
./scripts/campaigns/iti_v2.sh indices --run-id <RUN_ID>
./scripts/campaigns/iti_v2.sh evaluate --run-id <RUN_ID>
./scripts/campaigns/iti_v2.sh report --run-id <RUN_ID>
./scripts/campaigns/iti_v2.sh export-thesis --run-id <RUN_ID>
```

Não executar literalmente `<RUN_ID>`. O script deve oferecer `--help`, validar arquivos, propagar código de saída, rejeitar run existente não retomável e imprimir caminhos reais. `infer` usa GPU; `indices`, `evaluate` e `report` podem rodar em CPU depois de transferir os artefatos. Modelo externo por API não pertence ao job offline principal.

## 9. Job Slurm novo

Criar `jobs/sdumont/run_iti_v2.srm` após validar o invólucro. Modelo inicial para adaptar à política real:

```bash
#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --partition=sequana_gpu_dev
#SBATCH --job-name=iti_v2
#SBATCH --cpus-per-task=4
#SBATCH --gres=gpu:1
#SBATCH --mem=32G
#SBATCH --time=00:20:00
#SBATCH --output=job_iti_v2_%j.out
#SBATCH --error=job_iti_v2_%j.err
set -Eeuo pipefail
: "${ITI_PROJECT_DIR:?Defina ITI_PROJECT_DIR na submissao}"
: "${ITI_RUN_ID:?Defina ITI_RUN_ID na submissao}"
cd "$ITI_PROJECT_DIR"
module purge
module load cuda/12.6_sequana
module load anaconda3/2024.02_sequana
source venv/bin/activate
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-4}"
export TOKENIZERS_PARALLELISM=false
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
./scripts/campaigns/iti_v2.sh check --config configs/campaigns/iti_v2/protocol.yaml
srun ./scripts/campaigns/iti_v2.sh infer --run-id "$ITI_RUN_ID"
```

**Justificativa dos recursos propostos:** começar com 4 CPUs e 1 GPU no smoke, medir tokenização/utilização e ajustar antes de congelar produção. Os 30 CPUs do job histórico não são evidência de necessidade. 32G também é ponto inicial sujeito ao tamanho real do corpus, que ainda é carregado em memória na arquitetura atual. Não solicitar GPUs adicionais sem implementação de paralelismo e medição de ganho.

20 minutos é perfil de desenvolvimento já presente no projeto. Se o smoke indicar que a campanha ultrapassa esse limite, usar partição de produção autorizada ou dividir tarefas por corpus/view com cache e retomada. Não contornar limites de fila nem submeter uma campanha longa deliberadamente destinada ao timeout.

Submissão ilustrativa, após configuração e acesso de Gabriel:

```bash
export ITI_PROJECT_DIR="$SCRATCH/financial-sentiment-lab"
export ITI_RUN_ID="iti_v2_<commit>_<datahora>"
sbatch --export=ALL,ITI_PROJECT_DIR,ITI_RUN_ID jobs/sdumont/run_iti_v2.srm
squeue -u "$USER"
sacct -j <JOB_ID> --format=JobID,State,ExitCode,Elapsed,AllocCPUS,ReqMem,MaxRSS
```

Os parâmetros entre `<...>` devem ser substituídos; não gravar caminho pessoal no script. O job principal não executa scraper, download de ativos ou pesquisa bibliográfica. O usuário já pediu preparação para execução; este plano não pressupõe que o Cursor tenha acesso SSH/VPN nem que execute o job sem esse acesso.

## 10. Monitoramento e benchmark

Estender `CombinationPerformanceMonitor` em `modules/experiment/stages/metrics.py`, evitando outro monitor incompatível. Coletar:

| Bloco | Campos e cuidado |
|---|---|
| Identidade | run_id, job_id, commit, host, partição e horário UTC/local |
| Hardware | CPU real, CPUs permitidos por afinidade/cgroup, GPU nome/UUID/memória, RAM visível e limite da tarefa |
| Software | SO, kernel, Python, torch, CUDA runtime, driver, cuDNN, transformers, dtype, batch |
| Tempo | carregamento, tokenização, inferência, agregação, escrita e total; separar tempo na fila |
| Vazão | documentos/s e tokens/s; indicar denominador e modo de texto |
| Memória | RSS do processo e filhos, pico CUDA allocated/reserved, VRAM externa |
| Utilização | GPU e CPU amostradas a cada 1 s, quando disponíveis |
| Robustez | OOM, falhas, retentativas, truncamento, batches incompletos |
| Energia | opcional por integração da potência; métrica ausente se não houver suporte, nunca estimada como medida |

Capturar `lscpu`, `nvidia-smi`, `module list`, versões Python e `scontrol show job` em arquivos sanitizados. `nvidia-smi` por dispositivo pode incluir processos externos; não confundir utilização do nó com uso exclusivo do experimento. `MaxRSS` pode constar nos steps de `sacct`, não na linha pai. Valores indisponíveis devem ter status explícito.

Para tempo de GPU, sincronizar CUDA antes e depois das regiões cronometradas; registrar warm-up separado. Não introduzir sincronizações por documento que distorçam o regime de produção. Três repetições medidas de uma carga fixa, após warm-up, são o benchmark mínimo proposto; uma execução completa da campanha é separada desse benchmark. Informar mediana, mínimo/máximo e dispersão, sem prometer significância com três medições.

Comparação CPU/GPU: mesma carga e precisão; separar tempo end-to-end e inferência. Definir `speedup = mediana(T_cpu)/mediana(T_gpu)`. Não comparar GPU em cache quente com CPU incluindo downloads. Não comparar API remota com tempo local de kernel como se fossem a mesma grandeza.

Captura de sinais: em SIGTERM/timeout, gravar último lote confirmado, manifesto parcial e erro; permitir retomada em novo job. `set -e` não substitui tratamento dentro do Python. Métricas auxiliares podem falhar sem esconder falha original; falha do experimento nunca termina como sucesso por causa do logger.

## 11. Critério de liberação para produção

- Modelo real carregado offline na GPU alocada.
- Smoke com IDs e distribuições coerentes, sem uso de stub.
- Estimativa de memória/tempo compatível com a fila.
- Manifesto captura hardware efetivo e hashes.
- Saída completa somente com `_SUCCESS` validado.
- Transferência dos resultados verificada por hashes; preservar log Slurm e `sacct`.
- Pesquisa estatística usa as predições transferidas; não roda novamente inferência sem necessidade.

# Parte IV — Depois da execução

## 12. Ordem obrigatória de processamento

1. Conferir Slurm, exit code e manifesto da aplicação. Job `COMPLETED` não prova que todas as combinações previstas foram processadas.
2. Comparar número esperado de pares com predições, checar duplicatas, NaNs, modelos, views e corpus. Qualquer perda precisa aparecer em `exclusions.csv`.
3. Gerar índices H2/H7/H14 das mesmas predições e validar os exemplos aritméticos.
4. Gerar `alignment_audit.csv`, inspecionar automaticamente cutoffs, feriados, aquecimento e retornos futuros.
5. Rodar avaliação textual e descrever a referência utilizada. Resultado de modelo contra rótulo histórico não substitui a nova referência humana.
6. Rodar teste principal no conjunto externo bloqueado; depois secundários e sensibilidades, mantendo saída de todos.
7. Publicar `result_registry.json` como fonte única de números; todos os relatórios derivam dele e dos CSVs rastreados.
8. Gerar figuras e tabelas com scripts, evitando números digitados diretamente em LaTeX.
9. Atualizar trilha de pesquisa, documentação operacional, dashboard e manuscrito.
10. Compilar e conferir PDF, bibliografia, contagens, legendas e coerência das conclusões.

## 13. Tabelas, figuras e arquivos gerados

| Artefato | Conteúdo |
|---|---|
| `table_corpus` | inclusões, exclusões, datas, fontes, duplicatas, horários e classes |
| `table_annotation` | n por avaliador, concordância anterior ao consenso e regras de adjudicação |
| `table_textual_metrics` | modelo/view, macro-F1, acurácia, balanced accuracy, κ e IC |
| `figure_confusion` | matriz por view no mesmo teste |
| `figure_daily_signal` | S, ITI-H7 e volume em eixos/painéis separados |
| `figure_h_sensitivity` | H2/H7/H14, sem escolher vencedor retrospectivo |
| `table_primary` | ρ do candidato e baseline, Δ, IC, p e n |
| `table_secondary` | oito contrastes com p bruto/ajustado e status |
| `figure_delta_intervals` | deltas com intervalos, identificando análise principal |
| `table_resources` | solicitado versus alocado versus observado |
| `figure_resource_timeline` | uso da GPU/memória e fases do pipeline |
| `table_runtime` | CPU/GPU, repetições, tempos e vazão |

Exportar PDF/SVG para figuras vetoriais e PNG apenas quando necessário. Não usar eixos duplos para insinuar associação entre ITI e preço. Preferir painéis sincronizados para sinal/retorno/volume. Todas as legendas incluem corpus, run e natureza exploratória/externa.

Gerar `docs/Dissertacao_PPGCC/generated/results_macros.tex` com valores e tabelas em `generated/tables/`. Valores não disponíveis usam mensagem explícita no rascunho e impedem build final por `--final`. Não converter pendência em zero.

## 14. Regras de interpretação e revisão

- Δ positivo com IC cruzando zero: efeito pontual favorável, evidência inconclusiva; não “comprovou melhora”.
- IC totalmente positivo, ρ do ITI positivo e gate textual atendido: evidência de associação incremental **no protocolo e amostra examinados**; não causalidade, rentabilidade nem generalização setorial.
- Duas correlações negativas com Δ positivo: menor associação negativa; a hipótese direcional não fica validada.
- Sem benefício: resultado científico informativo; discutir persistência, erro textual, cobertura e escala temporal sem inventar causa única.
- Melhor macro-F1 sem ganho temporal: qualidade textual e utilidade temporal são dimensões distintas.
- Ganho temporal sem validade textual: não atribuir mecanismo econômico ao índice; investigar cobertura, datas e viés.
- Bom desempenho no piloto e perda externa: reportar instabilidade, sem retocar a especificação e reutilizar o mesmo teste como intocado.
- GPU mais rápida: benefício computacional medido; não melhora automática da qualidade científica.

Atualizar resumo, abstract e conclusão com os mesmos números do registro. Revisar também tempo verbal da metodologia e configuração efetiva do capítulo computacional. A seção de limitações deve refletir achados reais; não repetir automaticamente limitações que foram resolvidas nem apagar as que persistem.

## 15. Modelos paralelos e ensemble: continuidade delimitada

Preparar interface extensível agora; não transformar comparação de modelos em requisito para concluir a campanha v2 inicial.

1. Manter FinBERT-PT-BR como referência inicial, por idioma, domínio e artigo, não por suposta superioridade universal.
2. Reaproveitar os adaptadores já presentes para `pt_br_financial_sentiment_analysis`, BERTimbau e BERTweet como controles, conferindo origem, licença, revisão e adequação linguística. O checkpoint genérico e o financeiro podem compartilhar ancestral e erros; diversidade de nomes não garante independência.
3. Incluir futuramente um modelo aberto por instruções ou classificador ajustado ao alvo, escolhido em conjunto de desenvolvimento. Exigir model card, pesos, licença, tarefa em português e orçamento de hardware verificados. Não fixar neste plano um checkpoint recente não auditado.
4. Jev fica como **candidato por API**, condicionado a acesso, versão fixa e avaliação local. A página `jev.ia.br` é guia brasileiro; a fonte técnica é [TypeSafe](https://typesafe.ai/blog/introducing-system-one-models-and-jev) e sua [documentação](https://docs.typesafe.ai/introduction). Não há comprovação aqui de pesos abertos utilizáveis no SDumont. SDK aberto não torna pesos abertos.
5. Jev e modelos por instruções devem receber a mesma pergunta sobre Sabesp, as mesmas três classes e o mesmo texto; não consultar retornos futuros. Não tratar garantia de formato como garantia de verdade ou calibração no corpus brasileiro.
6. Separar papéis: `BaseSentimentModel` fornece sinal candidato; `BaseLabelJudge` fornece avaliação auxiliar. Um juiz não cria automaticamente referência humana. O mesmo modelo não pode gerar o gold e ser avaliado contra ele sem identificação explícita de dependência.
7. Se houver três probabilidades comparáveis, ensemble inicial `p_bar_k = mean_m(p_mk)`, e `s_bar=p_bar_positive-p_bar_negative`. Mesma lista de modelos e conjunto completo de respostas para todas as notícias. Falha de um participante gera `incomplete_ensemble`; não renormalizar pesos silenciosamente por notícia.
8. Se um modelo só fornecer rótulo ou confiança declarada, ele não entra no soft ensemble. Usar voto rígido em experimento distinto, com abstinência em empate. Não fabricar probabilidades de classe a partir de uma frase “90% confiante”.
9. Comparar cada modelo, média simples e melhor modelo selecionado no desenvolvimento, no mesmo teste humano externo; medir desacordo e correlação de erros. Pesos aprendidos e calibração somente em dados separados do teste. A média pode piorar o melhor modelo.
10. Somente depois da validação textual, recalcular ITI com o novo sinal mantendo corpus, calendário e H fixos. Se mudar simultaneamente modelo e fórmula, perde-se a identificação da origem do ganho.

# Parte V — Manuscrito acadêmico proposto

> **Instrução editorial:** o texto abaixo é destinado ao manuscrito. As marcações de citação entre colchetes correspondem às chaves do BibTeX da Parte VI. Não incluir as instruções operacionais acima na dissertação. Blocos “PREENCHIMENTO” são comandos editoriais e não prosa final. O texto usa presente para definir o método e futuro para avaliações não realizadas; depois da execução, ajustar somente as afirmações factuais correspondentes. Preservar dados pessoais e elementos institucionais existentes que estejam corretos.

## Título

**Índice Temporal Informacional a partir de notícias corporativas: construção e avaliação no setor brasileiro de saneamento**

O título mantém o escopo setorial como contexto; o estudo de caso principal é a Sabesp. Se a avaliação final permanecer restrita a uma empresa, é igualmente adequado usar “construção e avaliação para a Sabesp”, sem prometer comparação setorial executada.

## Resumo — versão anterior à nova campanha

Notícias corporativas reúnem informações sobre resultados, investimentos e decisões que podem ser relevantes para uma empresa. Transformar esse conteúdo em uma série temporal exige definir o alvo da classificação, a forma de agregação e o momento em que a informação pode ser utilizada. Este trabalho propõe o Índice Temporal Informacional (ITI), construído a partir de notícias em português e aplicado inicialmente à Sabesp. A formulação utiliza a diferença entre as probabilidades das classes positiva e negativa, agrega os escores de documentos únicos em médias diárias e representa sua persistência por uma média móvel exponencial parametrizada em dias de meia-vida. A proposta separa polaridade, volume de cobertura e incerteza do classificador, evitando ponderações heurísticas sobrepostas. O delineamento compreende uma avaliação textual diante de referência humana independente e uma avaliação temporal em que o índice é comparado ao mesmo sinal sem memória. A execução é organizada no Financial-Sentiment-Lab, com configurações versionadas, rastreabilidade dos dados e preparação para processamento no supercomputador Santos Dumont. A etapa exploratória anterior permitiu implementar o fluxo computacional e identificar limitações na classificação orientada à empresa e na comparabilidade das execuções. A nova campanha foi definida para examinar essas limitações com controle temporal e comparação explícita entre componentes. Sua avaliação quantitativa permanece pendente; portanto, não se atribui superioridade empírica à formulação reformulada. A contribuição pretendida é uma medida interpretável e um procedimento reproduzível que permitam avaliar a utilidade da persistência temporal sem confundi-la com alterações no corpus ou no classificador.

**Palavras-chave:** análise de sentimentos; notícias financeiras; índice temporal; processamento de linguagem natural; reprodutibilidade.

## Abstract — versão anterior à nova campanha

Corporate news contains information about earnings, investment, and decisions that may be relevant to a company. Converting such content into a time series requires defining the classification target, the aggregation rule, and when information becomes available. This study proposes the Informational Temporal Index (ITI), derived from Portuguese-language news and initially applied to Sabesp. The formulation uses the difference between positive and negative class probabilities, aggregates scores from unique documents into daily averages, and represents persistence through an exponentially weighted moving average parameterized by a half-life in calendar days. Polarity, coverage volume, and classifier uncertainty are treated separately, avoiding overlapping heuristic weights. The design includes a textual evaluation against independent human annotations and a temporal evaluation comparing the index with the same signal without memory. The workflow is implemented within Financial-Sentiment-Lab, with versioned configurations, data provenance, and preparation for execution on the Santos Dumont supercomputer. Earlier exploratory work established an operational workflow and revealed limitations in company-oriented classification and cross-run comparability. The new campaign is designed to investigate these issues through explicit temporal controls and component comparisons. Quantitative evaluation of the revised formulation is pending; no empirical superiority is claimed at this stage. The intended contribution is an interpretable measure and a reproducible procedure for assessing temporal persistence without confounding its effect with changes in the corpus or classifier.

**Keywords:** sentiment analysis; financial news; temporal index; natural language processing; reproducibility.

## Capítulo 1 — Introdução

### 1.1 Contexto e delimitação

Informações sobre uma empresa são divulgadas em diferentes formatos e momentos. Uma notícia pode apresentar resultados financeiros, descrever uma decisão regulatória ou apenas mencionar a companhia em uma agenda de mercado. Embora esses textos possam ser convertidos em escores por modelos de linguagem, a existência de um número não assegura que ele represente adequadamente a informação referente à empresa.

A relação entre conteúdo jornalístico e variáveis financeiras motiva o uso de métodos computacionais para organizar grandes conjuntos de textos. Trabalhos como o de Tetlock mostram a pertinência desse campo de investigação, mas não autorizam supor que qualquer medida de sentimento tenha utilidade para qualquer ativo ou período [@tetlock2007media]. Nesta pesquisa, a classificação textual é uma etapa de construção de uma medida, cuja qualidade precisa ser examinada antes de sua interpretação econômica.

O estudo concentra-se inicialmente em notícias em português relacionadas à Companhia de Saneamento Básico do Estado de São Paulo, Sabesp. O setor de saneamento fornece o contexto de aplicação, enquanto a empresa define a unidade principal de análise. A extensão a outras companhias depende de cobertura documental e de condições comparáveis de avaliação; ela não é assumida a partir dos resultados de um único caso.

O FinBERT-PT-BR foi escolhido como modelo inicial por sua relação com o domínio financeiro em português e pela existência de uma descrição acadêmica de seu desenvolvimento [@santos2023finbert]. Essa escolha permite estruturar a investigação a partir de um sinal linguístico documentado. Ela não substitui a avaliação de adequação às notícias de saneamento nem impede o uso posterior de outros modelos.

### 1.2 Problema e pergunta de pesquisa

A transformação de notícias em indicador temporal envolve decisões distintas. A primeira é identificar qual parte do texto se refere à empresa. A segunda é obter uma medida de polaridade. A terceira é combinar notícias de um período e definir por quanto tempo o sinal anterior permanece no índice. Quando todas essas decisões variam simultaneamente, torna-se difícil identificar a origem de um eventual benefício.

A pergunta central é: **a introdução de memória temporal em um sinal de polaridade textual referente à Sabesp aumenta sua associação positiva com retornos posteriores de SBSP3, em comparação ao mesmo sinal sem memória, sob um protocolo temporal previamente definido?** A expressão “referente à Sabesp” descreve o alvo pretendido da medida; sua adequação é examinada por avaliação humana e análise de erros.

A pergunta não equivale a investigar causalidade ou rentabilidade de uma estratégia. Retornos também dependem de informações ausentes do corpus e de fatores gerais de mercado. A comparação proposta busca uma associação incremental delimitada, não uma explicação completa do preço da ação.

### 1.3 Objetivos

O objetivo geral é construir e avaliar um Índice Temporal Informacional com componentes interpretáveis, preservando a distinção entre qualidade textual e comportamento temporal.

Os objetivos específicos são: organizar um corpus rastreável de notícias e pares notícia–empresa; produzir entradas textuais que privilegiem o conteúdo referente ao alvo; avaliar a classificação diante de referência humana independente; comparar agregação rígida e probabilística; especificar a persistência por meia-vida; avaliar o efeito da memória com calendário e amostra comuns; e documentar a execução computacional, incluindo recursos utilizados e limitações de reprodução.

### 1.4 Contribuição e hipótese

A contribuição proposta não consiste em inventar uma nova operação de suavização. Ela está na organização e avaliação de uma medida corporativa em português com decisões identificáveis sobre alvo, agregação e persistência. Essa decomposição permite testar componentes separadamente e compreender limitações que uma fórmula com muitos pesos pode ocultar.

A hipótese principal é que a memória de sete dias produz associação positiva maior com o retorno da semana seguinte do que a entrada diária sem memória. Meias-vidas de dois e quatorze dias são examinadas como sensibilidades. A escolha de sete dias é anterior à nova avaliação e possui interpretação temporal direta; não representa uma conclusão extraída dos resultados antigos.

O trabalho também admite a possibilidade de não encontrar benefício. Nesse caso, a contribuição permanece na caracterização das condições em que o sinal foi construído, dos erros da classificação e dos limites da hipótese temporal. Resultados negativos não serão substituídos por uma busca posterior de parâmetros apresentada como confirmação.

### 1.5 Organização

O segundo capítulo apresenta os conceitos necessários à medida. O terceiro discute famílias de índices e o posicionamento da proposta. O quarto especifica os dados, a formulação e a avaliação. O quinto descreve o ambiente computacional e a reprodutibilidade. O sexto reúne resultados e discussão, distinguindo a etapa histórica da nova campanha. O último capítulo sintetiza as contribuições e organiza a continuidade da pesquisa.

## Capítulo 2 — Fundamentação teórica

### 2.1 Sentimento financeiro e empresa-alvo

Sentimento textual, orientação econômica e retorno de mercado são objetos relacionados, mas diferentes. Uma notícia com linguagem negativa pode descrever um problema restrito a outra empresa. Um investimento pode ampliar capacidade e, simultaneamente, aumentar custos. Assim, a presença de palavras favoráveis ou desfavoráveis não determina, isoladamente, a direção da informação para a companhia analisada.

O tratamento do alvo aparece explicitamente em tarefas de sentimento financeiro, como SemEval-2017 Task 5, e em bases como FinEntity [@cortis2017semeval5; @tang2023finentity]. Esses antecedentes fundamentam a escolha do par texto–empresa como unidade de análise. O corpus em português, porém, exige avaliação própria: resultados e rótulos de outras línguas não são transferidos automaticamente.

Nesta pesquisa, polaridade refere-se à orientação da informação relatada para as perspectivas econômicas ou operacionais da empresa, conforme o conteúdo disponível. A classe neutra indica ausência de orientação predominante identificável. A falta de texto suficiente é registrada separadamente. Essa definição evita transformar falhas de extração ou menções incidentais em exemplos artificiais de neutralidade.

### 2.2 Modelos de linguagem e classificação

BERT utiliza representações contextuais para tarefas de linguagem, incluindo classificação de textos [@devlin2019bert]. A adaptação ao idioma e ao domínio é relevante porque os mesmos termos podem ter usos diferentes em linguagem geral e financeira. BERTimbau constitui um antecedente de representação em português brasileiro, enquanto FinBERT e FinBERT-PT-BR focalizam aplicações financeiras em seus respectivos contextos [@souza2020bertimbau; @araci2019finbert; @santos2023finbert].

O modelo empregado neste trabalho é identificado pelo repositório, pela revisão dos arquivos e pelo mapeamento de classes efetivamente carregado. Essa identificação é necessária porque o nome de uma família de modelos não determina sozinho os pesos utilizados. Também se distingue a adaptação do modelo de linguagem do classificador de sentimento descrito na literatura.

O comprimento máximo de entrada limita o conteúdo processado. Quando título e corpo excedem o orçamento de tokens, uma informação relevante localizada no fim da matéria pode não chegar ao modelo. Por isso, a avaliação registra o texto efetivamente utilizado e compara uma entrada documental com uma entrada de contexto focal. A segunda reduz informação alheia ao alvo, mas não equivale a uma garantia de compreensão da relação entre acontecimento e empresa.

### 2.3 Probabilidades e escore contínuo

Considere as classes negativa, neutra e positiva, codificadas como -1, 0 e +1. Se o classificador produz uma distribuição sobre essas classes, a média dessa codificação sob a distribuição fornecida é a diferença entre as probabilidades positiva e negativa. O escore preserva direção e varia entre -1 e +1.

Dois documentos podem receber o mesmo escore por razões distintas. Uma saída concentrada na classe neutra e outra dividida entre positivo e negativo podem produzir valor próximo de zero. Por isso, o escore é acompanhado da probabilidade neutra e da entropia da distribuição. A entropia descreve dispersão entre classes; não demonstra, sozinha, a existência de ambiguidade real no texto.

A maior probabilidade de saída não deve ser interpretada automaticamente como probabilidade de acerto. A literatura de calibração mostra a necessidade de confrontar confiança e desempenho observado [@guo2017calibration]. No presente estudo, a distribuição é utilizada como sinal do modelo; eventuais procedimentos de calibração serão ajustados em dados separados da avaliação final.

### 2.4 Agregação e persistência

Uma média diária de polaridade e uma contagem de notícias respondem a perguntas diferentes. A primeira resume a direção dos documentos selecionados; a segunda descreve cobertura. A média de um dia com uma notícia não tem o mesmo suporte amostral da média de um dia com muitas notícias, embora ambas permaneçam na mesma escala. Manter volume como série auxiliar permite observar essa diferença sem alterar arbitrariamente a polaridade.

A memória temporal define a influência de entradas anteriores no estado atual. Na média móvel exponencial adotada, essa influência diminui geometricamente. A meia-vida expressa o intervalo necessário para que a contribuição de um impulso caia à metade na ausência de novos impulsos. Ela fornece uma interpretação mais direta do que um coeficiente sem unidade temporal.

A persistência é uma hipótese da representação, não uma propriedade econômica comprovada a priori. A ocorrência de notícia antiga não garante que o mercado continue reagindo a ela. Essa é uma razão para comparar a série suavizada ao mesmo sinal sem memória e para tratar diferentes meias-vidas como escolhas verificáveis.

### 2.5 Referência humana e avaliação

A avaliação humana depende de uma tarefa definida e de instruções consistentes. Concordância entre anotadores e concordância entre modelo e referência final têm finalidades distintas. A primeira descreve a estabilidade da tarefa entre pessoas; a segunda descreve o desempenho da classificação automática diante do padrão adotado [@artstein2008agreement].

O coeficiente kappa considera concordância observada e uma referência de concordância esperada pelas margens [@cohen1960kappa]. Sua interpretação depende da distribuição das classes e do desenho da amostra. Em painéis completos com vários avaliadores, podem ser utilizadas medidas apropriadas como a de Fleiss [@fleiss1971nominal]. Nenhum desses coeficientes transforma um consenso em verdade sem incerteza.

A avaliação automática inclui matriz de confusão e medidas por classe, além de macro-F1 e acurácia. A apresentação conjunta é necessária porque uma classe frequente pode produzir acurácia aparentemente alta em um classificador pouco informativo. Exemplos de erro complementam as métricas ao mostrar diferenças entre o critério humano e o conteúdo efetivamente recebido pelo modelo.

### 2.6 Associação temporal e inferência

Uma correlação entre índice e retorno futuro descreve associação sob o alinhamento adotado. Ela não estabelece causalidade, e sua magnitude pode mudar com a janela temporal, a cobertura das notícias e a definição do retorno. Também não representa diretamente o desempenho de uma estratégia de investimento, que exigiria decisões, custos e avaliação próprios.

Observações temporais podem ser dependentes. Retornos de múltiplas semanas sobrepostos compartilham períodos, e o próprio índice suavizado possui persistência. Métodos de reamostragem em blocos procuram preservar parte dessa estrutura [@kunsch1989bootstrap]. A validade da aproximação depende da amostra e das condições do processo; intervalos devem ser apresentados com essas limitações.

Quando várias comparações são examinadas, aumenta a possibilidade de resultados nominais favoráveis por acaso. A definição de uma análise principal e o ajuste da família secundária organizam a interpretação. O procedimento de Holm oferece uma forma de controlar multiplicidade na família declarada [@holm1979multiple], mas não corrige escolhas metodológicas feitas após observar o teste.

## Capítulo 3 — Construção de índices e trabalhos relacionados

### 3.1 Da coleção de textos ao indicador

Um índice textual exige correspondência entre o conceito pretendido e os documentos utilizados. Não basta aplicar um classificador e agregar suas saídas. A seleção de fontes, o tratamento de duplicatas, as regras de elegibilidade e a estabilidade da cobertura influenciam o significado da série resultante.

O Economic Policy Uncertainty e o Geopolitical Risk ilustram construções em que o conceito medido orienta a seleção textual e a validação [@baker2016epu; @caldara2022gpr]. Esses índices não medem a mesma coisa que o ITI. Seu papel nesta pesquisa é fundamentar a necessidade de critérios explícitos e de evidências de validade, não fornecer pesos a serem transplantados.

### 3.2 Agregação corporativa

Hiew e colaboradores apresentam um índice de sentimento por empresa baseado no balanço entre textos positivos e negativos, dividido pelo total de textos classificados [@hiew2019bsi]. A formulação oferece um comparador simples para a agregação. Sua aplicação original utiliza outra língua, fonte textual e mercado; a versão utilizada aqui é uma adaptação metodológica.

O ITI emprega uma extensão probabilística: em lugar de cada documento contribuir apenas com -1, 0 ou +1, utiliza-se a diferença entre as probabilidades das classes extremas. Essa escolha é uma definição deste trabalho. O baseline rígido permanece na avaliação para verificar se conservar a distribuição do modelo produz comportamento diferente da classe vencedora.

### 3.3 Sentimento de notícias e memória

Shapiro, Sudhof e Wilson estudam a mensuração de sentimento a partir de notícias [@shapiro2022fed]. A documentação do índice diário apresentada por Buckman e colaboradores utiliza pesos que diminuem geometricamente com a idade da informação [@buckman2020news]. Esse é o antecedente adotado para motivar a persistência temporal.

A implementação proposta não reproduz integralmente o índice do Federal Reserve. O ITI trabalha com polaridade corporativa em português, médias diárias e uma regra explícita de ausência de novo impulso. A meia-vida parametriza essa regra, enquanto o efeito da memória é avaliado em comparação com o mesmo sinal diário. A diferença entre inspiração metodológica e reprodução é preservada para que a genealogia da medida não seja confundida com validação empírica.

### 3.4 Alvo e domínio linguístico

SemEval e FinEntity evidenciam a relevância de relacionar a polaridade a uma entidade específica. FinBERT-PT-BR oferece o ponto de partida linguístico do projeto. Essas duas linhas se complementam, mas nenhuma assegura que um classificador documental se torne orientado à Sabesp apenas por receber trechos selecionados.

A pesquisa combina esses antecedentes em uma estratégia verificável: delimitar contexto, manter o classificador inicial e avaliar os erros contra referência humana. Se o recorte de contexto não for suficiente, a continuidade poderá incorporar modelos condicionados ao alvo ou ajustados à tarefa. Essa possibilidade permanece separada da avaliação da memória, para não confundir mudanças simultâneas.

### 3.5 Posicionamento da proposta

O ITI é uma síntese de três decisões: produzir um sinal textual referente à empresa, resumi-lo diariamente e representar sua persistência. Sua originalidade é situada no desenho e na avaliação do procedimento para o corpus estudado, não na afirmação de uma técnica universalmente inédita.

A etapa anterior explorou uma fórmula com várias dimensões auxiliares. A reformulação reduz essas interações para permitir uma pergunta mais direta sobre o papel da memória. Evento, cobertura e características do texto são preservados como informações explicativas. Essa organização torna possível identificar benefícios e limitações sem atribuir a uma única fórmula os efeitos de mudanças na classificação, no corpus e no calendário.

## Capítulo 4 — Metodologia

### 4.1 Delineamento

O estudo é empírico e computacional, com aplicação inicial à Sabesp. A avaliação possui duas camadas. Na camada textual, examina-se a classificação de pares notícia–empresa. Na camada temporal, avalia-se a associação de séries construídas desses pares com retornos posteriores de SBSP3. Resultados de uma camada não substituem a validação da outra.

A campanha principal utiliza um classificador fixado e duas formas de entrada, documental e focal. A fórmula do índice é comparada à mesma entrada diária sem memória. A formulação anterior é preservada para reprodução histórica e comparação secundária, identificada por versão própria.

### 4.2 Dados e rastreabilidade

O corpus é organizado a partir dos arquivos e mecanismos de coleta do Financial-Sentiment-Lab. Cada documento mantém identificador estável, texto recuperado, fonte, URL, datas disponíveis e hash. Sua relação com a empresa é armazenada separadamente, permitindo que um mesmo documento participe de avaliações para mais de um alvo sem receber automaticamente a mesma polaridade.

São removidas cópias identificadas por URL canônica ou conteúdo idêntico normalizado. Títulos iguais, isoladamente, não determinam duplicação. A ordem temporal é preservada: uma publicação posterior não modifica retrospectivamente o representante já utilizado. Reportagens independentes sobre um mesmo acontecimento podem permanecer, de modo que a contagem representa documentos únicos observados e não o número exato de acontecimentos econômicos.

O inventário apresenta o fluxo de seleção e as perdas por falta de texto, data, alvo ou versão verificável. Também descreve fontes e cobertura ao longo do período. Em dados históricos, a ausência de notícia no arquivo não prova ausência de publicação. Essa limitação é registrada como parte do corpus, sem converter desconhecimento em cobertura completa.

**PREENCHIMENTO AUTOMÁTICO:** inserir tabela gerada de `corpus_manifest.json`, com datas, número bruto, duplicatas, pares elegíveis, fontes, precisão temporal e divisões. Não conservar “aproximadamente 465” como total da nova campanha sem recomputar.

### 4.3 Desenvolvimento e avaliação externa

As janelas utilizadas nas campanhas anteriores são tratadas como desenvolvimento. Sua inspeção já influenciou decisões da pesquisa, o que impede apresentá-las como avaliação independente da reformulação. A nova partição temporal é definida a partir de cobertura disponível e do histórico de uso dos dados, antes da consulta aos resultados da campanha.

O manifesto de divisão identifica datas, grupos e hashes. Caso não haja intervalo externo suficiente, os experimentos serão apresentados como exploratórios e a avaliação independente dependerá de extensão do corpus. Essa condição não será resolvida apenas por uma divisão aleatória das notícias, pois ela não preservaria o caráter temporal da pergunta financeira.

**PREENCHIMENTO AUTOMÁTICO:** inserir datas e status real de independência a partir de `split_manifest.json`. Se o status for exploratório, ajustar a designação do teste em todas as tabelas, mantendo a hipótese definida.

### 4.4 Anotação e avaliação textual

A pergunta de anotação solicita que o participante identifique a direção da informação apresentada para a empresa-alvo, sem utilizar o retorno posterior da ação. O formulário registra classe, possibilidade de avaliação, ambiguidade, tipo de notícia e trecho de evidência. Menção incidental e texto insuficiente são separados da classe neutra.

As avaliações independentes são preservadas antes da adjudicação. A concordância humana é calculada sobre os itens efetivamente compartilhados e acompanhada da distribuição das classes. O consenso final não substitui esse registro. A amostra histórica anotada pelo autor permanece como diagnóstico de desenvolvimento, sem ser denominada referência especialista independente.

A comparação automática utiliza macro-F1, medidas por classe, acurácia, balanced accuracy, kappa e matriz de confusão. O baseline de classe majoritária é definido no desenvolvimento. As entradas documental e focal são comparadas nos mesmos pares elegíveis, com apresentação da quantidade excluída. Intervalos por reamostragem respeitam grupos de documentos relacionados.

### 4.5 Preparação textual e classificação

A entrada documental concatena título e corpo. A entrada focal seleciona sentenças que mencionam o alvo e suas vizinhas imediatas, une intervalos sobrepostos e conserva a ordem do texto. Não são removidos números, negações ou conectivos que possam alterar o sentido. Casos de referência pronominal não resolvida recebem marcação específica.

O tokenizador e a revisão dos pesos são fixados. A entrada é limitada a 512 tokens, incluindo os especiais do modelo, e o processamento registra o comprimento original, o utilizado e a presença do alvo após o corte. A seleção focal procura reduzir a perda de informação relevante; seu benefício será verificado, não presumido.

As probabilidades das três classes são preservadas. O mapeamento entre índices e classes é validado com a configuração do checkpoint. Saídas incompletas ou inválidas produzem erro rastreável, em vez de um rótulo neutro. Essa regra evita que falhas computacionais sejam incorporadas à medida como observações válidas.

### 4.6 Formulação do ITI

Para o par notícia–empresa, define-se o escore:

\[
s_{i,c}=p^+_{i,c}-p^-_{i,c}.
\]

Para os documentos únicos elegíveis do dia civil, calcula-se a média:

\[
S_{c,d}=\frac{1}{n_{c,d}}\sum_{i=1}^{n_{c,d}}s_{i,c},\quad n_{c,d}>0.
\]

A entrada operacional é igual a essa média nos dias com notícias e a zero nos dias elegíveis com cobertura auditada e sem novo documento observado. Dias de cobertura desconhecida ou falha produzem ausência de estado na série estrita; a retomada exige reinicialização e novo aquecimento. Uma série condicionada apenas ao corpus observado pode ser produzida separadamente para diagnóstico exploratório. A média original permanece ausente quando seu denominador é zero. Assim, a implementação distingue “nenhuma notícia” de “média de sentimento igual a zero”.

A recorrência é:

\[
ITI^{(H)}_{c,d}=2^{-1/H}ITI^{(H)}_{c,d-1}+(1-2^{-1/H})X_{c,d}.
\]

H é medido em dias civis e o estado inicial é zero. A configuração principal utiliza H=7; H=2 e H=14 são sensibilidades. O calendário inclui dias sem negociação, e a avaliação começa depois de um aquecimento de 70 dias. A série é construída até o último cutoff avaliado, mesmo quando não existem notícias recentes.

Nos dias sem novo impulso, o índice decai em direção a zero. Isso é uma regra da representação, não uma conclusão sobre neutralidade econômica. Volume, negatividade e dispersão das probabilidades são mantidos como diagnósticos separados. A fórmula principal não multiplica confiança, magnitude, tipo de evento ou relevância heurística.

### 4.7 Sinais semanais e retornos

O alinhamento utiliza semanas identificadas pela sexta-feira civil e o último pregão efetivo de cada semana. Para acomodar horários incompletos, o sinal principal é o estado do fim do dia civil anterior a esse pregão. A escolha garante uma defasagem conservadora em relação ao preço inicial do retorno, ao custo de não incorporar notícias do próprio dia de fechamento.

Notícias com apenas data recebem disponibilidade assumida no final daquela data, com marcação explícita. Documentos sem data verificável ou sem versão temporal adequada não entram no painel estrito. A análise reconhece que textos recuperados retrospectivamente podem ter sido atualizados depois da publicação; a regra de cutoff não elimina essa limitação de conteúdo.

O retorno de h semanas é:

\[
R^{(h)}_{c,w}=\log\left(\frac{P^{adj}_{c,w+h}}{P^{adj}_{c,w}}\right),\quad h\in\{1,2,4\}.
\]

Os preços e retornos são organizados no calendário completo antes da junção com notícias. Portanto, uma semana sem sinal não desloca o horizonte das demais. Ausências de preço necessárias ao cálculo permanecem ausentes, com motivo documentado. A origem dos dados e a política de ajustes corporativos são registradas no manifesto.

### 4.8 Comparadores e teste principal

O comparador principal é a entrada diária sem memória, amostrada no mesmo cutoff do ITI. Essa escolha mantém constantes notícias, probabilidades, calendário e operador semanal. A única transformação adicional é a recorrência temporal. A média das notícias de uma semana pode ser apresentada como referência complementar, mas não representa essa ablação isolada.

A comparação principal utiliza a diferença entre correlações de Spearman com retorno de uma semana, para H=7. O teste é bilateral e a hipótese substantiva de benefício exige diferença positiva e associação positiva do candidato. São apresentados os dois coeficientes, sua diferença, intervalo de confiança e tamanho da amostra.

A reamostragem utiliza blocos móveis pareados de quatro semanas e 10.000 replicações, com semente fixa. Blocos de duas e oito semanas constituem sensibilidades. Lacunas não são comprimidas em uma falsa sequência temporal. Quando a amostra ou a variabilidade forem insuficientes, a comparação será registrada como indisponível para inferência, preservando a descrição dos dados.

A família secundária inclui variações de meia-vida, horizonte, métrica, entrada textual e fórmula. Os oito contrastes previamente estabelecidos recebem ajuste de Holm. Sensibilidades e contrastes adicionais motivados pelos resultados serão identificados como exploratórios. A taxa de vitórias das campanhas antigas não é o desfecho principal da nova avaliação.

### 4.9 Ameaças à validade

A validade do construto depende da correspondência entre o critério humano e o sinal do classificador. A validade temporal depende de datas, versões dos textos e preços. A validade estatística é limitada pelo número de semanas, pela dependência e pela concentração de acontecimentos. A validade externa permanece restrita à empresa, às fontes e ao período efetivamente examinados.

O protocolo reduz alguns riscos por meio de congelamento de versões, comparação pareada e janela externa. Ele não elimina cobertura seletiva, ambiguidade econômica ou ausência de fatores de mercado. Essas condições serão retomadas na discussão de acordo com as evidências observadas, sem transformar uma limitação possível em explicação comprovada de um resultado.

## Capítulo 5 — Ambiente computacional e reprodutibilidade

### 5.1 Organização do software

O Financial-Sentiment-Lab separa coleta, leitura de dados, modelos, construção de índices, avaliação e visualização. A reformulação preserva essa organização. Os modelos fornecem predições padronizadas; a construção do índice utiliza essas predições sem consultar retornos; a avaliação financeira incorpora o mercado posteriormente. Essa separação reduz o risco de informação do alvo contaminar a geração do sinal.

Configurações, versões e hashes acompanham cada execução. As probabilidades são reutilizadas entre meias-vidas, evitando repetir inferência quando apenas a transformação temporal muda. A identificação da execução distingue formulação, corpus, entrada textual e checkpoint. Uma reprodução histórica permanece separada de uma campanha com protocolo novo.

### 5.2 Uso do Santos Dumont

O processamento com GPU é organizado para o supercomputador Santos Dumont, mantido pelo Laboratório Nacional de Computação Científica [@lnccSdumont]. A documentação do projeto registra uma execução anterior nesse ambiente. Na nova campanha, o SDumont será utilizado como infraestrutura computacional para inferência e medição de recursos; sua utilização não constitui evidência da validade do índice.

A submissão é realizada por Slurm. Os recursos solicitados são registrados separadamente dos recursos alocados e de sua utilização observada. O script histórico requisita um nó, uma GPU, 30 CPUs e 32G de memória por até vinte minutos. Esses valores caracterizam aquela configuração de submissão; não são apresentados como necessidade definitiva da nova formulação nem como utilização efetiva medida.

A nova configuração é definida após um teste pequeno, considerando tempo, memória e aproveitamento da GPU. O ambiente registra modelo de processador e acelerador, memória disponível para a tarefa, versões de bibliotecas, driver e runtime CUDA. Essa descrição permite reproduzir as condições da execução sem confundir a capacidade total do supercomputador com os recursos de um único job.

**PREENCHIMENTO AUTOMÁTICO:** inserir tabela de recursos solicitados, alocados e observados a partir do novo manifesto e de `sacct`. CPU, GPU e memória específicas devem vir desses registros. Até existirem, manter na versão pré-execução a indicação “configuração efetiva da nova campanha pendente de medição”.

### 5.3 Medição de desempenho

O monitoramento distingue carregamento do modelo, preparação textual, inferência, agregação e escrita. Essa decomposição é necessária porque acelerar o processamento neural pode não reduzir na mesma proporção o tempo total. Documentos por segundo e tokens por segundo são informados junto ao tamanho dos lotes, ao comprimento das entradas e à precisão numérica.

A medição de GPU considera sua execução assíncrona, com sincronização nas fronteiras das fases cronometradas. O aquecimento é separado das repetições utilizadas no resumo de desempenho. O tempo de espera na fila não integra o tempo de inferência, embora possa ser apresentado como aspecto operacional.

Memória do processo, memória CUDA e utilização do dispositivo são medidas distintas. O relatório informa a origem e a disponibilidade de cada métrica. Uma comparação CPU–GPU utiliza a mesma carga e explicita se o resultado representa apenas inferência ou o fluxo completo. Não se atribui ganho de velocidade sem uma referência medida em condições comparáveis.

### 5.4 Benefícios e limitações

A execução no ambiente HPC oferece condições para processar lotes e ampliar comparações mantendo registro do ambiente. O reaproveitamento de predições reduz o custo de experimentar diferentes regras temporais. Esses benefícios operacionais serão quantificados quando existirem medições da nova campanha.

Há também limitações: tempo de fila, limites de execução, dependências de software, capacidade de memória e diferenças numéricas entre dispositivos. Um corpus pequeno pode não utilizar plenamente a GPU. A necessidade de preservar ativos localmente e retomar trabalhos interrompidos orienta o planejamento da execução. O desempenho computacional será discutido separadamente da qualidade da classificação e da evidência financeira.

## Capítulo 6 — Resultados preliminares e discussão

### 6.1 Aprendizados da etapa anterior — texto utilizável agora

A etapa exploratória permitiu estruturar o fluxo de notícias, classificação, agregação e avaliação. Seu principal resultado metodológico foi mostrar que a execução de uma fórmula não basta para validar o significado do índice. A qualidade do sinal textual, as versões do corpus e o alinhamento temporal condicionam a interpretação dos resultados.

No diagnóstico formal histórico descrito no documento de qualificação, cem notícias foram anotadas pelo autor. O classificador apresentou 50% de acurácia, kappa de aproximadamente 0,197 e F1 macro próximo de 0,45. Das 67 notícias anotadas como neutras, 35 receberam uma classe positiva ou negativa. Esses valores descrevem aquela amostra e protocolo; não constituem uma estimativa independente de desempenho em todo o corpus.

A classe neutra majoritária também mostra por que acurácia isolada é insuficiente. Um classificador constante neutro alcançaria 67% nessa amostra. A comparação não demonstra que ele é adequado à tarefa, mas evidencia que a avaliação deve considerar classes minoritárias, macro-F1 e o critério de anotação. O resultado orientou a separação entre sentimento do documento e informação referente à empresa.

A documentação canônica registra seis comparações favoráveis em 24 para a configuração R1, sem diferenças significativas pelo procedimento então empregado. Outros números pertencem a execuções legadas com corpus ou condições diferentes. A reconciliação dessas versões é parte do resultado de engenharia da pesquisa, e impede selecionar retrospectivamente a contagem mais favorável como síntese do estudo.

A revisão da fórmula mostrou ainda que alguns fatores influenciavam tanto o escore individual quanto a ponderação diária. Sua retirada da especificação principal reduz interações e torna a comparação mais interpretável. Isso não prova que todo peso adicional seja inútil; estabelece uma formulação de referência cuja complexidade pode ser ampliada apenas diante de evidência específica.

### 6.2 Caracterização da nova campanha

**PREENCHIMENTO APÓS EXECUÇÃO:** gerar a tabela de corpus e apresentar, em prosa, o total elegível, a cobertura temporal e as perdas relevantes. Identificar explicitamente o conjunto de desenvolvimento e o conjunto externo, ou declarar que a campanha permaneceu exploratória. Inserir run_id e hashes em apêndice, mantendo no capítulo apenas o necessário para interpretar a amostra.

Modelo de redação a completar com o registro: “A campanha utilizou [n] pares notícia–empresa entre [início] e [fim]. Após [regras e perdas], permaneceram [n] semanas elegíveis para a comparação principal. A proporção de documentos com horário conhecido foi [valor]; os demais seguiram a política conservadora de disponibilidade. O período [intervalo] foi reservado para avaliação externa e não participou da definição de parâmetros.” Se a última afirmação não for sustentada, substituí-la por descrição explícita da natureza exploratória.

### 6.3 Qualidade textual

**PREENCHIMENTO APÓS EXECUÇÃO:** inserir concordância pré-adjudicação, matriz de confusão e métricas por view. Comparar contexto e documento sobre os mesmos itens, informando retenção e truncamento. Descrever de três a cinco padrões de erro sustentados por exemplos de desenvolvimento, sem expor dados pessoais dos anotadores.

Texto interpretativo obrigatório: “As métricas são condicionadas ao protocolo de anotação e à amostra avaliável. O recorte focal [apresentou/não apresentou] benefício no critério textual adotado. Esse resultado [sustenta/limita] a interpretação do escore como polaridade referente à empresa e não determina, isoladamente, sua associação com retornos.” Escolher a redação somente após analisar estimativas e intervalos.

### 6.4 Associação temporal e ablações

**PREENCHIMENTO APÓS EXECUÇÃO:** apresentar primeiro o contraste H7 versus Soft, com as duas correlações, Δ, IC, p e n. Depois mostrar a família secundária completa, inclusive resultados indisponíveis e p ajustados. Não abrir a discussão com o melhor resultado entre sensibilidades.

Texto-base: “A comparação principal mantém constantes corpus, classificador, preparação textual e cutoff. Assim, a diferença observada corresponde à inclusão da memória definida no protocolo. A estimativa de Δ foi [valor], com intervalo [limites]. Esse resultado [sustenta/não oferece evidência suficiente para sustentar] a hipótese de associação incremental positiva no período avaliado.” Se as correlações forem negativas, explicar a direção e não usar “benefício” automaticamente.

### 6.5 Comportamento computacional

**PREENCHIMENTO APÓS EXECUÇÃO:** apresentar configuração efetiva e tempos, distinguindo campanha completa e benchmark. Explicar a fase dominante e os limites observados, apoiando cada conclusão em métricas. Caso não exista referência CPU comparável, relatar vazão e consumo sem afirmar speedup. Se não houver energia medida, não estimar sustentabilidade a partir da GPU utilizada.

### 6.6 Discussão integrada

**PREENCHIMENTO APÓS EXECUÇÃO:** organizar a discussão em três perguntas: o sinal representa adequadamente o alvo? A memória acrescenta associação no critério previsto? A implementação permite reproduzir a medida com custo conhecido? Responder cada pergunta com sua própria evidência.

O encerramento deve distinguir contribuição efetivamente alcançada de objetivo ainda pendente. Uma associação inconclusiva não apaga a melhoria de rastreabilidade; um pipeline robusto não confirma a hipótese financeira. A conclusão integrada precisa preservar essa separação.

## Capítulo 7 — Considerações finais e plano de continuidade

### 7.1 Síntese da proposta — versão pré-execução

Esta pesquisa organiza a construção de um Índice Temporal Informacional a partir de notícias corporativas em português. A reformulação concentra a medida em polaridade referente à empresa, agregação diária e persistência por meia-vida. O desenho busca tornar explícita a contribuição da memória, mantendo separadas cobertura, diagnóstico textual e avaliação de mercado.

A etapa exploratória foi útil por revelar problemas de interpretação e de comparabilidade que não seriam resolvidos apenas com novos parâmetros. O novo protocolo incorpora esses aprendizados na seleção dos dados, na referência humana, no calendário e na preservação das execuções. A avaliação da formulação reformulada permanece necessária; não se conclui, nesta versão, superioridade estatística ou capacidade preditiva do ITI-v2.

**APÓS EXECUÇÃO:** substituir o último período pela síntese factual do contraste principal, das limitações textuais e do estado da avaliação externa, sem alterar retrospectivamente a hipótese.

### 7.2 Ampliação dos modelos

O FinBERT-PT-BR permanece como referência inicial por sua adequação temática e linguística e por permitir validar o procedimento. A arquitetura do laboratório admite outros modelos sob um contrato comum de entrada e saída. Essa extensão será examinada em etapa própria, para que a troca do classificador não seja confundida com alteração da fórmula temporal.

A comparação poderá incluir classificadores em português, modelos com pesos disponíveis para execução local e modelos por instruções voltados à empresa. Critérios de inclusão compreendem documentação, licença, versão fixa, recursos necessários e capacidade de representar a tarefa. A seleção será realizada em desenvolvimento e a avaliação preservará um conjunto humano externo.

Jev é considerado um candidato tecnológico para decisões estruturadas, conforme documentação de seu fornecedor [@typesafeJev]. Sua inclusão depende de acesso e avaliação; não se pressupõe disponibilidade de pesos abertos ou execução local no SDumont. Alegações de calibração do fornecedor não substituem verificação nas notícias desta pesquisa.

### 7.3 Combinação de modelos

Uma etapa posterior poderá comparar a média de distribuições de modelos elegíveis com seus componentes individuais. Essa combinação é uma hipótese de melhoria, não um procedimento que garanta maior precisão. Modelos com erros semelhantes podem reforçar a mesma interpretação incorreta, e uma média pode reduzir o desempenho do melhor participante.

A avaliação manterá fixos o conjunto de documentos, as classes e a referência humana. Probabilidades ausentes não serão substituídas por confiança declarada. Pesos aprendidos e calibração dependerão de dados separados do teste. Juízes automáticos poderão auxiliar na análise de divergências, mas não serão apresentados como anotadores humanos independentes.

### 7.4 Continuidade temporal e setorial

Após a avaliação do caso principal, a extensão poderá examinar períodos adicionais e outras empresas de saneamento. A comparabilidade exige cobertura suficiente, identificação de alvos e regras de anotação compatíveis. Ajustes motivados por uma nova empresa serão registrados como adaptação, não tratados como aplicação inalterada do método.

Também poderão ser estudadas entradas intradiárias, agrupamentos de republicações e modelos explícitos de previsão. Essas extensões exigem desenhos próprios. A prioridade é concluir a avaliação da formulação simples, de modo que futuras melhorias possam ser comparadas com uma referência estável e reproduzível.

## Apêndice A — Protocolo de anotação

O anotador recebe o texto preservado, título, empresa-alvo e identificador do item. Não recebe previsão do modelo, rótulo de outro participante ou retorno posterior. A pergunta é: “Considerando apenas as informações apresentadas, qual é a orientação predominante do acontecimento para as perspectivas econômicas ou operacionais da empresa indicada?”

As respostas de polaridade são positiva, negativa e neutra. O participante indica separadamente se o item é avaliável e se há ambiguidade. Quando o texto é insuficiente ou o alvo não possui conteúdo substantivo, marca não avaliável. Em casos com efeitos conflitantes sem direção predominante, pode marcar neutra e ambígua, preservando os trechos que motivaram a decisão.

Exemplos didáticos, sem constituir regras automáticas: uma interrupção que produz custo explicitamente atribuído à empresa pode sustentar polaridade negativa; uma melhora operacional relatada para a companhia pode sustentar positiva; uma agenda sem resultado ou efeito descrito pode ser neutra. A simples ocorrência de “tarifa”, “privatização” ou “investimento” não define a classe. O anotador deve considerar a relação descrita, não a reação que imagina para a bolsa.

O formulário armazena news_id, versão textual, empresa, anotador, versão do protocolo, avaliável, polaridade, ambiguidade, tipo de matéria, evidência, observação e data. As respostas independentes são preservadas. A adjudicação mantém os rótulos originais e acrescenta decisão, responsável e justificativa. Mudanças nas instruções geram nova versão e não redefinem silenciosamente rótulos históricos.

## Apêndice B — Rastreabilidade

Cada execução é associada a um manifesto com identificação do código, corpus, checkpoint, tokenizador, preparação textual, calendário, preços, configuração do índice e protocolo de avaliação. O manifesto também registra hardware e ambiente, início e fim, artefatos concluídos e eventuais falhas.

As tabelas e figuras do manuscrito são produzidas a partir de arquivos de resultados identificados por esse manifesto. A existência de um run_id repetido no histórico não é suficiente para demonstrar equivalência de execuções; a comparação exige os respectivos insumos e configurações. Resultados antigos não recuperáveis integralmente permanecem identificados como registros documentais, sem alegação de reprodução independente.

## Apêndice C — Especificação matemática e verificações

Com entrada em [-1,1], estado inicial nesse intervalo e 0<λ<1, cada atualização do ITI é uma combinação convexa do estado anterior e da entrada. Portanto, o índice permanece em [-1,1]. Sem novos impulsos, após k dias o estado é multiplicado por λ^k. Para λ=2^(-1/H), k=H reduz essa contribuição à metade.

A inicialização e o aquecimento são parte da definição. O uso de dias civis deve ser preservado na implementação; remover dias sem notícia altera a unidade de H. A amostragem semanal também é parte do método: ITI e baseline principal são selecionados no mesmo dia de referência, anterior ao último pregão da semana. Essas propriedades são verificadas por testes independentes da associação observada com retornos.

# Parte VI — Bibliografia e acervo de artigos

## 16. Política bibliográfica

A bibliografia principal abaixo sustenta o manuscrito proposto. Ela não pretende preservar referências antigas sem função argumentativa. Entradas não utilizadas podem permanecer no acervo histórico, mas não precisam aparecer na lista de referências da dissertação.

Status de verificação: Hiew, SemEval, FinEntity, BERT, Araci, Guo, EPU, GPR, DNSI, Artstein e documentação TypeSafe foram consultados em páginas primárias ou textos disponibilizados pelos autores/instituições. FinBERT-PT-BR foi conferido no registro SBC indexado e no model card do autor; a página SBC apresentou timeout na abertura integral. O DOI publicado de Shapiro foi conferido no registro da editora, e uma versão de trabalho está disponível no Fed. Algumas referências clássicas complementares já constavam do `.bib` do projeto; o Cursor deve conferir seus PDFs locais e registrar a página exata para afirmações específicas. Não declarar que todos os PDFs foram baixados ou lidos integralmente nesta etapa.

O BibTeX seguinte é a base pronta para o texto proposto. Antes da entrega final, validar todas as chaves na compilação e a correspondência entre PDF, versão e metadados. Não copiar o DOI provisório `XXXXXXX` exibido no template do preprint de Hiew; citar a versão arXiv identificada. Não usar o ano de acesso como ano de publicação de um artigo.

## 17. Artigos principais e links de acesso

Os links de PDF abaixo indicam cópias abertas quando identificadas. DOI e página de editora podem exigir acesso institucional; isso não é falha do plano. Não baixar páginas HTML com extensão `.pdf`. “Já presente” significa que o arquivo foi identificado na árvore Git consultada, não que seu conteúdo binário tenha sido validado nesta sessão.

| Referência / chave | Papel | Página/DOI | PDF aberto ou acesso | Situação no acervo consultado |
|---|---|---|---|---|
| Hiew et al., 2019; v2 2022 — `hiew2019bsi` | baseline corporativo | [arXiv](https://arxiv.org/abs/1906.09024) | [PDF v2](https://arxiv.org/pdf/1906.09024v2) | Adicionar |
| Cortis et al., 2017 — `cortis2017semeval5` | alvo e sentimento financeiro | [ACL](https://aclanthology.org/S17-2089/) | [PDF](https://aclanthology.org/S17-2089.pdf) | `cortis2017_semeval5.pdf`; corrigir autoria |
| Tang et al., 2023 — `tang2023finentity` | entidade e classe | [ACL](https://aclanthology.org/2023.emnlp-main.956/) | [PDF](https://aclanthology.org/2023.emnlp-main.956.pdf) | `tang2023_finentity.pdf`; corrigir páginas |
| Santos, Bianchi e Costa, 2023 — `santos2023finbert` | sinal PT-BR financeiro | [SBC](https://sol.sbc.org.br/index.php/bwaif/article/view/24960) / [DOI](https://doi.org/10.5753/bwaif.2023.231151) | Botão PDF da SBC; [registro USP](https://repositorio.usp.br/item/003279804) como alternativa | `santos2023_finbert_ptbr.pdf`; reutilizar antes de baixar |
| Shapiro, Sudhof e Wilson, 2022 — `shapiro2022fed` | sentimento de notícias | [DOI corrigido](https://doi.org/10.1016/j.jeconom.2020.07.053) | [Working paper do Fed, versão 2020](https://www.frbsf.org/wp-content/uploads/wp2017-01.pdf) | `shapiro2022_news_sentiment.pdf`; verificar se é artigo ou working paper |
| Buckman et al., 2020 — `buckman2020news` | descrição do decaimento do DNSI | [Fed](https://www.frbsf.org/research-and-insights/publications/economic-letter/2020/04/news-sentiment-time-of-covid-19/) | [PDF](https://www.frbsf.org/wp-content/uploads/el2020-08.pdf) | Adicionar |
| Baker, Bloom e Davis, 2016 — `baker2016epu` | construção e validação | [DOI](https://doi.org/10.1093/qje/qjw024) | [Versão dos autores, março/2016](https://www.policyuncertainty.com/media/EPU_BBD_Mar2016.pdf) | `baker2016_epu.pdf` |
| Caldara e Iacoviello, 2022 — `caldara2022gpr` | construto e validação | [DOI](https://doi.org/10.1257/aer.20191823) | [PDF dos autores](https://www.matteoiacoviello.com/gpr_files/GPR_PAPER.pdf) | Adicionar |
| Guo et al., 2017 — `guo2017calibration` | calibração | [PMLR](https://proceedings.mlr.press/v70/guo17a.html) | [PDF](https://proceedings.mlr.press/v70/guo17a/guo17a.pdf) | Adicionar |
| Devlin et al., 2019 — `devlin2019bert` | BERT | [ACL](https://aclanthology.org/N19-1423/) | [PDF](https://aclanthology.org/N19-1423.pdf) | Adicionar se ausente |
| Souza, Nogueira e Lotufo, 2020 — `souza2020bertimbau` | português brasileiro | [DOI](https://doi.org/10.1007/978-3-030-61377-8_28) | [Repositório dos autores](https://github.com/neuralmind-ai/portuguese-bert); PDF local já disponível | `souza2020_bertimbau.pdf` |
| Araci, 2019 — `araci2019finbert` | FinBERT | [arXiv](https://arxiv.org/abs/1908.10063) | [PDF](https://arxiv.org/pdf/1908.10063) | `araci2020_finbert.pdf`; ano no nome não determina ano bibliográfico |
| Tetlock, 2007 — `tetlock2007media` | mídia e finanças | [DOI](https://doi.org/10.1111/j.1540-6261.2007.01232.x) | Editora/acesso institucional ou PDF local | `tetlock2007_media.pdf` |
| Artstein e Poesio, 2008 — `artstein2008agreement` | concordância | [ACL](https://aclanthology.org/J08-4004/) | [PDF](https://aclanthology.org/J08-4004.pdf) | `artstein2008_intercoder.pdf` |
| Cohen, 1960 — `cohen1960kappa` | dois avaliadores | [DOI](https://doi.org/10.1177/001316446002000104) | Editora/acesso institucional ou PDF local | `cohen1960_kappa.pdf` |
| Fleiss, 1971 — `fleiss1971nominal` | painel de avaliadores | [DOI](https://doi.org/10.1037/h0031619) | Editora/acesso institucional | PDF não identificado na árvore consultada |
| Künsch, 1989 — `kunsch1989bootstrap` | dependência temporal | [DOI](https://doi.org/10.1214/aos/1176347265) | Página da editora via DOI; obter opção de PDF | Adicionar |
| Holm, 1979 — `holm1979multiple` | multiplicidade | [JSTOR](https://www.jstor.org/stable/4615733) | Acesso institucional, se necessário | Adicionar |

### Complementares para a continuidade

Estas referências não são requisitos ocultos para executar o núcleo. Adicionar ao manuscrito apenas quando a extensão correspondente for efetivamente desenvolvida.

| Referência | Uso possível | Link |
|---|---|---|
| Sinha et al., 2022, SEntFiN 1.0 | anotação orientada à entidade | [DOI](https://doi.org/10.1002/asi.24634); já existe `sinha2022_sentfin.pdf` |
| Daudert, 2022, FinLin | corpora financeiros por entidade | [DOI](https://doi.org/10.1007/s10579-021-09555-3); já existe `daudert2022_finlin.pdf` |
| Aguda et al., 2024 | modelos como anotadores auxiliares | [ACL](https://aclanthology.org/2024.lrec-main.885/) / [PDF](https://aclanthology.org/2024.lrec-main.885.pdf); já existe PDF no acervo |
| Loughran e McDonald, 2011 | limitações de vocabulários gerais | [DOI](https://doi.org/10.1111/j.1540-6261.2010.01625.x); já existe `loughran2011_baselines.pdf` |
| Zheng et al., 2023 | limites de avaliação por LLM | [arXiv](https://arxiv.org/abs/2306.05685) / [PDF](https://arxiv.org/pdf/2306.05685); não valida automaticamente juiz financeiro |

### Fontes técnicas, não artigos científicos

- [Model card do checkpoint inicial](https://huggingface.co/lucas-leme/FinBERT-PT-BR).
- [DNSI — página de dados](https://www.frbsf.org/research-and-insights/data-and-indicators/daily-news-sentiment-index/).
- [SDumont/LNCC](https://sdumont.lncc.br/) e [máquina](https://sdumont.lncc.br/machine.php?pg=machine).
- [Slurm sbatch](https://slurm.schedmd.com/sbatch.html) e [sacct](https://slurm.schedmd.com/sacct.html).
- [Jev — anúncio oficial](https://typesafe.ai/blog/introducing-system-one-models-and-jev) e [documentação oficial](https://docs.typesafe.ai/introduction).
- [Jev.ia.br](https://jev.ia.br/) e [matéria fornecida pelo usuário](https://olhardigital.com.br/2026/09/17/inteligencia-artificial/conheca-o-jev-nova-ia-do-cocriador-do-chatgpt-que-nao-conversa-e-foi-criada-para-tomar-decisoes-dentro-de-softwares/): referências de contexto, não comprovação científica de calibração ou licença aberta.

## 18. BibTeX para incorporar ao arquivo canônico

Preservar chaves existentes quando já utilizadas e substituir seus campos incorretos. A chave Araci muda para 2019; atualizar todas as citações antigas ou manter alias temporário fora da bibliografia final. Chaves de páginas institucionais usam data de acesso, sem inventar data de publicação.

```bibtex
@misc{hiew2019bsi,
  author = {Hiew, Joshua Zoen Git and Huang, Xin and Mou, Hao and Li, Duan and Wu, Qi and Xu, Yabo},
  title = {{BERT}-based Financial Sentiment Index and {LSTM}-based Stock Return Predictability},
  year = {2019},
  howpublished = {arXiv:1906.09024},
  note = {Versão 2, revisada em 7 de julho de 2022},
  doi = {10.48550/arXiv.1906.09024},
  url = {https://arxiv.org/abs/1906.09024v2}
}
@inproceedings{cortis2017semeval5,
  author = {Cortis, Keith and Freitas, André and Daudert, Tobias and Huerlimann, Manuela and Zarrouk, Manel and Handschuh, Siegfried and Davis, Brian},
  title = {{SemEval}-2017 Task 5: Fine-Grained Sentiment Analysis on Financial Microblogs and News},
  booktitle = {Proceedings of the 11th International Workshop on Semantic Evaluation (SemEval-2017)},
  year = {2017}, pages = {519--535},
  publisher = {Association for Computational Linguistics},
  doi = {10.18653/v1/S17-2089},
  url = {https://aclanthology.org/S17-2089/}
}
@inproceedings{tang2023finentity,
  author = {Tang, Yixuan and Yang, Yi and Huang, Allen and Tam, Andy and Tang, Justin},
  title = {{FinEntity}: Entity-level Sentiment Classification for Financial Texts},
  booktitle = {Proceedings of the 2023 Conference on Empirical Methods in Natural Language Processing},
  year = {2023}, pages = {15465--15471},
  publisher = {Association for Computational Linguistics},
  doi = {10.18653/v1/2023.emnlp-main.956},
  url = {https://aclanthology.org/2023.emnlp-main.956/}
}
@inproceedings{santos2023finbert,
  author = {Santos, Lucas L. and Bianchi, Reinaldo A. C. and Costa, Anna H. R.},
  title = {{FinBERT-PT-BR}: Análise de Sentimentos de Textos em Português do Mercado Financeiro},
  booktitle = {Anais do II Brazilian Workshop on Artificial Intelligence in Finance},
  publisher = {Sociedade Brasileira de Computação},
  year = {2023}, pages = {144--155},
  doi = {10.5753/bwaif.2023.231151},
  url = {https://sol.sbc.org.br/index.php/bwaif/article/view/24960}
}
@article{shapiro2022fed,
  author = {Shapiro, Adam Hale and Sudhof, Moritz and Wilson, Daniel J.},
  title = {Measuring News Sentiment},
  journal = {Journal of Econometrics},
  year = {2022}, volume = {228}, number = {2}, pages = {221--243},
  doi = {10.1016/j.jeconom.2020.07.053},
  url = {https://doi.org/10.1016/j.jeconom.2020.07.053}
}
@techreport{buckman2020news,
  author = {Buckman, Shelby R. and Shapiro, Adam Hale and Sudhof, Moritz and Wilson, Daniel J.},
  title = {News Sentiment in the Time of {COVID-19}},
  institution = {Federal Reserve Bank of San Francisco},
  type = {FRBSF Economic Letter}, number = {2020-08}, year = {2020},
  url = {https://www.frbsf.org/wp-content/uploads/el2020-08.pdf}
}
@article{baker2016epu,
  author = {Baker, Scott R. and Bloom, Nicholas and Davis, Steven J.},
  title = {Measuring Economic Policy Uncertainty},
  journal = {The Quarterly Journal of Economics},
  year = {2016}, volume = {131}, number = {4}, pages = {1593--1636},
  doi = {10.1093/qje/qjw024},
  url = {https://doi.org/10.1093/qje/qjw024}
}
@article{caldara2022gpr,
  author = {Caldara, Dario and Iacoviello, Matteo},
  title = {Measuring Geopolitical Risk},
  journal = {American Economic Review},
  year = {2022}, volume = {112}, number = {4}, pages = {1194--1225},
  doi = {10.1257/aer.20191823},
  url = {https://www.matteoiacoviello.com/gpr_files/GPR_PAPER.pdf}
}
@inproceedings{guo2017calibration,
  author = {Guo, Chuan and Pleiss, Geoff and Sun, Yu and Weinberger, Kilian Q.},
  title = {On Calibration of Modern Neural Networks},
  booktitle = {Proceedings of the 34th International Conference on Machine Learning},
  series = {Proceedings of Machine Learning Research}, volume = {70},
  publisher = {PMLR}, year = {2017}, pages = {1321--1330},
  url = {https://proceedings.mlr.press/v70/guo17a.html}
}
@inproceedings{devlin2019bert,
  author = {Devlin, Jacob and Chang, Ming-Wei and Lee, Kenton and Toutanova, Kristina},
  title = {{BERT}: Pre-training of Deep Bidirectional Transformers for Language Understanding},
  booktitle = {Proceedings of the 2019 Conference of the North American Chapter of the Association for Computational Linguistics: Human Language Technologies, Volume 1},
  year = {2019}, pages = {4171--4186},
  publisher = {Association for Computational Linguistics},
  doi = {10.18653/v1/N19-1423},
  url = {https://aclanthology.org/N19-1423/}
}
@inproceedings{souza2020bertimbau,
  author = {Souza, Fábio and Nogueira, Rodrigo and Lotufo, Roberto},
  title = {{BERTimbau}: Pretrained {BERT} Models for Brazilian Portuguese},
  booktitle = {Intelligent Systems: BRACIS 2020},
  publisher = {Springer}, year = {2020}, pages = {403--417},
  doi = {10.1007/978-3-030-61377-8_28},
  url = {https://doi.org/10.1007/978-3-030-61377-8_28}
}
@misc{araci2019finbert,
  author = {Araci, Dogu},
  title = {{FinBERT}: Financial Sentiment Analysis with Pre-trained Language Models},
  year = {2019}, howpublished = {arXiv:1908.10063},
  doi = {10.48550/arXiv.1908.10063},
  url = {https://arxiv.org/abs/1908.10063}
}
@article{tetlock2007media,
  author = {Tetlock, Paul C.},
  title = {Giving Content to Investor Sentiment: The Role of Media in the Stock Market},
  journal = {The Journal of Finance},
  year = {2007}, volume = {62}, number = {3}, pages = {1139--1168},
  doi = {10.1111/j.1540-6261.2007.01232.x},
  url = {https://doi.org/10.1111/j.1540-6261.2007.01232.x}
}
@article{artstein2008agreement,
  author = {Artstein, Ron and Poesio, Massimo},
  title = {Inter-Coder Agreement for Computational Linguistics},
  journal = {Computational Linguistics},
  year = {2008}, volume = {34}, number = {4}, pages = {555--596},
  doi = {10.1162/coli.07-034-R2},
  url = {https://aclanthology.org/J08-4004/}
}
@article{cohen1960kappa,
  author = {Cohen, Jacob},
  title = {A Coefficient of Agreement for Nominal Scales},
  journal = {Educational and Psychological Measurement},
  year = {1960}, volume = {20}, number = {1}, pages = {37--46},
  doi = {10.1177/001316446002000104},
  url = {https://doi.org/10.1177/001316446002000104}
}
@article{fleiss1971nominal,
  author = {Fleiss, Joseph L.},
  title = {Measuring Nominal Scale Agreement Among Many Raters},
  journal = {Psychological Bulletin},
  year = {1971}, volume = {76}, number = {5}, pages = {378--382},
  doi = {10.1037/h0031619},
  url = {https://doi.org/10.1037/h0031619}
}
@article{kunsch1989bootstrap,
  author = {Künsch, Hans R.},
  title = {The Jackknife and the Bootstrap for General Stationary Observations},
  journal = {The Annals of Statistics},
  year = {1989}, volume = {17}, number = {3}, pages = {1217--1241},
  doi = {10.1214/aos/1176347265},
  url = {https://doi.org/10.1214/aos/1176347265}
}
@article{holm1979multiple,
  author = {Holm, Sture},
  title = {A Simple Sequentially Rejective Multiple Test Procedure},
  journal = {Scandinavian Journal of Statistics},
  year = {1979}, volume = {6}, number = {2}, pages = {65--70},
  url = {https://www.jstor.org/stable/4615733}
}
@misc{lnccSdumont,
  author = {{Laboratório Nacional de Computação Científica}},
  title = {Santos Dumont: Sistema Brasileiro de Computação Petaflópica},
  url = {https://sdumont.lncc.br/},
  urlaccessdate = {22 out. 2026},
  note = {Documentação institucional; configuração efetiva registrada por execução}
}
@misc{typesafeJev,
  author = {{TypeSafe AI}},
  title = {Introducing System One Models and Jev},
  year = {2026},
  url = {https://typesafe.ai/blog/introducing-system-one-models-and-jev},
  urlaccessdate = {22 out. 2026},
  note = {Anúncio técnico do fornecedor, publicado em 15 set. 2026; não é artigo revisado por pares}
}
```

## 19. Aquisição e validação dos PDFs pelo Cursor

1. Inventariar `docs/references/pdfs/` antes de baixar; reutilizar arquivos válidos já existentes.
2. Para cada chave principal, manter `bibliography_manifest.csv` com chave, título, versão, URL primária, URL do PDF, caminho, SHA256, licença/acesso, data de consulta e status.
3. Baixar somente de editoras, repositórios acadêmicos ou páginas dos autores. Não contornar paywalls. Usar timeout e limite de tentativas.
4. Conferir cabeçalho `%PDF-`, tamanho, abertura por leitor e primeira página; extrair título/autores/ano para comparação. Arquivo com status HTTP 200 pode ser tela de bloqueio HTML.
5. Renomear com padrão `autor_ano_tema.pdf`, preservando registro do nome antigo. O PDF araci2020 pode conter trabalho de 2019; corrigir metadados, não o conteúdo do artigo.
6. Distinguir working paper de versão publicada. Uma página específica de uma versão não deve ser atribuída à outra.
7. Criar nota curta em `docs/references/notas/<chave>.md`: referência, afirmação sustentada, seção/página real, limite e decisão metodológica relacionada. Não inventar número de página a partir de snippet.
8. Exportar `docs/references/downloads_pending.md` com links e motivo: indisponível, acesso institucional, URL quebrada, arquivo inconsistente ou versão não conferida. Esse é o checklist para Gabriel baixar manualmente.
9. Guardar na dissertação apenas citações relevantes. Notícias jornalísticas sobre Jev ficam como contexto; o anúncio/documentação oficial fundamenta a descrição da interface e não a precisão da tarefa.
10. Executar auditoria de chaves duplicadas, citações sem entrada, URLs provisórias e autores `Autor`, `Unknown`, `UTFPR` usados como pessoa. Não eliminar automaticamente trabalhos reais apenas porque exigem correção; impedir uso até resolver metadados essenciais.

## 20. Matriz de sustentação e escolhas próprias

| Afirmação/decisão | Base | Natureza |
|---|---|---|
| Polaridade deve identificar empresa-alvo | SemEval; FinEntity | Antecedente empírico/tarefa |
| Classificador inicial em português financeiro | FinBERT-PT-BR | Adequação inicial, não superioridade local |
| Hard-BSI com neutros no denominador | Hiew et al., seção 2.3, equação 1 da v2 | Fórmula antecedente |
| `p_pos-p_neg` | Esperança da codificação ordinal sob a distribuição do modelo | Derivação matemática própria; não atribuir fórmula a SemEval |
| Média diária simples | BSI como antecedente e decisão de agregação do projeto | Adaptação |
| Memória geométrica | Buckman et al.; contexto de Shapiro et al. | Motivação temporal |
| H7 principal e H2/H14 secundários | Protocolo desta pesquisa | Escolha própria pré-especificada |
| Entrada zero sem notícia | Regra de ausência de impulso desta pesquisa | Escolha própria; não neutralidade observada |
| Cutoff no dia anterior ao último pregão | Limitação de precisão temporal do corpus | Escolha própria conservadora |
| Corpus e validade precisam ser auditados | EPU/GPR como exemplos de construção | Princípio metodológico, sem transferência de fórmula |
| Calibração local precisa ser verificada | Guo et al. | Cuidado probabilístico |
| Blocos e família de testes | Künsch; Holm | Métodos; parâmetros operacionais próprios |
| Ensemble melhora o sinal | A ser testado | Hipótese futura, não fato |
| Jev tem pesos abertos | Não confirmado nas fontes primárias consultadas | Não afirmar |
| GPU produz speedup | Benchmark da própria campanha | Só afirmar após medir |

# Parte VII — Critérios finais e instrução ao Cursor

## 21. Definição de pronto antes da execução completa

- [ ] Arquitetura preservada e versões v1/v2 distinguíveis.
- [ ] Corpus, preços, calendário, checkpoint e protocolo fixados por hash.
- [ ] Datas do teste externo justificadas; quando inexistente, status exploratório explícito.
- [ ] Contextos focais rastreáveis e entrada efetiva registrada.
- [ ] Deduplicação causal e exclusões auditáveis.
- [ ] Fórmula v2 implementada sem pesos legados, calendário civil e aquecimento.
- [ ] Comparador principal amostrado no mesmo cutoff e a partir das mesmas predições.
- [ ] Retornos calculados no calendário completo antes de qualquer join.
- [ ] Testes de feriado, lacuna e disponibilidade temporal aprovados.
- [ ] Avaliação humana preparada sem exposição de rótulos/previsões.
- [ ] Configurações resolvidas e cache/retomada testados.
- [ ] Job Slurm validado em smoke; recursos e duração compatíveis com a fila.
- [ ] Monitoramento integrado ao pipeline existente.
- [ ] Documentação técnica, trilha e dashboard distinguem histórico e campanha nova.
- [ ] Manuscrito compilado na versão pré-execução, com bibliografia consistente.
- [ ] PDFs faltantes listados com links; nenhum download alegado sem arquivo validado.

## 22. Definição de pronto após execução

- [ ] Aplicação e Slurm terminam com estados coerentes; artefatos completos.
- [ ] Contagens, hashes, probabilidades, calendário e máscaras verificados.
- [ ] Referência humana caracterizada pelo trabalho efetivamente realizado.
- [ ] Contraste principal apresentado antes das sensibilidades.
- [ ] Todas as oito comparações secundárias reportadas; Holm aplicado conforme plano.
- [ ] Resultados indisponíveis têm motivo; nenhum NaN virou zero.
- [ ] Resultados históricos não se confundem com novas execuções.
- [ ] Recursos solicitados/alocados/observados separados.
- [ ] Tabelas, figuras e números do LaTeX derivam de registro único.
- [ ] Resumo, abstract, metodologia factual e conclusão atualizados sem mudança oportunista da hipótese.
- [ ] Build final bloqueia marcadores pendentes e citações indefinidas.
- [ ] PDF renderizado e conferido, especialmente equações, tabelas, sumário e referências.
- [ ] Relatório final informa testes, comandos, limitações e caminho de reprodução.

## 23. Instrução final pronta para o Cursor

> Implemente este plano integralmente no Financial-Sentiment-Lab, em etapas verificáveis. Comece pela inspeção do checkout e das instruções locais. Preserve mudanças existentes e resultados históricos. Não copie código para um projeto paralelo nem substitua os módulos por scripts monolíticos. Cada etapa deve atualizar `iti_v2_progress.md`, incluir testes proporcionais às invariantes e deixar evidências do que foi verificado.
>
> Conclua primeiro todos os ajustes de código, configuração, documentação, bibliografia e LaTeX que independem de execução no SDumont e de anotação humana nova. Implemente e teste os comandos propostos antes de apresentá-los como funcionais. Gere o manuscrito pré-execução com o texto da Parte V, mantendo explícita a ausência de resultados do ITI-v2. Não preencher números por aproximação ou suposição.
>
> Prepare o pacote offline, o job e os comandos exatos para o SDumont. Se houver acesso válido no ambiente, use o fluxo autorizado; caso contrário, entregue a sequência a Gabriel e registre o bloqueio apenas dessa etapa. Não confunda preparar um job com executá-lo. Não use saída simulada como evidência experimental.
>
> Depois de receber os resultados e as anotações, siga a Parte IV. Atualize tabelas, figuras, capítulo de resultados e sínteses dependentes a partir dos artefatos reais, sem alterar retroativamente o protocolo. A entrega só está completa quando código, documentação, resultados e dissertação descrevem a mesma versão da pesquisa.
