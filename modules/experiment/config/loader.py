"""Carregamento, validação e resolução das configurações YAML."""

from __future__ import annotations

import copy
import re
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence, cast
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import yaml

from modules.experiment import PROJECT_ROOT
from modules.experiment.common import CANONICAL_LABELS, to_serializable
from modules.datasets.config.loader import (
    ConfigurationError as DatasetsConfigurationError,
    DatasetConfiguration,
    load_datasets_configuration,
)
from modules.models.config.loader import (
    ConfigurationError as ModelsConfigurationError,
    ModelConfiguration,
    load_models_configuration,
)


SUPPORTED_SCHEMA_VERSION = "2.0"
SUPPORTED_ENVIRONMENTS = {"local", "sdumont"}
SUPPORTED_DATASET_FORMATS = {"csv", "jsonl", "parquet", "huggingface"}
SUPPORTED_SOURCE_PROVIDERS = {
    "huggingface_hub",
    "huggingface_hub_file",
    "huggingface_dataset",
}
SUPPORTED_DEVICES = {"auto", "cpu", "cuda"}
SUPPORTED_LANGUAGES = {"pt", "en"}
SUPPORTED_AGGREGATION_LEVELS = {
    "company_day",
    "sector_day",
    "market_day",
}
SUPPORTED_AGGREGATION_STATISTICS = {
    "mean",
    "median",
    "sum",
    "count",
}
RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


class ConfigurationError(ValueError):
    """Erro de leitura, validação ou resolução das configurações."""


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
class ExperimentCombination:
    """Uma combinação de modelo e dataset que será executada."""

    index: int
    model_key: str
    dataset_key: str
    combination_id: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SkippedCombination:
    """Combinação modelo×dataset excluída antes da execução."""

    model_key: str
    dataset_key: str
    reason: str
    model_language: str
    dataset_language: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ResolvedPaths:
    """Caminhos absolutos e relativos usados pelo experimento."""

    project_root: Path
    experiment_config: Path
    models_config: Path
    datasets_config: Path
    output_root: Path
    run_root: Path
    models_output_root: Path
    log_root: Path
    temp_root: Path

    def combination_root(
        self,
        model_key: str,
        dataset_key: str,
    ) -> Path:
        return (
            self.models_output_root
            / _sanitize_identifier(model_key, "model_key")
            / _sanitize_identifier(dataset_key, "dataset_key")
        )

    def indices_root(
        self,
        model_key: str,
        dataset_key: str,
    ) -> Path:
        return (
            self.run_root
            / "indices"
            / _sanitize_identifier(model_key, "model_key")
            / _sanitize_identifier(dataset_key, "dataset_key")
        )

    def merged_indices_root(self, dataset_key: str) -> Path:
        return (
            self.run_root
            / "indices"
            / "merged"
            / _sanitize_identifier(dataset_key, "dataset_key")
        )

    def to_dict(self) -> dict[str, str]:
        return {
            key: str(value)
            for key, value in asdict(self).items()
        }


