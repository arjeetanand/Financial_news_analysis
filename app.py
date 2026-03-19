from datetime import datetime, date
import json
import logging
import math
import warnings

import numpy as np
import pandas as pd
from flask import Flask, Response, jsonify, render_template, request
from flask_caching import Cache
from json import JSONEncoder

warnings.filterwarnings("ignore", message=".*This is a development server.*")
logging.basicConfig(level=logging.DEBUG)


class CustomJSONEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, np.number):
            if np.isnan(obj):
                return None
            return obj.item()
        return JSONEncoder.default(self, obj)


app = Flask(__name__)
cache = Cache(app, config={"CACHE_TYPE": "simple"})
app.config["CACHE_TYPE"] = "SimpleCache"
cache.init_app(app)
app.json_encoder = CustomJSONEncoder

DATA_FILE = "updated_final.xlsx"
df = pd.DataFrame()
trade_score_df = pd.DataFrame()
model_funds_df = pd.DataFrame()
alerts_df = pd.DataFrame()


def _safe_float(value):
    try:
        if pd.isna(value):
            return None
        return float(value)
    except Exception:
        return None


def _sentiment_score(text):
    value = str(text).strip().lower()
    mapping = {"positive": 1.0, "neutral": 0.5, "negative": 0.0}
    return mapping.get(value, 0.5)


def _trend_score(row):
    sma_10 = _safe_float(row.get("SMA_10"))
    sma_20 = _safe_float(row.get("SMA_20"))
    if sma_10 is None or sma_20 is None:
        return 0.5
    if sma_10 > sma_20:
        return 1.0
    if sma_10 < sma_20:
        return 0.0
    return 0.5


def _rsi_score(rsi_value):
    rsi = _safe_float(rsi_value)
    if rsi is None:
        return 0.5
    # Prefer neither overbought nor oversold; balanced momentum gets best score
    distance = abs(rsi - 50.0)
    return max(0.0, min(1.0, 1 - (distance / 50.0)))


def _volatility_penalty(row):
    before = _safe_float(row.get("News_Day_Before"))
    day = _safe_float(row.get("News_day"))
    after = _safe_float(row.get("News_Day_After"))

    points = [v for v in [before, day, after] if v is not None and v > 0]
    if len(points) < 2:
        return 0.2

    returns = []
    for i in range(1, len(points)):
        prev = points[i - 1]
        curr = points[i]
        returns.append((curr - prev) / prev)

    std_dev = float(np.std(returns)) if returns else 0.0
    return max(0.0, min(1.0, std_dev * 10))


def _trade_score_components(row):
    sentiment = _sentiment_score(row.get("Adjusted_Sentiment", row.get("Sentiment")))
    trend = _trend_score(row)
    rsi = _rsi_score(row.get("RSI"))
    volatility = _volatility_penalty(row)

    # Composite score with risk penalty
    raw = (0.35 * sentiment) + (0.35 * trend) + (0.3 * rsi)
    adjusted = max(0.0, min(1.0, raw - (0.25 * volatility)))

    return {
        "sentiment_component": round(sentiment * 100, 2),
        "trend_component": round(trend * 100, 2),
        "rsi_component": round(rsi * 100, 2),
        "risk_penalty": round(volatility * 100, 2),
        "trade_setup_score": round(adjusted * 100, 2),
    }


def _build_explanation(row, components):
    reasons = []

    adj_sentiment = str(row.get("Adjusted_Sentiment", row.get("Sentiment", "neutral"))).lower()
    if adj_sentiment == "positive":
        reasons.append("Positive adjusted sentiment from recent news flow")
    elif adj_sentiment == "negative":
        reasons.append("Negative adjusted sentiment suggests caution")
    else:
        reasons.append("Neutral sentiment keeps conviction moderate")

    sma_10 = _safe_float(row.get("SMA_10"))
    sma_20 = _safe_float(row.get("SMA_20"))
    if sma_10 and sma_20:
        if sma_10 > sma_20:
            reasons.append("Bullish trend: SMA-10 is above SMA-20")
        elif sma_10 < sma_20:
            reasons.append("Bearish trend: SMA-10 is below SMA-20")

    rsi = _safe_float(row.get("RSI"))
    if rsi is not None:
        if rsi > 70:
            reasons.append("RSI indicates overbought risk")
        elif rsi < 30:
            reasons.append("RSI indicates oversold rebound potential")
        else:
            reasons.append("RSI is in a healthier middle range")

    if components["risk_penalty"] > 40:
        reasons.append("Higher short-term volatility lowered confidence")

    return reasons[:4]


