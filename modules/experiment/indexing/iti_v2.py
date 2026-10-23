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
    frame = frame.drop_duplicates(subset=[company_col, date_col, news_col], keep="first")

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
        cov_series = (
            g["coverage_status"].reindex(full_index)
            if "coverage_status" in g.columns
            else pd.Series("eligible", index=full_index)
        )

        state = float(initial_value)
        values: list[float] = []
        days_since_list: list[int] = []
        warmup_flags: list[bool] = []
        eligible_segment_start: pd.Timestamp | None = None
        for day in full_index:
            if str(cov_series.loc[day]) != "eligible":
                values.append(np.nan)
                state = float(initial_value)
                eligible_segment_start = None
                days_since_list.append(
                    days_since_list[-1] + 1 if days_since_list else 0
                )
                warmup_flags.append(True)
                continue
            if eligible_segment_start is None:
                eligible_segment_start = day
                state = float(initial_value)
            if day in g.index and n_series.loc[day] > 0:
                x_t = float(x_series.loc[day])
                days_since = 0
            else:
                x_t = 0.0
                days_since = days_since_list[-1] + 1 if days_since_list else 1
            state = lam * state + (1.0 - lam) * x_t
            values.append(state)
            days_since_list.append(days_since)
            warmup_flags.append(
                (day - eligible_segment_start).days < warmup_days
            )

        out = pd.DataFrame(
            {
                "date": full_index,
                company_col: company,
                col_name: values,
                "days_since_last_news": days_since_list,
                "warmup": warmup_flags,
            }
        )
        outputs.append(out)

    return pd.concat(outputs, ignore_index=True)


CoverageStatus = Literal["eligible", "unknown", "failed"]


def _coverage_status_for_dates(
    dates: pd.Series,
    *,
    corpus_span: tuple[pd.Timestamp, pd.Timestamp] | None,
) -> pd.Series:
    if corpus_span is None:
        return pd.Series("eligible", index=dates.index, dtype=object)
    dmin, dmax = corpus_span[0].normalize(), corpus_span[1].normalize()
    normalized = pd.to_datetime(dates, errors="coerce").dt.normalize()
    status = pd.Series("unknown", index=dates.index, dtype=object)
    in_span = (normalized >= dmin) & (normalized <= dmax)
    status.loc[in_span] = "eligible"
    return status


def _expand_daily_calendar(
    daily_agg: pd.DataFrame,
    *,
    calendar_end: pd.Timestamp | None,
    corpus_span: tuple[pd.Timestamp, pd.Timestamp] | None = None,
    company_col: str = "company_id",
) -> pd.DataFrame:
    """Grade civil completa por empresa (dias sem matéria preservados na saída)."""

    if daily_agg.empty:
        return daily_agg.copy()

    end = (
        pd.Timestamp(calendar_end).normalize()
        if calendar_end is not None
        else pd.to_datetime(daily_agg["date"]).max().normalize()
    )
    parts: list[pd.DataFrame] = []
    for company, group in daily_agg.groupby(company_col, sort=False):
        first_news = pd.to_datetime(group["date"].min()).normalize()
        if corpus_span is not None:
            start = min(first_news, corpus_span[0].normalize())
        else:
            start = first_news
        full_index = pd.date_range(start, end, freq="D")
        base = pd.DataFrame({company_col: company, "date": full_index})
        merged = base.merge(group, on=[company_col, "date"], how="left")
        merged["n_articles"] = merged["n_articles"].fillna(0).astype(int)
        merged["coverage_status"] = _coverage_status_for_dates(
            merged["date"],
            corpus_span=corpus_span,
        )
        merged["soft_input"] = np.nan
        eligible_mask = merged["coverage_status"] == "eligible"
        merged.loc[eligible_mask, "soft_input"] = merged.loc[eligible_mask, "soft_mean"].fillna(
            0.0
        )
        merged["index_version"] = merged["index_version"].fillna("iti_v2")
        parts.append(merged)

    return pd.concat(parts, ignore_index=True)


def _resolve_ticker(company_id: str, company_to_ticker: dict[str, str]) -> str | None:
    direct = company_to_ticker.get(company_id)
    if direct:
        return direct
    lowered = {str(k).strip().lower(): v for k, v in company_to_ticker.items()}
    return lowered.get(str(company_id).strip().lower())


def last_eligible_signal_date(indexed: pd.DataFrame) -> pd.Timestamp | None:
    """Último dia civil com cobertura informacional elegível no quadro diário."""

    if indexed.empty:
        return None
    if "coverage_status" in indexed.columns:
        mask = indexed["coverage_status"].astype(str) == "eligible"
        if not mask.any():
            return None
        return pd.Timestamp(indexed.index[mask].max()).normalize()
    return pd.Timestamp(indexed.index.max()).normalize()


def _values_at_cutoff(
    indexed: pd.DataFrame,
    cutoff: pd.Timestamp,
    value_columns: tuple[str, ...],
) -> dict[str, object]:
    """Estado no instante causal ``cutoff``; sem reutilizar ITI após o fim do corpus."""

    cutoff_norm = pd.Timestamp(cutoff).normalize()
    last_eligible = last_eligible_signal_date(indexed)
    if last_eligible is None or cutoff_norm > last_eligible:
        out: dict[str, object] = {col: np.nan for col in value_columns}
        out["signal_exclusion"] = "cutoff_after_corpus_coverage"
        return out

    if cutoff_norm not in indexed.index:
        out = {col: np.nan for col in value_columns}
        out["signal_exclusion"] = "cutoff_not_in_daily_calendar"
        return out

    row = indexed.loc[cutoff_norm]
    if "coverage_status" in indexed.columns and str(row.get("coverage_status")) != "eligible":
        out = {col: np.nan for col in value_columns}
        out["signal_exclusion"] = "cutoff_not_eligible"
        return out

    out = {col: row.get(col, np.nan) for col in value_columns}
    if "warmup" in indexed.columns:
        out["warmup"] = bool(row.get("warmup", False))
    out["signal_exclusion"] = ""
    return out


