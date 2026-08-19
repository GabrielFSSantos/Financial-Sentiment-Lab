"""CLI do módulo de datasets: fetch, check e validate."""

from __future__ import annotations

import argparse
import sys

from modules.datasets import PROJECT_ROOT
from modules.datasets.assets import (
    AssetFetchError,
    check_dataset_assets,
    fetch_enabled_datasets,
)
from modules.datasets.config.loader import (
    ConfigurationError,
    load_datasets_configuration,
)
from modules.datasets.loader import DatasetLoader, validate_dataset


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m modules.datasets",
        description="Gerencia download e validação de datasets.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch_parser = subparsers.add_parser(
        "fetch",
        help="Baixa datasets enabled ausentes.",
    )
    fetch_parser.add_argument(
        "--dataset",
        action="append",
        dest="datasets",
        help="Baixa apenas o dataset informado (pode repetir).",
    )
    fetch_parser.add_argument(
        "--config",
        default="configs/datasets.yaml",
        help="Caminho para configs/datasets.yaml.",
    )

    check_parser = subparsers.add_parser(
        "check",
        help="Lista datasets enabled com source ausentes.",
    )
    check_parser.add_argument(
        "--config",
        default="configs/datasets.yaml",
        help="Caminho para configs/datasets.yaml.",
    )

    validate_parser = subparsers.add_parser(
        "validate",
        help="Valida formato e colunas mapeadas.",
    )
    validate_parser.add_argument(
        "--dataset",
        action="append",
        dest="datasets",
        help="Valida apenas o dataset informado (pode repetir).",
    )
    validate_parser.add_argument(
        "--config",
        default="configs/datasets.yaml",
        help="Caminho para configs/datasets.yaml.",
    )

    return parser


def _cmd_fetch(args: argparse.Namespace) -> int:
    try:
        configuration = load_datasets_configuration(
            project_root=PROJECT_ROOT,
            config_path=args.config,
        )
        summary = fetch_enabled_datasets(
            configuration,
            dataset_keys=args.datasets,
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
        configuration = load_datasets_configuration(
            project_root=PROJECT_ROOT,
            config_path=args.config,
        )
    except ConfigurationError as error:
        print(error, file=sys.stderr)
        return 1

    missing = check_dataset_assets(configuration)
    if not missing:
        print("Todos os datasets enabled com source estão presentes.")
        return 0

    print("Assets ausentes:")
    for item in missing:
        print(f"  - {item}")
    return 1


def _cmd_validate(args: argparse.Namespace) -> int:
    try:
        configuration = load_datasets_configuration(
            project_root=PROJECT_ROOT,
            config_path=args.config,
        )
    except ConfigurationError as error:
        print(error, file=sys.stderr)
        return 1

    selected = configuration.enabled_datasets
    if args.datasets:
        keys = set(args.datasets)
        selected = tuple(
            dataset
            for dataset in configuration.datasets
            if dataset.key in keys
        )
        missing = keys - {dataset.key for dataset in selected}
        if missing:
            print(
                f"Datasets não encontrados: {sorted(missing)}",
                file=sys.stderr,
            )
            return 1

    exit_code = 0

    for dataset in selected:
        try:
            report = validate_dataset(dataset)
            print(
                f"[OK] {report['dataset_key']}: "
                f"{len(report['columns'])} coluna(s) mapeada(s)"
            )
        except Exception as error:
            exit_code = 1
            print(f"[ERRO] {dataset.key}: {error}", file=sys.stderr)

    return exit_code


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "fetch":
        return _cmd_fetch(args)
    if args.command == "check":
        return _cmd_check(args)
    if args.command == "validate":
        return _cmd_validate(args)

    parser.error(f"Comando desconhecido: {args.command}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
