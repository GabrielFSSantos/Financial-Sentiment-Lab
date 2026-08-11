"""Download declarativo de modelos e datasets via YAML.

Use ``./scripts/setup_env.sh --fetch-assets`` antes da primeira inferência.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

import pandas as pd

from pipeline.common import ASSET_FETCH_HINT
from pipeline.configuration import (
    ConfigurationError,
    DatasetConfiguration,
    ModelConfiguration,
    ResolvedConfiguration,
)

try:
    from huggingface_hub import hf_hub_download, snapshot_download
except ImportError as error:  # pragma: no cover
    hf_hub_download = None  # type: ignore[assignment,misc]
    snapshot_download = None  # type: ignore[assignment,misc]
    _HF_IMPORT_ERROR = error
else:
    _HF_IMPORT_ERROR = None


AssetStatus = Literal["skipped", "downloaded", "failed"]
FetchStrategy = Literal["full", "sample"]


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
    if hf_hub_download is None or snapshot_download is None:
        raise AssetFetchError(
            "huggingface_hub não está instalado. "
            "Execute: pip install huggingface_hub"
        ) from _HF_IMPORT_ERROR


def _fetch_strategy(dataset: DatasetConfiguration) -> FetchStrategy:
    max_rows = dataset.limits.get("max_rows")
    if max_rows is None:
        return "full"
    if isinstance(max_rows, int) and max_rows >= 1:
        return "sample"
    raise AssetFetchError(
        f"Dataset {dataset.key}: limits.max_rows inválido."
    )


def _sample_row_limit(dataset: DatasetConfiguration) -> int:
    max_rows = dataset.limits.get("max_rows")
    if not isinstance(max_rows, int) or max_rows < 1:
        raise AssetFetchError(
            f"Dataset {dataset.key}: fetch amostrado exige "
            f"limits.max_rows inteiro >= 1."
        )
    return max_rows


def _model_is_present(model: ModelConfiguration) -> bool:
    if not model.model_dir.is_dir():
        return False

    missing = [
        filename
        for filename in model.required_files
        if not (model.model_dir / filename).is_file()
    ]
    return not missing


def _dataset_is_present(dataset: DatasetConfiguration) -> bool:
    if dataset.format == "huggingface":
        return True

    return (
        dataset.path is not None
        and dataset.path.is_file()
        and dataset.path.stat().st_size > 0
    )


def _resolve_materialize_target(dataset: DatasetConfiguration) -> Path:
    source = dataset.source
    if source and source.get("local_path"):
        return Path(source["local_path"])
    if dataset.path is None:
        raise AssetFetchError(
            f"Dataset {dataset.key} não possui local_path/path para "
            "materialização."
        )
    return dataset.path


def _write_materialized_rows(
    *,
    rows: list[dict[str, Any]],
    target: Path,
    materialize_format: str,
) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)

    if materialize_format == "jsonl":
        with target.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(
                    json.dumps(row, ensure_ascii=False) + "\n"
                )
        return

    if materialize_format == "csv":
        pd.DataFrame(rows).to_csv(target, index=False)
        return

    raise AssetFetchError(
        f"Formato de materialização não suportado: {materialize_format!r}."
    )


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


def _fetch_huggingface_hub_file(
    *,
    asset_key: str,
    asset_type: str,
    source: dict[str, Any],
    logger: logging.Logger,
) -> AssetFetchReport:
    _ensure_hf_hub()
    target = Path(source["local_path"])
    repo_id = source["repo_id"]
    filename = source["filename"]
    revision = source.get("revision", "main")

    if target.is_file() and target.stat().st_size > 0:
        return AssetFetchReport(
            asset_key=asset_key,
            asset_type=asset_type,
            provider="huggingface_hub_file",
            status="skipped",
            target=str(target),
            message="Arquivo já presente.",
        )

    target.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Baixando %s (%s) de %s", asset_key, filename, repo_id)

    try:
        downloaded = hf_hub_download(
            repo_id=repo_id,
            filename=filename,
            revision=revision,
            local_dir=str(target.parent),
            local_dir_use_symlinks=False,
        )
        downloaded_path = Path(downloaded)
        if not downloaded_path.is_file():
            nested = target.parent / filename
            if nested.is_file():
                downloaded_path = nested
        if downloaded_path.resolve() != target.resolve():
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                target.unlink()
            downloaded_path.replace(target)
            nested_parent = target.parent / Path(filename).parent
            if nested_parent.exists() and nested_parent != target.parent:
                try:
                    nested_parent.rmdir()
                except OSError:
                    pass
    except Exception as error:
        return AssetFetchReport(
            asset_key=asset_key,
            asset_type=asset_type,
            provider="huggingface_hub_file",
            status="failed",
            target=str(target),
            message=str(error),
        )

    size = target.stat().st_size if target.is_file() else None
    return AssetFetchReport(
        asset_key=asset_key,
        asset_type=asset_type,
        provider="huggingface_hub_file",
        status="downloaded",
        target=str(target),
        message="Arquivo baixado com sucesso.",
        bytes_downloaded=size,
    )


def _fetch_huggingface_dataset_sample(
    dataset: DatasetConfiguration,
    *,
    logger: logging.Logger,
) -> AssetFetchReport:
    source = dataset.source
    if not source:
        raise AssetFetchError(
            f"Dataset {dataset.key} não possui source configurado."
        )

    try:
        from datasets import load_dataset
    except ImportError as error:
        raise AssetFetchError(
            "Biblioteca datasets não instalada. "
            "Execute: pip install datasets"
        ) from error

    target = _resolve_materialize_target(dataset)
    if target.is_file() and target.stat().st_size > 0:
        return AssetFetchReport(
            asset_key=dataset.key,
            asset_type="dataset",
            provider=source["provider"],
            status="skipped",
            target=str(target),
            message="Subset local já materializado.",
        )

    max_rows = _sample_row_limit(dataset)
    materialize_format = str(
        source.get("materialize_format") or dataset.format
    ).lower()
    repo_id = source["repo_id"]
    revision = source.get("revision", "main")
    split = source.get("split", "train")

    load_kwargs: dict[str, Any] = {
        "path": repo_id,
        "split": split,
        "streaming": True,
        "revision": revision,
    }
    data_files = source.get("data_files") or source.get("filename")
    if data_files:
        load_kwargs["data_files"] = data_files

    logger.info(
        "Materializando amostra de %s (%d linhas) em %s",
        dataset.key,
        max_rows,
        target,
    )

    try:
        stream = load_dataset(**load_kwargs)
        rows: list[dict[str, Any]] = []
        for index, row in enumerate(stream):
            if index >= max_rows:
                break
            rows.append(dict(row))

        if not rows:
            raise AssetFetchError(
                f"Dataset {dataset.key}: streaming não retornou linhas."
            )

        _write_materialized_rows(
            rows=rows,
            target=target,
            materialize_format=materialize_format,
        )
    except Exception as error:
        return AssetFetchReport(
            asset_key=dataset.key,
            asset_type="dataset",
            provider=source["provider"],
            status="failed",
            target=str(target),
            message=str(error),
        )

    size = target.stat().st_size if target.is_file() else None
    return AssetFetchReport(
        asset_key=dataset.key,
        asset_type="dataset",
        provider=source["provider"],
        status="downloaded",
        target=str(target),
        message=(
            f"Subset materializado com {len(rows)} linha(s) "
            f"(limits.max_rows={max_rows})."
        ),
        bytes_downloaded=size,
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


def fetch_dataset_asset(
    dataset: DatasetConfiguration,
    *,
    logger: logging.Logger | None = None,
) -> AssetFetchReport | None:
    source = dataset.source
    if not source:
        return None

    if dataset.format == "huggingface":
        return AssetFetchReport(
            asset_key=dataset.key,
            asset_type="dataset",
            provider=source["provider"],
            status="skipped",
            target=source.get("repo_id", ""),
            message="format=huggingface lê direto do Hub.",
        )

    log = logger or logging.getLogger(__name__)
    provider = source["provider"]

    if _dataset_is_present(dataset):
        return AssetFetchReport(
            asset_key=dataset.key,
            asset_type="dataset",
            provider=provider,
            status="skipped",
            target=str(dataset.path),
            message="Dataset já presente.",
        )

    strategy = _fetch_strategy(dataset)
    if strategy == "sample":
        return _fetch_huggingface_dataset_sample(dataset, logger=log)

    if provider == "huggingface_hub_file":
        return _fetch_huggingface_hub_file(
            asset_key=dataset.key,
            asset_type="dataset",
            source=source,
            logger=log,
        )

    if provider == "huggingface_dataset":
        return _fetch_huggingface_dataset_sample(dataset, logger=log)

    raise AssetFetchError(
        f"Provider {provider!r} não suportado para datasets em arquivo."
    )


def check_enabled_assets(
    configuration: ResolvedConfiguration,
) -> list[str]:
    """Lista assets enabled ausentes (modelos e datasets com source)."""

    missing: list[str] = []

    for model in configuration.models:
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

    for dataset in configuration.datasets:
        if not dataset.source or dataset.format == "huggingface":
            continue
        if (
            dataset.path is None
            or not dataset.path.is_file()
            or dataset.path.stat().st_size == 0
        ):
            missing.append(
                f"dataset {dataset.key}: {dataset.path}"
            )

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

    for model in configuration.models:
        report = fetch_model_asset(model, logger=log)
        if report is not None:
            reports.append(report)
            if report.status == "failed":
                raise AssetFetchError(
                    f"Falha ao baixar modelo {model.key}: {report.message}"
                    f"{ASSET_FETCH_HINT}"
                )

    for dataset in configuration.datasets:
        report = fetch_dataset_asset(dataset, logger=log)
        if report is not None:
            reports.append(report)
            if report.status == "failed":
                raise AssetFetchError(
                    f"Falha ao baixar dataset {dataset.key}: "
                    f"{report.message}{ASSET_FETCH_HINT}"
                )

    return AssetFetchSummary(reports=tuple(reports))


__all__ = [
    "AssetFetchError",
    "AssetFetchReport",
    "AssetFetchSummary",
    "check_enabled_assets",
    "fetch_assets_for_configuration",
    "fetch_dataset_asset",
    "fetch_model_asset",
]
