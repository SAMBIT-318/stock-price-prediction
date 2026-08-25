import streamlit as st
import yfinance as yf
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from datetime import date, timedelta

# 1. Set up the Streamlit interface
st.title("📈 Stock Price Prediction App")
st.write("This app predicts the next trading day's closing price for Apple (AAPL) using a Random Forest Regressor.")

# 2. Fetch the data using yfinance
@st.cache_data 
def load_data(ticker):
    start_date = date.today() - timedelta(days=365 * 5) # Get last 5 years of data
    end_date = date.today()
    data = yf.download(ticker, start=start_date, end=end_date)
    
    # FIX: Flatten the complex column headers caused by the new yfinance update
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
        
    data.reset_index(inplace=True)
    return data

data_load_state = st.text('Loading data...')
df = load_data('AAPL')
data_load_state.text('Loading data... done!')

# 3. Display raw data and charts
st.subheader('Historical Closing Price')
st.line_chart(df.set_index('Date')['Close'])

st.subheader('Recent Raw Data')
st.write(df.tail())

# 4. Prepare data for the Random Forest model
st.write("---")
st.subheader("🤖 Model Training & Prediction")
st.write("Training Random Forest model on historical data...")

# Create a simple feature: using the previous day's close to predict today's close
df['Prev_Close'] = df['Close'].shift(1)
df_model = df.dropna() # Drop the first row which now has a NaN value

X = df_model[['Prev_Close']] # Features
y = df_model['Close']        # Target variable

# 5. Train the model
model = RandomForestRegressor(n_estimators=100, random_state=42)
model.fit(X, y)

# 6. Predict the next day
last_available_price = float(df['Close'].iloc[-1])

# Scikit-learn expects the prediction input to have the exact same column names as the training data
input_df = pd.DataFrame({'Prev_Close': [last_available_price]})
next_day_prediction = model.predict(input_df)

# 7. Display the result
st.metric(
    label="Predicted Next Day Closing Price (AAPL)", 
    value=f"${next_day_prediction[0]:.2f}",
    delta=f"{next_day_prediction[0] - last_available_price:.2f} from last close"
)
