"""Estratégias de busca por portal (API-first)."""

from __future__ import annotations

import html
import json
import logging
import re
from dataclasses import dataclass
from datetime import date, datetime
from email.utils import parsedate_to_datetime
from typing import Any, Iterable, Mapping
from urllib.parse import parse_qs, quote_plus, unquote, urljoin, urlparse, urlunparse, parse_qsl, urlencode
from xml.etree import ElementTree as ET

from modules.scrapers.core.html import extract_links, parse_html
from modules.scrapers.core.http import fetch_text

logger = logging.getLogger(__name__)

_ARTICLE_DATE_IN_URL = re.compile(r"/(\d{4})/(\d{2})/(\d{2})/")


@dataclass(frozen=True)
class SearchHit:
    url: str
    title: str = ""
    published: str = ""


@dataclass(frozen=True)
class QueryDebugStats:
    query: str
    raw_count: int
    filtered_count: int
    in_window_count: int
    samples: tuple[tuple[str, str], ...]


def discover_links(
    *,
    strategy: str,
    queries: Iterable[str],
    scraping: Mapping[str, Any],
    timeout: float,
    since: str = "",
    until: str = "",
) -> list[SearchHit]:
    normalized = str(strategy or "html").strip().lower()
    scraping_with_dates = dict(scraping)
    if since:
        scraping_with_dates.setdefault("api_after", f"{since}T00:00:00")
        scraping_with_dates.setdefault("rss_since", since)
        scraping_with_dates.setdefault("playwright_since", since)
    if until:
        scraping_with_dates.setdefault("api_before", f"{until}T23:59:59")
        scraping_with_dates.setdefault("rss_until", until)
        scraping_with_dates.setdefault("playwright_until", until)

    if normalized == "wordpress_api":
        return _wordpress_api(scraping=scraping_with_dates, queries=queries, timeout=timeout)
    if normalized == "rss":
        return _rss_feed(scraping=scraping_with_dates, queries=queries, timeout=timeout)
    if normalized == "playwright":
        return _playwright_search(scraping=scraping_with_dates, queries=queries, timeout=timeout)
    return _html_search(scraping=scraping_with_dates, queries=queries, timeout=timeout)


def debug_discover_links(
    *,
    scraping: Mapping[str, Any],
    queries: Iterable[str],
    timeout: float,
    since: str = "",
    until: str = "",
) -> list[QueryDebugStats]:
    """Diagnóstico Playwright: links brutos, filtrados e dentro da janela."""
    scraping_with_dates = dict(scraping)
    if since:
        scraping_with_dates["playwright_since"] = since
    if until:
        scraping_with_dates["playwright_until"] = until

    stats: list[QueryDebugStats] = []
    for query in queries:
        link_sets = _playwright_collect_query(
            scraping=scraping_with_dates,
            query=str(query),
            timeout=timeout,
        )
        samples: list[tuple[str, str]] = []
        for link in link_sets.in_window[:5]:
            item_date = _date_from_article_url(link)
            samples.append((link, item_date.isoformat() if item_date else "?"))
        stats.append(
            QueryDebugStats(
                query=str(query),
                raw_count=len(link_sets.raw),
                filtered_count=len(link_sets.filtered),
                in_window_count=len(link_sets.in_window),
                samples=tuple(samples),
            )
        )
    return stats


def _resolve_search_result_url(href: str) -> str:
    """Resolve redirects da busca Globo (measures.globo.com) para URL do artigo."""
    raw = str(href or "").strip()
    if not raw:
        return ""
    if "measures.globo.com" in raw:
        parsed = urlparse(raw)
        target = parse_qs(parsed.query).get("u", [""])[0]
        if target:
            return unquote(target)
    return raw


def _date_from_article_url(url: str) -> date | None:
    match = _ARTICLE_DATE_IN_URL.search(str(url or ""))
    if not match:
        return None
    try:
        return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    except ValueError:
        return None


def _link_in_date_window(
    link: str,
    *,
    since_date: date | None,
    until_date: date | None,
) -> bool:
    item_date = _date_from_article_url(link)
    if item_date is None:
        return True
    if since_date is not None and item_date < since_date:
        return False
    if until_date is not None and item_date > until_date:
        return False
    return True


def _build_paginated_search_url(template: str, query: str, page: int) -> str:
    base = template.format(query=quote_plus(str(query)))
    if page <= 1:
        return base
    parsed = urlparse(base)
    params = parse_qsl(parsed.query, keep_blank_values=True)
    params.append(("page", str(page)))
    return urlunparse(parsed._replace(query=urlencode(params)))


def _apply_globo_date_filter(page, since_date: date | None, until_date: date | None) -> None:
    """Aplica 'Período personalizado' na busca Globo (Valor/G1)."""
    if since_date is None or until_date is None:
        return
    try:
        page.get_by_text("FILTRAR POR DATA", exact=False).first.click(timeout=5000)
        page.wait_for_timeout(500)
        page.get_by_text("Período personalizado", exact=False).first.click(timeout=5000)
        page.wait_for_timeout(500)
        inputs = page.locator("input[placeholder='dd/mm/aaaa']")
        inputs.nth(0).fill(since_date.strftime("%d/%m/%Y"))
        inputs.nth(1).fill(until_date.strftime("%d/%m/%Y"))
        page.locator("button:has-text('Aplicar')").first.click(timeout=5000)
        page.wait_for_timeout(3000)
    except Exception as exc:
        logger.warning("Falha ao aplicar filtro de data Globo: %s", exc)


