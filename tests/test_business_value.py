import pandas as pd

from mlops.business_value import (
    compute_forward_returns,
    event_study_backtest,
    sentiment_calibration_table,
)


def _sample_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"Sentiment": "Positive", "News_day": 100.0, "News_Day_After": 103.0},
            {"Sentiment": "Negative", "News_day": 100.0, "News_Day_After": 98.0},
            {"Sentiment": "Neutral", "News_day": 100.0, "News_Day_After": 100.0},
            {"Sentiment": "Positive", "News_day": 100.0, "News_Day_After": 97.0},
        ]
    )


def test_compute_forward_returns_values():
    returns = compute_forward_returns(_sample_df())

    assert list(returns.round(4)) == [0.03, -0.02, 0.0, -0.03]


def test_event_study_backtest_has_expected_metrics():
    report = event_study_backtest(_sample_df())

    assert report.coverage == 1.0
    assert report.hit_rate == 2 / 3
    assert report.average_forward_return == -0.005


def test_sentiment_calibration_table_contains_buckets():
    table = sentiment_calibration_table(_sample_df())

    buckets = set(table["sentiment_bucket"].tolist())
    assert buckets == {"positive", "negative", "neutral"}
