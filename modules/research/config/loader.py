"""Carregamento e validação de ``configs/research.yaml``."""

from __future__ import annotations

import copy
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Mapping

import yaml

from modules.research import PROJECT_ROOT
from modules.research.common import BASELINE_COLUMNS, to_serializable


SUPPORTED_SCHEMA_VERSION = "2.0"
SUPPORTED_METRICS = {"pearson", "spearman", "r2", "mse"}
SUPPORTED_BASELINES = set(BASELINE_COLUMNS)
SUPPORTED_RETURN_MODES = {"point", "cumulative"}
SUPPORTED_ITI_PREDICTORS = {"iti_liquido", "iti_risco"}
RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


class ConfigurationError(ValueError):
    """Erro de leitura, validação ou resolução das configurações de research."""


class UniqueKeyLoader(yaml.SafeLoader):
    """Loader YAML que rejeita chaves duplicadas."""


def _construct_unique_mapping(
    loader: UniqueKeyLoader,
    node: yaml.nodes.MappingNode,
    deep: bool = False,
) -> dict[Any, Any]:
    mapping: dict[Any, Any] = {}

    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)

        if key in mapping:
            line = key_node.start_mark.line + 1
            raise ConfigurationError(
                f"Chave YAML duplicada na linha {line}: {key!r}"
            )

        mapping[key] = loader.construct_object(value_node, deep=deep)

    return mapping


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


@dataclass(frozen=True)
class InferenceConfiguration:
    """Configuração de inferência estatística (bootstrap em bloco)."""

    enabled: bool
    n_bootstrap: int
    block_size: int
    ci_level: float
    random_seed: int

    def to_dict(self) -> dict[str, Any]:
        return to_serializable(asdict(self))


@dataclass(frozen=True)
class ResearchConfiguration:
    """Configuração resolvida de ``configs/research.yaml``."""

    schema_version: str
    horizons: tuple[int, ...]
    iti_column: str
    iti_predictors: tuple[str, ...]
    abs_return_predictors: tuple[str, ...]
    return_column: str
    return_mode: str
    run_id: str | None
    experiment_output_root: Path
    model_key: str | None
    dataset_key: str | None
    market_config_path: Path
    company_to_ticker: dict[str, str]
    baselines: tuple[str, ...]
    metrics: tuple[str, ...]
    min_overlap_days: int
    inference: InferenceConfiguration
    research_output_root: Path
    defaults: dict[str, Any]
    raw: dict[str, Any] = field(repr=False)
    config_path: Path = field(repr=False)

    def uses_abs_target(self, predictor_key: str) -> bool:
        return predictor_key in self.abs_return_predictors

    def to_dict(self) -> dict[str, Any]:
        return to_serializable(asdict(self))


def _deep_merge(
    base: Mapping[str, Any],
    override: Mapping[str, Any],
) -> dict[str, Any]:
    result = copy.deepcopy(dict(base))

    for key, value in override.items():
        if (
            key in result
            and isinstance(result[key], Mapping)
            and isinstance(value, Mapping)
        ):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)

    return result


