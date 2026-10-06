"""CLI para rebuild do corpus strict a partir de raw/."""

from __future__ import annotations

import argparse

from modules.scrapers import PROJECT_ROOT
from modules.scrapers.config.loader import load_scrapers_configuration
from modules.scrapers.pipeline.corpus import build_strict_corpus


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Mescla raw/ em noticias_strict.csv (modo strict offline)."
    )
    parser.add_argument(
        "--output",
        default="data/water_utilities_corpus/articles_strict.csv",
        help="Caminho do corpus strict",
    )
    parser.add_argument(
        "--config",
        default="configs/scrapers.yaml",
        help="YAML de scrapers (para raw_dir)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    configuration = load_scrapers_configuration(
        project_root=PROJECT_ROOT,
        config_path=PROJECT_ROOT / args.config,
    )
    output_path = PROJECT_ROOT / args.output
    result = build_strict_corpus(
        raw_dir=configuration.raw_dir,
        strict_path=output_path,
    )
    print(
        f"Corpus strict: {result.classified_count} classificado(s) → {output_path}"
    )
    if result.discarded_count:
        print(f"Descartados: {result.discarded_count}")
    return 0
