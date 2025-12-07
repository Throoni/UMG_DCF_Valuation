"""
Data validation utilities for financial data
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple


def validate_financial_data(df: pd.DataFrame, required_columns: List[str]) -> Tuple[bool, List[str]]:
    """
    Validate that financial data contains required columns and has valid values
    
    Args:
        df: DataFrame to validate
        required_columns: List of required column names
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    # Check for required columns
    missing_columns = set(required_columns) - set(df.columns)
    if missing_columns:
        errors.append(f"Missing required columns: {missing_columns}")
    
    # Check for NaN values in required columns
    for col in required_columns:
        if col in df.columns:
            nan_count = df[col].isna().sum()
            if nan_count > 0:
                errors.append(f"Column {col} has {nan_count} NaN values")
    
    # Check for negative values where inappropriate
    positive_only_columns = ['Revenue', 'Total Assets', 'Total Equity']
    for col in positive_only_columns:
        if col in df.columns:
            negative_count = (df[col] < 0).sum()
            if negative_count > 0:
                errors.append(f"Column {col} has {negative_count} negative values")
    
    return len(errors) == 0, errors


def validate_accounting_identity(balance_sheet: pd.DataFrame) -> Tuple[bool, List[str]]:
    """
    Validate accounting identity: Assets = Liabilities + Equity
    
    Args:
        balance_sheet: DataFrame with balance sheet data
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    required_cols = ['Total Assets', 'Total Liabilities', 'Total Equity']
    if not all(col in balance_sheet.columns for col in required_cols):
        return False, ["Missing required balance sheet columns"]
    
    for idx, row in balance_sheet.iterrows():
        assets = row['Total Assets']
        liabilities = row['Total Liabilities']
        equity = row['Total Equity']
        
        # Allow small rounding differences (0.1% tolerance)
        calculated_equity = assets - liabilities
        if abs(calculated_equity - equity) > abs(assets) * 0.001:
            errors.append(
                f"Accounting identity violation at {idx}: "
                f"Assets ({assets}) != Liabilities ({liabilities}) + Equity ({equity})"
            )
    
    return len(errors) == 0, errors


def validate_cash_flow_identity(cash_flow: pd.DataFrame) -> Tuple[bool, List[str]]:
    """
    Validate cash flow identity: Operating + Investing + Financing = Change in Cash
    
    Args:
        cash_flow: DataFrame with cash flow statement data
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    required_cols = ['Operating Cash Flow', 'Investing Cash Flow', 
                     'Financing Cash Flow', 'Net Change in Cash']
    if not all(col in cash_flow.columns for col in required_cols):
        return False, ["Missing required cash flow columns"]
    
    for idx, row in cash_flow.iterrows():
        operating = row['Operating Cash Flow']
        investing = row['Investing Cash Flow']
        financing = row['Financing Cash Flow']
        net_change = row['Net Change in Cash']
        
        calculated_change = operating + investing + financing
        
        # Allow small rounding differences (0.1% tolerance)
        if abs(calculated_change - net_change) > abs(operating) * 0.001:
            errors.append(
                f"Cash flow identity violation at {idx}: "
                f"Sum ({calculated_change}) != Net Change ({net_change})"
            )
    
    return len(errors) == 0, errors


def validate_growth_consistency(revenue_growth: float, roic: float, 
                                reinvestment_rate: float) -> Tuple[bool, str]:
    """
    Validate that revenue growth is consistent with ROIC and reinvestment rate
    Growth should be <= ROIC × Reinvestment Rate
    
    Args:
        revenue_growth: Projected revenue growth rate
        roic: Return on Invested Capital
        reinvestment_rate: Reinvestment rate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    sustainable_growth = roic * reinvestment_rate
    
    if revenue_growth > sustainable_growth * 1.1:  # 10% tolerance
        return False, (
            f"Revenue growth ({revenue_growth:.2%}) exceeds sustainable growth "
            f"({sustainable_growth:.2%} = ROIC {roic:.2%} × Reinvestment {reinvestment_rate:.2%})"
        )
    
    return True, ""


def validate_wacc_range(wacc: float, min_wacc: float = 0.06, 
                       max_wacc: float = 0.15) -> Tuple[bool, str]:
    """
    Validate that WACC is within reasonable range
    
    Args:
        wacc: Weighted Average Cost of Capital
        min_wacc: Minimum reasonable WACC
        max_wacc: Maximum reasonable WACC
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if wacc < min_wacc:
        return False, f"WACC ({wacc:.2%}) is below minimum reasonable value ({min_wacc:.2%})"
    
    if wacc > max_wacc:
        return False, f"WACC ({wacc:.2%}) is above maximum reasonable value ({max_wacc:.2%})"
    
    return True, ""


def validate_terminal_value_pct(terminal_value: float, total_enterprise_value: float,
                                max_pct: float = 0.70) -> Tuple[bool, str]:
    """
    Validate that terminal value doesn't exceed maximum percentage of total value
    
    Args:
        terminal_value: Present value of terminal value
        total_enterprise_value: Total enterprise value
        max_pct: Maximum percentage allowed
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if total_enterprise_value == 0:
        return False, "Total enterprise value is zero"
    
    tv_pct = terminal_value / total_enterprise_value
    
    if tv_pct > max_pct:
        return False, (
            f"Terminal value ({tv_pct:.1%}) exceeds maximum recommended "
            f"({max_pct:.1%}). Consider extending forecast period."
        )
    
    return True, ""


def validate_terminal_growth_rate(g: float, max_g: float = 0.03) -> Tuple[bool, str]:
    """
    Validate that terminal growth rate doesn't exceed long-term GDP growth
    
    Args:
        g: Terminal growth rate
        max_g: Maximum growth rate (typically long-term GDP growth)
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if g > max_g:
        return False, (
            f"Terminal growth rate ({g:.2%}) exceeds long-term GDP growth ({max_g:.2%}). "
            f"Terminal growth should not exceed sustainable economic growth."
        )
    
    if g < 0:
        return False, f"Terminal growth rate ({g:.2%}) is negative"
    
    return True, ""