def _require_mapping(value: Any, location: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ConfigurationError(f"{location} precisa ser um objeto YAML.")
    return dict(value)


def _require_list(value: Any, location: str) -> list[Any]:
    if not isinstance(value, list):
        raise ConfigurationError(f"{location} precisa ser uma lista YAML.")
    return value


def _require_string(
    value: Any,
    location: str,
    *,
    allow_empty: bool = False,
) -> str:
    if not isinstance(value, str):
        raise ConfigurationError(f"{location} precisa ser texto.")

    normalized = value.strip()

    if not allow_empty and not normalized:
        raise ConfigurationError(f"{location} não pode ficar vazio.")

    return normalized


def _require_boolean(value: Any, location: str) -> bool:
    if not isinstance(value, bool):
        raise ConfigurationError(f"{location} precisa ser true ou false.")
    return value


def _require_integer(
    value: Any,
    location: str,
    *,
    minimum: int | None = None,
) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigurationError(
            f"{location} precisa ser um número inteiro."
        )

    if minimum is not None and value < minimum:
        raise ConfigurationError(
            f"{location} precisa ser maior ou igual a {minimum}."
        )

    return value


def _require_float(
    value: Any,
    location: str,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigurationError(f"{location} precisa ser numérico.")

    normalized = float(value)
    if minimum is not None and normalized < minimum:
        raise ConfigurationError(
            f"{location} precisa ser maior ou igual a {minimum}."
        )
    if maximum is not None and normalized > maximum:
        raise ConfigurationError(
            f"{location} precisa ser menor ou igual a {maximum}."
        )
    return normalized


def _sanitize_identifier(value: str, location: str) -> str:
    normalized = value.strip()

    if not RUN_ID_PATTERN.fullmatch(normalized):
        raise ConfigurationError(
            f"{location} contém caracteres inválidos: {value!r}."
        )

    return normalized


def _resolve_path(project_root: Path, value: str | Path) -> Path:
    path = Path(value).expanduser()

    if not path.is_absolute():
        path = project_root / path

    return path.resolve()


def _load_yaml_file(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ConfigurationError(
            f"Arquivo de configuração não encontrado: {path}"
        )

    try:
        with path.open("r", encoding="utf-8") as file:
            content = yaml.load(file, Loader=UniqueKeyLoader)
    except ConfigurationError:
        raise
    except yaml.YAMLError as error:
        raise ConfigurationError(
            f"YAML inválido em {path}: {error}"
        ) from error
    except OSError as error:
        raise ConfigurationError(
            f"Não foi possível ler {path}: {error}"
        ) from error

    if content is None:
        raise ConfigurationError(f"Arquivo de configuração vazio: {path}")

    if not isinstance(content, Mapping):
        raise ConfigurationError(
            f"A raiz de {path} precisa ser um objeto YAML."
        )

    return dict(content)


def _validate_schema_version(
    config: Mapping[str, Any],
    path: Path,
) -> None:
    version = str(config.get("schema_version", "")).strip()

    if version != SUPPORTED_SCHEMA_VERSION:
        raise ConfigurationError(
            f"{path} usa schema_version={version!r}. "
            f"A versão suportada é {SUPPORTED_SCHEMA_VERSION!r}."
        )


def _resolve_iti_predictors(
    defaults: Mapping[str, Any],
) -> tuple[str, ...]:
    if "iti_predictors" in defaults:
        raw = _require_list(defaults["iti_predictors"], "defaults.iti_predictors")
        if not raw:
            raise ConfigurationError("defaults.iti_predictors não pode ficar vazio.")
        predictors = tuple(
            _require_string(item, "defaults.iti_predictors")
            for item in raw
        )
    else:
        predictors = (
            _require_string(
                defaults.get("iti_column", "iti_liquido"),
                "defaults.iti_column",
            ),
        )

    invalid = sorted(set(predictors) - SUPPORTED_ITI_PREDICTORS)
    if invalid:
        supported = ", ".join(sorted(SUPPORTED_ITI_PREDICTORS))
        raise ConfigurationError(
            f"defaults.iti_predictors inválidos: {invalid}; use: {supported}."
        )
    return predictors


def _resolve_abs_return_predictors(
    defaults: Mapping[str, Any],
    iti_predictors: tuple[str, ...],
) -> tuple[str, ...]:
    raw = defaults.get("abs_return_predictors", ["iti_risco"])
    items = _require_list(raw, "defaults.abs_return_predictors")
    predictors = tuple(
        _require_string(item, "defaults.abs_return_predictors")
        for item in items
    )
    invalid = sorted(set(predictors) - set(iti_predictors))
    if invalid:
        raise ConfigurationError(
            "defaults.abs_return_predictors precisa ser subconjunto de "
            f"iti_predictors; inválidos: {invalid}."
        )
    return predictors


def _resolve_inference(
    validation: Mapping[str, Any],
) -> InferenceConfiguration:
    inference = _require_mapping(
        validation.get("inference", {}),
        "validation.inference",
    )
    return InferenceConfiguration(
        enabled=_require_boolean(
            inference.get("enabled", True),
            "validation.inference.enabled",
        ),
        n_bootstrap=_require_integer(
            inference.get("n_bootstrap", 500),
            "validation.inference.n_bootstrap",
            minimum=10,
        ),
        block_size=_require_integer(
            inference.get("block_size", 5),
            "validation.inference.block_size",
            minimum=1,
        ),
        ci_level=_require_float(
            inference.get("ci_level", 0.95),
            "validation.inference.ci_level",
            minimum=0.0,
            maximum=1.0,
        ),
        random_seed=_require_integer(
            inference.get("random_seed", 42),
            "validation.inference.random_seed",
            minimum=0,
        ),
    )


def load_research_configuration(
    *,
    project_root: str | Path | None = None,
    config_path: str | Path = "configs/research.yaml",
    run_id: str | None = None,
    model_key: str | None = None,
    dataset_key: str | None = None,
) -> ResearchConfiguration:
    """Carrega e valida ``configs/research.yaml``."""

    root = (
        Path(project_root).expanduser().resolve()
        if project_root is not None
        else PROJECT_ROOT
    )
    resolved_path = _resolve_path(root, config_path)
    raw_config = _load_yaml_file(resolved_path)
    _validate_schema_version(raw_config, resolved_path)

    defaults = _require_mapping(
        raw_config.get("defaults", {}),
        "defaults",
    )
    experiment_run = _require_mapping(
        raw_config.get("experiment_run", {}),
        "experiment_run",
    )
    market = _require_mapping(
        raw_config.get("market", {}),
        "market",
    )
    mapping = _require_mapping(
        raw_config.get("mapping", {}),
        "mapping",
    )
    validation = _require_mapping(
        raw_config.get("validation", {}),
        "validation",
    )
    paths = _require_mapping(
        raw_config.get("paths", {}),
        "paths",
    )

    horizons_raw = _require_list(
        defaults.get("horizons", [1, 5, 21]),
        "defaults.horizons",
    )
    if not horizons_raw:
        raise ConfigurationError("defaults.horizons não pode ficar vazio.")

    horizons = tuple(
        _require_integer(item, "defaults.horizons", minimum=1)
        for item in horizons_raw
    )

    iti_predictors = _resolve_iti_predictors(defaults)
    iti_column = iti_predictors[0]
    abs_return_predictors = _resolve_abs_return_predictors(
        defaults,
        iti_predictors,
    )
    return_column = _require_string(
        defaults.get("return_column", "log_return"),
        "defaults.return_column",
    )
    return_mode = _require_string(
        defaults.get("return_mode", "cumulative"),
        "defaults.return_mode",
    ).lower()
    if return_mode not in SUPPORTED_RETURN_MODES:
        supported = ", ".join(sorted(SUPPORTED_RETURN_MODES))
        raise ConfigurationError(
            f"defaults.return_mode precisa ser um de: {supported}."
        )

    configured_run_id = experiment_run.get("run_id")
    resolved_run_id: str | None
    if run_id is not None:
        resolved_run_id = _sanitize_identifier(run_id, "run_id")
    elif configured_run_id is None:
        resolved_run_id = None
    else:
        resolved_run_id = _sanitize_identifier(
            _require_string(configured_run_id, "experiment_run.run_id"),
            "experiment_run.run_id",
        )

    experiment_output_root = _resolve_path(
        root,
        _require_string(
            experiment_run.get("output_root", "outputs"),
            "experiment_run.output_root",
        ),
    )
    research_output_root = _resolve_path(
        root,
        _require_string(
            paths.get("output_root", "outputs"),
            "paths.output_root",
        ),
    )

    configured_model_key = experiment_run.get("model_key")
    configured_dataset_key = experiment_run.get("dataset_key")
    resolved_model_key = (
        _sanitize_identifier(model_key, "model_key")
        if model_key is not None
        else (
            _sanitize_identifier(
                _require_string(
                    configured_model_key,
                    "experiment_run.model_key",
                ),
                "experiment_run.model_key",
            )
            if configured_model_key is not None
            else None
        )
    )
    resolved_dataset_key = (
        _sanitize_identifier(dataset_key, "dataset_key")
        if dataset_key is not None
        else (
            _sanitize_identifier(
                _require_string(
                    configured_dataset_key,
                    "experiment_run.dataset_key",
                ),
                "experiment_run.dataset_key",
            )
            if configured_dataset_key is not None
            else None
        )
    )

    market_config_path = _resolve_path(
        root,
        _require_string(
            market.get("config_path", "configs/market.yaml"),
            "market.config_path",
        ),
    )

    company_mapping_raw = _require_mapping(
        mapping.get("company_to_ticker", {}),
        "mapping.company_to_ticker",
    )
    company_to_ticker = {
        _require_string(key, "mapping.company_to_ticker.<empresa>"): _require_string(
            value,
            f"mapping.company_to_ticker.{key}",
        )
        for key, value in company_mapping_raw.items()
    }

    baselines_raw = _require_list(
        validation.get("baselines", list(SUPPORTED_BASELINES)),
        "validation.baselines",
    )
    baselines = tuple(
        _require_string(item, "validation.baselines").lower()
        for item in baselines_raw
    )
    invalid_baselines = sorted(set(baselines) - SUPPORTED_BASELINES)
    if invalid_baselines:
        supported = ", ".join(sorted(SUPPORTED_BASELINES))
        raise ConfigurationError(
            f"validation.baselines inválidos: {invalid_baselines}; use: {supported}."
        )

    metrics_raw = _require_list(
        validation.get("metrics", list(SUPPORTED_METRICS)),
        "validation.metrics",
    )
    metrics = tuple(
        _require_string(item, "validation.metrics").lower()
        for item in metrics_raw
    )
    invalid_metrics = sorted(set(metrics) - SUPPORTED_METRICS)
    if invalid_metrics:
        supported = ", ".join(sorted(SUPPORTED_METRICS))
        raise ConfigurationError(
            f"validation.metrics inválidos: {invalid_metrics}; use: {supported}."
        )

    min_overlap_days = _require_integer(
        validation.get("min_overlap_days", 10),
        "validation.min_overlap_days",
        minimum=1,
    )
    inference = _resolve_inference(validation)

    return ResearchConfiguration(
        schema_version=SUPPORTED_SCHEMA_VERSION,
        horizons=horizons,
        iti_column=iti_column,
        iti_predictors=iti_predictors,
        abs_return_predictors=abs_return_predictors,
        return_column=return_column,
        return_mode=return_mode,
        run_id=resolved_run_id,
        experiment_output_root=experiment_output_root,
        model_key=resolved_model_key,
        dataset_key=resolved_dataset_key,
        market_config_path=market_config_path,
        company_to_ticker=company_to_ticker,
        baselines=baselines,
        metrics=metrics,
        min_overlap_days=min_overlap_days,
        inference=inference,
        research_output_root=research_output_root,
        defaults=defaults,
        raw=raw_config,
        config_path=resolved_path,
    )


__all__ = [
    "ConfigurationError",
    "InferenceConfiguration",
    "ResearchConfiguration",
    "load_research_configuration",
]
