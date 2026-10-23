"""ITI-v2: agregação diária por empresa e memória por meia-vida (dias civis).

Funções puras, sem leitura de mercado ou retornos. O legado permanece em
``temporal_index.py`` (legacy_v1).
"""

from __future__ import annotations

import math
from typing import Literal

import numpy as np
import pandas as pd

PROB_SUM_TOLERANCE = 1e-5
HALF_LIFE_PRIMARY = 7
HALF_LIFE_SENSITIVITY = (2, 14)


class ITIv2Error(ValueError):
    """Entrada ou estado inválido para ITI-v2."""


def lambda_from_half_life(half_life_days: float) -> float:
    if half_life_days <= 0:
        raise ITIv2Error(f"meia-vida deve ser positiva, recebido {half_life_days}")
    return 2.0 ** (-1.0 / half_life_days)


def continuous_sentiment(p_positive: float, p_negative: float) -> float:
    return float(p_positive - p_negative)


def validate_probabilities(
    p_negative: float,
    p_neutral: float,
    p_positive: float,
    *,
    tolerance: float = PROB_SUM_TOLERANCE,
) -> tuple[float, float, float]:
    """Exige três probabilidades finitas em [0,1] com soma ≈ 1."""

    for name, value in (
        ("p_negative", p_negative),
        ("p_neutral", p_neutral),
        ("p_positive", p_positive),
    ):
        if value is None or (isinstance(value, float) and math.isnan(value)):
            raise ITIv2Error(f"{name} ausente ou NaN")
        if not 0.0 <= float(value) <= 1.0:
            raise ITIv2Error(f"{name} fora de [0,1]: {value}")

    total = float(p_negative) + float(p_neutral) + float(p_positive)
    if abs(total - 1.0) > tolerance:
        raise ITIv2Error(f"soma de probabilidades inválida: {total}")
    return float(p_negative), float(p_neutral), float(p_positive)


def normalized_entropy(p_negative: float, p_neutral: float, p_positive: float) -> float:
    """Entropia normalizada em log base 3."""

    probs = np.array([p_negative, p_neutral, p_positive], dtype=float)
    probs = np.clip(probs, 0.0, 1.0)
    with np.errstate(divide="ignore", invalid="ignore"):
        terms = np.where(probs > 0, probs * np.log(probs), 0.0)
    entropy = -float(np.sum(terms))
    return entropy / math.log(3.0)


def aggregate_company_day(
    predictions: pd.DataFrame,
    *,
    date_col: str = "date",
    company_col: str = "company_id",
    news_col: str = "news_id",
    p_neg_col: str = "p_negative",
    p_neu_col: str = "p_neutral",
    p_pos_col: str = "p_positive",
) -> pd.DataFrame:
    """Agrega previsões únicas por (empresa, dia civil)."""

    required = {date_col, company_col, news_col, p_neg_col, p_neu_col, p_pos_col}
    missing = required - set(predictions.columns)
    if missing:
        raise ITIv2Error(f"colunas ausentes: {sorted(missing)}")

    frame = predictions.copy()
    frame[date_col] = pd.to_datetime(frame[date_col], errors="coerce").dt.normalize()
    frame = frame.dropna(subset=[date_col, company_col, news_col])

    scores: list[float] = []
    entropies: list[float] = []
    hard_labels: list[int] = []
    for row in frame.itertuples(index=False):
        pn, p0, pp = validate_probabilities(
            getattr(row, p_neg_col),
            getattr(row, p_neu_col),
            getattr(row, p_pos_col),
        )
        scores.append(continuous_sentiment(pp, pn))
        entropies.append(normalized_entropy(pn, p0, pp))
        hard_labels.append(
            1 if pp > pn and pp >= p0 else (-1 if pn > pp and pn >= p0 else 0)
        )

    frame["_score"] = scores
    frame["_entropy"] = entropies
    frame["_hard"] = hard_labels

    grouped = (
        frame.groupby([company_col, date_col], as_index=False)
        .agg(
            n_articles=(news_col, "nunique"),
            soft_mean=("_score", "mean"),
            hard_bsi=("_hard", "mean"),
            negative_mean=(p_neg_col, "mean"),
            mean_entropy=("_entropy", "mean"),
        )
        .rename(columns={date_col: "date"})
    )
    grouped["soft_input"] = grouped["soft_mean"]
    grouped["hard_input"] = grouped["hard_bsi"]
    grouped["index_version"] = "iti_v2"
    return grouped


