"""Amostragem e comparação de rótulos manuais vs FinBERT."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from modules.experiment import PROJECT_ROOT

LABEL_MAP = {
    "POSITIVE": "POS",
    "NEGATIVE": "NEG",
    "NEUTRAL": "NEU",
    "POS": "POS",
    "NEG": "NEG",
    "NEU": "NEU",
}


def _normalize_label(value: str) -> str:
    return LABEL_MAP.get(str(value).strip().upper(), str(value).strip().upper())


def _prepare_corpus(corpus: pd.DataFrame) -> pd.DataFrame:
    frame = corpus.copy()
    if "news_id" not in frame.columns and "id" in frame.columns:
        frame["news_id"] = frame["id"]
    if "titulo" not in frame.columns and "title" in frame.columns:
        frame["titulo"] = frame["title"]
    if "data" not in frame.columns and "date" in frame.columns:
        frame["data"] = frame["date"]
    return frame


def _prepare_predictions(predictions: pd.DataFrame) -> pd.DataFrame:
    frame = predictions.copy()
    label_col = "predicted_label" if "predicted_label" in frame.columns else "label"
    frame["rotulo_finbert"] = frame[label_col].map(_normalize_label)
    return frame[["news_id", "rotulo_finbert"]].drop_duplicates(subset=["news_id"])


def stratified_sample(
    corpus_path: Path,
    predictions_path: Path,
    *,
    n_total: int = 100,
    output_path: Path,
    seed: int = 42,
) -> pd.DataFrame:
    corpus = _prepare_corpus(pd.read_csv(corpus_path))
    predictions = _prepare_predictions(pd.read_csv(predictions_path))

    merged = corpus.merge(predictions, on="news_id", how="inner")
    if merged.empty:
        raise ValueError("Nenhuma notícia em comum entre corpus e predictions.")

    counts = merged["rotulo_finbert"].value_counts()
    targets: dict[str, int] = {}
    remaining = n_total
    labels = list(counts.index)
    for index, label in enumerate(labels):
        if index == len(labels) - 1:
            targets[label] = remaining
        else:
            share = max(1, round(n_total * counts[label] / len(merged)))
            targets[label] = min(share, remaining)
            remaining -= targets[label]

    frames: list[pd.DataFrame] = []
    for label, count in targets.items():
        subset = merged[merged["rotulo_finbert"] == label]
        frames.append(subset.sample(n=min(count, len(subset)), random_state=seed))

    sample = pd.concat(frames, ignore_index=True).head(n_total)
    sample["rotulo_manual"] = ""
    sample["notas"] = ""

    columns = [
        "news_id",
        "titulo",
        "url",
        "data",
        "rotulo_finbert",
        "rotulo_manual",
        "notas",
    ]
    for column in columns:
        if column not in sample.columns:
            sample[column] = ""
    sample = sample[columns]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sample.to_csv(output_path, index=False)
    return sample


def compare_manual_labels(
    manual_path: Path,
    predictions_path: Path,
    *,
    output_report: Path,
) -> dict[str, float]:
    manual = pd.read_csv(manual_path)
    predictions = _prepare_predictions(pd.read_csv(predictions_path))

    labeled = manual[manual["rotulo_manual"].astype(str).str.strip() != ""].copy()
    if labeled.empty:
        raise ValueError("Nenhum rótulo manual preenchido em rotulo_manual.")

    labeled["rotulo_manual"] = labeled["rotulo_manual"].map(_normalize_label)
    merged = labeled.merge(predictions, on="news_id", how="left", suffixes=("", "_pred"))
    if "rotulo_finbert_pred" in merged.columns:
        merged["rotulo_finbert"] = merged["rotulo_finbert_pred"].fillna(merged["rotulo_finbert"])

    merged["acerto"] = merged["rotulo_manual"] == merged["rotulo_finbert"]
    accuracy = float(merged["acerto"].mean())

    confusion = pd.crosstab(
        merged["rotulo_manual"],
        merged["rotulo_finbert"],
        rownames=["manual"],
        colnames=["finbert"],
    )

    lines = [
        "# Relatório de rótulos manuais vs FinBERT",
        "",
        f"- Amostra rotulada: {len(merged)}",
        f"- Acurácia: {accuracy:.1%}",
        "",
        "## Matriz de confusão",
        "",
        confusion.to_markdown(),
        "",
        "## Erros",
        "",
    ]
    errors = merged[~merged["acerto"]][
        ["news_id", "titulo", "rotulo_manual", "rotulo_finbert", "notas"]
    ]
    if errors.empty:
        lines.append("_Nenhum erro._")
    else:
        lines.append(errors.to_markdown(index=False))

    output_report.parent.mkdir(parents=True, exist_ok=True)
    output_report.write_text("\n".join(lines), encoding="utf-8")
    return {"accuracy": accuracy, "n_labeled": len(merged)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Rótulos manuais vs FinBERT")
    sub = parser.add_subparsers(dest="command", required=True)

    sample = sub.add_parser("sample", help="Gera amostra estratificada para rotulação")
    sample.add_argument(
        "--corpus",
        default=str(PROJECT_ROOT / "data/saneamento_corpus/noticias_strict_sabesp.csv"),
    )
    sample.add_argument("--predictions", required=True)
    sample.add_argument(
        "--output",
        default=str(PROJECT_ROOT / "data/saneamento_corpus/rotulos_manual_100.csv"),
    )
    sample.add_argument("--n", type=int, default=100)

    compare = sub.add_parser("compare", help="Compara rótulos manuais com predictions")
    compare.add_argument(
        "--manual",
        default=str(PROJECT_ROOT / "data/saneamento_corpus/rotulos_manual_100.csv"),
    )
    compare.add_argument("--predictions", required=True)
    compare.add_argument(
        "--report",
        default=str(PROJECT_ROOT / "outputs/campaigns/sabesp_2026/manual_label_report.md"),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "sample":
        stratified_sample(
            Path(args.corpus),
            Path(args.predictions),
            n_total=args.n,
            output_path=Path(args.output),
        )
        print(f"Amostra salva em {args.output}")
        return 0

    if args.command == "compare":
        metrics = compare_manual_labels(
            Path(args.manual),
            Path(args.predictions),
            output_report=Path(args.report),
        )
        print(f"Acurácia: {metrics['accuracy']:.1%} ({metrics['n_labeled']} rotulados)")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
