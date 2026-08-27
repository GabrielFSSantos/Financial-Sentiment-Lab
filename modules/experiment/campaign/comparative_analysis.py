"""Análise comparativa da campanha Sabesp e gate para scrape pré-evento."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from modules.experiment import PROJECT_ROOT


def _gate_decision(manifest: dict) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    passes = False

    for run in manifest.get("runs", []):
        if run.get("run_id") == "sabesp_r0_baseline":
            continue
        win_rate = (run.get("metrics_summary") or {}).get("win_rate")
        if win_rate is not None and win_rate >= 0.40:
            passes = True
            reasons.append(
                f"{run['run_id']}: win_rate {win_rate:.1%} ≥ 40%"
            )

    manual_report = (
        PROJECT_ROOT / "outputs" / "campaigns" / "sabesp_2026" / "manual_label_report.md"
    )
    if manual_report.is_file():
        text = manual_report.read_text(encoding="utf-8")
        if "Acurácia:" in text:
            for line in text.splitlines():
                if line.startswith("- Acurácia:"):
                    pct = float(line.split(":")[1].strip().rstrip("%")) / 100
                    if pct >= 0.70:
                        reasons.append(f"FinBERT manual accuracy {pct:.1%} ≥ 70%")
                    break

    return passes, reasons


def build_report(manifest: dict) -> str:
    lines = [
        "# Análise comparativa — campanha Sabesp 2026",
        "",
        "## Resumo por run",
        "",
        "| Run | α | Equação | Win rate | Status |",
        "|-----|---|---------|----------|--------|",
    ]

    for run in manifest.get("runs", []):
        metrics = run.get("metrics_summary") or {}
        win_rate = metrics.get("win_rate")
        win_str = f"{win_rate:.1%}" if win_rate is not None else "—"
        lines.append(
            f"| {run['run_id']} | {run.get('alpha', '—')} | {run.get('equation', '—')} "
            f"| {win_str} | {run.get('status', 'pending')} |"
        )

    lines.extend(["", "## Interpretação por eixo", ""])
    baseline = next(
        (r for r in manifest.get("runs", []) if r.get("run_id") == "sabesp_r0_baseline"),
        None,
    )
    baseline_rate = (
        (baseline.get("metrics_summary") or {}).get("win_rate") if baseline else None
    )

    for run in manifest.get("runs", []):
        if run.get("run_id") == "sabesp_r0_baseline":
            continue
        delta = run.get("delta_vs_baseline") or {}
        lines.append(f"### {run['run_id']}")
        lines.append(f"- Hipótese: {run.get('hypothesis', '')}")
        if baseline_rate is not None:
            rate = (run.get("metrics_summary") or {}).get("win_rate")
            if rate is not None:
                lines.append(f"- Win rate: {rate:.1%} (R0: {baseline_rate:.1%})")
        if delta:
            lines.append(f"- Delta vs R0: {delta}")
        lines.append("")

    passes, reasons = _gate_decision(manifest)
    decision = (
        "AVANÇAR com coleta pré-evento (mai–out/2022)"
        if passes
        else "NÃO AVANÇAR — priorizar reformulação da equação/rotulagem antes de nova coleta"
    )
    lines.extend(
        [
            "## Gate scrape pré-evento (mai–out/2022)",
            "",
            f"**Decisão:** {decision}.",
            "",
        ]
    )
    if reasons:
        lines.append("Condições atendidas:")
        for reason in reasons:
            lines.append(f"- {reason}")
    else:
        lines.append("_Nenhuma condição de gate atendida._")

    lines.extend(
        [
            "",
            "## Limitações",
            "",
            "- Evento único (privatização Sabesp)",
            "- N semanal ~26 pontos na janela",
            "- Correlação ≠ causalidade",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    report = build_report(manifest)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
    print(f"Relatório: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
