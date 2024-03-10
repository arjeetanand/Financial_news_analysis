# stocknews_analysis

## Overview

This project combines a Python-based analysis script and a Flask application to analyze financial news sentiment and its impact on stock prices. The Python script scrapes, processes, and analyzes financial news, while the Flask application provides an interactive interface for users to explore the analysis results.

## Getting Started

### Prerequisites
- Python 3.x
- Flask
- Pandas
- NumPy
- yfinance
- BeautifulSoup
- Transformers

Install the required libraries using:

pip install flask pandas numpy yfinance beautifulsoup4 transformers

## Running the Python Analysis Script

### Description
The script scrapes financial news, analyzes sentiment using the FinBERT model, and calculates various stock indicators.

### Execution
Run the following command to perform the analysis and generate the data file updated_final.xlsx:
python indian_stock_sentiment_from_news_headlines_project.py

## Running the Flask Application

### Setup
Ensure the data file updated_final.xlsx is in the same directory as the Flask app.

### Execution
Run the following command to start the server:


## Execution:
Access the web interface at [https://financialnewsanalysis-production.up.railway.app/](https://financialnewsanalysis-production.up.railway.app/).


## Features
- Financial News Scraping and Analysis: Automates the collection and sentiment analysis of financial news.
- Stock Price Retrieval and Analysis: Fetches and analyzes stock prices related to the news articles.
- Interactive Web Interface: Users can filter news by stock symbols, view sentiment analysis, and compare stock prices.

## Flask Application Routes
- `/`: Main dashboard displaying stock news and analysis.
- `/search_stocks`: AJAX endpoint for stock symbol search.
- `/stock_details/`: Detailed stock information and sentiment analysis.
- `/run-script`: Trigger background script execution for data update.

## Acknowledgments
- FinBERT model for sentiment analysis
- yfinance for stock data
- BeautifulSoup for web scraping
