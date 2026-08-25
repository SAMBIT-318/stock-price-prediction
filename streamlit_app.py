import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, mean_absolute_percentage_error
from datetime import date, timedelta

# --- 1. PAGE SETUP (Futuristic Wide Layout) ---
st.set_page_config(page_title="Nexus Quant | AI Stock Engine", layout="wide", initial_sidebar_state="expanded")

# Custom CSS to make it feel like a modern web app
st.markdown("""
    <style>
    .main-header { font-size: 2.5rem; font-weight: 700; color: #4A90E2; margin-bottom: 0px;}
    .sub-header { font-size: 1.2rem; color: #888888; margin-bottom: 30px;}
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">Nexus Quant Engine ⚡</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">2026-Era Agentic AI & Market Forecasting Terminal</div>', unsafe_allow_html=True)

# --- 2. SIDEBAR CONFIGURATION ---
with st.sidebar:
    st.header("⚙️ Terminal Controls")
    ticker = st.text_input("Asset Ticker:", "AAPL").upper()
    years = st.slider("Historical Data Range (Years):", 1, 10, 5)
    
    st.divider()
    
    st.subheader("🤖 AI Agent Settings")
    ai_model_type = st.selectbox("Neural Engine:", ["Gradient Boosting (Default)", "Random Forest"])
    n_trees = st.slider("Network Depth (Estimators):", 50, 500, 200, step=50)

# --- 3. DATA FETCHING & ENGINEERING ---
@st.cache_data(show_spinner="Connecting to market data streams...")
def load_data(ticker, years):
    start_date = date.today() - timedelta(days=365 * years)
    data = yf.download(ticker, start=start_date, end=date.today(), progress=False)
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    data.reset_index(inplace=True)
    return data

df = load_data(ticker, years)
if df.empty:
    st.error(f"⚠️ Market data unavailable for '{ticker}'. Please verify the ticker symbol.")
    st.stop()

# Engineering Technical Indicators
delta = df['Close'].diff()
df['RSI_14'] = 100 - (100 / (1 + (delta.where(delta > 0, 0).rolling(window=14).mean() / -delta.where(delta < 0, 0).rolling(window=14).mean())))
df['MACD'] = df['Close'].ewm(span=12, adjust=False).mean() - df['Close'].ewm(span=26, adjust=False).mean()
df['BB_Mid'] = df['Close'].rolling(window=20).mean()
df['BB_Std'] = df['Close'].rolling(window=20).std()
df['BB_Upper'], df['BB_Lower'] = df['BB_Mid'] + (df['BB_Std'] * 2), df['BB_Mid'] - (df['BB_Std'] * 2)
df['Volatility'] = df['Close'].pct_change().rolling(window=20).std() * np.sqrt(252)
df['Prev_Close'] = df['Close'].shift(1)
df = df.dropna()

# --- 4. MACHINE LEARNING ENGINE ---
features = ['Prev_Close', 'RSI_14', 'MACD', 'BB_Upper', 'BB_Lower', 'Volatility']
X, y = df[features], df['Close']
split_idx = int(len(df) * 0.8)
X_train, X_test, y_train, y_test = X[:split_idx], X[split_idx:], y[:split_idx], y[split_idx:]

model = GradientBoostingRegressor(n_estimators=n_trees, random_state=42) if ai_model_type == "Gradient Boosting (Default)" else RandomForestRegressor(n_estimators=n_trees, random_state=42)
model.fit(X_train, y_train)
test_preds = model.predict(X_test)
mae = mean_absolute_error(y_test, test_preds)

# Next Day Prediction
last_row = df.iloc[-1]
input_df = pd.DataFrame({f: [float(last_row[f])] for f in features})
next_pred = model.predict(input_df)[0]
last_close = float(last_row['Close'])

# --- 5. MODERN UI: TABBED INTERFACE ---
tab1, tab2, tab3 = st.tabs(["🔮 Executive Dashboard", "📈 Interactive Charting", "🔬 AI Diagnostics"])

# TAB 1: EXECUTIVE DASHBOARD
with tab1:
    st.subheader(f"Live AI Forecast for {ticker}")
    
    # Hero Metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Current Market Price", f"${last_close:.2f}")
    col2.metric("AI 24h Price Target", f"${next_pred:.2f}", f"${next_pred - last_close:.2f} projected")
    col3.metric("AI Confidence Variance (MAE)", f"± ${mae:.2f}", help="Historical average error margin")
    
    st.divider()
    
    # Agentic AI NLP Synthesis
    st.subheader("🧠 Agentic AI Synthesis")
    rsi_status = "Overbought (Potential Sell)" if last_row['RSI_14'] > 70 else "Oversold (Potential Buy)" if last_row['RSI_14'] < 30 else "Neutral"
    macd_status = "Bullish" if last_row['MACD'] > 0 else "Bearish"
    
    st.info(
        f"**Nexus AI Agent Report:** Based on the latest neural network pass utilizing {n_trees} estimators, "
        f"the engine projects a 24-hour target of **${next_pred:.2f}**. "
        f"Technical telemetry indicates the asset is currently **{rsi_status}** with an RSI of {last_row['RSI_14']:.1f}. "
        f"MACD momentum is presently **{macd_status}**. "
        f"Factoring in a historical Mean Absolute Error of ${mae:.2f}, traders should prepare for a trading channel between "
        f"**${next_pred - mae:.2f} and ${next_pred + mae:.2f}** over the next session."
    )

# TAB 2: INTERACTIVE CHARTING (Plotly)
with tab2:
    st.subheader(f"Interactive Candlestick & Volatility Data - {ticker}")
    
    fig = go.Figure()
    # Candlestick
    fig.add_trace(go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Market Price'))
    # Bollinger Bands
    fig.add_trace(go.Scatter(x=df['Date'], y=df['BB_Upper'], line=dict(color='rgba(255,255,255,0.2)', width=1), name='Upper Band'))
    fig.add_trace(go.Scatter(x=df['Date'], y=df['BB_Lower'], line=dict(color='rgba(255,255,255,0.2)', width=1), fill='tonexty', fillcolor='rgba(255,255,255,0.05)', name='Lower Band'))
    
    fig.update_layout(template="plotly_dark", height=600, margin=dict(l=0, r=0, t=30, b=0), xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

# TAB 3: AI DIAGNOSTICS & EXPORTS
with tab3:
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.subheader("Model Feature Importance")
        importance_df = pd.DataFrame({'Weight': model.feature_importances_}, index=features).sort_values(by='Weight', ascending=True)
        st.bar_chart(importance_df, horizontal=True)
        
    with col_b:
        st.subheader("Engine Accuracy Metrics")
        st.write(f"- **Root Mean Squared Error (RMSE):** ${np.sqrt(mean_squared_error(y_test, test_preds)):.2f}")
        st.write(f"- **Mean Absolute Percentage Error:** {mean_absolute_percentage_error(y_test, test_preds) * 100:.2f}%")
        
        st.divider()
        st.subheader("Data Export")
        st.write("Download the AI's engineered dataset for local quantitative analysis.")
        
        # CSV Export functionality
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(label="📥 Download Engineered Dataset (CSV)", data=csv, file_name=f'{ticker}_AI_Engineered_Data.csv', mime='text/csv')
