"""Pipeline fino ITI-v2: índices, lock, avaliação e relatório (P07/P11)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
import yaml

from modules.experiment import PROJECT_ROOT
from modules.experiment.campaign.iti_v2_protocol import load_iti_v2_protocol, write_resolved_protocol
from modules.experiment.campaign.iti_v2_acceptance import format_report, run_acceptance
from modules.experiment.campaign.iti_v2_inference import run_iti_v2_inference
from modules.experiment.campaign.iti_v2_statistics import (
    compute_horizon_metrics,
    metrics_to_dataframe,
)
from modules.experiment.campaign.protocol_lock import (
    build_protocol_lock,
    require_protocol_lock,
    write_protocol_lock,
)
from modules.experiment.indexing.iti_v2 import build_daily_iti_v2_frame, build_weekly_signals
from modules.market.config.loader import load_market_configuration
from modules.market.loader import load_market_prices
from modules.research.config.analysis_plan import load_analysis_plan
from modules.research.io.alignment_audit import align_iti_v2_weekly_to_market


def _default_protocol_path() -> Path:
    return PROJECT_ROOT / "configs/campaigns/iti_v2/protocol.yaml"


def _default_analysis_plan_path() -> Path:
    return PROJECT_ROOT / "configs/campaigns/iti_v2/analysis_plan.yaml"


def run_dir_for(run_id: str) -> Path:
    return PROJECT_ROOT / "outputs/campaigns/iti_v2" / run_id


def default_corpus_dir() -> Path:
    return PROJECT_ROOT / "outputs/corpus_inventory/iti_v2_p02"


def _load_company_to_ticker() -> dict[str, str]:
    path = PROJECT_ROOT / "configs/campaigns/iti_v2/research_weekly.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return dict(data.get("mapping", {}).get("company_to_ticker", {}))


def _primary_signal_column(protocol: object) -> str:
    primary = int(protocol.raw.get("index", {}).get("primary_half_life_days", 7))
    return f"iti_v2_h{primary}"


def _normalize_predictions_frame(frame: pd.DataFrame) -> pd.DataFrame:
    work = frame.copy()
    if "company_id" not in work.columns and "company" in work.columns:
        work["company_id"] = work["company"]
    if "news_id" not in work.columns and "id" in work.columns:
        work["news_id"] = work["id"]
    for col in ("p_negative", "p_neutral", "p_positive"):
        if col not in work.columns and col.replace("p_", "prob_") in work.columns:
            work[col] = work[col.replace("p_", "prob_")]
    if "status" in work.columns:
        work = work.loc[work["status"] == "ok"].copy()
    work = work.dropna(subset=["p_negative", "p_neutral", "p_positive"])
    required = {"date", "company_id", "news_id", "p_negative", "p_neutral", "p_positive"}
    missing = required - set(work.columns)
    if missing:
        raise ValueError(f"predictions sem colunas: {sorted(missing)}")
    return work


def build_indices(
    predictions_path: Path,
    run_id: str,
    *,
    protocol_path: Path | None = None,
    analysis_plan_path: Path | None = None,
) -> dict[str, Path]:
    protocol_path = protocol_path or _default_protocol_path()
    analysis_plan_path = analysis_plan_path or _default_analysis_plan_path()
    protocol = load_iti_v2_protocol(protocol_path)
    analysis = load_analysis_plan(analysis_plan_path)

    out_dir = run_dir_for(run_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    write_resolved_protocol(protocol, out_dir)

    plan_digest = {
        "analysis_plan": str(analysis_plan_path),
        "analysis_plan_fields": analysis.to_dict(),
    }
    (out_dir / "analysis_plan_resolved.json").write_text(
        json.dumps(plan_digest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    preds = _normalize_predictions_frame(pd.read_csv(predictions_path))
    daily = build_daily_iti_v2_frame(
        preds,
        half_lives=protocol.half_life_days,
        warmup_days=protocol.warmup_days,
    )
    weekly = build_weekly_signals(
        daily,
        week_anchor=analysis.week_anchor or protocol.week_anchor,
    )

    paths = {
        "iti_daily": out_dir / "iti_daily.csv",
        "iti_weekly": out_dir / "iti_weekly_signals.csv",
        "predictions_copy": out_dir / "predictions_source.csv",
    }
    daily.to_csv(paths["iti_daily"], index=False)
    weekly.to_csv(paths["iti_weekly"], index=False)
    preds.to_csv(paths["predictions_copy"], index=False)

    manifest = {
        "run_id": run_id,
        "protocol_sha256": protocol.content_sha256,
        "index_version": protocol.index_version,
        "n_predictions": int(len(preds)),
        "artifacts": {k: str(v) for k, v in paths.items()},
    }
    (out_dir / "run_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    return paths


def lock_protocol(
    corpus_dir: Path,
    *,
    protocol_path: Path | None = None,
    analysis_plan_path: Path | None = None,
    execution_mode: str = "exploratory",
) -> Path:
    protocol_path = protocol_path or _default_protocol_path()
    analysis_plan_path = analysis_plan_path or _default_analysis_plan_path()
    payload = build_protocol_lock(
        corpus_dir=corpus_dir,
        protocol_path=protocol_path,
        analysis_plan_path=analysis_plan_path,
        execution_mode=execution_mode,
    )
    return write_protocol_lock(corpus_dir / "protocol_lock.json", payload)


def evaluate_run(
    run_id: str,
    *,
    corpus_dir: Path | None = None,
    protocol_path: Path | None = None,
    analysis_plan_path: Path | None = None,
) -> dict[str, Path]:
    corpus_dir = corpus_dir or default_corpus_dir()
    lock = require_protocol_lock(corpus_dir)
    protocol_path = protocol_path or _default_protocol_path()
    analysis_plan_path = analysis_plan_path or _default_analysis_plan_path()
    protocol = load_iti_v2_protocol(protocol_path)
    analysis = load_analysis_plan(analysis_plan_path)

    out_dir = run_dir_for(run_id)
    weekly_path = out_dir / "iti_weekly_signals.csv"
    if not weekly_path.is_file():
        raise FileNotFoundError(
            f"Execute indices antes de evaluate: {weekly_path} ausente"
        )

    weekly = pd.read_csv(weekly_path)
    signal_col = _primary_signal_column(protocol)
    market = load_market_prices(load_market_configuration(project_root=PROJECT_ROOT))
    panel, audit = align_iti_v2_weekly_to_market(
        weekly,
        market,
        company_to_ticker=_load_company_to_ticker(),
        horizons=tuple(analysis.horizons_weeks),
        signal_column=signal_col,
    )

    paths = {
        "aligned_panel": out_dir / "aligned_panel.csv",
        "alignment_audit": out_dir / "alignment_audit.csv",
        "metrics": out_dir / "metrics_primary.json",
        "metrics_inference": out_dir / "metrics_inference.json",
        "metrics_table": out_dir / "metrics_by_horizon.csv",
    }
    panel.to_csv(paths["aligned_panel"], index=False)
    audit.to_csv(paths["alignment_audit"], index=False)

    horizon_rows = compute_horizon_metrics(
        panel,
        signal_column=signal_col,
        horizons=tuple(analysis.horizons_weeks),
        plan=analysis,
    )

    split_path = corpus_dir / "split_manifest.json"
    if split_path.is_file():
        split = json.loads(split_path.read_text(encoding="utf-8"))
        holdout = split.get("external_holdout", {})
        if holdout.get("status") == "selected" and holdout.get("cutoff_date_inclusive"):
            cutoff = pd.Timestamp(holdout["cutoff_date_inclusive"])
            date_series = pd.to_datetime(
                panel.get("period_end", panel.get("date")),
                errors="coerce",
            )
            dev_panel = panel.loc[date_series < cutoff].copy()
            ho_panel = panel.loc[date_series >= cutoff].copy()
            for label, subset in (("development", dev_panel), ("holdout", ho_panel)):
                rows = compute_horizon_metrics(
                    subset,
                    signal_column=signal_col,
                    horizons=(analysis.primary_horizon_weeks,),
                    plan=analysis,
                )
                (out_dir / f"metrics_{label}.json").write_text(
                    json.dumps({"split": label, "horizons": rows}, indent=2),
                    encoding="utf-8",
                )
    metrics_table = metrics_to_dataframe(horizon_rows)
    metrics_table.to_csv(paths["metrics_table"], index=False)

    primary_row = next(
        (
            r
            for r in horizon_rows
            if r.get("horizon_weeks") == analysis.primary_horizon_weeks
        ),
        horizon_rows[0] if horizon_rows else {},
    )
    metrics: dict[str, object] = {
        "run_id": run_id,
        "protocol_lock_git": lock.get("git_commit"),
        "execution_mode": lock.get("execution_mode"),
        "metric": analysis.primary_metric,
        "horizon_weeks": analysis.primary_horizon_weeks,
        "signal_column": signal_col,
        "n_panel": int(len(panel)),
        "n_audit_rows": int(len(audit)),
        "estimate": primary_row.get("estimate"),
        "p_value": primary_row.get("p_value"),
        "p_holm": primary_row.get("p_holm"),
        "ci_low": primary_row.get("ci_low"),
        "ci_high": primary_row.get("ci_high"),
        "status": primary_row.get("status", "missing"),
        "secondary_correction": analysis.secondary_correction,
        "bootstrap_replicates": primary_row.get("n_bootstrap"),
    }

    paths["metrics"].write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    paths["metrics_inference"].write_text(
        json.dumps(
            {
                "horizons": horizon_rows,
                "analysis_plan_schema": analysis.schema_version,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (out_dir / "protocol_lock_ref.json").write_text(
        json.dumps({"corpus_dir": str(corpus_dir), "lock": lock}, indent=2),
        encoding="utf-8",
    )
    return paths


def write_run_report(run_id: str) -> Path:
    out_dir = run_dir_for(run_id)
    metrics_path = out_dir / "metrics_primary.json"
    audit_path = out_dir / "alignment_audit.csv"
    if not metrics_path.is_file():
        raise FileNotFoundError("Execute evaluate antes de report")

    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    audit = pd.read_csv(audit_path) if audit_path.is_file() else pd.DataFrame()
    dropped = int((audit["join_status"] == "dropped").sum()) if not audit.empty else 0

    lines = [
        f"# Relatório ITI-v2 — `{run_id}`",
        "",
        f"- Modo: **{metrics.get('execution_mode', 'n/d')}**",
        f"- Métrica principal: {metrics.get('metric')} (h={metrics.get('horizon_weeks')} semanas)",
        f"- Sinal: `{metrics.get('signal_column')}`",
        f"- Estimativa: {metrics.get('estimate')}",
        f"- IC 95%: [{metrics.get('ci_low')}, {metrics.get('ci_high')}]",
        f"- p (bootstrap): {metrics.get('p_value')}",
        f"- p (Holm): {metrics.get('p_holm')}",
        f"- Status: {metrics.get('status')}",
        f"- Bootstrap replicates: {metrics.get('bootstrap_replicates', 'n/d')}",
        f"- Semanas com perda no join: {dropped}",
        "",
        "_Resultado confirmatório exige holdout independente (ver split_manifest / protocol_lock)._",
    ]
    report_path = out_dir / "report.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def validate_run_artifacts(run_id: str) -> None:
    """Exige artefatos mínimos antes de marcar sucesso (P07)."""

    out_dir = run_dir_for(run_id)
    required = (
        "iti_daily.csv",
        "iti_weekly_signals.csv",
        "aligned_panel.csv",
        "alignment_audit.csv",
        "metrics_primary.json",
        "metrics_inference.json",
        "metrics_by_horizon.csv",
        "report.md",
    )
    missing = [name for name in required if not (out_dir / name).is_file()]
    if missing:
        raise FileNotFoundError(f"Artefatos incompletos em {out_dir}: {missing}")
    (out_dir / "_SUCCESS").write_text("ok\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Campanha ITI-v2")
    sub = parser.add_subparsers(dest="command", required=True)

    indices = sub.add_parser("indices", help="Gera iti_daily e sinais semanais")
    indices.add_argument("--run-id", required=True)
    indices.add_argument("--predictions", required=True, type=Path)
    indices.add_argument("--protocol", type=Path, default=None)
    indices.add_argument("--analysis-plan", type=Path, default=None)

    lock = sub.add_parser("lock-protocol", help="Congela hashes P02 + configs (P11)")
    lock.add_argument("--corpus-dir", type=Path, default=None)
    lock.add_argument("--execution-mode", default="exploratory")

    evaluate = sub.add_parser("evaluate", help="Alinha mercado + métrica principal")
    evaluate.add_argument("--run-id", required=True)
    evaluate.add_argument("--corpus-dir", type=Path, default=None)

    report = sub.add_parser("report", help="Gera report.md e _SUCCESS")
    report.add_argument("--run-id", required=True)

    infer = sub.add_parser("infer", help="Valida lock e prepara diretório de run")
    infer.add_argument("--run-id", required=True)
    infer.add_argument("--corpus-dir", type=Path, default=None)
    infer.add_argument("--limit", type=int, default=0, help="0 = corpus completo")
    infer.add_argument("--model-key", default="finbert_ptbr")

    validate = sub.add_parser("validate", help="Critérios de aceite do plano")
    validate.add_argument("--run-id", default=None)
    validate.add_argument("--corpus-dir", type=Path, default=None)

    run_all = sub.add_parser("run-all", help="prepare→lock→infer→indices→evaluate→report→validate")
    run_all.add_argument("--run-id", required=True)
    run_all.add_argument("--corpus-csv", type=Path, default=None)
    run_all.add_argument("--infer-limit", type=int, default=0)

    export = sub.add_parser("export-thesis", help="Pacote de artefatos para dissertação")
    export.add_argument("--run-id", required=True)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "indices":
        pred = args.predictions
        if not pred.is_absolute():
            pred = PROJECT_ROOT / pred
        paths = build_indices(
            pred,
            args.run_id,
            protocol_path=args.protocol,
            analysis_plan_path=args.analysis_plan,
        )
        for name, path in paths.items():
            print(f"{name}: {path}")
        return 0

    if args.command == "lock-protocol":
        corpus = args.corpus_dir or default_corpus_dir()
        if not corpus.is_absolute():
            corpus = PROJECT_ROOT / corpus
        out = lock_protocol(corpus, execution_mode=args.execution_mode)
        print(f"protocol_lock: {out}")
        return 0

    if args.command == "evaluate":
        corpus = args.corpus_dir
        paths = evaluate_run(args.run_id, corpus_dir=corpus)
        for name, path in paths.items():
            print(f"{name}: {path}")
        return 0

    if args.command == "report":
        report_path = write_run_report(args.run_id)
        validate_run_artifacts(args.run_id)
        print(f"report: {report_path}")
        return 0

    if args.command == "infer":
        corpus = args.corpus_dir or default_corpus_dir()
        if not corpus.is_absolute():
            corpus = PROJECT_ROOT / corpus
        limit = None if args.limit == 0 else int(args.limit)
        path = run_iti_v2_inference(
            args.run_id,
            corpus_dir=corpus,
            model_key=args.model_key,
            limit=limit,
        )
        print(f"predictions: {path}")
        return 0

    if args.command == "validate":
        corpus = args.corpus_dir or default_corpus_dir()
        if not corpus.is_absolute():
            corpus = PROJECT_ROOT / corpus
        ok, results = run_acceptance(corpus_dir=corpus, run_id=args.run_id)
        report = format_report(results)
        log_dir = PROJECT_ROOT / "docs/plans"
        log_dir.mkdir(parents=True, exist_ok=True)
        (log_dir / "iti_v2_acceptance_latest.md").write_text(
            report, encoding="utf-8"
        )
        print(report)
        return 0 if ok else 1

    if args.command == "export-thesis":
        run_dir = run_dir_for(args.run_id)
        export_dir = run_dir / "thesis_export"
        export_dir.mkdir(parents=True, exist_ok=True)
        names = (
            "predictions.csv",
            "iti_daily.csv",
            "iti_weekly_signals.csv",
            "aligned_panel.csv",
            "alignment_audit.csv",
            "metrics_primary.json",
            "metrics_inference.json",
            "metrics_by_horizon.csv",
            "metrics_development.json",
            "metrics_holdout.json",
            "report.md",
            "protocol_lock_ref.json",
            "run_manifest.json",
        )
        for name in names:
            src = run_dir / name
            if src.is_file():
                (export_dir / name).write_bytes(src.read_bytes())
        corpus_lock = default_corpus_dir() / "protocol_lock.json"
        if corpus_lock.is_file():
            (export_dir / "protocol_lock.json").write_bytes(
                corpus_lock.read_bytes()
            )
        print(f"thesis_export: {export_dir}")
        return 0

    if args.command == "run-all":
        from modules.datasets.corpus_prepare import run_p02_prepare

        corpus_dir = default_corpus_dir()
        csv_path = args.corpus_csv or (
            PROJECT_ROOT / "data/water_utilities_corpus/articles_strict_sabesp.csv"
        )
        if not csv_path.is_absolute():
            csv_path = PROJECT_ROOT / csv_path
        run_p02_prepare(csv_path, corpus_dir)
        lock_protocol(corpus_dir)
        limit = None if args.infer_limit == 0 else int(args.infer_limit)
        pred_path = run_iti_v2_inference(
            args.run_id,
            corpus_dir=corpus_dir,
            limit=limit,
        )
        build_indices(pred_path, args.run_id)
        evaluate_run(args.run_id, corpus_dir=corpus_dir)
        write_run_report(args.run_id)
        validate_run_artifacts(args.run_id)
        ok, results = run_acceptance(corpus_dir=corpus_dir, run_id=args.run_id)
        report = format_report(results)
        (PROJECT_ROOT / "docs/plans/iti_v2_acceptance_latest.md").write_text(
            report, encoding="utf-8"
        )
        print(report)
        return 0 if ok else 1

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
