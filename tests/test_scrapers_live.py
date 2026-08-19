"""Testes live dos scrapers (rede real)."""

from __future__ import annotations

import pytest

from modules.scrapers.config.loader import load_scrapers_configuration
from modules.scrapers.sites.base import SiteScraper


@pytest.mark.network
def test_infomoney_live_smoke(project_root) -> None:
    configuration = load_scrapers_configuration(project_root=project_root)
    site = next(site for site in configuration.enabled_sites() if site.key == "infomoney")
    scraper = SiteScraper(configuration, site)
    records = scraper.scrape(since="2024-01-01", until="2024-03-31")
    assert isinstance(records, list)
