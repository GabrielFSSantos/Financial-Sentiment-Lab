"""Carregamento, validação e resolução das configurações do projeto.

Este módulo centraliza a configuração da pipeline. Ele:

- lê ``experiment.yaml``, ``models.yaml`` e ``datasets.yaml``;
- rejeita chaves YAML duplicadas;
- aplica os valores padrão de modelos e datasets;
- seleciona todos os modelos e datasets ativos;
- aplica seleções temporárias recebidas pela linha de comando;
- monta a matriz cartesiana ``modelo × dataset``;
- resolve o ambiente, o ``run_id`` e os caminhos do experimento;
- produz uma configuração serializável para metadados.

A seleção permanente fica exclusivamente em:

- ``configs/models.yaml``: ``enabled: true`` para modelos;
- ``configs/datasets.yaml``: ``enabled: true`` para datasets.

As opções ``--model`` e ``--dataset`` apenas substituem temporariamente
essa seleção durante uma execução.
"""

from __future__ import annotations

import copy
import re
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence, cast
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import yaml

from pipeline.common import CANONICAL_LABELS, to_serializable


SUPPORTED_SCHEMA_VERSION = "2.0"
SUPPORTED_ENVIRONMENTS = {"local", "sdumont"}
SUPPORTED_DATASET_FORMATS = {"csv", "jsonl"}
SUPPORTED_DEVICES = {"auto", "cpu", "cuda"}
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
class ModelConfiguration:
    """Configuração resolvida de um modelo."""

    key: str
    enabled: bool
    order: int
    model_name: str
    display_name: str
    adapter: str
    model_dir: Path
    parameters: dict[str, Any]
    loading: dict[str, Any]
    validation: dict[str, Any]
    required_files: tuple[str, ...]
    labels: dict[str, Any]
    metadata: dict[str, Any]
    raw: dict[str, Any] = field(repr=False)

    def to_dict(self) -> dict[str, Any]:
        return to_serializable(asdict(self))


