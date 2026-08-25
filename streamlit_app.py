import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from sklearn.ensemble import RandomForestRegressor
from datetime import date, timedelta

# --- 1. PAGE SETUP & CSS ---
st.set_page_config(page_title="Nexus Trade Terminal", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .main-header { font-size: 2.5rem; font-weight: 700; color: #00d09c; margin-bottom: 0px;}
    .sub-header { font-size: 1rem; color: #888888; margin-bottom: 20px;}
    .profit { color: #00d09c; font-weight: bold;}
    .loss { color: #ff5050; font-weight: bold;}
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">Nexus Trade Terminal</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Advanced Market Analytics & Portfolio Simulator</div>', unsafe_allow_html=True)

# --- 2. SIDEBAR SEARCH ---
with st.sidebar:
    st.header("🔍 Market Search")
    ticker = st.text_input("Search Asset (e.g., AAPL, TSLA, INFY.NS):", "AAPL").upper()
    
    st.divider()
    st.write("📈 **Market Indices**")
    st.metric("S&P 500", "5,420.12", "+1.2%")
    st.metric("NASDAQ", "17,133.50", "+1.5%")
    st.metric("NIFTY 50", "23,500.45", "-0.3%")

# --- 3. DATA FETCHING ---
@st.cache_data(show_spinner="Connecting to live market feeds...")
def load_data(ticker):
    stock = yf.Ticker(ticker)
    df = stock.history(period="2y")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.reset_index(inplace=True)
    
    # Get recent news
    try:
        news = stock.news[:5]
    except:
        news = []
        
    return df, news

df, news_data = load_data(ticker)

if df.empty:
    st.error("Asset not found. Please try a different ticker.")
    st.stop()

last_close = df['Close'].iloc[-1]
prev_close = df['Close'].iloc[-2]
daily_change = last_close - prev_close
daily_pct = (daily_change / prev_close) * 100

# --- 4. TERMINAL TABS (Like Groww/AngelOne) ---
tab1, tab2, tab3, tab4 = st.tabs(["📊 Markets & AI", "💼 My Portfolio", "📰 News Feed", "⚡ Trade Station"])

# --- TAB 1: MARKETS & AI ---
with tab1:
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader(f"{ticker} Price Chart")
        fig = go.Figure(data=[go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Price')])
        fig.update_layout(template="plotly_dark", height=500, margin=dict(l=0, r=0, t=30, b=0), xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
        
    with col2:
        st.subheader("Market Snapshot")
        st.metric(f"{ticker} Current", f"${last_close:.2f}", f"{daily_change:.2f} ({daily_pct:.2f}%)")
        st.write(f"**Day High:** ${df['High'].iloc[-1]:.2f}")
        st.write(f"**Day Low:** ${df['Low'].iloc[-1]:.2f}")
        st.write(f"**Volume:** {df['Volume'].iloc[-1]:,}")
        
        st.divider()
        st.subheader("🤖 AI Forecast")
        st.write("Using Random Forest to estimate next day trend based on 2-year momentum.")
        
        # Simple ML for UI demonstration
        df['Prev_Close'] = df['Close'].shift(1)
        df_ml = df.dropna()
        model = RandomForestRegressor(n_estimators=50, random_state=42)
        model.fit(df_ml[['Prev_Close']], df_ml['Close'])
        pred = model.predict([[last_close]])[0]
        
        trend = "Bullish 🟢" if pred > last_close else "Bearish 🔴"
        st.write(f"**AI Signal:** {trend}")
        st.write(f"**Projected Target:** ${pred:.2f}")
        st.caption("Disclaimer: AI models provide probabilistic estimates, not financial advice.")

# --- TAB 2: MOCK PORTFOLIO ---
with tab2:
    st.subheader("💼 Simulated Holdings")
    
    # Mock data for a portfolio
    portfolio_data = {
        'Asset': ['AAPL', 'MSFT', 'TSLA', 'NVDA'],
        'Shares': [15, 10, 5, 20],
        'Avg Price': [150.00, 310.00, 200.00, 110.00],
        'Current Price': [last_close if ticker == 'AAPL' else 175.50, 415.00, 185.00, 125.00]
    }
    port_df = pd.DataFrame(portfolio_data)
    port_df['Invested Value'] = port_df['Shares'] * port_df['Avg Price']
    port_df['Current Value'] = port_df['Shares'] * port_df['Current Price']
    port_df['P&L'] = port_df['Current Value'] - port_df['Invested Value']
    port_df['P&L %'] = (port_df['P&L'] / port_df['Invested Value']) * 100
    
    # Format for display
    display_df = port_df.style.format({
        'Avg Price': '${:.2f}', 'Current Price': '${:.2f}', 
        'Invested Value': '${:.2f}', 'Current Value': '${:.2f}',
        'P&L': '${:.2f}', 'P&L %': '{:.2f}%'
    })
    
    total_invested = port_df['Invested Value'].sum()
    total_current = port_df['Current Value'].sum()
    total_pl = total_current - total_invested
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Invested", f"${total_invested:,.2f}")
    c2.metric("Current Value", f"${total_current:,.2f}", f"${total_pl:,.2f}")
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)

# --- TAB 3: NEWS FEED ---
with tab3:
    st.subheader(f"📰 Latest News for {ticker}")
    if news_data:
        for article in news_data:
            st.markdown(f"**[{article.get('title', 'Headline Unavailable')}]({article.get('link', '#')})**")
            st.caption(f"Published by: {article.get('publisher', 'Unknown')}")
            st.write("---")
    else:
        st.write("No recent news found for this asset.")

# --- TAB 4: TRADE STATION ---
with tab4:
    st.subheader(f"⚡ Execute Order: {ticker}")
    t1, t2 = st.columns(2)
    
    with t1:
        st.info(f"**Current Market Price:** ${last_close:.2f}")
        order_type = st.selectbox("Order Type", ["Market Order", "Limit Order"])
        action = st.radio("Action", ["Buy", "Sell"], horizontal=True)
        quantity = st.number_input("Quantity (Shares)", min_value=1, value=1)
        
        if order_type == "Limit Order":
            limit_price = st.number_input("Limit Price ($)", value=float(last_close))
            total_cost = limit_price * quantity
        else:
            total_cost = last_close * quantity
            
        st.write(f"**Estimated Order Value:** ${total_cost:,.2f}")
        
        if st.button("Place Order"):
            st.success(f"✅ {action} order for {quantity} shares of {ticker} successfully placed in simulation mode!")
            
    with t2:
        st.write("### Order Book (Simulated)")
        st.write("Bid (Buyers) | Ask (Sellers)")
        st.text(f"${last_close - 0.05:.2f} x 100  |  ${last_close + 0.02:.2f} x 50")
        st.text(f"${last_close - 0.10:.2f} x 350  |  ${last_close + 0.08:.2f} x 200")
        st.text(f"${last_close - 0.15:.2f} x 500  |  ${last_close + 0.12:.2f} x 150")
