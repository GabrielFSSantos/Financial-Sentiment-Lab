"""Testes de configuração dos scrapers."""

from __future__ import annotations

from modules.scrapers.config.loader import load_scrapers_configuration


def test_scrapers_yaml_loads(project_root) -> None:
    configuration = load_scrapers_configuration(project_root=project_root)
    enabled = configuration.enabled_sites()
    keys = {site.key for site in enabled}
    assert keys == {"valor", "infomoney", "estadao", "g1_economia"}
    assert configuration.defaults["max_articles_per_site"] == 50
    assert configuration.defaults["default_since"] == "2020-01-01"


def test_scrapers_yaml_has_no_seed_urls(project_root) -> None:
    configuration = load_scrapers_configuration(project_root=project_root)
    for site in configuration.sites:
        assert "seed_urls" not in site.scraping


def test_site_filter(project_root) -> None:
    configuration = load_scrapers_configuration(project_root=project_root)
    filtered = configuration.enabled_sites(site_key="valor")
    assert len(filtered) == 1
    assert filtered[0].key == "valor"