def build_trade_scores(source_df):
    if source_df.empty:
        return pd.DataFrame()

    temp = source_df.copy()
    temp = temp.dropna(subset=["Triggered_Stock_Symbols"]).copy()

    rows = []
    for _, row in temp.iterrows():
        components = _trade_score_components(row)
        reasons = _build_explanation(row, components)
        rows.append(
            {
                "symbol": str(row.get("Triggered_Stock_Symbols")).upper(),
                "stock_name": str(row.get("Triggered_Stock_Names", "")).strip(", "),
                "headline": row.get("Headline", ""),
                **components,
                "explanations": reasons,
            }
        )

    scored = pd.DataFrame(rows)
    if scored.empty:
        return scored

    ranked = (
        scored.sort_values("trade_setup_score", ascending=False)
        .drop_duplicates(subset=["symbol"], keep="first")
        .reset_index(drop=True)
    )
    return ranked


def build_model_funds(scores_df):
    if scores_df.empty:
        return pd.DataFrame()

    universe = scores_df.copy()
    universe["risk"] = universe["risk_penalty"]

    def _make_bucket(name, frame):
        if frame.empty:
            return None

        now_score = frame["trade_setup_score"].mean()
        quality_score = (
            (100 - frame["risk"].mean()) * 0.4
            + frame["trend_component"].mean() * 0.3
            + frame["sentiment_component"].mean() * 0.3
        )
        future_score = min(100.0, max(0.0, quality_score))
        combined = (0.55 * now_score) + (0.45 * future_score)
        return {
            "fund_name": name,
            "now_score": round(now_score, 2),
            "future_score": round(future_score, 2),
            "combined_score": round(combined, 2),
            "holdings": ", ".join(frame["symbol"].head(5).tolist()),
            "avg_risk_penalty": round(frame["risk"].mean(), 2),
        }

    candidates = []
    candidates.append(_make_bucket("Momentum Leaders Fund", universe.nlargest(12, "trend_component")))
    candidates.append(_make_bucket("Sentiment Alpha Fund", universe.nlargest(12, "sentiment_component")))
    candidates.append(_make_bucket("Balanced Growth Fund", universe.nlargest(15, "trade_setup_score")))
    candidates.append(_make_bucket("Low Volatility Shield Fund", universe.nsmallest(12, "risk")))

    result = pd.DataFrame([c for c in candidates if c])
    if result.empty:
        return result

    return result.sort_values("combined_score", ascending=False).reset_index(drop=True)


def build_alerts(scores_df):
    if scores_df.empty:
        return pd.DataFrame()

    alerts = []
    for _, row in scores_df.iterrows():
        score = row["trade_setup_score"]
        risk = row["risk_penalty"]
        if score >= 75:
            level = "BUY WATCH"
            message = "Setup score is high with supportive trend/sentiment"
        elif score <= 35:
            level = "AVOID"
            message = "Low setup score indicates weak conditions"
        elif risk >= 45:
            level = "RISK ALERT"
            message = "Volatility risk is elevated"
        else:
            continue

        alerts.append(
            {
                "symbol": row["symbol"],
                "level": level,
                "score": round(score, 2),
                "risk_penalty": round(risk, 2),
                "message": message,
            }
        )

    return pd.DataFrame(alerts).head(20)


