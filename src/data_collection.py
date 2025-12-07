"""
Data collection module for UMG DCF Valuation Model
Collects financial data from multiple sources including Yahoo Finance,
company investor relations website, and market data
"""

import yfinance as yf
import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
import os
import sys
import json
from datetime import datetime
from typing import Dict, Optional, Tuple

# Add parent directory to path for config import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


class DataCollector:
    """Collects financial and market data from various sources"""
    
    def __init__(self, ticker: str = None):
        """
        Initialize data collector
        
        Args:
            ticker: Stock ticker symbol (defaults to config value)
        """
        self.ticker = ticker or config.YAHOO_FINANCE_TICKER
        self.company_name = config.COMPANY_NAME
        self.data = {}
        
    def collect_all_data(self) -> Dict:
        """
        Collect all required data from all sources
        
        Returns:
            Dictionary containing all collected data
        """
        print(f"Collecting data for {self.company_name} ({self.ticker})...")
        
        # Collect from Yahoo Finance
        print("  - Fetching data from Yahoo Finance...")
        yahoo_data = self.collect_yahoo_finance_data()
        self.data.update(yahoo_data)
        
        # Collect market data
        print("  - Fetching market data...")
        market_data = self.collect_market_data()
        self.data.update(market_data)
        
        # Collect peer data
        print("  - Fetching peer company data...")
        peer_data = self.collect_peer_data()
        self.data['peers'] = peer_data
        
        # Collect macro data
        print("  - Fetching macroeconomic data...")
        macro_data = self.collect_macro_data()
        self.data.update(macro_data)
        
        # Save raw data
        self.save_raw_data()
        
        print("Data collection complete!")
        return self.data
    
    def collect_yahoo_finance_data(self) -> Dict:
        """
        Collect financial statements and market data from Yahoo Finance
        
        Returns:
            Dictionary with financial statements and market data
        """
        try:
            stock = yf.Ticker(self.ticker)
            info = stock.info
            
            # Get financial statements
            income_stmt = stock.financials
            balance_sheet = stock.balance_sheet
            cash_flow = stock.cashflow
            
            # Get historical prices
            hist = stock.history(period="5y")
            
            # Get analyst data
            try:
                recommendations = stock.recommendations
            except:
                recommendations = None
            
            # Standardize column names (Yahoo Finance uses dates as columns)
            income_stmt = self._standardize_financial_statement(income_stmt, 'income')
            balance_sheet = self._standardize_financial_statement(balance_sheet, 'balance')
            cash_flow = self._standardize_financial_statement(cash_flow, 'cashflow')
            
            return {
                'income_statement': income_stmt,
                'balance_sheet': balance_sheet,
                'cash_flow': cash_flow,
                'stock_info': info,
                'price_history': hist,
                'recommendations': recommendations,
                'current_price': hist['Close'].iloc[-1] if not hist.empty else None,
                'market_cap': info.get('marketCap', None),
                'beta': info.get('beta', None),
                'shares_outstanding': info.get('sharesOutstanding', None),
            }
        except Exception as e:
            print(f"  Warning: Error collecting Yahoo Finance data: {e}")
            return {}
    
    def _standardize_financial_statement(self, df: pd.DataFrame, 
                                        statement_type: str) -> pd.DataFrame:
        """
        Standardize financial statement column names and structure
        
        Args:
            df: Raw financial statement DataFrame
            statement_type: Type of statement ('income', 'balance', 'cashflow')
            
        Returns:
            Standardized DataFrame
        """
        if df.empty:
            return pd.DataFrame()
        
        # Transpose if dates are columns
        if df.columns.dtype == 'datetime64[ns]':
            df = df.T
            df.index.name = 'Date'
            df = df.reset_index()
        
        # Map Yahoo Finance line items to standard names
        mapping = self._get_line_item_mapping(statement_type)
        
        # Create standardized DataFrame
        standardized = pd.DataFrame()
        standardized['Date'] = df.index if 'Date' not in df.columns else df['Date']
        
        for yahoo_name, standard_name in mapping.items():
            if yahoo_name in df.index:
                standardized[standard_name] = df.loc[yahoo_name].values
            elif yahoo_name in df.columns:
                standardized[standard_name] = df[yahoo_name].values
        
        return standardized
    
    def _get_line_item_mapping(self, statement_type: str) -> Dict[str, str]:
        """Get mapping from Yahoo Finance line items to standard names"""
        if statement_type == 'income':
            return {
                'Total Revenue': 'Revenue',
                'Cost Of Revenue': 'Cost of Revenue',
                'Gross Profit': 'Gross Profit',
                'Operating Income': 'Operating Income',
                'EBIT': 'EBIT',
                'EBITDA': 'EBITDA',
                'Interest Expense': 'Interest Expense',
                'Income Before Tax': 'Income Before Tax',
                'Income Tax Expense': 'Income Tax Expense',
                'Net Income': 'Net Income',
            }
        elif statement_type == 'balance':
            return {
                'Total Current Assets': 'Current Assets',
                'Total Assets': 'Total Assets',
                'Total Current Liabilities': 'Current Liabilities',
                'Total Debt': 'Total Debt',
                'Total Liabilities': 'Total Liabilities',
                'Total Stockholder Equity': 'Total Equity',
                'Cash And Cash Equivalents': 'Cash and Cash Equivalents',
            }
        elif statement_type == 'cashflow':
            return {
                'Total Cash From Operating Activities': 'Operating Cash Flow',
                'Capital Expenditures': 'Capital Expenditures',
                'Total Cashflows From Investing Activities': 'Investing Cash Flow',
                'Total Cash From Financing Activities': 'Financing Cash Flow',
                'Net Change In Cash': 'Net Change in Cash',
            }
        return {}
    
    def collect_market_data(self) -> Dict:
        """
        Collect additional market data
        
        Returns:
            Dictionary with market data
        """
        try:
            stock = yf.Ticker(self.ticker)
            info = stock.info
            
            # Get current market data
            current_data = stock.history(period="1d")
            
            return {
                'current_price': current_data['Close'].iloc[-1] if not current_data.empty else None,
                '52_week_high': info.get('fiftyTwoWeekHigh', None),
                '52_week_low': info.get('fiftyTwoWeekLow', None),
                'volume': info.get('volume', None),
                'average_volume': info.get('averageVolume', None),
                'dividend_yield': info.get('dividendYield', None),
                'payout_ratio': info.get('payoutRatio', None),
            }
        except Exception as e:
            print(f"  Warning: Error collecting market data: {e}")
            return {}
    
    def collect_peer_data(self) -> Dict:
        """
        Collect data for peer companies
        
        Returns:
            Dictionary with peer company data
        """
        peer_data = {}
        
        for peer in config.PEER_COMPANIES:
            ticker = peer['ticker']
            print(f"    - Collecting data for {peer['name']} ({ticker})...")
            
            try:
                stock = yf.Ticker(ticker)
                info = stock.info
                
                # Get key financial metrics
                income_stmt = stock.financials
                balance_sheet = stock.balance_sheet
                
                peer_data[ticker] = {
                    'name': peer['name'],
                    'market_cap': info.get('marketCap', None),
                    'beta': info.get('beta', None),
                    'current_price': info.get('currentPrice', None),
                    'ev_ebitda': info.get('enterpriseToEbitda', None),
                    'pe_ratio': info.get('trailingPE', None),
                    'pb_ratio': info.get('priceToBook', None),
                    'revenue': income_stmt.loc['Total Revenue'].iloc[0] if 'Total Revenue' in income_stmt.index else None,
                    'ebitda': income_stmt.loc['EBITDA'].iloc[0] if 'EBITDA' in income_stmt.index else None,
                }
            except Exception as e:
                print(f"      Warning: Could not collect data for {ticker}: {e}")
                peer_data[ticker] = {'name': peer['name'], 'error': str(e)}
        
        return peer_data
    
    def collect_macro_data(self) -> Dict:
        """
        Collect macroeconomic data (risk-free rate, equity risk premium)
        
        Returns:
            Dictionary with macroeconomic data
        """
        # For Netherlands/Eurozone, use 10-year German Bund as proxy for risk-free rate
        # In practice, you might want to use actual Dutch government bond data
        
        try:
            # Get 10-year German Bund yield (proxy for Eurozone risk-free rate)
            bund = yf.Ticker("^TNX")  # 10-year Treasury note (US - need to find Euro equivalent)
            # Note: Yahoo Finance doesn't have direct access to European bond yields
            # In production, you'd use a financial data API or manual input
            
            # Default values (should be updated with actual data)
            macro_data = {
                'risk_free_rate': 0.025,  # 2.5% - should be updated with actual 10Y Dutch/German bond
                'equity_risk_premium': config.DEFAULT_ASSUMPTIONS['equity_risk_premium'],
                'inflation_rate': 0.02,  # 2% - should be updated with actual data
                'long_term_gdp_growth': 0.025,  # 2.5% - long-term GDP growth
            }
            
            print("    Note: Using default macro assumptions. Update with actual data sources.")
            return macro_data
        except Exception as e:
            print(f"  Warning: Error collecting macro data: {e}")
            return {
                'risk_free_rate': 0.025,
                'equity_risk_premium': 0.05,
                'inflation_rate': 0.02,
                'long_term_gdp_growth': 0.025,
            }
    
    def save_raw_data(self):
        """Save collected raw data to JSON files"""
        os.makedirs(config.RAW_DATA_DIR, exist_ok=True)
        
        # Save as JSON (convert DataFrames to dict)
        data_to_save = {}
        for key, value in self.data.items():
            if isinstance(value, pd.DataFrame):
                data_to_save[key] = value.to_dict('records')
            elif isinstance(value, pd.Series):
                data_to_save[key] = value.to_dict()
            else:
                data_to_save[key] = value
        
        filename = os.path.join(config.RAW_DATA_DIR, 
                               f"{self.ticker.replace('.', '_')}_raw_data_{datetime.now().strftime('%Y%m%d')}.json")
        
        with open(filename, 'w') as f:
            json.dump(data_to_save, f, indent=2, default=str)
        
        print(f"  - Raw data saved to {filename}")
    
    def get_financial_statements(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Get standardized financial statements
        
        Returns:
            Tuple of (income_statement, balance_sheet, cash_flow)
        """
        income_stmt = self.data.get('income_statement', pd.DataFrame())
        balance_sheet = self.data.get('balance_sheet', pd.DataFrame())
        cash_flow = self.data.get('cash_flow', pd.DataFrame())
        
        return income_stmt, balance_sheet, cash_flow


if __name__ == "__main__":
    collector = DataCollector()
    data = collector.collect_all_data()
    print("\nData collection summary:")
    print(f"  - Income statement: {len(data.get('income_statement', []))} periods")
    print(f"  - Balance sheet: {len(data.get('balance_sheet', []))} periods")
    print(f"  - Cash flow: {len(data.get('cash_flow', []))} periods")

