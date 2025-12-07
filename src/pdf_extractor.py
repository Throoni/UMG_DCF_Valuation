"""
PDF Financial Statement Extractor
Extracts financial statements (Income Statement, Balance Sheet, Cash Flow) from PDF reports
"""

import pdfplumber
import pandas as pd
import numpy as np
import os
import re
from typing import Dict, List, Optional, Tuple
import sys

# Add parent directory to path for config import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


class PDFExtractor:
    """Extracts financial statements from PDF reports"""
    
    def __init__(self):
        """Initialize PDF extractor"""
        self.extracted_data = {}
    
    def extract_financial_tables(self, pdf_path: str) -> Dict:
        """
        Extract all tables from a PDF file
        
        Args:
            pdf_path: Path to PDF file
        
        Returns:
            Dictionary with extracted tables and metadata
        """
        if not os.path.exists(pdf_path):
            print(f"    Error: PDF file not found: {pdf_path}")
            return {}
        
        print(f"    Extracting tables from: {os.path.basename(pdf_path)}")
        
        tables = []
        text_content = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    # Extract tables
                    page_tables = page.extract_tables()
                    if page_tables:
                        for table in page_tables:
                            tables.append({
                                'page': page_num,
                                'table': table
                            })
                    
                    # Extract text for searching
                    text = page.extract_text()
                    if text:
                        text_content.append({
                            'page': page_num,
                            'text': text
                        })
        
        except Exception as e:
            print(f"    Error extracting from PDF: {e}")
            return {}
        
        return {
            'tables': tables,
            'text': text_content,
            'file': pdf_path
        }
    
    def parse_income_statement(self, pdf_data: Dict, year: int) -> Optional[pd.DataFrame]:
        """
        Parse income statement from extracted PDF data
        
        Args:
            pdf_data: Dictionary with extracted tables and text
            year: Year of the report
        
        Returns:
            DataFrame with income statement data, or None if not found
        """
        tables = pdf_data.get('tables', [])
        text = pdf_data.get('text', [])
        
        # Search for income statement table
        income_table = self._find_financial_statement_table(
            tables, text, 
            keywords=['income statement', 'statement of operations', 'profit and loss', 
                     'revenue', 'net income', 'operating income']
        )
        
        if not income_table:
            print(f"    Could not find income statement in PDF")
            return None
        
        # Parse the table
        df = self._parse_table_to_dataframe(income_table)
        
        if df is not None and not df.empty:
            # Standardize column names
            df = self._standardize_income_statement(df)
            df['Year'] = year
            print(f"    Extracted income statement with {len(df)} line items")
            return df
        
        return None
    
    def parse_balance_sheet(self, pdf_data: Dict, year: int) -> Optional[pd.DataFrame]:
        """
        Parse balance sheet from extracted PDF data
        
        Args:
            pdf_data: Dictionary with extracted tables and text
            year: Year of the report
        
        Returns:
            DataFrame with balance sheet data, or None if not found
        """
        tables = pdf_data.get('tables', [])
        text = pdf_data.get('text', [])
        
        # Search for balance sheet table
        balance_table = self._find_financial_statement_table(
            tables, text,
            keywords=['balance sheet', 'statement of financial position', 
                     'total assets', 'total liabilities', 'shareholders equity']
        )
        
        if not balance_table:
            print(f"    Could not find balance sheet in PDF")
            return None
        
        # Parse the table
        df = self._parse_table_to_dataframe(balance_table)
        
        if df is not None and not df.empty:
            # Standardize column names
            df = self._standardize_balance_sheet(df)
            df['Year'] = year
            print(f"    Extracted balance sheet with {len(df)} line items")
            return df
        
        return None
    
    def parse_cash_flow(self, pdf_data: Dict, year: int) -> Optional[pd.DataFrame]:
        """
        Parse cash flow statement from extracted PDF data
        
        Args:
            pdf_data: Dictionary with extracted tables and text
            year: Year of the report
        
        Returns:
            DataFrame with cash flow data, or None if not found
        """
        tables = pdf_data.get('tables', [])
        text = pdf_data.get('text', [])
        
        # Search for cash flow statement table
        cashflow_table = self._find_financial_statement_table(
            tables, text,
            keywords=['cash flow', 'statement of cash flows', 
                     'operating activities', 'investing activities', 'financing activities']
        )
        
        if not cashflow_table:
            print(f"    Could not find cash flow statement in PDF")
            return None
        
        # Parse the table
        df = self._parse_table_to_dataframe(cashflow_table)
        
        if df is not None and not df.empty:
            # Standardize column names
            df = self._standardize_cash_flow(df)
            df['Year'] = year
            print(f"    Extracted cash flow statement with {len(df)} line items")
            return df
        
        return None
    
    def _find_financial_statement_table(self, tables: List[Dict], 
                                       text: List[Dict],
                                       keywords: List[str]) -> Optional[List]:
        """Find the table that matches financial statement keywords"""
        # First, search text to find which page has the statement
        relevant_pages = set()
        
        for text_block in text:
            text_lower = text_block['text'].lower()
            if any(keyword.lower() in text_lower for keyword in keywords):
                relevant_pages.add(text_block['page'])
        
        # Look for tables on relevant pages
        for table_info in tables:
            if table_info['page'] in relevant_pages:
                table = table_info['table']
                # Check if table has financial statement characteristics
                if self._is_financial_statement_table(table, keywords):
                    return table
        
        # If not found, try all tables
        for table_info in tables:
            table = table_info['table']
            if self._is_financial_statement_table(table, keywords):
                return table
        
        return None
    
    def _is_financial_statement_table(self, table: List[List], 
                                     keywords: List[str]) -> bool:
        """Check if a table looks like a financial statement"""
        if not table or len(table) < 3:
            return False
        
        # Check first few rows for keywords
        table_text = ' '.join([
            ' '.join([str(cell) if cell else '' for cell in row])
            for row in table[:5]
        ]).lower()
        
        return any(keyword.lower() in table_text for keyword in keywords)
    
    def _parse_table_to_dataframe(self, table: List[List]) -> Optional[pd.DataFrame]:
        """Convert extracted table to DataFrame"""
        if not table:
            return None
        
        try:
            # Clean table data
            cleaned_table = []
            for row in table:
                cleaned_row = [str(cell).strip() if cell else '' for cell in row]
                # Skip completely empty rows
                if any(cell for cell in cleaned_row):
                    cleaned_table.append(cleaned_row)
            
            if not cleaned_table:
                return None
            
            # First row as header (if it looks like headers)
            headers = cleaned_table[0]
            
            # Try to identify data rows (skip header rows)
            data_start = 1
            if len(cleaned_table) > 1:
                # Check if second row looks like data or another header
                second_row = cleaned_table[1]
                if any(self._looks_like_number(cell) for cell in second_row):
                    data_start = 1
                else:
                    data_start = 2
                    headers = second_row  # Use second row as headers
            
            # Create DataFrame
            data_rows = cleaned_table[data_start:]
            
            if not data_rows:
                return None
            
            # Ensure headers match number of columns
            max_cols = max(len(row) for row in data_rows) if data_rows else 0
            if len(headers) < max_cols:
                headers.extend([f'Column_{i}' for i in range(len(headers), max_cols)])
            elif len(headers) > max_cols:
                headers = headers[:max_cols]
            
            df = pd.DataFrame(data_rows, columns=headers[:max_cols])
            
            return df
        
        except Exception as e:
            print(f"    Error parsing table: {e}")
            return None
    
    def _looks_like_number(self, text: str) -> bool:
        """Check if text looks like a number (with currency symbols, commas, etc.)"""
        if not text:
            return False
        
        # Remove common formatting
        cleaned = text.replace(',', '').replace('€', '').replace('$', '').replace('(', '').replace(')', '').strip()
        
        try:
            float(cleaned)
            return True
        except ValueError:
            return False
    
    def _standardize_income_statement(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize income statement column names"""
        # Map common variations to standard names
        column_mapping = {
            'revenue': 'Revenue',
            'total revenue': 'Revenue',
            'net revenue': 'Revenue',
            'sales': 'Revenue',
            'cost of revenue': 'Cost of Revenue',
            'cost of sales': 'Cost of Revenue',
            'gross profit': 'Gross Profit',
            'operating income': 'Operating Income',
            'ebit': 'EBIT',
            'ebitda': 'EBITDA',
            'net income': 'Net Income',
            'net earnings': 'Net Income',
        }
        
        # Rename columns (case-insensitive)
        df.columns = [col.strip() for col in df.columns]
        for old_name, new_name in column_mapping.items():
            df.columns = [new_name if col.lower() == old_name.lower() else col 
                         for col in df.columns]
        
        return df
    
    def _standardize_balance_sheet(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize balance sheet column names"""
        column_mapping = {
            'total assets': 'Total Assets',
            'total current assets': 'Current Assets',
            'total liabilities': 'Total Liabilities',
            'total current liabilities': 'Current Liabilities',
            'total debt': 'Total Debt',
            'shareholders equity': 'Total Equity',
            'stockholders equity': 'Total Equity',
            'cash and cash equivalents': 'Cash and Cash Equivalents',
        }
        
        df.columns = [col.strip() for col in df.columns]
        for old_name, new_name in column_mapping.items():
            df.columns = [new_name if col.lower() == old_name.lower() else col 
                         for col in df.columns]
        
        return df
    
    def _standardize_cash_flow(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize cash flow statement column names"""
        column_mapping = {
            'operating cash flow': 'Operating Cash Flow',
            'cash from operating activities': 'Operating Cash Flow',
            'investing cash flow': 'Investing Cash Flow',
            'cash from investing activities': 'Investing Cash Flow',
            'financing cash flow': 'Financing Cash Flow',
            'cash from financing activities': 'Financing Cash Flow',
            'capital expenditures': 'Capital Expenditures',
            'capex': 'Capital Expenditures',
            'net change in cash': 'Net Change in Cash',
        }
        
        df.columns = [col.strip() for col in df.columns]
        for old_name, new_name in column_mapping.items():
            df.columns = [new_name if col.lower() == old_name.lower() else col 
                         for col in df.columns]
        
        return df
    
    def extract_all_statements(self, pdf_path: str, year: int) -> Dict:
        """
        Extract all financial statements from a PDF
        
        Args:
            pdf_path: Path to PDF file
            year: Year of the report
        
        Returns:
            Dictionary with income_statement, balance_sheet, cash_flow DataFrames
        """
        pdf_data = self.extract_financial_tables(pdf_path)
        
        if not pdf_data:
            return {}
        
        results = {}
        
        # Extract each statement
        income_stmt = self.parse_income_statement(pdf_data, year)
        if income_stmt is not None:
            results['income_statement'] = income_stmt
        
        balance_sheet = self.parse_balance_sheet(pdf_data, year)
        if balance_sheet is not None:
            results['balance_sheet'] = balance_sheet
        
        cash_flow = self.parse_cash_flow(pdf_data, year)
        if cash_flow is not None:
            results['cash_flow'] = cash_flow
        
        return results
    
    def standardize_extracted_data(self, raw_data: Dict, year: int) -> Dict:
        """
        Convert extracted PDF data to standard format matching Yahoo Finance structure
        
        Args:
            raw_data: Dictionary with extracted statements
            year: Year of the data
        
        Returns:
            Standardized data in format compatible with financial_analysis.py
        """
        standardized = {}
        
        for statement_type, df in raw_data.items():
            if df is None or df.empty:
                continue
            
            # Convert to format: Date column + line items as columns
            # Similar to what Yahoo Finance provides after standardization
            standardized_df = pd.DataFrame()
            standardized_df['Date'] = pd.Timestamp(year=year, month=12, day=31)
            
            # Extract numeric values from first data column (usually the year column)
            # This is a simplified approach - in practice, you'd need to handle
            # multiple years if the PDF has comparative data
            
            for col in df.columns:
                if col.lower() not in ['year', 'line item', 'description', 'account']:
                    # Try to extract numeric value
                    if len(df) > 0:
                        # Look for the value in the first numeric column
                        for idx, row in df.iterrows():
                            line_item = str(row.iloc[0]) if len(row) > 0 else ''
                            # Try to find numeric value in this row
                            for val in row[1:]:
                                if self._looks_like_number(str(val)):
                                    # Map line item to standard name if possible
                                    standardized_df[line_item] = self._parse_number(str(val))
                                    break
            
            standardized[statement_type] = standardized_df
        
        return standardized
    
    def _parse_number(self, text: str) -> float:
        """Parse number from text, handling currency symbols and formatting"""
        if not text:
            return 0.0
        
        # Remove formatting
        cleaned = text.replace(',', '').replace('€', '').replace('$', '').strip()
        cleaned = cleaned.replace('(', '-').replace(')', '')  # Negative numbers
        
        try:
            return float(cleaned)
        except ValueError:
            return 0.0


if __name__ == "__main__":
    extractor = PDFExtractor()
    # Example usage would be:
    # pdf_path = "data/raw/ir_documents/annual/UMG_Annual_Report_2024.pdf"
    # results = extractor.extract_all_statements(pdf_path, 2024)
    # print(results)

