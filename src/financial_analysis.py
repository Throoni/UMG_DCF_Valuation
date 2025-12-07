"""
Financial statement analysis and normalization module
Calculates ratios, normalizes financials, and prepares data for DCF modeling
"""

import pandas as pd
import numpy as np
import os
import sys
from typing import Dict, Tuple, Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from utils.data_validation import validate_financial_data, validate_accounting_identity


class FinancialAnalyzer:
    """Analyzes and normalizes financial statements"""
    
    def __init__(self, income_stmt: pd.DataFrame, balance_sheet: pd.DataFrame, 
                 cash_flow: pd.DataFrame):
        """
        Initialize financial analyzer
        
        Args:
            income_stmt: Income statement DataFrame
            balance_sheet: Balance sheet DataFrame
            cash_flow: Cash flow statement DataFrame
        """
        self.income_stmt = income_stmt.copy()
        self.balance_sheet = balance_sheet.copy()
        self.cash_flow = cash_flow.copy()
        self.normalized_income_stmt = None
        self.normalized_balance_sheet = None
        self.normalized_cash_flow = None
        self.ratios = {}
        
    def normalize_financials(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Normalize financial statements by removing one-time items and adjusting
        for non-operating activities
        
        Returns:
            Tuple of (normalized_income_stmt, normalized_balance_sheet, normalized_cash_flow)
        """
        print("Normalizing financial statements...")
        
        # Normalize income statement
        self.normalized_income_stmt = self._normalize_income_statement()
        
        # Normalize balance sheet
        self.normalized_balance_sheet = self._normalize_balance_sheet()
        
        # Normalize cash flow
        self.normalized_cash_flow = self._normalize_cash_flow()
        
        return (self.normalized_income_stmt, 
                self.normalized_balance_sheet, 
                self.normalized_cash_flow)
    
    def _normalize_income_statement(self) -> pd.DataFrame:
        """Normalize income statement"""
        if self.income_stmt.empty:
            return pd.DataFrame()
        
        df = self.income_stmt.copy()
        
        # Preserve Date column if it exists
        date_col = None
        if 'Date' in df.columns:
            date_col = df['Date']
        
        # Calculate missing line items if needed
        if 'Gross Profit' not in df.columns and 'Revenue' in df.columns and 'Cost of Revenue' in df.columns:
            df['Gross Profit'] = df['Revenue'] - df['Cost of Revenue']
        
        if 'EBIT' not in df.columns and 'Operating Income' in df.columns:
            df['EBIT'] = df['Operating Income']
        elif 'Operating Income' not in df.columns and 'EBIT' in df.columns:
            df['Operating Income'] = df['EBIT']
        
        # Calculate EBITDA if not present
        if 'EBITDA' not in df.columns:
            if 'EBIT' in df.columns and 'Depreciation' in df.columns:
                df['EBITDA'] = df['EBIT'] + df['Depreciation']
            elif 'Operating Income' in df.columns:
                # Use operating income as proxy if depreciation not available
                df['EBITDA'] = df['Operating Income']
        
        # Ensure Date column is preserved
        if date_col is not None and 'Date' not in df.columns:
            df.insert(0, 'Date', date_col)
        
        return df
    
    def _normalize_balance_sheet(self) -> pd.DataFrame:
        """Normalize balance sheet"""
        if self.balance_sheet.empty:
            return pd.DataFrame()
        
        df = self.balance_sheet.copy()
        
        # Preserve Date column if it exists
        date_col = None
        if 'Date' in df.columns:
            date_col = df['Date']
        
        # Calculate working capital
        if 'Current Assets' in df.columns and 'Current Liabilities' in df.columns:
            df['Working Capital'] = df['Current Assets'] - df['Current Liabilities']
        
        # Calculate net debt
        if 'Total Debt' in df.columns and 'Cash and Cash Equivalents' in df.columns:
            df['Net Debt'] = df['Total Debt'] - df['Cash and Cash Equivalents']
        
        # Validate accounting identity
        if 'Total Assets' in df.columns and 'Total Liabilities' in df.columns and 'Total Equity' in df.columns:
            is_valid, errors = validate_accounting_identity(df)
            if not is_valid:
                print(f"  Warning: Accounting identity issues found: {errors}")
        
        # Ensure Date column is preserved
        if date_col is not None and 'Date' not in df.columns:
            df.insert(0, 'Date', date_col)
        
        return df
    
    def _normalize_cash_flow(self) -> pd.DataFrame:
        """Normalize cash flow statement"""
        if self.cash_flow.empty:
            return pd.DataFrame()
        
        df = self.cash_flow.copy()
        
        # Preserve Date column if it exists
        date_col = None
        if 'Date' in df.columns:
            date_col = df['Date']
        
        # Calculate free cash flow
        if 'Operating Cash Flow' in df.columns and 'Capital Expenditures' in df.columns:
            df['Free Cash Flow'] = df['Operating Cash Flow'] + df['Capital Expenditures']
            # Note: CapEx is typically negative, so we add it
        
        # Ensure Date column is preserved
        if date_col is not None and 'Date' not in df.columns:
            df.insert(0, 'Date', date_col)
        
        return df
    
    def calculate_ratios(self) -> Dict:
        """
        Calculate financial ratios and metrics
        
        Returns:
            Dictionary of calculated ratios
        """
        print("Calculating financial ratios...")
        
        ratios = {}
        
        # Income statement ratios
        if not self.normalized_income_stmt.empty:
            ratios.update(self._calculate_income_ratios())
        
        # Balance sheet ratios
        if not self.normalized_balance_sheet.empty:
            ratios.update(self._calculate_balance_ratios())
        
        # Cash flow ratios
        if not self.normalized_cash_flow.empty:
            ratios.update(self._calculate_cash_flow_ratios())
        
        # Combined ratios
        ratios.update(self._calculate_combined_ratios())
        
        self.ratios = ratios
        return ratios
    
    def _calculate_income_ratios(self) -> Dict:
        """Calculate income statement ratios"""
        ratios = {}
        df = self.normalized_income_stmt
        
        if 'Revenue' in df.columns:
            revenue = df['Revenue']
            
            # Growth rates
            if len(revenue) > 1:
                ratios['revenue_growth_yoy'] = revenue.pct_change(fill_method=None).dropna().tolist()
                ratios['revenue_cagr'] = self._calculate_cagr(revenue.iloc[0], revenue.iloc[-1], len(revenue))
            
            # Margins
            if 'Gross Profit' in df.columns:
                ratios['gross_margin'] = (df['Gross Profit'] / revenue).tolist()
            
            if 'EBIT' in df.columns:
                ratios['ebit_margin'] = (df['EBIT'] / revenue).tolist()
            
            if 'EBITDA' in df.columns:
                ratios['ebitda_margin'] = (df['EBITDA'] / revenue).tolist()
            
            if 'Net Income' in df.columns:
                ratios['net_margin'] = (df['Net Income'] / revenue).tolist()
                ratios['net_income_growth_yoy'] = df['Net Income'].pct_change(fill_method=None).dropna().tolist()
        
        # Tax rate
        if 'Income Before Tax' in df.columns and 'Income Tax Expense' in df.columns:
            ratios['effective_tax_rate'] = (
                df['Income Tax Expense'] / df['Income Before Tax']
            ).tolist()
        
        return ratios
    
    def _calculate_balance_ratios(self) -> Dict:
        """Calculate balance sheet ratios"""
        ratios = {}
        df = self.normalized_balance_sheet
        
        if 'Current Assets' in df.columns and 'Current Liabilities' in df.columns:
            ratios['current_ratio'] = (
                df['Current Assets'] / df['Current Liabilities']
            ).tolist()
        
        if 'Total Debt' in df.columns and 'Total Equity' in df.columns:
            ratios['debt_to_equity'] = (
                df['Total Debt'] / df['Total Equity']
            ).tolist()
        
        if 'Total Debt' in df.columns and 'Total Assets' in df.columns:
            ratios['debt_to_assets'] = (
                df['Total Debt'] / df['Total Assets']
            ).tolist()
        
        return ratios
    
    def _calculate_cash_flow_ratios(self) -> Dict:
        """Calculate cash flow ratios"""
        ratios = {}
        df = self.normalized_cash_flow
        
        if 'Operating Cash Flow' in df.columns:
            ocf = df['Operating Cash Flow']
            ratios['operating_cash_flow_growth'] = ocf.pct_change(fill_method=None).dropna().tolist()
        
        if 'Free Cash Flow' in df.columns:
            fcf = df['Free Cash Flow']
            ratios['free_cash_flow_growth'] = fcf.pct_change(fill_method=None).dropna().tolist()
        
        return ratios
    
    def _calculate_combined_ratios(self) -> Dict:
        """Calculate ratios that combine multiple statements"""
        ratios = {}
        
        # Working capital as % of revenue
        if (not self.normalized_balance_sheet.empty and 
            not self.normalized_income_stmt.empty):
            
            if ('Working Capital' in self.normalized_balance_sheet.columns and 
                'Revenue' in self.normalized_income_stmt.columns):
                
                # Align by date/index if possible
                wc = self.normalized_balance_sheet['Working Capital']
                revenue = self.normalized_income_stmt['Revenue']
                
                if len(wc) == len(revenue):
                    ratios['working_capital_pct_revenue'] = (
                        wc / revenue
                    ).tolist()
        
        # CapEx as % of revenue
        if (not self.normalized_cash_flow.empty and 
            not self.normalized_income_stmt.empty):
            
            if ('Capital Expenditures' in self.normalized_cash_flow.columns and 
                'Revenue' in self.normalized_income_stmt.columns):
                
                capex = self.normalized_cash_flow['Capital Expenditures'].abs()
                revenue = self.normalized_income_stmt['Revenue']
                
                if len(capex) == len(revenue):
                    ratios['capex_pct_revenue'] = (
                        capex / revenue
                    ).tolist()
        
        # Debt to EBITDA
        if (not self.normalized_balance_sheet.empty and 
            not self.normalized_income_stmt.empty):
            
            if ('Total Debt' in self.normalized_balance_sheet.columns and 
                'EBITDA' in self.normalized_income_stmt.columns):
                
                debt = self.normalized_balance_sheet['Total Debt']
                ebitda = self.normalized_income_stmt['EBITDA']
                
                if len(debt) == len(ebitda):
                    ratios['debt_to_ebitda'] = (
                        debt / ebitda
                    ).tolist()
        
        return ratios
    
    def _calculate_cagr(self, start_value: float, end_value: float, 
                       periods: int) -> float:
        """Calculate Compound Annual Growth Rate"""
        if start_value <= 0 or periods <= 0:
            return 0.0
        return (end_value / start_value) ** (1 / periods) - 1
    
    def get_working_capital_assumptions(self) -> Dict:
        """
        Calculate working capital assumptions for projections
        
        Returns:
            Dictionary with WC assumptions
        """
        if 'working_capital_pct_revenue' in self.ratios:
            wc_pct = self.ratios['working_capital_pct_revenue']
            avg_wc_pct = np.mean([x for x in wc_pct if not np.isnan(x) and np.isfinite(x)])
            
            return {
                'working_capital_pct_revenue': avg_wc_pct,
                'historical_values': wc_pct,
            }
        
        return {'working_capital_pct_revenue': 0.10}  # Default 10%
    
    def get_capex_assumptions(self) -> Dict:
        """
        Calculate CapEx assumptions for projections
        
        Returns:
            Dictionary with CapEx assumptions
        """
        assumptions = {}
        
        if 'capex_pct_revenue' in self.ratios:
            capex_pct = self.ratios['capex_pct_revenue']
            avg_capex_pct = np.mean([x for x in capex_pct if not np.isnan(x) and np.isfinite(x)])
            assumptions['capex_pct_revenue'] = avg_capex_pct
        else:
            assumptions['capex_pct_revenue'] = 0.05  # Default 5%
        
        # Get depreciation for maintenance CapEx calculation
        if 'Depreciation' in self.normalized_income_stmt.columns:
            depreciation = self.normalized_income_stmt['Depreciation']
            assumptions['avg_depreciation'] = depreciation.mean()
        elif 'Depreciation' in self.normalized_cash_flow.columns:
            depreciation = self.normalized_cash_flow['Depreciation']
            assumptions['avg_depreciation'] = depreciation.mean()
        else:
            assumptions['avg_depreciation'] = None
        
        return assumptions
    
    def get_tax_rate(self) -> float:
        """
        Get normalized tax rate for projections
        
        Returns:
            Effective tax rate
        """
        if 'effective_tax_rate' in self.ratios:
            tax_rates = [x for x in self.ratios['effective_tax_rate'] 
                        if not np.isnan(x) and np.isfinite(x) and 0 <= x <= 1]
            if tax_rates:
                return np.mean(tax_rates)
        
        return 0.25  # Default 25% tax rate
    
    def get_historical_margins(self) -> Dict:
        """
        Get historical margin trends
        
        Returns:
            Dictionary with margin data
        """
        margins = {}
        
        if 'gross_margin' in self.ratios:
            margins['gross_margin'] = {
                'historical': self.ratios['gross_margin'],
                'average': np.mean([x for x in self.ratios['gross_margin'] 
                                  if not np.isnan(x) and np.isfinite(x)]),
                'latest': self.ratios['gross_margin'][-1] if self.ratios['gross_margin'] else None,
            }
        
        if 'ebit_margin' in self.ratios:
            margins['ebit_margin'] = {
                'historical': self.ratios['ebit_margin'],
                'average': np.mean([x for x in self.ratios['ebit_margin'] 
                                  if not np.isnan(x) and np.isfinite(x)]),
                'latest': self.ratios['ebit_margin'][-1] if self.ratios['ebit_margin'] else None,
            }
        
        if 'ebitda_margin' in self.ratios:
            margins['ebitda_margin'] = {
                'historical': self.ratios['ebitda_margin'],
                'average': np.mean([x for x in self.ratios['ebitda_margin'] 
                                  if not np.isnan(x) and np.isfinite(x)]),
                'latest': self.ratios['ebitda_margin'][-1] if self.ratios['ebitda_margin'] else None,
            }
        
        return margins

