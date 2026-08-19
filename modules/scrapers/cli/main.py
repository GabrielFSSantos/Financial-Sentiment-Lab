"""CLI de coleta multiportal."""

from __future__ import annotations

import argparse

from modules.scrapers import PROJECT_ROOT
from modules.scrapers.config.loader import load_scrapers_configuration
from modules.scrapers.pipeline.runner import run_scrape
from modules.scrapers.pipeline.state import resolve_cron_window


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Coleta notícias de portais configurados.")
    parser.add_argument("--cron", action="store_true", help="Coleta incremental a partir do state")
    parser.add_argument("--since", required=False, help="Data inicial YYYY-MM-DD")
    parser.add_argument("--until", required=False, help="Data final YYYY-MM-DD")
    parser.add_argument("--site", required=False, help="Executa apenas um portal (ex.: valor)")
    parser.add_argument(
        "--config",
        default="configs/scrapers.yaml",
        help="Caminho do YAML de scrapers",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.cron and (args.since or args.until):
        parser.error("Use --cron ou (--since e --until), não ambos.")

    if not args.cron and (not args.since or not args.until):
        parser.error("Informe --since e --until (YYYY-MM-DD) ou use --cron.")

    configuration = load_scrapers_configuration(
        project_root=PROJECT_ROOT,
        config_path=PROJECT_ROOT / args.config,
    )

    if args.cron:
        default_since = str(configuration.defaults.get("default_since", "2020-01-01"))
        since, until = resolve_cron_window(
            state_path=configuration.state_path,
            corpus_path=configuration.corpus_path,
            default_since=default_since,
        )
        print(f"Cron: janela {since} → {until}")
        run_scrape(
            configuration,
            since=since,
            until=until,
            site_key=args.site,
            use_state=True,
        )
    else:
        run_scrape(
            configuration,
            since=args.since,
            until=args.until,
            site_key=args.site,
            use_state=False,
        )
    return 0
