"""Agregação temporal do sentimento por empresa, setor e mercado.

Este módulo trabalha sobre as previsões já padronizadas por
``pipeline.output_schema`` e produz o conteúdo de ``aggregates.csv``.

Níveis suportados:

- ``company_day``: uma linha por data e empresa;
- ``sector_day``: uma linha por data e setor;
- ``market_day``: uma linha por data para todo o mercado.

O módulo não salva arquivos. A persistência pertence ao
``pipeline.results.ResultsManager``.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from typing import Any, Literal, Mapping, Sequence, cast

import numpy as np
import pandas as pd

from pipeline.common import (
    CANONICAL_LABELS,
    column_series,
    deduplicate,
    numeric_series,
)
from pipeline.configuration import ResolvedConfiguration
from pipeline.output_schema import StandardizedPredictions


IDENTITY_COLUMNS: tuple[str, ...] = (
    "run_id",
    "environment",
    "combination_id",
    "combination_index",
    "model_key",
    "model_name",
    "model_display_name",
    "dataset_key",
    "dataset_name",
    "dataset_display_name",
)

SUPPORTED_LEVELS: tuple[str, ...] = (
    "company_day",
    "sector_day",
    "market_day",
)

SUPPORTED_STATISTICS: tuple[str, ...] = (
    "mean",
    "median",
    "sum",
    "count",
)

LEVEL_DIMENSIONS: dict[str, tuple[str, ...]] = {
    "company_day": ("date", "company"),
    "sector_day": ("date", "sector"),
    "market_day": ("date",),
}

STATISTIC_OUTPUT_COLUMNS: dict[str, str] = {
    "mean": "sentiment_mean",
    "median": "sentiment_median",
    "sum": "sentiment_sum",
    "count": "sentiment_count",
}

AGGREGATE_COLUMNS: tuple[str, ...] = (
    *IDENTITY_COLUMNS,
    "aggregation_level",
    "group_key",
    "date",
    "company",
    "sector",
    "ticker",
    "news_count",
    "sentiment_mean",
    "sentiment_median",
    "sentiment_sum",
    "sentiment_count",
    "mean_confidence",
    "positive_count",
    "negative_count",
    "neutral_count",
    "positive_percentage",
    "negative_percentage",
    "neutral_percentage",
)


class AggregationError(RuntimeError):
    """Erro-base durante a agregação."""


class AggregationConfigurationError(AggregationError, ValueError):
    """A configuração de agregação é inválida."""


class AggregationInputError(AggregationError, ValueError):
    """O DataFrame de previsões não pode ser agregado."""


@dataclass(frozen=True)
class AggregationLevelSummary:
    """Resumo da tentativa de geração de um nível."""

    level: str
    status: str
    reason: str | None
    source_rows: int
    eligible_rows: int
    dropped_missing_dimension_rows: int
    groups_before_minimum_filter: int
    groups_after_minimum_filter: int
    dropped_minimum_news_groups: int
    output_rows: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AggregationResult:
    """Resultado completo da agregação de uma combinação."""

    dataframe: pd.DataFrame
    enabled: bool
    status: str
    sentiment_column: str
    minimum_news_per_group: int
    requested_levels: tuple[str, ...]
    generated_levels: tuple[str, ...]
    skipped_levels: dict[str, str]
    level_summaries: tuple[AggregationLevelSummary, ...]
    warnings: tuple[str, ...] = field(default_factory=tuple)

    @property
    def row_count(self) -> int:
        return len(self.dataframe)

    def metadata(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "status": self.status,
            "sentiment_column": self.sentiment_column,
            "minimum_news_per_group": (
                self.minimum_news_per_group
            ),
            "requested_levels": list(self.requested_levels),
            "generated_levels": list(self.generated_levels),
            "skipped_levels": dict(self.skipped_levels),
            "row_count": self.row_count,
            "warnings": list(self.warnings),
            "level_summaries": [
                summary.to_dict()
                for summary in self.level_summaries
            ],
            "columns": list(self.dataframe.columns),
        }

    def save_arguments(self) -> dict[str, pd.DataFrame]:
        """Retorna o argumento aceito por ``ResultsManager``."""

        return {"aggregates": self.dataframe}


class SentimentAggregator:
    """Calcula agregações para uma combinação modelo × dataset."""

    def __init__(
        self,
        settings: Mapping[str, Any] | None = None,
    ) -> None:
        self.settings = dict(settings or {})

        self.enabled = _as_boolean(
            self.settings.get("enabled", True),
            "aggregation.enabled",
        )

        self.sentiment_column = _non_empty_string(
            self.settings.get(
                "sentiment_column",
                "continuous_sentiment",
            ),
            "aggregation.sentiment_column",
        )

        self.minimum_news_per_group = _positive_integer(
            self.settings.get(
                "minimum_news_per_group",
                1,
            ),
            "aggregation.minimum_news_per_group",
        )

        self.skip_level_when_columns_missing = _as_boolean(
            self.settings.get(
                "skip_level_when_columns_missing",
                True,
            ),
            (
                "aggregation."
                "skip_level_when_columns_missing"
            ),
        )

        self.levels = _normalize_levels(
            self.settings.get(
                "levels",
                SUPPORTED_LEVELS,
            )
        )

        self.statistics = _normalize_statistics(
            self.settings.get(
                "statistics",
                SUPPORTED_STATISTICS,
            )
        )

        self.include_class_counts = _as_boolean(
            self.settings.get(
                "include_class_counts",
                True,
            ),
            "aggregation.include_class_counts",
        )

        self.include_mean_confidence = _as_boolean(
            self.settings.get(
                "include_mean_confidence",
                True,
            ),
            "aggregation.include_mean_confidence",
        )

    def aggregate(
        self,
        predictions: StandardizedPredictions | pd.DataFrame,
    ) -> AggregationResult:
        """Gera todos os níveis configurados e os combina em uma tabela."""

        dataframe = _prediction_dataframe(predictions)

        if not self.enabled:
            return AggregationResult(
                dataframe=empty_aggregates(),
                enabled=False,
                status="disabled",
                sentiment_column=self.sentiment_column,
                minimum_news_per_group=(
                    self.minimum_news_per_group
                ),
                requested_levels=self.levels,
                generated_levels=tuple(),
                skipped_levels={
                    level: "aggregation_disabled"
                    for level in self.levels
                },
                level_summaries=tuple(
                    AggregationLevelSummary(
                        level=level,
                        status="skipped",
                        reason="aggregation_disabled",
                        source_rows=len(dataframe),
                        eligible_rows=0,
                        dropped_missing_dimension_rows=0,
                        groups_before_minimum_filter=0,
                        groups_after_minimum_filter=0,
                        dropped_minimum_news_groups=0,
                        output_rows=0,
                    )
                    for level in self.levels
                ),
            )

        self._validate_input(dataframe)
        identity = _extract_identity(dataframe)
        working = self._prepare_working_dataframe(
            dataframe
        )

        level_frames: list[pd.DataFrame] = []
        summaries: list[AggregationLevelSummary] = []
        generated_levels: list[str] = []
        skipped_levels: dict[str, str] = {}
        warnings: list[str] = []

        for level in self.levels:
            level_frame, summary = self._aggregate_level(
                working=working,
                identity=identity,
                level=level,
            )
            summaries.append(summary)

            if summary.status == "success":
                generated_levels.append(level)
                level_frames.append(level_frame)
            else:
                reason = (
                    summary.reason
                    or "level_not_generated"
                )
                skipped_levels[level] = reason
                warnings.append(
                    f"O nível {level!r} não foi gerado: "
                    f"{reason}."
                )

            if summary.dropped_missing_dimension_rows:
                warnings.append(
                    f"O nível {level!r} ignorou "
                    f"{summary.dropped_missing_dimension_rows} "
                    "linha(s) com dimensões ausentes ou inválidas."
                )

            if summary.dropped_minimum_news_groups:
                warnings.append(
                    f"O nível {level!r} removeu "
                    f"{summary.dropped_minimum_news_groups} "
                    "grupo(s) por não atingir "
                    "minimum_news_per_group."
                )

        if level_frames:
            aggregates = pd.concat(
                level_frames,
                ignore_index=True,
                sort=False,
            )
            aggregates = _ensure_aggregate_columns(
                aggregates
            )
            aggregates = self._sort_output(aggregates)
            status = (
                "success"
                if not skipped_levels
                else "partial"
            )
        else:
            aggregates = empty_aggregates()
            status = "unavailable"

        return AggregationResult(
            dataframe=aggregates,
            enabled=True,
            status=status,
            sentiment_column=self.sentiment_column,
            minimum_news_per_group=(
                self.minimum_news_per_group
            ),
            requested_levels=self.levels,
            generated_levels=tuple(generated_levels),
            skipped_levels=skipped_levels,
            level_summaries=tuple(summaries),
            warnings=tuple(deduplicate(warnings)),
        )

    def _validate_input(
        self,
        dataframe: pd.DataFrame,
    ) -> None:
        if not isinstance(dataframe, pd.DataFrame):
            raise AggregationInputError(
                "predictions precisa ser um pandas.DataFrame "
                "ou StandardizedPredictions."
            )

        if dataframe.empty:
            raise AggregationInputError(
                "Não é possível agregar um DataFrame vazio."
            )

        required = {
            *IDENTITY_COLUMNS,
            self.sentiment_column,
        }

        if self.include_class_counts:
            required.add("predicted_label")

        if self.include_mean_confidence:
            required.add("confidence")

        missing = sorted(
            required - set(dataframe.columns)
        )
        if missing:
            raise AggregationInputError(
                f"O DataFrame não possui colunas necessárias: "
                f"{missing}."
            )

        _extract_identity(dataframe)

    def _prepare_working_dataframe(
        self,
        dataframe: pd.DataFrame,
    ) -> pd.DataFrame:
        working = dataframe.copy()

        sentiment = numeric_series(
            column_series(working, self.sentiment_column),
            errors="coerce",
        )
        sentiment_array = sentiment.to_numpy(dtype=np.float64)
        invalid_sentiment_array = ~np.isfinite(sentiment_array)

        if bool(invalid_sentiment_array.any()):
            rows = working.index[
                invalid_sentiment_array
            ].tolist()[:20]
            raise AggregationInputError(
                f"A coluna {self.sentiment_column!r} possui "
                f"valores ausentes ou não finitos nas linhas "
                f"{rows}."
            )

        tolerance = 1e-6
        outside_interval = (
            (sentiment_array < -1.0 - tolerance)
            | (sentiment_array > 1.0 + tolerance)
        )
        if bool(outside_interval.any()):
            minimum = float(np.min(sentiment_array))
            maximum = float(np.max(sentiment_array))
            raise AggregationInputError(
                f"A coluna {self.sentiment_column!r} precisa "
                "estar no intervalo [-1, 1]. "
                f"Intervalo encontrado: [{minimum}, {maximum}]."
            )

        working[self.sentiment_column] = sentiment.astype("float64")

        if "date" in working.columns:
            parsed_dates = pd.to_datetime(
                column_series(working, "date"),
                errors="coerce",
            )
            parsed_date_series = cast(pd.Series, parsed_dates)
            working["date"] = (
                parsed_date_series.dt.strftime("%Y-%m-%d")
                .astype("string")
            )

        for column in ("company", "sector", "ticker"):
            if column in working.columns:
                working[column] = _clean_dimension(
                    column_series(working, column)
                )

        if self.include_class_counts:
            labels = (
                column_series(working, "predicted_label")
                .astype("string")
                .str.strip()
                .str.upper()
            )
            invalid_labels = (
                set(labels.dropna().unique())
                - set(CANONICAL_LABELS)
            )
            if invalid_labels:
                raise AggregationInputError(
                    "predicted_label possui classes inválidas: "
                    f"{sorted(invalid_labels)}."
                )

            missing_labels = cast(pd.Series, labels.isna())
            if bool(missing_labels.any()):
                rows = working.index[
                    missing_labels.to_numpy(dtype=bool)
                ].tolist()[:20]
                raise AggregationInputError(
                    "predicted_label possui valores ausentes "
                    f"nas linhas {rows}."
                )

            working["predicted_label"] = labels
            working["_positive_count"] = (
                labels.eq("POSITIVE").astype("int64")
            )
            working["_negative_count"] = (
                labels.eq("NEGATIVE").astype("int64")
            )
            working["_neutral_count"] = (
                labels.eq("NEUTRAL").astype("int64")
            )

        if self.include_mean_confidence:
            confidence = numeric_series(
                column_series(working, "confidence"),
                errors="coerce",
            )
            confidence_array = confidence.to_numpy(
                dtype=np.float64
            )
            invalid_confidence_array = (
                ~np.isfinite(confidence_array)
                | (confidence_array < 0.0)
                | (confidence_array > 1.0)
            )
            if bool(invalid_confidence_array.any()):
                rows = working.index[
                    invalid_confidence_array
                ].tolist()[:20]
                raise AggregationInputError(
                    "confidence possui valores inválidos "
                    f"nas linhas {rows}."
                )
            working["confidence"] = confidence.astype("float64")

        return working

    def _aggregate_level(
        self,
        *,
        working: pd.DataFrame,
        identity: Mapping[str, Any],
        level: str,
    ) -> tuple[pd.DataFrame, AggregationLevelSummary]:
        dimensions = LEVEL_DIMENSIONS[level]
        missing_columns = [
            column
            for column in dimensions
            if column not in working.columns
        ]

        if missing_columns:
            reason = (
                "missing_columns:"
                + ",".join(missing_columns)
            )

            if not self.skip_level_when_columns_missing:
                raise AggregationInputError(
                    f"O nível {level!r} exige as colunas "
                    f"{missing_columns}."
                )

            return (
                empty_aggregates(),
                AggregationLevelSummary(
                    level=level,
                    status="skipped",
                    reason=reason,
                    source_rows=len(working),
                    eligible_rows=0,
                    dropped_missing_dimension_rows=0,
                    groups_before_minimum_filter=0,
                    groups_after_minimum_filter=0,
                    dropped_minimum_news_groups=0,
                    output_rows=0,
                ),
            )

        valid_dimension_mask = pd.Series(
            True,
            index=working.index,
            dtype=bool,
        )

        for dimension in dimensions:
            valid_dimension_mask &= (
                working[dimension].notna()
            )

        eligible = working.loc[
            valid_dimension_mask
        ].copy()

        dropped_missing = (
            len(working) - len(eligible)
        )

        if eligible.empty:
            return (
                empty_aggregates(),
                AggregationLevelSummary(
                    level=level,
                    status="skipped",
                    reason="no_rows_with_required_dimensions",
                    source_rows=len(working),
                    eligible_rows=0,
                    dropped_missing_dimension_rows=(
                        dropped_missing
                    ),
                    groups_before_minimum_filter=0,
                    groups_after_minimum_filter=0,
                    dropped_minimum_news_groups=0,
                    output_rows=0,
                ),
            )

        named_aggregations: dict[
            str,
            tuple[str, str]
        ] = {
            "news_count": (
                self.sentiment_column,
                "size",
            ),
        }

        for statistic in self.statistics:
            named_aggregations[
                STATISTIC_OUTPUT_COLUMNS[statistic]
            ] = (
                self.sentiment_column,
                statistic,
            )

        if self.include_mean_confidence:
            named_aggregations["mean_confidence"] = (
                "confidence",
                "mean",
            )

        if self.include_class_counts:
            named_aggregations.update(
                {
                    "positive_count": (
                        "_positive_count",
                        "sum",
                    ),
                    "negative_count": (
                        "_negative_count",
                        "sum",
                    ),
                    "neutral_count": (
                        "_neutral_count",
                        "sum",
                    ),
                }
            )

        grouped = eligible.groupby(
            list(dimensions),
            sort=True,
            dropna=False,
            observed=True,
        )

        aggregated = grouped.agg(
            **named_aggregations
        ).reset_index()

        groups_before = len(aggregated)
        keep = (
            aggregated["news_count"]
            >= self.minimum_news_per_group
        )
        aggregated = aggregated.loc[keep].copy()
        groups_after = len(aggregated)
        dropped_groups = (
            groups_before - groups_after
        )

        if aggregated.empty:
            return (
                empty_aggregates(),
                AggregationLevelSummary(
                    level=level,
                    status="skipped",
                    reason=(
                        "no_groups_meet_minimum_news"
                    ),
                    source_rows=len(working),
                    eligible_rows=len(eligible),
                    dropped_missing_dimension_rows=(
                        dropped_missing
                    ),
                    groups_before_minimum_filter=(
                        groups_before
                    ),
                    groups_after_minimum_filter=0,
                    dropped_minimum_news_groups=(
                        dropped_groups
                    ),
                    output_rows=0,
                ),
            )

        aggregated = self._decorate_level(
            dataframe=aggregated,
            identity=identity,
            level=level,
        )
        aggregated = _ensure_aggregate_columns(
            aggregated
        )

        return (
            aggregated,
            AggregationLevelSummary(
                level=level,
                status="success",
                reason=None,
                source_rows=len(working),
                eligible_rows=len(eligible),
                dropped_missing_dimension_rows=(
                    dropped_missing
                ),
                groups_before_minimum_filter=(
                    groups_before
                ),
                groups_after_minimum_filter=(
                    groups_after
                ),
                dropped_minimum_news_groups=(
                    dropped_groups
                ),
                output_rows=len(aggregated),
            ),
        )

    def _decorate_level(
        self,
        *,
        dataframe: pd.DataFrame,
        identity: Mapping[str, Any],
        level: str,
    ) -> pd.DataFrame:
        output = dataframe.copy()

        for column in IDENTITY_COLUMNS:
            output[column] = identity[column]

        output["aggregation_level"] = level

        for dimension in (
            "date",
            "company",
            "sector",
            "ticker",
        ):
            if dimension not in output.columns:
                output[dimension] = pd.NA

        if self.include_class_counts:
            output["positive_count"] = (
                output["positive_count"]
                .astype("int64")
            )
            output["negative_count"] = (
                output["negative_count"]
                .astype("int64")
            )
            output["neutral_count"] = (
                output["neutral_count"]
                .astype("int64")
            )

            denominator = output[
                "news_count"
            ].astype(float)

            output["positive_percentage"] = (
                output["positive_count"]
                / denominator
                * 100.0
            )
            output["negative_percentage"] = (
                output["negative_count"]
                / denominator
                * 100.0
            )
            output["neutral_percentage"] = (
                output["neutral_count"]
                / denominator
                * 100.0
            )
        else:
            for column in (
                "positive_count",
                "negative_count",
                "neutral_count",
                "positive_percentage",
                "negative_percentage",
                "neutral_percentage",
            ):
                output[column] = pd.NA

        if not self.include_mean_confidence:
            output["mean_confidence"] = pd.NA

        for statistic, output_column in (
            STATISTIC_OUTPUT_COLUMNS.items()
        ):
            if statistic not in self.statistics:
                output[output_column] = pd.NA

        output["group_key"] = output.apply(
            lambda row: _build_group_key(
                level=level,
                date_value=row.get("date"),
                company_value=row.get("company"),
                sector_value=row.get("sector"),
            ),
            axis=1,
        )

        return output

    def _sort_output(
        self,
        dataframe: pd.DataFrame,
    ) -> pd.DataFrame:
        level_order = {
            level: index
            for index, level in enumerate(self.levels)
        }

        output = dataframe.copy()
        output["_level_order"] = (
            column_series(output, "aggregation_level")
            .map(
                lambda value: level_order.get(
                    str(value),
                    len(level_order),
                )
            )
            .astype("int64")
        )

        output.sort_values(
            by=[
                "_level_order",
                "date",
                "company",
                "sector",
                "group_key",
            ],
            kind="stable",
            na_position="last",
            inplace=True,
        )

        output.drop(
            columns=["_level_order"],
            inplace=True,
        )
        output.reset_index(drop=True, inplace=True)
        return output


def empty_aggregates() -> pd.DataFrame:
    """Retorna uma tabela vazia com o schema oficial."""

    return pd.DataFrame(
        columns=pd.Index(AGGREGATE_COLUMNS)
    )


def _prediction_dataframe(
    predictions: StandardizedPredictions | pd.DataFrame,
) -> pd.DataFrame:
    if isinstance(predictions, StandardizedPredictions):
        dataframe = predictions.dataframe
        if not isinstance(dataframe, pd.DataFrame):
            raise AggregationInputError(
                "StandardizedPredictions.dataframe precisa ser um "
                "pandas.DataFrame."
            )
        return dataframe.copy()

    if isinstance(predictions, pd.DataFrame):
        return predictions.copy()

    raise AggregationInputError(
        "predictions precisa ser StandardizedPredictions "
        "ou pandas.DataFrame."
    )


def _extract_identity(
    dataframe: pd.DataFrame,
) -> dict[str, Any]:
    identity: dict[str, Any] = {}

    for column in IDENTITY_COLUMNS:
        if column not in dataframe.columns:
            raise AggregationInputError(
                f"Coluna de identidade ausente: {column!r}."
            )

        values = (
            dataframe[column]
            .drop_duplicates()
            .tolist()
        )
        if len(values) != 1:
            raise AggregationInputError(
                f"A coluna {column!r} precisa conter um "
                f"único valor; encontrados: {values[:20]}."
            )

        identity[column] = values[0]

    return identity


def _normalize_levels(
    value: Any,
) -> tuple[str, ...]:
    values = _normalize_string_sequence(
        value,
        "aggregation.levels",
    )

    invalid = [
        level
        for level in values
        if level not in SUPPORTED_LEVELS
    ]
    if invalid:
        raise AggregationConfigurationError(
            f"Níveis de agregação não suportados: "
            f"{invalid}. Suportados: "
            f"{list(SUPPORTED_LEVELS)}."
        )

    return values


def _normalize_statistics(
    value: Any,
) -> tuple[str, ...]:
    values = _normalize_string_sequence(
        value,
        "aggregation.statistics",
    )

    invalid = [
        statistic
        for statistic in values
        if statistic not in SUPPORTED_STATISTICS
    ]
    if invalid:
        raise AggregationConfigurationError(
            f"Estatísticas não suportadas: {invalid}. "
            f"Suportadas: {list(SUPPORTED_STATISTICS)}."
        )

    return values


def _normalize_string_sequence(
    value: Any,
    field_name: str,
) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)):
        raise AggregationConfigurationError(
            f"{field_name} precisa ser uma lista."
        )

    try:
        normalized = tuple(
            str(item).strip().lower()
            for item in value
        )
    except TypeError as error:
        raise AggregationConfigurationError(
            f"{field_name} precisa ser iterável."
        ) from error

    if not normalized:
        raise AggregationConfigurationError(
            f"{field_name} não pode ficar vazio."
        )

    if any(not item for item in normalized):
        raise AggregationConfigurationError(
            f"{field_name} possui valor vazio."
        )

    if len(normalized) != len(set(normalized)):
        raise AggregationConfigurationError(
            f"{field_name} possui valores duplicados."
        )

    return normalized


def _as_boolean(
    value: Any,
    field_name: str,
) -> bool:
    if not isinstance(value, bool):
        raise AggregationConfigurationError(
            f"{field_name} precisa ser true ou false."
        )
    return value


def _positive_integer(
    value: Any,
    field_name: str,
) -> int:
    if isinstance(value, bool):
        raise AggregationConfigurationError(
            f"{field_name} precisa ser um inteiro positivo."
        )

    try:
        normalized = int(value)
    except (TypeError, ValueError) as error:
        raise AggregationConfigurationError(
            f"{field_name} precisa ser um inteiro positivo."
        ) from error

    if normalized < 1:
        raise AggregationConfigurationError(
            f"{field_name} precisa ser maior ou igual a 1."
        )

    return normalized


def _non_empty_string(
    value: Any,
    field_name: str,
) -> str:
    if not isinstance(value, str):
        raise AggregationConfigurationError(
            f"{field_name} precisa ser texto."
        )

    normalized = value.strip()
    if not normalized:
        raise AggregationConfigurationError(
            f"{field_name} não pode ficar vazio."
        )

    return normalized


def _clean_dimension(
    series: pd.Series,
) -> pd.Series:
    cleaned = (
        series.astype("string")
        .str.strip()
    )
    return cleaned.mask(cleaned.eq(""), pd.NA)


def _build_group_key(
    *,
    level: str,
    date_value: Any,
    company_value: Any,
    sector_value: Any,
) -> str:
    payload: dict[str, Any] = {
        "level": level,
        "date": _nullable_text(date_value),
    }

    if level == "company_day":
        payload["company"] = _nullable_text(
            company_value
        )
    elif level == "sector_day":
        payload["sector"] = _nullable_text(
            sector_value
        )

    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _nullable_text(value: Any) -> str | None:
    if value is None or value is pd.NA:
        return None

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    normalized = str(value).strip()
    return normalized or None


def _ensure_aggregate_columns(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    output = dataframe.copy()

    for column in AGGREGATE_COLUMNS:
        if column not in output.columns:
            output[column] = pd.NA

    output = output.loc[
        :,
        list(AGGREGATE_COLUMNS),
    ]

    integer_columns = (
        "combination_index",
        "news_count",
        "sentiment_count",
        "positive_count",
        "negative_count",
        "neutral_count",
    )
    for column in integer_columns:
        output[column] = numeric_series(
            column_series(output, column),
            errors="coerce",
        ).astype("Int64")

    float_columns = (
        "sentiment_mean",
        "sentiment_median",
        "sentiment_sum",
        "mean_confidence",
        "positive_percentage",
        "negative_percentage",
        "neutral_percentage",
    )
    for column in float_columns:
        output[column] = numeric_series(
            column_series(output, column),
            errors="coerce",
        ).astype("Float64")

    string_columns = (
        "run_id",
        "environment",
        "combination_id",
        "model_key",
        "model_name",
        "model_display_name",
        "dataset_key",
        "dataset_name",
        "dataset_display_name",
        "aggregation_level",
        "group_key",
        "date",
        "company",
        "sector",
        "ticker",
    )
    for column in string_columns:
        output[column] = (
            output[column].astype("string")
        )

    return output


__all__ = [
    "AGGREGATE_COLUMNS",
    "IDENTITY_COLUMNS",
    "LEVEL_DIMENSIONS",
    "STATISTIC_OUTPUT_COLUMNS",
    "SUPPORTED_LEVELS",
    "SUPPORTED_STATISTICS",
    "AggregationConfigurationError",
    "AggregationError",
    "AggregationInputError",
    "AggregationLevelSummary",
    "AggregationResult",
    "SentimentAggregator",
    "empty_aggregates",
]