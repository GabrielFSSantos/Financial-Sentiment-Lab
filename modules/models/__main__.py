"""CLI do módulo de modelos: fetch e check de pesos locais."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from modules.models import PROJECT_ROOT
from modules.models.assets import (
    AssetFetchError,
    check_model_assets,
    fetch_enabled_models,
)
from modules.models.config.loader import (
    ConfigurationError,
    load_models_configuration,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m modules.models",
        description="Gerencia download e validação de modelos FinBERT.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch_parser = subparsers.add_parser(
        "fetch",
        help="Baixa modelos enabled ausentes.",
    )
    fetch_parser.add_argument(
        "--model",
        action="append",
        dest="models",
        help="Baixa apenas o modelo informado (pode repetir).",
    )
    fetch_parser.add_argument(
        "--config",
        default="configs/models.yaml",
        help="Caminho para configs/models.yaml.",
    )

    check_parser = subparsers.add_parser(
        "check",
        help="Lista arquivos de modelos enabled ausentes.",
    )
    check_parser.add_argument(
        "--config",
        default="configs/models.yaml",
        help="Caminho para configs/models.yaml.",
    )

    return parser


def _cmd_fetch(args: argparse.Namespace) -> int:
    try:
        configuration = load_models_configuration(
            project_root=PROJECT_ROOT,
            config_path=args.config,
        )
        summary = fetch_enabled_models(
            configuration,
            model_keys=args.models,
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
        configuration = load_models_configuration(
            project_root=PROJECT_ROOT,
            config_path=args.config,
        )
    except ConfigurationError as error:
        print(error, file=sys.stderr)
        return 1

    missing = check_model_assets(configuration)
    if not missing:
        print("Todos os modelos enabled estão presentes.")
        return 0

    print("Assets ausentes:")
    for item in missing:
        print(f"  - {item}")
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
