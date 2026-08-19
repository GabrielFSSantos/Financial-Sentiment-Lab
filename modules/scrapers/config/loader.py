"""Carrega configs/scrapers.yaml."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml

from modules.scrapers import PROJECT_ROOT


@dataclass(frozen=True)
class SiteConfiguration:
    key: str
    enabled: bool
    display_name: str
    adapter: str
    output_file: str
    scraping: Mapping[str, Any]


@dataclass(frozen=True)
class ScrapersConfiguration:
    project_root: Path
    defaults: Mapping[str, Any]
    sites: tuple[SiteConfiguration, ...]

    @property
    def raw_dir(self) -> Path:
        return self.project_root / str(self.defaults.get("raw_dir", "data/saneamento_corpus/raw"))

    @property
    def corpus_path(self) -> Path:
        return self.project_root / str(
            self.defaults.get("corpus_path", "data/saneamento_corpus/noticias.csv")
        )

    @property
    def state_path(self) -> Path:
        return self.project_root / str(
            self.defaults.get("state_path", "data/saneamento_corpus/.scrape_state.json")
        )

    def enabled_sites(self, *, site_key: str | None = None) -> tuple[SiteConfiguration, ...]:
        enabled = tuple(site for site in self.sites if site.enabled)
        if not site_key:
            return enabled
        filtered = tuple(site for site in enabled if site.key == site_key)
        return filtered


def load_scrapers_configuration(
    *,
    project_root: Path | None = None,
    config_path: Path | None = None,
) -> ScrapersConfiguration:
    root = project_root or PROJECT_ROOT
    path = config_path or root / "configs" / "scrapers.yaml"
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"Configuração inválida: {path}")

    defaults = dict(payload.get("defaults") or {})
    sites_payload = payload.get("sites") or {}
    sites: list[SiteConfiguration] = []
    if isinstance(sites_payload, Mapping):
        for key, value in sites_payload.items():
            if not isinstance(value, Mapping):
                continue
            sites.append(
                SiteConfiguration(
                    key=str(key),
                    enabled=bool(value.get("enabled", False)),
                    display_name=str(value.get("display_name", key)),
                    adapter=str(value.get("adapter", "")),
                    output_file=str(value.get("output_file", f"{key}.csv")),
                    scraping=dict(value.get("scraping") or {}),
                )
            )

    return ScrapersConfiguration(
        project_root=root,
        defaults=defaults,
        sites=tuple(sites),
    )
