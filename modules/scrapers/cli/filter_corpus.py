"""CLI para filtrar corpus strict por empresa e janela temporal."""

from __future__ import annotations

import argparse
from pathlib import Path

from modules.scrapers import PROJECT_ROOT
from modules.scrapers.pipeline.corpus import filter_corpus_records
from modules.scrapers.schema.csv import read_csv, write_csv


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Filtra noticias_strict.csv por empresa e datas."
    )
    parser.add_argument(
        "--input",
        default="data/saneamento_corpus/noticias_strict.csv",
        help="CSV de entrada",
    )
    parser.add_argument(
        "-o",
        "--output",
        required=True,
        help="CSV de saída",
    )
    parser.add_argument("--company", default=None, help="Filtrar empresa (ex.: Sabesp)")
    parser.add_argument("--since", default=None, help="Data inicial YYYY-MM-DD")
    parser.add_argument("--until", default=None, help="Data final YYYY-MM-DD")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    input_path = PROJECT_ROOT / args.input
    output_path = PROJECT_ROOT / args.output

    records = read_csv(input_path)
    filtered = filter_corpus_records(
        records,
        company=args.company,
        since=args.since,
        until=args.until,
    )
    write_csv(output_path, filtered)
    print(f"Filtrado: {len(filtered)} registro(s) → {output_path}")
    return 0
