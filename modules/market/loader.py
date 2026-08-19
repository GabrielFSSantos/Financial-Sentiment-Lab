"""Leitura de preços locais e cálculo de retornos."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from modules.market.config.loader import MarketConfiguration


class MarketLoaderError(RuntimeError):
    """Erro ao carregar ou validar preços de mercado."""


CANONICAL_COLUMNS = ("date", "ticker", "close", "simple_return", "log_return")


def sanitize_price_frame(
    frame: pd.DataFrame,
    *,
    date_col: str = "date",
    ticker_col: str = "ticker",
    close_col: str = "close",
) -> pd.DataFrame:
    """Remove linhas inválidas e garante schema longo date/ticker/close."""

    working = frame.copy()
    for column in (date_col, ticker_col, close_col):
        if column not in working.columns:
            raise MarketLoaderError(
                f"Coluna ausente no CSV de mercado: {column}"
            )

    working[date_col] = pd.to_datetime(working[date_col], errors="coerce")
    working[ticker_col] = working[ticker_col].astype(str).str.strip()
    working[close_col] = pd.to_numeric(working[close_col], errors="coerce")
    working = working.dropna(subset=[date_col, ticker_col, close_col])
    working[date_col] = working[date_col].dt.date.astype(str)
    working = working.drop_duplicates(
        subset=[date_col, ticker_col],
        keep="last",
    )
    return working.loc[:, [date_col, ticker_col, close_col]].reset_index(drop=True)


def validate_market_csv(
    frame: pd.DataFrame,
    configuration: MarketConfiguration,
) -> None:
    """Valida colunas mínimas após normalização."""

    required = {
        configuration.columns["date"],
        configuration.columns["ticker"],
        configuration.columns["close"],
    }
    missing = sorted(required - set(frame.columns))
    if missing:
        raise MarketLoaderError(
            "Colunas ausentes no CSV de mercado: "
            f"{', '.join(missing)}"
        )


def _normalize_columns(
    frame: pd.DataFrame,
    configuration: MarketConfiguration,
) -> pd.DataFrame:
    rename_map = {
        original: internal
        for internal, original in configuration.columns.items()
        if original in frame.columns
    }
    normalized = frame.rename(columns=rename_map).copy()

    for column in ("date", "ticker", "close"):
        if column not in normalized.columns:
            raise MarketLoaderError(
                f"Coluna interna ausente após normalização: {column}"
            )

    try:
        return sanitize_price_frame(normalized)
    except MarketLoaderError:
        raise
    except Exception as error:
        raise MarketLoaderError(
            f"Falha ao sanitizar CSV de mercado: {error}"
        ) from error


def _compute_returns(
    frame: pd.DataFrame,
    *,
    return_columns: tuple[str, ...],
) -> pd.DataFrame:
    result = frame.sort_values(["ticker", "date"]).reset_index(drop=True)

    if "simple_return" in return_columns:
        result["simple_return"] = result.groupby("ticker")["close"].pct_change()
    if "log_return" in return_columns:
        result["log_return"] = result.groupby("ticker")["close"].transform(
            lambda series: np.log(series / series.shift(1))
        )

    return result


def load_market_prices(
    configuration: MarketConfiguration | str | Path,
    *,
    project_root: Path | None = None,
) -> pd.DataFrame:
    """Carrega CSV local e calcula retornos declarados na configuração."""

    if isinstance(configuration, (str, Path)):
        from modules.market.config.loader import load_market_configuration

        configuration = load_market_configuration(
            project_root=project_root,
            config_path=configuration,
        )

    path = configuration.local_path
    if not path.is_file():
        raise MarketLoaderError(
            f"Arquivo de preços não encontrado: {path}. "
            "Execute: python -m modules.market fetch"
        )

    try:
        frame = pd.read_csv(
            path,
            encoding=str(configuration.reader.get("encoding", "utf-8")),
            sep=str(configuration.reader.get("delimiter", ",")),
        )
    except OSError as error:
        raise MarketLoaderError(
            f"Não foi possível ler {path}: {error}"
        ) from error

    if frame.empty:
        raise MarketLoaderError(f"CSV de mercado vazio: {path}")

    validate_market_csv(frame, configuration)
    normalized = _normalize_columns(frame, configuration)
    if normalized.empty:
        raise MarketLoaderError(
            f"CSV de mercado sem linhas válidas após sanitização: {path}"
        )
    return _compute_returns(
        normalized,
        return_columns=configuration.return_columns,
    )


__all__ = [
    "CANONICAL_COLUMNS",
    "MarketLoaderError",
    "load_market_prices",
    "sanitize_price_frame",
    "validate_market_csv",
]
