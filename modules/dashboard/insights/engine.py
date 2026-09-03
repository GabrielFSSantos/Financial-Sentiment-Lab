"""Motor de insights baseado em regras."""

from __future__ import annotations

from typing import Any

from modules.dashboard.insights.rules import (
    ACCURACY_GATE,
    CONCENTRATION_THRESHOLD,
    KAPPA_GATE,
    SIGNIFICANT_WINS_LOW,
    WIN_RATE_GATE,
    WIN_RATE_IMPROVEMENT_PP,
    Insight,
    InsightLevel,
)


def generate(context: dict[str, Any]) -> list[Insight]:
    insights: list[Insight] = []
    page = context.get("page", "")

    if page == "overview":
        insights.extend(_overview_insights(context))
    elif page == "datasets":
        insights.extend(_dataset_insights(context))
    elif page == "runs":
        insights.extend(_run_insights(context))
    elif page == "compare":
        insights.extend(_compare_insights(context))
    elif page == "experiments":
        insights.extend(_experiment_insights(context))
    elif page == "research":
        insights.extend(_research_insights(context))
    elif page == "models":
        insights.extend(_model_insights(context))
    elif page == "trail":
        insights.extend(_trail_insights(context))

    return insights


def _overview_insights(ctx: dict[str, Any]) -> list[Insight]:
    out: list[Insight] = []
    if ctx.get("total_news"):
        out.append(Insight(f"Base com {ctx['total_news']:,} notícias disponíveis.".replace(",", "."), InsightLevel.INFO))
    if ctx.get("last_run"):
        out.append(Insight(f"Última execução: {ctx['last_run']}.", InsightLevel.INFO))
    best = ctx.get("best_campaign_run")
    baseline = ctx.get("baseline_win_rate")
    if best and baseline is not None:
        best_rate = best.get("win_rate")
        if best_rate is not None and best_rate - baseline >= WIN_RATE_IMPROVEMENT_PP:
            out.append(
                Insight(
                    f"{best.get('run_id')} melhorou win rate para {best_rate:.1%} "
                    f"(baseline {baseline:.1%}).",
                    InsightLevel.SUCCESS,
                )
            )
    return out


def _dataset_insights(ctx: dict[str, Any]) -> list[Insight]:
    out: list[Insight] = []
    for alert in ctx.get("alerts") or []:
        out.append(Insight(alert, InsightLevel.WARNING))
    gaps = ctx.get("gaps") or []
    if gaps:
        out.append(
            Insight(
                f"Há {len(gaps)} período(s) sem notícias na série temporal.",
                InsightLevel.WARNING,
            )
        )
    by_company = ctx.get("top_company_share")
    if by_company and by_company > CONCENTRATION_THRESHOLD:
        out.append(
            Insight(
                f"A empresa líder concentra {by_company:.0%} das notícias.",
                InsightLevel.WARNING,
            )
        )
    return out


def _run_insights(ctx: dict[str, Any]) -> list[Insight]:
    out: list[Insight] = []
    if not ctx.get("has_research"):
        out.append(
            Insight(
                "Esta run não possui research — execute `./scripts/run_research.sh --run-id <id>`.",
                InsightLevel.WARNING,
            )
        )
    if ctx.get("hypothesis"):
        out.append(Insight(f"Hipótese: {ctx['hypothesis']}", InsightLevel.INFO))
    delta = ctx.get("win_rate_delta")
    if delta is not None:
        level = InsightLevel.SUCCESS if delta > 0 else InsightLevel.DANGER if delta < 0 else InsightLevel.INFO
        out.append(Insight(f"Win rate {delta:+.1%} vs baseline.", level))
    return out


def _compare_insights(ctx: dict[str, Any]) -> list[Insight]:
    out: list[Insight] = []
    deltas = ctx.get("win_rate_deltas") or []
    for item in deltas:
        delta = item.get("delta")
        if delta is None:
            continue
        if delta >= WIN_RATE_IMPROVEMENT_PP:
            out.append(
                Insight(
                    f"{item['run_b']} melhorou {delta:+.1%} vs {item['run_a']}.",
                    InsightLevel.SUCCESS,
                )
            )
        elif delta <= -WIN_RATE_IMPROVEMENT_PP:
            out.append(
                Insight(
                    f"{item['run_b']} piorou {delta:+.1%} vs {item['run_a']}.",
                    InsightLevel.DANGER,
                )
            )
    return out


