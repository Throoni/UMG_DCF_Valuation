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
from typing import Dict, Optional, List, Tuple, List

# Add parent directory to path for config import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from src.ir_scraper import IRScraper
from src.pdf_extractor import PDFExtractor
from src.excel_data_reader import ExcelDataReader


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
        
        # Check for corrected data in output Excel file first (highest priority)
        excel_data = {}
        print("  - Checking for corrected data in output Excel file...")
        excel_reader = ExcelDataReader()
        excel_data = excel_reader.read_historical_financials()
        
        # Use Excel data if available and valid
        has_income = not excel_data.get('income_statement', pd.DataFrame()).empty
        has_balance = not excel_data.get('balance_sheet', pd.DataFrame()).empty
        has_cash = not excel_data.get('cash_flow', pd.DataFrame()).empty
        
        if excel_data and (has_income or has_balance):
            print("    ✓ Using corrected historical data from Excel file")
            if has_income:
                self.data['income_statement'] = excel_data.get('income_statement', pd.DataFrame())
            if has_balance:
                self.data['balance_sheet'] = excel_data.get('balance_sheet', pd.DataFrame())
            if has_cash:
                self.data['cash_flow'] = excel_data.get('cash_flow', pd.DataFrame())
        else:
            print("    No corrected data found in Excel file, collecting from sources...")
            excel_data = {}
        
        # Only collect from IR/Yahoo Finance if Excel data not available
        if not excel_data or (excel_data.get('income_statement', pd.DataFrame()).empty and 
                             excel_data.get('balance_sheet', pd.DataFrame()).empty):
            # Try to collect from IR documents first (more reliable)
            print("  - Attempting to fetch data from IR documents...")
            ir_data = self.collect_ir_documents()
            
            # Collect from Yahoo Finance (primary or fallback)
            print("  - Fetching data from Yahoo Finance...")
            yahoo_data = self.collect_yahoo_finance_data()
            
            # Merge data: IR takes priority, Yahoo Finance as fallback
            # Validate IR data has required columns before using it
            ir_data_valid = False
            if ir_data and not ir_data.get('income_statement', pd.DataFrame()).empty:
                income_stmt = ir_data['income_statement']
                # Check if IR data has at least one of the critical columns we need
                required_cols = ['Revenue', 'Total Revenue', 'Revenues', 'Net Income', 'EBIT', 'EBITDA']
                has_required = any(col in income_stmt.columns for col in required_cols)
                
                # Also check if we have at least one row with a Date
                has_date = 'Date' in income_stmt.columns and not income_stmt['Date'].isna().all()
                
                ir_data_valid = has_required and has_date
            
            if ir_data_valid:
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
                print("    Using Yahoo Finance data (IR extraction incomplete or unavailable)")
                self.data.update(yahoo_data)
        else:
            # Excel data is being used, still collect market/peer/macro data
            print("  - Collecting market data (corrected historical data already loaded from Excel)...")
            yahoo_data = self.collect_yahoo_finance_data()
            # Add market data from Yahoo Finance (shares outstanding, beta, etc.)
            if yahoo_data:
                self.data['stock_info'] = yahoo_data.get('stock_info', {})
                self.data['current_price'] = yahoo_data.get('current_price', None)
                self.data['market_cap'] = yahoo_data.get('market_cap', None)
                self.data['beta'] = yahoo_data.get('beta', None)
                self.data['shares_outstanding'] = yahoo_data.get('shares_outstanding', None)
        
        # Collect market data (always needed for WACC, etc.)
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
        
        # Validate data quality
        validation_warnings = self._validate_data_quality()
        if validation_warnings:
            print("  Data quality warnings:")
            for warning in validation_warnings:
                print(f"    - {warning}")
        
        # Save raw data
        self.save_raw_data()
        
        print("Data collection complete!")
        return self.data
    
    def _validate_data_quality(self) -> List[str]:
        """
        Validate data quality and return list of warnings
        
        Returns:
            List of warning messages
        """
        warnings = []
        
        # Check if we have minimum required data
        if self.data.get('income_statement', pd.DataFrame()).empty:
            warnings.append("Income statement is empty")
        if self.data.get('balance_sheet', pd.DataFrame()).empty:
            warnings.append("Balance sheet is empty")
        if self.data.get('cash_flow', pd.DataFrame()).empty:
            warnings.append("Cash flow statement is empty")
        
        # Check for critical line items
        income_stmt = self.data.get('income_statement', pd.DataFrame())
        if not income_stmt.empty:
            required_items = ['Revenue', 'Net Income']
            missing = [item for item in required_items if item not in income_stmt.columns]
            if missing:
                warnings.append(f"Income statement missing: {', '.join(missing)}")
        
        balance_sheet = self.data.get('balance_sheet', pd.DataFrame())
        if not balance_sheet.empty:
            required_items = ['Total Assets', 'Total Equity']
            missing = [item for item in required_items if item not in balance_sheet.columns]
            if missing:
                warnings.append(f"Balance sheet missing: {', '.join(missing)}")
        
        # Check for market data
        if not self.data.get('shares_outstanding'):
            warnings.append("Shares outstanding not available - valuation ratios may be incomplete")
        if not self.data.get('beta'):
            warnings.append("Beta not available - WACC calculation may use default value")
        
        return warnings
    
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
        # First, try exact matches - but avoid duplicates
        # Process in priority order: prefer exact matches over alternatives
        for yahoo_name, standard_name in mapping.items():
            if yahoo_name in df.index:
                # Only add if we don't already have this standard name
                # This prevents "Normalized EBITDA" from overwriting "EBITDA"
                # and ensures we get the best match first
                if standard_name not in standardized.columns:
                    standardized[standard_name] = df.loc[yahoo_name].values
            elif yahoo_name in df_transposed.columns:
                if standard_name not in standardized.columns:
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
            # Prefer actual EBITDA over Normalized EBITDA
            ebitda_candidates = [item for item in df.index if 'ebitda' in item.lower() and 'normalized' not in item.lower()]
            if not ebitda_candidates:
                # Fallback to normalized if actual not available
                ebitda_candidates = [item for item in df.index if 'ebitda' in item.lower()]
            if ebitda_candidates:
                standardized['EBITDA'] = df.loc[ebitda_candidates[0]].values
                print(f"    Found EBITDA as: {ebitda_candidates[0]}")
        
        if 'Net Income' not in standardized.columns and not df.empty:
            # Prefer the most standard "Net Income" line item
            # Priority: 1) Exact "Net Income", 2) "Net Income Common Stockholders", 3) Others without "continuing"
            ni_priority = [
                item for item in df.index 
                if item.lower() == 'net income'
            ]
            if not ni_priority:
                ni_priority = [
                    item for item in df.index 
                    if 'net income' in item.lower() and 'common stockholders' in item.lower()
                ]
            if not ni_priority:
                ni_priority = [
                    item for item in df.index 
                    if 'net income' in item.lower() 
                    and 'continuing' not in item.lower()
                    and 'discontinued' not in item.lower()
                    and 'noncontrolling' not in item.lower()
                ]
            if ni_priority:
                standardized['Net Income'] = df.loc[ni_priority[0]].values
                print(f"    Found Net Income as: {ni_priority[0]}")
        
        # For balance sheet, try to find missing key items
        if statement_type == 'balance':
            # Try to find Total Equity if not mapped
            if 'Total Equity' not in standardized.columns and not df.empty:
                equity_candidates = [
                    item for item in df.index 
                    if ('stockholder' in item.lower() or 'equity' in item.lower())
                    and 'total' in item.lower()
                    and 'minority' not in item.lower()
                ]
                if not equity_candidates:
                    equity_candidates = [
                        item for item in df.index 
                        if 'stockholder' in item.lower() or ('equity' in item.lower() and 'common' in item.lower())
                    ]
                if equity_candidates:
                    standardized['Total Equity'] = df.loc[equity_candidates[0]].values
                    print(f"    Found Total Equity as: {equity_candidates[0]}")
            
            # Try to find Current Assets if not mapped
            if 'Current Assets' not in standardized.columns and not df.empty:
                ca_candidates = [item for item in df.index if 'current asset' in item.lower() and 'total' in item.lower()]
                if ca_candidates:
                    standardized['Current Assets'] = df.loc[ca_candidates[0]].values
                    print(f"    Found Current Assets as: {ca_candidates[0]}")
            
            # Try to find Current Liabilities if not mapped
            if 'Current Liabilities' not in standardized.columns and not df.empty:
                cl_candidates = [item for item in df.index if 'current liab' in item.lower() and 'total' in item.lower()]
                if cl_candidates:
                    standardized['Current Liabilities'] = df.loc[cl_candidates[0]].values
                    print(f"    Found Current Liabilities as: {cl_candidates[0]}")
        
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
                'EBITDA': 'EBITDA',  # Prefer actual EBITDA over normalized
                # Note: 'Normalized EBITDA' is intentionally NOT mapped to avoid confusion
                'Interest Expense': 'Interest Expense',
                'Interest Expense Non Operating': 'Interest Expense',  # Alternative
                'Net Interest Income': 'Interest Expense',  # Alternative (negative)
                'Income Before Tax': 'Income Before Tax',
                'Income Tax Expense': 'Income Tax Expense',
                'Net Income': 'Net Income',  # Prefer exact match
                'Net Income Common Stockholders': 'Net Income',  # Alternative (good fallback)
                # Note: Excluding "Net Income From Continuing Operation Net Minority Interest" 
                # and similar variants to avoid confusion - use fallback logic instead
            }
        elif statement_type == 'balance':
            return {
                'Total Current Assets': 'Current Assets',
                'Current Assets': 'Current Assets',  # Direct match
                'Total Assets': 'Total Assets',
                'Total Current Liabilities': 'Current Liabilities',
                'Current Liabilities': 'Current Liabilities',  # Direct match
                'Total Debt': 'Total Debt',
                'Total Liabilities': 'Total Liabilities',
                'Total Liabilities Net Minority Interest': 'Total Liabilities',  # Alternative
                'Total Stockholder Equity': 'Total Equity',
                'Stockholders Equity': 'Total Equity',  # Alternative
                'Total Equity Gross Minority Interest': 'Total Equity',  # Alternative
                'Common Stock Equity': 'Total Equity',  # Alternative
                'Cash And Cash Equivalents': 'Cash and Cash Equivalents',
            }
        elif statement_type == 'cashflow':
            return {
                'Operating Cash Flow': 'Operating Cash Flow',
                'Total Cash From Operating Activities': 'Operating Cash Flow',
                'Cash From Operating Activities': 'Operating Cash Flow',
                'Capital Expenditure': 'Capital Expenditures',
                'Capital Expenditures': 'Capital Expenditures',
                'Investing Cash Flow': 'Investing Cash Flow',
                'Total Cashflows From Investing Activities': 'Investing Cash Flow',
                'Cash From Investing Activities': 'Investing Cash Flow',
                'Financing Cash Flow': 'Financing Cash Flow',
                'Total Cash From Financing Activities': 'Financing Cash Flow',
                'Cash From Financing Activities': 'Financing Cash Flow',
                'Free Cash Flow': 'Free Cash Flow',
                'Changes In Cash': 'Net Change in Cash',
                'Net Change In Cash': 'Net Change in Cash',
                'End Cash Position': 'Ending Cash',
                'Beginning Cash Position': 'Beginning Cash',
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
                    try:
                        extracted = extractor.extract_all_statements(filepath, year)
                        
                        if 'income_statement' in extracted and extracted['income_statement'] is not None:
                            df = extracted['income_statement']
                            if not df.empty:
                                # Ensure Date column exists and is datetime
                                if 'Date' not in df.columns:
                                    df['Date'] = pd.Timestamp(year=year, month=12, day=31)
                                df['Date'] = pd.to_datetime(df['Date'])
                                income_statements.append(df)
                        
                        if 'balance_sheet' in extracted and extracted['balance_sheet'] is not None:
                            df = extracted['balance_sheet']
                            if not df.empty:
                                if 'Date' not in df.columns:
                                    df['Date'] = pd.Timestamp(year=year, month=12, day=31)
                                df['Date'] = pd.to_datetime(df['Date'])
                                balance_sheets.append(df)
                        
                        if 'cash_flow' in extracted and extracted['cash_flow'] is not None:
                            df = extracted['cash_flow']
                            if not df.empty:
                                if 'Date' not in df.columns:
                                    df['Date'] = pd.Timestamp(year=year, month=12, day=31)
                                df['Date'] = pd.to_datetime(df['Date'])
                                cash_flows.append(df)
                    except Exception as e:
                        print(f"      Error extracting from {os.path.basename(filepath)}: {e}")
                        continue
                
                # Combine multiple years into single DataFrames
                # Use a more robust approach: ensure unique column names before concatenating
                if income_statements:
                    try:
                        # Clean each DataFrame: ensure unique column names and Date column
                        cleaned_statements = []
                        for df in income_statements:
                            if df.empty:
                                continue
                            df = df.copy()
                            df = df.reset_index(drop=True)
                            
                            # Ensure Date column exists
                            if 'Date' not in df.columns:
                                continue
                            
                            # Make column names unique
                            cols = df.columns.tolist()
                            seen = {}
                            new_cols = []
                            for col in cols:
                                if col in seen:
                                    seen[col] += 1
                                    new_cols.append(f"{col}_{seen[col]}")
                                else:
                                    seen[col] = 0
                                    new_cols.append(col)
                            df.columns = new_cols
                            
                            cleaned_statements.append(df)
                        
                        if cleaned_statements:
                            # Try to align columns - take union of all columns
                            all_cols = set()
                            for df in cleaned_statements:
                                all_cols.update(df.columns)
                            
                            # Reindex each DataFrame to have all columns
                            aligned_statements = []
                            for df in cleaned_statements:
                                df_aligned = df.reindex(columns=list(all_cols))
                                aligned_statements.append(df_aligned)
                            
                            combined_income = pd.concat(aligned_statements, ignore_index=True, sort=False)
                            # Remove duplicate Date rows if any
                            if 'Date' in combined_income.columns:
                                combined_income = combined_income.drop_duplicates(subset=['Date'], keep='last')
                            ir_data['income_statement'] = combined_income
                    except Exception as e:
                        print(f"      Error combining income statements: {e}")
                        import traceback
                        traceback.print_exc()
                        # Use the first one if combination fails
                        if income_statements:
                            ir_data['income_statement'] = income_statements[0].copy()
                
                if balance_sheets:
                    try:
                        cleaned_sheets = []
                        for df in balance_sheets:
                            if df.empty:
                                continue
                            df = df.copy().reset_index(drop=True)
                            if 'Date' in df.columns:
                                cleaned_sheets.append(df)
                        
                        if cleaned_sheets:
                            all_cols = set()
                            for df in cleaned_sheets:
                                all_cols.update(df.columns)
                            
                            aligned_sheets = []
                            for df in cleaned_sheets:
                                df_aligned = df.reindex(columns=list(all_cols))
                                aligned_sheets.append(df_aligned)
                            
                            combined_balance = pd.concat(aligned_sheets, ignore_index=True, sort=False)
                            if 'Date' in combined_balance.columns:
                                combined_balance = combined_balance.drop_duplicates(subset=['Date'], keep='last')
                            ir_data['balance_sheet'] = combined_balance
                    except Exception as e:
                        print(f"      Error combining balance sheets: {e}")
                        if balance_sheets:
                            ir_data['balance_sheet'] = balance_sheets[0].copy()
                
                if cash_flows:
                    try:
                        cleaned_flows = []
                        for df in cash_flows:
                            if df.empty:
                                continue
                            df = df.copy().reset_index(drop=True)
                            if 'Date' in df.columns:
                                cleaned_flows.append(df)
                        
                        if cleaned_flows:
                            all_cols = set()
                            for df in cleaned_flows:
                                all_cols.update(df.columns)
                            
                            aligned_flows = []
                            for df in cleaned_flows:
                                df_aligned = df.reindex(columns=list(all_cols))
                                aligned_flows.append(df_aligned)
                            
                            combined_cash = pd.concat(aligned_flows, ignore_index=True, sort=False)
                            if 'Date' in combined_cash.columns:
                                combined_cash = combined_cash.drop_duplicates(subset=['Date'], keep='last')
                            ir_data['cash_flow'] = combined_cash
                    except Exception as e:
                        print(f"      Error combining cash flows: {e}")
                        if cash_flows:
                            ir_data['cash_flow'] = cash_flows[0].copy()
                
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

