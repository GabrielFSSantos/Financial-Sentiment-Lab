"""Testes do motor de insights."""

from __future__ import annotations

from modules.dashboard.insights import engine as insights_engine
from modules.dashboard.insights.rules import InsightLevel


def test_overview_insights_with_data() -> None:
    insights = insights_engine.generate(
        {
            "page": "overview",
            "total_news": 465,
            "last_run": "sabesp_r0_baseline",
            "best_campaign_run": {"run_id": "sabesp_r1_alpha070", "win_rate": 0.42},
            "baseline_win_rate": 0.21,
        }
    )
    assert len(insights) >= 1
    assert any(i.level == InsightLevel.SUCCESS for i in insights)


def test_dataset_concentration_alert() -> None:
    insights = insights_engine.generate(
        {
            "page": "datasets",
            "alerts": ["Sabesp representa 100% das notícias."],
            "gaps": [],
            "top_company_share": 1.0,
        }
    )
    assert len(insights) >= 1
