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
import re
from datetime import datetime
from typing import Dict, Optional, Tuple, List

# Add parent directory to path for config import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from src.ir_scraper import IRScraper
from src.pdf_extractor import PDFExtractor


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
        
        # Try to collect from IR documents first (more reliable)
        print("  - Attempting to fetch data from IR documents...")
        ir_data = self.collect_ir_documents()
        
        # Collect from Yahoo Finance (primary or fallback)
        print("  - Fetching data from Yahoo Finance...")
        yahoo_data = self.collect_yahoo_finance_data()
        
        # Merge data: IR takes priority, Yahoo Finance as fallback
        if ir_data and not ir_data.get('income_statement', pd.DataFrame()).empty:
            print("    Using IR document data as primary source")
            self.data.update(ir_data)
            # Fill in any missing data from Yahoo Finance
            for key, value in yahoo_data.items():
                if key not in self.data or (isinstance(value, pd.DataFrame) and not value.empty):
                    if isinstance(self.data.get(key), pd.DataFrame) and self.data[key].empty:
                        self.data[key] = value
                    elif key not in self.data:
                        self.data[key] = value
        else:
            print("    Using Yahoo Finance data (IR extraction unavailable)")
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
        
        Yahoo Finance structure: dates as columns, line items as index
        We need: dates as rows, line items as columns
        
        Args:
            df: Raw financial statement DataFrame (dates as columns, line items as index)
            statement_type: Type of statement ('income', 'balance', 'cashflow')
            
        Returns:
            Standardized DataFrame with dates as rows and line items as columns
        """
        if df.empty:
            return pd.DataFrame()
        
        # Yahoo Finance: dates are columns, line items are in index
        # Transpose to get dates as rows
        df_transposed = df.T.copy()
        
        # Convert date index to column
        df_transposed.reset_index(inplace=True)
        df_transposed.rename(columns={'index': 'Date'}, inplace=True)
        
        # Map Yahoo Finance line items to standard names
        mapping = self._get_line_item_mapping(statement_type)
        
        # Create standardized DataFrame starting with Date column
        standardized = pd.DataFrame()
        standardized['Date'] = df_transposed['Date']
        
        # Map line items from original index to standard names
        # First, try exact matches
        for yahoo_name, standard_name in mapping.items():
            if yahoo_name in df.index:
                # Get the values for this line item across all dates
                standardized[standard_name] = df.loc[yahoo_name].values
            elif yahoo_name in df_transposed.columns:
                standardized[standard_name] = df_transposed[yahoo_name].values
        
        # If we didn't get Revenue, try to find it with partial matching
        if 'Revenue' not in standardized.columns and not df.empty:
            # Try to find revenue by searching index
            revenue_candidates = [item for item in df.index if 'revenue' in item.lower() or 'revenues' in item.lower()]
            if revenue_candidates:
                standardized['Revenue'] = df.loc[revenue_candidates[0]].values
                print(f"    Found revenue as: {revenue_candidates[0]}")
        
        # Try to find other key items with partial matching if not found
        if 'EBITDA' not in standardized.columns and not df.empty:
            ebitda_candidates = [item for item in df.index if 'ebitda' in item.lower()]
            if ebitda_candidates:
                standardized['EBITDA'] = df.loc[ebitda_candidates[0]].values
                print(f"    Found EBITDA as: {ebitda_candidates[0]}")
        
        if 'Net Income' not in standardized.columns and not df.empty:
            ni_candidates = [item for item in df.index if 'net income' in item.lower() and 'continuing' not in item.lower()]
            if ni_candidates:
                standardized['Net Income'] = df.loc[ni_candidates[0]].values
                print(f"    Found Net Income as: {ni_candidates[0]}")
        
        # Sort by date (most recent first)
        if not standardized.empty and 'Date' in standardized.columns:
            standardized = standardized.sort_values('Date', ascending=False).reset_index(drop=True)
        
        return standardized
    
    def _get_line_item_mapping(self, statement_type: str) -> Dict[str, str]:
        """Get mapping from Yahoo Finance line items to standard names"""
        if statement_type == 'income':
            return {
                'Total Revenue': 'Revenue',
                'Operating Revenue': 'Revenue',  # Alternative name
                'Revenues': 'Revenue',  # Alternative name
                'Revenue': 'Revenue',  # Direct match
                'Cost Of Revenue': 'Cost of Revenue',
                'Cost Of Goods And Services Sold': 'Cost of Revenue',  # Alternative
                'Reconciled Cost Of Revenue': 'Cost of Revenue',  # Alternative
                'Gross Profit': 'Gross Profit',
                'Operating Income': 'Operating Income',
                'Total Operating Income As Reported': 'Operating Income',  # Alternative
                'EBIT': 'EBIT',
                'EBITDA': 'EBITDA',
                'Normalized EBITDA': 'EBITDA',  # Alternative
                'Interest Expense': 'Interest Expense',
                'Interest Expense Non Operating': 'Interest Expense',  # Alternative
                'Net Interest Income': 'Interest Expense',  # Alternative (negative)
                'Income Before Tax': 'Income Before Tax',
                'Income Tax Expense': 'Income Tax Expense',
                'Net Income': 'Net Income',
                'Net Income Common Stockholders': 'Net Income',  # Alternative
                'Net Income From Continuing Operation Net Minority Interest': 'Net Income',  # Alternative
                'Net Income From Continuing And Discontinued Operation': 'Net Income',  # Alternative
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
    
    def collect_ir_documents(self) -> Dict:
        """
        Collect financial data from IR documents (annual/quarterly reports)
        
        Returns:
            Dictionary with financial statements from IR documents
        """
        ir_data = {
            'income_statement': pd.DataFrame(),
            'balance_sheet': pd.DataFrame(),
            'cash_flow': pd.DataFrame(),
        }
        
        try:
            # Initialize scraper and extractor
            scraper = IRScraper()
            extractor = PDFExtractor()
            
            # Find and download annual reports
            print("    Searching for annual reports...")
            annual_reports = scraper.find_annual_reports()
            
            if not annual_reports:
                print("    No annual reports found via web scraping")
                # Try to use already downloaded PDFs
                annual_reports = self._find_downloaded_pdfs('annual')
            
            if annual_reports:
                print(f"    Found {len(annual_reports)} annual report(s)")
                
                # Download reports if needed
                downloaded_files = []
                for report in annual_reports[:config.IR_YEARS_TO_DOWNLOAD]:
                    filepath = scraper.download_report(report)
                    if filepath:
                        downloaded_files.append((filepath, report['year']))
                
                # If no new downloads, check existing files
                if not downloaded_files:
                    downloaded_files = self._find_downloaded_pdfs_with_years('annual')
                
                # Extract data from each PDF
                income_statements = []
                balance_sheets = []
                cash_flows = []
                
                for filepath, year in downloaded_files:
                    print(f"    Extracting data from {os.path.basename(filepath)}...")
                    extracted = extractor.extract_all_statements(filepath, year)
                    
                    if 'income_statement' in extracted:
                        income_statements.append(extracted['income_statement'])
                    if 'balance_sheet' in extracted:
                        balance_sheets.append(extracted['balance_sheet'])
                    if 'cash_flow' in extracted:
                        cash_flows.append(extracted['cash_flow'])
                
                # Combine multiple years into single DataFrames
                if income_statements:
                    ir_data['income_statement'] = pd.concat(income_statements, ignore_index=True)
                if balance_sheets:
                    ir_data['balance_sheet'] = pd.concat(balance_sheets, ignore_index=True)
                if cash_flows:
                    ir_data['cash_flow'] = pd.concat(cash_flows, ignore_index=True)
                
                # Standardize format to match Yahoo Finance structure
                ir_data = self._standardize_ir_data(ir_data)
            else:
                print("    No annual reports available")
        
        except Exception as e:
            print(f"    Warning: Error collecting IR documents: {e}")
            print(f"    Falling back to Yahoo Finance data")
        
        return ir_data
    
    def _find_downloaded_pdfs(self, report_type: str) -> List[Dict]:
        """Find already downloaded PDF files"""
        if report_type == 'annual':
            pdf_dir = config.IR_ANNUAL_DIR
        else:
            pdf_dir = config.IR_QUARTERLY_DIR
        
        if not os.path.exists(pdf_dir):
            return []
        
        reports = []
        for filename in os.listdir(pdf_dir):
            if filename.lower().endswith('.pdf'):
                # Extract year from filename
                year_match = re.search(r'(\d{4})', filename)
                if year_match:
                    year = int(year_match.group(1))
                    reports.append({
                        'url': '',
                        'year': year,
                        'type': report_type,
                        'title': filename,
                        'filename': filename
                    })
        
        return reports
    
    def _find_downloaded_pdfs_with_years(self, report_type: str) -> List[Tuple[str, int]]:
        """Find downloaded PDFs and extract years"""
        if report_type == 'annual':
            pdf_dir = config.IR_ANNUAL_DIR
        else:
            pdf_dir = config.IR_QUARTERLY_DIR
        
        if not os.path.exists(pdf_dir):
            return []
        
        files = []
        for filename in os.listdir(pdf_dir):
            if filename.lower().endswith('.pdf'):
                filepath = os.path.join(pdf_dir, filename)
                # Extract year from filename
                year_match = re.search(r'(\d{4})', filename)
                if year_match:
                    year = int(year_match.group(1))
                    files.append((filepath, year))
        
        return files
    
    def _standardize_ir_data(self, ir_data: Dict) -> Dict:
        """
        Standardize IR extracted data to match Yahoo Finance format
        (dates as rows, line items as columns)
        """
        standardized = {}
        
        for statement_type, df in ir_data.items():
            if df.empty:
                standardized[statement_type] = df
                continue
            
            # IR data should already have Date column
            # Ensure it's in the right format
            if 'Date' in df.columns:
                # Convert to datetime if needed
                df['Date'] = pd.to_datetime(df['Date'])
                standardized[statement_type] = df
            elif 'Year' in df.columns:
                # Convert Year to Date
                df['Date'] = pd.to_datetime(df['Year'].astype(str) + '-12-31')
                df = df.drop('Year', axis=1)
                standardized[statement_type] = df
            else:
                standardized[statement_type] = df
        
        return standardized
    
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

