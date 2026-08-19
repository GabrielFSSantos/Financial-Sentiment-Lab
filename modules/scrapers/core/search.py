"""Estratégias de busca por portal (API-first)."""

from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from email.utils import parsedate_to_datetime
from typing import Any, Iterable, Mapping
from urllib.parse import quote_plus, urljoin
from xml.etree import ElementTree as ET

from modules.scrapers.core.html import extract_links, parse_html
from modules.scrapers.core.http import fetch_text


@dataclass(frozen=True)
class SearchHit:
    url: str
    title: str = ""
    published: str = ""


def discover_links(
    *,
    strategy: str,
    scraping: Mapping[str, Any],
    queries: Iterable[str],
    timeout: float,
    since: str = "",
    until: str = "",
) -> list[SearchHit]:
    normalized = str(strategy or "html").strip().lower()
    scraping_with_dates = dict(scraping)
    if since:
        scraping_with_dates.setdefault("api_after", f"{since}T00:00:00")
        scraping_with_dates.setdefault("rss_since", since)
    if until:
        scraping_with_dates.setdefault("api_before", f"{until}T23:59:59")
        scraping_with_dates.setdefault("rss_until", until)

    if normalized == "wordpress_api":
        return _wordpress_api(scraping=scraping_with_dates, queries=queries, timeout=timeout)
    if normalized == "rss":
        return _rss_feed(scraping=scraping_with_dates, queries=queries, timeout=timeout)
    if normalized == "playwright":
        return _playwright_search(scraping=scraping_with_dates, queries=queries, timeout=timeout)
    return _html_search(scraping=scraping_with_dates, queries=queries, timeout=timeout)


def _wordpress_api(
    *,
    scraping: Mapping[str, Any],
    queries: Iterable[str],
    timeout: float,
) -> list[SearchHit]:
    api_url = str(
        scraping.get(
            "api_url",
            "https://www.infomoney.com.br/wp-json/wp/v2/posts",
        )
    )
    per_page = int(scraping.get("api_per_page", 20))
    hits: list[SearchHit] = []
    seen: set[str] = set()

    for query in queries:
        page = 1
        while page <= int(scraping.get("api_max_pages", 3)):
            params = [
                f"search={quote_plus(str(query))}",
                f"per_page={per_page}",
                f"page={page}",
            ]
            after = str(scraping.get("api_after", "")).strip()
            before = str(scraping.get("api_before", "")).strip()
            if after:
                params.append(f"after={quote_plus(after)}")
            if before:
                params.append(f"before={quote_plus(before)}")
            url = f"{api_url}?{'&'.join(params)}"
            try:
                payload = fetch_text(url, timeout=timeout, headers={"Accept": "application/json"})
            except Exception:
                break
            records = json.loads(payload)
            if not isinstance(records, list) or not records:
                break

            for record in records:
                if not isinstance(record, Mapping):
                    continue
                link = str(record.get("link", "")).strip()
                if not link or link in seen:
                    continue
                seen.add(link)
                title_payload = record.get("title")
                title = ""
                if isinstance(title_payload, Mapping):
                    title = _strip_html(str(title_payload.get("rendered", "")))
                published = str(record.get("date", ""))[:10]
                hits.append(SearchHit(url=link, title=title, published=published))

            page += 1
    return hits


def _rss_feed(
    *,
    scraping: Mapping[str, Any],
    queries: Iterable[str],
    timeout: float,
) -> list[SearchHit]:
    feed_url = str(scraping.get("rss_url", "")).strip()
    if not feed_url:
        return []

    xml_payload = fetch_text(feed_url, timeout=timeout)
    root = ET.fromstring(xml_payload.encode("utf-8"))
    channel = root.find("channel")
    if channel is None:
        channel = root

    query_terms = tuple(str(item).strip().lower() for item in queries if str(item).strip())
    article_pattern = scraping.get("article_url_pattern")
    pattern = re.compile(str(article_pattern)) if article_pattern else None
    exclude = tuple(str(item) for item in scraping.get("link_exclude_substrings") or ())
    since_date = _parse_iso_date(str(scraping.get("rss_since", "")))
    until_date = _parse_iso_date(str(scraping.get("rss_until", "")))

    hits: list[SearchHit] = []
    seen: set[str] = set()
    for item in channel.findall("item"):
        link = (item.findtext("link") or "").strip()
        if not link or link in seen:
            continue
        if any(token in link for token in exclude):
            continue
        if pattern is not None and not pattern.search(link):
            continue

        title = _strip_html(item.findtext("title") or "")
        description = _strip_html(item.findtext("description") or "")
        content = _strip_html(item.findtext("{http://purl.org/rss/1.0/modules/content/}encoded") or "")
        haystack = f"{title} {description} {content}".lower()
        if query_terms and not any(term in haystack for term in query_terms):
            continue

        published = _parse_rss_date(item.findtext("pubDate") or "")
        if since_date and published:
            item_date = _parse_iso_date(published)
            if item_date is not None and item_date < since_date:
                break
        if until_date and published:
            item_date = _parse_iso_date(published)
            if item_date is not None and item_date > until_date:
                continue
        seen.add(link)
        hits.append(SearchHit(url=link, title=title, published=published))
    return hits


