"""Unified evaluation CLI (delegates to existing modules)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


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

    export_ws = sub.add_parser(
        "export-worksheet",
        help="CSV para rotulação manual (título + URL do corpus)",
    )
    export_ws.add_argument("--manual", type=Path, default=None)
    export_ws.add_argument("--corpus", type=Path, default=None)
    export_ws.add_argument("--output", type=Path, default=None)
    export_ws.add_argument("--subset-news-ids", type=Path, default=None)
    export_ws.add_argument(
        "--english-headers",
        action="store_true",
        help="Cabeçalhos canônicos em inglês/técnicos",
    )

    pilot = sub.add_parser("llm-judge-pilot", help="LLM-as-judge pilot batch (qualification)")
    pilot.add_argument("--limit", type=int, default=10)
    pilot.add_argument("--model-id", default=None)
    pilot.add_argument("--mock", action="store_true")
    pilot.add_argument("--output-csv", type=Path, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    if args.command == "classifier-pt":
        from modules.evaluation.classifier_eval_pt import main as pt_main

        return pt_main([args.action])

    if args.command == "manual-sample":
        from modules.evaluation.manual_labels import main as manual_main

        return manual_main([])

    if args.command == "export-worksheet":
        from modules.evaluation.manual_labels import main as manual_main

        argv = ["export-worksheet"]
        if args.manual is not None:
            argv.extend(["--manual", str(args.manual)])
        if args.corpus is not None:
            argv.extend(["--corpus", str(args.corpus)])
        if args.output is not None:
            argv.extend(["--output", str(args.output)])
        if args.subset_news_ids is not None:
            argv.extend(["--subset-news-ids", str(args.subset_news_ids)])
        if args.english_headers:
            argv.append("--english-headers")
        return manual_main(argv)

    if args.command == "llm-judge-pilot":
        from modules.evaluation.core.settings import load_evaluation_settings
        from modules.evaluation.llm_judge_pilot import run_pilot

        settings = load_evaluation_settings()
        model_id = args.model_id or settings.llm_judge_model_id
        out = run_pilot(
            limit=args.limit,
            model_id=model_id,
            mock=args.mock,
            output_csv=args.output_csv,
        )
        print(f"Piloto gravado em: {out}")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
