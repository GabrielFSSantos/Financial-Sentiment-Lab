"""Orquestração da validação incremental ITI vs baselines vs mercado."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from modules.market.config.loader import load_market_configuration
from modules.market.loader import MarketLoaderError, load_market_prices
from modules.research.config.loader import ResearchConfiguration
from modules.research.io.align import AlignmentError, align_combination
from modules.research.io.experiment import (
    ExperimentIOError,
    list_index_combinations,
    load_uncertainty_daily,
    read_run_summary,
    resolve_run_directory,
)
from modules.research.io.reports import (
    combination_output_dir,
    write_combination_reports,
    write_research_summary,
)
from modules.research.validation.incremental import run_incremental_validation
from modules.research.validation.market import (
    run_market_validation,
    run_uncertainty_validation,
)


class ResearchRunnerError(RuntimeError):
    """Erro durante a execução da validação."""


@dataclass
class PredictorWinStats:
    wins: int = 0
    significant_wins: int = 0
    comparisons: int = 0


@dataclass
class CombinationResult:
    model_key: str
    dataset_key: str
    overlap_days: int
    dropped_companies: tuple[str, ...]
    output_dir: str
    predictor_stats: dict[str, PredictorWinStats] = field(default_factory=dict)
    predictor_stats_error: dict[str, PredictorWinStats] = field(default_factory=dict)


@dataclass
class ResearchRunSummary:
    run_id: str
    combinations: tuple[CombinationResult, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    sample_warnings: tuple[str, ...] = field(default_factory=tuple)
    conclusion_metrics: tuple[str, ...] = ("pearson", "spearman")

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "combination_count": len(self.combinations),
            "combinations": [
                {
                    "model_key": item.model_key,
                    "dataset_key": item.dataset_key,
                    "overlap_days": item.overlap_days,
                    "dropped_companies": list(item.dropped_companies),
                    "output_dir": item.output_dir,
                    "predictor_stats": {
                        predictor: {
                            "wins": stats.wins,
                            "significant_wins": stats.significant_wins,
                            "comparisons": stats.comparisons,
                        }
                        for predictor, stats in item.predictor_stats.items()
                    },
                    "predictor_stats_error": {
                        predictor: {
                            "wins": stats.wins,
                            "significant_wins": stats.significant_wins,
                            "comparisons": stats.comparisons,
                        }
                        for predictor, stats in item.predictor_stats_error.items()
                    },
                }
                for item in self.combinations
            ],
            "warnings": list(self.warnings),
            "sample_warnings": list(self.sample_warnings),
            "conclusion_metrics": list(self.conclusion_metrics),
            "conclusion": self._conclusion(),
        }

    def _conclusion(self) -> str:
        totals: dict[str, PredictorWinStats] = {}
        for combination in self.combinations:
            for predictor, stats in combination.predictor_stats.items():
                aggregate = totals.setdefault(predictor, PredictorWinStats())
                aggregate.wins += stats.wins
                aggregate.significant_wins += stats.significant_wins
                aggregate.comparisons += stats.comparisons

        if not totals:
            return "Nenhuma comparação ITI vs baseline disponível."

        metric_label = ", ".join(self.conclusion_metrics)
        parts = []
        for predictor, stats in sorted(totals.items()):
            if stats.comparisons == 0:
                continue
            ratio = stats.wins / stats.comparisons
            sig_ratio = stats.significant_wins / stats.comparisons
            parts.append(
                f"{predictor} ({metric_label}): {stats.wins}/"
                f"{stats.comparisons} vitórias ({ratio:.1%}), "
                f"{stats.significant_wins} significativas ({sig_ratio:.1%})"
            )

        return "; ".join(parts) if parts else "Nenhuma comparação ITI vs baseline disponível."


def _count_predictor_wins(
    incremental: pd.DataFrame,
    *,
    metrics: tuple[str, ...] | None = None,
) -> dict[str, PredictorWinStats]:
    deltas = incremental.attrs.get("deltas")
    if deltas is None or deltas.empty:
        return {}

    working = deltas
    if metrics is not None:
        working = working[working["metric"].isin(metrics)]
        if working.empty:
            return {}

    stats: dict[str, PredictorWinStats] = {}
    for predictor in working["iti_predictor"].unique():
        subset = working[working["iti_predictor"] == predictor]
        wins = int((subset["delta"] > 0).sum())
        significant = int(subset["significant"].sum()) if "significant" in subset else 0
        stats[str(predictor)] = PredictorWinStats(
            wins=wins,
            significant_wins=significant,
            comparisons=int(len(subset)),
        )
    return stats


def run_research(configuration: ResearchConfiguration) -> ResearchRunSummary:
    """Executa validação para todas as combinações do run."""

    run_dir = resolve_run_directory(configuration)
    run_id = run_dir.name
    combinations = list_index_combinations(
        configuration,
        run_dir=run_dir,
    )

    market_config = load_market_configuration(
        config_path=configuration.market_config_path,
    )
    market_prices = load_market_prices(market_config)

    warnings: list[str] = []
    sample_warnings: list[str] = []
    results: list[CombinationResult] = []

    for combination in combinations:
        try:
            alignment = align_combination(
                combination,
                configuration,
                market_prices=market_prices,
            )
        except AlignmentError as error:
            raise ResearchRunnerError(str(error)) from error

        if alignment.dropped_companies:
            warnings.append(
                "Empresas sem ticker mapeado em "
                f"{combination.model_key}/{combination.dataset_key}: "
                f"{', '.join(alignment.dropped_companies)}"
            )

        incremental = run_incremental_validation(
            alignment.panel,
            configuration,
        )
        combo_sample_warnings = incremental.attrs.get("sample_warnings")
        if combo_sample_warnings:
            sample_warnings.extend(combo_sample_warnings)
        market_metrics = run_market_validation(
            alignment.panel,
            configuration,
        )

        uncertainty_metrics = None
        if combination.uncertainty_daily is not None:
            uncertainty = load_uncertainty_daily(
                combination.uncertainty_daily
            )
            uncertainty_metrics = run_uncertainty_validation(
                uncertainty,
                alignment.panel,
                configuration,
            )

        output_dir = combination_output_dir(
            research_output_root=configuration.research_output_root,
            run_id=run_id,
            model_key=combination.model_key,
            dataset_key=combination.dataset_key,
        )
        write_combination_reports(
            output_dir=output_dir,
            aligned_panel=alignment.panel,
            incremental=incremental,
            market_metrics=market_metrics,
        )

        deltas = incremental.attrs.get("deltas")
        if deltas is not None and not deltas.empty:
            deltas.to_csv(output_dir / "incremental_deltas.csv", index=False)

        if uncertainty_metrics is not None:
            uncertainty_metrics.to_csv(
                output_dir / "uncertainty_metrics.csv",
                index=False,
            )

        results.append(
            CombinationResult(
                model_key=combination.model_key,
                dataset_key=combination.dataset_key,
                overlap_days=alignment.overlap_days,
                dropped_companies=alignment.dropped_companies,
                output_dir=str(output_dir),
                predictor_stats=_count_predictor_wins(
                    incremental,
                    metrics=configuration.conclusion_metrics,
                ),
                predictor_stats_error=_count_predictor_wins(
                    incremental,
                    metrics=tuple(
                        metric
                        for metric in configuration.metrics
                        if metric not in configuration.conclusion_metrics
                    ),
                ),
            )
        )

    summary = ResearchRunSummary(
        run_id=run_id,
        combinations=tuple(results),
        warnings=tuple(warnings),
        sample_warnings=tuple(sorted(set(sample_warnings))),
        conclusion_metrics=configuration.conclusion_metrics,
    )
    summary_path = (
        configuration.research_output_root
        / run_id
        / "research"
        / "research_summary.json"
    )
    payload = summary.to_dict()
    payload["experiment_summary"] = read_run_summary(run_dir)
    payload["return_mode"] = configuration.return_mode
    payload["return_column"] = configuration.return_column
    payload["iti_predictors"] = list(configuration.iti_predictors)
    payload["sample_warnings"] = list(summary.sample_warnings)
    write_research_summary(summary_path=summary_path, payload=payload)
    return summary


def check_research_inputs(
    configuration: ResearchConfiguration,
) -> tuple[list[str], list[str]]:
    """Verifica pré-requisitos para validação.

    Returns:
        Tupla ``(errors, warnings)``. Erros bloqueiam validate; avisos não.
    """

    errors: list[str] = []
    warnings: list[str] = []

    try:
        resolve_run_directory(configuration)
    except ExperimentIOError as error:
        errors.append(str(error))

    try:
        list_index_combinations(configuration)
    except ExperimentIOError as error:
        errors.append(str(error))

    market_config = load_market_configuration(
        config_path=configuration.market_config_path,
    )
    if not market_config.local_path.is_file():
        errors.append(
            f"CSV de mercado ausente: {market_config.local_path}. "
            "Execute: python -m modules.market fetch"
        )
        return errors, warnings

    try:
        market_prices = load_market_prices(market_config)
    except MarketLoaderError as error:
        errors.append(f"CSV de mercado inválido: {error}")
        return errors, warnings

    if market_prices.empty:
        errors.append("CSV de mercado vazio após sanitização.")
        return errors, warnings

    tickers_in_csv = sorted(market_prices["ticker"].dropna().unique())
    date_min = market_prices["date"].min()
    date_max = market_prices["date"].max()
    warnings.append(
        "Mercado: "
        f"{len(market_prices)} linha(s), "
        f"{len(tickers_in_csv)} ticker(s) "
        f"({', '.join(tickers_in_csv)}), "
        f"período {date_min} → {date_max}."
    )

    mapped_tickers = sorted(set(configuration.company_to_ticker.values()))
    missing_mapped = [
        ticker for ticker in mapped_tickers if ticker not in tickers_in_csv
    ]
    if missing_mapped:
        warnings.append(
            "Tickers mapeados ausentes no CSV de mercado: "
            f"{', '.join(missing_mapped)}."
        )

    if market_config.source is not None:
        source_tickers = list(market_config.source.tickers)
        missing_source = [
            ticker for ticker in source_tickers if ticker not in tickers_in_csv
        ]
        if missing_source:
            errors.append(
                "Tickers declarados em market.yaml ausentes no CSV: "
                f"{', '.join(missing_source)}."
            )

    return errors, warnings


__all__ = [
    "CombinationResult",
    "PredictorWinStats",
    "ResearchRunSummary",
    "ResearchRunnerError",
    "check_research_inputs",
    "run_research",
]
