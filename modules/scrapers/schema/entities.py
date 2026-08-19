"""Entidades B3 de saneamento para enriquecimento de artigos."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class EntityMatch:
    company: str
    sector: str
    ticker: str


SANITATION_ENTITIES: tuple[EntityMatch, ...] = (
    EntityMatch("Sabesp", "Saneamento", "SBSP3"),
    EntityMatch("Companhia de Saneamento de Minas Gerais", "Saneamento", "CSMG3"),
    EntityMatch("Companhia de Saneamento do Paraná", "Saneamento", "SAPR4"),
    EntityMatch("Copasa", "Saneamento", "CSMG3"),
    EntityMatch("Sanepar", "Saneamento", "SAPR4"),
)

_PATTERNS: tuple[tuple[re.Pattern[str], EntityMatch], ...] = tuple(
    (
        re.compile(
            rf"\b{re.escape(entity.company)}\b|\b{re.escape(entity.ticker)}\b",
            re.I,
        ),
        entity,
    )
    for entity in SANITATION_ENTITIES
)


def match_entity(text: str) -> EntityMatch | None:
    for pattern, entity in _PATTERNS:
        if pattern.search(text):
            return entity
    if re.search(r"\bsaneamento\b|\bsabesp\b|\bcopasa\b|\bsanepar\b", text, re.I):
        return EntityMatch("Saneamento", "Saneamento", "SETOR")
    return None
