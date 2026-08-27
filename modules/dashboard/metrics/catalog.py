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