def backtest_news_reaction(source_df, symbol=None, min_score=60, holding_days=1):
    if source_df.empty:
        return {
            "trades": 0,
            "win_rate": 0,
            "avg_return": 0,
            "total_return": 0,
            "message": "No data available for backtesting.",
        }

    temp = source_df.copy()
    if symbol:
        temp = temp[temp["Triggered_Stock_Symbols"].str.upper() == symbol.upper()]

    trades = []
    for _, row in temp.iterrows():
        components = _trade_score_components(row)
        score = components["trade_setup_score"]
        if score < min_score:
            continue

        entry = _safe_float(row.get("News_day")) or _safe_float(row.get("News_Day_Before"))
        exit_price = _safe_float(row.get("News_Day_After"))
        if entry is None or exit_price is None or entry == 0:
            continue

        ret = ((exit_price - entry) / entry) * 100
        trades.append(ret)

    if not trades:
        return {
            "trades": 0,
            "win_rate": 0,
            "avg_return": 0,
            "total_return": 0,
            "message": "No qualifying trades for selected filters.",
        }

    win_rate = (sum(1 for r in trades if r > 0) / len(trades)) * 100
    avg_return = float(np.mean(trades))
    total_return = float(np.sum(trades))

    return {
        "trades": len(trades),
        "win_rate": round(win_rate, 2),
        "avg_return": round(avg_return, 2),
        "total_return": round(total_return, 2),
        "holding_days": holding_days,
        "message": "Backtest generated from news-day to next-day move proxy.",
    }


def compute_portfolio_overlap(scores_df, base_symbols_csv, candidate_symbols_csv):
    base = {x.strip().upper() for x in base_symbols_csv.split(",") if x.strip()}
    candidate = {x.strip().upper() for x in candidate_symbols_csv.split(",") if x.strip()}

    if not base or not candidate:
        return {
            "overlap_count": 0,
            "overlap_ratio": 0,
            "common_symbols": [],
            "message": "Enter both base and candidate portfolio symbols.",
        }

    common = sorted(base.intersection(candidate))
    ratio = (len(common) / len(candidate)) * 100 if candidate else 0

    # diversification score: higher overlap => lower diversification
    diversification_gain = max(0.0, 100 - ratio)

    return {
        "overlap_count": len(common),
        "overlap_ratio": round(ratio, 2),
        "common_symbols": common,
        "diversification_gain": round(diversification_gain, 2),
        "message": "Lower overlap ratio indicates better diversification potential.",
    }


def refresh_analytics():
    global df, trade_score_df, model_funds_df, alerts_df
    df = pd.read_excel(DATA_FILE)
    trade_score_df = build_trade_scores(df)
    model_funds_df = build_model_funds(trade_score_df)
    alerts_df = build_alerts(trade_score_df)


refresh_analytics()


@app.route("/")
@cache.cached(timeout=50, query_string=True)
def dashboard():
    stock_query = request.args.get("stock", None)
    news_symbol_filter = request.args.get("news_symbol", "")
    min_score = request.args.get("min_score", 60, type=int)
    backtest_symbol = request.args.get("backtest_symbol", "")
    base_symbols = request.args.get("base_symbols", "")
    candidate_symbols = request.args.get("candidate_symbols", "")

    unique_stock_symbols = df["Triggered_Stock_Symbols"].dropna().unique().tolist()

    if stock_query:
        filtered_df = df[
            (df["Triggered_Stock_Names"].str.contains(stock_query, case=False, na=False))
            | (df["Triggered_Stock_Symbols"].str.contains(stock_query, case=False, na=False))
        ]
        stock_data = filtered_df.iloc[0].to_dict() if not filtered_df.empty else None
    else:
        stock_data = None

    if news_symbol_filter:
        df_filtered_news = df[df["Triggered_Stock_Symbols"].str.contains(news_symbol_filter, case=False, na=False)]
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
    sentiments_ordered = ["positive", "negative", "neutral"]
    sentiments = {
        sentiment: df_nonan[df_nonan["Sentiment"].str.lower() == sentiment]
        .drop_duplicates(subset=["Triggered_Stock_Symbols"])
        .to_dict(orient="records")
        for sentiment in sentiments_ordered
    }

    if news_symbol_filter and not df_filtered_news.empty:
        selected_stock = df_filtered_news.iloc[0]
        stock_prices = {
            "price_day_before": selected_stock.get("News_Day_Before"),
            "price_day_of": selected_stock.get("News_day"),
        }
    else:
        stock_prices = {"price_day_before": None, "price_day_of": None}

    top_trade_setups = trade_score_df.head(10).to_dict(orient="records") if not trade_score_df.empty else []
    model_funds = model_funds_df.to_dict(orient="records") if not model_funds_df.empty else []
    alerts = alerts_df.to_dict(orient="records") if not alerts_df.empty else []

    backtest_result = backtest_news_reaction(df, symbol=backtest_symbol or None, min_score=min_score, holding_days=1)
    overlap_result = compute_portfolio_overlap(trade_score_df, base_symbols, candidate_symbols)

    return render_template(
        "html.html",
        sentiments=sentiments,
        stock_data=stock_data,
        news_list=news_list,
        stock_prices=stock_prices,
        page=page,
        pages=pages,
        unique_stock_symbols=unique_stock_symbols,
        top_trade_setups=top_trade_setups,
        model_funds=model_funds,
        alerts=alerts,
        backtest_result=backtest_result,
        min_score=min_score,
        backtest_symbol=backtest_symbol,
        base_symbols=base_symbols,
        candidate_symbols=candidate_symbols,
        overlap_result=overlap_result,
    )


