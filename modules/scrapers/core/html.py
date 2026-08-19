"""Parsing HTML para scrapers."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Iterable
from urllib.parse import urljoin

from bs4 import BeautifulSoup


def parse_html(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


def extract_links(
    soup: BeautifulSoup,
    *,
    base_url: str,
    selector: str,
    exclude_substrings: Iterable[str] = (),
) -> list[str]:
    links: list[str] = []
    seen: set[str] = set()
    excludes = tuple(exclude_substrings)
    for anchor in soup.select(selector):
        href = anchor.get("href")
        if not href:
            continue
        absolute = urljoin(base_url, href.strip())
        if any(token in absolute for token in excludes):
            continue
        if absolute in seen:
            continue
        seen.add(absolute)
        links.append(absolute)
    return links


def extract_paragraphs(soup: BeautifulSoup, selector: str) -> str:
    chunks: list[str] = []
    for node in soup.select(selector):
        text = node.get_text(" ", strip=True)
        if text:
            chunks.append(text)
    return "\n".join(chunks).strip()


def extract_title(soup: BeautifulSoup) -> str:
    for selector in ("h1", "meta[property='og:title']", "title"):
        if selector.startswith("meta"):
            node = soup.select_one(selector)
            if node and node.get("content"):
                return str(node["content"]).strip()
            continue
        node = soup.select_one(selector)
        if node:
            text = node.get_text(" ", strip=True)
            if text:
                return text
    return ""


def parse_date(value: str) -> str | None:
    raw = value.strip()
    if not raw:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(raw[:19], fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    match = re.search(r"(\d{4}-\d{2}-\d{2})", raw)
    if match:
        return match.group(1)
    return None
