As an AI, I cannot generate an actual `.pdf` file for you to download directly. However, I have formatted the complete documentation below into a clean, formal layout.

You can copy the text below and paste it directly into **Google Docs**, **Microsoft Word**, or a Markdown editor, and then simply click **File > Download > PDF Document** (or **Print > Save as PDF**).

Here is the complete, final version ready for your portfolio:

---

### Nexus Pro | Global Markets Terminal ⚡

An institutional-grade trading dashboard and algorithmic market analysis terminal built with Python and Streamlit.

This application transforms raw market data into actionable intelligence, featuring live global asset tracking, AI-driven price forecasting, options chain exploration, strategy backtesting, and live paper trading integration via Alpaca.

#### 🌟 Key Features

* **Live Paper Trading Execution:** Direct API integration with Alpaca for executing Market and Limit orders, tracking portfolio equity, and managing open positions in real-time.
* **Global Market Coverage:** Real-time data routing for US Equities, Indian Equities (NSE/BSE), Global Indices (Nifty 50, Sensex), and Commodities (Crude Oil, Gold).
* **Advanced Interactive Charting:** Multi-pane Plotly charting featuring Candlesticks, Volume, Bollinger Bands, Moving Averages (SMA/EMA), and MACD momentum oscillators.
* **AI & Machine Learning:** Utilizes a `RandomForestRegressor` to calculate probabilistic next-session price targets, paired with an NLP sentiment analysis engine that scores live financial news.
* **Real-Time Options Chain:** Live derivatives data (Calls/Puts) including Strike, Bid/Ask, Open Interest, and Implied Volatility.
* **Algorithmic Strategy Backtester:** Simulates a Moving Average Crossover strategy against historical data, outputting quantitative risk metrics including Sharpe Ratio, Max Drawdown, and Alpha outperformance.

---

#### 📁 Project Structure

```text
stock-price-prediction/
├── streamlit_app.py       # Main Streamlit web application
├── requirements.txt       # Python dependencies
├── .gitignore
├── notebooks/             # Original exploratory ML notebooks
│   ├── Stock_Price_Prediction_Clean.ipynb
│   └── Stock_Price_Prediction_Project.ipynb
└── README.md

```

---

#### 🚀 How to Run Locally

**1. Install Dependencies**
Ensure you have Python 3.10+ installed. Clone the repository and install the required packages:

```bash
pip install -r requirements.txt

```

**2. Alpaca API Keys (Optional but Recommended)**
To use the live Trade Station and Portfolio features, you will need a free paper trading account from Alpaca.

* You can enter your API Key and Secret Key directly into the app's sidebar UI.
* Alternatively, for auto-login, set up a `.streamlit/secrets.toml` file in the root directory:

```toml
ALPACA_API_KEY = "your_api_key_here"
ALPACA_SECRET_KEY = "your_secret_key_here"

```

**3. Launch the Application**
Start the Streamlit server:

```bash
streamlit run streamlit_app.py

```

The terminal will open automatically in your web browser at `http://localhost:8501`.

---

#### 🛠️ Technology Stack

* **Frontend/Framework:** Streamlit
* **Data Pipelines:** yfinance, Pandas, NumPy
* **Machine Learning:** Scikit-Learn (RandomForestRegressor)
* **Data Visualization:** Plotly (plotly.graph_objects)
* **Brokerage API:** alpaca-py

---

#### ⚠️ Important Note / Disclaimer

This project is for educational and portfolio purposes only and does **not** constitute financial advice. The machine learning models provide probabilistic estimates based on historical data, which cannot guarantee future market performance. Always perform your own due diligence before trading real capital.
