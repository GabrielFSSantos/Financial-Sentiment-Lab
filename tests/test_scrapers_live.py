"""Testes live dos scrapers (rede real)."""

from __future__ import annotations

import pytest

from modules.scrapers.config.loader import load_scrapers_configuration
from modules.scrapers.core.search import debug_discover_links
from modules.scrapers.sites.base import SiteScraper

ANCHOR_SINCE = "2023-11-01"
ANCHOR_UNTIL = "2023-11-30"

API_SITES = ("infomoney", "money_times", "exame")
PLAYWRIGHT_SITES = ("valor", "g1_economia")


@pytest.mark.network
@pytest.mark.parametrize("site_key", API_SITES)
def test_site_live_smoke_api(project_root, site_key: str) -> None:
    configuration = load_scrapers_configuration(project_root=project_root)
    site = next(site for site in configuration.enabled_sites() if site.key == site_key)
    scraper = SiteScraper(configuration, site)
    records = scraper.scrape(since=ANCHOR_SINCE, until=ANCHOR_UNTIL)
    assert isinstance(records, list)
    assert len(records) >= 1, f"{site_key}: esperado >= 1 registro em nov/2023"


@pytest.mark.network
@pytest.mark.playwright
@pytest.mark.parametrize("site_key", PLAYWRIGHT_SITES)
def test_site_live_smoke_playwright(project_root, site_key: str) -> None:
    pytest.importorskip("playwright")
    configuration = load_scrapers_configuration(project_root=project_root)
    site = next(site for site in configuration.enabled_sites() if site.key == site_key)
    if not site.enabled:
        pytest.skip(f"{site_key} desabilitado na config")
    timeout = float(configuration.defaults.get("request_timeout", 30.0))
    debug_stats = debug_discover_links(
        scraping=site.scraping,
        queries=("Sabesp",),
        timeout=timeout,
        since=ANCHOR_SINCE,
        until=ANCHOR_UNTIL,
    )
    in_window = sum(item.in_window_count for item in debug_stats)
    if in_window == 0:
        pytest.skip(
            f"{site_key}: nenhum link na janela {ANCHOR_SINCE}–{ANCHOR_UNTIL} "
            "(site ou busca indisponível)."
        )
    scraper = SiteScraper(configuration, site)
    records = scraper.scrape(since=ANCHOR_SINCE, until=ANCHOR_UNTIL)
    assert isinstance(records, list)
    assert len(records) >= 1, (
        f"{site_key}: {in_window} links na janela mas 0 coletados"
    )
