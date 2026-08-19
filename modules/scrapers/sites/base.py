"""Scraper genérico configurável por YAML."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime
from typing import Any, Mapping

from modules.scrapers.config.loader import ScrapersConfiguration, SiteConfiguration
from modules.scrapers.core.html import extract_paragraphs, extract_title, parse_date, parse_html
from modules.scrapers.core.http import fetch_text, sleep
from modules.scrapers.core.search import SearchHit, discover_links
from modules.scrapers.pipeline.state import is_url_seen
from modules.scrapers.schema.entities import match_entity
from modules.scrapers.schema.csv import normalize_url


class SiteScraper:
    """Busca links, baixa artigos e monta registros do corpus."""

    def __init__(
        self,
        configuration: ScrapersConfiguration,
        site: SiteConfiguration,
    ) -> None:
        self.configuration = configuration
        self.site = site
        self.defaults = configuration.defaults
        self.scraping: Mapping[str, Any] = site.scraping

    def scrape(
        self,
        *,
        since: str,
        until: str,
        state: Mapping[str, Any] | None = None,
    ) -> list[dict[str, str]]:
        max_articles = int(self.defaults.get("max_articles_per_site", 50))
        delay = float(self.defaults.get("delay_seconds", 2.0))
        timeout = float(self.defaults.get("request_timeout", 30.0))
        min_chars = int(self.defaults.get("min_article_chars", 40))

        since_date = datetime.strptime(since, "%Y-%m-%d").date()
        until_date = datetime.strptime(until, "%Y-%m-%d").date()
        queries = tuple(
            self.scraping.get(
                "search_queries",
                ("Sabesp", "Copasa", "Sanepar", "saneamento"),
            )
        )
        strategy = str(self.scraping.get("search_strategy", "html"))

        hits = discover_links(
            strategy=strategy,
            scraping=self.scraping,
            queries=queries,
            timeout=timeout,
            since=since,
            until=until,
        )

        records: list[dict[str, str]] = []
        seen_urls: set[str] = set()
        max_misses = int(self.defaults.get("max_fetch_misses", 25))
        misses = 0
        for hit in hits:
            if len(records) >= max_articles:
                break
            record = self._fetch_article(
                hit,
                since_date=since_date,
                until_date=until_date,
                timeout=timeout,
                delay=delay,
                min_chars=min_chars,
                seen_urls=seen_urls,
                state=state,
            )
            if record is not None:
                records.append(record)
                misses = 0
                continue
            misses += 1
            if misses >= max_misses:
                break
        return records

    def _fetch_article(
        self,
        hit: SearchHit,
        *,
        since_date,
        until_date,
        timeout: float,
        delay: float,
        min_chars: int,
        seen_urls: set[str],
        state: Mapping[str, Any] | None,
    ) -> dict[str, str] | None:
        article_url = hit.url.strip()
        normalized = normalize_url(article_url)
        if not normalized or normalized in seen_urls:
            return None
        if state is not None and is_url_seen(state, normalized):
            return None
        seen_urls.add(normalized)

        body_selector = str(
            self.scraping.get(
                "body_selector",
                "article p, .content-text__container p, .mc-article-body p",
            )
        )
        fonte = str(self.scraping.get("fonte") or self.site.display_name or self.site.key)

        try:
            article_html = fetch_text(article_url, timeout=timeout)
        except Exception:
            return None
        sleep(delay)

        soup = parse_html(article_html)
        title = extract_title(soup) or hit.title
        body = extract_paragraphs(soup, body_selector)
        combined = f"{title} {body}".strip()
        if len(combined) < min_chars:
            return None

        entity = match_entity(combined)
        if entity is None:
            return None

        parsed_date = hit.published or self._extract_date(soup, article_url, until_date)
        if not parsed_date:
            return None

        article_date = datetime.strptime(parsed_date, "%Y-%m-%d").date()
        if article_date < since_date or article_date > until_date:
            return None

        digest = hashlib.sha256(normalized.encode()).hexdigest()[:12]
        return {
            "id": f"{self.site.key}_{digest}",
            "data": parsed_date,
            "empresa": entity.company,
            "setor": entity.sector,
            "ticker": entity.ticker,
            "titulo": title or combined[:120],
            "noticia": body or combined,
            "fonte": fonte,
            "url": article_url,
        }

    def _extract_date(self, soup, article_url: str, until_date) -> str:
        date_node = soup.select_one("time[datetime], meta[property='article:published_time']")
        raw_date = ""
        if date_node is not None:
            raw_date = str(
                date_node.get("datetime")
                or date_node.get("content")
                or date_node.get_text(" ", strip=True)
            )
        parsed_date = parse_date(raw_date)
        if not parsed_date:
            match = re.search(r"/(\d{4}/\d{2}/\d{2})/", article_url)
            if match:
                parsed_date = match.group(1).replace("/", "-")
        if not parsed_date:
            parsed_date = until_date.strftime("%Y-%m-%d")
        return parsed_date
