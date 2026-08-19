"""Download e materialização de preços declarados em ``configs/market.yaml``."""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

import pandas as pd

from modules.market.common import ASSET_FETCH_HINT
from modules.market.config.loader import MarketConfiguration

try:
    import yfinance as yf
except ImportError as error:  # pragma: no cover
    yf = None  # type: ignore[assignment]
    _YF_IMPORT_ERROR = error
else:
    _YF_IMPORT_ERROR = None


AssetStatus = Literal["skipped", "downloaded", "failed"]


class AssetFetchError(RuntimeError):
    """Erro durante o download de preços de mercado."""


@dataclass(frozen=True)
class AssetFetchReport:
    asset_key: str
    asset_type: str
    provider: str
    status: AssetStatus
    target: str
    message: str = ""
    bytes_downloaded: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AssetFetchSummary:
    reports: tuple[AssetFetchReport, ...] = field(default_factory=tuple)

    @property
    def downloaded_count(self) -> int:
        return sum(report.status == "downloaded" for report in self.reports)

    @property
    def failed_count(self) -> int:
        return sum(report.status == "failed" for report in self.reports)

    def to_dict(self) -> dict[str, Any]:
        return {
            "downloaded_count": self.downloaded_count,
            "failed_count": self.failed_count,
            "reports": [report.to_dict() for report in self.reports],
        }


def _ensure_yfinance() -> None:
    if yf is None:
        raise AssetFetchError(
            "yfinance não está instalado. Execute: pip install yfinance"
        ) from _YF_IMPORT_ERROR


def _market_file_is_present(path: Path) -> bool:
    return path.is_file() and path.stat().st_size > 0


def check_market_assets(configuration: MarketConfiguration) -> list[str]:
    """Lista paths ausentes para mercado enabled."""

    if not configuration.enabled:
        return []

    if _market_file_is_present(configuration.local_path):
        return []

    if configuration.source is None:
        return [str(configuration.local_path)]

    return [str(configuration.local_path)]


def _normalize_yfinance_frame(
    *,
    frame: pd.DataFrame,
    ticker: str,
    configuration: MarketConfiguration,
) -> pd.DataFrame:
    working = frame.reset_index()
    date_col = configuration.columns["date"]
    close_col = configuration.columns["close"]
    ticker_col = configuration.columns["ticker"]

    if "Date" in working.columns:
        working = working.rename(columns={"Date": date_col})
    elif "Datetime" in working.columns:
        working = working.rename(columns={"Datetime": date_col})
    elif date_col not in working.columns:
        first_column = working.columns[0]
        if first_column in {"index", "level_0"} or first_column not in {
            date_col,
            close_col,
            ticker_col,
        }:
            working = working.rename(columns={first_column: date_col})

    if "Close" in working.columns:
        working = working.rename(columns={"Close": close_col})
    elif close_col not in working.columns:
        raise AssetFetchError(
            f"Coluna Close ausente no retorno yfinance para {ticker}."
        )

    working[ticker_col] = ticker
    working[date_col] = pd.to_datetime(
        working[date_col],
        errors="coerce",
    ).dt.date.astype(str)

    return working.loc[:, [date_col, ticker_col, close_col]]


def _fetch_yfinance(
    *,
    configuration: MarketConfiguration,
    logger: logging.Logger,
    force: bool,
) -> AssetFetchReport:
    source = configuration.source
    if source is None:
        return AssetFetchReport(
            asset_key="market",
            asset_type="market",
            provider="local",
            status="skipped",
            target=str(configuration.local_path),
            message="Nenhuma source configurada; use CSV local.",
        )

    target = configuration.local_path
    if _market_file_is_present(target) and not force:
        return AssetFetchReport(
            asset_key="market",
            asset_type="market",
            provider=source.provider,
            status="skipped",
            target=str(target),
            message="Arquivo local já presente.",
        )

    _ensure_yfinance()
    target.parent.mkdir(parents=True, exist_ok=True)

    frames: list[pd.DataFrame] = []
    for ticker in source.tickers:
        logger.info("Baixando %s via yfinance", ticker)
        try:
            history = yf.download(
                ticker,
                start=source.start,
                end=source.end,
                progress=False,
                auto_adjust=True,
            )
        except Exception as error:
            return AssetFetchReport(
                asset_key="market",
                asset_type="market",
                provider="yfinance",
                status="failed",
                target=str(target),
                message=f"{ticker}: {error}",
            )

        if history is None or history.empty:
            return AssetFetchReport(
                asset_key="market",
                asset_type="market",
                provider="yfinance",
                status="failed",
                target=str(target),
                message=f"Histórico vazio para {ticker}.",
            )

        frames.append(
            _normalize_yfinance_frame(
                frame=history,
                ticker=ticker,
                configuration=configuration,
            )
        )

    combined = pd.concat(frames, ignore_index=True)
    combined = combined.sort_values(
        [configuration.columns["ticker"], configuration.columns["date"]]
    )
    combined.to_csv(
        target,
        index=False,
        encoding=str(configuration.reader.get("encoding", "utf-8")),
    )

    return AssetFetchReport(
        asset_key="market",
        asset_type="market",
        provider="yfinance",
        status="downloaded",
        target=str(target),
        message=f"{len(combined)} linha(s) materializadas.",
        bytes_downloaded=target.stat().st_size,
    )


def fetch_market_assets(
    configuration: MarketConfiguration,
    *,
    force: bool = False,
    logger: logging.Logger | None = None,
) -> AssetFetchSummary:
    """Baixa preços ausentes conforme ``configs/market.yaml``."""

    log = logger or logging.getLogger(__name__)

    if not configuration.enabled:
        return AssetFetchSummary(
            reports=(
                AssetFetchReport(
                    asset_key="market",
                    asset_type="market",
                    provider="local",
                    status="skipped",
                    target=str(configuration.local_path),
                    message="market.enabled=false",
                ),
            )
        )

    if configuration.source is None:
        if _market_file_is_present(configuration.local_path):
            report = AssetFetchReport(
                asset_key="market",
                asset_type="market",
                provider="local",
                status="skipped",
                target=str(configuration.local_path),
                message="Modo local; CSV presente.",
            )
        else:
            report = AssetFetchReport(
                asset_key="market",
                asset_type="market",
                provider="local",
                status="failed",
                target=str(configuration.local_path),
                message=(
                    "CSV local ausente e nenhuma source configurada."
                    + ASSET_FETCH_HINT
                ),
            )
        return AssetFetchSummary(reports=(report,))

    report = _fetch_yfinance(
        configuration=configuration,
        logger=log,
        force=force,
    )
    return AssetFetchSummary(reports=(report,))


__all__ = [
    "AssetFetchError",
    "AssetFetchReport",
    "AssetFetchSummary",
    "check_market_assets",
    "fetch_market_assets",
]
