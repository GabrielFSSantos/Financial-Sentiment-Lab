"""B3 entity matching for article enrichment (config-driven)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml

from modules.common.paths import CONFIGS_DIR

PENDING_COMPANY = "PENDENTE"


@dataclass(frozen=True)
class EntityMatch:
    company: str
    sector: str
    ticker: str


def _builtin_sector_keywords() -> tuple[str, ...]:
    return (
        "saneamento",
        "esgoto",
        "abastecimento",
        "tarifa",
        "concessão",
        "concessao",
        "marco do saneamento",
        "tratamento de esgoto",
        "água e esgoto",
        "agua e esgoto",
    )


def _builtin_entities() -> tuple[EntityMatch, ...]:
    return (
        EntityMatch(
            "Companhia de Saneamento Básico do Estado de Minas Gerais",
            "Saneamento",
            "CSMG3",
        ),
        EntityMatch("Companhia de Saneamento de Minas Gerais", "Saneamento", "CSMG3"),
        EntityMatch("Companhia de Saneamento do Paraná", "Saneamento", "SAPR4"),
        EntityMatch("Sabesp", "Saneamento", "SBSP3"),
        EntityMatch("Copasa", "Saneamento", "CSMG3"),
        EntityMatch("Sanepar", "Saneamento", "SAPR4"),
    )


def _load_entities_config() -> Mapping[str, Any] | None:
    path = CONFIGS_DIR / "entities.yaml"
    if not path.is_file():
        return None
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    return data if isinstance(data, Mapping) else None


def _entities_from_config(raw: Mapping[str, Any]) -> tuple[EntityMatch, ...]:
    items = raw.get("entities", [])
    result: list[EntityMatch] = []
    if isinstance(items, list):
        for entry in items:
            if not isinstance(entry, Mapping):
                continue
            result.append(
                EntityMatch(
                    str(entry.get("company", "")),
                    str(entry.get("sector", "Saneamento")),
                    str(entry.get("ticker", "")),
                )
            )
    return tuple(result) if result else _builtin_entities()


def _sector_keywords_from_config(raw: Mapping[str, Any]) -> tuple[str, ...]:
    items = raw.get("sector_keywords", [])
    if isinstance(items, list) and items:
        return tuple(str(item) for item in items)
    return _builtin_sector_keywords()


def _aliases_from_config(
    raw: Mapping[str, Any],
    entities: tuple[EntityMatch, ...],
) -> tuple[tuple[str, EntityMatch], ...]:
    ticker_aliases: list[tuple[str, EntityMatch]] = []
    tickers = raw.get("ticker_aliases")
    if isinstance(tickers, Mapping):
        for ticker, meta in tickers.items():
            if isinstance(meta, Mapping):
                ticker_aliases.append(
                    (
                        str(ticker),
                        EntityMatch(
                            str(meta.get("company", "")),
                            str(meta.get("sector", "Saneamento")),
                            str(meta.get("ticker", ticker)),
                        ),
                    )
                )
    if ticker_aliases:
        return tuple(ticker_aliases)

    return (
        ("SBSP3", EntityMatch("Sabesp", "Saneamento", "SBSP3")),
        ("CSMG3", EntityMatch("Copasa", "Saneamento", "CSMG3")),
        ("SAPR4", EntityMatch("Sanepar", "Saneamento", "SAPR4")),
        ("SAPR3", EntityMatch("Sanepar", "Saneamento", "SAPR4")),
        ("SAPR11", EntityMatch("Sanepar", "Saneamento", "SAPR4")),
    )


def _name_aliases_from_config(raw: Mapping[str, Any]) -> tuple[tuple[str, EntityMatch], ...]:
    items = raw.get("name_aliases", [])
    result: list[tuple[str, EntityMatch]] = []
    if isinstance(items, list):
        for entry in items:
            if not isinstance(entry, Mapping):
                continue
            result.append(
                (
                    str(entry.get("match", "")),
                    EntityMatch(
                        str(entry.get("company", "")),
                        str(entry.get("sector", "Saneamento")),
                        str(entry.get("ticker", "")),
                    ),
                )
            )
    if result:
        return tuple(result)
    return (
        (
            "Companhia de Saneamento Básico do Estado de São Paulo",
            EntityMatch("Sabesp", "Saneamento", "SBSP3"),
        ),
    )


_CONFIG = _load_entities_config()
SANITATION_ENTITIES = (
    _entities_from_config(_CONFIG) if _CONFIG else _builtin_entities()
)
SECTOR_KEYWORDS = (
    _sector_keywords_from_config(_CONFIG) if _CONFIG else _builtin_sector_keywords()
)
TICKER_ALIASES = (
    _aliases_from_config(_CONFIG, SANITATION_ENTITIES) if _CONFIG else _aliases_from_config({}, SANITATION_ENTITIES)
)
NAME_ALIASES = (
    _name_aliases_from_config(_CONFIG) if _CONFIG else _name_aliases_from_config({})
)

_PATTERNS: tuple[tuple[re.Pattern[str], EntityMatch], ...] = tuple(
    (
        re.compile(rf"\b{re.escape(entity.company)}\b", re.I),
        entity,
    )
    for entity in SANITATION_ENTITIES
) + tuple(
    (
        re.compile(rf"\b{re.escape(ticker)}\b", re.I),
        entity,
    )
    for ticker, entity in TICKER_ALIASES
) + tuple(
    (
        re.compile(rf"\b{re.escape(name)}\b", re.I),
        entity,
    )
    for name, entity in NAME_ALIASES
)


def match_entity(text: str) -> EntityMatch | None:
    for pattern, entity in _PATTERNS:
        if pattern.search(text):
            return entity
    return None


def matches_sector_keywords(text: str) -> bool:
    haystack = str(text or "").lower()
    return any(keyword in haystack for keyword in SECTOR_KEYWORDS)
