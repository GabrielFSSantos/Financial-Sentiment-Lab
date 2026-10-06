"""Fixtures compartilhadas da suíte de testes."""

from __future__ import annotations

import os
from pathlib import Path

import pytest


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "network: testes que acessam internet (requer SCRAPERS_LIVE=1)",
    )


def pytest_collection_modifyitems(
    config: pytest.Config,
    items: list[pytest.Item],
) -> None:
    if os.environ.get("SCRAPERS_LIVE") == "1":
        return

    skip_live = pytest.mark.skip(
        reason="Teste live desabilitado; use SCRAPERS_LIVE=1 para rodar.",
    )
    for item in items:
        if item.get_closest_marker("network") or item.get_closest_marker(
            "playwright"
        ):
            item.add_marker(skip_live)


@pytest.fixture
def project_root() -> Path:
    return Path(__file__).resolve().parents[1]
