from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import requests
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import logging
import threading
import time
from typing import Dict, List, Tuple
import json

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Twelve Data API configuration
TWELVE_DATA_API_KEY = "your_twelve_data_api_key_here"  # Replace with your actual API key
BASE_URL = "https://api.twelvedata.com"

# Global variables for real-time data
active_portfolios = {}
real_time_data_cache = {}
last_fetch_time = {}

class RealTimePortfolioAnalyzer:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.risk_free_rate = 0.02  # 2% annual risk-free rate
        self.market_hours = self._get_market_hours()
    
    def _get_market_hours(self):
        """Get market trading hours (9:30 AM - 4:00 PM EST)"""
        return {
            'open': 9.5,  # 9:30 AM
            'close': 16.0  # 4:00 PM
        }
    
    def is_market_open(self):
        """Check if market is currently open"""
        now = datetime.now()
        current_hour = now.hour + now.minute / 60.0
        
        # Check if it's a weekday and within market hours
        if now.weekday() < 5:  # Monday = 0, Friday = 4
            return self.market_hours['open'] <= current_hour <= self.market_hours['close']
        return False
    
    def fetch_real_time_quotes(self, symbols: List[str]) -> Dict:
        """Fetch real-time quotes from Twelve Data API"""
        quotes = {}
        
        for symbol in symbols:
            try:
                # Use real-time quote endpoint
                url = f"{BASE_URL}/quote"
                params = {
                    'symbol': symbol,
                    'apikey': self.api_key
                }
                
                response = requests.get(url, params=params, timeout=5)
                data = response.json()
                
                if 'close' in data:
                    quotes[symbol] = {
                        'price': float(data['close']),
                        'change': float(data.get('change', 0)),
                        'change_percent': float(data.get('percent_change', 0)),
                        'volume': int(data.get('volume', 0)),
                        'timestamp': datetime.now().isoformat(),
                        'is_market_open': self.is_market_open()
                    }
                else:
                    # Fallback to mock data if API fails
                    quotes[symbol] = self._generate_mock_quote(symbol)
                    
            except Exception as e:
                logger.error(f"Error fetching real-time data for {symbol}: {str(e)}")
                quotes[symbol] = self._generate_mock_quote(symbol)
        
        return quotes
    
    def _generate_mock_quote(self, symbol: str) -> Dict:
        """Generate mock real-time quote for demonstration"""
        base_price = hash(symbol) % 200 + 50  # Generate consistent base price
        change_percent = (np.random.random() - 0.5) * 4  # ±2% random change
        price = base_price * (1 + change_percent / 100)
        
        return {
            'price': round(price, 2),
            'change': round(price - base_price, 2),
            'change_percent': round(change_percent, 2),
            'volume': np.random.randint(10000, 1000000),
            'timestamp': datetime.now().isoformat(),
            'is_market_open': self.is_market_open()
        }
    
    def fetch_historical_data(self, symbols: List[str], period: str = "1year") -> Dict:
        """Fetch historical stock data from Twelve Data API"""
        stock_data = {}
        
        for symbol in symbols:
            try:
                url = f"{BASE_URL}/time_series"
                params = {
                    'symbol': symbol,
                    'interval': '1day',
                    'outputsize': 252,  # ~1 year of trading days
                    'apikey': self.api_key
                }
                
                response = requests.get(url, params=params, timeout=10)
                data = response.json()
                
                if 'values' in data and len(data['values']) > 0:
                    # Convert to DataFrame
                    df = pd.DataFrame(data['values'])
                    df['date'] = pd.to_datetime(df['datetime'])
                    df['close'] = pd.to_numeric(df['close'])
                    df = df.sort_values('date')
                    
                    # Calculate daily returns
                    df['returns'] = df['close'].pct_change().dropna()
                    
                    stock_data[symbol] = {
                        'prices': df['close'].values,
                        'returns': df['returns'].dropna().values,
                        'dates': df['date'].values
                    }
                else:
                    logger.warning(f"No historical data for {symbol}, using mock data")
                    stock_data[symbol] = self._generate_mock_historical_data()
                    
            except Exception as e:
                logger.error(f"Error fetching historical data for {symbol}: {str(e)}")
                stock_data[symbol] = self._generate_mock_historical_data()
        
        return stock_data
    
    def _generate_mock_historical_data(self) -> Dict:
        """Generate mock historical data for demonstration"""
        np.random.seed(42)
        returns = np.random.normal(0.0008, 0.02, 252)  # Daily returns
        prices = 100 * np.cumprod(1 + returns)
        dates = pd.date_range(start='2023-01-01', periods=252, freq='D')
        
        return {
            'prices': prices,
            'returns': returns,
            'dates': dates
        }
    
    def calculate_real_time_portfolio_metrics(self, portfolio: List[Dict], 
                                            current_prices: Dict, 
                                            historical_data: Dict) -> Dict:
        """Calculate portfolio metrics with real-time prices"""
        symbols = [holding['symbol'] for holding in portfolio]
        weights = np.array([holding['allocation'] / 100 for holding in portfolio])
        
        # Calculate current portfolio value
        portfolio_value = 0
        total_change = 0
        