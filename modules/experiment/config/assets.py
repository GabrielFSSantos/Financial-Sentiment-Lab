"""Orquestração de assets: modelos, datasets e mercado.

Use ``./scripts/setup_env.sh --fetch-assets`` antes da primeira inferência.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from modules.datasets.assets import (
    AssetFetchError as DatasetsAssetFetchError,
    AssetFetchReport as DatasetsAssetFetchReport,
    check_dataset_assets,
    fetch_enabled_datasets,
)
from modules.datasets.config.loader import (
    DatasetsConfiguration,
    load_datasets_configuration,
)
from modules.experiment.common import ASSET_FETCH_HINT
from modules.experiment.config.loader import (
    ConfigurationError,
    ResolvedConfiguration,
)
from modules.models.assets import (
    AssetFetchError as ModelsAssetFetchError,
    AssetFetchReport as ModelsAssetFetchReport,
    check_model_assets,
    fetch_enabled_models,
)
from modules.market.assets import (
    AssetFetchError as MarketAssetFetchError,
    AssetFetchReport as MarketAssetFetchReport,
    check_market_assets,
    fetch_market_assets,
)
from modules.market.config.loader import (
    MarketConfiguration,
    load_market_configuration,
)
from modules.models.config.loader import (
    ModelsConfiguration,
    load_models_configuration,
)


AssetStatus = Literal["skipped", "downloaded", "failed"]


class AssetFetchError(RuntimeError):
    """Erro durante o download de um asset declarado no YAML."""


@dataclass(frozen=True)
class AssetFetchReport:
    asset_key: str
    asset_type: str
    provider: str
    status: AssetStatus
    target: str
    message: str = ""
    bytes_downloaded: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AssetFetchSummary:
    reports: tuple[AssetFetchReport, ...] = field(default_factory=tuple)

    @property
    def downloaded_count(self) -> int:
        return sum(report.status == "downloaded" for report in self.reports)

    @property
    def failed_count(self) -> int:
        return sum(report.status == "failed" for report in self.reports)

    def to_dict(self) -> dict[str, Any]:
        return {
            "downloaded_count": self.downloaded_count,
            "failed_count": self.failed_count,
            "reports": [report.to_dict() for report in self.reports],
        }


def _convert_model_report(report: ModelsAssetFetchReport) -> AssetFetchReport:
    return AssetFetchReport(
        asset_key=report.asset_key,
        asset_type=report.asset_type,
        provider=report.provider,
        status=report.status,
        target=report.target,
        message=report.message,
        bytes_downloaded=report.bytes_downloaded,
    )


def _convert_dataset_report(
    report: DatasetsAssetFetchReport,
) -> AssetFetchReport:
    return AssetFetchReport(
        asset_key=report.asset_key,
        asset_type=report.asset_type,
        provider=report.provider,
        status=report.status,
        target=report.target,
        message=report.message,
        bytes_downloaded=report.bytes_downloaded,
    )


def _convert_market_report(
    report: MarketAssetFetchReport,
) -> AssetFetchReport:
    return AssetFetchReport(
        asset_key=report.asset_key,
        asset_type=report.asset_type,
        provider=report.provider,
        status=report.status,
        target=report.target,
        message=report.message,
        bytes_downloaded=report.bytes_downloaded,
    )


def _market_configuration(
    configuration: ResolvedConfiguration,
) -> MarketConfiguration:
    return load_market_configuration(
        project_root=configuration.paths.project_root,
        config_path="configs/market.yaml",
    )


def _filtered_models_configuration(
    configuration: ResolvedConfiguration,
) -> ModelsConfiguration:
    models_cfg = load_models_configuration(
        project_root=configuration.paths.project_root,
        config_path=configuration.paths.models_config,
    )
    enabled_keys = {model.key for model in configuration.models}
    return ModelsConfiguration(
        schema_version=models_cfg.schema_version,
        defaults=models_cfg.defaults,
        models=tuple(
            model
            for model in models_cfg.models
            if model.enabled and model.key in enabled_keys
        ),
        config_path=models_cfg.config_path,
    )


def _filtered_datasets_configuration(
    configuration: ResolvedConfiguration,
) -> DatasetsConfiguration:
    datasets_cfg = load_datasets_configuration(
        project_root=configuration.paths.project_root,
        config_path=configuration.paths.datasets_config,
    )
    enabled_keys = {dataset.key for dataset in configuration.datasets}
    return DatasetsConfiguration(
        schema_version=datasets_cfg.schema_version,
        defaults=datasets_cfg.defaults,
        datasets=tuple(
            dataset
            for dataset in datasets_cfg.datasets
            if dataset.enabled and dataset.key in enabled_keys
        ),
        config_path=datasets_cfg.config_path,
    )


def check_enabled_assets(
    configuration: ResolvedConfiguration,
) -> list[str]:
    """Lista assets enabled ausentes (modelos e datasets com source)."""

    missing = check_model_assets(
        _filtered_models_configuration(configuration)
    )
    missing.extend(
        check_dataset_assets(
            _filtered_datasets_configuration(configuration)
        )
    )
    missing.extend(check_market_assets(_market_configuration(configuration)))
    return missing


def fetch_assets_for_configuration(
    configuration: ResolvedConfiguration,
    *,
    scope: str = "enabled_only",
    logger: logging.Logger | None = None,
) -> AssetFetchSummary:
    """Baixa assets ausentes dos recursos enabled."""

    if scope != "enabled_only":
        raise ConfigurationError(
            f"scope={scope!r} não suportado; use enabled_only."
        )

    log = logger or logging.getLogger(__name__)
    reports: list[AssetFetchReport] = []

    try:
        model_summary = fetch_enabled_models(
            _filtered_models_configuration(configuration),
            logger=log,
        )
    except ModelsAssetFetchError as error:
        raise AssetFetchError(str(error)) from error

    reports.extend(
        _convert_model_report(report)
        for report in model_summary.reports
    )

    try:
        dataset_summary = fetch_enabled_datasets(
            _filtered_datasets_configuration(configuration),
            logger=log,
        )
    except DatasetsAssetFetchError as error:
        raise AssetFetchError(str(error)) from error

    reports.extend(
        _convert_dataset_report(report)
        for report in dataset_summary.reports
    )

    try:
        market_summary = fetch_market_assets(
            _market_configuration(configuration),
            logger=log,
        )
    except MarketAssetFetchError as error:
        raise AssetFetchError(str(error)) from error

    reports.extend(
        _convert_market_report(report)
        for report in market_summary.reports
    )

    failed = [report for report in reports if report.status == "failed"]
    if failed:
        report = failed[0]
        if report.asset_type == "model":
            asset_label = f"modelo {report.asset_key}"
        elif report.asset_type == "market":
            asset_label = f"mercado {report.asset_key}"
        else:
            asset_label = f"dataset {report.asset_key}"
        raise AssetFetchError(
            f"Falha ao baixar {asset_label}: {report.message}{ASSET_FETCH_HINT}"
        )

    return AssetFetchSummary(reports=tuple(reports))


__all__ = [
    "AssetFetchError",
    "AssetFetchReport",
    "AssetFetchSummary",
    "check_enabled_assets",
    "fetch_assets_for_configuration",
]
