"""Entidades B3 de saneamento para enriquecimento de artigos."""

from __future__ import annotations

import re
from dataclasses import dataclass

PENDING_COMPANY = "PENDENTE"

SECTOR_KEYWORDS: tuple[str, ...] = (
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


@dataclass(frozen=True)
class EntityMatch:
    company: str
    sector: str
    ticker: str


SANITATION_ENTITIES: tuple[EntityMatch, ...] = (
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

TICKER_ALIASES: tuple[tuple[str, EntityMatch], ...] = (
    ("SBSP3", EntityMatch("Sabesp", "Saneamento", "SBSP3")),
    ("CSMG3", EntityMatch("Copasa", "Saneamento", "CSMG3")),
    ("SAPR4", EntityMatch("Sanepar", "Saneamento", "SAPR4")),
    ("SAPR3", EntityMatch("Sanepar", "Saneamento", "SAPR4")),
    ("SAPR11", EntityMatch("Sanepar", "Saneamento", "SAPR4")),
)

NAME_ALIASES: tuple[tuple[str, EntityMatch], ...] = (
    (
        "Companhia de Saneamento Básico do Estado de São Paulo",
        EntityMatch("Sabesp", "Saneamento", "SBSP3"),
    ),
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
