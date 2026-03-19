import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import pandas as pd

import app as app_module


def _client_with_df(df):
    app_module.app.config["TESTING"] = True
    app_module.df = df
    app_module.inference_service = app_module.InferenceService(
        entity_linker=app_module._build_entity_linker(df)
    )
    return app_module.app.test_client()


def _df_for_inference():
    return pd.DataFrame(
        [
            {
                "Triggered_Stock_Symbols": "TCS",
                "Triggered_Stock_Names": "Tata Consultancy Services",
                "Sentiment": "Positive",
            }
        ]
    )


def test_infer_sentiment_returns_prediction():
    client = _client_with_df(_df_for_inference())

    response = client.post(
        "/api/v1/inference/sentiment",
        json={"text": "TCS gains after upbeat guidance"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["label"] in {"Positive", "Neutral", "Negative"}
    assert 0.0 <= payload["confidence"] <= 1.0


def test_infer_explain_returns_keyword_rationale():
    client = _client_with_df(_df_for_inference())

    response = client.post(
        "/api/v1/inference/explain",
        json={"text": "TCS gains with strong profit growth"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["label"] == "Positive"
    assert "positive_keywords" in payload


def test_infer_entities_returns_matches():
    client = _client_with_df(_df_for_inference())

    response = client.post(
        "/api/v1/inference/entities",
        json={"text": "Tata Consultancy Services signs a new deal"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["entities"][0]["symbol"] == "TCS"


def test_infer_news_requires_content():
    client = _client_with_df(_df_for_inference())

    response = client.post("/api/v1/inference/news", json={})

    assert response.status_code == 400
    assert "error" in response.get_json()


def test_sentiment_trend_endpoint_returns_time_series():
    df = pd.DataFrame(
        [
            {
                "Triggered_Stock_Symbols": "TCS",
                "Triggered_Stock_Names": "Tata Consultancy Services",
                "Sentiment": "Positive",
                "Date_Time": "2026-03-10T10:00:00",
            },
            {
                "Triggered_Stock_Symbols": "INFY",
                "Triggered_Stock_Names": "Infosys",
                "Sentiment": "Negative",
                "Date_Time": "2026-03-10T11:00:00",
            },
        ]
    )
    client = _client_with_df(df)

    response = client.get("/api/v1/sentiment_trend")

    assert response.status_code == 200
    payload = response.get_json()
    assert isinstance(payload, list)
    assert any(item["Trend_Sentiment"] == "positive" for item in payload)


def test_infer_news_returns_explanation_payload():
    client = _client_with_df(_df_for_inference())

    response = client.post(
        "/api/v1/inference/news",
        json={"headline": "TCS gains", "summary": "profit growth remains strong"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert "explanation" in payload
    assert "confidence" in payload["explanation"]
