# Financial News Analysis for Indian Stocks

A full-stack AI/ML project that **scrapes business news, classifies sentiment with FinBERT, maps news to NSE stock symbols, enriches records with market indicators, and serves an interactive Flask dashboard**.

## What this project does

This project has two major parts:

1. **Data pipeline (`indian_stock_sentiment_from_news_headlines_project.py`)**
   - Scrapes stock-market news from Economic Times and Moneycontrol.
   - Parses and combines headlines/summaries into a single dataset.
   - Runs transformer-based sentiment analysis (`yiyanghkust/finbert-tone`).
   - Applies rule-based sentiment adjustment for finance keywords.
   - Maps mentioned companies to stock symbols.
   - Pulls historical price data with `yfinance` and computes technical indicators:
     - SMA (10, 20, 50)
     - RSI
     - MACD + signal line
   - Produces model-ready/serving-ready outputs (`final.parquet`, `updated_final.xlsx`).

2. **Web app (`app.py`)**
   - Loads the generated Excel dataset.
   - Provides:
     - **Dashboard (`/`)** with sentiment buckets and paginated news.
     - **Symbol search API (`/search_stocks`)** for frontend filtering.
     - **Stock details API (`/stock_details/<symbol>`)** with JSON-safe serialization.
     - **Script trigger route (`/run-script`)** to refresh data pipeline output.
     - **About page (`/about`)**.
   - Uses simple Flask caching to reduce repeated dashboard compute.

---

## Latest changes

Recent updates (from the latest merged work) include:

- Fix for a **dashboard filter edge-case crash** when filtering by an unknown symbol.
- Added **route-level regression tests** for key app endpoints:
  - `/search_stocks`
  - `/stock_details/<symbol>`
  - dashboard with unknown `news_symbol` filter

These tests are in `tests/test_app_routes.py` and help prevent regressions in user-facing behavior.

---

## Project structure

```text
.
├── app.py
├── indian_stock_sentiment_from_news_headlines_project.py
├── tests/
│   └── test_app_routes.py
├── templates/
├── static/
├── requirements.txt
├── final.parquet
└── updated_final.xlsx
```

---

## Setup

### 1) Create and activate a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate
```

### 2) Install dependencies

```bash
pip install -r requirements.txt
```

If your `requirements.txt` is incomplete, install core packages manually:

```bash
pip install flask flask-caching pandas numpy yfinance beautifulsoup4 transformers torch pyarrow python-dateutil pytz openpyxl pytest
```

---

## Run the data pipeline

```bash
python indian_stock_sentiment_from_news_headlines_project.py
```

Expected outputs:

- `combined_summaries.parquet`
- `final.parquet`
- `updated_final.xlsx`

---

## Run the Flask app

```bash
python app.py
```

Then open:

- `http://127.0.0.1:5000/`

Production deployment reference (if active):

- `https://financialnewsanalysis-production.up.railway.app/`

---

## Run tests

```bash
pytest -q
```

---

## Known limitations

- Scraping selectors are source-site dependent and can break if page HTML changes.
- Symbol matching is rule-based and may miss aliases/abbreviations.
- Pipeline is batch-style; no scheduler/orchestration included yet.
- No model evaluation dashboard (precision/recall/F1 by label) is currently tracked.

---

## How to make this a standout AI/ML resume project

Below is a **part-by-part implementation plan**. We are now starting with **Part 1** and added working open-source code under `mlops/`.

### Part 1 (implemented): Productionize data + model pipeline

What is now included:
- `mlops/contracts.py`: lightweight data-contract checks (required columns, sentiment labels, duplicate warnings).
- `mlops/artifacts.py`: local artifact registry with SHA-256 hashes for reproducibility.
- `mlops/pipeline_cli.py`: CLI to validate output files and write lineage + artifact metadata.

Run it on your generated dataset:

```bash
python -m mlops.pipeline_cli --input updated_final.xlsx
```

Artifacts generated:
- `artifacts/registry.json`
- `artifacts/lineage.json`

### Part 2 (implemented): Add MLOps discipline

What is now included:
- `mlops/experiments.py`: a tiny local experiment tracker that logs model runs and metrics to `artifacts/experiments.jsonl`.
- `mlops/drift.py`: sentiment distribution drift detection using PSI (Population Stability Index).
- `mlops/pipeline_cli.py` now supports:
  - `--track-experiment` to persist each run as an experiment record
  - `--baseline` and `--drift-threshold` to compute and store drift reports

Example:

```bash
python -m mlops.pipeline_cli \
  --input updated_final.xlsx \
  --baseline updated_final.xlsx \
  --track-experiment
```

### Part 3 (implemented): Improve entity linking quality

