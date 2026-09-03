"""Textos explicativos dos gráficos do dashboard FSL."""

CHART_HELP: dict[str, str] = {
    "corpus_by_company": """
**O que é**

Ranking de empresas por volume de notícias no corpus filtrado.

**Eixos e variáveis**

- **Eixo Y:** empresa (ticker ou nome)
- **Eixo X:** quantidade de notícias

**Como interpretar**

Empresas com poucas notícias podem gerar ITI instável. Concentração em uma única empresa
limita a generalização dos resultados de research.
""",
    "corpus_by_source": """
**O que é**

Distribuição de notícias por portal/fonte de origem.

**Eixos e variáveis**

- **Eixo Y:** fonte (portal)
- **Eixo X:** quantidade de notícias

**Como interpretar**

Diversidade de fontes reduz viés editorial. Dominância de uma fonte pode espelhar agenda
do setor, não apenas eventos corporativos.
""",
    "corpus_time_series": """
**O que é**

Série temporal do volume de notícias coletadas (mês, semana ou dia conforme filtro).

**Eixos e variáveis**

- **Eixo X:** período
- **Eixo Y:** contagem de notícias

**Como interpretar**

Picos indicam cobertura intensa (eventos, resultados). Lacunas sugerem períodos sem coleta
ou ausência de matéria — relevante para overlap no research semanal.
""",
    "corpus_heatmap": """
**O que é**

Mapa de calor empresa × mês mostrando densidade de notícias.

**Eixos e variáveis**

- **Linhas:** empresas
- **Colunas:** meses
- **Cor:** volume de notícias

**Como interpretar**

Células vazias ou claras indicam baixa cobertura naquele mês. Útil para diagnosticar
gaps antes de interpretar ITI ou correlações com mercado.
""",
    "class_distribution": """
**O que é**

Distribuição das classes previstas pelo modelo (POS, NEG, NEU) na run selecionada.

**Eixos e variáveis**

- **Eixo Y:** classe prevista
- **Eixo X:** contagem de notícias

**Como interpretar**

Desbalanceamento forte (ex.: excesso de NEU) pode refletir corpus ou viés do classificador.
Não equivale a acurácia — para isso, use a aba *Qualidade do classificador*.
""",
    "sentiment_by_company": r"""
**O que é**

Sentimento contínuo médio (\(d\)) agregado por empresa na run.

**Eixos e variáveis**

- **Eixo X:** empresa
- **Eixo Y:** sentimento médio (\(d \in [-1, 1]\))

**Como interpretar**

Valores positivos indicam tom médio favorável nas notícias da empresa. Compare runs
ou empresas com cautela — o classificador não passou no gate κ na amostra manual.
""",
    "sentiment_time_series": r"""
**O que é**

Evolução diária do sentimento contínuo médio (\(d\)) ao longo do tempo.

**Eixos e variáveis**

- **Eixo X:** data
- **Eixo Y:** \(d\) médio

**Como interpretar**

Tendências sugerem mudança de tom na cobertura. Picos isolados podem corresponder a
eventos pontuais — cruze com a tabela de notícias no módulo Datasets.
""",
    "iti_daily": """
**O que é**

Série do **ITI líquido** diário: índice de impacto informacional (impacto − risco) com memória EWMA.

**Eixos e variáveis**

- **Eixo X:** data
- **Eixo Y:** ITI líquido

**Como interpretar**

Valores positivos sustentados sugerem impacto informacional líquido favorável no período.
O parâmetro α (EWMA) controla a persistência — runs com α maior suavizam menos o histórico.
""",
    "iti_vs_return": """
**O que é**

Dispersão entre ITI (eixo X) e **retorno logarítmico futuro** (eixo Y) no horizonte selecionado.

**Eixos e variáveis**

- **Eixo X:** ITI líquido (ou último valor da semana W-FRI)
- **Eixo Y:** `future_log_return_{h}` (h = 1, 2 ou 4 semanas)
- **Cor (opcional):** empresa

**Como interpretar**

Correlação visual **não implica causalidade**. Pontos dispersos ou poucos indicam sinal fraco.
Resultados são exploratórios — ver limitações do classificador (κ).
""",
    "incremental_delta": """
**O que é**

**Delta incremental** médio: diferença entre a métrica do ITI e a do baseline (B0–B3)
para o mesmo horizonte e empresa.

**Eixos e variáveis**

- **Eixo X:** baseline (B0, B1, B2, B3)
- **Eixo Y:** Δ médio (ITI − baseline)

**Como interpretar**

Δ > 0 indica que o ITI superou o baseline na média das comparações. Vitórias significativas
(ex.: 2/24) são contadas separadamente no `research_summary.json`.
""",
    "market_metrics_heatmap": """
**O que é**

Heatmap de métricas de mercado por baseline, horizonte e tipo de série (Pearson, Spearman, win rate).

**Eixos e variáveis**

- **Linhas:** série × horizonte
- **Colunas:** métrica
- **Cor:** valor numérico

**Como interpretar**

Permite comparar rapidamente qual baseline e horizonte têm associação mais forte com retornos.
Valores próximos de zero indicam pouco sinal linear ou monotônico.
""",
    "win_rate_by_run": """
**O que é**

Taxa de vitórias do ITI contra baselines B0–B2 por run de experimento.

**Eixos e variáveis**

- **Eixo X:** run_id
- **Eixo Y:** win rate (0–100%)

**Como interpretar**

Acima de 40% é o gate exploratório da campanha Sabesp. Compare sempre contra o baseline R0
e considere significância (bootstrap) na trajetória oficial.
""",
    "win_rate_heatmap": """
**O que é**

Visão matricial do win rate por run (útil quando há poucas runs selecionadas).

**Como interpretar**

Cores mais intensas = win rate maior. Use junto com a tabela de parâmetros para correlacionar
α e modo de horizonte com desempenho.
""",
    "alpha_vs_winrate": """
**O que é**

Relação entre o parâmetro **α (EWMA)** do ITI e o win rate de cada run da campanha.

**Eixos e variáveis**

- **Eixo X:** α
- **Eixo Y:** win rate
- **Rótulo:** run_id

**Como interpretar**

Busca-se α que maximize vitórias incrementais sem overfit. R1 (α=0,70) é o candidato principal
da campanha — confirme na tabela de experimentos e na Parte 4 da trajetória.
""",
    "ablation_bars": """
**O que é**

Win rate das **ablações** R3–R6 (desativação de dimensões m, r, e, u, q, h do ITI) vs baseline.

**Como interpretar**

Queda grande ao desativar uma dimensão sugere contribuição relevante. Ablações negativas
indicam que a dimensão pode adicionar ruído no recorte Sabesp.
""",
    "sentiment_compare_runs": """
**O que é**

Comparação do sentimento médio por empresa entre múltiplas runs selecionadas.

**Eixos e variáveis**

- **Eixo X:** empresa
- **Eixo Y:** sentimento médio
- **Cor:** run_id

**Como interpretar**

Divergências entre runs com mesmo corpus indicam efeito de parâmetros ITI ou modelo.
Runs idênticas em sentimento mas diferentes em win rate sugerem que o ganho vem do índice, não do classificador isolado.
""",
    "param_diff_table": """
**O que é**

Tabela de diferenças de parâmetros ITI entre duas runs (ex.: baseline R0 vs candidata).

**Colunas**

- **parameter:** nome do campo (α, `horizon_mode`, dimensões desabilitadas, etc.)
- **run_a / run_b:** valores em cada run

**Como interpretar**

Foque em α, `horizon_mode` (ewma_alpha vs fixed) e dimensões desabilitadas.
Valores mistos são exibidos como texto para compatibilidade com PyArrow.
""",
    "pipeline_journey": """
**O que é**

Visão do fluxo da pesquisa Financial Sentiment Lab: do corpus ao research.

**Etapas**

1. **Coleta** — scraper e corpus strict Sabesp
2. **FinBERT** — classificação POS/NEG/NEU
3. **ITI** — índice EWMA por empresa/dia
4. **Research** — validação vs baselines e mercado (W-FRI)
5. **Conclusão** — síntese exploratória (trajetoria.md)

**Limitação**

O classificador não atingiu o gate κ na validação manual — interprete research como hipótese, não prova.
""",
    "kappa_gate": """
**O que é**

Validação do classificador na amostra manual **n=100** (rótulos humanos vs previsões).

**Métricas**

- **Acurácia:** proporção de acertos (gate ≥ 70%)
- **Cohen's κ:** concordância além do acaso (gate ≥ 0,40)

**Como interpretar**

Nenhum modelo da bateria PT passou no gate na execução atual. Research e win rates são
**condicionados** a esse limite — não use para decisão de investimento sem revalidação.
""",
}
