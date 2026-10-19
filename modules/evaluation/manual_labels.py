"""Manual label sampling and agreement vs FinBERT."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from sklearn.metrics import cohen_kappa_score

from modules.experiment import PROJECT_ROOT

# (coluna canônica no manual_labels_100.csv, cabeçalho PT no export Drive)
WORKSHEET_COLUMN_MAP: tuple[tuple[str, str], ...] = (
    ("news_id", "id_noticia"),
    ("data", "data"),
    ("fonte", "fonte"),
    ("titulo", "titulo"),
    ("url", "link"),
    ("impacto_alvo", "impacto_sabesp_anotador_1"),
    ("tipologia", "tipologia"),
    ("sentimento_global", "tom_da_materia"),
    ("ambiguo", "caso_ambiguo"),
    ("notas", "notas_anotador_1"),
    ("anotador", "nome_anotador_1"),
    ("anotador_2", "nome_anotador_2"),
    ("impacto_alvo_2", "impacto_sabesp_anotador_2"),
    ("anotador_3", "nome_anotador_3"),
    ("impacto_alvo_3", "impacto_sabesp_anotador_3"),
    ("rotulo_finbert", "referencia_finbert"),
    ("rotulo_llm_juiz", "referencia_llm_juiz"),
    ("notas_llm", "justificativa_llm"),
    ("versao_protocolo", "versao_protocolo"),
)

WORKSHEET_COLUMNS: tuple[str, ...] = tuple(
    canonical for canonical, _ in WORKSHEET_COLUMN_MAP
)
WORKSHEET_HEADERS_PT: dict[str, str] = dict(WORKSHEET_COLUMN_MAP)
WORKSHEET_HEADERS_PT_ORDER: tuple[str, ...] = tuple(
    pt for _, pt in WORKSHEET_COLUMN_MAP
)

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
    labels = sorted(
        set(merged["rotulo_manual"].dropna()) | set(merged["rotulo_finbert"].dropna())
    )
    kappa = float(
        cohen_kappa_score(
            merged["rotulo_manual"],
            merged["rotulo_finbert"],
            labels=labels,
        )
    )

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
        f"- Cohen's kappa: {kappa:.3f}",
        "",
        "## Matriz de confusão",
        "",
        confusion.to_string(),
        "",
        "## Erros",
        "",
    ]
    errors = merged[~merged["acerto"]][
        [
            column
            for column in (
                "news_id",
                "titulo",
                "rotulo_manual",
                "rotulo_finbert",
                "notas",
            )
            if column in merged.columns
        ]
    ]
    if errors.empty:
        lines.append("_Nenhum erro._")
    else:
        lines.append(errors.to_string(index=False))

    output_report.parent.mkdir(parents=True, exist_ok=True)
    output_report.write_text("\n".join(lines), encoding="utf-8")
    return {"accuracy": accuracy, "cohen_kappa": kappa, "n_labeled": len(merged)}


def export_annotation_worksheet(
    manual_path: Path,
    corpus_path: Path,
    output_path: Path,
    *,
    subset_news_ids_path: Path | None = None,
    use_portuguese_headers: bool = True,
    blind_for_annotator_2: bool = False,
    blind_for_new_expert: bool = False,
) -> pd.DataFrame:
    """Join formal sample with corpus title/URL for Drive annotation worksheet."""
    manual = pd.read_csv(manual_path)
    if "news_id" not in manual.columns:
        raise ValueError("Amostra manual precisa da coluna news_id.")

    if subset_news_ids_path is not None and subset_news_ids_path.is_file():
        subset = pd.read_csv(subset_news_ids_path)
        id_col = "news_id" if "news_id" in subset.columns else subset.columns[0]
        allowed = set(subset[id_col].astype(str).str.strip())
        manual = manual[manual["news_id"].astype(str).str.strip().isin(allowed)].copy()
        if manual.empty:
            raise ValueError("Subconjunto news_id não intersecta a amostra manual.")

    corpus = _prepare_corpus(pd.read_csv(corpus_path))
    if "id" not in corpus.columns:
        raise ValueError("Corpus strict precisa da coluna id.")
    for column in ("data", "fonte", "titulo", "url"):
        if column not in corpus.columns:
            raise ValueError(f"Corpus strict precisa da coluna {column}.")

    context = corpus[["id", "data", "fonte", "titulo", "url"]].drop_duplicates(
        subset=["id"]
    )
    merged = manual.merge(
        context,
        left_on="news_id",
        right_on="id",
        how="left",
    )
    missing = int(merged["url"].isna().sum())
    if missing:
        bad = merged.loc[merged["url"].isna(), "news_id"].astype(str).tolist()
        preview = ", ".join(bad[:5])
        suffix = "..." if len(bad) > 5 else ""
        raise ValueError(
            f"{missing} news_id da amostra manual sem match no corpus strict: "
            f"{preview}{suffix}"
        )

    for column in WORKSHEET_COLUMNS:
        if column not in merged.columns:
            merged[column] = ""
    if blind_for_new_expert or blind_for_annotator_2:
        merged["versao_protocolo"] = "2026-10-19"
    columns = list(WORKSHEET_COLUMNS)
    if blind_for_new_expert:
        hidden = {
            "impacto_alvo",
            "notas",
            "anotador",
            "rotulo_finbert",
            "rotulo_llm_juiz",
            "notas_llm",
            "sentimento_global",
        }
        columns = [c for c in columns if c not in hidden]
        for col in ("impacto_alvo_2", "anotador_2", "impacto_alvo_3", "anotador_3"):
            if col in merged.columns:
                merged[col] = ""
    elif blind_for_annotator_2:
        columns = [
            c
            for c in columns
            if c
            not in (
                "impacto_alvo",
                "notas",
                "anotador",
                "rotulo_finbert",
                "rotulo_llm_juiz",
                "notas_llm",
            )
        ]
    frame = merged[columns].copy()
    if use_portuguese_headers:
        frame = frame.rename(
            columns={k: v for k, v in WORKSHEET_HEADERS_PT.items() if k in columns}
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_path, index=False)
    return frame


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Rótulos manuais vs FinBERT")
    sub = parser.add_subparsers(dest="command", required=True)

    sample = sub.add_parser("sample", help="Gera amostra estratificada para rotulação")
    sample.add_argument(
        "--corpus",
        default=str(
            PROJECT_ROOT / "data/water_utilities_corpus/articles_strict_sabesp.csv"
        ),
    )
    sample.add_argument("--predictions", required=True)
    sample.add_argument(
        "--output",
        default=str(PROJECT_ROOT / "data/water_utilities_corpus/manual_labels_100.csv"),
    )
    sample.add_argument("--n", type=int, default=100)

    compare = sub.add_parser("compare", help="Compara rótulos manuais com predictions")
    compare.add_argument(
        "--manual",
        default=str(PROJECT_ROOT / "data/water_utilities_corpus/manual_labels_100.csv"),
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
        print(
            f"Acurácia: {metrics['accuracy']:.1%} | "
            f"kappa: {metrics['cohen_kappa']:.3f} "
            f"({metrics['n_labeled']} rotulados)"
        )
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
