# from flask import Flask, request, jsonify
# from flask_cors import CORS
# import os
# import requests
# import pandas as pd
# import numpy as np
# from datetime import datetime, timedelta
# import warnings
# from dotenv import load_dotenv

# warnings.filterwarnings("ignore")

# # ML Models
# from prophet import Prophet
# from statsmodels.tsa.arima.model import ARIMA
# from sklearn.preprocessing import MinMaxScaler
# from sklearn.metrics import mean_absolute_error, mean_squared_error
# import tensorflow as tf
# from tensorflow.keras.models import Sequential
# from tensorflow.keras.layers import LSTM, Dense, Dropout

# app = Flask(__name__)
# CORS(app)

# # Load API key from environment (.env) instead of hardcoding
# load_dotenv()
# TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY")
# TWELVE_DATA_BASE_URL = "https://api.twelvedata.com"

# class StockPredictor:
#     def __init__(self, api_key):
#         self.api_key = api_key
        
#     def fetch_stock_data(self, symbol, interval="1day", outputsize=60):
#         """Fetch historical stock data from Twelve Data API"""
#         try:
#             url = f"{TWELVE_DATA_BASE_URL}/time_series"
#             params = {
#                 'symbol': symbol,
#                 'interval': interval,
#                 'outputsize': outputsize,
#                 'apikey': self.api_key
#             }
            
#             response = requests.get(url, params=params)
#             data = response.json()
            
#             if 'values' in data:
#                 df = pd.DataFrame(data['values'])
#                 df['datetime'] = pd.to_datetime(df['datetime'])
#                 df = df.sort_values('datetime')
                
#                 # Convert price columns to float
#                 for col in ['open', 'high', 'low', 'close', 'volume']:
#                     df[col] = pd.to_numeric(df[col], errors='coerce')
                
#                 return df
#             else:
#                 raise Exception(f"Error fetching data: {data.get('message', 'Unknown error')}")
                
#         except Exception as e:
#             print(f"Error fetching stock data: {e}")
#             return None
    
#     def get_stock_info(self, symbol):
#         """Get current stock information"""
#         try:
#             url = f"{TWELVE_DATA_BASE_URL}/quote"
#             params = {
#                 'symbol': symbol,
#                 'apikey': self.api_key
#             }
            
#             response = requests.get(url, params=params)
#             data = response.json()
            
#             return {
#                 'symbol': data.get('symbol', symbol),
#                 'name': data.get('name', 'Unknown Company'),
#                 'current_price': float(data.get('close', 0)),
#                 'change': float(data.get('percent_change', 0))
#             }
#         except Exception as e:
#             print(f"Error fetching stock info: {e}")
#             return None
    
#     def predict_with_prophet(self, df, days=7):
#         """Prophet time series prediction"""
#         try:
#             # Prepare data for Prophet
#             prophet_df = df[['datetime', 'close']].copy()
#             prophet_df.columns = ['ds', 'y']
            
#             # Create and fit model
#             model = Prophet(
#                 daily_seasonality=True,
#                 weekly_seasonality=True,
#                 yearly_seasonality=False,
#                 interval_width=0.95
#             )
#             model.fit(prophet_df)
            
#             # Make future predictions
#             future = model.make_future_dataframe(periods=days)
#             forecast = model.predict(future)
            
#             # Extract predictions for the next 7 days
#             predictions = []
#             for i in range(len(forecast) - days, len(forecast)):
#                 pred_date = forecast.iloc[i]['ds'].strftime('%Y-%m-%d')
#                 pred_price = max(0, forecast.iloc[i]['yhat'])
#                 upper_bound = max(0, forecast.iloc[i]['yhat_upper'])
#                 lower_bound = max(0, forecast.iloc[i]['yhat_lower'])
                
#                 # Calculate confidence based on prediction interval width
#                 confidence = 1 - (upper_bound - lower_bound) / pred_price if pred_price > 0 else 0.8
#                 confidence = min(max(confidence, 0.5), 0.95)
                
#                 predictions.append({
#                     'date': pred_date,
#                     'predicted_price': round(pred_price, 2),
#                     'confidence': round(confidence, 3),
#                     'upper_bound': round(upper_bound, 2),
#                     'lower_bound': round(lower_bound, 2)
#                 })
            
#             # Calculate metrics
#             actual_values = prophet_df['y'].values
#             predicted_values = forecast['yhat'].iloc[:len(actual_values)].values
            
#             mae = mean_absolute_error(actual_values, predicted_values)
#             rmse = np.sqrt(mean_squared_error(actual_values, predicted_values))
            
#             return predictions, {'mae': round(mae, 2), 'rmse': round(rmse, 2)}
            
#         except Exception as e:
#             print(f"Prophet prediction error: {e}")
#             return None, None
    
#     def predict_with_arima(self, df, days=7):
#         """ARIMA statistical prediction"""
#         try:
#             prices = df['close'].values
            
