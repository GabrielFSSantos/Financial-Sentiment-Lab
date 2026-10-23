"""Loader estrito para ``analysis_plan.yaml`` (ITI-v2)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

ALLOWED_KEYS = frozenset(
    {
        "schema_version",
        "primary_metric",
        "primary_horizon_weeks",
        "horizons_weeks",
        "bootstrap_replicates",
        "block_length_weeks",
        "block_sensitivity_weeks",
        "seed",
        "alpha",
        "secondary_correction",
        "week_anchor",
        "returns_before_join",
        "constant_series_policy",
        "nan_as_zero_financial",
    }
)


class AnalysisPlanError(ValueError):
    """YAML de análise inválido ou com campos ignorados."""


@dataclass(frozen=True)
class AnalysisPlan:
    schema_version: str
    primary_metric: str
    primary_horizon_weeks: int
    horizons_weeks: tuple[int, ...]
    bootstrap_replicates: int
    block_length_weeks: int
    block_sensitivity_weeks: tuple[int, ...]
    seed: int
    alpha: float
    secondary_correction: str
    week_anchor: str
    returns_before_join: bool
    constant_series_policy: str
    nan_as_zero_financial: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "primary_metric": self.primary_metric,
            "primary_horizon_weeks": self.primary_horizon_weeks,
            "horizons_weeks": list(self.horizons_weeks),
            "bootstrap_replicates": self.bootstrap_replicates,
            "block_length_weeks": self.block_length_weeks,
            "block_sensitivity_weeks": list(self.block_sensitivity_weeks),
            "seed": self.seed,
            "alpha": self.alpha,
            "secondary_correction": self.secondary_correction,
            "week_anchor": self.week_anchor,
            "returns_before_join": self.returns_before_join,
            "constant_series_policy": self.constant_series_policy,
            "nan_as_zero_financial": self.nan_as_zero_financial,
        }


def load_analysis_plan(path: Path) -> AnalysisPlan:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise AnalysisPlanError("analysis_plan precisa ser um objeto YAML.")

    unknown = set(raw) - ALLOWED_KEYS
    if unknown:
        raise AnalysisPlanError(
            f"Campos desconhecidos em analysis_plan (seriam ignorados): {sorted(unknown)}"
        )

    missing = ALLOWED_KEYS - set(raw)
    if missing:
        raise AnalysisPlanError(f"Campos obrigatórios ausentes: {sorted(missing)}")

    horizons = tuple(int(x) for x in raw["horizons_weeks"])
    block_sens = tuple(int(x) for x in raw["block_sensitivity_weeks"])

    return AnalysisPlan(
        schema_version=str(raw["schema_version"]),
        primary_metric=str(raw["primary_metric"]),
        primary_horizon_weeks=int(raw["primary_horizon_weeks"]),
        horizons_weeks=horizons,
        bootstrap_replicates=int(raw["bootstrap_replicates"]),
        block_length_weeks=int(raw["block_length_weeks"]),
        block_sensitivity_weeks=block_sens,
        seed=int(raw["seed"]),
        alpha=float(raw["alpha"]),
        secondary_correction=str(raw["secondary_correction"]),
        week_anchor=str(raw["week_anchor"]),
        returns_before_join=bool(raw["returns_before_join"]),
        constant_series_policy=str(raw["constant_series_policy"]),
        nan_as_zero_financial=str(raw["nan_as_zero_financial"]),
    )