@app.route("/search_stocks")
def search_stocks():
    query = request.args.get("q", "").lower()
    if query:
        results = df["Triggered_Stock_Symbols"].fillna("").str.lower().str.contains(query)
        unique_symbols = df.loc[results, "Triggered_Stock_Symbols"].unique().tolist()
        return jsonify(unique_symbols)
    return jsonify([])


@app.route("/stock_details/<symbol>")
def stock_details(symbol):
    symbol = symbol.upper()
    stock_data = df[df["Triggered_Stock_Symbols"].str.upper() == symbol]
    cleaned_data = stock_data.replace({np.nan: None}).to_dict(orient="records")

    if trade_score_df.empty:
        enriched = cleaned_data
    else:
        score_map = trade_score_df.set_index("symbol").to_dict(orient="index")
        enriched = []
        for item in cleaned_data:
            sym = str(item.get("Triggered_Stock_Symbols", "")).upper()
            score_info = score_map.get(sym, {})
            item["Trade_Setup_Score"] = score_info.get("trade_setup_score")
            item["Trade_Explainability"] = score_info.get("explanations", [])
            enriched.append(item)

    cleaned_data_str = [{k: str(v) for k, v in item.items()} for item in enriched]
    json_data = json.dumps(cleaned_data_str)
    return Response(json_data, mimetype="application/json")


@app.route("/api/fund_screener")
def fund_screener_api():
    sort_by = request.args.get("sort_by", "combined_score")
    safe_sort = sort_by if sort_by in {"combined_score", "now_score", "future_score"} else "combined_score"

    if model_funds_df.empty:
        return jsonify([])

    response = model_funds_df.sort_values(safe_sort, ascending=False).to_dict(orient="records")
    return jsonify(response)


@app.route("/api/backtest")
def backtest_api():
    symbol = request.args.get("symbol", "")
    min_score = request.args.get("min_score", 60, type=int)
    result = backtest_news_reaction(df, symbol=symbol or None, min_score=min_score)
    return jsonify(result)


@app.route("/api/alerts")
def alerts_api():
    return jsonify(alerts_df.to_dict(orient="records") if not alerts_df.empty else [])


@app.route("/api/portfolio_overlap")
def portfolio_overlap_api():
    base_symbols = request.args.get("base_symbols", "")
    candidate_symbols = request.args.get("candidate_symbols", "")
    result = compute_portfolio_overlap(trade_score_df, base_symbols, candidate_symbols)
    return jsonify(result)


@app.route("/about")
def about():
    return render_template("/about.html")


@app.route("/run-script")
def run_script():
    logging.info("Starting script execution")
    try:
        script_path = "indian_stock_sentiment_from_news_headlines_project.py"
        import subprocess

        subprocess.run(["python", script_path], check=True)
        logging.info("Script execution completed")
    except Exception as e:
        logging.error(f"Script execution failed: {e}")
        return jsonify({"error": "Script execution failed"}), 500

    try:
        refresh_analytics()
    except Exception as e:
        logging.error(f"Failed to load refreshed data: {e}")
        return jsonify({"error": "Failed to load updated data"}), 500

    try:
        records = df.to_dict(orient="records")
        return jsonify(records)
    except Exception as e:
        logging.error(f"Failed to serialize data: {e}")
        return jsonify({"error": "Failed to serialize data"}), 500


if __name__ == "__main__":
    app.run(debug=True)
