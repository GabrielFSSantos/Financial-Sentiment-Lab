"""CLI do módulo de mercado: fetch e check de preços locais."""

from __future__ import annotations

import argparse
import sys

from modules.market import PROJECT_ROOT
from modules.market.assets import (
    AssetFetchError,
    check_market_assets,
    fetch_market_assets,
)
from modules.market.config.loader import (
    ConfigurationError,
    load_market_configuration,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m modules.market",
        description="Gerencia download e validação de preços de mercado.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch_parser = subparsers.add_parser(
        "fetch",
        help="Baixa preços ausentes via source configurada.",
    )
    fetch_parser.add_argument(
        "--config",
        default="configs/market.yaml",
        help="Caminho para configs/market.yaml.",
    )
    fetch_parser.add_argument(
        "--force",
        action="store_true",
        help="Rebaixa mesmo se o CSV local já existir.",
    )

    check_parser = subparsers.add_parser(
        "check",
        help="Lista CSV de mercado ausente.",
    )
    check_parser.add_argument(
        "--config",
        default="configs/market.yaml",
        help="Caminho para configs/market.yaml.",
    )

    return parser


def _cmd_fetch(args: argparse.Namespace) -> int:
    try:
        configuration = load_market_configuration(
            project_root=PROJECT_ROOT,
            config_path=args.config,
        )
        summary = fetch_market_assets(
            configuration,
            force=args.force,
        )
    except (ConfigurationError, AssetFetchError) as error:
        print(error, file=sys.stderr)
        return 1

    for report in summary.reports:
        print(
            f"[{report.status}] {report.asset_key}: "
            f"{report.target} — {report.message}"
        )

    print(
        f"Concluído: {summary.downloaded_count} baixado(s), "
        f"{summary.failed_count} falha(s)."
    )
    return 0 if summary.failed_count == 0 else 1


def _cmd_check(args: argparse.Namespace) -> int:
    try:
        configuration = load_market_configuration(
            project_root=PROJECT_ROOT,
            config_path=args.config,
        )
    except ConfigurationError as error:
        print(error, file=sys.stderr)
        return 1

    missing = check_market_assets(configuration)
    if not missing:
        print("Preços de mercado presentes.")
        return 0

    print("Assets ausentes:")
    for item in missing:
        print(f"  - {item}")
    print("Execute: python -m modules.market fetch")
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "fetch":
        return _cmd_fetch(args)
    if args.command == "check":
        return _cmd_check(args)

    parser.error(f"Comando desconhecido: {args.command}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
