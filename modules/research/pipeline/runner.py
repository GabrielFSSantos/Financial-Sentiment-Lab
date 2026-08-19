"""Orquestração da validação incremental ITI vs baselines vs mercado."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from modules.market.config.loader import load_market_configuration
from modules.market.loader import load_market_prices
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
class CombinationResult:
    model_key: str
    dataset_key: str
    overlap_days: int
    dropped_companies: tuple[str, ...]
    output_dir: str
    iti_wins: int = 0
    baseline_comparisons: int = 0


@dataclass
class ResearchRunSummary:
    run_id: str
    combinations: tuple[CombinationResult, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)

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
                    "iti_wins": item.iti_wins,
                    "baseline_comparisons": item.baseline_comparisons,
                }
                for item in self.combinations
            ],
            "warnings": list(self.warnings),
            "conclusion": self._conclusion(),
        }

    def _conclusion(self) -> str:
        total_wins = sum(item.iti_wins for item in self.combinations)
        total_comparisons = sum(
            item.baseline_comparisons for item in self.combinations
        )
        if total_comparisons == 0:
            return "Nenhuma comparação ITI vs baseline disponível."
        ratio = total_wins / total_comparisons
        return (
            f"ITI venceu {total_wins}/{total_comparisons} comparações "
            f"({ratio:.1%}) contra baselines nos horizontes configurados."
        )


def _count_iti_wins(incremental: pd.DataFrame) -> tuple[int, int]:
    deltas = incremental.attrs.get("deltas")
    if deltas is None or deltas.empty:
        return 0, 0
    wins = int((deltas["delta"] > 0).sum())
    return wins, int(len(deltas))


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

        if uncertainty_metrics is not None:
            uncertainty_metrics.to_csv(
                output_dir / "uncertainty_metrics.csv",
                index=False,
            )

        iti_wins, baseline_comparisons = _count_iti_wins(incremental)
        results.append(
            CombinationResult(
                model_key=combination.model_key,
                dataset_key=combination.dataset_key,
                overlap_days=alignment.overlap_days,
                dropped_companies=alignment.dropped_companies,
                output_dir=str(output_dir),
                iti_wins=iti_wins,
                baseline_comparisons=baseline_comparisons,
            )
        )

    summary = ResearchRunSummary(
        run_id=run_id,
        combinations=tuple(results),
        warnings=tuple(warnings),
    )
    summary_path = (
        configuration.research_output_root
        / run_id
        / "research"
        / "research_summary.json"
    )
    payload = summary.to_dict()
    payload["experiment_summary"] = read_run_summary(run_dir)
    write_research_summary(summary_path=summary_path, payload=payload)
    return summary


def check_research_inputs(configuration: ResearchConfiguration) -> list[str]:
    """Verifica pré-requisitos para validação."""

    issues: list[str] = []

    try:
        resolve_run_directory(configuration)
    except ExperimentIOError as error:
        issues.append(str(error))

    try:
        list_index_combinations(configuration)
    except ExperimentIOError as error:
        issues.append(str(error))

    market_config = load_market_configuration(
        config_path=configuration.market_config_path,
    )
    if not market_config.local_path.is_file():
        issues.append(
            f"CSV de mercado ausente: {market_config.local_path}. "
            "Execute: python -m modules.market fetch"
        )

    return issues


__all__ = [
    "CombinationResult",
    "ResearchRunSummary",
    "ResearchRunnerError",
    "check_research_inputs",
    "run_research",
]
