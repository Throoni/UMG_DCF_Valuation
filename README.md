# UMG DCF Valuation Model

A comprehensive Discounted Cash Flow (DCF) valuation model for Universal Music Group (UMG.AS), built for the CFA Research Challenge. This model follows professional valuation standards and Damodaran's methodology.

## 🎯 Overview

This project provides a complete, production-ready DCF valuation framework that:
- Automatically collects financial data from multiple sources
- Performs rigorous financial statement analysis
- Builds 5-year financial projections
- Calculates WACC using proper CAPM methodology
- Generates professionally formatted Excel outputs with verifiable formulas
- Includes comprehensive audit system for validation
- Performs sensitivity and scenario analysis

## Features

- **Automated Data Collection**: Fetches financial data from Yahoo Finance and company investor relations
- **Financial Statement Analysis**: Normalizes financials and calculates key ratios
- **DCF Modeling**: 5-year explicit forecast with terminal value calculation
- **WACC Calculation**: Proper CAPM-based cost of equity and cost of debt
- **Sensitivity Analysis**: Tests impact of key assumptions on valuation
- **Scenario Analysis**: Base, Bull, and Bear cases
- **Relative Valuation**: Peer company multiples analysis
- **Excel Output**: Professionally formatted workbook with all formulas visible
- **Comprehensive Audit System**: Validates financial and technical correctness

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd UMG_Challenge
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

3. Run the model:
```bash
python main.py
```

The model will automatically:
- Collect financial data
- Perform analysis
- Generate Excel output
- Run validation audit

## 📊 Usage

### Basic Usage

Run the main script to generate the complete DCF valuation:

```bash
python main.py
```

### Workflow

The script executes the following steps:

1. **Data Collection** - Fetches financial data from Yahoo Finance and company IR
2. **Financial Analysis** - Normalizes statements and calculates key ratios
3. **DCF Assumptions** - Prepares projection assumptions from historical data
4. **DCF Modeling** - Builds 5-year projections and calculates WACC
5. **Valuation Analysis** - Performs sensitivity and scenario analysis
6. **Excel Generation** - Creates formatted workbook with all formulas
7. **Audit** - Validates financial and technical correctness

### Customization

Edit `config.py` to adjust:
- Company ticker and information
- Default assumptions (terminal growth, WACC components)
- Excel formatting preferences
- Validation thresholds
- Peer companies for relative valuation

## 📁 Output

The model generates an Excel workbook (`outputs/UMG_DCF_Model.xlsx`) with the following sheets:

1. **Executive Summary**: Key metrics and recommendation
2. **Data Sources**: Attribution of data sources
3. **Historical Financials**: Normalized historical statements
4. **Financial Analysis**: Ratios and trends
5. **DCF Assumptions**: All input assumptions
6. **Revenue Model**: Revenue projections with growth drivers
7. **Income Statement Projections**: 5-year forecast
8. **Balance Sheet Projections**: 5-year forecast
9. **Cash Flow Projections**: 5-year forecast
10. **FCFF Calculation**: Free cash flow to firm by year
11. **WACC Calculation**: Step-by-step WACC derivation
12. **Terminal Value**: Perpetuity growth and exit multiple methods
13. **DCF Valuation**: Final equity value and per-share value
14. **Sensitivity Analysis**: Impact of key variables
15. **Scenario Analysis**: Base/Bull/Bear cases
16. **Relative Valuation**: Peer multiples and implied valuation
17. **Summary**: Final recommendation and price target

## 🔬 Methodology

### DCF Framework

The model follows Damodaran's valuation methodology:

- **Free Cash Flow to Firm (FCFF)**: 
  ```
  FCFF = EBIT(1-t) + Depreciation - CapEx - ΔNWC
  ```
- **Mid-Year Convention**: Cash flows assumed at mid-year for more accurate discounting
- **Terminal Value**: Perpetuity growth method where g ≤ long-term GDP growth (typically 1.5-3%)
- **WACC Calculation**: 
  ```
  WACC = (E/(E+D)) × Re + (D/(E+D)) × Rd × (1-t)
  ```
  Where:
  - Re = Risk-free rate + β × Equity Risk Premium (CAPM)
  - Rd = Cost of debt (market YTM or synthetic rating)