def build_daily_iti_v2_frame(
    predictions: pd.DataFrame,
    *,
    half_lives: tuple[int, ...] = (2, 7, 14),
    calendar_end: pd.Timestamp | None = None,
    warmup_days: int = 70,
    corpus_span: tuple[pd.Timestamp, pd.Timestamp] | None = None,
) -> pd.DataFrame:
    """Pipeline diário: agregação + colunas ITI para cada meia-vida."""

    daily_agg = aggregate_company_day(predictions)
    expanded = _expand_daily_calendar(
        daily_agg,
        calendar_end=calendar_end,
        corpus_span=corpus_span,
    )
    if expanded.empty:
        return expanded

    end = (
        pd.Timestamp(calendar_end).normalize()
        if calendar_end is not None
        else pd.to_datetime(expanded["date"]).max().normalize()
    )

    result = expanded.copy()
    for h in half_lives:
        idx = compute_half_life_index(
            expanded,
            h,
            calendar_end=end,
            warmup_days=warmup_days,
        )
        col = f"iti_v2_h{h}"
        merge_cols = ["date", "company_id", col, "days_since_last_news", "warmup"]
        result = result.drop(columns=[col, "days_since_last_news", "warmup"], errors="ignore")
        result = result.merge(
            idx[merge_cols],
            on=["date", "company_id"],
            how="left",
        )
    return result


def build_weekly_signals(
    daily_frame: pd.DataFrame,
    *,
    company_col: str = "company_id",
    date_col: str = "date",
    week_anchor: str = "W-FRI",
    value_columns: tuple[str, ...] | None = None,
    market_sessions: pd.DataFrame | None = None,
    company_to_ticker: dict[str, str] | None = None,
    corpus_span: tuple[pd.Timestamp, pd.Timestamp] | None = None,
) -> pd.DataFrame:
    """Amostra sinais no cutoff causal (dia civil anterior ao último pregão da semana)."""

    if daily_frame.empty:
        return daily_frame.copy()

    work = daily_frame.copy()
    work[date_col] = pd.to_datetime(work[date_col], errors="coerce").dt.normalize()
    work = work.dropna(subset=[date_col])

    if value_columns is None:
        value_columns = tuple(
            col
            for col in work.columns
            if col.startswith("iti_v2_h")
            or col
            in ("soft_mean", "soft_input", "hard_bsi", "hard_input", "n_articles", "legacy_c_iti")
        )

    use_market = (
        market_sessions is not None
        and not market_sessions.empty
        and company_to_ticker
    )

    rows: list[dict[str, object]] = []
    for company, group in work.groupby(company_col, sort=False):
        indexed = group.set_index(date_col).sort_index()
        if use_market:
            ticker = _resolve_ticker(str(company), company_to_ticker or {})
            if not ticker:
                continue
            sessions = market_sessions.loc[
                market_sessions["ticker"].astype(str) == str(ticker)
            ].sort_values("week_id")
            last_eligible = (
                pd.Timestamp(corpus_span[1]).normalize()
                if corpus_span is not None
                else last_eligible_signal_date(indexed)
            )
            for _, session in sessions.iterrows():
                cutoff = pd.Timestamp(session["signal_cutoff_at"]).normalize()
                if last_eligible is not None and cutoff > last_eligible:
                    continue
                vals = _values_at_cutoff(indexed, cutoff, value_columns)
                exclusion = vals.pop("signal_exclusion", "")
                if all(pd.isna(vals.get(c)) for c in value_columns):
                    continue
                week_end = pd.Timestamp(session["week_id"]).normalize()
                rows.append(
                    {
                        company_col: company,
                        **vals,
                        "week_end": week_end,
                        "week_id": str(week_end.to_period(week_anchor)),
                        "period_end": str(session.get("period_end", "")),
                        "market_close_at": session.get("market_close_at", ""),
                        "signal_cutoff_at": cutoff,
                        "signal_exclusion": exclusion,
                    }
                )
        else:
            weekly = indexed.resample(week_anchor).last()
            weekly = weekly.dropna(how="all", subset=list(value_columns))
            span_end = (
                pd.Timestamp(corpus_span[1]).normalize() if corpus_span is not None else None
            )
            for week_end, row in weekly.iterrows():
                if span_end is not None and pd.Timestamp(week_end).normalize() > span_end:
                    continue
                rows.append(
                    {
                        company_col: company,
                        **{col: row.get(col, np.nan) for col in value_columns},
                        "week_end": pd.Timestamp(week_end).normalize(),
                        "week_id": str(pd.Timestamp(week_end).to_period(week_anchor)),
                        "period_end": pd.Timestamp(week_end).date().isoformat(),
                    }
                )

    if not rows:
        return pd.DataFrame()

    out = pd.DataFrame(rows)
    out["date"] = pd.to_datetime(out["week_end"]).dt.date.astype(str)
    return out
