"""
Valuation Analysis Module
Sensitivity analysis, scenario analysis, and relative valuation
"""

import pandas as pd
import numpy as np
import os
import sys
from typing import Dict, List, Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from src.dcf_model import DCFModel


class ValuationAnalyzer:
    """Performs sensitivity analysis, scenario analysis, and relative valuation"""
    
    def __init__(self, dcf_model: DCFModel, base_assumptions: Dict):
        """
        Initialize valuation analyzer
        
        Args:
            dcf_model: DCFModel instance
            base_assumptions: Base case assumptions dictionary
        """
        self.dcf_model = dcf_model
        self.base_assumptions = base_assumptions
        self.sensitivity_results = {}
        self.scenario_results = {}
        self.relative_valuation = {}
    
    def run_sensitivity_analysis(self) -> Dict:
        """
        Run sensitivity analysis on key variables
        
        Returns:
            Dictionary with sensitivity analysis results
        """
        print("Running sensitivity analysis...")
        
        # WACC sensitivity
        wacc_sensitivity = self._wacc_sensitivity()
        
        # Terminal growth rate sensitivity
        terminal_growth_sensitivity = self._terminal_growth_sensitivity()
        
        # Revenue growth sensitivity
        revenue_growth_sensitivity = self._revenue_growth_sensitivity()
        
        # Margin sensitivity
        margin_sensitivity = self._margin_sensitivity()
        
        self.sensitivity_results = {
            'wacc': wacc_sensitivity,
            'terminal_growth': terminal_growth_sensitivity,
            'revenue_growth': revenue_growth_sensitivity,
            'margin': margin_sensitivity,
        }
        
        return self.sensitivity_results
    
    def _wacc_sensitivity(self) -> pd.DataFrame:
        """Sensitivity analysis on WACC"""
        base_wacc = self.dcf_model.wacc
        ranges = config.DEFAULT_ASSUMPTIONS['wacc_sensitivity_range']
        
        results = []
        
        for wacc_change in ranges:
            new_wacc = base_wacc + wacc_change
            
            # Recalculate valuation with new WACC
            terminal_value_data = self.dcf_model.calculate_terminal_value()
            valuation = self.dcf_model.calculate_valuation(terminal_value_data)
            
            results.append({
                'WACC Change': f"{wacc_change:+.1%}",
                'WACC': f"{new_wacc:.2%}",
                'Value per Share': valuation['value_per_share'],
                'Equity Value': valuation['equity_value'],
                'Upside/Downside': ((valuation['value_per_share'] / 
                                    self.dcf_model.market_data.get('current_price', 1)) - 1) * 100
            })
        
        return pd.DataFrame(results)
    
    def _terminal_growth_sensitivity(self) -> pd.DataFrame:
        """Sensitivity analysis on terminal growth rate"""
        base_growth = config.DEFAULT_ASSUMPTIONS['terminal_growth_rate']
        ranges = config.DEFAULT_ASSUMPTIONS['terminal_growth_sensitivity_range']
        
        results = []
        
        for growth_change in ranges:
            new_growth = base_growth + growth_change
            
            # Recalculate terminal value and valuation
            terminal_value_data = self.dcf_model.calculate_terminal_value(
                terminal_growth_rate=new_growth
            )
            valuation = self.dcf_model.calculate_valuation(terminal_value_data)
            
            results.append({
                'Terminal Growth Change': f"{growth_change:+.1%}",
                'Terminal Growth': f"{new_growth:.2%}",
                'Value per Share': valuation['value_per_share'],
                'Equity Value': valuation['equity_value'],
                'Upside/Downside': ((valuation['value_per_share'] / 
                                    self.dcf_model.market_data.get('current_price', 1)) - 1) * 100
            })
        
        return pd.DataFrame(results)
    
    def _revenue_growth_sensitivity(self) -> pd.DataFrame:
        """Sensitivity analysis on revenue growth"""
        base_growth = self.base_assumptions.get('revenue_growth', [0.05] * 5)
        ranges = config.DEFAULT_ASSUMPTIONS['revenue_growth_sensitivity_range']
        
        results = []
        
        for growth_change in ranges:
            new_growth = [g + growth_change for g in base_growth]
            
            # Rebuild projections with new growth
            new_assumptions = self.base_assumptions.copy()
            new_assumptions['revenue_growth'] = new_growth
            
            self.dcf_model.build_projections(new_assumptions)
            terminal_value_data = self.dcf_model.calculate_terminal_value()
            valuation = self.dcf_model.calculate_valuation(terminal_value_data)
            
            results.append({
                'Revenue Growth Change': f"{growth_change:+.1%}",
                'Value per Share': valuation['value_per_share'],
                'Equity Value': valuation['equity_value'],
                'Upside/Downside': ((valuation['value_per_share'] / 
                                    self.dcf_model.market_data.get('current_price', 1)) - 1) * 100
            })
        
        return pd.DataFrame(results)
    
    def _margin_sensitivity(self) -> pd.DataFrame:
        """Sensitivity analysis on EBIT margin"""
        base_margin = self.base_assumptions.get('ebit_margin', 0.15)
        ranges = config.DEFAULT_ASSUMPTIONS['margin_sensitivity_range']
        
        results = []
        
        for margin_change in ranges:
            new_margin = base_margin + margin_change
            
            # Rebuild projections with new margin
            new_assumptions = self.base_assumptions.copy()
            new_assumptions['ebit_margin'] = new_margin
            
            self.dcf_model.build_projections(new_assumptions)
            terminal_value_data = self.dcf_model.calculate_terminal_value()
            valuation = self.dcf_model.calculate_valuation(terminal_value_data)
            
            results.append({
                'EBIT Margin Change': f"{margin_change:+.1%}",
                'EBIT Margin': f"{new_margin:.2%}",
                'Value per Share': valuation['value_per_share'],
                'Equity Value': valuation['equity_value'],
                'Upside/Downside': ((valuation['value_per_share'] / 
                                    self.dcf_model.market_data.get('current_price', 1)) - 1) * 100
            })
        
        return pd.DataFrame(results)
    
    def run_scenario_analysis(self) -> Dict:
        """
        Run scenario analysis (Base, Bull, Bear cases)
        
        Returns:
            Dictionary with scenario analysis results
        """
        print("Running scenario analysis...")
        
        # Base case (already calculated)
        base_case = self._calculate_scenario("Base", self.base_assumptions)
        
        # Bull case (optimistic)
        bull_assumptions = self._get_bull_case_assumptions()
        bull_case = self._calculate_scenario("Bull", bull_assumptions)
        
        # Bear case (conservative)
        bear_assumptions = self._get_bear_case_assumptions()
        bear_case = self._calculate_scenario("Bear", bear_assumptions)
        
        self.scenario_results = {
            'base': base_case,
            'bull': bull_case,
            'bear': bear_case,
        }
        
        return self.scenario_results
    
    def _get_bull_case_assumptions(self) -> Dict:
        """Get optimistic assumptions for bull case"""
        assumptions = self.base_assumptions.copy()
        
        # Higher revenue growth
        base_growth = assumptions.get('revenue_growth', [0.05] * 5)
        assumptions['revenue_growth'] = [g * 1.5 for g in base_growth]
        
        # Higher margins
        if 'ebit_margin' in assumptions:
            assumptions['ebit_margin'] = assumptions['ebit_margin'] * 1.2
        
        # Lower WACC (better market conditions)
        if 'cost_of_equity' not in assumptions:
            # Adjust beta down or ERP down
            pass
        
        return assumptions
    
    def _get_bear_case_assumptions(self) -> Dict:
        """Get conservative assumptions for bear case"""
        assumptions = self.base_assumptions.copy()
        
        # Lower revenue growth
        base_growth = assumptions.get('revenue_growth', [0.05] * 5)
        assumptions['revenue_growth'] = [g * 0.7 for g in base_growth]
        
        # Lower margins
        if 'ebit_margin' in assumptions:
            assumptions['ebit_margin'] = assumptions['ebit_margin'] * 0.8
        
        # Higher WACC (worse market conditions)
        if 'cost_of_equity' not in assumptions:
            # Adjust beta up or ERP up
            pass
        
        return assumptions
    
    def _calculate_scenario(self, scenario_name: str, assumptions: Dict) -> Dict:
        """Calculate valuation for a specific scenario"""
        print(f"  Calculating {scenario_name} case...")
        
        # Build projections
        self.dcf_model.build_projections(assumptions)
        
        # Calculate WACC (may need to adjust for scenario)
        wacc = self.dcf_model.calculate_wacc()
        
        # Calculate terminal value
        terminal_value_data = self.dcf_model.calculate_terminal_value()
        
        # Calculate valuation
        valuation = self.dcf_model.calculate_valuation(terminal_value_data)
        
        current_price = self.dcf_model.market_data.get('current_price', 1)
        upside_downside = ((valuation['value_per_share'] / current_price) - 1) * 100
        
        return {
            'scenario': scenario_name,
            'assumptions': assumptions,
            'wacc': wacc,
            'value_per_share': valuation['value_per_share'],
            'equity_value': valuation['equity_value'],
            'enterprise_value': valuation['enterprise_value'],
            'current_price': current_price,
            'upside_downside_pct': upside_downside,
            'recommendation': self._get_recommendation(upside_downside),
        }
    
    def _get_recommendation(self, upside_downside: float) -> str:
        """Get investment recommendation based on upside/downside"""
        if upside_downside > 20:
            return "Strong Buy"
        elif upside_downside > 10:
            return "Buy"
        elif upside_downside > -10:
            return "Hold"
        elif upside_downside > -20:
            return "Sell"
        else:
            return "Strong Sell"
    
    def calculate_relative_valuation(self, peer_data: Dict) -> Dict:
        """
        Calculate relative valuation using peer multiples
        
        Args:
            peer_data: Dictionary with peer company data
        
        Returns:
            Dictionary with relative valuation results
        """
        print("Calculating relative valuation...")
        
        # Get company's financial metrics
        if self.dcf_model.income_projections is None:
            raise ValueError("Must build projections before relative valuation")
        
        latest_revenue = self.dcf_model.revenue_projections.iloc[-1]
        latest_ebitda = self.dcf_model.income_projections['EBITDA'].iloc[-1]
        latest_ebit = self.dcf_model.income_projections['EBIT'].iloc[-1]
        latest_net_income = self.dcf_model.income_projections['Net Income'].iloc[-1]
        
        # Calculate peer multiples
        peer_multiples = []
        
        for ticker, data in peer_data.items():
            if 'error' in data:
                continue
            
            multiples = {}
            multiples['Ticker'] = ticker
            multiples['Name'] = data.get('name', ticker)
            
            # EV/EBITDA
            if data.get('ev_ebitda'):
                multiples['EV/EBITDA'] = data['ev_ebitda']
            
            # P/E
            if data.get('pe_ratio'):
                multiples['P/E'] = data['pe_ratio']
            
            # P/B
            if data.get('pb_ratio'):
                multiples['P/B'] = data['pb_ratio']
            
            peer_multiples.append(multiples)
        
        peer_df = pd.DataFrame(peer_multiples)
        
        # Calculate implied valuations
        implied_valuations = {}
        
        # EV/EBITDA multiple
        if 'EV/EBITDA' in peer_df.columns:
            median_ev_ebitda = peer_df['EV/EBITDA'].median()
            implied_ev = latest_ebitda * median_ev_ebitda
            
            # Convert to equity value (subtract net debt)
            net_debt = self.dcf_model.enterprise_value - self.dcf_model.equity_value if self.dcf_model.enterprise_value else 0
            implied_equity_value = implied_ev - net_debt
            
            shares = self.dcf_model.market_data.get('shares_outstanding', 1)
            implied_value_per_share = implied_equity_value / shares
            
            implied_valuations['EV/EBITDA'] = {
                'multiple': median_ev_ebitda,
                'implied_equity_value': implied_equity_value,
                'implied_value_per_share': implied_value_per_share,
            }
        
        # P/E multiple
        if 'P/E' in peer_df.columns:
            median_pe = peer_df['P/E'].median()
            implied_equity_value = latest_net_income * median_pe
            shares = self.dcf_model.market_data.get('shares_outstanding', 1)
            implied_value_per_share = implied_equity_value / shares
            
            implied_valuations['P/E'] = {
                'multiple': median_pe,
                'implied_equity_value': implied_equity_value,
                'implied_value_per_share': implied_value_per_share,
            }
        
        self.relative_valuation = {
            'peer_multiples': peer_df,
            'implied_valuations': implied_valuations,
        }
        
        return self.relative_valuation
    
    def get_final_recommendation(self) -> Dict:
        """
        Get final investment recommendation combining DCF and relative valuation
        
        Returns:
            Dictionary with final recommendation
        """
        # Get base case DCF value
        base_value = self.scenario_results['base']['value_per_share']
        current_price = self.scenario_results['base']['current_price']
        
        # Get relative valuation (weighted average if multiple methods)
        relative_values = []
        if 'EV/EBITDA' in self.relative_valuation.get('implied_valuations', {}):
            relative_values.append(
                self.relative_valuation['implied_valuations']['EV/EBITDA']['implied_value_per_share']
            )
        if 'P/E' in self.relative_valuation.get('implied_valuations', {}):
            relative_values.append(
                self.relative_valuation['implied_valuations']['P/E']['implied_value_per_share']
            )
        
        if relative_values:
            avg_relative_value = np.mean(relative_values)
        else:
            avg_relative_value = base_value
        
        # Weighted target price (70% DCF, 30% relative)
        target_price = 0.7 * base_value + 0.3 * avg_relative_value
        
        # Calculate upside/downside
        upside_downside = ((target_price / current_price) - 1) * 100
        
        # Get recommendation
        recommendation = self._get_recommendation(upside_downside)
        
        return {
            'current_price': current_price,
            'dcf_value': base_value,
            'relative_value': avg_relative_value if relative_values else None,
            'target_price': target_price,
            'upside_downside_pct': upside_downside,
            'recommendation': recommendation,
        }

