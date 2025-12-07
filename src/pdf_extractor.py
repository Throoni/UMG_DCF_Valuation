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
    
    # Comprehensive heading variants for income statement
    INCOME_STATEMENT_HEADING_VARIANTS = [
        r'statement of profit or loss',
        r'statement of profit or loss and other comprehensive income',
        r'consolidated statement of operations',
        r'consolidated statement of earnings',
        r'income statement',
        r'interim statement of profit or loss',
        r'condensed consolidated interim statement of profit or loss',
        r'statement of operations',
        r'statement of earnings',
        r'profit and loss',
        r'profit or loss',
        r'consolidated income statement',
        r'consolidated statement of profit or loss',
    ]
    
    # Required line items for income statement validation
    INCOME_STATEMENT_LINE_ITEMS = [
        'revenue', 'revenues', 'sales', 'net revenue', 'total revenue',
        'cost of revenue', 'cost of sales', 'cost of goods sold', 'cost of goods and services',
        'gross profit',
        'operating income', 'operating profit', 'ebit', 'operating earnings',
        'ebitda',
        'net income', 'net earnings', 'profit for the year', 'profit attributable',
        'earnings per share', 'eps', 'basic earnings per share',
    ]
    
    # Comprehensive heading variants for balance sheet
    BALANCE_SHEET_HEADING_VARIANTS = [
        r'statement of financial position',
        r'consolidated statement of financial position',
        r'balance sheet',
        r'consolidated balance sheet',
        r'statement of financial condition',
    ]
    
    # Required line items for balance sheet validation
    BALANCE_SHEET_LINE_ITEMS = [
        'total assets',
        'total current assets', 'current assets',
        'total liabilities', 'total liabilities and equity',
        'total current liabilities', 'current liabilities',
        'shareholders equity', 'stockholders equity', 'total equity',
        'total debt', 'long term debt', 'short term debt',
        'cash and cash equivalents', 'cash and cash equivalents at end of period',
    ]
    
    # Comprehensive heading variants for cash flow
    CASH_FLOW_HEADING_VARIANTS = [
        r'statement of cash flows',
        r'consolidated statement of cash flows',
        r'cash flow statement',
        r'statement of cash flow',
        r'cash flows',
    ]
    
    # Required line items for cash flow validation
    CASH_FLOW_LINE_ITEMS = [
        'operating activities', 'cash from operating activities', 'cash flows from operating activities',
        'investing activities', 'cash from investing activities', 'cash flows from investing activities',
        'financing activities', 'cash from financing activities', 'cash flows from financing activities',
        'capital expenditures', 'capex', 'purchase of property, plant and equipment',
        'net change in cash', 'net increase in cash', 'net decrease in cash',
    ]
    
    def __init__(self, verbose: bool = False):
        """Initialize PDF extractor
        
        Args:
            verbose: If True, print detailed debug information during extraction
        """
        self.extracted_data = {}
        self.verbose = verbose
    
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
        
        # Search for income statement table with comprehensive keywords
        heading_keywords = self.INCOME_STATEMENT_HEADING_VARIANTS
        line_item_keywords = self.INCOME_STATEMENT_LINE_ITEMS
        
        result = self._find_financial_statement_table(
            tables, text, 
            heading_keywords=heading_keywords,
            line_item_keywords=line_item_keywords,
            statement_type='income statement'
        )
        
        if result is None:
            # Try text-based fallback parser
            if self.verbose:
                print(f"    Table extraction failed, trying text-based parser...")
            text_df = self._parse_text_based_statement(
                text, heading_keywords, line_item_keywords, 'income statement', year
            )
            if text_df is not None and not text_df.empty:
                if self.verbose:
                    print(f"    ✓ Extracted income statement using text-based parser ({len(text_df.columns)} line items)")
                return text_df
            
            if self.verbose:
                print(f"    Could not find income statement in PDF")
                print(f"      Searched for headings matching: {', '.join(heading_keywords[:3])}...")
                print(f"      Required line items: revenue, cost of revenue, net income, etc.")
            else:
                print(f"    Could not find income statement in PDF")
            return None
        
        income_table, confidence, debug_info = result
        
        if self.verbose and debug_info:
            print(f"    Income statement detection: {debug_info}")
        
        if confidence < 0.35:
            if self.verbose:
                print(f"    Warning: Low confidence score ({confidence:.2f}) for income statement")
            # Reject very low confidence extractions to avoid wrong tables
            if confidence < 0.25:
                if self.verbose:
                    print(f"    Rejecting extraction due to very low confidence ({confidence:.2f})")
                return None
        
        # Parse the table
        df = self._parse_table_to_dataframe(income_table)
        
        if df is not None and not df.empty:
            # Standardize column names
            df = self._standardize_income_statement(df)
            # Add Date column instead of Year for consistency
            df['Date'] = pd.Timestamp(year=year, month=12, day=31)
            if 'Year' in df.columns:
                df = df.drop('Year', axis=1)
            print(f"    Extracted income statement with {len(df)} line items (confidence: {confidence:.2f})")
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
        
        # Search for balance sheet table with comprehensive keywords
        heading_keywords = self.BALANCE_SHEET_HEADING_VARIANTS
        line_item_keywords = self.BALANCE_SHEET_LINE_ITEMS
        
        result = self._find_financial_statement_table(
            tables, text,
            heading_keywords=heading_keywords,
            line_item_keywords=line_item_keywords,
            statement_type='balance sheet'
        )
        
        if result is None:
            # Try text-based fallback parser
            if self.verbose:
                print(f"    Table extraction failed, trying text-based parser...")
            text_df = self._parse_text_based_statement(
                text, heading_keywords, line_item_keywords, 'balance sheet', year
            )
            if text_df is not None and not text_df.empty:
                if self.verbose:
                    print(f"    ✓ Extracted balance sheet using text-based parser ({len(text_df.columns)} line items)")
                return text_df
            
            if self.verbose:
                print(f"    Could not find balance sheet in PDF")
                print(f"      Searched for headings matching: {', '.join(heading_keywords[:3])}...")
                print(f"      Required line items: total assets, total liabilities, shareholders equity, etc.")
            else:
                print(f"    Could not find balance sheet in PDF")
            return None
        
        balance_table, confidence, debug_info = result
        
        if self.verbose and debug_info:
            print(f"    Balance sheet detection: {debug_info}")
        
        if confidence < 0.35:
            if self.verbose:
                print(f"    Warning: Low confidence score ({confidence:.2f}) for balance sheet")
            # Reject very low confidence extractions to avoid wrong tables
            if confidence < 0.25:
                if self.verbose:
                    print(f"    Rejecting extraction due to very low confidence ({confidence:.2f})")
                return None
        
        # Parse the table
        df = self._parse_table_to_dataframe(balance_table)
        
        if df is not None and not df.empty:
            # Standardize column names
            df = self._standardize_balance_sheet(df)
            # Add Date column instead of Year for consistency
            df['Date'] = pd.Timestamp(year=year, month=12, day=31)
            if 'Year' in df.columns:
                df = df.drop('Year', axis=1)
            print(f"    Extracted balance sheet with {len(df)} line items (confidence: {confidence:.2f})")
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
        
        # Search for cash flow statement table with comprehensive keywords
        heading_keywords = self.CASH_FLOW_HEADING_VARIANTS
        line_item_keywords = self.CASH_FLOW_LINE_ITEMS
        
        result = self._find_financial_statement_table(
            tables, text,
            heading_keywords=heading_keywords,
            line_item_keywords=line_item_keywords,
            statement_type='cash flow'
        )
        
        if result is None:
            # Try text-based fallback parser
            if self.verbose:
                print(f"    Table extraction failed, trying text-based parser...")
            text_df = self._parse_text_based_statement(
                text, heading_keywords, line_item_keywords, 'cash flow', year
            )
            if text_df is not None and not text_df.empty:
                if self.verbose:
                    print(f"    ✓ Extracted cash flow statement using text-based parser ({len(text_df.columns)} line items)")
                return text_df
            
            if self.verbose:
                print(f"    Could not find cash flow statement in PDF")
                print(f"      Searched for headings matching: {', '.join(heading_keywords[:3])}...")
                print(f"      Required line items: operating activities, investing activities, financing activities, etc.")
            else:
                print(f"    Could not find cash flow statement in PDF")
            return None
        
        cashflow_table, confidence, debug_info = result
        
        if self.verbose and debug_info:
            print(f"    Cash flow detection: {debug_info}")
        
        if confidence < 0.35:
            if self.verbose:
                print(f"    Warning: Low confidence score ({confidence:.2f}) for cash flow")
            # Reject very low confidence extractions to avoid wrong tables
            if confidence < 0.25:
                if self.verbose:
                    print(f"    Rejecting extraction due to very low confidence ({confidence:.2f})")
                return None
        
        # Parse the table
        df = self._parse_table_to_dataframe(cashflow_table)
        
        if df is not None and not df.empty:
            # Standardize column names
            df = self._standardize_cash_flow(df)
            # Add Date column instead of Year for consistency
            df['Date'] = pd.Timestamp(year=year, month=12, day=31)
            if 'Year' in df.columns:
                df = df.drop('Year', axis=1)
            print(f"    Extracted cash flow statement with {len(df)} line items (confidence: {confidence:.2f})")
            return df
        
        return None
    
    def _parse_text_based_statement(self, text: List[Dict], 
                                    heading_keywords: List[str],
                                    line_item_keywords: List[str],
                                    statement_type: str,
                                    year: int) -> Optional[pd.DataFrame]:
        """
        Fallback parser: Extract financial statement from text when table extraction fails
        
        This handles cases where pdfplumber.extract_tables() doesn't correctly
        identify multi-column tables (e.g., when it only extracts one column).
        
        Args:
            text: List of page text dictionaries
            heading_keywords: Keywords to identify statement headings
            line_item_keywords: Keywords for line items
            statement_type: Type of statement
            year: Year of the report
            
        Returns:
            DataFrame with extracted statement, or None if not found
        """
        # Find page with heading
        target_page = None
        for page_data in text:
            page_text = page_data.get('text', '').lower()
            for keyword_pattern in heading_keywords:
                if re.search(keyword_pattern, page_text, re.IGNORECASE):
                    target_page = page_data
                    break
            if target_page:
                break
        
        if not target_page:
            return None
        
        # Extract lines from the target page
        page_text = target_page.get('text', '')
        lines = page_text.split('\n')
        
        # Find the section with line items
        # Look for lines that contain both line item keywords and numbers
        statement_lines = []
        in_statement_section = False
        
        for i, line in enumerate(lines):
            line_lower = line.lower()
            
            # Check if we've entered the statement section
            if not in_statement_section:
                for keyword_pattern in heading_keywords:
                    if re.search(keyword_pattern, line_lower, re.IGNORECASE):
                        in_statement_section = True
                        break
                continue
            
            # Check if we've left the statement section (hit next major heading)
            if in_statement_section:
                # Stop if we hit another major financial statement heading
                # But be more careful - only stop if it's clearly a new section
                other_headings = []
                if statement_type == 'income statement':
                    other_headings = self.BALANCE_SHEET_HEADING_VARIANTS + self.CASH_FLOW_HEADING_VARIANTS
                elif statement_type == 'balance sheet':
                    other_headings = self.CASH_FLOW_HEADING_VARIANTS
                
                if other_headings and any(re.search(pattern, line_lower, re.IGNORECASE) 
                       for pattern in other_headings):
                    # Check if this looks like a real heading (all caps or title case, standalone)
                    if (line_stripped.isupper() or line_stripped.istitle()) and len(statement_lines) > 5:
                        break
                
                # Check if line contains a line item keyword and numbers
                has_keyword = any(kw in line_lower for kw in line_item_keywords)
                has_number = bool(re.search(r'[\d,()]+', line))  # Has digits, commas, parentheses
                
                # For balance sheet, also look for common patterns like "TOTAL ASSETS" or "Total equity"
                if statement_type == 'balance sheet':
                    balance_patterns = [
                        r'\btotal\s+(assets|liabilities|equity)\b',
                        r'\b(cash|equity|debt|assets|liabilities)\b.*\d',
                        r'\b(goodwill|intangible|receivable|payable)\b.*\d',
                    ]
                    has_keyword = has_keyword or any(re.search(p, line_lower, re.IGNORECASE) for p in balance_patterns)
                
                # For cash flow, look for activity patterns
                if statement_type == 'cash flow':
                    cashflow_patterns = [
                        r'\b(operating|investing|financing)\s+activities\b',
                        r'\b(capital\s+expenditures?|capex)\b',
                        r'\bnet\s+change\s+in\s+cash\b',
                    ]
                    has_keyword = has_keyword or any(re.search(p, line_lower, re.IGNORECASE) for p in cashflow_patterns)
                
                if has_keyword and has_number:
                    statement_lines.append(line)
                elif has_number and len(statement_lines) > 0:
                    # Continue collecting lines with numbers (might be continuation or subtotals)
                    statement_lines.append(line)
                elif not has_number and len(statement_lines) > 5:
                    # Stop if we hit non-numeric lines after collecting data
                    break
        
        if not statement_lines:
            return None
        
        # Parse lines into structured data
        # Format is typically: "Line Item Note Value1 Value2"
        parsed_data = []
        
        for line in statement_lines:
            # Split line into components
            # Pattern: text (line item) + optional note number + numbers (values)
            parts = line.split()
            if len(parts) < 2:
                continue
            
            # Find where numbers start (usually after line item name and optional note)
            number_start_idx = None
            for i, part in enumerate(parts):
                # Check if part is a number (with formatting)
                cleaned = part.replace(',', '').replace('(', '').replace(')', '').replace('€', '').replace('$', '')
                if cleaned.replace('-', '').replace('.', '').isdigit():
                    number_start_idx = i
                    break
            
            if number_start_idx is None:
                continue
            
            # Line item name is everything before the numbers (excluding note if it's a single digit)
            line_item_parts = parts[:number_start_idx]
            # Remove note numbers (single digits or "Note X")
            line_item_parts = [p for p in line_item_parts 
                             if not (p.isdigit() and len(p) <= 2) 
                             and not p.lower().startswith('note')
                             and not p.lower() in ['3', '5', '7', '9', '10', '13', '17', '20']]  # Common note references
            
            if not line_item_parts:
                continue
            
            line_item = ' '.join(line_item_parts).strip()
            
            # Clean up common patterns
            # Remove trailing "Note" references
            line_item = re.sub(r'\s+note\s+\d+$', '', line_item, flags=re.IGNORECASE)
            # Handle "TOTAL" prefix (common in balance sheets)
            if line_item.upper().startswith('TOTAL '):
                line_item = line_item[6:].strip()
                line_item = 'Total ' + line_item
            values = parts[number_start_idx:]
            
            # Parse values (handle negative numbers in parentheses)
            parsed_values = []
            for val_str in values:
                # Remove commas, currency symbols
                cleaned = val_str.replace(',', '').replace('€', '').replace('$', '').strip()
                # Handle negative in parentheses: (123) -> -123
                if cleaned.startswith('(') and cleaned.endswith(')'):
                    cleaned = '-' + cleaned[1:-1]
                
                try:
                    num_val = float(cleaned)
                    parsed_values.append(num_val)
                except ValueError:
                    break  # Stop if we hit non-numeric value
            
            if parsed_values:
                # Use the first value (current year) or the value for the target year
                # For now, use first value
                parsed_data.append({
                    'Line Item': line_item,
                    'Value': parsed_values[0] if parsed_values else None
                })
        
        if not parsed_data:
            return None
        
        # Convert to DataFrame
        df = pd.DataFrame(parsed_data)
        
        # Map line items to standard names
        df = self._map_line_items_to_standard(df, statement_type)
        
        # Convert to wide format (line items as columns, single row with Date)
        wide_df = pd.DataFrame()
        wide_df['Date'] = [pd.Timestamp(year=year, month=12, day=31)]
        
        for _, row in df.iterrows():
            line_item = row['Line Item']
            value = row['Value']
            if pd.notna(value):
                wide_df[line_item] = [value]
        
        return wide_df
    
    def _map_line_items_to_standard(self, df: pd.DataFrame, statement_type: str) -> pd.DataFrame:
        """
        Map extracted line items to standard names based on statement type
        """
        if statement_type == 'income statement':
            mapping = {
                'revenues': 'Revenue',
                'revenue': 'Revenue',
                'cost of revenues': 'Cost of Revenue',
                'cost of revenue': 'Cost of Revenue',
                'gross profit': 'Gross Profit',
                'operating profit': 'EBIT',
                'operating income': 'EBIT',
                'ebit': 'EBIT',
                'ebitda': 'EBITDA',
                'net income': 'Net Income',
                'net profit': 'Net Income',
                'profit for the year': 'Net Income',
                'profit attributable': 'Net Income',
                'income taxes': 'Income Tax Expense',
                'income tax expense': 'Income Tax Expense',
                'tax expense': 'Income Tax Expense',
            }
        elif statement_type == 'balance sheet':
            mapping = {
                'total assets': 'Total Assets',
                'assets': 'Total Assets',
                'total liabilities': 'Total Liabilities',
                'liabilities': 'Total Liabilities',
                'total equity': 'Total Equity',
                'equity': 'Total Equity',
                'shareholders equity': 'Total Equity',
                'shareowners equity': 'Total Equity',
                'stockholders equity': 'Total Equity',
                'total equity and liabilities': 'Total Equity',
                'current assets': 'Current Assets',
                'current liabilities': 'Current Liabilities',
                'total debt': 'Total Debt',
                'debt': 'Total Debt',
                'cash and cash equivalents': 'Cash and Cash Equivalents',
                'cash': 'Cash and Cash Equivalents',
                'goodwill': 'Goodwill',
                'intangible assets': 'Intangible Assets',
                'property plant and equipment': 'PP&E',
                'accounts receivable': 'Accounts Receivable',
                'receivables': 'Accounts Receivable',
                'inventory': 'Inventory',
                'accounts payable': 'Accounts Payable',
                'deferred tax assets': 'Deferred Tax Assets',
                'deferred tax liabilities': 'Deferred Tax Liabilities',
                'long term debt': 'Long Term Debt',
                'short term debt': 'Short Term Debt',
            }
        else:  # cash flow
            mapping = {
                'cash from operating activities': 'Operating Cash Flow',
                'operating activities': 'Operating Cash Flow',
                'cash flows from operating activities': 'Operating Cash Flow',
                'cash from investing activities': 'Investing Cash Flow',
                'investing activities': 'Investing Cash Flow',
                'cash flows from investing activities': 'Investing Cash Flow',
                'cash from financing activities': 'Financing Cash Flow',
                'financing activities': 'Financing Cash Flow',
                'cash flows from financing activities': 'Financing Cash Flow',
                'capital expenditures': 'Capital Expenditures',
                'capex': 'Capital Expenditures',
                'purchase of property plant and equipment': 'Capital Expenditures',
                'net change in cash': 'Net Change in Cash',
                'increase decrease in cash': 'Net Change in Cash',
                'cash at beginning of period': 'Beginning Cash',
                'cash at end of period': 'Ending Cash',
                'cash and cash equivalents at beginning': 'Beginning Cash',
                'cash and cash equivalents at end': 'Ending Cash',
            }
        
        # Apply mapping (case-insensitive)
        df['Line Item'] = df['Line Item'].apply(
            lambda x: mapping.get(x.lower().strip(), x)
        )
        
        return df
    
    def _find_financial_statement_table(self, tables: List[Dict],
                                        text: List[Dict],
                                        heading_keywords: List[str],
                                        line_item_keywords: List[str],
                                        statement_type: str) -> Optional[Tuple[List, float, str]]:
        """
        Find the table that matches financial statement keywords with enhanced detection
        
        Args:
            tables: List of extracted tables with page numbers
            text: List of extracted text blocks with page numbers
            heading_keywords: List of regex patterns for statement headings
            line_item_keywords: List of keywords for required line items
            statement_type: Type of statement ('income statement', 'balance sheet', 'cash flow')
        
        Returns:
            Tuple of (table, confidence_score, debug_info) or None if not found
        """
        # Step 1: Find all candidate headings
        candidates = self._find_statement_headings(text, heading_keywords, statement_type)
        
        if self.verbose:
            print(f"    Found {len(candidates)} candidate heading(s) for {statement_type}:")
            for cand in candidates:
                print(f"      - Page {cand['page']}: '{cand['heading']}'")
        
        if not candidates:
            debug_msg = f"No headings found matching {statement_type} patterns"
            if self.verbose:
                print(f"    {debug_msg}")
            # Try searching all tables without heading match
            return self._search_all_tables(tables, line_item_keywords, statement_type, debug_msg)
        
        # Step 2: For each candidate heading, find and score tables on that page
        best_table = None
        best_score = 0.0
        best_debug = ""
        
        for candidate in candidates:
            page = candidate['page']
            heading_text = candidate['heading']
            
            # Find tables on this page
            page_tables = [t for t in tables if t['page'] == page]
            
            if not page_tables:
                if self.verbose:
                    print(f"      Found heading '{heading_text}' on page {page} but no table below it")
                continue
            
            # Score each table on this page
            # Prioritize tables that appear after the heading (usually the first table on the page)
            for idx, table_info in enumerate(page_tables):
                table = table_info['table']
                is_valid, confidence = self._is_financial_statement_table(
                    table, line_item_keywords, statement_type
                )
                
                # Boost confidence if this is the first table on the page (likely the main statement)
                if idx == 0 and is_valid:
                    confidence = min(confidence * 1.2, 1.0)  # Boost by 20% but cap at 1.0
                
                if is_valid and confidence > best_score:
                    best_table = table
                    best_score = confidence
                    best_debug = f"Found on page {page} under heading '{heading_text}' (confidence: {confidence:.2f})"
                    
                    if self.verbose:
                        print(f"      ✓ Selected table on page {page} (confidence: {confidence:.2f})")
        
        # Step 3: If no table found via headings, search all tables
        if best_table is None:
            debug_msg = f"Found {len(candidates)} heading(s) but no valid table below them"
            if self.verbose:
                print(f"    {debug_msg}")
                for cand in candidates:
                    page = cand['page']
                    page_tables = [t for t in tables if t['page'] == page]
                    if page_tables:
                        print(f"      Page {page} has {len(page_tables)} table(s) but none matched criteria")
                    else:
                        print(f"      Page {page} has no tables")
            return self._search_all_tables(tables, line_item_keywords, statement_type, debug_msg)
        
        return (best_table, best_score, best_debug)
    
    def _search_all_tables(self, tables: List[Dict], line_item_keywords: List[str],
                          statement_type: str, debug_msg: str) -> Optional[Tuple[List, float, str]]:
        """Search all tables when heading-based search fails"""
        best_table = None
        best_score = 0.0
        
        for table_info in tables:
            table = table_info['table']
            is_valid, confidence = self._is_financial_statement_table(
                table, line_item_keywords, statement_type
            )
            
            if is_valid and confidence > best_score:
                best_table = table
                best_score = confidence
        
        if best_table is not None:
            return (best_table, best_score, f"Searched all tables, found match (confidence: {best_score:.2f})")
        else:
            if self.verbose:
                print(f"    {debug_msg}")
                print(f"    Searched all {len(tables)} tables but none matched {statement_type} criteria")
                print(f"    Required line items not found or insufficient period columns detected")
            else:
                print(f"    {debug_msg}")
            return None
    
    def _find_statement_headings(self, text: List[Dict], 
                                heading_patterns: List[str],
                                statement_type: str) -> List[Dict]:
        """
        Find all headings that match statement name variants
        
        Args:
            text: List of text blocks with page numbers
            heading_patterns: List of regex patterns for statement headings
            statement_type: Type of statement for logging
        
        Returns:
            List of candidate headings with page numbers and heading text
        """
        candidates = []
        
        for text_block in text:
            page = text_block['page']
            text_content = text_block['text']
            
            # Split text into lines to find headings (usually on separate lines)
            lines = text_content.split('\n')
            
            for i, line in enumerate(lines):
                line_stripped = line.strip()
                if not line_stripped:
                    continue
                    
                line_lower = line_stripped.lower()
                
                # Check if line matches any heading pattern
                for pattern in heading_patterns:
                    # Compile regex pattern (case-insensitive)
                    regex = re.compile(pattern, re.IGNORECASE)
                    match = regex.search(line_lower)
                    if match:
                        # Found a match - check if it looks like a heading
                        # Headings are usually:
                        # - Short (less than 150 chars, more than 5)
                        # - Not obviously part of a sentence (avoid lines with sentence connectors at start)
                        # - Often standalone or at start of line
                        line_length = len(line_stripped)
                        
                        # Basic length check
                        if line_length < 5 or line_length > 150:
                            continue
                        
                        # Check if it's likely a heading vs part of a sentence
                        # Headings often:
                        # - Start with the pattern (or close to it)
                        # - Are in all caps or title case
                        # - Don't start with lowercase articles/prepositions
                        starts_with_article = line_lower.startswith(('the ', 'a ', 'an ', 'this ', 'that '))
                        is_upper_or_title = line_stripped.isupper() or line_stripped.istitle()
                        pattern_at_start = match.start() < 20  # Pattern appears early in line
                        
                        # Exclude obvious sentence fragments
                        is_sentence_fragment = (
                            starts_with_article and not is_upper_or_title and not pattern_at_start
                        ) or (
                            line_lower.count('.') > 2 or  # Too many periods (likely paragraph)
                            (line_lower.count(',') > 3 and not is_upper_or_title)  # Too many commas
                        )
                        
                        if not is_sentence_fragment:
                            candidates.append({
                                'page': page,
                                'heading': line_stripped,
                                'line_number': i,
                                'statement_type': statement_type
                            })
                            break  # Don't match same line with multiple patterns
        
        return candidates
    
    def _is_financial_statement_table(self, table: List[List], 
                                     line_item_keywords: List[str],
                                     statement_type: str) -> Tuple[bool, float]:
        """
        Check if a table looks like a financial statement with confidence scoring
        
        Args:
            table: Table data as list of lists
            line_item_keywords: List of keywords for required line items
            statement_type: Type of statement being validated
        
        Returns:
            Tuple of (is_valid, confidence_score) where confidence is 0.0-1.0
        """
        if not table or len(table) < 3:
            return (False, 0.0)
        
        # Combine all table text for searching (check more rows for better detection)
        table_text = ' '.join([
            ' '.join([str(cell) if cell else '' for cell in row])
            for row in table[:15]  # Check first 15 rows for better coverage
        ]).lower()
        
        # Check for required line items
        found_items = []
        for keyword in line_item_keywords:
            if keyword.lower() in table_text:
                found_items.append(keyword)
        
        # Calculate confidence based on how many required items are found
        # Use a more lenient approach: require fewer items but weight them
        required_count = min(len(line_item_keywords), 3)  # Require at least 3 key items for validation
        found_count = len(found_items)
        
        if found_count == 0:
            return (False, 0.0)
        
        # Base confidence from line items (0.0 to 0.7)
        # More lenient: if we find at least 2 items, give some confidence
        if found_count >= 2:
            line_item_confidence = min(found_count / max(required_count, 2), 1.0) * 0.7
        else:
            line_item_confidence = (found_count / 2.0) * 0.35  # Partial credit for 1 item
        
        # Check for period columns (years/dates) - adds up to 0.3
        period_confidence = self._check_period_columns(table) * 0.3
        
        total_confidence = line_item_confidence + period_confidence
        
        # Threshold: must have at least 2 line items and reasonable confidence
        # Balance between being too strict (misses valid tables) and too lenient (gets wrong tables)
        is_valid = (
            found_count >= 2 and total_confidence >= 0.30
        ) or (
            found_count >= 3 and total_confidence >= 0.25
        ) or (
            found_count >= 2 and period_confidence > 0.10 and total_confidence >= 0.28
        )
        
        return (is_valid, total_confidence)
    
    def _check_period_columns(self, table: List[List]) -> float:
        """
        Check if table has columns that look like periods/years
        
        Returns:
            Confidence score (0.0-1.0) for period column detection
        """
        if not table or len(table) < 2:
            return 0.0
        
        # Check header rows (first 2 rows typically)
        headers = []
        for row in table[:2]:
            headers.extend([str(cell).strip() if cell else '' for cell in row])
        
        period_indicators = 0
        total_headers = len([h for h in headers if h])
        
        if total_headers == 0:
            return 0.0
        
        # Look for year patterns (4-digit years)
        year_pattern = re.compile(r'\b(19|20)\d{2}\b')
        # Look for period patterns (months, quarters, "ended", etc.)
        period_pattern = re.compile(r'(january|february|march|april|may|june|july|august|september|october|november|december|q[1-4]|quarter|ended|period)', re.IGNORECASE)
        
        for header in headers:
            header_lower = header.lower()
            if year_pattern.search(header):
                period_indicators += 1
            elif period_pattern.search(header_lower):
                period_indicators += 1
            elif self._looks_like_number(header) and len(header) == 4:
                # Might be a year
                try:
                    year = int(header)
                    if 1900 <= year <= 2100:
                        period_indicators += 1
                except:
                    pass
        
        # Confidence based on how many headers look like periods
        return min(period_indicators / max(total_headers, 1), 1.0)
    
    def _parse_table_to_dataframe(self, table: List[List]) -> Optional[pd.DataFrame]:
        """
        Convert extracted table to DataFrame with improved structure detection
        
        Handles:
        - Multi-row headers (e.g., "Year ended December 31" spanning rows)
        - Line item column detection (usually first column with text)
        - Period column detection (columns with years/dates)
        """
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
            
            # Detect header rows and data start
            header_end, data_start = self._detect_table_structure(cleaned_table)
            
            # Extract headers (may span multiple rows)
            if header_end >= 0:
                headers = self._extract_headers(cleaned_table[:header_end+1])
            else:
                headers = cleaned_table[0] if cleaned_table else []
            
            # Extract data rows
            data_rows = cleaned_table[data_start:] if data_start < len(cleaned_table) else []
            
            if not data_rows:
                return None
            
            # Ensure headers match number of columns
            max_cols = max(len(row) for row in data_rows) if data_rows else 0
            if len(headers) < max_cols:
                headers.extend([f'Column_{i}' for i in range(len(headers), max_cols)])
            elif len(headers) > max_cols:
                headers = headers[:max_cols]
            
            # Create DataFrame
            df = pd.DataFrame(data_rows, columns=headers[:max_cols])
            
            return df
        
        except Exception as e:
            print(f"    Error parsing table: {e}")
            return None
    
    def _detect_table_structure(self, cleaned_table: List[List]) -> Tuple[int, int]:
        """
        Detect where headers end and data starts
        
        Returns:
            Tuple of (header_end_row_index, data_start_row_index)
        """
        if len(cleaned_table) < 2:
            return (0, 1)
        
        # Check first few rows to identify header vs data
        header_end = 0
        data_start = 1
        
        # Look for patterns indicating header rows:
        # - Contain year/period patterns but not many numbers
        # - Contain words like "Note", "€", "millions", "thousands"
        # - Second row might be sub-header with units or additional period info
        
        year_pattern = re.compile(r'\b(19|20)\d{2}\b')
        period_keywords = ['note', '€', 'euros', 'millions', 'thousands', 'in millions', 
                          'january', 'february', 'march', 'april', 'may', 'june',
                          'july', 'august', 'september', 'october', 'november', 'december',
                          'ended', 'period', 'year']
        
        for i in range(min(3, len(cleaned_table))):
            row = cleaned_table[i]
            row_text = ' '.join(row).lower()
            
            # Count numeric values in row
            numeric_count = sum(1 for cell in row if self._looks_like_number(cell))
            
            # Check if row looks like a header (has period indicators but few numbers)
            has_period_indicator = year_pattern.search(' '.join(row)) or \
                                  any(kw in row_text for kw in period_keywords)
            
            if has_period_indicator and numeric_count < len(row) * 0.3:
                # Likely a header row
                header_end = i
                data_start = i + 1
            elif numeric_count > len(row) * 0.5:
                # Row has many numbers, likely data
                if i > 0:
                    header_end = i - 1
                    data_start = i
                break
        
        return (header_end, data_start)
    
    def _extract_headers(self, header_rows: List[List]) -> List[str]:
        """
        Extract headers from potentially multi-row header structure
        
        Handles cases where:
        - First row has period names, second row has units
        - Headers span multiple rows with merged cells
        """
        if not header_rows:
            return []
        
        if len(header_rows) == 1:
            return header_rows[0]
        
        # For multi-row headers, combine intelligently
        # Usually: first row has periods, second row has units/notes
        # Use the row with more non-empty cells as base
        base_row_idx = 0
        max_non_empty = sum(1 for cell in header_rows[0] if cell)
        
        for i, row in enumerate(header_rows[1:], 1):
            non_empty = sum(1 for cell in row if cell)
            if non_empty > max_non_empty:
                max_non_empty = non_empty
                base_row_idx = i
        
        base_row = header_rows[base_row_idx]
        
        # Combine with other rows if they add useful info
        for i, row in enumerate(header_rows):
            if i == base_row_idx:
                continue
            
            # Merge: if base cell is empty but this row has value, use this row's value
            for j, cell in enumerate(row):
                if j < len(base_row):
                    if not base_row[j] and cell:
                        base_row[j] = cell
                    elif base_row[j] and cell and len(cell) < len(base_row[j]):
                        # Shorter text might be unit/note, append it
                        base_row[j] = f"{base_row[j]} {cell}".strip()
        
        return base_row
    
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
    
    def extract_all_statements(self, pdf_path: str, year: int, verbose: Optional[bool] = None) -> Dict:
        """
        Extract all financial statements from a PDF
        
        Args:
            pdf_path: Path to PDF file
            year: Year of the report
            verbose: Override verbose mode for this extraction (uses instance default if None)
        
        Returns:
            Dictionary with income_statement, balance_sheet, cash_flow DataFrames
        """
        # Temporarily set verbose mode if provided
        original_verbose = self.verbose
        if verbose is not None:
            self.verbose = verbose
        
        try:
            pdf_data = self.extract_financial_tables(pdf_path)
            
            if not pdf_data:
                return {}
            
            if self.verbose:
                print(f"    Extracted {len(pdf_data.get('tables', []))} table(s) from PDF")
                print(f"    Processing {len(pdf_data.get('text', []))} page(s) of text")
            
            results = {}
            
            # Extract each statement
            if self.verbose:
                print(f"    Searching for income statement...")
            income_stmt = self.parse_income_statement(pdf_data, year)
            if income_stmt is not None:
                results['income_statement'] = income_stmt
            
            if self.verbose:
                print(f"    Searching for balance sheet...")
            balance_sheet = self.parse_balance_sheet(pdf_data, year)
            if balance_sheet is not None:
                results['balance_sheet'] = balance_sheet
            
            if self.verbose:
                print(f"    Searching for cash flow statement...")
            cash_flow = self.parse_cash_flow(pdf_data, year)
            if cash_flow is not None:
                results['cash_flow'] = cash_flow
            
            if self.verbose:
                print(f"    Extraction complete: {len(results)} statement(s) found")
            
            return results
        finally:
            # Restore original verbose mode
            self.verbose = original_verbose
    
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

