"""Unified evaluation CLI (delegates to existing modules)."""

from __future__ import annotations

import argparse
import sys


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m modules.evaluation",
        description="Classifier evaluation and campaign reports.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    battery = sub.add_parser(
        "classifier-pt",
        help="PT classifier battery (finbert vs baselines)",
    )
    battery.add_argument(
        "action",
        choices=("prepare", "run", "iti-if-gate"),
    )

    sub.add_parser("manual-sample", help="Stratified manual label sample")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    if args.command == "classifier-pt":
        from modules.evaluation.classifier_eval_pt import main as pt_main

        return pt_main([args.action])

    if args.command == "manual-sample":
        from modules.evaluation.manual_labels import main as manual_main

        return manual_main([])

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
