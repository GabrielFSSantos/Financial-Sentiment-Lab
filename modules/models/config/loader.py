"""Carregamento e validação de ``configs/models.yaml``."""

from __future__ import annotations

import copy
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Mapping

import yaml

from modules.models import PROJECT_ROOT
from modules.models.sentiment import CANONICAL_SENTIMENT_LABELS


SUPPORTED_SCHEMA_VERSION = "2.0"
SUPPORTED_SOURCE_PROVIDERS = {"huggingface_hub"}
SUPPORTED_DEVICES = {"auto", "cpu", "cuda"}
SUPPORTED_LANGUAGES = {"pt", "en"}
RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")

CANONICAL_LABELS = CANONICAL_SENTIMENT_LABELS


class ConfigurationError(ValueError):
    """Erro de leitura, validação ou resolução das configurações de modelos."""


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
    language: str
    adapter: str
    model_dir: Path
    parameters: dict[str, Any]
    loading: dict[str, Any]
    validation: dict[str, Any]
    required_files: tuple[str, ...]
    labels: dict[str, Any]
    metadata: dict[str, Any]
    source: dict[str, Any]
    raw: dict[str, Any] = field(repr=False)

    def to_dict(self) -> dict[str, Any]:
        from modules.models.common import to_serializable

        return to_serializable(asdict(self))


@dataclass(frozen=True)
class ModelsConfiguration:
    """Configuração completa de ``configs/models.yaml``."""

    schema_version: str
    defaults: dict[str, Any]
    models: tuple[ModelConfiguration, ...]
    config_path: Path

    @property
    def enabled_models(self) -> tuple[ModelConfiguration, ...]:
        return tuple(model for model in self.models if model.enabled)

    def get_model(self, key: str) -> ModelConfiguration:
        for model in self.models:
            if model.key == key:
                return model
        raise ConfigurationError(
            f"Modelo não encontrado em configs/models.yaml: {key}"
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

    return source


def _validate_model_labels(
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


def _resolve_models(
    *,
    project_root: Path,
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
        language = _require_language(
            merged.get("language"),
            f"models.{model_key}.language",
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
            project_root,
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
        _validate_model_labels(model_key, labels)

        metadata = _require_mapping(
            merged.get("metadata", {}),
            f"models.{model_key}.metadata",
        )
        source = _resolve_optional_source(
            project_root=project_root,
            raw_source=merged.get("source"),
            location=f"models.{model_key}.source",
            default_local_dir=model_dir,
        )

        resolved.append(
            ModelConfiguration(
                key=model_key,
                enabled=enabled,
                order=order,
                model_name=model_name,
                display_name=display_name,
                language=language,
                adapter=adapter,
                model_dir=model_dir,
                parameters=parameters,
                loading=loading,
                validation=validation,
                required_files=required_files,
                labels=labels,
                metadata=metadata,
                source=source,
                raw=merged,
            )
        )

    return sorted(
        resolved,
        key=lambda item: (item.order, item.key),
    )


def load_models_configuration(
    *,
    project_root: str | Path | None = None,
    config_path: str | Path = "configs/models.yaml",
) -> ModelsConfiguration:
    """Carrega e valida ``configs/models.yaml``."""

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
    models = tuple(
        _resolve_models(
            project_root=root,
            config=raw_config,
        )
    )

    return ModelsConfiguration(
        schema_version=SUPPORTED_SCHEMA_VERSION,
        defaults=defaults,
        models=models,
        config_path=resolved_path,
    )


__all__ = [
    "ConfigurationError",
    "ModelConfiguration",
    "ModelsConfiguration",
    "load_models_configuration",
]