@dataclass(frozen=True)
class ResolvedConfiguration:
    """Configuração completa pronta para ser usada pelo runner."""

    schema_version: str
    run_id: str
    environment: str
    dry_run: bool
    experiment: dict[str, Any]
    execution: dict[str, Any]
    outputs: dict[str, Any]
    classification_metrics: dict[str, Any]
    performance_metrics: dict[str, Any]
    aggregation: dict[str, Any]
    compatibility: dict[str, Any]
    temporal_index: dict[str, Any]
    reproducibility: dict[str, Any]
    preflight_checks: dict[str, Any]
    paths: ResolvedPaths
    models: tuple[ModelConfiguration, ...]
    datasets: tuple[DatasetConfiguration, ...]
    combinations: tuple[ExperimentCombination, ...]
    skipped_combinations: tuple[SkippedCombination, ...]
    source_files: dict[str, dict[str, Any]] = field(repr=False)

    @property
    def model_keys(self) -> tuple[str, ...]:
        return tuple(model.key for model in self.models)

    @property
    def dataset_keys(self) -> tuple[str, ...]:
        return tuple(dataset.key for dataset in self.datasets)

    def get_model(self, key: str) -> ModelConfiguration:
        for model in self.models:
            if model.key == key:
                return model
        raise ConfigurationError(
            f"Modelo não selecionado na configuração resolvida: {key}"
        )

    def get_dataset(self, key: str) -> DatasetConfiguration:
        for dataset in self.datasets:
            if dataset.key == key:
                return dataset
        raise ConfigurationError(
            f"Dataset não selecionado na configuração resolvida: {key}"
        )

    def to_dict(self) -> dict[str, Any]:
        """Retorna uma estrutura segura para JSON ou YAML."""

        return {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "environment": self.environment,
            "dry_run": self.dry_run,
            "experiment": to_serializable(self.experiment),
            "execution": to_serializable(self.execution),
            "outputs": to_serializable(self.outputs),
            "classification_metrics": to_serializable(
                self.classification_metrics
            ),
            "performance_metrics": to_serializable(
                self.performance_metrics
            ),
            "aggregation": to_serializable(self.aggregation),
            "compatibility": to_serializable(self.compatibility),
            "temporal_index": to_serializable(self.temporal_index),
            "reproducibility": to_serializable(self.reproducibility),
            "preflight_checks": to_serializable(self.preflight_checks),
            "paths": self.paths.to_dict(),
            "selected_models": [
                model.to_dict()
                for model in self.models
            ],
            "selected_datasets": [
                dataset.to_dict()
                for dataset in self.datasets
            ],
            "combinations": [
                combination.to_dict()
                for combination in self.combinations
            ],
            "skipped_combinations": [
                skipped.to_dict()
                for skipped in self.skipped_combinations
            ],
            "configuration_sources": {
                "experiment": str(self.paths.experiment_config),
                "models": str(self.paths.models_config),
                "datasets": str(self.paths.datasets_config),
            },
        }


def _deep_merge(
    base: Mapping[str, Any],
    override: Mapping[str, Any],
) -> dict[str, Any]:
    """Mescla recursivamente dois mapeamentos sem alterar os originais."""

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