def _html_search(
    *,
    scraping: Mapping[str, Any],
    queries: Iterable[str],
    timeout: float,
) -> list[SearchHit]:
    search_url_template = str(scraping.get("search_url", "")).strip()
    if not search_url_template:
        return []

    base_url = str(scraping.get("base_url", "")).strip()
    link_selector = str(scraping.get("link_selector", "a[href]"))
    exclude = tuple(str(item) for item in scraping.get("link_exclude_substrings") or ())
    article_pattern = scraping.get("article_url_pattern")
    pattern = re.compile(str(article_pattern)) if article_pattern else None

    hits: list[SearchHit] = []
    seen: set[str] = set()
    for query in queries:
        search_url = search_url_template.format(query=quote_plus(str(query)))
        search_html = fetch_text(search_url, timeout=timeout)
        soup = parse_html(search_html)
        for link in extract_links(
            soup,
            base_url=base_url,
            selector=link_selector,
            exclude_substrings=exclude,
        ):
            if link in seen:
                continue
            if pattern is not None and not pattern.search(link):
                continue
            seen.add(link)
            hits.append(SearchHit(url=link))
    return hits


def _playwright_search(
    *,
    scraping: Mapping[str, Any],
    queries: Iterable[str],
    timeout: float,
) -> list[SearchHit]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            "Playwright não instalado. Instale com: pip install playwright && playwright install chromium"
        ) from exc

    search_url_template = str(scraping.get("search_url", "")).strip()
    if not search_url_template:
        return []

    link_selector = str(scraping.get("link_selector", "a[href]"))
    base_url = str(scraping.get("base_url", "")).strip()
    exclude = tuple(str(item) for item in scraping.get("link_exclude_substrings") or ())
    article_pattern = scraping.get("article_url_pattern")
    pattern = re.compile(str(article_pattern)) if article_pattern else None
    wait_ms = int(scraping.get("playwright_wait_ms", 3000))

    hits: list[SearchHit] = []
    seen: set[str] = set()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_default_timeout(int(timeout * 1000))
        for query in queries:
            search_url = search_url_template.format(query=quote_plus(str(query)))
            page.goto(search_url, wait_until="domcontentloaded")
            page.wait_for_timeout(wait_ms)
            anchors = page.query_selector_all(link_selector)
            for anchor in anchors:
                href = anchor.get_attribute("href")
                if not href:
                    continue
                link = urljoin(base_url, href.strip())
                if any(token in link for token in exclude):
                    continue
                if pattern is not None and not pattern.search(link):
                    continue
                if link in seen:
                    continue
                seen.add(link)
                title = (anchor.inner_text() or "").strip()
                hits.append(SearchHit(url=link, title=title))
        browser.close()
    return hits


def _parse_rss_date(value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    try:
        return parsedate_to_datetime(raw).strftime("%Y-%m-%d")
    except (TypeError, ValueError, OverflowError):
        match = re.search(r"(\d{4}-\d{2}-\d{2})", raw)
        if match:
            return match.group(1)
    return ""


def _strip_html(value: str) -> str:
    unescaped = html.unescape(str(value or ""))
    without_tags = re.sub(r"<[^>]+>", " ", unescaped)
    return re.sub(r"\s+", " ", without_tags).strip()


def _parse_iso_date(value: str) -> date | None:
    raw = str(value or "").strip()[:10]
    if not raw:
        return None
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError:
        return None