@dataclass(frozen=True)
class DatasetConfiguration:
    """Configuração resolvida de um dataset."""

    key: str
    enabled: bool
    order: int
    dataset_name: str
    display_name: str
    path: Path
    format: str
    reader: dict[str, Any]
    columns: dict[str, str | None]
    required_fields: tuple[str, ...]
    labels: dict[str, Any]
    dates: dict[str, Any]
    validation: dict[str, Any]
    metadata: dict[str, Any]
    raw: dict[str, Any] = field(repr=False)

    def to_dict(self) -> dict[str, Any]:
        return to_serializable(asdict(self))


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
    reproducibility: dict[str, Any]
    preflight_checks: dict[str, Any]
    paths: ResolvedPaths
    models: tuple[ModelConfiguration, ...]
    datasets: tuple[DatasetConfiguration, ...]
    combinations: tuple[ExperimentCombination, ...]
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
            else Path(__file__).resolve().parents[1]
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
        models_config = _load_yaml_file(models_config_path)
        datasets_config = _load_yaml_file(datasets_config_path)

        _validate_schema_version(
            models_config,
            models_config_path,
        )
        _validate_schema_version(
            datasets_config,
            datasets_config_path,
        )

        all_models = self._resolve_models(models_config)
        all_datasets = self._resolve_datasets(datasets_config)

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

        combinations = self._build_combinations(
            selected_models,
            selected_datasets,
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
            source_files={
                "experiment": copy.deepcopy(experiment_config),
                "models": copy.deepcopy(models_config),
                "datasets": copy.deepcopy(datasets_config),
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

    def _resolve_models(
        self,
        config: Mapping[str, Any],
    ) -> list[ModelConfiguration]:
        defaults = _require_mapping(
            config.get("defaults", {}),
            "models.defaults",
        )
        models = _require_mapping(
            config.get("models"),
            "models",
        )

        if not models:
            raise ConfigurationError(
                "configs/models.yaml não possui modelos cadastrados."
            )

        resolved: list[ModelConfiguration] = []

        for key, raw_value in models.items():
            model_key = _sanitize_identifier(
                _require_string(key, "models.<chave>"),
                "models.<chave>",
            )
            raw_model = _require_mapping(
                raw_value,
                f"models.{model_key}",
            )
            merged = _deep_merge(defaults, raw_model)

            enabled = _require_boolean(
                merged.get("enabled"),
                f"models.{model_key}.enabled",
            )
            order = _require_integer(
                merged.get("order"),
                f"models.{model_key}.order",
                minimum=0,
            )
            model_name = _sanitize_identifier(
                _require_string(
                    merged.get("model_name"),
                    f"models.{model_key}.model_name",
                ),
                f"models.{model_key}.model_name",
            )

            if model_name != model_key:
                raise ConfigurationError(
                    f"models.{model_key}.model_name precisa ser "
                    f"igual à chave {model_key!r}."
                )

            display_name = _require_string(
                merged.get("display_name"),
                f"models.{model_key}.display_name",
            )
            adapter = _require_string(
                merged.get("adapter"),
                f"models.{model_key}.adapter",
            )

            if adapter.count(".") < 2:
                raise ConfigurationError(
                    f"models.{model_key}.adapter precisa usar "
                    "o formato pacote.modulo.Classe."
                )

            model_dir = _resolve_path(
                self.project_root,
                _require_string(
                    merged.get("model_dir"),
                    f"models.{model_key}.model_dir",
                ),
            )
            parameters = _require_mapping(
                merged.get("parameters"),
                f"models.{model_key}.parameters",
            )
            loading = _require_mapping(
                merged.get("loading"),
                f"models.{model_key}.loading",
            )
            validation = _require_mapping(
                merged.get("validation"),
                f"models.{model_key}.validation",
            )

            batch_size = _require_integer(
                parameters.get("batch_size"),
                f"models.{model_key}.parameters.batch_size",
                minimum=1,
            )
            max_length = _require_integer(
                parameters.get("max_length"),
                f"models.{model_key}.parameters.max_length",
                minimum=1,
            )
            device = _require_string(
                parameters.get("device"),
                f"models.{model_key}.parameters.device",
            ).lower()

            if device not in SUPPORTED_DEVICES:
                raise ConfigurationError(
                    f"models.{model_key}.parameters.device precisa "
                    "ser auto, cpu ou cuda."
                )

            parameters["batch_size"] = batch_size
            parameters["max_length"] = max_length
            parameters["device"] = device

            files = _require_mapping(
                merged.get("files"),
                f"models.{model_key}.files",
            )
            required_files_raw = _require_list(
                files.get("required"),
                f"models.{model_key}.files.required",
            )
            required_files = tuple(
                _require_string(
                    item,
                    f"models.{model_key}.files.required",
                )
                for item in required_files_raw
            )

            if not required_files:
                raise ConfigurationError(
                    f"models.{model_key}.files.required está vazio."
                )

            labels = _require_mapping(
                merged.get("labels"),
                f"models.{model_key}.labels",
            )
            self._validate_model_labels(model_key, labels)

            metadata = _require_mapping(
                merged.get("metadata", {}),
                f"models.{model_key}.metadata",
            )

            resolved.append(
                ModelConfiguration(
                    key=model_key,
                    enabled=enabled,
                    order=order,
                    model_name=model_name,
                    display_name=display_name,
                    adapter=adapter,
                    model_dir=model_dir,
                    parameters=parameters,
                    loading=loading,
                    validation=validation,
                    required_files=required_files,
                    labels=labels,
                    metadata=metadata,
                    raw=merged,
                )
            )

        return sorted(
            resolved,
            key=lambda item: (item.order, item.key),
        )

    def _validate_model_labels(
        self,
        model_key: str,
        labels: Mapping[str, Any],
    ) -> None:
        id2label = _require_mapping(
            labels.get("id2label"),
            f"models.{model_key}.labels.id2label",
        )

        normalized_values = {
            _require_string(
                value,
                f"models.{model_key}.labels.id2label",
            ).upper()
            for value in id2label.values()
        }

        if normalized_values != set(CANONICAL_LABELS):
            raise ConfigurationError(
                f"models.{model_key}.labels.id2label precisa "
                f"conter exatamente {list(CANONICAL_LABELS)}."
            )

        canonical = _require_mapping(
            labels.get("canonical"),
            f"models.{model_key}.labels.canonical",
        )
        expected = {
            "positive": "POSITIVE",
            "negative": "NEGATIVE",
            "neutral": "NEUTRAL",
        }

        for key, expected_value in expected.items():
            actual = _require_string(
                canonical.get(key),
                f"models.{model_key}.labels.canonical.{key}",
            ).upper()

            if actual != expected_value:
                raise ConfigurationError(
                    f"models.{model_key}.labels.canonical.{key} "
                    f"precisa ser {expected_value}."
                )

    def _resolve_datasets(
        self,
        config: Mapping[str, Any],
    ) -> list[DatasetConfiguration]:
        defaults = _require_mapping(
            config.get("defaults", {}),
            "datasets.defaults",
        )
        datasets = _require_mapping(
            config.get("datasets"),
            "datasets",
        )

        if not datasets:
            raise ConfigurationError(
                "configs/datasets.yaml não possui datasets cadastrados."
            )

        resolved: list[DatasetConfiguration] = []

        for key, raw_value in datasets.items():
            dataset_key = _sanitize_identifier(
                _require_string(key, "datasets.<chave>"),
                "datasets.<chave>",
            )
            raw_dataset = _require_mapping(
                raw_value,
                f"datasets.{dataset_key}",
            )
            merged = _deep_merge(defaults, raw_dataset)

            enabled = _require_boolean(
                merged.get("enabled"),
                f"datasets.{dataset_key}.enabled",
            )
            order = _require_integer(
                merged.get("order"),
                f"datasets.{dataset_key}.order",
                minimum=0,
            )
            dataset_name = _sanitize_identifier(
                _require_string(
                    merged.get("dataset_name"),
                    f"datasets.{dataset_key}.dataset_name",
                ),
                f"datasets.{dataset_key}.dataset_name",
            )

            if dataset_name != dataset_key:
                raise ConfigurationError(
                    f"datasets.{dataset_key}.dataset_name precisa ser "
                    f"igual à chave {dataset_key!r}."
                )

            display_name = _require_string(
                merged.get("display_name"),
                f"datasets.{dataset_key}.display_name",
            )
            dataset_path = _resolve_path(
                self.project_root,
                _require_string(
                    merged.get("path"),
                    f"datasets.{dataset_key}.path",
                ),
            )
            dataset_format = _require_string(
                merged.get("format"),
                f"datasets.{dataset_key}.format",
            ).lower()

            if dataset_format not in SUPPORTED_DATASET_FORMATS:
                raise ConfigurationError(
                    f"datasets.{dataset_key}.format não é suportado: "
                    f"{dataset_format}"
                )

            reader = _require_mapping(
                merged.get("reader"),
                f"datasets.{dataset_key}.reader",
            )
            columns_raw = _require_mapping(
                merged.get("columns"),
                f"datasets.{dataset_key}.columns",
            )
            columns: dict[str, str | None] = {}

            for internal_name, original_name in columns_raw.items():
                internal = _require_string(
                    internal_name,
                    f"datasets.{dataset_key}.columns.<chave>",
                )

                if original_name is None:
                    columns[internal] = None
                else:
                    columns[internal] = _require_string(
                        original_name,
                        f"datasets.{dataset_key}.columns.{internal}",
                    )

            required_fields_raw = _require_list(
                merged.get("required_fields", ["news_id", "text"]),
                f"datasets.{dataset_key}.required_fields",
            )
            required_fields = tuple(
                _require_string(
                    item,
                    f"datasets.{dataset_key}.required_fields",
                )
                for item in required_fields_raw
            )

            if not required_fields:
                raise ConfigurationError(
                    f"datasets.{dataset_key}.required_fields está vazio."
                )

            for field_name in required_fields:
                if not columns.get(field_name):
                    raise ConfigurationError(
                        f"datasets.{dataset_key} não possui mapeamento "
                        f"para o campo obrigatório {field_name!r}."
                    )

            labels = _require_mapping(
                merged.get("labels"),
                f"datasets.{dataset_key}.labels",
            )
            dates = _require_mapping(
                merged.get("dates"),
                f"datasets.{dataset_key}.dates",
            )
            validation = _require_mapping(
                merged.get("validation"),
                f"datasets.{dataset_key}.validation",
            )
            metadata = _require_mapping(
                merged.get("metadata", {}),
                f"datasets.{dataset_key}.metadata",
            )

            self._validate_dataset_labels(
                dataset_key,
                labels,
                columns,
            )
            self._validate_dataset_dates(
                dataset_key,
                dates,
                columns,
            )
            self._validate_dataset_reader(
                dataset_key,
                reader,
            )

            resolved.append(
                DatasetConfiguration(
                    key=dataset_key,
                    enabled=enabled,
                    order=order,
                    dataset_name=dataset_name,
                    display_name=display_name,
                    path=dataset_path,
                    format=dataset_format,
                    reader=reader,
                    columns=columns,
                    required_fields=required_fields,
                    labels=labels,
                    dates=dates,
                    validation=validation,
                    metadata=metadata,
                    raw=merged,
                )
            )

        return sorted(
            resolved,
            key=lambda item: (item.order, item.key),
        )

    def _validate_dataset_reader(
        self,
        dataset_key: str,
        reader: Mapping[str, Any],
    ) -> None:
        _require_string(
            reader.get("encoding"),
            f"datasets.{dataset_key}.reader.encoding",
        )
        _require_string(
            reader.get("delimiter"),
            f"datasets.{dataset_key}.reader.delimiter",
        )
        _require_string(
            reader.get("quotechar"),
            f"datasets.{dataset_key}.reader.quotechar",
        )
        _require_integer(
            reader.get("header"),
            f"datasets.{dataset_key}.reader.header",
            minimum=0,
        )
        _require_boolean(
            reader.get("low_memory"),
            f"datasets.{dataset_key}.reader.low_memory",
        )
        _require_boolean(
            reader.get("skip_blank_lines"),
            f"datasets.{dataset_key}.reader.skip_blank_lines",
        )

        on_bad_lines = _require_string(
            reader.get("on_bad_lines"),
            f"datasets.{dataset_key}.reader.on_bad_lines",
        )

        if on_bad_lines not in {"error", "warn", "skip"}:
            raise ConfigurationError(
                f"datasets.{dataset_key}.reader.on_bad_lines precisa "
                "ser error, warn ou skip."
            )

    def _validate_dataset_labels(
        self,
        dataset_key: str,
        labels: Mapping[str, Any],
        columns: Mapping[str, str | None],
    ) -> None:
        available = _require_boolean(
            labels.get("available"),
            f"datasets.{dataset_key}.labels.available",
        )
        _require_boolean(
            labels.get("normalize_case"),
            f"datasets.{dataset_key}.labels.normalize_case",
        )
        _require_boolean(
            labels.get("strip_whitespace"),
            f"datasets.{dataset_key}.labels.strip_whitespace",
        )
        mapping = _require_mapping(
            labels.get("mapping", {}),
            f"datasets.{dataset_key}.labels.mapping",
        )

        if available and not columns.get("true_label"):
            raise ConfigurationError(
                f"datasets.{dataset_key} possui labels.available=true, "
                "mas columns.true_label não foi mapeada."
            )

        if available and not mapping:
            raise ConfigurationError(
                f"datasets.{dataset_key} possui rótulos, mas o "
                "mapeamento está vazio."
            )

        invalid = sorted(
            {
                _require_string(
                    value,
                    f"datasets.{dataset_key}.labels.mapping",
                ).upper()
                for value in mapping.values()
            }
            - set(CANONICAL_LABELS)
        )

        if invalid:
            raise ConfigurationError(
                f"datasets.{dataset_key} possui classes de destino "
                f"inválidas: {invalid}"
            )

    def _validate_dataset_dates(
        self,
        dataset_key: str,
        dates: Mapping[str, Any],
        columns: Mapping[str, str | None],
    ) -> None:
        available = _require_boolean(
            dates.get("available"),
            f"datasets.{dataset_key}.dates.available",
        )
        _require_boolean(
            dates.get("dayfirst"),
            f"datasets.{dataset_key}.dates.dayfirst",
        )
        _require_boolean(
            dates.get("fail_on_invalid"),
            f"datasets.{dataset_key}.dates.fail_on_invalid",
        )
        _require_string(
            dates.get("output_format"),
            f"datasets.{dataset_key}.dates.output_format",
        )

        if available:
            if not columns.get("date"):
                raise ConfigurationError(
                    f"datasets.{dataset_key} possui dates.available=true, "
                    "mas columns.date não foi mapeada."
                )

            _require_string(
                dates.get("format"),
                f"datasets.{dataset_key}.dates.format",
            )
        elif dates.get("format") is not None:
            raise ConfigurationError(
                f"datasets.{dataset_key}.dates.format precisa ser null "
                "quando dates.available=false."
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
    ) -> list[ExperimentCombination]:
        combinations: list[ExperimentCombination] = []
        index = 0

        for model in models:
            for dataset in datasets:
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

        return combinations

    def _validate_resolved_configuration(
        self,
        config: ResolvedConfiguration,
    ) -> None:
        if not config.combinations:
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
            if not dataset.path.is_file():
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