"""
Configuration file for UMG DCF Valuation Model
Contains all company-specific settings, data sources, and default assumptions
"""

# Company Information
COMPANY_TICKER = "UMG.AS"
COMPANY_NAME = "Universal Music Group"
EXCHANGE = "Euronext Amsterdam"
SECTOR = "Entertainment"
INDUSTRY = "Music & Media"

# Data Source URLs
INVESTOR_RELATIONS_URL = "https://www.universalmusic.com/investors/"
INVESTOR_RELATIONS_ALT_URL = "https://www.universalmusic.com/investor-relations/"
YAHOO_FINANCE_TICKER = "UMG.AS"

# IR Document Settings
IR_DOCUMENTS_DIR = "data/raw/ir_documents"
IR_ANNUAL_DIR = "data/raw/ir_documents/annual"
IR_QUARTERLY_DIR = "data/raw/ir_documents/quarterly"
IR_YEARS_TO_DOWNLOAD = 5  # Download last 5 years of reports
IR_SCRAPING_TIMEOUT = 30  # seconds
IR_RETRY_ATTEMPTS = 3

# Default Assumptions (can be overridden)
DEFAULT_ASSUMPTIONS = {
    # Terminal Value
    "terminal_growth_rate": 0.025,  # 2.5% (long-term GDP growth)
    "terminal_growth_rate_min": 0.015,  # 1.5%
    "terminal_growth_rate_max": 0.03,  # 3.0%
    
    # WACC Components
    "risk_free_rate_source": "10Y Netherlands Government Bond",
    "equity_risk_premium": 0.05,  # 5% (can be adjusted based on market)
    "beta_source": "Yahoo Finance or calculated",
    
    # Forecast Period
    "forecast_years": 5,
    
    # Terminal Value Method Weights
    "terminal_value_perpetuity_weight": 0.7,  # 70% weight on perpetuity method
    "terminal_value_exit_multiple_weight": 0.3,  # 30% weight on exit multiple
    
    # Sensitivity Analysis Ranges
    "wacc_sensitivity_range": [-0.02, -0.01, 0.01, 0.02],  # ±1%, ±2%
    "terminal_growth_sensitivity_range": [-0.01, -0.005, 0.005, 0.01],  # ±0.5%, ±1%
    "revenue_growth_sensitivity_range": [-0.05, -0.02, 0.02, 0.05],  # ±2%, ±5%
    "margin_sensitivity_range": [-0.02, -0.01, 0.01, 0.02],  # ±1%, ±2%
}

# Excel Formatting Settings
EXCEL_FORMATTING = {
    "header_color": "366092",  # Blue
    "input_color": "DCE6F1",  # Light blue
    "calculation_color": "FFFFFF",  # White
    "formula_color": "F2F2F2",  # Light gray
    "font_name": "Calibri",
    "header_font_size": 11,
    "data_font_size": 10,
    "number_format": "#,##0",
    "percentage_format": "0.00%",
    "currency_format": "€#,##0.00",
}

# Validation Thresholds
VALIDATION_THRESHOLDS = {
    "terminal_value_max_pct_of_total": 0.70,  # TV should not exceed 70% of total value
    "wacc_min": 0.06,  # Minimum reasonable WACC
    "wacc_max": 0.15,  # Maximum reasonable WACC
    "terminal_growth_max": 0.03,  # Maximum terminal growth (GDP growth)
    "roic_min_for_growth": 0.08,  # Minimum ROIC to sustain growth
}

# Peer Companies for Relative Valuation
PEER_COMPANIES = [
    {"ticker": "SONY", "name": "Sony Group Corporation", "exchange": "NYSE"},
    {"ticker": "WMG", "name": "Warner Music Group", "exchange": "NASDAQ"},
    {"ticker": "SPOT", "name": "Spotify Technology", "exchange": "NYSE"},
    # Add more peers as needed
]

# File Paths
DATA_DIR = "data"
RAW_DATA_DIR = "data/raw"
PROCESSED_DATA_DIR = "data/processed"
OUTPUT_DIR = "outputs"
EXCEL_OUTPUT_FILE = "outputs/UMG_DCF_Model.xlsx"

