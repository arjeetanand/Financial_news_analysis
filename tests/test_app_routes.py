import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import pandas as pd

import app as app_module


def _build_test_df():
    return pd.DataFrame(
        [
            {
                "Triggered_Stock_Symbols": "TCS",
                "Triggered_Stock_Names": "Tata Consultancy Services",
                "Sentiment": "Positive",
                "Headline": "TCS gains on strong guidance",
                "Summary": "Shares gain after upbeat outlook.",
                "Date": "2026-03-10",
                "Time": "10:00",
                "Date_Time": "2026-03-10T10:00:00",
                "News_Day_Before": 3200.0,
                "News_day": 3250.0,
                "SMA_10": 100.0,
                "SMA_20": 95.0,
                "SMA_50": 90.0,
                "RSI": 60.0,
                "MACD": 1.5,
                "MACD_Signal": 1.2,
                "MACD_Analysis": "Bullish crossover",
                "SMA_Analysis": "Uptrend",
                "RSI_Analysis": "Healthy momentum",
                "Adjusted_Sentiment": "Positive",
            },
            {
                "Triggered_Stock_Symbols": "INFY",
                "Triggered_Stock_Names": "Infosys",
                "Sentiment": "Neutral",
                "Headline": "Infosys remains stable",
                "Summary": "No major move.",
                "Date": "2026-03-11",
                "Time": "11:00",
                "Date_Time": "2026-03-11T11:00:00",
                "News_Day_Before": float("nan"),
                "News_day": float("nan"),
                "SMA_10": 200.0,
                "SMA_20": 205.0,
                "SMA_50": 210.0,
                "RSI": 45.0,
                "MACD": -0.4,
                "MACD_Signal": -0.3,
                "MACD_Analysis": "Weak trend",
                "SMA_Analysis": "Sideways",
                "RSI_Analysis": "Neutral momentum",
                "Adjusted_Sentiment": "Neutral",
            },
        ]
    )


def _client_with_df(df):
    app_module.app.config["TESTING"] = True
    app_module.df = df
    return app_module.app.test_client()


def test_search_stocks_returns_symbols_for_query():
    client = _client_with_df(_build_test_df())

    response = client.get("/search_stocks?q=tc")

    assert response.status_code == 200
    assert response.get_json() == ["TCS"]


def test_search_stocks_empty_query_returns_empty_list():
    client = _client_with_df(_build_test_df())

    response = client.get("/search_stocks?q=")

    assert response.status_code == 200
    assert response.get_json() == []


def test_stock_details_known_symbol_returns_records():
    client = _client_with_df(_build_test_df())

    response = client.get("/stock_details/TCS")

    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["Triggered_Stock_Symbols"] == "TCS"


def test_stock_details_unknown_symbol_returns_empty_list():
    client = _client_with_df(_build_test_df())

    response = client.get("/stock_details/UNKNOWN")

    assert response.status_code == 200
    assert response.get_json() == []


def test_stock_details_handles_nan_fields_without_crashing():
    client = _client_with_df(_build_test_df())

    response = client.get("/stock_details/INFY")

    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["Triggered_Stock_Symbols"] == "INFY"
