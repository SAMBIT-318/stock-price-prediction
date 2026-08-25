import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error
from datetime import date, timedelta

# 1. Set up professional layout
st.set_page_config(page_title="AI Stock Predictor", layout="wide")
st.title("🚀 Advanced AI Stock Price Predictor")
st.write("Predicts the next trading day's closing price using Machine Learning and Technical Indicators.")

# 2. Sidebar for User Input
st.sidebar.header("⚙️ Dashboard Settings")
ticker = st.sidebar.text_input("Enter Stock Ticker:", "AAPL").upper()
years = st.sidebar.slider("Years of Historical Data to Train:", 1, 10, 5)

# 3. Fetch data dynamically
@st.cache_data
def load_data(ticker, years):
    start_date = date.today() - timedelta(days=365 * years)
    data = yf.download(ticker, start=start_date, end=date.today(), progress=False)
    
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
        
    data.reset_index(inplace=True)
    return data

data_load_state = st.text(f'Fetching live market data for {ticker}...')
df = load_data(ticker, years)
data_load_state.empty() # Clears the loading text once done

# Safety check if user types an invalid ticker
if df.empty:
    st.error(f"No data found for '{ticker}'. Please enter a valid Yahoo Finance ticker.")
    st.stop()

# 4. Feature Engineering (Making the model smarter)
# Adding Simple Moving Averages (SMA) to help the model detect trends
df['SMA_10'] = df['Close'].rolling(window=10).mean()
df['SMA_50'] = df['Close'].rolling(window=50).mean()
df['Prev_Close'] = df['Close'].shift(1)
df = df.dropna() # Remove early rows that don't have enough data for the 50-day average

# 5. Dashboard Layout - Top Charts
col1, col2 = st.columns([2, 1]) # Make the chart column twice as wide as the data table

with col1:
    st.subheader(f"📈 {ticker} Price & Trendlines")
    # Plotting Close price alongside our new Moving Averages
    st.line_chart(df.set_index('Date')[['Close', 'SMA_10', 'SMA_50']])

with col2:
    st.subheader("📊 Recent Market Data")
    st.dataframe(df[['Date', 'Close', 'SMA_10', 'SMA_50']].tail(8), hide_index=True)

# 6. Prepare Machine Learning Model
st.write("---")
st.subheader("🤖 AI Prediction Engine")

# Features the model will learn from
features = ['Prev_Close', 'SMA_10', 'SMA_50']
X = df[features]
y = df['Close']

# Train/Test Split (to calculate model accuracy)
split_idx = int(len(df) * 0.8) # Train on first 80%, test on last 20%
X_train, X_test = X[:split_idx], X[split_idx:]
y_train, y_test = y[:split_idx], y[split_idx:]

# Train the model
model = RandomForestRegressor(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# Calculate model error
predictions = model.predict(X_test)
mae = mean_absolute_error(y_test, predictions)

# 7. Predict the NEXT day
last_row = df.iloc[-1]
input_df = pd.DataFrame({
    'Prev_Close': [float(last_row['Close'])],
    'SMA_10': [float(last_row['SMA_10'])],
    'SMA_50': [float(last_row['SMA_50'])]
})

next_day_prediction = model.predict(input_df)[0]
last_close = float(last_row['Close'])

# 8. Display Final Results in nice columns
metric1, metric2, metric3 = st.columns(3)

with metric1:
    st.metric(label=f"Current Close Price ({ticker})", value=f"${last_close:.2f}")
    
with metric2:
    st.metric(
        label="AI Predicted Next Close", 
        value=f"${next_day_prediction:.2f}",
        delta=f"${next_day_prediction - last_close:.2f} expected change"
    )

with metric3:
    st.metric(
        label="Model Error (MAE)", 
        value=f"${mae:.2f}",
        help="Mean Absolute Error: On average, the model's historical predictions were off by this dollar amount."
    )
