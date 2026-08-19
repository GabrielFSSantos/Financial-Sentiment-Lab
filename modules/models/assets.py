"""Download e validação de pesos locais declarados em ``configs/models.yaml``."""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

from modules.models.common import ASSET_FETCH_HINT
from modules.models.config.loader import (
    ModelConfiguration,
    ModelsConfiguration,
)

try:
    from huggingface_hub import snapshot_download
except ImportError as error:  # pragma: no cover
    snapshot_download = None  # type: ignore[assignment,misc]
    _HF_IMPORT_ERROR = error
else:
    _HF_IMPORT_ERROR = None


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


def _ensure_hf_hub() -> None:
    if snapshot_download is None:
        raise AssetFetchError(
            "huggingface_hub não está instalado. "
            "Execute: pip install huggingface_hub"
        ) from _HF_IMPORT_ERROR


def _model_is_present(model: ModelConfiguration) -> bool:
    if not model.model_dir.is_dir():
        return False

    missing = [
        filename
        for filename in model.required_files
        if not (model.model_dir / filename).is_file()
    ]
    return not missing


def _fetch_huggingface_hub(
    *,
    asset_key: str,
    asset_type: str,
    source: dict[str, Any],
    logger: logging.Logger,
) -> AssetFetchReport:
    _ensure_hf_hub()
    target = Path(source["local_dir"])
    repo_id = source["repo_id"]
    revision = source.get("revision", "main")

    target.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Baixando %s de %s para %s", asset_key, repo_id, target)

    try:
        snapshot_download(
            repo_id=repo_id,
            revision=revision,
            local_dir=str(target),
        )
    except Exception as error:
        return AssetFetchReport(
            asset_key=asset_key,
            asset_type=asset_type,
            provider="huggingface_hub",
            status="failed",
            target=str(target),
            message=str(error),
        )

    return AssetFetchReport(
        asset_key=asset_key,
        asset_type=asset_type,
        provider="huggingface_hub",
        status="downloaded",
        target=str(target),
        message="Snapshot baixado com sucesso.",
    )


def fetch_model_asset(
    model: ModelConfiguration,
    *,
    logger: logging.Logger | None = None,
) -> AssetFetchReport | None:
    source = model.source
    if not source:
        return None

    log = logger or logging.getLogger(__name__)
    provider = source["provider"]

    if _model_is_present(model):
        return AssetFetchReport(
            asset_key=model.key,
            asset_type="model",
            provider=provider,
            status="skipped",
            target=str(model.model_dir),
            message="Modelo já presente.",
        )

    if provider == "huggingface_hub":
        return _fetch_huggingface_hub(
            asset_key=model.key,
            asset_type="model",
            source=source,
            logger=log,
        )

    raise AssetFetchError(
        f"Provider {provider!r} não suportado para modelos."
    )


def check_model_assets(
    configuration: ModelsConfiguration,
) -> list[str]:
    """Lista modelos enabled com source ausentes ou incompletos."""

    missing: list[str] = []

    for model in configuration.enabled_models:
        if not model.source:
            continue
        if not model.model_dir.is_dir():
            missing.append(
                f"modelo {model.key}: diretório {model.model_dir}"
            )
            continue
        for filename in model.required_files:
            if not (model.model_dir / filename).is_file():
                missing.append(
                    f"modelo {model.key}: falta {filename}"
                )

    return missing


def fetch_enabled_models(
    configuration: ModelsConfiguration,
    *,
    model_keys: list[str] | None = None,
    logger: logging.Logger | None = None,
) -> AssetFetchSummary:
    """Baixa modelos enabled ausentes."""

    log = logger or logging.getLogger(__name__)
    reports: list[AssetFetchReport] = []
    selected_keys = set(model_keys) if model_keys else None

    for model in configuration.enabled_models:
        if selected_keys is not None and model.key not in selected_keys:
            continue

        report = fetch_model_asset(model, logger=log)
        if report is not None:
            reports.append(report)
            if report.status == "failed":
                raise AssetFetchError(
                    f"Falha ao baixar modelo {model.key}: {report.message}"
                    f"{ASSET_FETCH_HINT}"
                )

    return AssetFetchSummary(reports=tuple(reports))


__all__ = [
    "AssetFetchError",
    "AssetFetchReport",
    "AssetFetchSummary",
    "check_model_assets",
    "fetch_enabled_models",
    "fetch_model_asset",
]
