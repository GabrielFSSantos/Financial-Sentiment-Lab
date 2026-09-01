"""Bateria PT: rótulos manuais × FinBERT / BERTweet / BERTimbau."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import pandas as pd

from modules.evaluation.classifier_eval import (
    evaluate_predictions_csv,
    format_evaluation_report,
)
from modules.experiment import PROJECT_ROOT

MANUAL_PATH = PROJECT_ROOT / "data/saneamento_corpus/rotulos_manual_100.csv"
CORPUS_PATH = PROJECT_ROOT / "data/saneamento_corpus/noticias_strict_sabesp.csv"
EVAL_PATH = PROJECT_ROOT / "data/saneamento_corpus/rotulos_manual_100_eval.csv"
REPORT_DIR = PROJECT_ROOT / "outputs/campaigns/classifier_eval_pt"
CLASSIFIER_CONFIG = (
    PROJECT_ROOT / "configs/campaigns/trilha_b/classifier_diag.yaml"
)
R1_CONFIG = (
    PROJECT_ROOT / "configs/campaigns/sabesp_2026/experiments/r1_alpha070.yaml"
)
RESEARCH_CONFIG = (
    PROJECT_ROOT / "configs/campaigns/sabesp_2026/research_weekly.yaml"
)

MODELS: tuple[str, ...] = (
    "finbert_ptbr",
    "bertweet_pt_sentiment",
    "bertimbau_sentiment",
)

GATE_ACCURACY = 0.70
GATE_KAPPA = 0.40


def build_eval_dataset(
    *,
    manual_path: Path = MANUAL_PATH,
    corpus_path: Path = CORPUS_PATH,
    output_path: Path = EVAL_PATH,
) -> pd.DataFrame:
    manual = pd.read_csv(manual_path)
    corpus = pd.read_csv(corpus_path)
    if "news_id" not in manual.columns:
        raise ValueError("rotulos_manual_100.csv precisa da coluna news_id.")
    if "id" not in corpus.columns:
        raise ValueError("Corpus strict precisa da coluna id.")

    merged = manual.merge(
        corpus,
        left_on="news_id",
        right_on="id",
        how="left",
        suffixes=("", "_corpus"),
    )
    missing = merged["noticia"].isna().sum()
    if missing:
        raise ValueError(
            f"{missing} news_id da amostra manual sem match no corpus strict."
        )

    merged["id"] = merged["news_id"]
    if "titulo_corpus" in merged.columns:
        merged["titulo"] = merged["titulo"].fillna(merged["titulo_corpus"])

    columns = [
        "id",
        "data",
        "empresa",
        "setor",
        "ticker",
        "titulo",
        "noticia",
        "fonte",
        "url",
        "rotulo_manual",
        "rotulo_finbert",
        "notas",
    ]
    for column in columns:
        if column not in merged.columns:
            merged[column] = ""
    frame = merged[columns].copy()
    labeled = frame[frame["rotulo_manual"].astype(str).str.strip() != ""]
    if labeled.empty:
        raise ValueError("Nenhum rotulo_manual preenchido na amostra.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_path, index=False)
    return output_path


def _run_id_for_model(model_key: str) -> str:
    return f"eval_pt_{model_key}"


def _predictions_path(model_key: str) -> Path:
    return (
        PROJECT_ROOT
        / "outputs"
        / _run_id_for_model(model_key)
        / "models"
        / model_key
        / "rotulos_manual_pt_100"
        / "predictions.csv"
    )


def run_inference(model_key: str, *, skip_setup: bool = True) -> Path:
    run_id = _run_id_for_model(model_key)
    cmd = [
        str(PROJECT_ROOT / "scripts/run_experiment.sh"),
    ]
    if skip_setup:
        cmd.append("--skip-setup")
    cmd.extend(
        [
            "--experiment-config",
            str(CLASSIFIER_CONFIG.relative_to(PROJECT_ROOT)),
            "--run-id",
            run_id,
            "--dataset",
            "rotulos_manual_pt_100",
            "--model",
            model_key,
        ]
    )
    subprocess.run(cmd, cwd=PROJECT_ROOT, check=True)
    predictions = _predictions_path(model_key)
    if not predictions.is_file():
        raise FileNotFoundError(f"Predictions ausentes: {predictions}")
    return predictions


def evaluate_model(model_key: str) -> dict[str, float | int | str]:
    predictions = _predictions_path(model_key)
    if not predictions.is_file():
        predictions = run_inference(model_key)
    metrics = evaluate_predictions_csv(predictions)
    metrics["model_key"] = model_key
    report_path = REPORT_DIR / f"{model_key}_report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(format_evaluation_report(metrics), encoding="utf-8")
    return metrics


def passes_gate(metrics: dict[str, float | int | str]) -> bool:
    accuracy = float(metrics["accuracy"])
    kappa = float(metrics["cohen_kappa"])
    return accuracy >= GATE_ACCURACY or kappa >= GATE_KAPPA


def pick_winner(results: list[dict[str, float | int | str]]) -> str | None:
    passing = [item for item in results if passes_gate(item)]
    if not passing:
        return None
    passing.sort(
        key=lambda item: (float(item["cohen_kappa"]), float(item["accuracy"])),
        reverse=True,
    )
    return str(passing[0]["model_key"])


def write_comparative_report(results: list[dict[str, float | int | str]]) -> Path:
    lines = [
        "# Bateria PT — rótulos manuais (100 notícias)",
        "",
        f"Gate: acurácia ≥ {GATE_ACCURACY:.0%} **ou** κ ≥ {GATE_KAPPA:.2f}.",
        "",
        "| Modelo | Acurácia | κ | Passa gate? |",
        "|--------|----------|---|-------------|",
    ]
    for item in results:
        model_key = str(item["model_key"])
        gate = "sim" if passes_gate(item) else "não"
        lines.append(
            f"| `{model_key}` | {float(item['accuracy']):.1%} | "
            f"{float(item['cohen_kappa']):.3f} | {gate} |"
        )

    winner = pick_winner(results)
    lines.extend(["", "## Decisão", ""])
    if winner:
        lines.append(
            f"Modelo vencedor para ITI condicional: **`{winner}`** "
            f"(melhor κ entre os que passam o gate)."
        )
    else:
        lines.append(
            "Nenhum modelo passou o gate — **não** rodar ITI com controles PT."
        )

    path = REPORT_DIR / "comparative_report.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")

    summary = {
        "gate_accuracy": GATE_ACCURACY,
        "gate_kappa": GATE_KAPPA,
        "models": [
            {
                "model_key": str(item["model_key"]),
                "accuracy": float(item["accuracy"]),
                "cohen_kappa": float(item["cohen_kappa"]),
                "passes_gate": passes_gate(item),
            }
            for item in results
        ],
        "winner": winner,
    }
    (REPORT_DIR / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return path


def run_battery(*, skip_setup: bool = True) -> list[dict[str, float | int | str]]:
    build_eval_dataset()
    results: list[dict[str, float | int | str]] = []
    for model_key in MODELS:
        if not _predictions_path(model_key).is_file():
            run_inference(model_key, skip_setup=skip_setup)
        results.append(evaluate_model(model_key))
    write_comparative_report(results)
    return results


def run_conditional_iti(winner: str, *, skip_setup: bool = True) -> None:
    run_id = f"sabesp_ctrl_event_r1_{winner}"
    cmd_exp = [
        str(PROJECT_ROOT / "scripts/run_experiment.sh"),
    ]
    if skip_setup:
        cmd_exp.append("--skip-setup")
    cmd_exp.extend(
        [
            "--experiment-config",
            str(R1_CONFIG.relative_to(PROJECT_ROOT)),
            "--run-id",
            run_id,
            "--dataset",
            "saneamento_sabesp_strict_event",
            "--model",
            winner,
        ]
    )
    subprocess.run(cmd_exp, cwd=PROJECT_ROOT, check=True)

    cmd_res = [
        str(PROJECT_ROOT / "scripts/run_research.sh"),
        "--run-id",
        run_id,
        "--dataset",
        "saneamento_sabesp_strict_event",
        "--model",
        winner,
        "--config",
        str(RESEARCH_CONFIG.relative_to(PROJECT_ROOT)),
    ]
    subprocess.run(cmd_res, cwd=PROJECT_ROOT, check=True)
    print(f"ITI condicional concluído: outputs/{run_id}/")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bateria PT vs rótulos manuais")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("prepare", help="Gera rotulos_manual_100_eval.csv")
    sub.add_parser("run", help="Inferência + κ para os 3 modelos PT")
    sub.add_parser(
        "iti-if-gate",
        help="Roda ITI evento só se algum modelo passar o gate",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "prepare":
        path = build_eval_dataset()
        print(f"Dataset eval: {path} ({len(pd.read_csv(path))} linhas)")
        return 0
    if args.command == "run":
        results = run_battery()
        for item in results:
            print(
                f"{item['model_key']}: "
                f"{float(item['accuracy']):.1%} | κ={float(item['cohen_kappa']):.3f}"
            )
        print(f"Relatório: {REPORT_DIR / 'comparative_report.md'}")
        return 0
    if args.command == "iti-if-gate":
        summary_path = REPORT_DIR / "summary.json"
        if not summary_path.is_file():
            run_battery()
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        winner = summary.get("winner")
        if not winner:
            print("Gate não atingido — ITI condicional omitido.")
            return 0
        run_conditional_iti(str(winner))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