What is now included:
- `mlops/entity_linking.py`: reusable `EntityLinker` with normalization, alias expansion, exact/symbol matching, and fuzzy fallback.
- DataFrame helper that adds `Linked_Company_Names`, `Linked_Symbols`, and `Entity_Link_Score`.
- `evaluate_entity_linking(...)` utility to benchmark symbol mapping accuracy against a labeled set.
- `mlops/pipeline_cli.py` support for labeled evaluation via `--entity-labels`, `--pred-col`, and `--label-col`.

Example:

```bash
python -m mlops.pipeline_cli \
  --input updated_final.xlsx \
  --entity-labels labeled_symbols.csv \
  --pred-col Triggered_Stock_Symbols \
  --label-col True_Symbol
```

### Part 4 (implemented): Demonstrate measurable business value

What is now included:
- `mlops/business_value.py`: event-study backtest helpers for sentiment vs. forward returns.
- Reported metrics include `coverage`, `hit_rate`, `average_forward_return`, `strategy_mean_return`, and `strategy_sharpe_like`.
- Sentiment calibration table generation (bucket counts + mean forward return).
- `mlops/pipeline_cli.py` supports `--run-backtest`, `--entry-price-col`, `--exit-price-col`, and records backtest outputs in lineage.

Example:

```bash
python -m mlops.pipeline_cli \
  --input updated_final.xlsx \
  --run-backtest \
  --entry-price-col News_day \
  --exit-price-col News_Day_After
```

### Part 5 (implemented): Serve inference as APIs

What is now included:
- `mlops/inference.py`: modular inference service with open-source, rule-based sentiment and entity inference wrappers.
- New Flask inference endpoints in `app.py`:
  - `POST /api/v1/inference/sentiment`
  - `POST /api/v1/inference/entities`
  - `POST /api/v1/inference/news`
- Request validation + JSON responses suitable for integration from frontend or external services.

Example requests:

```bash
curl -X POST http://127.0.0.1:5000/api/v1/inference/sentiment \
  -H "Content-Type: application/json" \
  -d '{"text": "TCS gains after upbeat guidance"}'

curl -X POST http://127.0.0.1:5000/api/v1/inference/news \
  -H "Content-Type: application/json" \
  -d '{"headline": "Infosys wins mega deal", "summary": "Shares rally on order win"}'
```

### Part 6 (implemented): Harden software engineering quality

What is now included:
- `pyproject.toml` with formatter/linter/test settings (`black`, `ruff`, pytest defaults).
- GitHub Actions CI workflow (`.github/workflows/ci.yml`) for lint, format-check, and test automation.

### Part 7 (implemented): Upgrade front-end storytelling

What is now included:
- `GET /api/v1/sentiment_trend` endpoint in `app.py` returning date-wise sentiment counts.
- New dashboard visualization section in `templates/html.html`.
- Frontend chart rendering in `static/js/js.js` using Chart.js to show sentiment trends over time.
- Added model explanation workflow:
  - `POST /api/v1/inference/explain` endpoint returning sentiment label, confidence, and keyword-level rationale.
  - UI explainer panel to inspect prediction explanations directly from the dashboard.
- Supporting styles for the new chart and explainer cards in `static/css/style.css`.

---

To elevate this from a good student project to a strong AI/ML engineer portfolio project:

1. **Productionize data + model pipeline**
   - Use Airflow/Prefect for scheduled runs.
   - Add data validation with Great Expectations.
   - Track lineage and artifact versions (DVC or MLflow Artifacts).

2. **Add MLOps discipline**
   - Track experiments in MLflow (model version, hyperparameters, metrics).
   - Add automated retraining triggers and drift detection.
   - Create model cards and dataset cards.

3. **Improve entity linking quality**
   - Replace string matching with NER + entity resolution.
   - Add fuzzy matching and ticker disambiguation.
   - Benchmark mapping accuracy on a labeled validation set.

4. **Demonstrate measurable business value**
   - Create event-study style backtests (news sentiment vs. subsequent returns).
   - Report hit-rate, Sharpe-like proxy, and calibration plots.
   - Add baseline comparisons (lexicon sentiment vs FinBERT vs finetuned model).

5. **Serve inference as APIs**
   - Split ETL, inference, and serving into modular services.
   - Add FastAPI endpoints with OpenAPI docs.
   - Containerize with Docker and deploy on cloud (AWS/GCP/Azure).

6. **Harden software engineering quality**
   - Add linting/formatting (`ruff`, `black`) + type checks (`mypy`).
   - Expand test coverage to pipeline logic and data contracts.
   - Add CI/CD (GitHub Actions) for tests, build, deploy.

7. **Upgrade front-end storytelling**
   - Add interactive charts (Plotly/ECharts) for sentiment trend by symbol/date.
   - Show model confidence and explanation snippets.
   - Add downloadable reports for recruiters/interview demos.

---

## Acknowledgments

- `yiyanghkust/finbert-tone` for finance sentiment modeling
- `yfinance` for market data
- Economic Times and Moneycontrol as source websites
- Flask for rapid dashboard/API development
