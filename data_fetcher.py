import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf
import time

class TradingViewDataFetcher:
    """Data fetcher for stock data using Yahoo Finance as fallback"""
    
    def __init__(self):
        self.session = None
        
    def get_stock_data(self, symbol, period='5d', interval='1d'):
        """
        Fetch stock data for given symbol, period and interval
        
        Args:
            symbol (str): Stock symbol (BIST stocks should have .IS suffix)
            period (str): Time period ('1d', '5d', '1mo', '3mo', etc.)
            interval (str): Data interval ('5m', '15m', '1h', '4h', '1d', '1wk')
            
        Returns:
            pandas.DataFrame: Stock data with OHLCV columns
        """
        try:
            # Add .IS suffix for BIST stocks if not present
            if not symbol.endswith('.IS'):
                yf_symbol = f"{symbol}.IS"
            else:
                yf_symbol = symbol
            
            # Create ticker object
            ticker = yf.Ticker(yf_symbol)
            
            # Fetch data with interval
            data = ticker.history(period=period, interval=interval)
            
            if data.empty:
                print(f"No data found for {symbol}")
                return None
            
            # Standardize column names
            data.columns = data.columns.str.lower()
            
            # Ensure required columns exist
            required_columns = ['open', 'high', 'low', 'close', 'volume']
            missing_columns = [col for col in required_columns if col not in data.columns]
            
            if missing_columns:
                print(f"Missing columns for {symbol}: {missing_columns}")
                return None
            
            # Clean data
            data = self._clean_data(data)
            
            return data
            
        except Exception as e:
            print(f"Error fetching data for {symbol}: {str(e)}")
            return None
    
    def _clean_data(self, data):
        """Clean and validate stock data"""
        if data is None or data.empty:
            return None
        
        # Remove rows with NaN values in critical columns
        data = data.dropna(subset=['close', 'volume'])
        
        # Remove rows with zero volume (invalid data)
        data = data[data['volume'] > 0]
        
        # Remove rows with zero or negative prices
        data = data[data['close'] > 0]
        data = data[data['high'] > 0]
        data = data[data['low'] > 0]
        data = data[data['open'] > 0]
        
        # Ensure high >= low >= 0
        data = data[data['high'] >= data['low']]
        
        # Sort by index (date)
        data = data.sort_index()
        
        return data
    
    def get_multiple_stocks_data(self, symbols, period='5d', interval='1d'):
        """
        Fetch data for multiple stocks
        
        Args:
            symbols (list): List of stock symbols
            period (str): Time period
            interval (str): Data interval
            
        Returns:
            dict: Dictionary with symbol as key and DataFrame as value
        """
        results = {}
        
        for symbol in symbols:
            try:
                data = self.get_stock_data(symbol, period, interval)
                if data is not None:
                    results[symbol] = data
                
                # Rate limiting to avoid being blocked
                time.sleep(0.2)
                
            except Exception as e:
                print(f"Error fetching {symbol}: {str(e)}")
                continue
        
        return results
    
    def validate_data_quality(self, data):
        """
        Validate data quality and return quality score
        
        Args:
            data (pandas.DataFrame): Stock data
            
        Returns:
            dict: Quality metrics
        """
        if data is None or data.empty:
            return {'score': 0, 'issues': ['No data']}
        
        issues = []
        score = 100
        
        # Check for missing values
        missing_pct = data.isnull().sum().sum() / (len(data) * len(data.columns)) * 100
        if missing_pct > 0:
            issues.append(f"Missing values: {missing_pct:.1f}%")
            score -= missing_pct * 2
        
        # Check for zero volumes
        zero_volume_pct = (data['volume'] == 0).sum() / len(data) * 100
        if zero_volume_pct > 0:
            issues.append(f"Zero volume periods: {zero_volume_pct:.1f}%")
            score -= zero_volume_pct * 3
        
        # Check for price anomalies (high < low)
        price_anomalies = (data['high'] < data['low']).sum()
        if price_anomalies > 0:
            issues.append(f"Price anomalies: {price_anomalies}")
            score -= price_anomalies * 10
        
        # Check data freshness (should be recent)
        last_date = data.index[-1].date()
        days_old = (datetime.now().date() - last_date).days
        if days_old > 7:
            issues.append(f"Data is {days_old} days old")
            score -= days_old
        
        return {
            'score': max(0, score),
            'issues': issues,
            'data_points': len(data),
            'date_range': f"{data.index[0].date()} to {data.index[-1].date()}"
        }
