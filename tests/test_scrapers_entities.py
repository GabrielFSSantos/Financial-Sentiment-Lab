"""Testes de entidades e tickers do scraper."""

from __future__ import annotations

from modules.scrapers.schema.entities import (
    PENDING_COMPANY,
    match_entity,
    matches_sector_keywords,
)


def test_match_entity_sabesp_ticker() -> None:
    entity = match_entity("Ação SBSP3 subiu após resultado da Sabesp.")
    assert entity is not None
    assert entity.company == "Sabesp"
    assert entity.ticker == "SBSP3"


def test_match_entity_sanepar_sapr3_maps_to_sapr4() -> None:
    entity = match_entity("Sanepar (SAPR3) divulga resultados.")
    assert entity is not None
    assert entity.company == "Sanepar"
    assert entity.ticker == "SAPR4"


def test_match_entity_sanepar_sapr11() -> None:
    entity = match_entity("Unit SAPR11 reage a tarifas da Sanepar.")
    assert entity is not None
    assert entity.ticker == "SAPR4"


def test_match_entity_copasa() -> None:
    entity = match_entity("Copasa anuncia investimentos em Minas.")
    assert entity is not None
    assert entity.company == "Copasa"
    assert entity.ticker == "CSMG3"


def test_matches_sector_keywords_without_company() -> None:
    assert matches_sector_keywords("Novo marco do saneamento avança no Congresso.")
    assert not matches_sector_keywords("Ibovespa fecha em alta.")


def test_pending_company_constant() -> None:
    assert PENDING_COMPANY == "PENDENTE"
