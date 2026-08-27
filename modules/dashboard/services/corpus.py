"""Estatísticas e exploração do corpus."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from modules.dashboard.config import DEFAULT_CORPUS
from modules.dashboard.services.catalog import DatasetInfo, list_datasets


COLUMN_MAP = {
    "id": "news_id",
    "data": "date",
    "empresa": "company",
    "setor": "sector",
    "titulo": "title",
    "noticia": "text",
    "fonte": "source",
}


@dataclass
class CorpusStats:
    total: int
    companies: int
    sectors: int
    sources: int
    date_min: str | None
    date_max: str | None
    by_company: pd.DataFrame
    by_sector: pd.DataFrame
    by_source: pd.DataFrame
    time_series: pd.DataFrame
    gaps: list[dict[str, str]]
    alerts: list[str]


def _normalize_frame(frame: pd.DataFrame) -> pd.DataFrame:
    working = frame.copy()
    for old, new in COLUMN_MAP.items():
        if old in working.columns and new not in working.columns:
            working = working.rename(columns={old: new})
    if "date" in working.columns:
        working["date"] = pd.to_datetime(working["date"], errors="coerce")
    return working


def load_corpus(path: Path | None = None) -> pd.DataFrame:
    target = path or DEFAULT_CORPUS
    if not target.is_file():
        return pd.DataFrame()
    frame = pd.read_csv(target)
    return _normalize_frame(frame)


def filter_corpus(
    frame: pd.DataFrame,
    *,
    companies: list[str] | None = None,
    sectors: list[str] | None = None,
    sources: list[str] | None = None,
    date_from: pd.Timestamp | None = None,
    date_to: pd.Timestamp | None = None,
) -> pd.DataFrame:
    if frame.empty:
        return frame
    working = frame.copy()
    if companies and "company" in working.columns:
        working = working[working["company"].isin(companies)]
    if sectors and "sector" in working.columns:
        working = working[working["sector"].isin(sectors)]
    if sources and "source" in working.columns:
        working = working[working["source"].isin(sources)]
    if date_from is not None and "date" in working.columns:
        working = working[working["date"] >= date_from]
    if date_to is not None and "date" in working.columns:
        working = working[working["date"] <= date_to]
    return working


def _detect_gaps(dates: pd.Series, freq: str = "W") -> list[dict[str, str]]:
    if dates.empty:
        return []
    parsed = pd.to_datetime(dates, errors="coerce").dropna()
    if parsed.empty:
        return []
    start, end = parsed.min(), parsed.max()
    full_range = pd.date_range(start=start, end=end, freq=freq)
    present = set(parsed.dt.to_period(freq).unique())
    gaps: list[dict[str, str]] = []
    for period in full_range.to_period(freq).unique():
        if period not in present:
            gaps.append(
                {
                    "period": str(period),
                    "start": str(period.start_time.date()),
                    "end": str(period.end_time.date()),
                }
            )
    return gaps[:10]


def compute_stats(frame: pd.DataFrame, *, freq: str = "ME") -> CorpusStats:
    empty = CorpusStats(
        total=0,
        companies=0,
        sectors=0,
        sources=0,
        date_min=None,
        date_max=None,
        by_company=pd.DataFrame(),
        by_sector=pd.DataFrame(),
        by_source=pd.DataFrame(),
        time_series=pd.DataFrame(),
        gaps=[],
        alerts=["Corpus vazio ou arquivo não encontrado."],
    )
    if frame.empty:
        return empty

    by_company = (
        frame.groupby("company", dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
        if "company" in frame.columns
        else pd.DataFrame()
    )
    by_sector = (
        frame.groupby("sector", dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
        if "sector" in frame.columns
        else pd.DataFrame()
    )
    by_source = (
        frame.groupby("source", dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
        if "source" in frame.columns
        else pd.DataFrame()
    )

    time_series = pd.DataFrame()
    if "date" in frame.columns:
        time_series = (
            frame.dropna(subset=["date"])
            .set_index("date")
            .resample(freq)
            .size()
            .reset_index(name="count")
        )
        time_series.columns = ["period", "count"]

    alerts: list[str] = []
    if not by_company.empty and frame.shape[0] > 0:
        top_share = by_company.iloc[0]["count"] / frame.shape[0]
        if top_share > 0.4:
            alerts.append(
                f"{by_company.iloc[0]['company']} representa "
                f"{top_share:.0%} das notícias — concentração elevada."
            )
    if not by_source.empty and frame.shape[0] > 0:
        top_source = by_source.iloc[0]
        share = top_source["count"] / frame.shape[0]
        if share > 0.5:
            alerts.append(
                f"Fonte {top_source['source']} domina com {share:.0%} das notícias."
            )

    gaps = _detect_gaps(frame["date"]) if "date" in frame.columns else []

    date_min = str(frame["date"].min().date()) if "date" in frame.columns and frame["date"].notna().any() else None
    date_max = str(frame["date"].max().date()) if "date" in frame.columns and frame["date"].notna().any() else None

    return CorpusStats(
        total=len(frame),
        companies=frame["company"].nunique() if "company" in frame.columns else 0,
        sectors=frame["sector"].nunique() if "sector" in frame.columns else 0,
        sources=frame["source"].nunique() if "source" in frame.columns else 0,
        date_min=date_min,
        date_max=date_max,
        by_company=by_company,
        by_sector=by_sector,
        by_source=by_source,
        time_series=time_series,
        gaps=gaps,
        alerts=alerts,
    )


def company_month_heatmap(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty or "date" not in frame.columns or "company" not in frame.columns:
        return pd.DataFrame()
    working = frame.dropna(subset=["date"]).copy()
    working["month"] = working["date"].dt.to_period("M").astype(str)
    pivot = working.pivot_table(
        index="company",
        columns="month",
        values="news_id" if "news_id" in working.columns else "title",
        aggfunc="count",
        fill_value=0,
    )
    return pivot


def resolve_dataset_path(dataset: DatasetInfo | None) -> Path:
    if dataset and dataset.path.is_file():
        return dataset.path
    return DEFAULT_CORPUS
