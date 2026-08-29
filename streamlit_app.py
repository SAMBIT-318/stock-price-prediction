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
import random
import requests

# Import Alpaca Components
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest, GetOrdersRequest
from alpaca.trading.enums import OrderSide, TimeInForce, QueryOrderStatus

# --- 1. PAGE SETUP & MOOMOO UI THEME ---
st.set_page_config(page_title="Nexus Pro", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    /* Global Moomoo Dark Background */
    .stApp {
        background-color: #131722;
        color: #d1d4dc;
    }

    /* Screen Width Expansion */
    .block-container {
        max-width: 98% !important;
        padding-top: 1.5rem !important;
        padding-bottom: 2rem !important;
        padding-left: 1.2rem !important;
        padding-right: 1.2rem !important;
    }

    /* Typography */
    .main-header { 
        font-size: 2.2rem; 
        font-weight: 700; 
        color: #ffffff;
        letter-spacing: -0.5px; 
        margin-bottom: 0px;
    }
    .sub-header { 
        font-size: 1.1rem; 
        color: #8a93a6; 
        margin-bottom: 25px;
    }

    /* Moomoo Solid Panels */
    .moomoo-panel {
        background-color: #1e222d !important;
        border: 1px solid #2b3139 !important;
        border-radius: 6px !important;
        padding: 20px !important;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1) !important;
        margin-bottom: 1rem;
    }

    /* Moomoo Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0px;
        background-color: transparent;
        padding: 0;
        border-bottom: 1px solid #2b3139;
    }

    .stTabs [data-baseweb="tab-list"] button {
        background: transparent !important;
        border-radius: 0px !important;
        color: #8a93a6 !important;
        font-size: 1.05rem !important;
        font-weight: 600 !important;
        padding: 12px 20px !important;
        transition: all 0.2s ease;
        border: none !important;
    }

    .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
        color: #FF6933 !important; /* Moomoo Orange */
        border-bottom: 2px solid #FF6933 !important;
        background-color: rgba(255, 105, 51, 0.05) !important;
    }

    /* Input Fields */
    div[data-baseweb="input"] {
        background-color: #131722 !important;
        border: 1px solid #2b3139 !important;
        border-radius: 4px !important;
        color: #ffffff !important;
    }

    /* Moomoo Primary Buttons */
    .stButton > button {
        background-color: #FF6933 !important;
        border: none !important;
        color: #ffffff !important;
        border-radius: 4px !important;
        font-weight: 600 !important;
        transition: background-color 0.2s ease !important;
    }
    .stButton > button:hover {
        background-color: #ff8555 !important;
        transform: none;
        box-shadow: none !important;
    }

    /* Sidebar Moomoo Theme */
    [data-testid="stSidebar"] {
        background-color: #1e222d !important;
        border-right: 1px solid #2b3139 !important;
    }
    
    /* Metrics overriding */
    [data-testid="stMetricValue"] {
        color: #ffffff;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. DATABASE & TWILIO API GATEWAY ---
def init_db():
    conn = sqlite3.connect('nexus_users.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users(mobile TEXT PRIMARY KEY, password TEXT)')
    conn.commit()
    conn.close()

def make_hash(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def user_exists(mobile):
    conn = sqlite3.connect('nexus_users.db')
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE mobile = ?', (mobile,))
    data = c.fetchone()
    conn.close()
    return data is not None

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

def dispatch_sms_otp(mobile_number, otp_code):
    """
    Dispatches OTP via Twilio API in real-time.
    """
    # 1. Paste your Account SID and Auth Token inside the quotes below
    account_sid = "PASTE_YOUR_ACCOUNT_SID_HERE"
    auth_token = "PASTE_YOUR_AUTH_TOKEN_HERE"
    
    # Your Twilio phone number
    twilio_number = "+17372508034" 
    
    # Format the user's mobile number with the +91 country code
    clean_number = "".join(filter(str.isdigit, str(mobile_number)))
    target_number = f"+91{clean_number}" if len(clean_number) == 10 else f"+{clean_number}"
    
    url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
    
    # The message payload
    data = {
        "From": twilio_number,
        "To": target_number,
        "Body": f"Your Nexus Pro verification code is: {otp_code}. Do not share this."
    }
    
    try:
        # Send the request to Twilio using Basic Auth
        res = requests.post(url, data=data, auth=(account_sid, auth_token), timeout=10)
        
        if res.status_code in [200, 201]:
            return True
        else:
            error_msg = res.json().get('message', 'Unknown Twilio API Error')
            st.error(f"Twilio API Error: {error_msg}")
            return False
    except Exception as e:
        st.error(f"Twilio Connection Failed: {e}")
        return False

init_db()

# Session State Initialization
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "current_user" not in st.session_state:
    st.session_state["current_user"] = ""
if "otp_sent" not in st.session_state:
    st.session_state["otp_sent"] = False
if "generated_otp" not in st.session_state:
    st.session_state["generated_otp"] = ""
if "reg_mobile_pending" not in st.session_state:
    st.session_state["reg_mobile_pending"] = ""
if "reg_pass_pending" not in st.session_state:
    st.session_state["reg_pass_pending"] = ""

# --- 3. AUTHENTICATION UI ---
def auth_screen():
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div align="center"><h1 class="main-header">Nexus Pro Trading</h1></div>', unsafe_allow_html=True)
    st.markdown('<div align="center"><p class="sub-header">Advanced Execution & Analytics Terminal</p></div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.3, 1])
    with col2:
        st.markdown('<div class="moomoo-panel">', unsafe_allow_html=True)
        tab_login, tab_register = st.tabs(["Secure Login", "Open Account"])
        
        with tab_login:
            st.markdown("<br>### Account Login", unsafe_allow_html=True)
            log_mobile = st.text_input("Mobile Number", key="log_mobile", placeholder="Enter your registered mobile")
            log_password = st.text_input("Password", type="password", key="log_pass", placeholder="Enter your password")
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Unlock Terminal", use_container_width=True, type="primary"):
                if log_mobile and log_password:
                    result = login_user(log_mobile, log_password)
                    if result:
                        st.success("Authentication successful! Loading workspace...")
                        time.sleep(1)
                        st.session_state["logged_in"] = True
                        st.session_state["current_user"] = log_mobile
                        st.rerun()
                    else:
                        st.error("Invalid mobile number or password.")
                else:
                    st.warning("Please complete all fields.")

        with tab_register:
            st.markdown("<br>### Register Account", unsafe_allow_html=True)
            
            if not st.session_state["otp_sent"]:
                reg_mobile = st.text_input("Mobile Number", key="reg_mobile", placeholder="10-digit mobile number")
                reg_password = st.text_input("Create Password", type="password", key="reg_pass", placeholder="Create a strong password")
                reg_confirm = st.text_input("Confirm Password", type="password", key="reg_conf_pass", placeholder="Re-enter password")
                
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("Send Verification Code", use_container_width=True):
                    if reg_mobile and reg_password and reg_confirm:
                        if reg_password != reg_confirm:
                            st.error("Passwords do not match!")
                        elif len(reg_mobile) < 10:
                            st.warning("Please provide a valid 10-digit mobile number.")
                        elif user_exists(reg_mobile):
                            st.error("Existing user credential, please log in.")
                        else:
                            otp = str(random.randint(100000, 999999))
                            sent = dispatch_sms_otp(reg_mobile, otp)
                            if sent:
                                st.session_state["otp_sent"] = True
                                st.session_state["generated_otp"] = otp
                                st.session_state["reg_mobile_pending"] = reg_mobile
                                st.session_state["reg_pass_pending"] = reg_password
                                st.rerun()
                            else:
                                st.error("Failed to transmit SMS. Please check your Twilio settings.")
                    else:
                        st.warning("Please fill out all registration fields.")
            else:
                st.success(f"SMS Verification code has been dispatched to **{st.session_state['reg_mobile_pending']}**.")
                
                entered_otp = st.text_input("Enter 6-digit Code Received", key="entered_otp", max_chars=6)
                
                st.markdown("<br>", unsafe_allow_html=True)
                v1, v2 = st.columns(2)
                with v1:
                    if st.button("Verify & Activate", use_container_width=True, type="primary"):
                        if entered_otp == st.session_state["generated_otp"]:
                            success = add_user(st.session_state["reg_mobile_pending"], st.session_state["reg_pass_pending"])
                            if success:
                                st.success("Account successfully created! Please log in.")
                                time.sleep(1.5)
                                st.session_state["otp_sent"] = False
                                st.rerun()
                            else:
                                st.error("Error writing user credentials to database.")
                        else:
                            st.error("Incorrect verification code. Please check your SMS.")
                with v2:
                    if st.button("Change Number", use_container_width=True):
                        st.session_state["otp_sent"] = False
                        st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)

# --- 4. MAIN APPLICATION DASHBOARD ---
def main_app():
    st.markdown('<div class="main-header">Nexus Pro Markets</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Live Telemetry & Execution Desk</div>', unsafe_allow_html=True)

    try:
        api_key = st.secrets.get("ALPACA_API_KEY", "")
        secret_key = st.secrets.get("ALPACA_SECRET_KEY", "")
    except Exception:
        api_key = ""
        secret_key = ""

    # --- SIDEBAR CONFIGURATION ---
    with st.sidebar:
        st.markdown('<div class="moomoo-panel" style="padding:15px !important;">', unsafe_allow_html=True)
        st.write(f"👤 Account: **{st.session_state['current_user']}**")
        if st.button("Logout", type="primary", use_container_width=True):
            st.session_state["logged_in"] = False
            st.session_state["current_user"] = ""
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.header("Watchlist & Ticker")
        
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
        
        if st.button("Force Refresh Data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        
        st.divider()
        if api_key and secret_key:
            st.success("Alpaca Broker Online")
        else:
            st.error("Broker Disconnected")
            st.caption("Add ALPACA_API_KEY to secrets to trade.")

    # --- TECHNICAL ENGINE ---
    @st.cache_data(show_spinner="Syncing live exchange order flow...")
    def fetch_market_data(symbol, period_choice):
        stock = yf.Ticker(symbol)
        df = stock.history(period=period_choice)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.reset_index(inplace=True)
        
        if not df.empty:
            df['SMA_20'] = df['Close'].rolling(window=20).mean()
            df['SMA_50'] = df['Close'].rolling(window=50).mean()
            
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
            raw_news = stock.news[:10]
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
        st.error(f"Market telemetry unavailable for '{ticker}'. Please verify the symbol.")
        st.stop()

    last_close = float(df['Close'].iloc[-1])
    prev_close = float(df['Close'].iloc[-2])
    change_val = last_close - prev_close
    change_pct = (change_val / prev_close) * 100
    currency_sym = "₹" if ".NS" in ticker or ".BO" in ticker or "^NSE" in ticker or "^BSE" in ticker else "$"

    # --- TABS ---
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "Detailed Quotes", 
        "Options Chain",
        "Fundamentals", 
        "Live Portfolio", 
        "Trade Station",
        "Strategy Backtester"
    ])

    # [TAB 1: ADVANCED CHARTING]
    with tab1:
        st.markdown('<div class="moomoo-panel">', unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Spot Price", f"{currency_sym}{last_close:.2f}", f"{change_val:+.2f} ({change_pct:+.2f}%)")
        c2.metric("Day High", f"{currency_sym}{df['High'].iloc[-1]:.2f}")
        c3.metric("Day Low", f"{currency_sym}{df['Low'].iloc[-1]:.2f}")
        c4.metric("Trading Volume", f"{int(df['Volume'].iloc[-1]):,}")
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="moomoo-panel">', unsafe_allow_html=True)
        fig = make_subplots(
            rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03, 
            row_heights=[0.65, 0.15, 0.20],
            subplot_titles=(f"{ticker} Quote & Volatility", "Volume", "MACD Momentum")
        )
        
        # Moomoo Candlestick Colors (Green Up, Red Down)
        fig.add_trace(go.Candlestick(
            x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], 
            name='Price',
            increasing_line_color='#2EBD85', decreasing_line_color='#F6465D'
        ), row=1, col=1)
        
        fig.add_trace(go.Scatter(x=df['Date'], y=df['SMA_20'], line=dict(color='#F2B602', width=1.5), name='MA 20'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['Date'], y=df['SMA_50'], line=dict(color='#8F52E3', width=1.5), name='MA 50'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['Date'], y=df['BB_Upper'], line=dict(color='rgba(255,255,255,0.1)', width=1), name='BB Upper'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['Date'], y=df['BB_Lower'], line=dict(color='rgba(255,255,255,0.1)', width=1), fill='tonexty', fillcolor='rgba(255,255,255,0.03)', name='BB Lower'), row=1, col=1)
        
        colors = ['#2EBD85' if c >= o else '#F6465D' for c, o in zip(df['Close'], df['Open'])]
        fig.add_trace(go.Bar(x=df['Date'], y=df['Volume'], marker_color=colors, name='Volume', showlegend=False), row=2, col=1)
        
        macd_colors = ['#2EBD85' if h >= 0 else '#F6465D' for h in df['MACD_Hist']]
        fig.add_trace(go.Bar(x=df['Date'], y=df['MACD_Hist'], marker_color=macd_colors, name='MACD Hist', showlegend=False), row=3, col=1)
        fig.add_trace(go.Scatter(x=df['Date'], y=df['MACD'], line=dict(color='#00e5ff', width=1.5), name='MACD'), row=3, col=1)
        fig.add_trace(go.Scatter(x=df['Date'], y=df['MACD_Signal'], line=dict(color='#ff9100', width=1.5), name='Signal'), row=3, col=1)
        
        fig.update_layout(
            template="plotly_dark", 
            paper_bgcolor="#1e222d",
            plot_bgcolor="#1e222d",
            font=dict(color="#d1d4dc"),
            height=850, 
            margin=dict(l=10, r=10, t=30, b=10), 
            xaxis_rangeslider_visible=False
        )
        # Update grid colors for Moomoo look
        fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#2b3139')
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#2b3139')
        
        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="moomoo-panel">', unsafe_allow_html=True)
        st.subheader("Neural Target & AI Signal")
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
            
            ai1, ai2 = st.columns([1, 3])
            ai1.metric("Predicted Target", f"{currency_sym}{predicted_target:.2f}", f"{predicted_target - last_close:+.2f}")
            ai2.info(
                f"**Signal State:** {'🟢 BULLISH' if predicted_target > last_close else '🔴 BEARISH'}. "
                f"RSI oscillator stands at **{df['RSI'].iloc[-1]:.1f}** | MACD: **{df['MACD'].iloc[-1]:.2f}**."
            )
        st.markdown('</div>', unsafe_allow_html=True)

    # [TAB 2: OPTIONS CHAIN]
    with tab2:
        st.markdown('<div class="moomoo-panel">', unsafe_allow_html=True)
        st.subheader(f"Options Matrix: {ticker}")
        try:
            stock_obj = yf.Ticker(ticker)
            expirations = stock_obj.options
            if expirations:
                col_exp, col_opt_type = st.columns([1, 2])
                selected_exp = col_exp.selectbox("Expiration Date:", expirations)
                opt_type = col_opt_type.radio("Derivative Class:", ["Calls", "Puts"], horizontal=True)
                
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
                        }), use_container_width=True, height=700, hide_index=True
                    )
                else:
                    st.info("No options contracts traded for this expiration cycle.")
            else:
                st.info(f"Options derivatives are not listed for ticker '{ticker}'.")
        except Exception as e:
            st.warning(f"Could not load options data: {e}")
        st.markdown('</div>', unsafe_allow_html=True)

    # [TAB 3: VALUATION & FUNDAMENTALS]
    with tab3:
        st.markdown('<div class="moomoo-panel">', unsafe_allow_html=True)
        st.subheader(f"Company Valuation: {ticker}")
        f1, f2, f3, f4 = st.columns(4)
        f1.metric("Market Cap", f"{currency_sym}{stock_info.get('marketCap', 0):,}")
        f2.metric("Trailing P/E", f"{stock_info.get('trailingPE', 'N/A')}")
        f3.metric("Forward P/E", f"{stock_info.get('forwardPE', 'N/A')}")
        f4.metric("Beta", f"{stock_info.get('beta', 'N/A')}")
        
        st.markdown("<br>", unsafe_allow_html=True)
        f5, f6, f7, f8 = st.columns(4)
        f5.metric("52W High", f"{currency_sym}{stock_info.get('fiftyTwoWeekHigh', 'N/A')}")
        f6.metric("52W Low", f"{currency_sym}{stock_info.get('fiftyTwoWeekLow', 'N/A')}")
        f7.metric("Dividend Yield", f"{(stock_info.get('dividendYield', 0) or 0)*100:.2f}%")
        f8.metric("Operating Margin", f"{(stock_info.get('profitMargins', 0) or 0)*100:.2f}%")
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="moomoo-panel">', unsafe_allow_html=True)
        st.subheader("Market News")
        if news_data:
            n_col1, n_col2 = st.columns(2)
            for i, item in enumerate(news_data):
                col = n_col1 if i % 2 == 0 else n_col2
                with col:
                    st.markdown(f"#### [{item['title']}]({item['link']})")
                    st.caption(f"Source: **{item['publisher']}**")
                    st.write("---")
        else:
            st.write("No active news items available for this asset.")
        st.markdown('</div>', unsafe_allow_html=True)

    # [TAB 4: LIVE PORTFOLIO]
    with tab4:
        st.markdown('<div class="moomoo-panel">', unsafe_allow_html=True)
        st.subheader("Live Execution Portfolio")
        if not api_key or not secret_key:
            st.error("Alpaca Trading API credentials missing.")
        else:
            try:
                client = TradingClient(api_key, secret_key, paper=True)
                acc = client.get_account()
                p1, p2, p3, p4 = st.columns(4)
                p1.metric("Portfolio Equity", f"${float(acc.equity or 0.0):,.2f}")
                p2.metric("Buying Power", f"${float(acc.buying_power or 0.0):,.2f}")
                p3.metric("Cash Balance", f"${float(acc.cash or 0.0):,.2f}")
                dt_power = acc.daytrading_buying_power if acc.daytrading_buying_power is not None else acc.buying_power
                p4.metric("Daytrade Power", f"${float(dt_power or 0.0):,.2f}")
                
                st.divider()
                st.subheader("Open Positions")
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
                    }), use_container_width=True, height=550, hide_index=True)
            except Exception as e:
                st.error(f"Connection Failed: {e}")
        st.markdown('</div>', unsafe_allow_html=True)

    # [TAB 5: TRADE STATION]
    with tab5:
        st.markdown('<div class="moomoo-panel">', unsafe_allow_html=True)
        st.subheader(f"Execution Desk: {ticker}")
        t_col1, t_col2 = st.columns([1, 1.5]) 
        with t_col1:
            st.info(f"**Live Quote:** {currency_sym}{last_close:.2f}")
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
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Transmit Order to Alpaca", use_container_width=True, type="primary"):
                if not api_key or not secret_key:
                    st.error("Alpaca API Keys missing.")
                elif is_foreign:
                    st.error("Broker Rejection: Alpaca US broker does not support foreign equities/indices.")
                else:
                    try:
                        trading_client = TradingClient(api_key, secret_key, paper=True)
                        side_choice = OrderSide.BUY if order_side == "Buy" else OrderSide.SELL
                        if order_style == "Limit Order":
                            order_payload = LimitOrderRequest(symbol=ticker, qty=order_qty, side=side_choice, time_in_force=TimeInForce.DAY, limit_price=limit_px)
                        else:
                            order_payload = MarketOrderRequest(symbol=ticker, qty=order_qty, side=side_choice, time_in_force=TimeInForce.DAY)
                        submitted = trading_client.submit_order(order_data=order_payload)
                        st.success(f"Order Transmitted! ID: `{submitted.id}`")
                    except Exception as e:
                        st.error(f"Routing Rejected: {e}")
        with t_col2:
            st.write("### Account Liquidity")
            if api_key and secret_key:
                try:
                    client = TradingClient(api_key, secret_key, paper=True)
                    account_meta = client.get_account()
                    
                    l_col1, l_col2 = st.columns(2)
                    l_col1.metric("Equity Balance", f"${float(account_meta.equity or 0.0):,.2f}")
                    l_col2.metric("Available Buying Power", f"${float(account_meta.buying_power or 0.0):,.2f}")
                    
                    st.divider()
                    st.write("### Execution Log")
                    order_req = GetOrdersRequest(status=QueryOrderStatus.ALL, limit=30)
                    orders = client.get_orders(filter=order_req)
                    if orders:
                        ord_list = [{
                            'Time': o.created_at.strftime('%Y-%m-%d %H:%M') if o.created_at else 'N/A',
                            'Symbol': o.symbol,
                            'Side': str(o.side).split('.')[-1].upper(),
                            'Qty': float(o.qty) if o.qty else 0.0,
                            'Status': str(o.status).split('.')[-1].upper()
                        } for o in orders]
                        st.dataframe(pd.DataFrame(ord_list), use_container_width=True, height=400, hide_index=True)
                    else:
                        st.info("No recent transactions found.")
                except Exception:
                    st.warning("Could not sync live account data.")
        st.markdown('</div>', unsafe_allow_html=True)

    # [TAB 6: BACKTESTER]
    with tab6:
        st.markdown('<div class="moomoo-panel">', unsafe_allow_html=True)
        st.subheader(f"Strategy Simulator: {ticker}")
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
            b_fig.add_trace(go.Scatter(x=b_df['Date'], y=b_df['Cum_Strategy'] * 100, name='SMA Crossover Alpha', line=dict(color='#FF6933', width=2.5)))
            b_fig.add_trace(go.Scatter(x=b_df['Date'], y=b_df['Cum_Market'] * 100, name='Buy & Hold Benchmark', line=dict(color='#888888', width=2, dash='dot')))
            
            b_fig.update_layout(
                template="plotly_dark", 
                paper_bgcolor="#1e222d",
                plot_bgcolor="#1e222d",
                font=dict(color="#d1d4dc"),
                height=750, 
                yaxis_title="Cumulative Return (%)", 
                margin=dict(l=10, r=10, t=30, b=10)
            )
            b_fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#2b3139')
            b_fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#2b3139')
            
            st.plotly_chart(b_fig, use_container_width=True)
            
            r1, r2, r3, r4 = st.columns(4)
            r1.metric("Strategy Net Return", f"{b_df['Cum_Strategy'].iloc[-1] * 100:+.2f}%")
            r2.metric("Buy & Hold Return", f"{b_df['Cum_Market'].iloc[-1] * 100:+.2f}%")
            r3.metric("Alpha Generated", f"{(b_df['Cum_Strategy'].iloc[-1] - b_df['Cum_Market'].iloc[-1]) * 100:+.2f}%")
            r4.metric("Max Drawdown Risk", f"{max_drawdown:.2f}%")
        else:
            st.info("Insufficient historical points to execute strategy simulation.")
        st.markdown('</div>', unsafe_allow_html=True)

# --- 5. APPLICATION ROUTING ---
if not st.session_state["logged_in"]:
    auth_screen()
else:
    main_app()