def _playwright_scroll(page, steps: int) -> None:
    for _ in range(max(0, steps)):
        page.evaluate("window.scrollBy(0, Math.max(window.innerHeight, 600))")
        page.wait_for_timeout(500)


@dataclass
class _PlaywrightLinkSets:
    raw: list[str]
    filtered: list[str]
    in_window: list[str]
    hits: list[SearchHit]


def _playwright_collect_query(
    *,
    scraping: Mapping[str, Any],
    query: str,
    timeout: float,
    page=None,
    browser=None,
) -> _PlaywrightLinkSets:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            "Playwright não instalado. Instale com: "
            "pip install -r requirements-scrapers.txt && playwright install chromium"
        ) from exc

    search_url_template = str(scraping.get("search_url", "")).strip()
    if not search_url_template:
        return _PlaywrightLinkSets([], [], [], [])

    link_selector = str(scraping.get("link_selector", "a[href]"))
    base_url = str(scraping.get("base_url", "")).strip()
    exclude = tuple(str(item) for item in scraping.get("link_exclude_substrings") or ())
    article_pattern = scraping.get("article_url_pattern")
    pattern = re.compile(str(article_pattern)) if article_pattern else None
    wait_ms = int(scraping.get("playwright_wait_ms", 3000))
    scroll_steps = int(scraping.get("playwright_scroll_steps", 3))
    max_pages = int(scraping.get("playwright_max_pages", 3))
    wait_until = str(scraping.get("playwright_wait_until", "domcontentloaded")).strip()
    since_date = _parse_iso_date(str(scraping.get("playwright_since", "")))
    until_date = _parse_iso_date(str(scraping.get("playwright_until", "")))
    wait_selector = link_selector.split(",")[0].strip()

    raw: list[str] = []
    filtered: list[str] = []
    in_window: list[str] = []
    hits: list[SearchHit] = []
    seen: set[str] = set()

    def collect_from_page(active_page) -> int:
        added = 0
        anchors = active_page.query_selector_all(link_selector)
        for anchor in anchors:
            href = anchor.get_attribute("href")
            if not href:
                continue
            resolved = _resolve_search_result_url(href.strip())
            if not resolved:
                continue
            link = resolved if resolved.startswith("http") else urljoin(base_url, resolved)
            if link in seen:
                continue
            seen.add(link)
            raw.append(link)
            if any(token in link for token in exclude):
                continue
            if pattern is not None and not pattern.search(link):
                continue
            filtered.append(link)
            if not _link_in_date_window(link, since_date=since_date, until_date=until_date):
                continue
            in_window.append(link)
            item_date = _date_from_article_url(link)
            published = item_date.isoformat() if item_date else ""
            title = (anchor.inner_text() or "").strip()
            hits.append(SearchHit(url=link, title=title, published=published))
            added += 1
        return added

    def run_on_page(active_page) -> None:
        for page_num in range(1, max_pages + 1):
            search_url = _build_paginated_search_url(search_url_template, query, page_num)
            try:
                try:
                    active_page.goto(
                        search_url,
                        wait_until=wait_until,
                        timeout=int(timeout * 1000),
                    )
                except Exception:
                    active_page.goto(
                        search_url,
                        wait_until="domcontentloaded",
                        timeout=int(timeout * 1000),
                    )
                if page_num == 1 and "globo.com" in search_url:
                    _apply_globo_date_filter(active_page, since_date, until_date)
                try:
                    active_page.wait_for_selector(wait_selector, timeout=wait_ms)
                except Exception:
                    active_page.wait_for_timeout(wait_ms)
                _playwright_scroll(active_page, scroll_steps)
                added = collect_from_page(active_page)
            except Exception as exc:
                logger.warning("Falha na busca Playwright %s: %s", search_url, exc)
                break
            if page_num > 1 and added == 0:
                break

    if page is not None:
        run_on_page(page)
        return _PlaywrightLinkSets(raw, filtered, in_window, hits)

    with sync_playwright() as playwright:
        owns_browser = browser is None
        if owns_browser:
            browser = playwright.chromium.launch(headless=True)
        try:
            active_page = page or browser.new_page()
            active_page.set_default_timeout(int(timeout * 1000))
            run_on_page(active_page)
        finally:
            if owns_browser and browser is not None:
                browser.close()
    return _PlaywrightLinkSets(raw, filtered, in_window, hits)


def _playwright_search(
    *,
    scraping: Mapping[str, Any],
    queries: Iterable[str],
    timeout: float,
) -> list[SearchHit]:
    hits: list[SearchHit] = []
    seen: set[str] = set()
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            "Playwright não instalado. Instale com: "
            "pip install -r requirements-scrapers.txt && playwright install chromium"
        ) from exc

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.set_default_timeout(int(timeout * 1000))
            for query in queries:
                link_sets = _playwright_collect_query(
                    scraping=scraping,
                    query=str(query),
                    timeout=timeout,
                    page=page,
                    browser=browser,
                )
                for hit in link_sets.hits:
                    if hit.url in seen:
                        continue
                    seen.add(hit.url)
                    hits.append(hit)
        finally:
            browser.close()
    return hits


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

    try:
        xml_payload = fetch_text(feed_url, timeout=timeout)
    except Exception as exc:
        logger.warning("Falha ao buscar feed RSS %s: %s", feed_url, exc)
        return []
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
        try:
            search_html = fetch_text(search_url, timeout=timeout)
        except Exception as exc:
            logger.warning("Falha na busca HTML %s: %s", search_url, exc)
            continue
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
            item_date = _date_from_article_url(link)
            published = item_date.isoformat() if item_date else ""
            hits.append(SearchHit(url=link, published=published))
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