def _require_mapping(
    value: Any,
    location: str,
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ConfigurationError(
            f"{location} precisa ser um objeto YAML."
        )
    return dict(value)


def _require_list(
    value: Any,
    location: str,
) -> list[Any]:
    if not isinstance(value, list):
        raise ConfigurationError(
            f"{location} precisa ser uma lista YAML."
        )
    return value


def _require_string(
    value: Any,
    location: str,
    *,
    allow_empty: bool = False,
) -> str:
    if not isinstance(value, str):
        raise ConfigurationError(
            f"{location} precisa ser texto."
        )

    normalized = value.strip()

    if not allow_empty and not normalized:
        raise ConfigurationError(
            f"{location} não pode ficar vazio."
        )

    return normalized


def _require_language(value: Any, location: str) -> str:
    language = _require_string(value, location).lower()

    if language not in SUPPORTED_LANGUAGES:
        supported = ", ".join(sorted(SUPPORTED_LANGUAGES))
        raise ConfigurationError(
            f"{location} precisa ser um idioma suportado: {supported}."
        )

    return language


def _optional_mapping(
    value: Any,
    location: str,
) -> dict[str, Any]:
    if value is None:
        return {}
    return dict(_require_mapping(value, location))


def _resolve_optional_source(
    *,
    project_root: Path,
    raw_source: Any,
    location: str,
    default_local_dir: Path | None = None,
    default_local_path: Path | None = None,
) -> dict[str, Any]:
    if raw_source is None:
        return {}

    source = dict(_require_mapping(raw_source, location))
    provider = _require_string(
        source.get("provider"),
        f"{location}.provider",
    ).lower()

    if provider not in SUPPORTED_SOURCE_PROVIDERS:
        supported = ", ".join(sorted(SUPPORTED_SOURCE_PROVIDERS))
        raise ConfigurationError(
            f"{location}.provider precisa ser um dos valores: {supported}."
        )

    source["provider"] = provider
    source["repo_id"] = _require_string(
        source.get("repo_id"),
        f"{location}.repo_id",
    )
    source["revision"] = _require_string(
        source.get("revision", "main"),
        f"{location}.revision",
    )

    if provider == "huggingface_hub":
        local_dir = source.get("local_dir")
        if local_dir is None and default_local_dir is not None:
            local_dir = str(default_local_dir.relative_to(project_root))
        source["local_dir"] = str(
            _resolve_path(
                project_root,
                _require_string(
                    local_dir,
                    f"{location}.local_dir",
                ),
            )
        )
    elif provider == "huggingface_hub_file":
        filename = _require_string(
            source.get("filename"),
            f"{location}.filename",
        )
        local_path = source.get("local_path")
        if local_path is None and default_local_path is not None:
            local_path = str(default_local_path.relative_to(project_root))
        source["filename"] = filename
        source["local_path"] = str(
            _resolve_path(
                project_root,
                _require_string(
                    local_path,
                    f"{location}.local_path",
                ),
            )
        )
    elif provider == "huggingface_dataset":
        source["config"] = _require_string(
            source.get("config", "default"),
            f"{location}.config",
        )
        source["split"] = _require_string(
            source.get("split", "train"),
            f"{location}.split",
        )
        if source.get("data_files") is not None:
            source["data_files"] = _require_string(
                source["data_files"],
                f"{location}.data_files",
            )
        local_path = source.get("local_path")
        if local_path is None and default_local_path is not None:
            local_path = str(default_local_path.relative_to(project_root))
        if local_path is not None:
            source["local_path"] = str(
                _resolve_path(
                    project_root,
                    _require_string(
                        local_path,
                        f"{location}.local_path",
                    ),
                )
            )

    if source.get("materialize_format") is not None:
        materialize_format = str(source["materialize_format"]).lower()
        if materialize_format not in {"csv", "jsonl"}:
            raise ConfigurationError(
                f"{location}.materialize_format precisa ser csv ou jsonl."
            )
        source["materialize_format"] = materialize_format

    return source


def _resolve_max_rows_limit(value: Any, location: str) -> int | None:
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized == "max":
            return None
        raise ConfigurationError(
            f"{location} precisa ser inteiro >= 1 ou max."
        )
    return _require_integer(value, location, minimum=1)


def _resolve_dataset_limits(
    raw_limits: Any,
    location: str,
) -> dict[str, Any]:
    limits = _optional_mapping(raw_limits, location)
    resolved: dict[str, Any] = {}

    if "max_rows" in limits:
        resolved["max_rows"] = _resolve_max_rows_limit(
            limits["max_rows"],
            f"{location}.max_rows",
        )

    for key in ("date_from", "date_to"):
        if key in limits:
            value = limits[key]
            if value is None:
                continue
            resolved[key] = _require_string(
                value,
                f"{location}.{key}",
            )

    return resolved


def _resolve_text_compose(
    raw_compose: Any,
    location: str,
) -> dict[str, Any] | None:
    if raw_compose is None:
        return None

    compose = dict(_require_mapping(raw_compose, location))
    compose["template"] = _require_string(
        compose.get("template"),
        f"{location}.template",
    )
    fields = _require_mapping(
        compose.get("fields"),
        f"{location}.fields",
    )
    compose["fields"] = {
        _require_string(key, f"{location}.fields.<chave>"): _require_string(
            value,
            f"{location}.fields.{key}",
        )
        for key, value in fields.items()
    }
    compose["skip_if_all_empty"] = _require_boolean(
        compose.get("skip_if_all_empty", True),
        f"{location}.skip_if_all_empty",
    )
    return compose


def _require_boolean(
    value: Any,
    location: str,
) -> bool:
    if not isinstance(value, bool):
        raise ConfigurationError(
            f"{location} precisa ser true ou false."
        )
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


def _sanitize_identifier(
    value: str,
    location: str,
) -> str:
    normalized = value.strip()

    if not RUN_ID_PATTERN.fullmatch(normalized):
        raise ConfigurationError(
            f"{location} contém caracteres inválidos: {value!r}. "
            "Use apenas letras, números, ponto, hífen e sublinhado."
        )

    return normalized


def _normalize_requested_keys(
    values: Sequence[str] | None,
    option_name: str,
) -> tuple[str, ...]:
    if not values:
        return ()

    result: list[str] = []
    seen: set[str] = set()

    for value in values:
        if not isinstance(value, str):
            raise ConfigurationError(
                f"{option_name} precisa receber nomes em texto."
            )

        for item in value.split(","):
            key = item.strip()

            if not key:
                continue

            _sanitize_identifier(key, option_name)

            if key not in seen:
                seen.add(key)
                result.append(key)

    if not result:
        raise ConfigurationError(
            f"{option_name} foi informado, mas não contém nomes válidos."
        )

    return tuple(result)


def _resolve_path(
    project_root: Path,
    value: str | Path,
) -> Path:
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
        raise ConfigurationError(
            f"Arquivo de configuração vazio: {path}"
        )

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


class ConfigurationLoader:
    """Carrega e resolve todos os arquivos de configuração."""

    def __init__(
        self,
        *,
        project_root: str | Path | None = None,
        experiment_config: str | Path = "configs/experiment.yaml",
        model_keys: Sequence[str] | None = None,
        dataset_keys: Sequence[str] | None = None,
        environment: str | None = None,
        dry_run: bool | None = None,
        run_id: str | None = None,
    ) -> None:
        root = (
            Path(project_root)
            if project_root is not None
            else PROJECT_ROOT
        )

        self.project_root = root.expanduser().resolve()
        self.experiment_config_path = _resolve_path(
            self.project_root,
            experiment_config,
        )
        self.requested_model_keys = _normalize_requested_keys(
            model_keys,
            "--model",
        )
        self.requested_dataset_keys = _normalize_requested_keys(
            dataset_keys,
            "--dataset",
        )
        self.environment_override = environment
        self.dry_run_override = dry_run
        self.run_id_override = run_id

    def load(self) -> ResolvedConfiguration:
        experiment_config = _load_yaml_file(
            self.experiment_config_path
        )
        _validate_schema_version(
            experiment_config,
            self.experiment_config_path,
        )
        self._validate_experiment_structure(experiment_config)

        config_files = _require_mapping(
            experiment_config["configuration_files"],
            "configuration_files",
        )

        models_config_path = _resolve_path(
            self.project_root,
            _require_string(
                config_files.get("models"),
                "configuration_files.models",
            ),
        )
        datasets_config_path = _resolve_path(
            self.project_root,
            _require_string(
                config_files.get("datasets"),
                "configuration_files.datasets",
            ),
        )
        try:
            models_cfg = load_models_configuration(
                project_root=self.project_root,
                config_path=models_config_path,
            )
        except ModelsConfigurationError as error:
            raise ConfigurationError(str(error)) from error
        try:
            datasets_cfg = load_datasets_configuration(
                project_root=self.project_root,
                config_path=datasets_config_path,
            )
        except DatasetsConfigurationError as error:
            raise ConfigurationError(str(error)) from error

        all_models = list(models_cfg.models)
        all_datasets = list(datasets_cfg.datasets)

        selected_models = self._select_models(all_models)
        selected_datasets = self._select_datasets(all_datasets)

        experiment_section = copy.deepcopy(
            _require_mapping(
                experiment_config["experiment"],
                "experiment",
            )
        )
        execution_section = copy.deepcopy(
            _require_mapping(
                experiment_config["execution"],
                "execution",
            )
        )

        environment = self._resolve_environment(execution_section)
        dry_run = self._resolve_dry_run(execution_section)
        run_id = self._resolve_run_id(experiment_section)

        execution_section["environment"] = environment
        execution_section["dry_run"] = dry_run
        experiment_section["run_id"] = run_id

        paths = self._resolve_paths(
            experiment_config=experiment_config,
            models_config_path=models_config_path,
            datasets_config_path=datasets_config_path,
            run_id=run_id,
        )

        combinations, skipped_combinations = self._build_combinations(
            selected_models,
            selected_datasets,
            require_language_match=_require_boolean(
                _require_mapping(
                    experiment_config.get(
                        "compatibility",
                        {"require_language_match": True},
                    ),
                    "compatibility",
                ).get(
                    "require_language_match",
                    True,
                ),
                "compatibility.require_language_match",
            ),
        )

        resolved = ResolvedConfiguration(
            schema_version=SUPPORTED_SCHEMA_VERSION,
            run_id=run_id,
            environment=environment,
            dry_run=dry_run,
            experiment=experiment_section,
            execution=execution_section,
            outputs=copy.deepcopy(
                _require_mapping(
                    experiment_config["outputs"],
                    "outputs",
                )
            ),
            classification_metrics=copy.deepcopy(
                _require_mapping(
                    experiment_config["classification_metrics"],
                    "classification_metrics",
                )
            ),
            performance_metrics=copy.deepcopy(
                _require_mapping(
                    experiment_config["performance_metrics"],
                    "performance_metrics",
                )
            ),
            aggregation=copy.deepcopy(
                _require_mapping(
                    experiment_config["aggregation"],
                    "aggregation",
                )
            ),
            compatibility=copy.deepcopy(
                _require_mapping(
                    experiment_config.get(
                        "compatibility",
                        {"require_language_match": True},
                    ),
                    "compatibility",
                )
            ),
            temporal_index=copy.deepcopy(
                _require_mapping(
                    experiment_config.get(
                        "temporal_index",
                        {"enabled": False},
                    ),
                    "temporal_index",
                )
            ),
            reproducibility=copy.deepcopy(
                _require_mapping(
                    experiment_config["reproducibility"],
                    "reproducibility",
                )
            ),
            preflight_checks=copy.deepcopy(
                _require_mapping(
                    experiment_config["preflight_checks"],
                    "preflight_checks",
                )
            ),
            paths=paths,
            models=tuple(selected_models),
            datasets=tuple(selected_datasets),
            combinations=tuple(combinations),
            skipped_combinations=tuple(skipped_combinations),
            source_files={
                "experiment": copy.deepcopy(experiment_config),
                "models": _load_yaml_file(models_config_path),
                "datasets": _load_yaml_file(datasets_config_path),
            },
        )

        self._validate_resolved_configuration(resolved)
        return resolved

    def _validate_experiment_structure(
        self,
        config: Mapping[str, Any],
    ) -> None:
        obsolete_sections = {
            "model_selection",
            "dataset_selection",
            "combined_sentiment_index",
            "parallelism",
            "paper_reproduction",
            "asset_fetch",
        }
        found_obsolete = sorted(
            obsolete_sections.intersection(config)
        )

        if found_obsolete:
            raise ConfigurationError(
                "configs/experiment.yaml contém seções removidas: "
                f"{found_obsolete}. Modelos e datasets devem ser "
                "controlados por enabled em seus próprios arquivos."
            )

        required_sections = {
            "experiment",
            "execution",
            "configuration_files",
            "paths",
            "outputs",
            "classification_metrics",
            "performance_metrics",
            "aggregation",
            "reproducibility",
            "preflight_checks",
        }
        missing = sorted(required_sections.difference(config))

        if missing:
            raise ConfigurationError(
                "Seções obrigatórias ausentes em experiment.yaml: "
                f"{missing}"
            )

        experiment = _require_mapping(
            config["experiment"],
            "experiment",
        )
        execution = _require_mapping(
            config["execution"],
            "execution",
        )
        outputs = _require_mapping(
            config["outputs"],
            "outputs",
        )
        aggregation = _require_mapping(
            config["aggregation"],
            "aggregation",
        )

        _require_string(
            experiment.get("name"),
            "experiment.name",
        )
        _require_string(
            experiment.get("run_id_prefix"),
            "experiment.run_id_prefix",
        )
        _require_integer(
            experiment.get("random_seed"),
            "experiment.random_seed",
            minimum=0,
        )
        _require_string(
            experiment.get("timezone"),
            "experiment.timezone",
        )

        configured_run_id = experiment.get("run_id")
        if configured_run_id is not None:
            _sanitize_identifier(
                _require_string(
                    configured_run_id,
                    "experiment.run_id",
                ),
                "experiment.run_id",
            )

        environment = _require_string(
            execution.get("environment"),
            "execution.environment",
        ).lower()

        if environment not in SUPPORTED_ENVIRONMENTS:
            raise ConfigurationError(
                "execution.environment precisa ser local ou sdumont."
            )

        for key in (
            "dry_run",
            "fail_fast",
            "save_partial_results",
            "overwrite_existing_run",
            "unload_model_after_combination",
        ):
            _require_boolean(
                execution.get(key),
                f"execution.{key}",
            )

        log_level = _require_string(
            execution.get("log_level"),
            "execution.log_level",
        ).upper()

        if log_level not in {
            "DEBUG",
            "INFO",
            "WARNING",
            "ERROR",
            "CRITICAL",
        }:
            raise ConfigurationError(
                "execution.log_level possui um valor inválido."
            )

        for key in (
            "save_predictions",
            "save_metrics",
            "save_aggregates",
            "save_metadata",
            "save_experiment_summary",
            "save_resolved_config",
        ):
            _require_boolean(
                outputs.get(key),
                f"outputs.{key}",
            )

        if outputs.get("tabular_format") != "csv":
            raise ConfigurationError(
                "outputs.tabular_format atualmente precisa ser csv."
            )

        precision = _require_integer(
            outputs.get("float_precision"),
            "outputs.float_precision",
            minimum=0,
        )

        if precision > 15:
            raise ConfigurationError(
                "outputs.float_precision não pode ser maior que 15."
            )

        levels = _require_list(
            aggregation.get("levels"),
            "aggregation.levels",
        )
        invalid_levels = sorted(
            set(levels) - SUPPORTED_AGGREGATION_LEVELS
        )

        if invalid_levels:
            raise ConfigurationError(
                f"Níveis de agregação inválidos: {invalid_levels}"
            )

        statistics = _require_list(
            aggregation.get("statistics"),
            "aggregation.statistics",
        )
        invalid_statistics = sorted(
            set(statistics)
            - SUPPORTED_AGGREGATION_STATISTICS
        )

        if invalid_statistics:
            raise ConfigurationError(
                "Estatísticas de agregação inválidas: "
                f"{invalid_statistics}"
            )

    def _select_models(
        self,
        models: Sequence[ModelConfiguration],
    ) -> list[ModelConfiguration]:
        by_key = {model.key: model for model in models}

        if self.requested_model_keys:
            missing = [
                key
                for key in self.requested_model_keys
                if key not in by_key
            ]

            if missing:
                raise ConfigurationError(
                    f"Modelos solicitados não cadastrados: {missing}"
                )

            requested = set(self.requested_model_keys)
            selected = [
                model
                for model in models
                if model.key in requested
            ]
        else:
            selected = [
                model
                for model in models
                if model.enabled
            ]

        if not selected:
            raise ConfigurationError(
                "Nenhum modelo foi selecionado. Ative pelo menos um "
                "modelo em configs/models.yaml ou use --model."
            )

        return selected

    def _select_datasets(
        self,
        datasets: Sequence[DatasetConfiguration],
    ) -> list[DatasetConfiguration]:
        by_key = {
            dataset.key: dataset
            for dataset in datasets
        }

        if self.requested_dataset_keys:
            missing = [
                key
                for key in self.requested_dataset_keys
                if key not in by_key
            ]

            if missing:
                raise ConfigurationError(
                    f"Datasets solicitados não cadastrados: {missing}"
                )

            requested = set(self.requested_dataset_keys)
            selected = [
                dataset
                for dataset in datasets
                if dataset.key in requested
            ]
        else:
            selected = [
                dataset
                for dataset in datasets
                if dataset.enabled
            ]

        if not selected:
            raise ConfigurationError(
                "Nenhum dataset foi selecionado. Ative pelo menos um "
                "dataset em configs/datasets.yaml ou use --dataset."
            )

        return selected

    def _resolve_environment(
        self,
        execution: Mapping[str, Any],
    ) -> str:
        value = (
            self.environment_override
            if self.environment_override is not None
            else execution.get("environment")
        )
        environment = _require_string(
            value,
            "execution.environment",
        ).lower()

        if environment not in SUPPORTED_ENVIRONMENTS:
            raise ConfigurationError(
                "O ambiente precisa ser local ou sdumont."
            )

        return environment

    def _resolve_dry_run(
        self,
        execution: Mapping[str, Any],
    ) -> bool:
        if self.dry_run_override is not None:
            if not isinstance(self.dry_run_override, bool):
                raise ConfigurationError(
                    "A sobrescrita de dry_run precisa ser booleana."
                )
            return self.dry_run_override

        return _require_boolean(
            execution.get("dry_run"),
            "execution.dry_run",
        )

    def _resolve_run_id(
        self,
        experiment: Mapping[str, Any],
    ) -> str:
        configured = (
            self.run_id_override
            if self.run_id_override is not None
            else experiment.get("run_id")
        )

        if configured is not None:
            return _sanitize_identifier(
                _require_string(
                    configured,
                    "experiment.run_id",
                ),
                "experiment.run_id",
            )

        prefix = _sanitize_identifier(
            _require_string(
                experiment.get("run_id_prefix"),
                "experiment.run_id_prefix",
            ),
            "experiment.run_id_prefix",
        )
        timezone_name = _require_string(
            experiment.get("timezone"),
            "experiment.timezone",
        )

        try:
            timezone = ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError as error:
            raise ConfigurationError(
                f"Fuso horário inválido: {timezone_name}"
            ) from error

        timestamp = datetime.now(timezone).strftime(
            "%Y%m%d_%H%M%S"
        )
        return f"{prefix}_{timestamp}"

    def _resolve_paths(
        self,
        *,
        experiment_config: Mapping[str, Any],
        models_config_path: Path,
        datasets_config_path: Path,
        run_id: str,
    ) -> ResolvedPaths:
        paths = _require_mapping(
            experiment_config["paths"],
            "paths",
        )
        output_root = _resolve_path(
            self.project_root,
            _require_string(
                paths.get("output_root"),
                "paths.output_root",
            ),
        )
        log_root = _resolve_path(
            self.project_root,
            _require_string(
                paths.get("log_root"),
                "paths.log_root",
            ),
        )
        temp_root = _resolve_path(
            self.project_root,
            _require_string(
                paths.get("temp_root"),
                "paths.temp_root",
            ),
        )
        run_root = output_root / run_id

        return ResolvedPaths(
            project_root=self.project_root,
            experiment_config=self.experiment_config_path,
            models_config=models_config_path,
            datasets_config=datasets_config_path,
            output_root=output_root,
            run_root=run_root,
            models_output_root=run_root / "models",
            log_root=log_root,
            temp_root=temp_root,
        )

    def _build_combinations(
        self,
        models: Sequence[ModelConfiguration],
        datasets: Sequence[DatasetConfiguration],
        *,
        require_language_match: bool,
    ) -> tuple[list[ExperimentCombination], list[SkippedCombination]]:
        combinations: list[ExperimentCombination] = []
        skipped: list[SkippedCombination] = []
        index = 0

        for model in models:
            for dataset in datasets:
                if (
                    require_language_match
                    and model.language != dataset.language
                ):
                    skipped.append(
                        SkippedCombination(
                            model_key=model.key,
                            dataset_key=dataset.key,
                            reason="language_mismatch",
                            model_language=model.language,
                            dataset_language=dataset.language,
                        )
                    )
                    continue

                combinations.append(
                    ExperimentCombination(
                        index=index,
                        model_key=model.key,
                        dataset_key=dataset.key,
                        combination_id=(
                            f"{model.key}__{dataset.key}"
                        ),
                    )
                )
                index += 1

        return combinations, skipped

    def _validate_resolved_configuration(
        self,
        config: ResolvedConfiguration,
    ) -> None:
        if not config.combinations:
            if config.skipped_combinations:
                skipped_summary = ", ".join(
                    f"{item.model_key}×{item.dataset_key}"
                    for item in config.skipped_combinations
                )
                raise ConfigurationError(
                    "A matriz modelo × dataset ficou vazia após o "
                    f"filtro de idioma. Combinações ignoradas: "
                    f"{skipped_summary}."
                )

            raise ConfigurationError(
                "A matriz modelo × dataset ficou vazia."
            )

        checks = config.preflight_checks

        if not _require_boolean(
            checks.get("enabled"),
            "preflight_checks.enabled",
        ):
            return

        if checks.get("validate_model_files", True):
            self._validate_model_resources(config.models)

        if checks.get("validate_dataset_files", True):
            self._validate_dataset_resources(config.datasets)

        if checks.get("validate_output_directory", True):
            self._validate_parent_directory(
                config.paths.output_root,
                "diretório de saída",
            )

    def _validate_model_resources(
        self,
        models: Iterable[ModelConfiguration],
    ) -> None:
        for model in models:
            if model.source:
                continue

            validation = model.validation

            if validation.get("require_model_directory", True):
                if not model.model_dir.is_dir():
                    raise ConfigurationError(
                        f"Diretório do modelo {model.key} não encontrado: "
                        f"{model.model_dir}"
                    )

            if validation.get("require_required_files", True):
                missing = [
                    filename
                    for filename in model.required_files
                    if not (model.model_dir / filename).is_file()
                ]

                if missing:
                    raise ConfigurationError(
                        f"O modelo {model.key} não possui os arquivos "
                        f"obrigatórios: {missing}"
                    )

    def _validate_dataset_resources(
        self,
        datasets: Iterable[DatasetConfiguration],
    ) -> None:
        for dataset in datasets:
            if dataset.format == "huggingface" and dataset.path is None:
                if not dataset.source:
                    raise ConfigurationError(
                        f"O dataset {dataset.key} usa format=huggingface "
                        "sem path e sem source declarado."
                    )
                continue

            if dataset.source and (
                dataset.path is None or not dataset.path.is_file()
            ):
                continue

            if dataset.path is None or not dataset.path.is_file():
                raise ConfigurationError(
                    f"Arquivo do dataset {dataset.key} não encontrado: "
                    f"{dataset.path}"
                )

    def _validate_parent_directory(
        self,
        path: Path,
        description: str,
    ) -> None:
        current = path

        while not current.exists() and current != current.parent:
            current = current.parent

        if not current.exists():
            raise ConfigurationError(
                f"Não foi possível localizar um diretório pai para "
                f"{description}: {path}"
            )

        if not current.is_dir():
            raise ConfigurationError(
                f"O caminho pai de {description} não é um diretório: "
                f"{current}"
            )


def load_configuration(
    *,
    project_root: str | Path | None = None,
    experiment_config: str | Path = "configs/experiment.yaml",
    model_keys: Sequence[str] | None = None,
    dataset_keys: Sequence[str] | None = None,
    environment: str | None = None,
    dry_run: bool | None = None,
    run_id: str | None = None,
) -> ResolvedConfiguration:
    """Atalho público para carregar a configuração completa."""

    loader = ConfigurationLoader(
        project_root=project_root,
        experiment_config=experiment_config,
        model_keys=model_keys,
        dataset_keys=dataset_keys,
        environment=environment,
        dry_run=dry_run,
        run_id=run_id,
    )
    return loader.load()


__all__ = [
    "CANONICAL_LABELS",
    "ConfigurationError",
    "ConfigurationLoader",
    "DatasetConfiguration",
    "ExperimentCombination",
    "ModelConfiguration",
    "ResolvedConfiguration",
    "ResolvedPaths",
    "load_configuration",
]