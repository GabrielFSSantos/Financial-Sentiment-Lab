"""Relatório de volume do corpus de saneamento."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from modules.scrapers import PROJECT_ROOT
from modules.scrapers.config.loader import load_scrapers_configuration


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Resumo do corpus de saneamento.")
    parser.add_argument(
        "--config",
        default="configs/scrapers.yaml",
        help="Caminho do YAML de scrapers",
    )
    parser.add_argument(
        "--corpus",
        default=None,
        help="Caminho alternativo do CSV (default: noticias.csv do YAML)",
    )
    return parser


def _summarize(path: Path, label: str) -> None:
    if not path.is_file():
        print(f"\n=== {label}: ausente ({path}) ===")
        return

    df = pd.read_csv(path)
    print(f"\n=== {label}: {len(df)} registro(s) — {path} ===")
    if df.empty:
        return

    if "empresa" in df.columns:
        print("\nPor empresa:")
        print(df["empresa"].value_counts().head(15).to_string())
    if "fonte" in df.columns:
        print("\nPor fonte:")
        print(df["fonte"].value_counts().head(15).to_string())
    if "data" in df.columns:
        dates = pd.to_datetime(df["data"], errors="coerce")
        print(f"\nPeríodo: {dates.min()} → {dates.max()}")
        print("\nPor mês:")
        print(dates.dt.to_period("M").value_counts().sort_index().tail(12).to_string())


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    configuration = load_scrapers_configuration(
        project_root=PROJECT_ROOT,
        config_path=PROJECT_ROOT / args.config,
    )
    corpus_path = (
        PROJECT_ROOT / args.corpus
        if args.corpus
        else configuration.corpus_path
    )
    _summarize(corpus_path, "Classificados")
    _summarize(configuration.pending_corpus_path, "Pendentes")
    return 0
