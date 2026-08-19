"""Construção do Índice Temporal Informacional (ITI).

Transforma previsões padronizadas em séries temporais persistentes
por empresa, setor e mercado, usando regras determinísticas e
transparentes definidas no relatório de pesquisa.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Mapping, Sequence

import numpy as np
import pandas as pd

from modules.experiment.common import column_series, numeric_series
from modules.experiment.config.loader import (
    ExperimentCombination,
    ResolvedConfiguration,
)
from modules.experiment.indexing.baselines import build_baselines_daily
from modules.experiment.indexing.dimensions import resolve_dimensions


class TemporalIndexError(RuntimeError):
    """Erro durante a construção do ITI."""


from modules.experiment.indexing.constants import DIMENSION_KEYS, DIMENSION_SHORT_NAMES

RESAMPLE_RULES: dict[str, str] = {
    "weekly": "W",
    "monthly": "ME",
    "quarterly": "QE",
}

RESAMPLE_OUTPUT_NAMES: dict[str, str] = {
    "weekly": "iti_weekly.csv",
    "monthly": "iti_monthly.csv",
    "quarterly": "iti_quarterly.csv",
}


@dataclass(frozen=True)
class TemporalIndexArtifacts:
    """DataFrames e caminhos produzidos para uma combinação."""

    news_impact: pd.DataFrame
    iti_daily: pd.DataFrame
    iti_sector_daily: pd.DataFrame
    iti_market_daily: pd.DataFrame
    resampled: dict[str, pd.DataFrame] = field(default_factory=dict)
    baselines_daily: pd.DataFrame | None = None


@dataclass(frozen=True)
class UncertaintyMergeResult:
    """Série de incerteza agregada entre modelos."""

    dataset_key: str
    disagreement_daily: pd.DataFrame
    iti_uncertainty_daily: pd.DataFrame


class TemporalIndexBuilder:
    """Calcula o ITI a partir de previsões de uma combinação."""

    def __init__(self, configuration: ResolvedConfiguration) -> None:
        self.configuration = configuration
        self.settings = dict(configuration.temporal_index)
        self._defaults = self._resolve_defaults()
        self._seen_titles: set[str] = set()

    @property
    def enabled(self) -> bool:
        return bool(self.settings.get("enabled", False))

    def build(
        self,
        *,
        combination: ExperimentCombination,
        predictions: pd.DataFrame,
    ) -> TemporalIndexArtifacts:
        if predictions.empty:
            raise TemporalIndexError(
                "Não é possível calcular o ITI sem previsões."
            )

        news_impact = build_news_impact_frame(
            predictions,
            defaults=self._defaults,
            settings=self.settings,
            seen_titles=self._seen_titles,
        )
        daily_impact = compute_daily_company_impact(news_impact)
        iti_daily = compute_iti_daily_series(
            daily_impact,
            alpha=self._alpha(),
            initial_value=self._initial_value(),
            horizon_mode=self._horizon_mode(),
        )
        iti_sector_daily = aggregate_level_series(
            iti_daily,
            level="sector",
        )
        iti_market_daily = aggregate_level_series(
            iti_daily,
            level="market",
        )

        resampled: dict[str, pd.DataFrame] = {}
        if self._resample_enabled():
            for frequency in self._resample_frequencies():
                resampled[frequency] = resample_iti_series(
                    iti_daily,
                    frequency=frequency,
                )

        baselines_daily = None
        baselines_settings = self.settings.get("baselines", {})
        if isinstance(baselines_settings, Mapping) and baselines_settings.get("enabled", False):
            baselines_daily = build_baselines_daily(predictions)

        return TemporalIndexArtifacts(
            news_impact=news_impact,
            iti_daily=iti_daily,
            iti_sector_daily=iti_sector_daily,
            iti_market_daily=iti_market_daily,
            resampled=resampled,
            baselines_daily=baselines_daily,
        )

    def _alpha(self) -> float:
        alpha = float(self.settings.get("alpha", 0.85))
        if not 0.0 < alpha < 1.0:
            raise TemporalIndexError(
                "temporal_index.alpha precisa estar entre 0 e 1."
            )
        return alpha

    def _initial_value(self) -> float:
        return float(self.settings.get("initial_value", 0.0))

    def _horizon_mode(self) -> str:
        horizon = self.settings.get("horizon", {})
        if isinstance(horizon, Mapping):
            return str(horizon.get("mode", "ewma_alpha")).strip().lower()
        return "ewma_alpha"

    @property
    def fail_on_error(self) -> bool:
        return bool(self.settings.get("fail_on_error", False))

    def _resolve_defaults(self) -> dict[str, float]:
        defaults_raw = self.settings.get("defaults", {})
        if not isinstance(defaults_raw, Mapping):
            raise TemporalIndexError(
                "temporal_index.defaults precisa ser um objeto YAML."
            )

        defaults: dict[str, float] = {}
        for key in DIMENSION_KEYS:
            value = defaults_raw.get(key, 1.0)
            try:
                numeric = float(value)
            except (TypeError, ValueError) as error:
                raise TemporalIndexError(
                    f"temporal_index.defaults.{key} precisa ser numérico."
                ) from error

            if not math.isfinite(numeric):
                raise TemporalIndexError(
                    f"temporal_index.defaults.{key} precisa ser finito."
                )

            defaults[key] = numeric

        return defaults

    def _resample_enabled(self) -> bool:
        resample = self.settings.get("resample", {})
        if not isinstance(resample, Mapping):
            return False
        return bool(resample.get("enabled", False))

    def _resample_frequencies(self) -> tuple[str, ...]:
        resample = self.settings.get("resample", {})
        if not isinstance(resample, Mapping):
            return ()

        frequencies = resample.get("frequencies", [])
        if not isinstance(frequencies, list):
            raise TemporalIndexError(
                "temporal_index.resample.frequencies precisa ser uma lista."
            )

        normalized: list[str] = []
        for item in frequencies:
            frequency = str(item).strip().lower()
            if frequency not in RESAMPLE_RULES:
                supported = ", ".join(sorted(RESAMPLE_RULES))
                raise TemporalIndexError(
                    "Frequência de reamostragem não suportada: "
                    f"{item!r}. Use: {supported}."
                )
            normalized.append(frequency)

        return tuple(normalized)


def build_news_impact_frame(
    predictions: pd.DataFrame,
    *,
    defaults: Mapping[str, float],
    settings: Mapping[str, Any] | None = None,
    seen_titles: set[str] | None = None,
) -> pd.DataFrame:
    """Calcula dimensões e impactos por notícia."""

    frame = predictions.copy()
    required = (
        "news_id",
        "date",
        "continuous_sentiment",
        "confidence",
    )

    for column in required:
        if column not in frame.columns:
            raise TemporalIndexError(
                f"Coluna obrigatória ausente para o ITI: {column}."
            )

    frame["date"] = pd.to_datetime(
        column_series(frame, "date"),
        errors="coerce",
    )
    if frame["date"].isna().any():
        raise TemporalIndexError(
            "Existem datas inválidas nas previsões."
        )

    frame["d"] = numeric_series(
        column_series(frame, "continuous_sentiment"),
    ).astype(float)
    frame["c"] = numeric_series(
        column_series(frame, "confidence"),
    ).astype(float)

    dimensions = resolve_dimensions(
        frame,
        settings=dict(settings or {}),
        defaults=defaults,
        seen_titles=seen_titles,
    )
    for key in DIMENSION_KEYS:
        short = DIMENSION_SHORT_NAMES[key]
        frame[short] = dimensions[key]

    frame["I_n"] = (
        frame["d"]
        * frame["m"]
        * frame["r"]
        * frame["c"]
        * frame["e"]
        * frame["u"]
    )
    frame["R_n"] = (
        np.maximum(0.0, -frame["d"])
        * frame["m"]
        * frame["r"]
        * frame["c"]
        * frame["q"]
    )
    frame["w_n"] = frame["c"] * frame["r"] * frame["u"]

    output_columns = [
        "news_id",
        "date",
        "company",
        "sector",
        "ticker",
        "d",
        "m",
        "r",
        "c",
        "e",
        "h",
        "q",
        "u",
        "I_n",
        "R_n",
        "w_n",
    ]

    for column in ("company", "sector", "ticker"):
        if column not in frame.columns:
            frame[column] = None

    return frame.loc[:, output_columns].copy()


def compute_daily_company_impact(
    news_impact: pd.DataFrame,
) -> pd.DataFrame:
    """Agrega impacto líquido e de risco por empresa e dia."""

    frame = news_impact.copy()
    frame["company"] = frame["company"].fillna("UNKNOWN")
    frame["sector"] = frame["sector"].fillna("UNKNOWN")
    frame["weighted_I"] = frame["I_n"] * frame["w_n"]
    frame["weighted_R"] = frame["R_n"] * frame["w_n"]

    grouped = frame.groupby(
        ["company", "sector", "date"],
        dropna=False,
        as_index=False,
    ).agg(
        weighted_I=("weighted_I", "sum"),
        weighted_R=("weighted_R", "sum"),
        weight_sum=("w_n", "sum"),
        mean_I=("I_n", "mean"),
        mean_R=("R_n", "mean"),
        news_count=("news_id", "count"),
        mean_confidence=("c", "mean"),
        mean_relevance=("r", "mean"),
        mean_horizon=("h", "mean"),
    )

    grouped["impacto_dia"] = np.where(
        grouped["weight_sum"] > 0.0,
        grouped["weighted_I"] / grouped["weight_sum"],
        grouped["mean_I"],
    )
    grouped["risco_dia"] = np.where(
        grouped["weight_sum"] > 0.0,
        grouped["weighted_R"] / grouped["weight_sum"],
        grouped["mean_R"],
    )

    return grouped.loc[
        :,
        [
            "company",
            "sector",
            "date",
            "impacto_dia",
            "risco_dia",
            "news_count",
            "mean_confidence",
            "mean_relevance",
            "mean_horizon",
        ],
    ].sort_values(["company", "date"]).reset_index(drop=True)


def _effective_alpha(alpha: float, horizon: float, *, mode: str) -> float:
    if mode != "ewma_alpha":
        return alpha
    safe_horizon = max(float(horizon), 0.05)
    effective = alpha ** (1.0 / safe_horizon)
    return float(min(max(effective, 0.01), 0.999))


def compute_iti_daily_series(
    daily_impact: pd.DataFrame,
    *,
    alpha: float,
    initial_value: float,
    horizon_mode: str = "ewma_alpha",
) -> pd.DataFrame:
    """Atualiza o ITI recursivamente por empresa."""

    if daily_impact.empty:
        return empty_iti_daily()

    rows: list[dict[str, Any]] = []

    for (company, sector), group in daily_impact.groupby(
        ["company", "sector"],
        dropna=False,
    ):
        group = group.sort_values("date")
        impact_by_date = {
            pd.Timestamp(row["date"]): row
            for _, row in group.iterrows()
        }
        dates = pd.date_range(
            start=group["date"].min(),
            end=group["date"].max(),
            freq="D",
        )

        iti_liquido = float(initial_value)
        iti_risco = float(initial_value)

        for current_date in dates:
            timestamp = pd.Timestamp(current_date)
            if timestamp in impact_by_date:
                daily_row = impact_by_date[timestamp]
                impacto_dia = float(daily_row["impacto_dia"])
                risco_dia = float(daily_row["risco_dia"])
                news_count = int(daily_row["news_count"])
                mean_horizon = float(daily_row.get("mean_horizon", 1.0))
                alpha_eff = _effective_alpha(alpha, mean_horizon, mode=horizon_mode)
                iti_liquido = (
                    alpha_eff * iti_liquido
                    + (1.0 - alpha_eff) * impacto_dia
                )
                iti_risco = (
                    alpha_eff * iti_risco
                    + (1.0 - alpha_eff) * risco_dia
                )
            else:
                impacto_dia = 0.0
                risco_dia = 0.0
                news_count = 0
                alpha_eff = alpha
                iti_liquido = alpha_eff * iti_liquido
                iti_risco = alpha_eff * iti_risco

            rows.append(
                {
                    "date": timestamp.date().isoformat(),
                    "company": company,
                    "sector": sector,
                    "impacto_dia": impacto_dia,
                    "risco_dia": risco_dia,
                    "news_count": news_count,
                    "iti_liquido": iti_liquido,
                    "iti_risco": iti_risco,
                }
            )

    return pd.DataFrame(rows)


def aggregate_level_series(
    iti_daily: pd.DataFrame,
    *,
    level: Literal["sector", "market"],
) -> pd.DataFrame:
    """Agrega o ITI diário por setor ou mercado."""

    if iti_daily.empty:
        return empty_level_daily(level)

    frame = iti_daily.copy()
    frame["date"] = pd.to_datetime(frame["date"])

    if level == "sector":
        group_columns = ["date", "sector"]
    else:
        group_columns = ["date"]

    grouped = (
        frame.groupby(group_columns, dropna=False)
        .agg(
            impacto_dia=("impacto_dia", "mean"),
            risco_dia=("risco_dia", "mean"),
            iti_liquido=("iti_liquido", "mean"),
            iti_risco=("iti_risco", "mean"),
            news_count=("news_count", "sum"),
            company_count=("company", "nunique"),
        )
        .reset_index()
    )

    grouped["date"] = grouped["date"].dt.date.astype(str)
    grouped["aggregation_level"] = level
    return grouped


def resample_iti_series(
    iti_daily: pd.DataFrame,
    *,
    frequency: str,
) -> pd.DataFrame:
    """Reamostra a série diária por empresa."""

    if iti_daily.empty:
        return empty_resampled(frequency)

    rule = RESAMPLE_RULES[frequency]
    rows: list[dict[str, Any]] = []

    frame = iti_daily.copy()
    frame["date"] = pd.to_datetime(frame["date"])

    for (company, sector), group in frame.groupby(
        ["company", "sector"],
        dropna=False,
    ):
        indexed = group.set_index("date").sort_index()

        for period_start, period_df in indexed.resample(rule):
            if period_df.empty:
                continue

            rows.append(
                {
                    "company": company,
                    "sector": sector,
                    "frequency": frequency,
                    "period_start": period_start.date().isoformat(),
                    "period_end": period_df.index.max().date().isoformat(),
                    "impacto_dia_mean": float(
                        period_df["impacto_dia"].mean()
                    ),
                    "impacto_dia_sum": float(
                        period_df["impacto_dia"].sum()
                    ),
                    "iti_liquido_mean": float(
                        period_df["iti_liquido"].mean()
                    ),
                    "iti_liquido_min": float(
                        period_df["iti_liquido"].min()
                    ),
                    "iti_liquido_max": float(
                        period_df["iti_liquido"].max()
                    ),
                    "iti_liquido_std": float(
                        period_df["iti_liquido"].std()
                    ),
                    "iti_risco_mean": float(
                        period_df["iti_risco"].mean()
                    ),
                    "news_count": int(period_df["news_count"].sum()),
                }
            )

    return pd.DataFrame(rows)


def merge_uncertainty_across_models(
    *,
    configuration: ResolvedConfiguration,
    news_impact_files: Mapping[str, Sequence[Path]],
) -> list[UncertaintyMergeResult]:
    """Consolida divergência entre modelos para o mesmo dataset."""

    settings = configuration.temporal_index.get("uncertainty", {})
    if not isinstance(settings, Mapping) or not settings.get(
        "enabled",
        False,
    ):
        return []

    min_models = int(settings.get("min_models", 2))
    results: list[UncertaintyMergeResult] = []

    for dataset_key, paths in news_impact_files.items():
        valid_paths = [path for path in paths if path.is_file()]
        if len(valid_paths) < min_models:
            continue

        frames: list[pd.DataFrame] = []
        for path in valid_paths:
            frame = pd.read_csv(path)
            model_key = path.parent.parent.name
            subset = frame.loc[
                :,
                ["news_id", "date", "company", "sector", "d"],
            ].copy()
            subset["model_key"] = model_key
            frames.append(subset)

        merged = pd.concat(frames, ignore_index=True)
        disagreement = (
            merged.groupby(
                ["news_id", "date", "company", "sector"],
                dropna=False,
            )["d"]
            .agg(["var", "count", "std", "mean"])
            .reset_index()
            .rename(
                columns={
                    "var": "disagreement_var",
                    "count": "model_count",
                    "std": "disagreement_std",
                    "mean": "direction_mean",
                }
            )
        )
        disagreement["date"] = pd.to_datetime(
            disagreement["date"],
            errors="coerce",
        )
        disagreement["company"] = disagreement["company"].fillna(
            "UNKNOWN"
        )
        disagreement["sector"] = disagreement["sector"].fillna(
            "UNKNOWN"
        )

        uncertainty_daily = (
            disagreement.groupby(
                ["date", "company", "sector"],
                dropna=False,
            )
            .agg(
                disagreement_mean=("disagreement_var", "mean"),
                disagreement_max=("disagreement_var", "max"),
                news_count=("news_id", "nunique"),
                model_count=("model_count", "max"),
            )
            .reset_index()
        )
        uncertainty_daily["date"] = uncertainty_daily["date"].dt.date.astype(
            str
        )

        results.append(
            UncertaintyMergeResult(
                dataset_key=dataset_key,
                disagreement_daily=disagreement,
                iti_uncertainty_daily=uncertainty_daily,
            )
        )

    return results


def _extract_dimension_series(
    frame: pd.DataFrame,
    *,
    key: str,
    default: float,
) -> pd.Series:
    short = DIMENSION_SHORT_NAMES[key]
    values = pd.Series(default, index=frame.index, dtype=float)

    if "prediction_metadata" not in frame.columns:
        return values

    aliases = {
        key,
        short,
        key.replace("_", ""),
    }

    for index, raw_metadata in frame["prediction_metadata"].items():
        metadata = _parse_prediction_metadata(raw_metadata)
        if not metadata:
            continue

        for alias in aliases:
            if alias in metadata:
                try:
                    values.at[index] = float(metadata[alias])
                except (TypeError, ValueError):
                    pass
                break

    return values


def _parse_prediction_metadata(value: Any) -> dict[str, Any]:
    if value is None or (
        isinstance(value, float) and math.isnan(value)
    ):
        return {}

    if isinstance(value, Mapping):
        return dict(value)

    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}

        if isinstance(parsed, Mapping):
            return dict(parsed)

    return {}


def empty_iti_daily() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "date",
            "company",
            "sector",
            "impacto_dia",
            "risco_dia",
            "news_count",
            "iti_liquido",
            "iti_risco",
        ]
    )


def empty_level_daily(level: str) -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "date",
            "sector" if level == "sector" else "aggregation_level",
            "impacto_dia",
            "risco_dia",
            "iti_liquido",
            "iti_risco",
            "news_count",
            "company_count",
            "aggregation_level",
        ]
    )


def empty_resampled(frequency: str) -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "company",
            "sector",
            "frequency",
            "period_start",
            "period_end",
            "impacto_dia_mean",
            "impacto_dia_sum",
            "iti_liquido_mean",
            "iti_liquido_min",
            "iti_liquido_max",
            "iti_liquido_std",
            "iti_risco_mean",
            "news_count",
        ]
    )


__all__ = [
    "TemporalIndexArtifacts",
    "TemporalIndexBuilder",
    "TemporalIndexError",
    "UncertaintyMergeResult",
    "aggregate_level_series",
    "build_news_impact_frame",
    "compute_daily_company_impact",
    "compute_iti_daily_series",
    "merge_uncertainty_across_models",
    "resample_iti_series",
]
