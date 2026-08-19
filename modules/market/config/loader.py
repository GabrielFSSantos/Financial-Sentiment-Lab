"""Carregamento e validação de ``configs/market.yaml``."""

from __future__ import annotations

import copy
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Mapping

import yaml

from modules.market import PROJECT_ROOT
from modules.market.common import to_serializable


SUPPORTED_SCHEMA_VERSION = "2.0"
SUPPORTED_PROVIDERS = {"local", "yfinance"}
SUPPORTED_RETURN_TYPES = {"simple_return", "log_return"}


class ConfigurationError(ValueError):
    """Erro de leitura, validação ou resolução das configurações de mercado."""


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
class MarketSourceConfiguration:
    """Fonte externa opcional para materializar preços locais."""

    provider: str
    tickers: tuple[str, ...]
    start: str | None
    end: str | None
    raw: dict[str, Any] = field(repr=False)

    def to_dict(self) -> dict[str, Any]:
        return to_serializable(asdict(self))


@dataclass(frozen=True)
class MarketConfiguration:
    """Configuração resolvida de ``configs/market.yaml``."""

    schema_version: str
    enabled: bool
    local_path: Path
    format: str
    reader: dict[str, Any]
    columns: dict[str, str]
    returns: dict[str, Any]
    source: MarketSourceConfiguration | None
    defaults: dict[str, Any]
    raw: dict[str, Any] = field(repr=False)
    config_path: Path = field(repr=False)

    @property
    def return_columns(self) -> tuple[str, ...]:
        compute = self.returns.get("compute", [])
        if not isinstance(compute, list):
            return ("simple_return", "log_return")
        return tuple(
            item
            for item in compute
            if isinstance(item, str) and item in SUPPORTED_RETURN_TYPES
        )

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


def _resolve_source(
    *,
    raw_source: Any,
    location: str,
) -> MarketSourceConfiguration | None:
    if raw_source is None:
        return None

    source = _require_mapping(raw_source, location)
    provider = _require_string(
        source.get("provider"),
        f"{location}.provider",
    ).lower()

    if provider not in SUPPORTED_PROVIDERS:
        supported = ", ".join(sorted(SUPPORTED_PROVIDERS))
        raise ConfigurationError(
            f"{location}.provider precisa ser um dos valores: {supported}."
        )

    tickers_raw = _require_list(
        source.get("tickers", []),
        f"{location}.tickers",
    )
    if not tickers_raw:
        raise ConfigurationError(
            f"{location}.tickers não pode ficar vazio quando source está definido."
        )

    tickers = tuple(
        _require_string(item, f"{location}.tickers")
        for item in tickers_raw
    )

    start = source.get("start")
    end = source.get("end")
    start_value = (
        _require_string(start, f"{location}.start")
        if start is not None
        else None
    )
    end_value = (
        _require_string(end, f"{location}.end")
        if end is not None
        else None
    )

    return MarketSourceConfiguration(
        provider=provider,
        tickers=tickers,
        start=start_value,
        end=end_value,
        raw=source,
    )


def _resolve_returns(raw_returns: Any, location: str) -> dict[str, Any]:
    returns = _require_mapping(raw_returns, location)
    compute_raw = returns.get("compute", ["simple_return", "log_return"])
    compute_list = _require_list(compute_raw, f"{location}.compute")

    if not compute_list:
        raise ConfigurationError(f"{location}.compute não pode ficar vazio.")

    compute = []
    for item in compute_list:
        normalized = _require_string(item, f"{location}.compute").lower()
        if normalized not in SUPPORTED_RETURN_TYPES:
            supported = ", ".join(sorted(SUPPORTED_RETURN_TYPES))
            raise ConfigurationError(
                f"{location}.compute contém valor inválido {item!r}; "
                f"use: {supported}."
            )
        compute.append(normalized)

    return {"compute": compute}


def load_market_configuration(
    *,
    project_root: str | Path | None = None,
    config_path: str | Path = "configs/market.yaml",
) -> MarketConfiguration:
    """Carrega e valida ``configs/market.yaml``."""

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
    market_raw = _require_mapping(
        raw_config.get("market"),
        "market",
    )
    merged = _deep_merge(defaults, market_raw)

    enabled = _require_boolean(
        merged.get("enabled", True),
        "market.enabled",
    )
    local_path = _resolve_path(
        root,
        _require_string(
            merged.get("local_path"),
            "market.local_path",
        ),
    )
    market_format = _require_string(
        merged.get("format", "csv"),
        "market.format",
    ).lower()

    if market_format != "csv":
        raise ConfigurationError(
            f"market.format={market_format!r} não é suportado; use csv."
        )

    reader = _require_mapping(
        merged.get("reader"),
        "market.reader",
    )
    columns_raw = _require_mapping(
        merged.get("columns"),
        "market.columns",
    )
    columns = {
        _require_string(key, "market.columns.<chave>"): _require_string(
            value,
            f"market.columns.{key}",
        )
        for key, value in columns_raw.items()
    }

    for required in ("date", "ticker", "close"):
        if required not in columns:
            raise ConfigurationError(
                f"market.columns precisa mapear a coluna interna {required!r}."
            )

    returns = _resolve_returns(
        merged.get("returns", defaults.get("returns", {})),
        "market.returns",
    )
    source = _resolve_source(
        raw_source=merged.get("source"),
        location="market.source",
    )

    return MarketConfiguration(
        schema_version=SUPPORTED_SCHEMA_VERSION,
        enabled=enabled,
        local_path=local_path,
        format=market_format,
        reader=reader,
        columns=columns,
        returns=returns,
        source=source,
        defaults=defaults,
        raw=merged,
        config_path=resolved_path,
    )


__all__ = [
    "ConfigurationError",
    "MarketConfiguration",
    "MarketSourceConfiguration",
    "load_market_configuration",
]
