# --- TAB 4: TRADE STATION (ALPACA PAPER TRADING) ---
with tab4:
    st.subheader(f"⚡ Execute Order: {ticker} (Live Paper Trading)")
    
    st.markdown("Enter your [Alpaca Paper Trading](https://alpaca.markets/) API keys below:")
    col_k1, col_k2 = st.columns(2)
    api_key = col_k1.text_input("Alpaca API Key", type="password")
    secret_key = col_k2.text_input("Alpaca Secret Key", type="password")
    
    st.divider()
    
    t1, t2 = st.columns(2)
    
    with t1:
        st.info(f"**Current Market Price:** ${last_close:.2f}")
        action = st.radio("Action", ["Buy", "Sell"], horizontal=True)
        quantity = st.number_input("Quantity (Shares)", min_value=0.01, value=1.0, step=1.0)
        
        st.write(f"**Estimated Order Value:** ${last_close * quantity:,.2f}")
        
        if st.button("Place Paper Trade via Alpaca"):
            if not api_key or not secret_key:
                st.error("⚠️ Please enter your Alpaca API Key and Secret Key above to connect.")
            else:
                with st.spinner("Transmitting order to Alpaca exchange..."):
                    try:
                        from alpaca.trading.client import TradingClient
                        from alpaca.trading.requests import MarketOrderRequest
                        from alpaca.trading.enums import OrderSide, TimeInForce
                        
                        trading_client = TradingClient(api_key, secret_key, paper=True)
                        side = OrderSide.BUY if action == "Buy" else OrderSide.SELL
                        
                        market_order_data = MarketOrderRequest(
                            symbol=ticker,
                            qty=quantity,
                            side=side,
                            time_in_force=TimeInForce.DAY
                        )
                        
                        order = trading_client.submit_order(order_data=market_order_data)
                        st.success(f"✅ Order successfully routed to Alpaca!")
                        st.write(f"**Order ID:** `{order.id}`")
                        st.write(f"**Status:** `{order.status}`")
                    except Exception as e:
                        st.error(f"❌ Order Failed: {e}")
                        
    with t2:
        st.write("### Live Account Status")
        if st.button("Check Buying Power"):
            if api_key and secret_key:
                try:
                    from alpaca.trading.client import TradingClient
                    client = TradingClient(api_key, secret_key, paper=True)
                    account = client.get_account()
                    st.metric("Total Equity", f"${float(account.equity):,.2f}")
                    st.metric("Buying Power", f"${float(account.buying_power):,.2f}")
                except Exception as e:
                    st.error("Could not fetch account details. Check your API keys.")
            else:
                st.warning("Enter keys above to view account status.")
