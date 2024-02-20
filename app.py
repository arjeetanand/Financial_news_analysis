from datetime import datetime, date
import numpy as np
from flask import Flask, render_template, request, jsonify, Response
from flask.json import JSONEncoder
import pandas as pd
import subprocess
import logging
from flask_caching import Cache
import math
import json


# Set up basic logging
logging.basicConfig(level=logging.DEBUG)


class CustomJSONEncoder(JSONEncoder):
    def default(self, obj):
        # Convert NaN values to None, which becomes 'null' in JSON
        if isinstance(obj, np.float) and np.isnan(obj):
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
    if news_symbol_filter:
        selected_stock = df_filtered_news[
            df_filtered_news["Triggered_Stock_Symbols"].str.contains(
                news_symbol_filter, case=False, na=False
            )
        ].iloc[
            0
        ]  # Assuming the first matching record is what we want
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


@app.route("/about")
def about():
    return render_template("/about.html")


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
