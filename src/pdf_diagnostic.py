"""
PDF Extraction Diagnostic Tool
Compares PDF extracted values against confirmed manual data to identify extraction issues
"""

import pandas as pd
import os
import sys
from typing import Dict, List, Tuple
from src.pdf_extractor import PDFExtractor
from src.excel_data_reader import ExcelDataReader

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


class PDFDiagnostic:
    """Diagnostic tool to identify PDF extraction issues"""
    
    def __init__(self):
        self.extractor = PDFExtractor(verbose=True)
        self.excel_reader = ExcelDataReader()
    
    def compare_extraction_vs_manual(self, pdf_path: str, year: int) -> Dict:
        """
        Compare PDF extracted values against manual data for a specific year
        
        Args:
            pdf_path: Path to PDF file
            year: Year to compare
        
        Returns:
            Dictionary with comparison results
        """
        print(f"\n{'='*60}")
        print(f"PDF EXTRACTION DIAGNOSTIC")
        print(f"{'='*60}")
        print(f"PDF: {os.path.basename(pdf_path)}")
        print(f"Year: {year}")
        print(f"{'='*60}\n")
        
        # Load corrected data from Excel
        manual_data = self.excel_reader.read_historical_financials()
        if manual_data['income_statement'].empty and manual_data['balance_sheet'].empty:
            print("ERROR: No manual data found for comparison")
            return {}
        
        # Extract from PDF
        print("Extracting data from PDF...")
        pdf_data = self.extractor.extract_all_statements(pdf_path, year, verbose=True)
        
        # Compare key line items
        comparison = {
            'year': year,
            'income_statement': {},
            'balance_sheet': {},
            'cash_flow': {},
            'issues': []
        }
        
        # Compare Income Statement
        if not manual_data['income_statement'].empty:
            manual_income = manual_data['income_statement']
            manual_year_row = manual_income[manual_income['Date'].dt.year == year]
            
            if not manual_year_row.empty and 'income_statement' in pdf_data:
                pdf_income = pdf_data['income_statement']
                
                # Compare key metrics
                key_metrics = ['Revenue', 'EBITDA', 'Net Income', 'EBIT']
                for metric in key_metrics:
                    if metric in manual_year_row.columns:
                        manual_val = manual_year_row[metric].iloc[0] if not manual_year_row.empty else None
                        pdf_val = pdf_income[metric].iloc[0] if metric in pdf_income.columns and not pdf_income.empty else None
                        
                        comparison['income_statement'][metric] = {
                            'manual': manual_val,
                            'pdf': pdf_val,
                            'difference': None,
                            'difference_pct': None
                        }
                        
                        if manual_val is not None and pdf_val is not None:
                            diff = abs(manual_val - pdf_val)
                            diff_pct = (diff / abs(manual_val)) * 100 if manual_val != 0 else None
                            comparison['income_statement'][metric]['difference'] = diff
                            comparison['income_statement'][metric]['difference_pct'] = diff_pct
                            
                            if diff_pct and diff_pct > 1.0:  # More than 1% difference
                                comparison['issues'].append(
                                    f"Income Statement - {metric}: "
                                    f"Manual={manual_val:,.0f}, PDF={pdf_val:,.0f}, "
                                    f"Diff={diff:,.0f} ({diff_pct:.1f}%)"
                                )
        
        # Compare Balance Sheet
        if not manual_data['balance_sheet'].empty:
            manual_balance = manual_data['balance_sheet']
            manual_year_row = manual_balance[manual_balance['Date'].dt.year == year]
            
            if not manual_year_row.empty and 'balance_sheet' in pdf_data:
                pdf_balance = pdf_data['balance_sheet']
                
                # Compare key metrics
                key_metrics = ['Total Assets', 'Cash and Cash Equivalents', 'Total Equity', 'Total Debt']
                for metric in key_metrics:
                    if metric in manual_year_row.columns:
                        manual_val = manual_year_row[metric].iloc[0] if not manual_year_row.empty else None
                        pdf_val = pdf_balance[metric].iloc[0] if metric in pdf_balance.columns and not pdf_balance.empty else None
                        
                        comparison['balance_sheet'][metric] = {
                            'manual': manual_val,
                            'pdf': pdf_val,
                            'difference': None,
                            'difference_pct': None
                        }
                        
                        if manual_val is not None and pdf_val is not None:
                            diff = abs(manual_val - pdf_val)
                            diff_pct = (diff / abs(manual_val)) * 100 if manual_val != 0 else None
                            comparison['balance_sheet'][metric]['difference'] = diff
                            comparison['balance_sheet'][metric]['difference_pct'] = diff_pct
                            
                            if diff_pct and diff_pct > 1.0:  # More than 1% difference
                                comparison['issues'].append(
                                    f"Balance Sheet - {metric}: "
                                    f"Manual={manual_val:,.0f}, PDF={pdf_val:,.0f}, "
                                    f"Diff={diff:,.0f} ({diff_pct:.1f}%)"
                                )
        
        # Compare Cash Flow
        if not manual_data['cash_flow'].empty:
            manual_cash = manual_data['cash_flow']
            manual_year_row = manual_cash[manual_cash['Date'].dt.year == year]
            
            if not manual_year_row.empty and 'cash_flow' in pdf_data:
                pdf_cash = pdf_data['cash_flow']
                
                # Compare key metrics
                key_metrics = ['Operating Cash Flow', 'Free Cash Flow']
                for metric in key_metrics:
                    if metric in manual_year_row.columns:
                        manual_val = manual_year_row[metric].iloc[0] if not manual_year_row.empty else None
                        pdf_val = pdf_cash[metric].iloc[0] if metric in pdf_cash.columns and not pdf_cash.empty else None
                        
                        comparison['cash_flow'][metric] = {
                            'manual': manual_val,
                            'pdf': pdf_val,
                            'difference': None,
                            'difference_pct': None
                        }
                        
                        if manual_val is not None and pdf_val is not None:
                            diff = abs(manual_val - pdf_val)
                            diff_pct = (diff / abs(manual_val)) * 100 if manual_val != 0 else None
                            comparison['cash_flow'][metric]['difference'] = diff
                            comparison['cash_flow'][metric]['difference_pct'] = diff_pct
                            
                            if diff_pct and diff_pct > 1.0:  # More than 1% difference
                                comparison['issues'].append(
                                    f"Cash Flow - {metric}: "
                                    f"Manual={manual_val:,.0f}, PDF={pdf_val:,.0f}, "
                                    f"Diff={diff:,.0f} ({diff_pct:.1f}%)"
                                )
        
        # Print summary
        self._print_comparison_summary(comparison)
        
        return comparison
    
    def _print_comparison_summary(self, comparison: Dict):
        """Print formatted comparison summary"""
        print(f"\n{'='*60}")
        print("COMPARISON SUMMARY")
        print(f"{'='*60}\n")
        
        # Income Statement
        if comparison['income_statement']:
            print("Income Statement:")
            for metric, values in comparison['income_statement'].items():
                manual = values['manual']
                pdf = values['pdf']
                diff_pct = values['difference_pct']
                
                status = "✓" if diff_pct and diff_pct <= 1.0 else "✗"
                print(f"  {status} {metric}:")
                print(f"    Manual: {manual:,.0f}" if manual is not None else "    Manual: N/A")
                print(f"    PDF:    {pdf:,.0f}" if pdf is not None else "    PDF:    N/A")
                if diff_pct is not None:
                    print(f"    Diff:   {values['difference']:,.0f} ({diff_pct:.1f}%)")
                print()
        
        # Balance Sheet
        if comparison['balance_sheet']:
            print("Balance Sheet:")
            for metric, values in comparison['balance_sheet'].items():
                manual = values['manual']
                pdf = values['pdf']
                diff_pct = values['difference_pct']
                
                status = "✓" if diff_pct and diff_pct <= 1.0 else "✗"
                print(f"  {status} {metric}:")
                print(f"    Manual: {manual:,.0f}" if manual is not None else "    Manual: N/A")
                print(f"    PDF:    {pdf:,.0f}" if pdf is not None else "    PDF:    N/A")
                if diff_pct is not None:
                    print(f"    Diff:   {values['difference']:,.0f} ({diff_pct:.1f}%)")
                print()
        
        # Issues
        if comparison['issues']:
            print(f"\n{'='*60}")
            print("IDENTIFIED ISSUES (>1% difference):")
            print(f"{'='*60}")
            for issue in comparison['issues']:
                print(f"  - {issue}")
        else:
            print("\n✓ No significant differences found (all within 1%)")
    
    def diagnose_all_pdfs(self) -> List[Dict]:
        """
        Run diagnostic on all available PDF files
        
        Returns:
            List of comparison results for each PDF
        """
        results = []
        
        # Find all PDF files
        pdf_dir = config.IR_ANNUAL_DIR
        if not os.path.exists(pdf_dir):
            print(f"PDF directory not found: {pdf_dir}")
            return results
        
        pdf_files = [f for f in os.listdir(pdf_dir) if f.lower().endswith('.pdf')]
        
        if not pdf_files:
            print(f"No PDF files found in {pdf_dir}")
            return results
        
        # Extract year from filename and compare
        import re
        for pdf_file in pdf_files:
            year_match = re.search(r'(\d{4})', pdf_file)
            if year_match:
                year = int(year_match.group(1))
                pdf_path = os.path.join(pdf_dir, pdf_file)
                result = self.compare_extraction_vs_manual(pdf_path, year)
                results.append(result)
        
        return results


if __name__ == "__main__":
    diagnostic = PDFDiagnostic()
    results = diagnostic.diagnose_all_pdfs()
    
    print(f"\n{'='*60}")
    print(f"DIAGNOSTIC COMPLETE")
    print(f"Analyzed {len(results)} PDF file(s)")
    print(f"{'='*60}")