### Key Assumptions

- **Forecast Period**: 5-year explicit forecast + terminal value
- **Terminal Growth Rate**: 2.5% (long-term GDP growth, configurable)
- **WACC**: Calculated using CAPM for cost of equity
- **Working Capital**: Linked to revenue (historical %)
- **CapEx**: Maintenance + Growth components
- **Tax Rate**: Effective tax rate from historical data

### Validation Rules

- Terminal value should not exceed 70% of total enterprise value
- WACC typically ranges from 6-15% for most companies
- Revenue growth must be sustainable (Growth ≤ ROIC × Reinvestment Rate)
- Terminal growth rate cannot exceed long-term GDP growth

## ✅ Validation & Audit

The comprehensive audit system automatically validates:

### Financial Validation
- ✓ Accounting identities (Assets = Liabilities + Equity)
- ✓ Cash flow consistency (Operating + Investing + Financing = Net Change)
- ✓ WACC reasonableness (6-15% range)
- ✓ Terminal value percentage (<70% of total value)
- ✓ Growth sustainability checks
- ✓ FCFF sign validation (should be positive in terminal year)
- ✓ Revenue projection reasonableness

### Technical Validation
- ✓ Excel formula syntax verification
- ✓ Cross-sheet consistency checks
- ✓ Data type validation
- ✓ Missing data detection
- ✓ Code quality checks

### Audit Output

After each run, the audit system provides:
- Summary of passed checks
- Warnings for potential issues
- Errors that need attention
- Overall audit status

## 📂 Project Structure

```
UMG_Challenge/
├── main.py                 # Main execution script (entry point)
├── config.py              # Configuration and assumptions
├── requirements.txt       # Python dependencies
├── README.md              # This file
├── .gitignore            # Git ignore rules
├── GITHUB_SETUP.md       # GitHub setup instructions
├── src/                   # Source code modules
│   ├── __init__.py
│   ├── data_collection.py     # Data fetching module
│   ├── financial_analysis.py  # Financial statement analysis
│   ├── dcf_model.py          # DCF core calculations
│   ├── valuation_analysis.py  # Sensitivity and scenario analysis
│   ├── excel_generator.py    # Excel output generation
│   └── audit_system.py       # Validation and audit
├── utils/                 # Utility functions
│   ├── __init__.py
│   ├── data_validation.py
│   └── formatting.py
├── tests/                 # Test suite
│   ├── __init__.py
│   └── test_integration.py
├── data/                  # Data storage
│   ├── raw/               # Raw collected data
│   └── processed/         # Processed financials
└── outputs/               # Generated Excel files
    └── UMG_DCF_Model.xlsx
```

## ⚠️ Important Notes

### Data Collection
- Requires active internet connection
- Yahoo Finance API may have rate limits
- Some data may need manual verification from company IR website
- Macro data (risk-free rate, ERP) should be updated with current market conditions

### Assumptions
- Default assumptions are based on historical averages
- Company-specific factors may require manual adjustment
- Terminal growth rate should reflect long-term economic growth
- WACC components should be validated against current market conditions

### Excel Output
- All formulas are visible and verifiable
- Data can be manually adjusted in Excel
- Formulas will automatically recalculate
- Professional formatting for presentation

## 🧪 Testing

Run the test suite:

```bash
pytest tests/ -v
```

## 🤝 Contributing

This project is designed for the CFA Research Challenge. For improvements:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run the audit system to validate
5. Submit a pull request

## 📝 License

This project is for educational purposes as part of the CFA Research Challenge.

## 🙏 Acknowledgments

- Valuation methodology based on Aswath Damodaran's framework
- Built for CFA Institute Research Challenge standards
- Follows professional equity research best practices

## 📧 Contact

For questions or issues related to this valuation model, please refer to the project documentation or create an issue in the repository.

