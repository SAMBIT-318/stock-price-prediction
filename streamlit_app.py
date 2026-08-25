import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from sklearn.ensemble import RandomForestRegressor
from datetime import date, timedelta

# Import Alpaca components globally
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

# --- 1. PAGE SETUP & CSS ---
st.set_page_config(page_title="Nexus Trade Terminal", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .main-header { font-size: 2.5rem; font-weight: 700; color: #00d09c; margin-bottom: 0px;}
    .sub-header { font-size: 1rem; color: #888888; margin-bottom: 20px;}
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">Nexus Trade Terminal</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Advanced Market Analytics & Alpaca Paper Trading</div>', unsafe_allow_html=True)

# --- 2. SIDEBAR SEARCH & API KEYS ---
with st.sidebar:
    st.header("🔍 Market Search")
    ticker = st.text_input("Search Asset (e.g., AAPL, TSLA, MSFT):", "AAPL").upper()
    
    st.divider()
    
    # MOVED API KEYS HERE SO ALL TABS CAN USE THEM
    st.header("🔑 Alpaca API Keys")
    api_key = st.text_input("Alpaca API Key", type="password")
    secret_key = st.text_input("Alpaca Secret Key", type="password")
    
    st.divider()
    st.write("📈 **Market Indices**")
    st.metric("S&P 500", "5,420.12", "+1.2%")
    st.metric("NASDAQ", "17,133.50", "+1.5%")

# --- 3. DATA FETCHING ---
@st.cache_data(show_spinner="Connecting to live market feeds...")
def load_data(ticker):
    stock = yf.Ticker(ticker)
    df = stock.history(period="2y")
    if isinstance(df.columns, pd.MultiIndex):
        data_cols = df.columns.get_level_values(0)
        df.columns = data_cols
    df.reset_index(inplace=True)
    
    try:
        news = stock.news[:5]
    except Exception:
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

# --- 4. TERMINAL TABS ---
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
        df['Prev_Close'] = df['Close'].shift(1)
        df_ml = df.dropna()
        model = RandomForestRegressor(n_estimators=50, random_state=42)
        model.fit(df_ml[['Prev_Close']], df_ml['Close'])
        pred = model.predict([[last_close]])[0]
        
        trend = "Bullish 🟢" if pred > last_close else "Bearish 🔴"
        st.write(f"**AI Signal:** {trend}")
        st.write(f"**Projected Target:** ${pred:.2f}")

# --- TAB 2: LIVE PORTFOLIO ---
with tab2:
    st.subheader("💼 Live Alpaca Portfolio")
    
    if not api_key or not secret_key:
        st.warning("⚠️ Please enter your Alpaca API Key and Secret Key in the sidebar to view your live portfolio.")
    else:
        try:
            # Connect to Alpaca
            client = TradingClient(api_key, secret_key, paper=True)
            
            # Fetch Account Balance & Buying Power
            account = client.get_account()
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Equity (Portfolio Value)", f"${float(account.equity):,.2f}")
            c2.metric("Buying Power", f"${float(account.buying_power):,.2f}")
            c3.metric("Available Cash", f"${float(account.cash):,.2f}")
            
            st.divider()
            st.subheader("📊 Open Positions")
            
            # Fetch Open Positions
            positions = client.get_all_positions()
            
            if not positions:
                st.info("You currently have no open positions in your Alpaca account.")
            else:
                # Convert positions into a Pandas DataFrame for a clean table
                pos_data = []
                for p in positions:
                    pos_data.append({
                        'Asset': p.symbol,
                        'Shares': float(p.qty),
                        'Avg Price': float(p.avg_entry_price),
                        'Current Price': float(p.current_price),
                        'Market Value': float(p.market_value),
                        'P&L ($)': float(p.unrealized_pl),
                        'P&L (%)': float(p.unrealized_plpc) * 100
                    })
                
                df_pos = pd.DataFrame(pos_data)
                
                # Format the DataFrame to look professional
                display_df = df_pos.style.format({
                    'Shares': '{:.4f}', 
                    'Avg Price': '${:.2f}',
                    'Current Price': '${:.2f}',
                    'Market Value': '${:.2f}',
                    'P&L ($)': '${:.2f}',
                    'P&L (%)': '{:.2f}%'
                })
                
                st.dataframe(display_df, use_container_width=True, hide_index=True)
                
        except Exception as e:
            st.error(f"❌ Could not fetch portfolio data. Please check if your API keys are correct. Error: {e}")

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

# --- TAB 4: TRADE STATION (ALPACA PAPER TRADING) ---
with tab4:
    st.subheader(f"⚡ Execute Order: {ticker}")
    
    t1, t2 = st.columns(2)
    
    with t1:
        st.info(f"**Current Market Price:** ${last_close:.2f}")
        action = st.radio("Action", ["Buy", "Sell"], horizontal=True)
        quantity = st.number_input("Quantity (Shares)", min_value=0.01, value=1.0, step=1.0)
        
        st.write(f"**Estimated Order Value:** ${last_close * quantity:,.2f}")
        
        if st.button("Place Paper Trade via Alpaca"):
            if not api_key or not secret_key:
                st.error("⚠️ Please enter your Alpaca API keys in the sidebar.")
            else:
                with st.spinner("Transmitting order to Alpaca exchange..."):
                    try:
                        trading_client = TradingClient(api_key, secret_key, paper=True)
                        side = OrderSide.BUY if action == "Buy" else OrderSide.SELL
                        
                        market_order_data = MarketOrderRequest(
                            symbol=ticker,
                            qty=quantity,
                            side=side,
                            time_in_force=TimeInForce.DAY
                        )
                        
                        order = trading_client.submit_order(order_data=market_order_data)
                        st.success("✅ Order successfully routed to Alpaca!")
                        st.write(f"**Order ID:** `{order.id}`")
                        st.write(f"**Status:** `{order.status}`")
                    except Exception as e:
                        st.error(f"❌ Order Failed: {e}")
                        
    with t2:
        st.write("### Quick Account Status")
        if not api_key or not secret_key:
            st.warning("Enter API keys in the sidebar to view status.")
        else:
            try:
                client = TradingClient(api_key, secret_key, paper=True)
                account = client.get_account()
                st.metric("Total Equity", f"${float(account.equity):,.2f}")
                st.metric("Buying Power", f"${float(account.buying_power):,.2f}")
            except Exception as e:
                st.error("Could not fetch account details.")
