"""Testes de append raw e parser de artigo."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from modules.scrapers.core.search import SearchHit
from modules.scrapers.config.loader import load_scrapers_configuration
from modules.scrapers.schema.csv import append_records
from modules.scrapers.sites.base import SiteScraper


def test_append_records_dedupes_existing(tmp_path: Path) -> None:
    target = tmp_path / "valor.csv"
    first_total, first_added = append_records(
        target,
        [{"id": "a", "url": "https://valor.globo.com/foo/", "titulo": "Sabesp"}],
    )
    second_total, second_added = append_records(
        target,
        [{"id": "b", "url": "https://valor.globo.com/foo?utm=1", "titulo": "Sabesp"}],
    )
    assert first_total == 1 and first_added == 1
    assert second_total == 1 and second_added == 0


def test_site_scraper_parses_fixture_article(project_root) -> None:
    configuration = load_scrapers_configuration(project_root=project_root)
    site = next(site for site in configuration.sites if site.key == "valor")
    scraper = SiteScraper(configuration, site)
    fixture = (project_root / "tests/fixtures/valor_article.html").read_text(encoding="utf-8")

    with patch("modules.scrapers.sites.base.fetch_text", return_value=fixture):
        record = scraper._fetch_article(
            SearchHit(
                url="https://valor.globo.com/empresas/noticia/2024/03/01/sabesp.ghtml",
                published="2024-03-01",
            ),
            since_date=__import__("datetime").date(2024, 1, 1),
            until_date=__import__("datetime").date(2024, 12, 31),
            timeout=5,
            delay=0,
            min_chars=40,
            seen_urls=set(),
            state=None,
        )

    assert record is not None
    assert record["empresa"] == "Sabesp"
    assert record["data"] == "2024-03-01"
    assert "saneamento" in record["noticia"].lower()