def _experiment_insights(ctx: dict[str, Any]) -> list[Insight]:
    out: list[Insight] = []
    best = ctx.get("best_run_id")
    best_rate = ctx.get("best_win_rate")
    if best and best_rate is not None:
        out.append(
            Insight(
                f"Melhor run da campanha: {best} com win rate {best_rate:.1%}.",
                InsightLevel.SUCCESS if best_rate >= WIN_RATE_GATE else InsightLevel.INFO,
            )
        )
    if best_rate is not None and best_rate >= WIN_RATE_GATE:
        out.append(
            Insight("Gate de coleta pré-evento atendido (win rate ≥ 40%).", InsightLevel.SUCCESS)
        )
    return out


def _research_insights(ctx: dict[str, Any]) -> list[Insight]:
    out: list[Insight] = []
    if ctx.get("classifier_gate_failed"):
        out.append(
            Insight(
                "Classificador não passou no gate κ — resultados de research são exploratórios.",
                InsightLevel.WARNING,
            )
        )
    overlap = ctx.get("overlap_days")
    if overlap is not None and overlap < 30:
        out.append(
            Insight(
                f"Apenas {overlap} pontos de overlap — amostra pequena para inferência forte.",
                InsightLevel.WARNING,
            )
        )
    win_rate = ctx.get("win_rate")
    if win_rate is not None:
        if win_rate < WIN_RATE_GATE:
            out.append(
                Insight(
                    f"Win rate {win_rate:.1%} abaixo do gate exploratório ({WIN_RATE_GATE:.0%}).",
                    InsightLevel.WARNING,
                )
            )
        else:
            out.append(Insight(f"Win rate ITI vs baselines: {win_rate:.1%}.", InsightLevel.SUCCESS))
    sig = ctx.get("significant_wins")
    if sig is not None and sig <= SIGNIFICANT_WINS_LOW:
        out.append(
            Insight(
                f"Apenas {sig} vitória(s) significativa(s) — sinal estatístico fraco.",
                InsightLevel.WARNING,
            )
        )
    return out


def _model_insights(ctx: dict[str, Any]) -> list[Insight]:
    out: list[Insight] = []
    if not ctx.get("has_labels"):
        out.append(
            Insight(
                "Dataset sem rótulos verdadeiros — métricas supervisionadas indisponíveis.",
                InsightLevel.WARNING,
            )
        )
    kappa = ctx.get("kappa")
    if kappa is not None and kappa < KAPPA_GATE:
        out.append(
            Insight(
                f"FinBERT κ={kappa:.3f} abaixo do gate ({KAPPA_GATE:.2f}) — ITI condicionado.",
                InsightLevel.DANGER,
            )
        )
    accuracy = ctx.get("accuracy")
    if accuracy is not None and accuracy < ACCURACY_GATE:
        out.append(
            Insight(
                f"Acurácia {accuracy:.1%} abaixo do gate ({ACCURACY_GATE:.0%}).",
                InsightLevel.WARNING,
            )
        )
    dist = ctx.get("dominant_class")
    if dist:
        out.append(Insight(f"Classe predominante nas previsões: {dist}.", InsightLevel.INFO))
    return out


def _trail_insights(ctx: dict[str, Any]) -> list[Insight]:
    out: list[Insight] = []
    if ctx.get("classifier_gate_failed"):
        out.append(
            Insight(
                "Trilha F5: gate do classificador não atendido — veja relatório κ.",
                InsightLevel.WARNING,
            )
        )
    total = ctx.get("total_runs")
    if total is not None:
        out.append(Insight(f"{total} run(s) disponível(is) no dashboard.", InsightLevel.INFO))
    return out
