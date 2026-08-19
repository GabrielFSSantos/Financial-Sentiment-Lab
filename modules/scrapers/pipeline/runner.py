"""Orquestração da coleta multiportal."""

from __future__ import annotations

import importlib

from modules.scrapers.config.loader import ScrapersConfiguration
from modules.scrapers.pipeline.state import (
    load_state,
    save_state,
    update_site_state,
)
from modules.scrapers.schema.csv import append_records


def import_scraper(adapter: str):
    module_name, _, class_name = adapter.rpartition(".")
    module = importlib.import_module(module_name)
    return getattr(module, class_name)


def run_scrape(
    configuration: ScrapersConfiguration,
    *,
    since: str,
    until: str,
    site_key: str | None = None,
    use_state: bool = False,
) -> int:
    sites = configuration.enabled_sites(site_key=site_key)
    if site_key and not sites:
        raise ValueError(f"Site não encontrado ou desabilitado: {site_key}")

    state = load_state(configuration.state_path) if use_state else {"sites": {}, "seen_urls": []}
    total_new = 0

    for site in sites:
        scraper_cls = import_scraper(site.adapter)
        scraper = scraper_cls(configuration, site)
        records = scraper.scrape(
            since=since,
            until=until,
            state=state if use_state else None,
        )
        output_path = configuration.raw_dir / site.output_file
        total_rows, added_rows = append_records(output_path, records)
        print(
            f"{site.key}: {len(records)} coletado(s), +{added_rows} novo(s) "
            f"→ {output_path} (total {total_rows})"
        )
        total_new += added_rows

        if use_state:
            update_site_state(
                state,
                site_key=site.key,
                last_until=until,
                collected_urls=[record.get("url", "") for record in records],
            )
            save_state(configuration.state_path, state)

    return total_new
