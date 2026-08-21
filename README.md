# Stock Price Prediction using Python

A machine learning project that predicts the next trading day's AAPL closing price using historical stock-market data and a Random Forest Regressor.

## Project Overview

This project uses:
- `yfinance` to collect AAPL historical market data
- Pandas and NumPy for data preparation
- Moving averages for feature engineering
- Random Forest Regression for prediction
- MAE, MSE, RMSE and R² for evaluation
- Matplotlib for actual-vs-predicted visualization

## Project Structure

```text
stock-price-prediction/
├── README.md
├── requirements.txt
├── .gitignore
├── notebooks/
│   ├── Stock_Price_Prediction_Clean.ipynb
│   └── Stock_Price_Prediction_Project.ipynb
├── data/
│   └── README.md
└── images/
    └── README.md
```

## How to Run

### 1. Install Python

Use Python 3.10+.

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Open the notebook

```bash
jupyter notebook
```

Open:

`notebooks/Stock_Price_Prediction_Clean.ipynb`

### 4. Run all cells

The notebook downloads AAPL data from Yahoo Finance through `yfinance`, prepares the data, trains the model, evaluates it, and displays the prediction graph.

## Dataset

## Dataset

The project uses historical AAPL stock-market data.

The dataset used for the project is available in:

`data/stock_data.csv`

The notebook can also retrieve historical AAPL data using `yfinance`.

## Model

**Algorithm:** Random Forest Regressor

**Features:**
- Open
- High
- Low
- Volume
- 10-day moving average
- 50-day moving average

**Target:** Next trading day's closing price

## Evaluation Metrics

- Mean Absolute Error (MAE)
- Mean Squared Error (MSE)
- Root Mean Squared Error (RMSE)
- R² Score

## Important Note

The original uploaded notebook is preserved in the repository for reference. The `Stock_Price_Prediction_Clean.ipynb` notebook is the recommended version for your GitHub portfolio because it removes the unrelated/failed visualization section and uses a time-ordered train/test split.

This project is for educational purposes and is not financial advice. Stock prices are influenced by many factors that are not captured by this model.
