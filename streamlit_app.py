import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, mean_absolute_percentage_error
from datetime import date, timedelta

# --- PAGE SETUP ---
st.set_page_config(page_title="Advanced AI Stock Quant", layout="wide")
st.title("🧠 Advanced AI Quant Stock Predictor")
st.write("Professional-grade machine learning dashboard with 10 advanced analytical features.")

# --- SIDEBAR: ADVANCED FEATURES 1 & 2 ---
st.sidebar.header("⚙️ AI Configuration Engine")
ticker = st.sidebar.text_input("Enter Stock Ticker:", "AAPL").upper()
years = st.sidebar.slider("Years of Historical Data:", 1, 10, 5)

st.sidebar.markdown("### 1. AI Model Selector")
ai_model_type = st.sidebar.selectbox("Choose Machine Learning Algorithm:", ["Random Forest", "Gradient Boosting"])

st.sidebar.markdown("### 2. AI Hyperparameter Tuning")
n_trees = st.sidebar.slider("Number of AI Trees (Estimators):", 50, 300, 100, step=50)

# --- DATA FETCHING ---
@st.cache_data
def load_data(ticker, years):
    start_date = date.today() - timedelta(days=365 * years)
    data = yf.download(ticker, start=start_date, end=date.today(), progress=False)
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    data.reset_index(inplace=True)
    return data

df = load_data(ticker, years)
if df.empty:
    st.error(f"No data found for '{ticker}'.")
    st.stop()

# --- FEATURE ENGINEERING (FEATURES 3, 4, 5, 6) ---
st.write("---")
st.subheader("📊 Advanced Feature Engineering")

# 3. RSI (Relative Strength Index)
delta = df['Close'].diff()
gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
rs = gain / loss
df['RSI_14'] = 100 - (100 / (1 + rs))

# 4. MACD (Moving Average Convergence Divergence)
exp1 = df['Close'].ewm(span=12, adjust=False).mean()
exp2 = df['Close'].ewm(span=26, adjust=False).mean()
df['MACD'] = exp1 - exp2

# 5. Bollinger Bands
df['BB_Mid'] = df['Close'].rolling(window=20).mean()
df['BB_Std'] = df['Close'].rolling(window=20).std()
df['BB_Upper'] = df['BB_Mid'] + (df['BB_Std'] * 2)
df['BB_Lower'] = df['BB_Mid'] - (df['BB_Std'] * 2)

# 6. Market Risk Engine (Annualized Volatility)
df['Volatility'] = df['Close'].pct_change().rolling(window=20).std() * np.sqrt(252)

df['Prev_Close'] = df['Close'].shift(1)
df = df.dropna() # Drop NaN values created by rolling windows

with st.expander("View Engineered AI Dataset (Technical Indicators)"):
    st.dataframe(df[['Date', 'Close', 'RSI_14', 'MACD', 'BB_Upper', 'BB_Lower', 'Volatility']].tail(10))

# --- MACHINE LEARNING PREPARATION ---
features = ['Prev_Close', 'RSI_14', 'MACD', 'BB_Upper', 'BB_Lower', 'Volatility']
X = df[features]
y = df['Close']

split_idx = int(len(df) * 0.8)
X_train, X_test = X[:split_idx], X[split_idx:]
y_train, y_test = y[:split_idx], y[split_idx:]

# Initialize selected model
if ai_model_type == "Random Forest":
    model = RandomForestRegressor(n_estimators=n_trees, random_state=42)
else:
    model = GradientBoostingRegressor(n_estimators=n_trees, random_state=42)

model.fit(X_train, y_train)
test_predictions = model.predict(X_test)

# --- ADVANCED EVALUATION (FEATURES 7, 8, 9, 10) ---
st.write("---")
st.subheader("🔬 AI Engine Diagnostics & Predictions")

col1, col2 = st.columns(2)

with col1:
    # 7. AI Explainability (Feature Importance)
    st.markdown("### 7. AI Explainability (XAI)")
    st.write("Which features drove the AI's decision?")
    importance_df = pd.DataFrame({'Importance': model.feature_importances_}, index=features).sort_values(by='Importance', ascending=True)
    st.bar_chart(importance_df, horizontal=True)

with col2:
    # 8. Historical Backtesting
    st.markdown("### 8. Backtesting Visualization")
    st.write("Actual vs Predicted Prices (Test Set)")
    backtest_df = pd.DataFrame({'Actual': y_test.values, 'Predicted': test_predictions}, index=df['Date'].iloc[split_idx:])
    st.line_chart(backtest_df)

# 9. Deep Quant Metrics
mae = mean_absolute_error(y_test, test_predictions)
rmse = np.sqrt(mean_squared_error(y_test, test_predictions))
mape = mean_absolute_percentage_error(y_test, test_predictions) * 100

st.markdown("### 9. Deep Quant Metrics")
m1, m2, m3 = st.columns(3)
m1.metric("Mean Absolute Error (MAE)", f"${mae:.2f}")
m2.metric("Root Mean Squared Error", f"${rmse:.2f}")
m3.metric("Mean Abs Percentage Error", f"{mape:.2f}%")

# 10. AI Confidence Bands & Future Prediction
last_row = df.iloc[-1]
input_df = pd.DataFrame({
    'Prev_Close': [float(last_row['Close'])],
    'RSI_14': [float(last_row['RSI_14'])],
    'MACD': [float(last_row['MACD'])],
    'BB_Upper': [float(last_row['BB_Upper'])],
    'BB_Lower': [float(last_row['BB_Lower'])],
    'Volatility': [float(last_row['Volatility'])]
})

next_pred = model.predict(input_df)[0]
last_close = float(last_row['Close'])

st.write("---")
st.markdown("### 10. Final Prediction & AI Confidence Bounds")
st.write(f"Based on closing data from {last_row['Date'].strftime('%Y-%m-%d')}")

p1, p2, p3 = st.columns(3)
p1.metric(label="Predicted Next Close", value=f"${next_pred:.2f}", delta=f"${next_pred - last_close:.2f}")
p2.metric(label="Best Case (Upper Bound)", value=f"${next_pred + mae:.2f}", help="Prediction + historical MAE")
p3.metric(label="Worst Case (Lower Bound)", value=f"${next_pred - mae:.2f}", help="Prediction - historical MAE")
