"""Testes das estratégias de busca (mock, sem rede)."""

from __future__ import annotations

from datetime import date
from unittest.mock import patch

import requests

from modules.scrapers.core.search import (
    _date_from_article_url,
    _link_in_date_window,
    _resolve_search_result_url,
    discover_links,
)


SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <item>
      <title>Sabesp anuncia investimentos</title>
      <link>https://valor.globo.com/empresas/noticia/2024/03/01/sabesp-investimentos.ghtml</link>
      <pubDate>Fri, 01 Mar 2024 12:00:00 +0000</pubDate>
      <description>Companhia de saneamento</description>
    </item>
    <item>
      <title>Mercado financeiro fecha em alta</title>
      <link>https://valor.globo.com/financas/noticia/2024/03/01/mercado-fecha-alta.ghtml</link>
      <pubDate>Fri, 01 Mar 2024 12:00:00 +0000</pubDate>
      <description>Sem relação com saneamento</description>
    </item>
  </channel>
</rss>
"""

SAMPLE_WP_JSON = """[
  {
    "link": "https://www.infomoney.com.br/mercados/sabesp-resultado/",
    "date": "2024-02-10T10:00:00",
    "title": {"rendered": "Sabesp divulga resultado"}
  }
]"""

SAMPLE_HTML = """
<html><body>
  <a href="/empresas/noticia/2024/02/01/copasa-plano.ghtml">Copasa plano</a>
  <a href="/busca/?q=x">Busca</a>
</body></html>
"""


def test_rss_search_filters_by_keyword() -> None:
    scraping = {
        "rss_url": "https://example.com/rss.xml",
        "article_url_pattern": "valor\\.globo\\.com/.+/noticia/",
        "search_queries": ["Sabesp", "saneamento"],
    }
    with patch("modules.scrapers.core.search.fetch_text", return_value=SAMPLE_RSS):
        hits = discover_links(strategy="rss", scraping=scraping, queries=("Sabesp",), timeout=5)
    assert len(hits) == 1
    assert "sabesp-investimentos" in hits[0].url


def test_wordpress_api_search() -> None:
    scraping = {
        "api_url": "https://www.infomoney.com.br/wp-json/wp/v2/posts",
    }
    with patch("modules.scrapers.core.search.fetch_text", return_value=SAMPLE_WP_JSON):
        hits = discover_links(
            strategy="wordpress_api",
            scraping=scraping,
            queries=("Sabesp",),
            timeout=5,
        )
    assert len(hits) == 1
    assert hits[0].published == "2024-02-10"


def test_html_search_respects_exclude() -> None:
    scraping = {
        "search_url": "https://valor.globo.com/busca/?q={query}",
        "base_url": "https://valor.globo.com",
        "link_selector": "a[href]",
        "link_exclude_substrings": ["/busca/"],
        "article_url_pattern": "valor\\.globo\\.com/.+/noticia/",
    }
    with patch("modules.scrapers.core.search.fetch_text", return_value=SAMPLE_HTML):
        hits = discover_links(strategy="html", scraping=scraping, queries=("Copasa",), timeout=5)
    assert len(hits) == 1
    assert hits[0].url.endswith("copasa-plano.ghtml")


def test_html_search_ignores_http_errors() -> None:
    scraping = {
        "search_url": "https://www.estadao.com.br/buscador/?q={query}",
        "base_url": "https://www.estadao.com.br",
        "link_selector": "a[href]",
    }
    with patch(
        "modules.scrapers.core.search.fetch_text",
        side_effect=requests.exceptions.HTTPError("404 Client Error"),
    ):
        hits = discover_links(strategy="html", scraping=scraping, queries=("Sabesp",), timeout=5)
    assert hits == []


def test_rss_search_ignores_http_errors() -> None:
    scraping = {
        "rss_url": "https://einvestidor.estadao.com.br/feed",
    }
    with patch(
        "modules.scrapers.core.search.fetch_text",
        side_effect=requests.exceptions.HTTPError("404 Client Error"),
    ):
        hits = discover_links(strategy="rss", scraping=scraping, queries=("Sabesp",), timeout=5)
    assert hits == []


def test_date_from_article_url() -> None:
    url = "https://valor.globo.com/empresas/noticia/2023/11/29/sabesp.ghtml"
    assert _date_from_article_url(url) == date(2023, 11, 29)


def test_link_in_date_window_filters_by_url_date() -> None:
    link = "https://g1.globo.com/economia/noticia/2024/01/15/teste.ghtml"
    since = date(2023, 11, 1)
    until = date(2023, 11, 30)
    assert not _link_in_date_window(link, since_date=since, until_date=until)

    in_window = "https://g1.globo.com/economia/noticia/2023/11/15/teste.ghtml"
    assert _link_in_date_window(in_window, since_date=since, until_date=until)


def test_resolve_globo_measures_redirect() -> None:
    href = (
        "https://measures.globo.com/v1/click?u="
        "https%3A%2F%2Fvalor.globo.com%2Fempresas%2Fnoticia%2F2023%2F11%2F29%2Fsabesp.ghtml"
    )
    resolved = _resolve_search_result_url(href)
    assert resolved == "https://valor.globo.com/empresas/noticia/2023/11/29/sabesp.ghtml"


def test_link_without_url_date_passes_window_filter() -> None:
    link = "https://einvestidor.estadao.com.br/investimentos/sabesp/"
    since = date(2023, 11, 1)
    until = date(2023, 11, 30)
    assert _link_in_date_window(link, since_date=since, until_date=until)
