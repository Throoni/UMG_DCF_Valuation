"""
Main execution script for UMG DCF Valuation Model
Orchestrates all modules and generates final Excel output
"""

import os
import sys
import pandas as pd
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from src.data_collection import DataCollector
from src.financial_analysis import FinancialAnalyzer
from src.dcf_model import DCFModel
from src.valuation_analysis import ValuationAnalyzer
from src.excel_generator import ExcelGenerator
from src.audit_system import AuditSystem


def main():
    """Main execution function"""
    print("=" * 60)
    print("UMG DCF VALUATION MODEL")
    print("=" * 60)
    print(f"Company: {config.COMPANY_NAME} ({config.COMPANY_TICKER})")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    try:
        # Step 1: Collect Data
        print("\n[Step 1/7] Data Collection")
        print("-" * 60)
        collector = DataCollector()
        data = collector.collect_all_data()
        
        if not data:
            print("ERROR: No data collected. Exiting.")
            return 1
        
        # Step 2: Analyze Financial Statements
        print("\n[Step 2/7] Financial Analysis")
        print("-" * 60)
        income_stmt = data.get('income_statement', pd.DataFrame())
        balance_sheet = data.get('balance_sheet', pd.DataFrame())
        cash_flow = data.get('cash_flow', pd.DataFrame())
        
        if income_stmt.empty or balance_sheet.empty or cash_flow.empty:
            print("ERROR: Missing financial statements. Exiting.")
            return 1
        
        financial_analyzer = FinancialAnalyzer(income_stmt, balance_sheet, cash_flow)
        financial_analyzer.normalize_financials()
        financial_analyzer.calculate_ratios()
        
        # Step 3: Prepare DCF Assumptions
        print("\n[Step 3/7] Preparing DCF Assumptions")
        print("-" * 60)
        
        # Get assumptions from historical analysis
        wc_assumptions = financial_analyzer.get_working_capital_assumptions()
        capex_assumptions = financial_analyzer.get_capex_assumptions()
        tax_rate = financial_analyzer.get_tax_rate()
        margins = financial_analyzer.get_historical_margins()
        
        # Build base assumptions
        # Revenue growth - use historical average or default
        revenue_growth_historical = financial_analyzer.ratios.get('revenue_growth_yoy', [])
        if revenue_growth_historical:
            avg_growth = sum([g for g in revenue_growth_historical if not pd.isna(g)]) / len(revenue_growth_historical)
            base_growth = max(0.02, min(0.10, avg_growth))  # Cap between 2% and 10%
        else:
            base_growth = 0.05  # Default 5%
        
        base_assumptions = {
            'revenue_growth': [base_growth] * config.DEFAULT_ASSUMPTIONS['forecast_years'],
            'gross_margin': margins.get('gross_margin', {}).get('latest', 0.40),
            'ebit_margin': margins.get('ebit_margin', {}).get('latest', 0.15),
            'tax_rate': tax_rate,
            'working_capital_pct': wc_assumptions.get('working_capital_pct_revenue', 0.10),
            'capex_pct': capex_assumptions.get('capex_pct_revenue', 0.05),
            'depreciation_pct': 0.03,  # Default 3% of revenue
        }
        
        print(f"  Revenue growth: {base_growth:.1%} per year")
        print(f"  EBIT margin: {base_assumptions['ebit_margin']:.1%}")
        print(f"  Tax rate: {tax_rate:.1%}")
        
        # Step 4: Build DCF Model
        print("\n[Step 4/7] Building DCF Model")
        print("-" * 60)
        
        market_data = {
            'beta': data.get('beta', 1.0),
            'market_cap': data.get('market_cap', None),
            'current_price': data.get('current_price', None),
            'shares_outstanding': data.get('shares_outstanding', None),
        }
        
        macro_data = data.get('macro_data', {
            'risk_free_rate': 0.025,
            'equity_risk_premium': 0.05,
        })
        
        dcf_model = DCFModel(financial_analyzer, market_data, macro_data)
        dcf_model.build_projections(base_assumptions)
        dcf_model.calculate_wacc()
        
        terminal_value_data = dcf_model.calculate_terminal_value()
        valuation = dcf_model.calculate_valuation(terminal_value_data)
        
        # Step 5: Valuation Analysis
        print("\n[Step 5/7] Valuation Analysis")
        print("-" * 60)
        
        valuation_analyzer = ValuationAnalyzer(dcf_model, base_assumptions)
        valuation_analyzer.run_sensitivity_analysis()
        valuation_analyzer.run_scenario_analysis()
        
        # Relative valuation
        peer_data = data.get('peers', {})
        if peer_data:
            valuation_analyzer.calculate_relative_valuation(peer_data)
        
        final_recommendation = valuation_analyzer.get_final_recommendation()
        
        # Step 6: Generate Excel Output
        print("\n[Step 6/7] Generating Excel Output")
        print("-" * 60)
        
        excel_generator = ExcelGenerator(
            financial_analyzer,
            dcf_model,
            valuation_analyzer,
            collector,
            final_recommendation
        )
        
        excel_path = excel_generator.generate_excel()
        
        # Step 7: Run Audit
        print("\n[Step 7/7] Running Audit")
        print("-" * 60)
        
        audit_system = AuditSystem()
        audit_results = audit_system.run_full_audit(
            financial_analyzer=financial_analyzer,
            dcf_model=dcf_model,
            valuation_analyzer=valuation_analyzer,
            excel_file_path=excel_path
        )
        
        # Final Summary
        print("\n" + "=" * 60)
        print("VALUATION COMPLETE")
        print("=" * 60)
        print(f"\nRecommendation: {final_recommendation.get('recommendation', 'N/A')}")
        print(f"Current Price: {final_recommendation.get('current_price', 0):.2f}")
        print(f"Target Price: {final_recommendation.get('target_price', 0):.2f}")
        print(f"Upside/Downside: {final_recommendation.get('upside_downside_pct', 0):.1f}%")
        print(f"\nExcel file: {excel_path}")
        
        is_passed, status_msg = audit_system.get_audit_status()
        print(f"\nAudit Status: {status_msg}")
        
        if not is_passed:
            print("\nWARNING: Audit found errors. Please review before using results.")
            return 1
        
        return 0
    
    except Exception as e:
        print(f"\nERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

