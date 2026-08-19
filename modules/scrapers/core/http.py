"""HTTP helpers para scrapers."""

from __future__ import annotations

import time
from typing import Mapping

import requests

DEFAULT_HEADERS: Mapping[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; FinancialSentimentLab/1.0; +https://github.com)"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
}


def fetch_text(
    url: str,
    *,
    timeout: float,
    headers: Mapping[str, str] | None = None,
) -> str:
    response = requests.get(
        url,
        timeout=timeout,
        headers={**DEFAULT_HEADERS, **(headers or {})},
    )
    response.raise_for_status()
    response.encoding = response.encoding or "utf-8"
    return response.text


def sleep(delay_seconds: float) -> None:
    if delay_seconds > 0:
        time.sleep(delay_seconds)