#             # Fit ARIMA model
#             model = ARIMA(prices, order=(5, 1, 0))
#             fitted_model = model.fit()
            
#             # Make predictions
#             forecast_result = fitted_model.forecast(steps=days)
#             conf_int = fitted_model.get_forecast(steps=days).conf_int()
            
#             predictions = []
#             current_date = df['datetime'].max()
            
#             for i in range(days):
#                 pred_date = (current_date + timedelta(days=i+1)).strftime('%Y-%m-%d')
#                 pred_price = max(0, forecast_result[i])
#                 upper_bound = max(0, conf_int.iloc[i, 1])
#                 lower_bound = max(0, conf_int.iloc[i, 0])
                
#                 # Calculate confidence
#                 confidence = 0.85 - (i * 0.05)  # Decreasing confidence over time
#                 confidence = max(confidence, 0.6)
                
#                 predictions.append({
#                     'date': pred_date,
#                     'predicted_price': round(pred_price, 2),
#                     'confidence': round(confidence, 3),
#                     'upper_bound': round(upper_bound, 2),
#                     'lower_bound': round(lower_bound, 2)
#                 })
            
#             # Calculate metrics
#             residuals = fitted_model.resid
#             mae = np.mean(np.abs(residuals))
#             rmse = np.sqrt(np.mean(residuals**2))
            
#             return predictions, {'mae': round(mae, 2), 'rmse': round(rmse, 2)}
            
#         except Exception as e:
#             print(f"ARIMA prediction error: {e}")
#             return None, None
    
#     def predict_with_lstm(self, df, days=7):
#         """LSTM deep learning prediction"""
#         try:
#             prices = df['close'].values.reshape(-1, 1)
            
#             # Scale the data
#             scaler = MinMaxScaler(feature_range=(0, 1))
#             scaled_prices = scaler.fit_transform(prices)
            
#             # Prepare training data
#             sequence_length = 10
#             if len(scaled_prices) < sequence_length + 1:
#                 raise Exception("Not enough data for LSTM prediction")
            
#             X, y = [], []
#             for i in range(sequence_length, len(scaled_prices)):
#                 X.append(scaled_prices[i-sequence_length:i, 0])
#                 y.append(scaled_prices[i, 0])
            
#             X, y = np.array(X), np.array(y)
#             X = np.reshape(X, (X.shape[0], X.shape[1], 1))
            
#             # Build LSTM model
#             model = Sequential([
#                 LSTM(50, return_sequences=True, input_shape=(sequence_length, 1)),
#                 Dropout(0.2),
#                 LSTM(50, return_sequences=False),
#                 Dropout(0.2),
#                 Dense(25),
#                 Dense(1)
#             ])
            
#             model.compile(optimizer='adam', loss='mean_squared_error')
            
#             # Train model (with limited epochs for demo)
#             model.fit(X, y, batch_size=1, epochs=5, verbose=0)
            
#             # Make predictions
#             predictions = []
#             current_sequence = scaled_prices[-sequence_length:]
#             current_date = df['datetime'].max()
            
#             for i in range(days):
#                 # Predict next value
#                 next_pred = model.predict(current_sequence.reshape(1, sequence_length, 1), verbose=0)
#                 pred_price_scaled = next_pred[0, 0]
                
#                 # Transform back to original scale
#                 pred_price = scaler.inverse_transform([[pred_price_scaled]])[0, 0]
#                 pred_price = max(0, pred_price)
                
#                 # Generate confidence intervals (simplified)
#                 noise_factor = 0.1 * (i + 1)  # Increasing uncertainty over time
#                 upper_bound = pred_price * (1 + noise_factor)
#                 lower_bound = pred_price * (1 - noise_factor)
                
#                 confidence = 0.9 - (i * 0.05)  # Decreasing confidence
#                 confidence = max(confidence, 0.6)
                
#                 pred_date = (current_date + timedelta(days=i+1)).strftime('%Y-%m-%d')
                
#                 predictions.append({
#                     'date': pred_date,
#                     'predicted_price': round(pred_price, 2),
#                     'confidence': round(confidence, 3),
#                     'upper_bound': round(upper_bound, 2),
#                     'lower_bound': round(lower_bound, 2)
#                 })
                
#                 # Update sequence for next prediction
#                 current_sequence = np.append(current_sequence[1:], [[pred_price_scaled]], axis=0)
            
#             # Calculate metrics (simplified)
#             train_predictions = model.predict(X, verbose=0)
#             train_predictions = scaler.inverse_transform(train_predictions)
#             actual_train = scaler.inverse_transform(y.reshape(-1, 1))
            
#             mae = mean_absolute_error(actual_train, train_predictions)
#             rmse = np.sqrt(mean_squared_error(actual_train, train_predictions))

#             return predictions, {"mae": round(mae, 2), "rmse": round(rmse, 2)}