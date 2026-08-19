"""Carregamento e validação de ``configs/datasets.yaml``."""

from __future__ import annotations

import copy
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Mapping

import yaml

from modules.datasets import PROJECT_ROOT
from modules.datasets.common import CANONICAL_LABELS, to_serializable


SUPPORTED_SCHEMA_VERSION = "2.0"
SUPPORTED_DATASET_FORMATS = {"csv", "jsonl", "parquet", "huggingface"}
SUPPORTED_SOURCE_PROVIDERS = {
    "huggingface_hub",
    "huggingface_hub_file",
    "huggingface_dataset",
}
SUPPORTED_LANGUAGES = {"pt", "en"}
RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


class ConfigurationError(ValueError):
    """Erro de leitura, validação ou resolução das configurações de datasets."""


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
class DatasetConfiguration:
    """Configuração resolvida de um dataset."""

    key: str
    enabled: bool
    order: int
    dataset_name: str
    display_name: str
    language: str
    path: Path | None
    format: str
    reader: dict[str, Any]
    columns: dict[str, str | None]
    required_fields: tuple[str, ...]
    labels: dict[str, Any]
    dates: dict[str, Any]
    validation: dict[str, Any]
    metadata: dict[str, Any]
    source: dict[str, Any]
    text_compose: dict[str, Any] | None
    limits: dict[str, Any]
    raw: dict[str, Any] = field(repr=False)

    def to_dict(self) -> dict[str, Any]:
        return to_serializable(asdict(self))


@dataclass(frozen=True)
class DatasetsConfiguration:
    """Configuração completa de ``configs/datasets.yaml``."""

    schema_version: str
    defaults: dict[str, Any]
    datasets: tuple[DatasetConfiguration, ...]
    config_path: Path

    @property
    def enabled_datasets(self) -> tuple[DatasetConfiguration, ...]:
        return tuple(dataset for dataset in self.datasets if dataset.enabled)

    def get_dataset(self, key: str) -> DatasetConfiguration:
        for dataset in self.datasets:
            if dataset.key == key:
                return dataset
        raise ConfigurationError(
            f"Dataset não encontrado em configs/datasets.yaml: {key}"
        )


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


def _require_language(value: Any, location: str) -> str:
    language = _require_string(value, location).lower()

    if language not in SUPPORTED_LANGUAGES:
        supported = ", ".join(sorted(SUPPORTED_LANGUAGES))
        raise ConfigurationError(
            f"{location} precisa ser um idioma suportado: {supported}."
        )

    return language


def _optional_mapping(value: Any, location: str) -> dict[str, Any]:
    if value is None:
        return {}
    return dict(_require_mapping(value, location))


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


def _sanitize_identifier(value: str, location: str) -> str:
    normalized = value.strip()

    if not RUN_ID_PATTERN.fullmatch(normalized):
        raise ConfigurationError(
            f"{location} contém caracteres inválidos: {value!r}. "
            "Use apenas letras, números, ponto, hífen e sublinhado."
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


def _validate_dataset_reader(
    dataset_key: str,
    reader: Mapping[str, Any],
    dataset_format: str,
) -> None:
    if dataset_format in {"parquet", "huggingface"}:
        return

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

        date_format = dates.get("format")
        if date_format is not None:
            _require_string(
                date_format,
                f"datasets.{dataset_key}.dates.format",
            )
    elif dates.get("format") is not None:
        raise ConfigurationError(
            f"datasets.{dataset_key}.dates.format precisa ser null "
            "quando dates.available=false."
        )


def _resolve_datasets(
    *,
    project_root: Path,
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
        language = _require_language(
            merged.get("language"),
            f"datasets.{dataset_key}.language",
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

        raw_path = merged.get("path")
        dataset_path: Path | None
        if raw_path is None:
            if dataset_format == "huggingface":
                dataset_path = None
            else:
                raise ConfigurationError(
                    f"datasets.{dataset_key}.path é obrigatório "
                    f"quando format={dataset_format!r}."
                )
        else:
            dataset_path = _resolve_path(
                project_root,
                _require_string(
                    raw_path,
                    f"datasets.{dataset_key}.path",
                ),
            )

        source = _resolve_optional_source(
            project_root=project_root,
            raw_source=merged.get("source"),
            location=f"datasets.{dataset_key}.source",
            default_local_path=dataset_path,
        )
        if (
            source.get("provider") == "huggingface_hub_file"
            and dataset_path is None
        ):
            dataset_path = Path(source["local_path"])

        text_compose = _resolve_text_compose(
            merged.get("text_compose"),
            f"datasets.{dataset_key}.text_compose",
        )
        limits = _resolve_dataset_limits(
            merged.get("limits", {}),
            f"datasets.{dataset_key}.limits",
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
            if field_name == "text" and text_compose is not None:
                continue
            if not columns.get(field_name):
                raise ConfigurationError(
                    f"datasets.{dataset_key} não possui mapeamento "
                    f"para o campo obrigatório {field_name!r}."
                )

        if "text" in required_fields and not columns.get("text"):
            if text_compose is None:
                raise ConfigurationError(
                    f"datasets.{dataset_key} não possui columns.text "
                    "nem text_compose."
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

        _validate_dataset_labels(
            dataset_key,
            labels,
            columns,
        )
        _validate_dataset_dates(
            dataset_key,
            dates,
            columns,
        )
        _validate_dataset_reader(
            dataset_key,
            reader,
            dataset_format,
        )

        resolved.append(
            DatasetConfiguration(
                key=dataset_key,
                enabled=enabled,
                order=order,
                dataset_name=dataset_name,
                display_name=display_name,
                language=language,
                path=dataset_path,
                format=dataset_format,
                reader=reader,
                columns=columns,
                required_fields=required_fields,
                labels=labels,
                dates=dates,
                validation=validation,
                metadata=metadata,
                source=source,
                text_compose=text_compose,
                limits=limits,
                raw=merged,
            )
        )

    return sorted(
        resolved,
        key=lambda item: (item.order, item.key),
    )


def load_datasets_configuration(
    *,
    project_root: str | Path | None = None,
    config_path: str | Path = "configs/datasets.yaml",
) -> DatasetsConfiguration:
    """Carrega e valida ``configs/datasets.yaml``."""

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
    datasets = tuple(
        _resolve_datasets(
            project_root=root,
            config=raw_config,
        )
    )

    return DatasetsConfiguration(
        schema_version=SUPPORTED_SCHEMA_VERSION,
        defaults=defaults,
        datasets=datasets,
        config_path=resolved_path,
    )


__all__ = [
    "ConfigurationError",
    "DatasetConfiguration",
    "DatasetsConfiguration",
    "load_datasets_configuration",
]
