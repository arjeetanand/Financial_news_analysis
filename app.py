from datetime import datetime, date
import json
import logging
import math
import subprocess
import warnings

import numpy as np
import pandas as pd
from flask import Flask, render_template, request, jsonify, Response, make_response

from mlops.entity_linking import EntityLinker
from mlops.inference import InferenceService
from flask_caching import Cache
from json import JSONEncoder

warnings.filterwarnings("ignore", message=".*This is a development server.*")


# Set up basic logging
logging.basicConfig(level=logging.DEBUG)


class CustomJSONEncoder(JSONEncoder):
    def default(self, obj):
        # Convert NaN values to None, which becomes 'null' in JSON
        if isinstance(obj, np.floating) and np.isnan(obj):
            return None

        elif isinstance(obj, (datetime, date)):
            return obj.isoformat()
        elif isinstance(obj, np.number):
            if np.isnan(obj):
                return None  # Convert np.nan to None
            else:
                return obj.item()
        return JSONEncoder.default(self, obj)


app = Flask(__name__)
cache = Cache(app, config={"CACHE_TYPE": "simple"})
app.config["CACHE_TYPE"] = "SimpleCache"
cache.init_app(app)
app.json_encoder = CustomJSONEncoder

excel_path = "updated_final.xlsx"
df = pd.read_excel(excel_path)


def _build_entity_linker(source_df):
    columns_present = {"Triggered_Stock_Names", "Triggered_Stock_Symbols"}.issubset(source_df.columns)
    if not columns_present:
        return EntityLinker({})

    mapped = source_df[["Triggered_Stock_Names", "Triggered_Stock_Symbols"]].dropna()
    company_to_symbol = {}
    for _, row in mapped.iterrows():
        company = str(row["Triggered_Stock_Names"]).strip()
        symbol = str(row["Triggered_Stock_Symbols"]).strip()
        if company and symbol:
            company_to_symbol[company] = symbol
    return EntityLinker(company_to_symbol=company_to_symbol)


inference_service = InferenceService(entity_linker=_build_entity_linker(df))


@app.route("/")
@cache.cached(timeout=50, query_string=True)
def dashboard():
    stock_query = request.args.get("stock", None)
    news_symbol_filter = request.args.get("news_symbol", "")

    # Get unique stock symbols for filter dropdown
    unique_stock_symbols = df["Triggered_Stock_Symbols"].dropna().unique().tolist()

    if stock_query:
        filtered_df = df[
            (
                df["Triggered_Stock_Names"].str.contains(
                    stock_query, case=False, na=False
                )
            )
            | (
                df["Triggered_Stock_Symbols"].str.contains(
                    stock_query, case=False, na=False
                )
            )
        ]
        if not filtered_df.empty:
            stock_data = filtered_df.iloc[0].to_dict()
        else:
            stock_data = None
    else:
        stock_data = None

    if news_symbol_filter:
        df_filtered_news = df[
            df["Triggered_Stock_Symbols"].str.contains(
                news_symbol_filter, case=False, na=False
            )
        ]
    else:
        df_filtered_news = df

        if stock_data:
            if stock_data.get("SMA_10") > stock_data.get("SMA_20"):
                stock_data["trend"] = "bullish"
            elif stock_data.get("SMA_10") < stock_data.get("SMA_20"):
                stock_data["trend"] = "bearish"
            else:
                stock_data["trend"] = "neutral"

    page = request.args.get("page", 1, type=int)
    per_page = 8
    total = len(df_filtered_news)
    pages = math.ceil(total / per_page)
    start = (page - 1) * per_page
    end = start + per_page
    news_list = df_filtered_news.iloc[start:end].to_dict(orient="records")

    df_nonan = df.dropna(subset=["Triggered_Stock_Symbols"])
    # Organize sentiments and stocks, ensuring order and removing duplicates
    sentiments_ordered = ["positive", "negative", "neutral"]
    sentiments = {
        sentiment: df_nonan[df_nonan["Sentiment"].str.lower() == sentiment]
        .drop_duplicates(subset=["Triggered_Stock_Symbols"])
        .to_dict(orient="records")
        for sentiment in sentiments_ordered
    }

    # Fetching stock prices
    if news_symbol_filter and not df_filtered_news.empty:
        selected_stock = df_filtered_news.iloc[0]
        stock_prices = {
            "price_day_before": selected_stock.get("News_Day_Before"),
            "price_day_of": selected_stock.get("News_day"),
        }
    else:
        stock_prices = {"price_day_before": None, "price_day_of": None}

    return render_template(
        "html.html",
        sentiments=sentiments,
        stock_data=stock_data,
        news_list=news_list,
        stock_prices=stock_prices,
        page=page,
        pages=pages,
        unique_stock_symbols=unique_stock_symbols,
    )


@app.route("/search_stocks")
def search_stocks():
    query = request.args.get("q", "").lower()
    if query:
        # Convert NaN values to empty strings before the contains check
        results = (
            df["Triggered_Stock_Symbols"].fillna("").str.lower().str.contains(query)
        )
        unique_symbols = df.loc[results, "Triggered_Stock_Symbols"].unique().tolist()
        return jsonify(unique_symbols)
    return jsonify([])


