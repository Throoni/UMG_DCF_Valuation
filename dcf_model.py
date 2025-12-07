"""
DCF Model Core - Revenue projections, FCFF calculation, WACC, Terminal Value
Implements proper DCF methodology following Damodaran's framework
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional
import config
from utils.data_validation import (
    validate_growth_consistency, validate_wacc_range, 
    validate_terminal_value_pct, validate_terminal_growth_rate
)


class DCFModel:
    """Core DCF valuation model"""
    
    def __init__(self, financial_analyzer, market_data: Dict, macro_data: Dict):
        """
        Initialize DCF model
        
        Args:
            financial_analyzer: FinancialAnalyzer instance with normalized financials
            market_data: Market data dictionary (beta, market cap, etc.)
            macro_data: Macroeconomic data (risk-free rate, ERP, etc.)
        """
        self.financial_analyzer = financial_analyzer
        self.market_data = market_data
        self.macro_data = macro_data
        self.forecast_years = config.DEFAULT_ASSUMPTIONS['forecast_years']
        
        # Projections
        self.revenue_projections = None
        self.income_projections = None
        self.balance_sheet_projections = None
        self.cash_flow_projections = None
        self.fcff_projections = None
        
        # Valuation components
        self.wacc = None
        self.terminal_value = None
        self.enterprise_value = None
        self.equity_value = None
        self.value_per_share = None
        
    def build_projections(self, assumptions: Dict) -> Dict:
        """
        Build 5-year financial projections
        
        Args:
            assumptions: Dictionary with projection assumptions:
                - revenue_growth: List of growth rates for each year
                - gross_margin: Target gross margin or list of margins
                - ebit_margin: Target EBIT margin or list of margins
                - tax_rate: Tax rate for projections
                - working_capital_pct: Working capital as % of revenue
                - capex_pct: CapEx as % of revenue
                - depreciation_pct: Depreciation as % of revenue or CapEx
        
        Returns:
            Dictionary with all projections
        """
        print("Building financial projections...")
        
        # Get starting values from latest historical data
        latest_income = self.financial_analyzer.normalized_income_stmt.iloc[-1] if not self.financial_analyzer.normalized_income_stmt.empty else None
        latest_balance = self.financial_analyzer.normalized_balance_sheet.iloc[-1] if not self.financial_analyzer.normalized_balance_sheet.empty else None
        
        if latest_income is None or 'Revenue' not in latest_income:
            raise ValueError("Cannot build projections: missing historical revenue data")
        
        starting_revenue = latest_income['Revenue']
        
        # Build revenue projections
        self.revenue_projections = self._project_revenue(
            starting_revenue, 
            assumptions.get('revenue_growth', [0.05] * self.forecast_years)
        )
        
        # Build income statement projections
        self.income_projections = self._project_income_statement(
            self.revenue_projections,
            assumptions
        )
        
        # Build balance sheet projections
        self.balance_sheet_projections = self._project_balance_sheet(
            self.revenue_projections,
            self.income_projections,
            latest_balance,
            assumptions
        )
        
        # Build cash flow projections
        self.cash_flow_projections = self._project_cash_flow(
            self.income_projections,
            self.balance_sheet_projections,
            assumptions
        )
        
        # Calculate FCFF
        self.fcff_projections = self._calculate_fcff(
            self.income_projections,
            self.cash_flow_projections,
            self.balance_sheet_projections,
            assumptions.get('tax_rate', 0.25)
        )
        
        return {
            'revenue': self.revenue_projections,
            'income_statement': self.income_projections,
            'balance_sheet': self.balance_sheet_projections,
            'cash_flow': self.cash_flow_projections,
            'fcff': self.fcff_projections,
        }
    
    def _project_revenue(self, starting_revenue: float, 
                        growth_rates: list) -> pd.Series:
        """Project revenue based on growth rates"""
        revenue = [starting_revenue]
        
        for i, growth in enumerate(growth_rates):
            if i >= self.forecast_years:
                break
            next_revenue = revenue[-1] * (1 + growth)
            revenue.append(next_revenue)
        
        # Remove starting value
        revenue = revenue[1:]
        
        return pd.Series(revenue, index=range(1, len(revenue) + 1), name='Revenue')
    
    def _project_income_statement(self, revenue: pd.Series, 
                                  assumptions: Dict) -> pd.DataFrame:
        """Project income statement"""
        income = pd.DataFrame(index=revenue.index)
        income['Revenue'] = revenue
        
        # Gross margin
        gross_margin = assumptions.get('gross_margin', 0.40)
        if isinstance(gross_margin, list):
            income['Gross Margin %'] = pd.Series(gross_margin[:len(revenue)], index=revenue.index)
        else:
            income['Gross Margin %'] = gross_margin
        
        income['Gross Profit'] = income['Revenue'] * income['Gross Margin %']
        income['Cost of Revenue'] = income['Revenue'] - income['Gross Profit']
        
        # Operating expenses (derived from EBIT margin)
        ebit_margin = assumptions.get('ebit_margin', 0.15)
        if isinstance(ebit_margin, list):
            income['EBIT Margin %'] = pd.Series(ebit_margin[:len(revenue)], index=revenue.index)
        else:
            income['EBIT Margin %'] = ebit_margin
        
        income['EBIT'] = income['Revenue'] * income['EBIT Margin %']
        income['Operating Expenses'] = income['Gross Profit'] - income['EBIT']
        
        # Depreciation
        depreciation_pct = assumptions.get('depreciation_pct', 0.03)
        if isinstance(depreciation_pct, list):
            income['Depreciation'] = income['Revenue'] * pd.Series(depreciation_pct[:len(revenue)], index=revenue.index)
        else:
            income['Depreciation'] = income['Revenue'] * depreciation_pct
        
        # EBITDA
        income['EBITDA'] = income['EBIT'] + income['Depreciation']
        
        # Interest expense (assume constant or linked to debt)
        interest_rate = assumptions.get('interest_rate', 0.04)
        # For simplicity, assume interest expense is constant or % of revenue
        if 'interest_expense' in assumptions:
            if isinstance(assumptions['interest_expense'], list):
                income['Interest Expense'] = pd.Series(assumptions['interest_expense'][:len(revenue)], index=revenue.index)
            else:
                income['Interest Expense'] = assumptions['interest_expense']
        else:
            income['Interest Expense'] = income['Revenue'] * 0.01  # Default 1% of revenue
        
        # Income before tax
        income['Income Before Tax'] = income['EBIT'] - income['Interest Expense']
        
        # Tax
        tax_rate = assumptions.get('tax_rate', 0.25)
        income['Tax Rate'] = tax_rate
        income['Income Tax Expense'] = income['Income Before Tax'] * tax_rate
        
        # Net income
        income['Net Income'] = income['Income Before Tax'] - income['Income Tax Expense']
        
        return income
    
    def _project_balance_sheet(self, revenue: pd.Series, income: pd.DataFrame,
                              latest_balance: pd.Series, assumptions: Dict) -> pd.DataFrame:
        """Project balance sheet"""
        balance = pd.DataFrame(index=revenue.index)
        
        # Working capital
        wc_pct = assumptions.get('working_capital_pct', 0.10)
        if isinstance(wc_pct, list):
            balance['Working Capital'] = revenue * pd.Series(wc_pct[:len(revenue)], index=revenue.index)
        else:
            balance['Working Capital'] = revenue * wc_pct
        
        # Change in working capital (for cash flow)
        balance['Change in WC'] = balance['Working Capital'].diff().fillna(0)
        
        # For simplicity, we'll focus on items needed for FCFF
        # In a full model, you'd project all balance sheet items
        
        return balance
    
    def _project_cash_flow(self, income: pd.DataFrame, balance: pd.DataFrame,
                          assumptions: Dict) -> pd.DataFrame:
        """Project cash flow statement"""
        cash_flow = pd.DataFrame(index=income.index)
        
        # Operating cash flow (starting from net income)
        cash_flow['Net Income'] = income['Net Income']
        cash_flow['Depreciation'] = income['Depreciation']
        cash_flow['Change in WC'] = -balance['Change in WC']  # Negative because increase in WC is cash outflow
        
        cash_flow['Operating Cash Flow'] = (
            cash_flow['Net Income'] + 
            cash_flow['Depreciation'] + 
            cash_flow['Change in WC']
        )
        
        # Capital expenditures
        capex_pct = assumptions.get('capex_pct', 0.05)
        if isinstance(capex_pct, list):
            cash_flow['Capital Expenditures'] = -income['Revenue'] * pd.Series(capex_pct[:len(income)], index=income.index)
        else:
            cash_flow['Capital Expenditures'] = -income['Revenue'] * capex_pct
        
        # Free cash flow (simplified - would include other items in full model)
        cash_flow['Free Cash Flow'] = (
            cash_flow['Operating Cash Flow'] + 
            cash_flow['Capital Expenditures']
        )
        
        return cash_flow
    
    def _calculate_fcff(self, income: pd.DataFrame, cash_flow: pd.DataFrame,
                       balance: pd.DataFrame, tax_rate: float) -> pd.Series:
        """
        Calculate Free Cash Flow to Firm (FCFF)
        FCFF = EBIT(1-t) + Depreciation - CapEx - ΔNWC
        """
        fcff = (
            income['EBIT'] * (1 - tax_rate) +
            income['Depreciation'] +
            cash_flow['Capital Expenditures'] -  # Already negative
            balance['Change in WC']
        )
        
        return fcff
    
    def calculate_wacc(self, assumptions: Optional[Dict] = None) -> float:
        """
        Calculate Weighted Average Cost of Capital (WACC)
        WACC = (E/(E+D)) * Re + (D/(E+D)) * Rd * (1-t)
        
        Args:
            assumptions: Optional dict to override defaults:
                - cost_of_equity: Override calculated cost of equity
                - cost_of_debt: Override calculated cost of debt
                - equity_weight: Override calculated equity weight
                - debt_weight: Override calculated debt weight
        
        Returns:
            WACC as decimal (e.g., 0.10 for 10%)
        """
        print("Calculating WACC...")
        
        # Cost of Equity (CAPM)
        if assumptions and 'cost_of_equity' in assumptions:
            cost_of_equity = assumptions['cost_of_equity']
        else:
            cost_of_equity = self._calculate_cost_of_equity()
        
        # Cost of Debt
        if assumptions and 'cost_of_debt' in assumptions:
            cost_of_debt = assumptions['cost_of_debt']
        else:
            cost_of_debt = self._calculate_cost_of_debt()
        
        # Capital Structure
        if assumptions and 'equity_weight' in assumptions and 'debt_weight' in assumptions:
            equity_weight = assumptions['equity_weight']
            debt_weight = assumptions['debt_weight']
        else:
            equity_weight, debt_weight = self._get_capital_structure()
        
        # Tax rate
        tax_rate = assumptions.get('tax_rate', 0.25) if assumptions else 0.25
        
        # Calculate WACC
        wacc = (equity_weight * cost_of_equity + 
                debt_weight * cost_of_debt * (1 - tax_rate))
        
        # Validate WACC
        is_valid, error_msg = validate_wacc_range(wacc)
        if not is_valid:
            print(f"  Warning: {error_msg}")
        
        self.wacc = wacc
        return wacc
    
    def _calculate_cost_of_equity(self) -> float:
        """Calculate cost of equity using CAPM: Re = Rf + β × (Rm - Rf)"""
        risk_free_rate = self.macro_data.get('risk_free_rate', 0.025)
        equity_risk_premium = self.macro_data.get('equity_risk_premium', 0.05)
        beta = self.market_data.get('beta', 1.0)
        
        if beta is None:
            print("  Warning: Beta not available, using default of 1.0")
            beta = 1.0
        
        cost_of_equity = risk_free_rate + beta * equity_risk_premium
        
        print(f"    Risk-free rate: {risk_free_rate:.2%}")
        print(f"    Beta: {beta:.2f}")
        print(f"    Equity risk premium: {equity_risk_premium:.2%}")
        print(f"    Cost of equity: {cost_of_equity:.2%}")
        
        return cost_of_equity
    
    def _calculate_cost_of_debt(self) -> float:
        """Calculate cost of debt"""
        # Try to get from market data
        if 'cost_of_debt' in self.market_data:
            return self.market_data['cost_of_debt']
        
        # Use risk-free rate + credit spread (default 2%)
        risk_free_rate = self.macro_data.get('risk_free_rate', 0.025)
        credit_spread = 0.02  # 200 bps default spread
        
        cost_of_debt = risk_free_rate + credit_spread
        
        print(f"    Cost of debt: {cost_of_debt:.2%} (Rf + {credit_spread:.2%} spread)")
        
        return cost_of_debt
    
    def _get_capital_structure(self) -> Tuple[float, float]:
        """Get equity and debt weights"""
        market_cap = self.market_data.get('market_cap', None)
        
        # Get debt from balance sheet
        if not self.financial_analyzer.normalized_balance_sheet.empty:
            latest_balance = self.financial_analyzer.normalized_balance_sheet.iloc[-1]
            if 'Total Debt' in latest_balance:
                debt = latest_balance['Total Debt']
            else:
                debt = 0
        else:
            debt = 0
        
        # If market cap not available, use book equity
        if market_cap is None or market_cap == 0:
            if not self.financial_analyzer.normalized_balance_sheet.empty:
                latest_balance = self.financial_analyzer.normalized_balance_sheet.iloc[-1]
                if 'Total Equity' in latest_balance:
                    equity_value = latest_balance['Total Equity']
                else:
                    equity_value = 1000  # Default
            else:
                equity_value = 1000
        else:
            equity_value = market_cap
        
        total_capital = equity_value + debt
        
        if total_capital == 0:
            equity_weight = 0.7
            debt_weight = 0.3
        else:
            equity_weight = equity_value / total_capital
            debt_weight = debt / total_capital
        
        print(f"    Equity weight: {equity_weight:.2%}")
        print(f"    Debt weight: {debt_weight:.2%}")
        
        return equity_weight, debt_weight
    
    def calculate_terminal_value(self, terminal_growth_rate: float = None,
                                exit_multiple: float = None,
                                exit_multiple_metric: str = 'EBITDA') -> Dict:
        """
        Calculate terminal value using both perpetuity growth and exit multiple methods
        
        Args:
            terminal_growth_rate: Terminal growth rate (defaults to config)
            exit_multiple: Exit multiple (e.g., EV/EBITDA)
            exit_multiple_metric: Metric for exit multiple ('EBITDA', 'EBIT', 'Revenue')
        
        Returns:
            Dictionary with terminal value calculations
        """
        print("Calculating terminal value...")
        
        if terminal_growth_rate is None:
            terminal_growth_rate = config.DEFAULT_ASSUMPTIONS['terminal_growth_rate']
        
        # Validate terminal growth rate
        is_valid, error_msg = validate_terminal_growth_rate(terminal_growth_rate)
        if not is_valid:
            print(f"  Warning: {error_msg}")
        
        # Get final year FCFF
        final_fcff = self.fcff_projections.iloc[-1]
        
        # Perpetuity growth method
        # TV = FCFF × (1+g) / (WACC - g)
        if self.wacc is None:
            raise ValueError("WACC must be calculated before terminal value")
        
        if self.wacc <= terminal_growth_rate:
            raise ValueError(
                f"WACC ({self.wacc:.2%}) must be greater than terminal growth rate "
                f"({terminal_growth_rate:.2%})"
            )
        
        terminal_value_perpetuity = (
            final_fcff * (1 + terminal_growth_rate) / 
            (self.wacc - terminal_growth_rate)
        )
        
        print(f"    Terminal growth rate: {terminal_growth_rate:.2%}")
        print(f"    Final year FCFF: {final_fcff:,.0f}")
        print(f"    Terminal value (perpetuity): {terminal_value_perpetuity:,.0f}")
        
        # Exit multiple method
        terminal_value_exit = None
        if exit_multiple is not None:
            # Get final year metric
            if exit_multiple_metric == 'EBITDA':
                final_metric = self.income_projections['EBITDA'].iloc[-1]
            elif exit_multiple_metric == 'EBIT':
                final_metric = self.income_projections['EBIT'].iloc[-1]
            elif exit_multiple_metric == 'Revenue':
                final_metric = self.revenue_projections.iloc[-1]
            else:
                raise ValueError(f"Unknown exit multiple metric: {exit_multiple_metric}")
            
            terminal_value_exit = final_metric * exit_multiple
            print(f"    Exit multiple ({exit_multiple_metric}): {exit_multiple:.2f}x")
            print(f"    Terminal value (exit multiple): {terminal_value_exit:,.0f}")
        
        # Weighted terminal value
        if terminal_value_exit is not None:
            perpetuity_weight = config.DEFAULT_ASSUMPTIONS['terminal_value_perpetuity_weight']
            exit_weight = config.DEFAULT_ASSUMPTIONS['terminal_value_exit_multiple_weight']
            terminal_value = (perpetuity_weight * terminal_value_perpetuity + 
                            exit_weight * terminal_value_exit)
        else:
            terminal_value = terminal_value_perpetuity
        
        self.terminal_value = terminal_value
        
        return {
            'terminal_value_perpetuity': terminal_value_perpetuity,
            'terminal_value_exit': terminal_value_exit,
            'terminal_value': terminal_value,
            'terminal_growth_rate': terminal_growth_rate,
            'exit_multiple': exit_multiple,
            'exit_multiple_metric': exit_multiple_metric,
        }
    
    def calculate_valuation(self, terminal_value_data: Dict) -> Dict:
        """
        Calculate enterprise value and equity value
        
        Args:
            terminal_value_data: Output from calculate_terminal_value()
        
        Returns:
            Dictionary with valuation results
        """
        print("Calculating valuation...")
        
        if self.wacc is None:
            raise ValueError("WACC must be calculated before valuation")
        
        if self.fcff_projections is None:
            raise ValueError("FCFF projections must be calculated before valuation")
        
        # Discount FCFF (mid-year convention)
        pv_fcff = []
        for i, fcff in enumerate(self.fcff_projections, start=1):
            # Mid-year convention: discount period = i - 0.5
            discount_period = i - 0.5
            pv = fcff / ((1 + self.wacc) ** discount_period)
            pv_fcff.append(pv)
        
        pv_fcff_sum = sum(pv_fcff)
        
        # Discount terminal value (mid-year convention)
        # Terminal value occurs at end of final year, so discount period = forecast_years - 0.5
        discount_period_tv = self.forecast_years - 0.5
        terminal_value = terminal_value_data['terminal_value']
        pv_terminal_value = terminal_value / ((1 + self.wacc) ** discount_period_tv)
        
        # Enterprise value
        enterprise_value = pv_fcff_sum + pv_terminal_value
        
        # Validate terminal value percentage
        tv_pct = pv_terminal_value / enterprise_value
        is_valid, error_msg = validate_terminal_value_pct(
            pv_terminal_value, enterprise_value
        )
        if not is_valid:
            print(f"  Warning: {error_msg}")
        
        # Equity value = Enterprise value - Net debt + Non-operating assets - NCI
        # Get net debt from latest balance sheet
        if not self.financial_analyzer.normalized_balance_sheet.empty:
            latest_balance = self.financial_analyzer.normalized_balance_sheet.iloc[-1]
            if 'Net Debt' in latest_balance:
                net_debt = latest_balance['Net Debt']
            elif 'Total Debt' in latest_balance and 'Cash and Cash Equivalents' in latest_balance:
                net_debt = latest_balance['Total Debt'] - latest_balance['Cash and Cash Equivalents']
            else:
                net_debt = 0
        else:
            net_debt = 0
        
        non_operating_assets = 0  # Would need to identify from financials
        non_controlling_interests = 0  # Would need to identify from financials
        
        equity_value = enterprise_value - net_debt + non_operating_assets - non_controlling_interests
        
        # Value per share
        shares_outstanding = self.market_data.get('shares_outstanding', None)
        if shares_outstanding is None or shares_outstanding == 0:
            # Try to calculate from market cap and price
            market_cap = self.market_data.get('market_cap', None)
            current_price = self.market_data.get('current_price', None)
            if market_cap and current_price:
                shares_outstanding = market_cap / current_price
            else:
                raise ValueError("Cannot calculate value per share: shares outstanding not available")
        
        value_per_share = equity_value / shares_outstanding
        
        self.enterprise_value = enterprise_value
        self.equity_value = equity_value
        self.value_per_share = value_per_share
        
        print(f"    PV of FCFF: {pv_fcff_sum:,.0f}")
        print(f"    PV of Terminal Value: {pv_terminal_value:,.0f}")
        print(f"    Enterprise Value: {enterprise_value:,.0f}")
        print(f"    Net Debt: {net_debt:,.0f}")
        print(f"    Equity Value: {equity_value:,.0f}")
        print(f"    Shares Outstanding: {shares_outstanding:,.0f}")
        print(f"    Value per Share: {value_per_share:.2f}")
        
        return {
            'pv_fcff': pv_fcff_sum,
            'pv_terminal_value': pv_terminal_value,
            'enterprise_value': enterprise_value,
            'net_debt': net_debt,
            'equity_value': equity_value,
            'shares_outstanding': shares_outstanding,
            'value_per_share': value_per_share,
            'terminal_value_pct': tv_pct,
        }

