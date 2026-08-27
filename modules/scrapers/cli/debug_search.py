"""CLI de diagnóstico de busca Playwright."""

from __future__ import annotations

import argparse

from modules.scrapers import PROJECT_ROOT
from modules.scrapers.config.loader import load_scrapers_configuration
from modules.scrapers.core.search import debug_discover_links


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Diagnóstico de links Playwright por portal.")
    parser.add_argument("--site", required=True, help="Portal (ex.: valor, g1_economia)")
    parser.add_argument("--since", required=True, help="Data inicial YYYY-MM-DD")
    parser.add_argument("--until", required=True, help="Data final YYYY-MM-DD")
    parser.add_argument("--query", default="Sabesp", help="Termo de busca (default: Sabesp)")
    parser.add_argument(
        "--config",
        default="configs/scrapers.yaml",
        help="Caminho do YAML de scrapers",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    configuration = load_scrapers_configuration(
        project_root=PROJECT_ROOT,
        config_path=PROJECT_ROOT / args.config,
    )
    sites = configuration.enabled_sites(site_key=args.site)
    if not sites:
        parser.error(f"Site não encontrado ou desabilitado: {args.site}")

    site = sites[0]
    strategy = str(site.scraping.get("search_strategy", "")).strip().lower()
    if strategy != "playwright":
        parser.error(f"Site {args.site} não usa search_strategy: playwright")

    timeout = float(configuration.defaults.get("request_timeout", 30.0))
    stats = debug_discover_links(
        scraping=site.scraping,
        queries=(args.query,),
        timeout=timeout,
        since=args.since,
        until=args.until,
    )

    print(f"=== debug-search: {site.key} ({args.since} → {args.until}) ===")
    for item in stats:
        print(f"\nQuery: {item.query}")
        print(f"  Links brutos:     {item.raw_count}")
        print(f"  Após filtros:     {item.filtered_count}")
        print(f"  Na janela:        {item.in_window_count}")
        if item.samples:
            print("  Amostra (URL | data):")
            for url, published in item.samples:
                print(f"    {published} | {url[:100]}")
        else:
            print("  Amostra: (vazia)")
    return 0
