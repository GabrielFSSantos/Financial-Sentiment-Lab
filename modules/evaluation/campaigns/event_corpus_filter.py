"""Filtro heurístico de roundups/agendas no corpus evento Sabesp."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from modules.evaluation.classifier_error_analysis import classify_typology
from modules.experiment import PROJECT_ROOT

CORPUS_PATH = PROJECT_ROOT / "data/water_utilities_corpus/articles_strict_sabesp.csv"
FILTERED_PATH = (
    PROJECT_ROOT
    / "data/water_utilities_corpus/articles_strict_sabesp_event_filtered.csv"
)
EVENT_DATE_FROM = "2023-11-01"
EVENT_DATE_TO = "2024-04-30"


def load_event_corpus(corpus_path: Path = CORPUS_PATH) -> pd.DataFrame:
    frame = pd.read_csv(corpus_path)
    frame["data"] = pd.to_datetime(frame["data"], errors="coerce")
    mask = (
        (frame["data"] >= EVENT_DATE_FROM)
        & (frame["data"] <= EVENT_DATE_TO)
        & (frame["empresa"].astype(str).str.strip().str.lower() == "sabesp")
    )
    return frame[mask].copy()


def filter_roundups(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    working = frame.copy()
    working["notas"] = ""
    working["tipologia"] = working.apply(classify_typology, axis=1)
    removed = working[working["tipologia"] == "roundup_agenda"].copy()
    kept = working[working["tipologia"] == "focal_sabesp"].drop(columns=["tipologia"])
    return kept, removed


def build_filtered_corpus(
    *,
    corpus_path: Path = CORPUS_PATH,
    output_path: Path = FILTERED_PATH,
) -> dict[str, int]:
    event = load_event_corpus(corpus_path)
    kept, removed = filter_roundups(event)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    kept.to_csv(output_path, index=False)
    return {
        "event_total": len(event),
        "kept": len(kept),
        "removed": len(removed),
        "roundup_fraction": len(removed) / len(event) if len(event) else 0.0,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Filtra roundups do corpus evento")
    parser.add_argument("--corpus", default=str(CORPUS_PATH))
    parser.add_argument("--output", default=str(FILTERED_PATH))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    stats = build_filtered_corpus(
        corpus_path=Path(args.corpus),
        output_path=Path(args.output),
    )
    print(
        f"Evento: {stats['event_total']} | "
        f"mantidas: {stats['kept']} | "
        f"removidas (roundup): {stats['removed']} "
        f"({stats['roundup_fraction']:.1%})"
    )
    print(f"CSV: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