@app.route("/stock_details/<symbol>")
def stock_details(symbol):
    symbol = symbol.upper()  # Assuming symbols are stored in uppercase
    stock_data = df[df["Triggered_Stock_Symbols"].str.upper() == symbol]

    # Replace NaN values with None (which converts to null in JSON)
    cleaned_data = stock_data.replace({np.nan: None}).to_dict(orient="records")

    # Ensure all data is string type to avoid sorting issues
    cleaned_data_str = [{k: str(v) for k, v in item.items()} for item in cleaned_data]

    # Manually serialize data to JSON
    json_data = json.dumps(cleaned_data_str)

    # Return response with application/json content type
    return Response(json_data, mimetype="application/json")


@app.route("/api/v1/sentiment_trend")
def sentiment_trend():
    trend_df = df.copy()
    if "Date_Time" in trend_df.columns:
        trend_df["Trend_Date"] = pd.to_datetime(trend_df["Date_Time"], errors="coerce").dt.date
    elif "Date" in trend_df.columns:
        trend_df["Trend_Date"] = pd.to_datetime(trend_df["Date"], errors="coerce").dt.date
    else:
        return jsonify([])

    if "Sentiment" in trend_df.columns:
        trend_df["Trend_Sentiment"] = trend_df["Sentiment"].astype(str).str.lower()
    else:
        trend_df["Trend_Sentiment"] = "unknown"
    trend_df = trend_df.dropna(subset=["Trend_Date"])

    grouped = (
        trend_df.groupby(["Trend_Date", "Trend_Sentiment"], as_index=False)
        .size()
        .rename(columns={"size": "count"})
        .sort_values(["Trend_Date", "Trend_Sentiment"])
    )
    grouped["Trend_Date"] = grouped["Trend_Date"].astype(str)
    return jsonify(grouped.to_dict(orient="records"))


@app.route("/api/v1/reports/sentiment_summary")
def sentiment_summary_report():
    summary_df = (
        df.assign(Sentiment=df["Sentiment"].astype(str).str.lower())
        .groupby("Sentiment", as_index=False)
        .size()
        .rename(columns={"size": "count"})
        .sort_values("Sentiment")
    )

    return jsonify(summary_df.to_dict(orient="records"))


@app.route("/api/v1/reports/download")
def download_report():
    report_df = df.copy()
    csv_bytes = report_df.to_csv(index=False).encode("utf-8")

    response = make_response(csv_bytes)
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = "attachment; filename=financial_news_report.csv"
    return response


@app.route("/api/v1/inference/sentiment", methods=["POST"])
def infer_sentiment():
    payload = request.get_json(silent=True) or {}
    text_value = str(payload.get("text", "")).strip()
    if not text_value:
        return jsonify({"error": "Field 'text' is required"}), 400

    prediction = inference_service.predict_sentiment(text_value)
    return jsonify(prediction.__dict__)


@app.route("/api/v1/inference/explain", methods=["POST"])
def infer_explain():
    payload = request.get_json(silent=True) or {}
    text_value = str(payload.get("text", "")).strip()
    if not text_value:
        return jsonify({"error": "Field 'text' is required"}), 400

    return jsonify(inference_service.explain_sentiment(text_value))


@app.route("/api/v1/inference/entities", methods=["POST"])
def infer_entities():
    payload = request.get_json(silent=True) or {}
    text_value = str(payload.get("text", "")).strip()
    if not text_value:
        return jsonify({"error": "Field 'text' is required"}), 400

    return jsonify({"entities": inference_service.predict_entities(text_value)})


@app.route("/api/v1/inference/news", methods=["POST"])
def infer_news():
    payload = request.get_json(silent=True) or {}
    headline = str(payload.get("headline", "")).strip()
    summary = str(payload.get("summary", "")).strip()
    if not headline and not summary:
        return jsonify({"error": "At least one of 'headline' or 'summary' is required"}), 400

    return jsonify(inference_service.predict_news(headline=headline, summary=summary))


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/run-script")
def run_script():
    logging.info("Starting script execution")
    try:
        script_path = "indian_stock_sentiment_from_news_headlines_project.py"
        subprocess.run(["python", script_path], check=True)
        logging.info("Script execution completed")
    except Exception as e:
        logging.error(f"Script execution failed: {e}")
        return jsonify({"error": "Script execution failed"}), 500

    try:
        df = pd.read_excel("updated_final_output.xlsx")
    except Exception as e:
        logging.error(f"Failed to load Excel file: {e}")
        return jsonify({"error": "Failed to load updated data"}), 500

    try:
        records = df.to_dict(orient="records")
        return jsonify(records)
    except Exception as e:
        logging.error(f"Failed to serialize data: {e}")
        return jsonify({"error": "Failed to serialize data"}), 500


if __name__ == "__main__":
    app.run(debug=True)
