"""CLI do módulo de research: validate e check."""

from __future__ import annotations

import argparse
import sys

from modules.research import PROJECT_ROOT
from modules.research.config.loader import (
    ConfigurationError,
    load_research_configuration,
)
from modules.research.pipeline.runner import (
    ResearchRunnerError,
    check_research_inputs,
    run_research,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m modules.research",
        description="Validação científica ITI vs baselines vs mercado.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser(
        "validate",
        help="Executa validação incremental para um run do experimento.",
    )
    validate_parser.add_argument(
        "--config",
        default="configs/research.yaml",
        help="Caminho para configs/research.yaml.",
    )
    validate_parser.add_argument(
        "--run-id",
        dest="run_id",
        default=None,
        help="Run do experimento (default: mais recente).",
    )
    validate_parser.add_argument(
        "--model",
        dest="model_key",
        default=None,
        help="Restringe ao modelo informado.",
    )
    validate_parser.add_argument(
        "--dataset",
        dest="dataset_key",
        default=None,
        help="Restringe ao dataset informado.",
    )

    check_parser = subparsers.add_parser(
        "check",
        help="Verifica índices do experimento e CSV de mercado.",
    )
    check_parser.add_argument(
        "--config",
        default="configs/research.yaml",
        help="Caminho para configs/research.yaml.",
    )
    check_parser.add_argument(
        "--run-id",
        dest="run_id",
        default=None,
        help="Run do experimento (default: mais recente).",
    )

    return parser


def _cmd_validate(args: argparse.Namespace) -> int:
    try:
        configuration = load_research_configuration(
            project_root=PROJECT_ROOT,
            config_path=args.config,
            run_id=args.run_id,
            model_key=args.model_key,
            dataset_key=args.dataset_key,
        )
        summary = run_research(configuration)
    except (ConfigurationError, ResearchRunnerError) as error:
        print(error, file=sys.stderr)
        return 1

    print(summary.to_dict()["conclusion"])
    print(
        f"Run {summary.run_id}: {len(summary.combinations)} combinação(ões) "
        "validada(s)."
    )
    for warning in summary.warnings:
        print(f"AVISO: {warning}", file=sys.stderr)
    return 0


def _cmd_check(args: argparse.Namespace) -> int:
    try:
        configuration = load_research_configuration(
            project_root=PROJECT_ROOT,
            config_path=args.config,
            run_id=args.run_id,
        )
    except ConfigurationError as error:
        print(error, file=sys.stderr)
        return 1

    issues = check_research_inputs(configuration)
    if not issues:
        print("Pré-requisitos de research atendidos.")
        return 0

    print("Pendências:")
    for issue in issues:
        print(f"  - {issue}")
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "validate":
        return _cmd_validate(args)
    if args.command == "check":
        return _cmd_check(args)

    parser.error(f"Comando desconhecido: {args.command}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
