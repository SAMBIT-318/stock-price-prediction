import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from sklearn.ensemble import RandomForestRegressor
from datetime import date, timedelta
import sqlite3
import hashlib
import time

# Import Alpaca Components
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest, GetOrdersRequest
from alpaca.trading.enums import OrderSide, TimeInForce, QueryOrderStatus

# --- 1. PAGE SETUP & MODERN UI THEME ---
st.set_page_config(page_title="Nexus Pro", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .main-header { font-size: 3rem; font-weight: 800; color: #00d09c; letter-spacing: -0.5px; margin-bottom: 0px;}
    .sub-header { font-size: 1.5rem; color: #9aa0a6; margin-bottom: 20px;}
    /* Adjust Streamlit tab label size */
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p,
    .stTabs [data-baseweb="tab-list"] button div,
    .stTabs [data-baseweb="tab-list"] button span,
    .stTabs [data-baseweb="tab"] {
        font-size: 1.5rem !important;
        font-weight: 700 !important;
    }
    .stat-box { background-color: #1e222d; padding: 12px; border-radius: 8px; border: 1px solid #2a2e39;}
    .auth-box { max-width: 400px; margin: 0 auto; padding: 2rem; background-color: #1e222d; border-radius: 10px; border: 1px solid #00d09c; box-shadow: 0 4px 15px rgba(0,208,156,0.2);}
    </style>
""", unsafe_allow_html=True)

# --- 2. DATABASE & AUTHENTICATION FUNCTIONS ---
def init_db():
    conn = sqlite3.connect('nexus_users.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users(mobile TEXT PRIMARY KEY, password TEXT)')
    conn.commit()
    conn.close()

def make_hash(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def add_user(mobile, password):
    conn = sqlite3.connect('nexus_users.db')
    c = conn.cursor()
    try:
        c.execute('INSERT INTO users(mobile, password) VALUES (?,?)', (mobile, make_hash(password)))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False

def login_user(mobile, password):
    conn = sqlite3.connect('nexus_users.db')
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE mobile = ? AND password = ?', (mobile, make_hash(password)))
    data = c.fetchall()
    conn.close()
    return data

init_db()

# Initialize Session State
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "current_user" not in st.session_state:
    st.session_state["current_user"] = ""

# --- 3. AUTHENTICATION UI (LOGIN/REGISTER) ---
def auth_screen():
    st.markdown('<div align="center"><h1 class="main-header">Nexus Pro | Access Gateway ⚡</h1></div>', unsafe_allow_html=True)
    st.markdown('<div align="center"><p class="sub-header">Secure Authentication Required</p></div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        tab1, tab2 = st.tabs(["🔐 Login", "📝 Register"])
        
        with tab1:
            st.subheader("Login to your account")
            log_mobile = st.text_input("Mobile Number", key="log_mobile", placeholder="Enter your registered mobile")
            log_password = st.text_input("Password", type="password", key="log_pass", placeholder="Enter password")
            
            if st.button("Access Dashboard", use_container_width=True, type="primary"):
                if log_mobile and log_password:
                    result = login_user(log_mobile, log_password)
                    if result:
                        st.success("Authentication Successful! Initializing workspace...")
                        st.balloons()
                        time.sleep(1.5)
                        st.session_state["logged_in"] = True
                        st.session_state["current_user"] = log_mobile
                        st.rerun()
                    else:
                        st.error("Invalid mobile number or password.")
                else:
                    st.warning("Please enter both mobile and password.")

        with tab2:
            st.subheader("Create a new account")
            reg_mobile = st.text_input("Mobile Number", key="reg_mobile", placeholder="10-digit mobile number")
            reg_password = st.text_input("Password", type="password", key="reg_pass", placeholder="Create a strong password")
            reg_confirm = st.text_input("Confirm Password", type="password", key="reg_conf_pass", placeholder="Confirm your password")
            
            if st.button("Register Account", use_container_width=True):
                if reg_mobile and reg_password and reg_confirm:
                    if reg_password != reg_confirm:
                        st.error("Passwords do not match!")
                    elif len(reg_mobile) < 10:
                        st.warning("Please enter a valid mobile number.")
                    else:
                        success = add_user(reg_mobile, reg_password)
                        if success:
                            st.success("Account created successfully! You can now login.")
                        else:
                            st.error("Mobile number is already registered.")
                else:
                    st.warning("Please fill out all fields.")

# --- 4. MAIN APPLICATION DASHBOARD ---
def main_app():
    st.markdown('<div class="main-header">Nexus Pro | Global Markets ⚡</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">US & Indian Equities, Options Chain, Commodities, AI Analytics & Alpaca Execution</div>', unsafe_allow_html=True)

    # --- SECURE BACKGROUND AUTHENTICATION ---
    try:
        api_key = st.secrets["ALPACA_API_KEY"]
        secret_key = st.secrets["ALPACA_SECRET_KEY"]
    except Exception:
        api_key = ""
        secret_key = ""

    # --- SIDEBAR CONFIGURATION ---
    with st.sidebar:
        st.success(f"👤 Logged in: {st.session_state['current_user']}")
        if st.button("🚪 Secure Logout", type="primary", use_container_width=True):
            st.session_state["logged_in"] = False
            st.session_state["current_user"] = ""
            st.rerun()
            
        st.divider()
        st.header("⚡ Watchlist & Ticker")
        
        market_assets = {
            "Custom Ticker Search": "Custom",
            "--- US EQUITIES ---": "",
            "Apple (AAPL)": "AAPL",
            "Nvidia (NVDA)": "NVDA",
            "Tesla (TSLA)": "TSLA",
            "Microsoft (MSFT)": "MSFT",
            "Google (GOOGL)": "GOOGL",
            "Amazon (AMZN)": "AMZN",
            "--- INDIAN INDICES ---": "",
            "Nifty 50": "^NSEI",
            "Bank Nifty": "^NSEBANK",
            "Sensex": "^BSESN",
            "--- INDIAN EQUITIES ---": "",
            "Reliance (NSE)": "RELIANCE.NS",
            "TCS (NSE)": "TCS.NS",
            "HDFC Bank (NSE)": "HDFCBANK.NS",
            "--- COMMODITIES ---": "",
            "Crude Oil": "CL=F",
            "Gold Futures": "GC=F"
        }
        
        selected_name = st.selectbox("Quick Select Asset:", list(market_assets.keys()))
        
        if selected_name == "Custom Ticker Search":
            ticker = st.text_input("Enter Ticker (e.g., INFY.NS, TSLA):", "AAPL").upper()
        elif market_assets[selected_name] == "":
            ticker = "AAPL"
        else:
            ticker = market_assets[selected_name]
            
        timeframe = st.selectbox("Historical Lookback:", ["6mo", "1y", "2y", "5y"], index=2)
        
        if st.button("🔄 Force Refresh Data"):
            st.cache_data.clear()
            st.rerun()
        
        st.divider()
        if api_key and secret_key:
            st.success("🟢 Live Paper Trading Connected")
            st.caption("You are testing on a shared public paper trading account.")
        else:
            st.error("🔴 Broker Disconnected")
            st.caption("Developer: Please add ALPACA_API_KEY to Streamlit Secrets.")

    # --- DATA FETCHING & TECHNICAL ENGINE ---
    @st.cache_data(show_spinner="Loading live market telemetry...")
    def fetch_market_data(symbol, period_choice):
        stock = yf.Ticker(symbol)
        df = stock.history(period=period_choice)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.reset_index(inplace=True)
        
        if not df.empty:
            df['SMA_20'] = df['Close'].rolling(window=20).mean()
            df['SMA_50'] = df['Close'].rolling(window=50).mean()
            df['EMA_200'] = df['Close'].ewm(span=200, adjust=False).mean()
            
            df['BB_Mid'] = df['Close'].rolling(window=20).mean()
            df['BB_Std'] = df['Close'].rolling(window=20).std()
            df['BB_Upper'] = df['BB_Mid'] + (df['BB_Std'] * 2)
            df['BB_Lower'] = df['BB_Mid'] - (df['BB_Std'] * 2)
            
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))
            
            df['EMA_12'] = df['Close'].ewm(span=12, adjust=False).mean()
            df['EMA_26'] = df['Close'].ewm(span=26, adjust=False).mean()
            df['MACD'] = df['EMA_12'] - df['EMA_26']
            df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
            df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']
            
        try:
            info = stock.info
        except Exception:
            info = {}
            
        news_extracted = []
        try:
            raw_news = stock.news[:8]
            for n in raw_news:
                if 'content' in n:
                    c = n['content']
                    title = c.get('title', 'Headline Unavailable')
                    link = c.get('clickThroughUrl', c.get('canonicalUrl', {}).get('url', '#'))
                    publisher = c.get('provider', {}).get('displayName', 'Yahoo Finance')
                else:
                    title = n.get('title', 'Headline Unavailable')
                    link = n.get('link', '#')
                    publisher = n.get('publisher', 'Yahoo Finance')
                news_extracted.append({'title': title, 'link': link, 'publisher': publisher})
        except Exception:
            pass
            
        return df, info, news_extracted

    df, stock_info, news_data = fetch_market_data(ticker, timeframe)

    if df.empty:
        st.error(f"⚠️ Market data unavailable for '{ticker}'. Please verify the symbol.")
        st.stop()

    last_close = float(df['Close'].iloc[-1])
    prev_close = float(df['Close'].iloc[-2])
    change_val = last_close - prev_close
    change_pct = (change_val / prev_close) * 100

    currency_sym = "₹" if ".NS" in ticker or ".BO" in ticker or "^NSE" in ticker or "^BSE" in ticker else "$"

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📈 Interactive Analytics", 
        "🎯 Options Chain",
        "🏢 Valuation & Fundamentals", 
        "💼 Live Portfolio", 
        "⚡ Trade Station",
        "🧪 Strategy Backtester"
    ])

    # [TAB 1: ADVANCED CHARTING]
    with tab1:
        col_metric1, col_metric2, col_metric3, col_metric4 = st.columns(4)
        col_metric1.metric("Spot Price", f"{currency_sym}{last_close:.2f}", f"{change_val:+.2f} ({change_pct:+.2f}%)")
        col_metric2.metric("Day High", f"{currency_sym}{df['High'].iloc[-1]:.2f}")
        col_metric3.metric("Day Low", f"{currency_sym}{df['Low'].iloc[-1]:.2f}")
        col_metric4.metric("Trading Volume", f"{int(df['Volume'].iloc[-1]):,}")
        
        st.divider()
        fig = make_subplots(
            rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03, 
            row_heights=[0.60, 0.20, 0.20],
            subplot_titles=(f"{ticker} Price Action & Volatility Bands", "Volume Telemetry", "MACD Momentum Oscillator")
        )
        
        fig.add_trace(go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Price'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['Date'], y=df['SMA_20'], line=dict(color='#ffa726', width=1.2), name='SMA 20'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['Date'], y=df['SMA_50'], line=dict(color='#29b6f6', width=1.2), name='SMA 50'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['Date'], y=df['BB_Upper'], line=dict(color='rgba(255,255,255,0.2)', width=1), name='BB Upper'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['Date'], y=df['BB_Lower'], line=dict(color='rgba(255,255,255,0.2)', width=1), fill='tonexty', fillcolor='rgba(255,255,255,0.03)', name='BB Lower'), row=1, col=1)
        
        colors = ['#00d09c' if c >= o else '#ff5050' for c, o in zip(df['Close'], df['Open'])]
        fig.add_trace(go.Bar(x=df['Date'], y=df['Volume'], marker_color=colors, name='Volume', showlegend=False), row=2, col=1)
        
        macd_colors = ['#00d09c' if h >= 0 else '#ff5050' for h in df['MACD_Hist']]
        fig.add_trace(go.Bar(x=df['Date'], y=df['MACD_Hist'], marker_color=macd_colors, name='MACD Hist', showlegend=False), row=3, col=1)
        fig.add_trace(go.Scatter(x=df['Date'], y=df['MACD'], line=dict(color='#00e5ff', width=1.2), name='MACD Line'), row=3, col=1)
        fig.add_trace(go.Scatter(x=df['Date'], y=df['MACD_Signal'], line=dict(color='#ff9100', width=1.2), name='Signal Line'), row=3, col=1)
        
        fig.update_layout(template="plotly_dark", height=700, margin=dict(l=0, r=0, t=30, b=0), xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
        
        st.subheader("🤖 Neural Price Target & AI Signal")
        ml_df = df[['Close', 'SMA_20', 'SMA_50', 'RSI', 'MACD']].dropna().copy()
        ml_df['Target'] = ml_df['Close'].shift(-1)
        ml_features = ml_df.dropna()
        
        if len(ml_features) > 20:
            X = ml_features[['Close', 'SMA_20', 'SMA_50', 'RSI', 'MACD']]
            y = ml_features['Target']
            rf = RandomForestRegressor(n_estimators=100, random_state=42)
            rf.fit(X[:-1], y[:-1])
            
            last_features = np.array([[last_close, df['SMA_20'].iloc[-1], df['SMA_50'].iloc[-1], df['RSI'].iloc[-1], df['MACD'].iloc[-1]]])
            predicted_target = rf.predict(last_features)[0]
            
            c_ai1, c_ai2 = st.columns([1, 2])
            c_ai1.metric("Predicted Next Session Target", f"{currency_sym}{predicted_target:.2f}", f"{predicted_target - last_close:+.2f}")
            c_ai2.info(
                f"**Model Signal:** {'BULLISH 🟢' if predicted_target > last_close else 'BEARISH 🔴'}. "
                f"Current RSI is **{df['RSI'].iloc[-1]:.1f}** | MACD: **{df['MACD'].iloc[-1]:.2f}**. "
                f"Asset is trading {'Above' if last_close > df['SMA_50'].iloc[-1] else 'Below'} the 50-day SMA."
            )

    # [TAB 2: OPTIONS CHAIN]
    with tab2:
        st.subheader(f"🎯 Real-Time Options Chain: {ticker}")
        try:
            stock_obj = yf.Ticker(ticker)
            expirations = stock_obj.options
            if expirations:
                col_exp, col_opt_type = st.columns([2, 1])
                selected_exp = col_exp.selectbox("Select Expiration Date:", expirations)
                opt_type = col_opt_type.radio("Option Type:", ["Calls (Bullish)", "Puts (Bearish)"], horizontal=True)
                
                chain = stock_obj.option_chain(selected_exp)
                opt_df = chain.calls if "Calls" in opt_type else chain.puts
                
                if not opt_df.empty:
                    display_cols = ['strike', 'lastPrice', 'bid', 'ask', 'volume', 'openInterest', 'impliedVolatility']
                    opt_view = opt_df[[c for c in display_cols if c in opt_df.columns]].copy()
                    opt_view.fillna(0, inplace=True)
                    opt_view['impliedVolatility'] = opt_view['impliedVolatility'] * 100
                    
                    st.dataframe(
                        opt_view.style.format({
                            'strike': f'{currency_sym}{{:,.2f}}',
                            'lastPrice': f'{currency_sym}{{:,.2f}}',
                            'bid': f'{currency_sym}{{:,.2f}}',
                            'ask': f'{currency_sym}{{:,.2f}}',
                            'volume': '{:,.0f}',
                            'openInterest': '{:,.0f}',
                            'impliedVolatility': '{:.2f}%'
                        }), use_container_width=True, hide_index=True
                    )
                else:
                    st.info("No options data returned for this expiration.")
            else:
                st.info(f"Derivatives chain not available on Yahoo Finance for '{ticker}'.")
        except Exception as e:
            st.warning(f"Could not load options chain: {e}")

    # [TAB 3: VALUATION]
    with tab3:
        st.subheader(f"🏢 Fundamental Breakdown: {ticker}")
        f1, f2, f3, f4 = st.columns(4)
        f1.metric("Market Capitalization", f"{currency_sym}{stock_info.get('marketCap', 0):,}")
        f2.metric("Trailing P/E Ratio", f"{stock_info.get('trailingPE', 'N/A')}")
        f3.metric("Forward P/E Ratio", f"{stock_info.get('forwardPE', 'N/A')}")
        f4.metric("Beta (Volatility)", f"{stock_info.get('beta', 'N/A')}")
        
        f5, f6, f7, f8 = st.columns(4)
        f5.metric("52-Week High", f"{currency_sym}{stock_info.get('fiftyTwoWeekHigh', 'N/A')}")
        f6.metric("52-Week Low", f"{currency_sym}{stock_info.get('fiftyTwoWeekLow', 'N/A')}")
        f7.metric("Dividend Yield", f"{(stock_info.get('dividendYield', 0) or 0)*100:.2f}%")
        f8.metric("Profit Margin", f"{(stock_info.get('profitMargins', 0) or 0)*100:.2f}%")
        
        st.divider()
        st.subheader("📰 Live Market News")
        if news_data:
            for item in news_data:
                st.markdown(f"#### [{item['title']}]({item['link']})")
                st.caption(f"Source: **{item['publisher']}**")
                st.write("---")
        else:
            st.write("No exact live news items could be routed for this ticker at this moment.")

    # [TAB 4: PORTFOLIO]
    with tab4:
        st.subheader("💼 Live Alpaca Portfolio Execution")
        if not api_key or not secret_key:
            st.error("⚠️ Alpaca API Keys not detected in Secrets.")
        else:
            try:
                client = TradingClient(api_key, secret_key, paper=True)
                acc = client.get_account()
                p1, p2, p3, p4 = st.columns(4)
                p1.metric("Total Equity", f"${float(acc.equity or 0.0):,.2f}")
                p2.metric("Buying Power", f"${float(acc.buying_power or 0.0):,.2f}")
                p3.metric("Cash Balance", f"${float(acc.cash or 0.0):,.2f}")
                dt_power = acc.daytrading_buying_power if acc.daytrading_buying_power is not None else acc.buying_power
                p4.metric("Daytrade Power", f"${float(dt_power or 0.0):,.2f}")
                
                st.divider()
                st.subheader("📊 Open Positions")
                positions = client.get_all_positions()
                if not positions:
                    st.info("No active open positions in this account.")
                else:
                    pos_list = [{
                        'Asset': p.symbol, 'Shares': float(p.qty), 'Entry Price': float(p.avg_entry_price),
                        'Current Price': float(p.current_price), 'Market Value': float(p.market_value),
                        'Unrealized P&L ($)': float(p.unrealized_pl), 'P&L (%)': float(p.unrealized_plpc) * 100
                    } for p in positions]
                    st.dataframe(pd.DataFrame(pos_list).style.format({
                        'Shares': '{:.2f}', 'Entry Price': '${:.2f}', 'Current Price': '${:.2f}',
                        'Market Value': '${:.2f}', 'Unrealized P&L ($)': '${:.2f}', 'P&L (%)': '{:.2f}%'
                    }), use_container_width=True, hide_index=True)
            except Exception as e:
                st.error(f"❌ Account Connection Failed: {e}")

    # [TAB 5: TRADE STATION]
    with tab5:
        st.subheader(f"⚡ Execution Desk: {ticker}")
        t_col1, t_col2 = st.columns(2)
        with t_col1:
            st.info(f"**Live Exchange Quote:** {currency_sym}{last_close:.2f}")
            order_style = st.selectbox("Order Routing Type", ["Market Order", "Limit Order"])
            order_side = st.radio("Side", ["Buy", "Sell"], horizontal=True)
            order_qty = st.number_input("Shares Quantity", min_value=0.01, value=1.0, step=1.0)
            
            limit_px = None
            if order_style == "Limit Order":
                limit_px = st.number_input(f"Limit Price ({currency_sym})", min_value=0.01, value=float(last_close), step=0.5)
                est_value = limit_px * order_qty
            else:
                est_value = last_close * order_qty
                
            st.write(f"**Gross Order Notional:** {currency_sym}{est_value:,.2f}")
            is_foreign = "^" in ticker or "=F" in ticker or ".NS" in ticker or ".BO" in ticker
            
            if st.button("🚀 Transmit Order to Alpaca"):
                if not api_key or not secret_key:
                    st.error("⚠️ Alpaca API Keys missing.")
                elif is_foreign:
                    st.error("❌ Broker Rejection: Alpaca does not support foreign equities/indices.")
                else:
                    try:
                        trading_client = TradingClient(api_key, secret_key, paper=True)
                        side_choice = OrderSide.BUY if order_side == "Buy" else OrderSide.SELL
                        if order_style == "Limit Order":
                            order_payload = LimitOrderRequest(symbol=ticker, qty=order_qty, side=side_choice, time_in_force=TimeInForce.DAY, limit_price=limit_px)
                        else:
                            order_payload = MarketOrderRequest(symbol=ticker, qty=order_qty, side=side_choice, time_in_force=TimeInForce.DAY)
                        submitted = trading_client.submit_order(order_data=order_payload)
                        st.success(f"✅ Order Transmitted Successfully! ID: `{submitted.id}`")
                    except Exception as e:
                        st.error(f"❌ Routing Rejected: {e}")
        with t_col2:
            st.write("### Account Liquidity Snapshot")
            if api_key and secret_key:
                try:
                    client = TradingClient(api_key, secret_key, paper=True)
                    account_meta = client.get_account()
                    st.metric("Total Equity", f"${float(account_meta.equity or 0.0):,.2f}")
                    st.metric("Available Buying Power", f"${float(account_meta.buying_power or 0.0):,.2f}")
                except Exception:
                    st.warning("Could not sync live account data.")

    # [TAB 6: BACKTESTER]
    with tab6:
        st.subheader(f"🧪 Strategy Simulator: {ticker}")
        b_df = df[['Date', 'Close', 'SMA_20', 'SMA_50']].dropna().copy()
        if len(b_df) > 50:
            b_df['Signal'] = np.where(b_df['SMA_20'] > b_df['SMA_50'], 1, 0)
            b_df['Market_Return'] = b_df['Close'].pct_change()
            b_df['Strategy_Return'] = b_df['Signal'].shift(1) * b_df['Market_Return']
            b_df['Cum_Market'] = (1 + b_df['Market_Return']).cumprod() - 1
            b_df['Cum_Strategy'] = (1 + b_df['Strategy_Return']).cumprod() - 1
            
            strat_cum = (1 + b_df['Strategy_Return']).cumprod()
            peak = strat_cum.cummax()
            max_drawdown = ((strat_cum - peak) / peak).min() * 100
            
            b_fig = go.Figure()
            b_fig.add_trace(go.Scatter(x=b_df['Date'], y=b_df['Cum_Strategy'] * 100, name='SMA Crossover', line=dict(color='#00d09c', width=2)))
            b_fig.add_trace(go.Scatter(x=b_df['Date'], y=b_df['Cum_Market'] * 100, name='Buy & Hold', line=dict(color='#888888', width=1.5, dash='dot')))
            b_fig.update_layout(template="plotly_dark", height=420, yaxis_title="Cumulative Return (%)", margin=dict(l=0, r=0, t=20, b=0))
            st.plotly_chart(b_fig, use_container_width=True)
            
            r1, r2, r3 = st.columns(3)
            r1.metric("Strategy Net Return", f"{b_df['Cum_Strategy'].iloc[-1] * 100:+.2f}%")
            r2.metric("Buy & Hold Return", f"{b_df['Cum_Market'].iloc[-1] * 100:+.2f}%")
            r3.metric("Max Drawdown (Risk)", f"{max_drawdown:.2f}%")
        else:
            st.info("Insufficient historical points to run complete backtest.")

# --- 5. APPLICATION ROUTING ---
if not st.session_state["logged_in"]:
    auth_screen()
else:
    main_app()
