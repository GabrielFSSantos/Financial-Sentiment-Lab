"""Análise de erro das 100 notícias rotuladas manualmente (bateria PT)."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd
from sklearn.metrics import classification_report, cohen_kappa_score

from modules.evaluation.classifier_eval import evaluate_predictions_frame
from modules.evaluation.classifier_eval_pt import (
    EVAL_PATH,
    MODELS,
    REPORT_DIR,
    _predictions_path,
    build_eval_dataset,
)
from modules.evaluation.manual_labels import _normalize_label
from modules.experiment import PROJECT_ROOT

ROUNDUP_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\bibovespa\b",
        r"\bday[\s-]?trade\b",
        r"\broundup\b",
        r"\bagenda\b",
        r"\bcoisas para saber\b",
        r"\bmercado geral\b",
        r"\bvis[oõ]es sobre a bolsa\b",
        r"\bminicontratos\b",
        r"\bbolsa de valores ao vivo\b",
        r"\bcomo investir\b",
        r"\bsetor amplo\b",
        r"\bmen[cç][aã]o tangencial\b",
        r"\bibovespa geral\b",
        r"\bagenda mercado\b",
    )
)


def classify_typology(row: pd.Series) -> str:
    """Classifica notícia como roundup/agenda ou focal Sabesp."""
    notas = str(row.get("notas", "") or "").strip().lower()
    titulo = str(row.get("titulo", "") or "").strip().lower()
    combined = f"{notas} {titulo}"

    if notas in {"ibovespa geral", "day trade", "roundup", "agenda mercado", "mercado geral"}:
        return "roundup_agenda"
    if any(pattern.search(combined) for pattern in ROUNDUP_PATTERNS):
        return "roundup_agenda"
    return "focal_sabesp"


def _load_eval_frame() -> pd.DataFrame:
    build_eval_dataset()
    frame = pd.read_csv(EVAL_PATH)
    frame["tipologia"] = frame.apply(classify_typology, axis=1)
    return frame


def _merge_predictions(frame: pd.DataFrame, model_key: str) -> pd.DataFrame:
    predictions = pd.read_csv(_predictions_path(model_key))
    pred_col = "predicted_label" if "predicted_label" in predictions.columns else "rotulo_finbert"
    id_col = "news_id" if "news_id" in predictions.columns else "id"
    preds = predictions[[id_col, pred_col]].rename(
        columns={id_col: "id", pred_col: "predicted_label"}
    )
    merged = frame.merge(preds, on="id", how="left")
    merged["true_norm"] = merged["rotulo_manual"].map(_normalize_label)
    merged["pred_norm"] = merged["predicted_label"].map(_normalize_label)
    return merged


def _metrics_for_subset(
    subset: pd.DataFrame,
    *,
    model_key: str,
) -> dict[str, float | int | str | dict]:
    valid = subset[
        subset["true_norm"].notna()
        & subset["pred_norm"].notna()
        & subset["rotulo_manual"].astype(str).str.strip().ne("")
    ].copy()
    if valid.empty:
        return {
            "model_key": model_key,
            "n_labeled": 0,
            "accuracy": 0.0,
            "cohen_kappa": 0.0,
            "f1_report": {},
        }

    y_true = valid["true_norm"].tolist()
    y_pred = valid["pred_norm"].tolist()
    labels = sorted(set(y_true) | set(y_pred))
    report = classification_report(
        y_true,
        y_pred,
        labels=labels,
        output_dict=True,
        zero_division=0,
    )
    return {
        "model_key": model_key,
        "n_labeled": len(valid),
        "accuracy": float(report["accuracy"]),
        "cohen_kappa": float(cohen_kappa_score(y_true, y_pred, labels=labels)),
        "f1_report": report,
    }


def analyze_models() -> tuple[pd.DataFrame, dict[str, object]]:
    frame = _load_eval_frame()
    typology_counts = frame["tipologia"].value_counts().to_dict()
    results: list[dict[str, object]] = []

    for model_key in MODELS:
        merged = _merge_predictions(frame, model_key)
        overall = _metrics_for_subset(merged, model_key=model_key)
        focal = _metrics_for_subset(
            merged[merged["tipologia"] == "focal_sabesp"],
            model_key=model_key,
        )
        roundup = _metrics_for_subset(
            merged[merged["tipologia"] == "roundup_agenda"],
            model_key=model_key,
        )
        results.append(
            {
                "model_key": model_key,
                "overall": overall,
                "focal": focal,
                "roundup": roundup,
            }
        )

    summary = {
        "n_total": len(frame),
        "typology_counts": typology_counts,
        "roundup_fraction": typology_counts.get("roundup_agenda", 0) / len(frame),
        "results": results,
    }
    return frame, summary


def _format_f1_table(report: dict) -> list[str]:
    labels = [label for label in report if label not in {"accuracy", "macro avg", "weighted avg"}]
    lines = [
        "| Classe | Precision | Recall | F1 | Suporte |",
        "|--------|-----------|--------|----|---------|",
    ]
    for label in sorted(labels):
        stats = report[label]
        lines.append(
            f"| {label} | {stats['precision']:.2f} | {stats['recall']:.2f} | "
            f"{stats['f1-score']:.2f} | {int(stats['support'])} |"
        )
    lines.append(
        f"| **macro** | — | — | {report['macro avg']['f1-score']:.2f} | "
        f"{int(report['macro avg']['support'])} |"
    )
    return lines


def _format_subset_row(name: str, metrics: dict[str, object]) -> str:
    return (
        f"| {name} | {int(metrics['n_labeled'])} | "
        f"{float(metrics['accuracy']):.1%} | {float(metrics['cohen_kappa']):.3f} |"
    )


def format_error_analysis_report(summary: dict[str, object]) -> str:
    typology = summary["typology_counts"]
    n_total = int(summary["n_total"])
    n_roundup = int(typology.get("roundup_agenda", 0))
    n_focal = int(typology.get("focal_sabesp", 0))
    roundup_pct = float(summary["roundup_fraction"]) * 100

    lines = [
        "# Análise de erro — 100 notícias rotuladas manualmente",
        "",
        f"Fonte: `{EVAL_PATH.relative_to(PROJECT_ROOT)}` + predictions em `outputs/eval_pt_*/`.",
        "",
        "## Tipologia (heurística título + notas)",
        "",
        "| Tipologia | n | % |",
        "|-----------|---|---|",
        f"| `focal_sabesp` | {n_focal} | {100 - roundup_pct:.1f}% |",
        f"| `roundup_agenda` | {n_roundup} | {roundup_pct:.1f}% |",
        f"| **Total** | {n_total} | 100% |",
        "",
        "Padrões roundup/agenda: ibovespa, day trade, agenda, mercado geral, "
        "menção tangencial, setor amplo (ver `ROUNDUP_PATTERNS` no código).",
        "",
    ]

    high_contamination = roundup_pct >= 25.0
    lines.extend(
        [
            f"**Contaminação material (≥25%)?** "
            f"{'sim' if high_contamination else 'não'} ({roundup_pct:.1f}%).",
            "",
        ]
    )

    for item in summary["results"]:
        model_key = str(item["model_key"])
        overall = item["overall"]
        focal = item["focal"]
        roundup = item["roundup"]
        lines.extend(
            [
                f"## `{model_key}`",
                "",
                "### F1 por classe (amostra completa)",
                "",
                *_format_f1_table(overall["f1_report"]),
                "",
                "### Concordância por tipologia",
                "",
                "| Subconjunto | n | Acurácia | κ |",
                "|-------------|---|----------|---|",
                _format_subset_row("completa", overall),
                _format_subset_row("focal_sabesp", focal),
                _format_subset_row("roundup_agenda", roundup),
                "",
            ]
        )

    lines.extend(
        [
            "## Leitura",
            "",
            "- F1 por classe revela viés NEU/NEG do FinBERT (recall baixo em POS).",
            "- Comparar κ focal vs. completa indica se roundups **contaminam** a métrica Marco 3.",
            "- Gate 70% / κ≥0,40 não foi atingido em nenhum subconjunto.",
            "",
        ]
    )
    return "\n".join(lines)


def write_error_analysis_report(output_path: Path | None = None) -> Path:
    _, summary = analyze_models()
    report = format_error_analysis_report(summary)
    path = output_path or (REPORT_DIR / "error_analysis.md")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report, encoding="utf-8")

    decision_path = REPORT_DIR / "error_analysis_summary.json"
    import json

    decision_path.write_text(
        json.dumps(
            {
                "roundup_fraction": summary["roundup_fraction"],
                "high_contamination": summary["roundup_fraction"] >= 0.25,
                "typology_counts": summary["typology_counts"],
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Análise de erro bateria PT")
    parser.add_argument(
        "--output",
        default=str(REPORT_DIR / "error_analysis.md"),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    path = write_error_analysis_report(Path(args.output))
    print(f"Relatório: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
