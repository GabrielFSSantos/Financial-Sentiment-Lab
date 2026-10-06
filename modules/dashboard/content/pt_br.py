"""Textos da interface em português (Brasil)."""

NAV_OVERVIEW = "Visão Geral"
NAV_DATASETS = "Datasets e Scraper"
NAV_MODELS = "Modelos"
NAV_RUNS = "Runs"
NAV_COMPARE = "Comparação"
NAV_EXPERIMENTS = "Experimentos"
NAV_RESEARCH = "Research"
NAV_TRAIL = "Trilha da pesquisa"

TAB_PANORAMA = "Panorama"
TAB_COVERAGE = "Cobertura temporal"
TAB_SAMPLE = "Amostra"
TAB_DISTRIBUTION = "Distribuição"
TAB_CLASSIFIER = "Qualidade do classificador"
TAB_SUMMARY = "Resumo"
TAB_ITI_CONFIG = "Configuração ITI"
TAB_ITI_SERIES = "Série ITI"
TAB_ITI_MARKET = "ITI vs mercado"
TAB_INCREMENTAL = "Incremental"
TAB_SERIES = "Séries"
TAB_RAW_METRICS = "Métricas brutas"
TAB_CAMPAIGN = "Campanha"
TAB_ALPHA = "Alpha"
TAB_ABLATIONS = "Ablações"

HELP_EXPANDER = "O que isto mostra?"
CHART_HELP_EXPANDER = HELP_EXPANDER

EXPLORATORY_CALLOUT = (
    "Os resultados de research são **exploratórios** e condicionados à qualidade do classificador. "
    "O gate de κ (≥ 0,40) e acurácia (≥ 70%) **não foi atingido** na amostra manual n=100 — "
    "consulte a aba *Qualidade do classificador* e a [trajetória da pesquisa](docs/research_trail/part-04-results.md) (Parte 4)."
)

PIPELINE_STEPS = [
    ("Coleta", "Scraper de notícias do setor de saneamento (corpus Sabesp)."),
    ("FinBERT", "Classificação de sentimento PT-BR por notícia (POS/NEG/NEU)."),
    ("ITI", "Índice temporal EWMA: impacto informacional líquido por empresa/dia."),
    ("Research", "Validação ITI vs baselines B0–B3 e retornos futuros (W-FRI)."),
    ("Conclusão", "Síntese exploratória — ver research_trail Parte 4."),
]

RESEARCH_PHASES = [
    ("F0", "Corpus e coleta", "Base de notícias strict Sabesp."),
    ("F1", "Auditoria metodológica", "Regras de inclusão e alinhamento temporal."),
    ("F2", "FinBERT e ITI", "Pipeline de sentimento e índice EWMA."),
    ("F3", "Baselines B0–B3", "Contagens, sentimento médio, ponderado e setorial."),
    ("F4", "Research semanal", "Alinhamento W-FRI e métricas incrementais."),
    ("F5", "Classificador", "Validação manual n=100 e gate κ."),
    ("F6", "Campanha Sabesp", "R0–R9: α, ablações e ensemble."),
]
