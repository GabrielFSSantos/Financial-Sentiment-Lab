"""Métricas de concordância entre rótulos de referência e predições."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from sklearn.metrics import accuracy_score, cohen_kappa_score, confusion_matrix

from modules.evaluation.manual_labels import LABEL_MAP, _normalize_label

LABEL_COLUMNS = ("true_label", "predicted_label", "rotulo_manual", "rotulo_finbert")


def _resolve_columns(frame: pd.DataFrame) -> tuple[str, str]:
    true_col = next(
        (column for column in ("true_label", "rotulo_manual") if column in frame.columns),
        None,
    )
    pred_col = next(
        (
            column
            for column in ("predicted_label", "rotulo_finbert")
            if column in frame.columns
        ),
        None,
    )
    if not true_col or not pred_col:
        raise ValueError(
            "CSV precisa de colunas de rótulo verdadeiro e predito "
            f"(encontradas: {list(frame.columns)})."
        )
    return true_col, pred_col


def evaluate_predictions_frame(frame: pd.DataFrame) -> dict[str, float | int | str]:
    true_col, pred_col = _resolve_columns(frame)
    labeled = frame[
        frame[true_col].astype(str).str.strip().ne("")
        & frame[true_col].notna()
    ].copy()
    if labeled.empty:
        raise ValueError("Nenhuma linha com rótulo de referência preenchido.")

    labeled["true_norm"] = labeled[true_col].map(_normalize_label)
    labeled["pred_norm"] = labeled[pred_col].map(_normalize_label)
    valid = labeled[
        labeled["true_norm"].notna() & labeled["pred_norm"].notna()
    ]
    if valid.empty:
        raise ValueError("Nenhuma linha com rótulos normalizáveis.")

    y_true = valid["true_norm"].tolist()
    y_pred = valid["pred_norm"].tolist()
    labels = sorted(set(y_true) | set(y_pred))
    kappa = float(cohen_kappa_score(y_true, y_pred, labels=labels))
    accuracy = float(accuracy_score(y_true, y_pred))
    matrix = confusion_matrix(y_true, y_pred, labels=labels)

    return {
        "n_labeled": len(valid),
        "accuracy": accuracy,
        "cohen_kappa": kappa,
        "labels": labels,
        "confusion_matrix": matrix,
        "true_column": true_col,
        "predicted_column": pred_col,
    }


def evaluate_predictions_csv(predictions_path: Path) -> dict[str, float | int | str]:
    return evaluate_predictions_frame(pd.read_csv(predictions_path))


def format_evaluation_report(metrics: dict[str, float | int | str]) -> str:
    labels = metrics["labels"]
    matrix = metrics["confusion_matrix"]
    header = " | ".join(["", *labels])
    separator = " | ".join(["---"] * (len(labels) + 1))
    rows = [header, separator]
    for index, label in enumerate(labels):
        row_values = " | ".join(str(value) for value in matrix[index])
        rows.append(f"{label} | {row_values}")

    return "\n".join(
        [
            "# Relatório de concordância classificador × rótulo",
            "",
            f"- Amostra: {metrics['n_labeled']}",
            f"- Acurácia: {metrics['accuracy']:.1%}",
            f"- Cohen's kappa: {metrics['cohen_kappa']:.3f}",
            f"- Colunas: `{metrics['true_column']}` vs `{metrics['predicted_column']}`",
            "",
            "## Matriz de confusão",
            "",
            "\n".join(rows),
            "",
        ]
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Acurácia e kappa entre rótulos de referência e predições."
    )
    parser.add_argument(
        "--predictions",
        required=True,
        help="CSV com true_label/rotulo_manual e predicted_label/rotulo_finbert.",
    )
    parser.add_argument(
        "--report",
        help="Caminho opcional para salvar relatório Markdown.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    metrics = evaluate_predictions_csv(Path(args.predictions))
    print(
        f"Acurácia: {metrics['accuracy']:.1%} | "
        f"kappa: {metrics['cohen_kappa']:.3f} "
        f"({metrics['n_labeled']} rotulados)"
    )
    if args.report:
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(format_evaluation_report(metrics), encoding="utf-8")
        print(f"Relatório salvo em {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