def compute_half_life_index(
    daily: pd.DataFrame,
    half_life_days: int,
    *,
    company_col: str = "company_id",
    input_col: str = "soft_input",
    initial_value: float = 0.0,
    warmup_days: int = 70,
    calendar_end: pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Recorrência ITI com entrada ``soft_input``; dias sem linha usam X=0."""

    lam = lambda_from_half_life(half_life_days)
    col_name = f"iti_v2_h{half_life_days}"

    if daily.empty:
        return daily.assign(**{col_name: pd.Series(dtype=float)})

    work = daily.sort_values(["company_id" if company_col == "company_id" else company_col, "date"]).copy()
    work["date"] = pd.to_datetime(work["date"], errors="coerce").dt.normalize()

    outputs: list[pd.DataFrame] = []
    for company, group in work.groupby(company_col, sort=False):
        g = group.set_index("date").sort_index()
        start = g.index.min()
        end = calendar_end.normalize() if calendar_end is not None else g.index.max()
        full_index = pd.date_range(start, end, freq="D")
        x_series = g[input_col].reindex(full_index)
        n_series = g.get("n_articles", pd.Series(0, index=g.index)).reindex(full_index).fillna(0)

        state = float(initial_value)
        values: list[float] = []
        days_since_list: list[int] = []
        for day in full_index:
            if day in g.index and n_series.loc[day] > 0:
                x_t = float(x_series.loc[day])
                days_since = 0
            else:
                x_t = 0.0
                days_since = days_since_list[-1] + 1 if days_since_list else 1
            state = lam * state + (1.0 - lam) * x_t
            values.append(state)
            days_since_list.append(days_since)

        out = pd.DataFrame(
            {
                "date": full_index,
                company_col: company,
                col_name: values,
                "days_since_last_news": days_since_list,
            }
        )
        out["warmup"] = (out["date"] - start).dt.days < warmup_days
        outputs.append(out)

    return pd.concat(outputs, ignore_index=True)


CoverageStatus = Literal["eligible", "unknown", "failed"]


def build_daily_iti_v2_frame(
    predictions: pd.DataFrame,
    *,
    half_lives: tuple[int, ...] = (2, 7, 14),
    calendar_end: pd.Timestamp | None = None,
    warmup_days: int = 70,
) -> pd.DataFrame:
    """Pipeline diário: agregação + colunas ITI para cada meia-vida."""

    daily = aggregate_company_day(predictions)
    daily["coverage_status"] = "eligible"

    merged = daily
    for h in half_lives:
        idx = compute_half_life_index(
            daily,
            h,
            calendar_end=calendar_end,
            warmup_days=warmup_days,
        )
        merged = merged.merge(
            idx[["date", "company_id", f"iti_v2_h{h}"]],
            on=["date", "company_id"],
            how="left",
        )
    return merged


def build_weekly_signals(
    daily_frame: pd.DataFrame,
    *,
    company_col: str = "company_id",
    date_col: str = "date",
    week_anchor: str = "W-FRI",
    value_columns: tuple[str, ...] | None = None,
) -> pd.DataFrame:
    """Colapsa série diária para fim de semana (último valor observado na semana)."""

    if daily_frame.empty:
        return daily_frame.copy()

    work = daily_frame.copy()
    work[date_col] = pd.to_datetime(work[date_col], errors="coerce").dt.normalize()
    work = work.dropna(subset=[date_col])

    if value_columns is None:
        value_columns = tuple(
            col
            for col in work.columns
            if col.startswith("iti_v2_h") or col in ("soft_mean", "hard_bsi", "n_articles")
        )

    rows: list[pd.DataFrame] = []
    for company, group in work.groupby(company_col, sort=False):
        indexed = group.set_index(date_col).sort_index()
        weekly = indexed.resample(week_anchor).last()
        weekly = weekly.dropna(how="all", subset=list(value_columns))
        weekly[company_col] = company
        weekly["week_end"] = weekly.index
        weekly["week_id"] = weekly.index.to_period(week_anchor).astype(str)
        rows.append(weekly.reset_index(drop=True))

    out = pd.concat(rows, ignore_index=True)
    out["date"] = pd.to_datetime(out["week_end"]).dt.date.astype(str)
    return out
