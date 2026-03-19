from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


SENTIMENT_TO_SIGNAL = {
    "positive": 1.0,
    "negative": -1.0,
    "neutral": 0.0,
}


@dataclass
class BacktestReport:
    coverage: float
    hit_rate: float
    average_forward_return: float
    strategy_mean_return: float
    strategy_sharpe_like: float



def _to_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def compute_forward_returns(
    df: pd.DataFrame,
    *,
    entry_price_col: str = "News_day",
    exit_price_col: str = "News_Day_After",
) -> pd.Series:
    entry = _to_numeric(df[entry_price_col])
    exit_price = _to_numeric(df[exit_price_col])
    returns = (exit_price - entry) / entry
    returns = returns.replace([np.inf, -np.inf], np.nan)
    return returns


def sentiment_signals(df: pd.DataFrame, sentiment_col: str = "Sentiment") -> pd.Series:
    normalized = df[sentiment_col].fillna("").astype(str).str.lower().str.strip()
    return normalized.map(SENTIMENT_TO_SIGNAL).fillna(0.0)


def event_study_backtest(
    df: pd.DataFrame,
    *,
    sentiment_col: str = "Sentiment",
    entry_price_col: str = "News_day",
    exit_price_col: str = "News_Day_After",
) -> BacktestReport:
    returns = compute_forward_returns(
        df,
        entry_price_col=entry_price_col,
        exit_price_col=exit_price_col,
    )
    signals = sentiment_signals(df, sentiment_col=sentiment_col)

    valid_mask = returns.notna()
    if valid_mask.sum() == 0:
        return BacktestReport(
            coverage=0.0,
            hit_rate=0.0,
            average_forward_return=0.0,
            strategy_mean_return=0.0,
            strategy_sharpe_like=0.0,
        )

    valid_returns = returns[valid_mask]
    valid_signals = signals[valid_mask]

    directional_truth = np.sign(valid_returns)
    directional_pred = np.sign(valid_signals)

    comparable_mask = directional_pred != 0
    if comparable_mask.sum() == 0:
        hit_rate = 0.0
    else:
        hit_rate = float((directional_truth[comparable_mask] == directional_pred[comparable_mask]).mean())

    strategy_returns = valid_signals * valid_returns
    mean_strategy = float(strategy_returns.mean())
    std_strategy = float(strategy_returns.std(ddof=0))
    sharpe_like = float(mean_strategy / std_strategy) if std_strategy > 0 else 0.0

    return BacktestReport(
        coverage=float(valid_mask.mean()),
        hit_rate=hit_rate,
        average_forward_return=float(valid_returns.mean()),
        strategy_mean_return=mean_strategy,
        strategy_sharpe_like=sharpe_like,
    )


def sentiment_calibration_table(
    df: pd.DataFrame,
    *,
    sentiment_col: str = "Sentiment",
    entry_price_col: str = "News_day",
    exit_price_col: str = "News_Day_After",
) -> pd.DataFrame:
    returns = compute_forward_returns(
        df,
        entry_price_col=entry_price_col,
        exit_price_col=exit_price_col,
    )
    temp = df.copy()
    temp["forward_return"] = returns
    temp["sentiment_bucket"] = temp[sentiment_col].fillna("").astype(str).str.lower().str.strip()

    grouped = (
        temp.dropna(subset=["forward_return"])
        .groupby("sentiment_bucket", as_index=False)
        .agg(count=("forward_return", "size"), mean_forward_return=("forward_return", "mean"))
        .sort_values("sentiment_bucket")
    )
    return grouped
