"""Catálogo de explicações de métricas."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MetricInfo:
    key: str
    label: str
    description: str
    interpretation_guide: str
    higher_is_better: bool
    bands: tuple[tuple[float, float, str], ...]


METRICS: dict[str, MetricInfo] = {
    "win_rate": MetricInfo(
        key="win_rate",
        label="Taxa de vitórias (ITI vs baseline)",
        description="Proporção de comparações em que o ITI superou baselines B0–B2.",
        interpretation_guide="Valores acima de 50% indicam que o ITI vence baselines na maioria das comparações.",
        higher_is_better=True,
        bands=((0, 0.25, "fraco"), (0.25, 0.4, "abaixo do gate"), (0.4, 1.0, "promissor")),
    ),
    "pearson": MetricInfo(
        key="pearson",
        label="Correlação de Pearson",
        description="Associação linear entre ITI e retorno futuro.",
        interpretation_guide="Próximo de 1 ou -1 indica associação forte; próximo de 0 indica pouco sinal.",
        higher_is_better=True,
        bands=((0, 0.2, "fraco"), (0.2, 0.5, "moderado"), (0.5, 1.0, "forte")),
    ),
    "spearman": MetricInfo(
        key="spearman",
        label="Correlação de Spearman",
        description="Associação monotônica (não exige linearidade) entre ITI e retorno.",
        interpretation_guide="Útil quando relações são não-lineares.",
        higher_is_better=True,
        bands=((0, 0.2, "fraco"), (0.2, 0.5, "moderado"), (0.5, 1.0, "forte")),
    ),
    "f1": MetricInfo(
        key="f1",
        label="F1 Score",
        description="Equilíbrio entre precisão e recall das classificações.",
        interpretation_guide="Quanto maior, melhor o equilíbrio entre acertos e cobertura.",
        higher_is_better=True,
        bands=((0, 0.5, "fraco"), (0.5, 0.7, "moderado"), (0.7, 1.0, "bom")),
    ),
    "precision": MetricInfo(
        key="precision",
        label="Precisão",
        description="Das previsões positivas, quantas estavam corretas.",
        interpretation_guide="Alta precisão reduz falsos positivos.",
        higher_is_better=True,
        bands=((0, 0.5, "fraca"), (0.5, 0.75, "moderada"), (0.75, 1.0, "alta")),
    ),
    "recall": MetricInfo(
        key="recall",
        label="Recall",
        description="Dos casos positivos reais, quantos foram identificados.",
        interpretation_guide="Alto recall captura mais eventos relevantes.",
        higher_is_better=True,
        bands=((0, 0.5, "baixo"), (0.5, 0.75, "moderado"), (0.75, 1.0, "alto")),
    ),
    "news_count": MetricInfo(
        key="news_count",
        label="Quantidade de notícias",
        description="Volume de notícias no recorte analisado.",
        interpretation_guide="Baixo volume pode indicar cobertura insuficiente para inferências estáveis.",
        higher_is_better=True,
        bands=((0, 50, "muito baixo"), (50, 200, "moderado"), (200, 10000, "adequado")),
    ),
    "iti_liquido": MetricInfo(
        key="iti_liquido",
        label="ITI líquido",
        description="Índice de impacto informacional agregado (positivo menos risco).",
        interpretation_guide="Valores positivos sugerem impacto líquido positivo no período.",
        higher_is_better=True,
        bands=((-1, 0, "negativo"), (0, 0.1, "neutro"), (0.1, 1, "positivo")),
    ),
    "confidence": MetricInfo(
        key="confidence",
        label="Confiança do modelo",
        description="Probabilidade máxima atribuída à classe prevista.",
        interpretation_guide="Baixa confiança média sugere incerteza nas previsões.",
        higher_is_better=True,
        bands=((0, 0.5, "baixa"), (0.5, 0.75, "moderada"), (0.75, 1.0, "alta")),
    ),
    "kappa": MetricInfo(
        key="kappa",
        label="Cohen's κ (classificador)",
        description="Concordância entre rótulos manuais e previsões, além do acaso.",
        interpretation_guide="Gate da pesquisa: κ ≥ 0,40 na amostra n=100.",
        higher_is_better=True,
        bands=((-1, 0.2, "fraco — gate falhou"), (0.2, 0.4, "abaixo do gate"), (0.4, 1.0, "gate atendido")),
    ),
    "accuracy": MetricInfo(
        key="accuracy",
        label="Acurácia (classificador)",
        description="Proporção de previsões corretas na amostra manual.",
        interpretation_guide="Gate da pesquisa: acurácia ≥ 70% na amostra n=100.",
        higher_is_better=True,
        bands=((0, 0.5, "fraca"), (0.5, 0.7, "abaixo do gate"), (0.7, 1.0, "gate atendido")),
    ),
    "delta_win_rate": MetricInfo(
        key="delta_win_rate",
        label="Δ win rate vs baseline",
        description="Diferença de win rate entre run candidata e baseline R0.",
        interpretation_guide="Valores positivos indicam melhoria incremental na campanha.",
        higher_is_better=True,
        bands=((-1, -0.05, "piora relevante"), (-0.05, 0.05, "estável"), (0.05, 1.0, "melhoria")),
    ),
    "overlap_weeks": MetricInfo(
        key="overlap_weeks",
        label="Semanas alinhadas (overlap)",
        description="Pontos semanais com ITI e retorno futuro disponíveis.",
        interpretation_guide="Poucos pontos (~24) limitam poder estatístico.",
        higher_is_better=True,
        bands=((0, 15, "muito baixo"), (15, 30, "moderado"), (30, 500, "adequado")),
    ),
    "alpha_ewma": MetricInfo(
        key="alpha_ewma",
        label="Parâmetro α (EWMA)",
        description="Peso da observação atual na memória exponencial do ITI.",
        interpretation_guide="α maior reage mais rápido a notícias recentes; α menor suaviza o histórico.",
        higher_is_better=False,
        bands=((0, 0.3, "memória longa"), (0.3, 0.6, "intermediário"), (0.6, 1.0, "memória curta")),
    ),
    "significant_wins": MetricInfo(
        key="significant_wins",
        label="Vitórias significativas",
        description="Comparações com delta favorável e significância estatística (bootstrap).",
        interpretation_guide="Ex.: 2/24 comparações significativas na campanha Sabesp.",
        higher_is_better=True,
        bands=((0, 2, "muito baixo"), (2, 8, "moderado"), (8, 100, "alto")),
    ),
    "exploratory_caveat": MetricInfo(
        key="exploratory_caveat",
        label="Aviso exploratório",
        description=(
            "Resultados de research são exploratórios e condicionados ao classificador "
            "não validado (κ abaixo do gate)."
        ),
        interpretation_guide="Use para gerar hipóteses, não conclusões causais ou de investimento.",
        higher_is_better=False,
        bands=((0, 1, "sempre aplicável neste recorte")),
    ),
    "runs_count": MetricInfo(
        key="runs_count",
        label="Runs concluídas",
        description="Execuções de experimento disponíveis em outputs/.",
        interpretation_guide="Mais runs permitem comparação de α e ablações.",
        higher_is_better=True,
        bands=((0, 3, "inicial"), (3, 8, "campanha parcial"), (8, 100, "campanha completa")),
    ),
}


def get_metric(key: str) -> MetricInfo | None:
    return METRICS.get(key)


def interpret_value(key: str, value: float | None) -> str:
    if value is None:
        return "Valor indisponível."
    info = get_metric(key)
    if not info:
        return ""
    for low, high, label in info.bands:
        if low <= value < high:
            return f"Resultado {label} para esta métrica ({info.interpretation_guide})"
    return info.interpretation_guide
