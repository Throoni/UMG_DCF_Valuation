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
    
    def calculate_all_ratios(self, market_data: Optional[Dict] = None) -> Dict:
        """
        Calculate all financial ratios including valuation ratios
        
        Args:
            market_data: Optional dictionary with market data for valuation ratios
        
        Returns:
            Complete dictionary of all calculated ratios
        """
        # Calculate base ratios
        ratios = self.calculate_ratios()
        
        # Add valuation ratios if market data provided
        if market_data:
            valuation_ratios = self.calculate_valuation_ratios(market_data)
            ratios.update(valuation_ratios)
        
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
        
        # Liquidity Ratios
        if 'Current Assets' in df.columns and 'Current Liabilities' in df.columns:
            ratios['current_ratio'] = (
                df['Current Assets'] / df['Current Liabilities']
            ).tolist()
        
            # Quick Ratio (assuming Cash + Marketable Securities + Receivables)
            if 'Cash and Cash Equivalents' in df.columns:
                quick_assets = df['Cash and Cash Equivalents']
                if 'Accounts Receivable' in df.columns:
                    quick_assets = quick_assets + df['Accounts Receivable']
                ratios['quick_ratio'] = (quick_assets / df['Current Liabilities']).tolist()
            
            # Cash Ratio
            if 'Cash and Cash Equivalents' in df.columns:
                ratios['cash_ratio'] = (
                    df['Cash and Cash Equivalents'] / df['Current Liabilities']
                ).tolist()
        
        # Leverage Ratios
        if 'Total Debt' in df.columns and 'Total Equity' in df.columns:
            ratios['debt_to_equity'] = (
                df['Total Debt'] / df['Total Equity']
            ).tolist()
            
            # Equity Ratio
            if 'Total Assets' in df.columns:
                ratios['equity_ratio'] = (
                    df['Total Equity'] / df['Total Assets']
            ).tolist()
        
        if 'Total Debt' in df.columns and 'Total Assets' in df.columns:
            ratios['debt_to_assets'] = (
                df['Total Debt'] / df['Total Assets']
            ).tolist()
        
        # Working Capital
        if 'Current Assets' in df.columns and 'Current Liabilities' in df.columns:
            ratios['working_capital'] = (
                df['Current Assets'] - df['Current Liabilities']
            ).tolist()
        
        return ratios
    
    def _calculate_cash_flow_ratios(self) -> Dict:
        """Calculate cash flow ratios"""
        ratios = {}
        df = self.normalized_cash_flow
        
        if 'Operating Cash Flow' in df.columns:
            ocf = df['Operating Cash Flow']
            ratios['operating_cash_flow_growth'] = ocf.pct_change(fill_method=None).dropna().tolist()
            
            # Operating Cash Flow to Current Liabilities
            if not self.normalized_balance_sheet.empty:
                if 'Current Liabilities' in self.normalized_balance_sheet.columns:
                    cl = self.normalized_balance_sheet['Current Liabilities']
                    if len(ocf) == len(cl):
                        ratios['ocf_to_current_liabilities'] = (ocf / cl).tolist()
        
        if 'Free Cash Flow' in df.columns:
            fcf = df['Free Cash Flow']
            ratios['free_cash_flow_growth'] = fcf.pct_change(fill_method=None).dropna().tolist()
        
        return ratios
    
    def _calculate_combined_ratios(self) -> Dict:
        """Calculate ratios that combine multiple statements"""
        ratios = {}
        
        income_df = self.normalized_income_stmt
        balance_df = self.normalized_balance_sheet
        cashflow_df = self.normalized_cash_flow
        
        # Working capital as % of revenue
        if (not balance_df.empty and not income_df.empty):
            if ('Current Assets' in balance_df.columns and 
                'Current Liabilities' in balance_df.columns and
                'Revenue' in income_df.columns):
                wc = balance_df['Current Assets'] - balance_df['Current Liabilities']
                revenue = income_df['Revenue']
                if len(wc) == len(revenue):
                    ratios['working_capital_pct_revenue'] = (wc / revenue).tolist()
        
        # CapEx as % of revenue
        if (not cashflow_df.empty and not income_df.empty):
            if ('Capital Expenditures' in cashflow_df.columns and 
                'Revenue' in income_df.columns):
                capex = cashflow_df['Capital Expenditures'].abs()
                revenue = income_df['Revenue']
                if len(capex) == len(revenue):
                    ratios['capex_pct_revenue'] = (capex / revenue).tolist()
        
        # Debt to EBITDA
        if (not balance_df.empty and not income_df.empty):
            if ('Total Debt' in balance_df.columns and 
                'EBITDA' in income_df.columns):
                debt = balance_df['Total Debt']
                ebitda = income_df['EBITDA']
                if len(debt) == len(ebitda):
                    ratios['debt_to_ebitda'] = (debt / ebitda).tolist()
        
        # Return on Equity (ROE)
        if (not balance_df.empty and not income_df.empty):
            if ('Total Equity' in balance_df.columns and 
                'Net Income' in income_df.columns):
                equity = balance_df['Total Equity']
                net_income = income_df['Net Income']
                if len(equity) == len(net_income):
                    # Use average equity for better accuracy
                    equity_avg = equity.rolling(window=2, min_periods=1).mean()
                    ratios['roe'] = (net_income / equity_avg).tolist()
        
        # Return on Assets (ROA)
        if (not balance_df.empty and not income_df.empty):
            if ('Total Assets' in balance_df.columns and 
                'Net Income' in income_df.columns):
                assets = balance_df['Total Assets']
                net_income = income_df['Net Income']
                if len(assets) == len(net_income):
                    assets_avg = assets.rolling(window=2, min_periods=1).mean()
                    ratios['roa'] = (net_income / assets_avg).tolist()
        
        # Return on Invested Capital (ROIC)
        if (not balance_df.empty and not income_df.empty):
            if ('Total Equity' in balance_df.columns and 
                'Total Debt' in balance_df.columns and
                'EBIT' in income_df.columns):
                invested_capital = balance_df['Total Equity'] + balance_df['Total Debt']
                ebit = income_df['EBIT']
                if len(invested_capital) == len(ebit):
                    ic_avg = invested_capital.rolling(window=2, min_periods=1).mean()
                    ratios['roic'] = (ebit / ic_avg).tolist()
        
        # Interest Coverage Ratio
        if (not income_df.empty):
            if ('EBIT' in income_df.columns and 
                'Interest Expense' in income_df.columns):
                ebit = income_df['EBIT']
                interest = income_df['Interest Expense'].abs()
                ratios['interest_coverage'] = (ebit / interest).tolist()
        
        # Asset Turnover
        if (not balance_df.empty and not income_df.empty):
            if ('Total Assets' in balance_df.columns and 
                'Revenue' in income_df.columns):
                assets = balance_df['Total Assets']
                revenue = income_df['Revenue']
                if len(assets) == len(revenue):
                    assets_avg = assets.rolling(window=2, min_periods=1).mean()
                    ratios['asset_turnover'] = (revenue / assets_avg).tolist()
        
        # Receivables Turnover and DSO
        if (not balance_df.empty and not income_df.empty):
            if ('Accounts Receivable' in balance_df.columns and 
                'Revenue' in income_df.columns):
                receivables = balance_df['Accounts Receivable']
                revenue = income_df['Revenue']
                if len(receivables) == len(revenue):
                    ar_avg = receivables.rolling(window=2, min_periods=1).mean()
                    ratios['receivables_turnover'] = (revenue / ar_avg).tolist()
                    ratios['dso'] = (365 * ar_avg / revenue).tolist()  # Days Sales Outstanding
        
        # Payables Turnover and DPO
        if (not balance_df.empty and not income_df.empty):
            if ('Accounts Payable' in balance_df.columns and 
                'Cost of Revenue' in income_df.columns):
                payables = balance_df['Accounts Payable']
                cogs = income_df['Cost of Revenue']
                if len(payables) == len(cogs):
                    ap_avg = payables.rolling(window=2, min_periods=1).mean()
                    ratios['payables_turnover'] = (cogs / ap_avg).tolist()
                    ratios['dpo'] = (365 * ap_avg / cogs).tolist()  # Days Payable Outstanding
        
        # Working Capital Turnover
        if (not balance_df.empty and not income_df.empty):
            if ('Current Assets' in balance_df.columns and 
                'Current Liabilities' in balance_df.columns and
                'Revenue' in income_df.columns):
                wc = balance_df['Current Assets'] - balance_df['Current Liabilities']
                revenue = income_df['Revenue']
                if len(wc) == len(revenue):
                    wc_avg = wc.rolling(window=2, min_periods=1).mean()
                    ratios['working_capital_turnover'] = (revenue / wc_avg).tolist()
        
        # EBITDA Growth
        if not income_df.empty:
            if 'EBITDA' in income_df.columns:
                ebitda = income_df['EBITDA']
                if len(ebitda) > 1:
                    ratios['ebitda_growth_yoy'] = ebitda.pct_change(fill_method=None).dropna().tolist()
                    ratios['ebitda_cagr'] = self._calculate_cagr(ebitda.iloc[0], ebitda.iloc[-1], len(ebitda))
        
        # Asset Growth
        if not balance_df.empty:
            if 'Total Assets' in balance_df.columns:
                assets = balance_df['Total Assets']
                if len(assets) > 1:
                    ratios['asset_growth_yoy'] = assets.pct_change(fill_method=None).dropna().tolist()
        
        # Equity Growth
        if not balance_df.empty:
            if 'Total Equity' in balance_df.columns:
                equity = balance_df['Total Equity']
                if len(equity) > 1:
                    ratios['equity_growth_yoy'] = equity.pct_change(fill_method=None).dropna().tolist()
        
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
    
    def calculate_valuation_ratios(self, market_data: Dict) -> Dict:
        """
        Calculate valuation ratios using market data
        
        Args:
            market_data: Dictionary with market data (price, shares_outstanding, market_cap, etc.)
        
        Returns:
            Dictionary of valuation ratios
        """
        ratios = {}
        
        if not market_data:
            return ratios
        
        current_price = market_data.get('current_price')
        shares_outstanding = market_data.get('shares_outstanding')
        market_cap = market_data.get('market_cap')
        
        if not shares_outstanding or shares_outstanding <= 0:
            return ratios
        
        income_df = self.normalized_income_stmt
        balance_df = self.normalized_balance_sheet
        
        # Per Share Metrics
        if not income_df.empty:
            if 'Net Income' in income_df.columns:
                net_income = income_df['Net Income'].iloc[-1] if len(income_df) > 0 else None
                if net_income and pd.notna(net_income):
                    ratios['eps'] = net_income / shares_outstanding
            
            if 'Revenue' in income_df.columns:
                revenue = income_df['Revenue'].iloc[-1] if len(income_df) > 0 else None
                if revenue and pd.notna(revenue):
                    ratios['revenue_per_share'] = revenue / shares_outstanding
        
        if not balance_df.empty:
            if 'Total Equity' in balance_df.columns:
                equity = balance_df['Total Equity'].iloc[-1] if len(balance_df) > 0 else None
                if equity and pd.notna(equity):
                    ratios['book_value_per_share'] = equity / shares_outstanding
        
        if not self.normalized_cash_flow.empty:
            if 'Operating Cash Flow' in self.normalized_cash_flow.columns:
                ocf = self.normalized_cash_flow['Operating Cash Flow'].iloc[-1] if len(self.normalized_cash_flow) > 0 else None
                if ocf and pd.notna(ocf):
                    ratios['cash_flow_per_share'] = ocf / shares_outstanding
        
        # Valuation Ratios (require current price)
        if current_price and current_price > 0:
            if 'eps' in ratios and ratios['eps'] and ratios['eps'] > 0:
                ratios['pe_ratio'] = current_price / ratios['eps']
            
            if 'book_value_per_share' in ratios and ratios['book_value_per_share'] and ratios['book_value_per_share'] > 0:
                ratios['pb_ratio'] = current_price / ratios['book_value_per_share']
            
            if 'revenue_per_share' in ratios and ratios['revenue_per_share'] and ratios['revenue_per_share'] > 0:
                ratios['ps_ratio'] = current_price / ratios['revenue_per_share']
        
        # Enterprise Value Ratios
        if market_cap and market_cap > 0:
            # Calculate Net Debt
            net_debt = 0
            if not balance_df.empty:
                if 'Total Debt' in balance_df.columns:
                    debt = balance_df['Total Debt'].iloc[-1] if len(balance_df) > 0 else 0
                    if pd.notna(debt):
                        net_debt = debt
                if 'Cash and Cash Equivalents' in balance_df.columns:
                    cash = balance_df['Cash and Cash Equivalents'].iloc[-1] if len(balance_df) > 0 else 0
                    if pd.notna(cash):
                        net_debt = net_debt - cash
            
            ev = market_cap + net_debt
            ratios['enterprise_value'] = ev
            
            if not income_df.empty:
                if 'EBITDA' in income_df.columns:
                    ebitda = income_df['EBITDA'].iloc[-1] if len(income_df) > 0 else None
                    if ebitda and pd.notna(ebitda) and ebitda > 0:
                        ratios['ev_ebitda'] = ev / ebitda
                
                if 'EBIT' in income_df.columns:
                    ebit = income_df['EBIT'].iloc[-1] if len(income_df) > 0 else None
                    if ebit and pd.notna(ebit) and ebit > 0:
                        ratios['ev_ebit'] = ev / ebit
                
                if 'Revenue' in income_df.columns:
                    revenue = income_df['Revenue'].iloc[-1] if len(income_df) > 0 else None
                    if revenue and pd.notna(revenue) and revenue > 0:
                        ratios['ev_revenue'] = ev / revenue
                        ratios['market_cap_to_revenue'] = market_cap / revenue
        
        return ratios
    
    def calculate_all_ratios(self, market_data: Optional[Dict] = None) -> Dict:
        """
        Calculate all financial ratios including valuation ratios
        
        Args:
            market_data: Optional dictionary with market data for valuation ratios
        
        Returns:
            Complete dictionary of all calculated ratios
        """
        # Calculate base ratios
        ratios = self.calculate_ratios()
        
        # Add valuation ratios if market data provided
        if market_data:
            valuation_ratios = self.calculate_valuation_ratios(market_data)
            ratios.update(valuation_ratios)
        
        return ratios

