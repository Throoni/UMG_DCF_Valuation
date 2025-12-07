"""
Integration tests for UMG DCF Valuation Model
Tests end-to-end workflow
"""

import pytest
import pandas as pd
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from src.data_collection import DataCollector
from src.financial_analysis import FinancialAnalyzer
from src.dcf_model import DCFModel
from src.valuation_analysis import ValuationAnalyzer
from src.audit_system import AuditSystem


def test_data_collection():
    """Test data collection module"""
    collector = DataCollector()
    data = collector.collect_all_data()
    
    assert data is not None
    assert 'income_statement' in data or 'income_statement' in data.keys()


def test_financial_analysis():
    """Test financial analysis module"""
    # Create sample data
    income_stmt = pd.DataFrame({
        'Revenue': [1000, 1100, 1200],
        'Cost of Revenue': [600, 660, 720],
        'Gross Profit': [400, 440, 480],
        'EBIT': [200, 220, 240],
        'Net Income': [150, 165, 180],
    })
    
    balance_sheet = pd.DataFrame({
        'Total Assets': [2000, 2200, 2400],
        'Total Liabilities': [1200, 1320, 1440],
        'Total Equity': [800, 880, 960],
    })
    
    cash_flow = pd.DataFrame({
        'Operating Cash Flow': [180, 200, 220],
        'Capital Expenditures': [-50, -55, -60],
    })
    
    analyzer = FinancialAnalyzer(income_stmt, balance_sheet, cash_flow)
    analyzer.normalize_financials()
    ratios = analyzer.calculate_ratios()
    
    assert ratios is not None
    assert 'gross_margin' in ratios or len(ratios) > 0


def test_dcf_model():
    """Test DCF model calculations"""
    # Create sample financial analyzer
    income_stmt = pd.DataFrame({'Revenue': [1000], 'EBIT': [200]})
    balance_sheet = pd.DataFrame({'Total Assets': [2000]})
    cash_flow = pd.DataFrame({'Operating Cash Flow': [180]})
    
    analyzer = FinancialAnalyzer(income_stmt, balance_sheet, cash_flow)
    analyzer.normalize_financials()
    
    market_data = {'beta': 1.0, 'market_cap': 1000, 'current_price': 10}
    macro_data = {'risk_free_rate': 0.025, 'equity_risk_premium': 0.05}
    
    dcf = DCFModel(analyzer, market_data, macro_data)
    
    assumptions = {
        'revenue_growth': [0.05] * 5,
        'ebit_margin': 0.20,
        'tax_rate': 0.25,
        'working_capital_pct': 0.10,
        'capex_pct': 0.05,
    }
    
    dcf.build_projections(assumptions)
    wacc = dcf.calculate_wacc()
    
    assert wacc > 0
    assert wacc < 1  # Should be a percentage


def test_audit_system():
    """Test audit system"""
    audit = AuditSystem()
    
    # Test with minimal data
    income_stmt = pd.DataFrame({'Revenue': [1000]})
    balance_sheet = pd.DataFrame({
        'Total Assets': [2000],
        'Total Liabilities': [1200],
        'Total Equity': [800],
    })
    cash_flow = pd.DataFrame({'Operating Cash Flow': [180]})
    
    analyzer = FinancialAnalyzer(income_stmt, balance_sheet, cash_flow)
    analyzer.normalize_financials()
    
    results = audit.run_full_audit(financial_analyzer=analyzer)
    
    assert results is not None
    assert 'financial_checks' in results


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

