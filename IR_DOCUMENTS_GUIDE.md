# IR Documents Download and Extraction Guide

## Overview

The UMG DCF Valuation Model now supports direct download and extraction of financial data from Universal Music Group's investor relations website. This provides more reliable and complete data than Yahoo Finance alone.

## How It Works

### Automatic Process

When you run `python main.py`, the system will:

1. **Attempt IR Document Collection** (Primary Source)
   - Scrape UMG's investor relations website for annual/quarterly reports
   - Download PDF reports to `data/raw/ir_documents/annual/` or `data/raw/ir_documents/quarterly/`
   - Extract financial statements (Income Statement, Balance Sheet, Cash Flow) from PDFs
   - Standardize the data to match the model's expected format

2. **Fallback to Yahoo Finance** (If IR Fails)
   - If IR scraping/download fails, automatically uses Yahoo Finance
   - If PDF extraction fails, falls back to Yahoo Finance
   - If partial data extracted, merges with Yahoo Finance

### Data Priority

1. **IR Documents** (if successfully extracted) - Most reliable
2. **Yahoo Finance** (fallback) - Still reliable but may have gaps
3. **Manual Input** (if needed) - For edge cases

## Manual PDF Download

If automatic scraping doesn't find reports, you can manually download PDFs:

1. Visit UMG's investor relations page: https://www.universalmusic.com/investors/
2. Download annual reports (PDF format)
3. Place them in: `data/raw/ir_documents/annual/`
4. Name them with year in filename (e.g., `UMG_Annual_Report_2024.pdf`)
5. Run the model again - it will automatically detect and extract from these PDFs

## Directory Structure

```
data/raw/ir_documents/
├── annual/
│   ├── UMG_Annual_Report_2024.pdf
│   ├── UMG_Annual_Report_2023.pdf
│   └── ...
└── quarterly/
    └── (quarterly reports if available)
```

## Configuration

Edit `config.py` to adjust:

- `IR_YEARS_TO_DOWNLOAD`: Number of years to download (default: 5)
- `IR_SCRAPING_TIMEOUT`: Timeout for web requests (default: 30 seconds)
- `IR_RETRY_ATTEMPTS`: Number of retry attempts (default: 3)

## PDF Extraction

The PDF extractor uses `pdfplumber` to:
- Extract tables from PDF pages
- Identify financial statements by keywords
- Parse line items and values
- Standardize column names
- Handle multiple years of data

### Extraction Accuracy

PDF extraction is complex and may not be 100% accurate. The system:
- Uses multiple extraction methods
- Validates extracted data
- Falls back to Yahoo Finance if extraction quality is poor
- Provides warnings when data quality is uncertain

## Troubleshooting

### No Reports Found
- **Cause**: Website structure may have changed or reports not publicly accessible
- **Solution**: Manually download PDFs and place in `ir_documents/annual/`

### PDF Extraction Fails
- **Cause**: PDF format may be non-standard or scanned images
- **Solution**: System automatically falls back to Yahoo Finance

### Partial Data Extracted
- **Cause**: Some tables may not be detected correctly
- **Solution**: System merges with Yahoo Finance data to fill gaps

## Benefits

1. **More Reliable Data**: Direct from company source
2. **Complete Financials**: May include more detail than Yahoo Finance
3. **Historical Accuracy**: Official company reports
4. **Automatic**: No manual data entry needed
5. **Fallback Protection**: Always has Yahoo Finance as backup

## Notes

- PDF extraction works best with text-based PDFs (not scanned images)
- Different report formats across years may require adjustments
- The system is designed to be robust and will always provide data (via fallback if needed)
- Downloaded PDFs are saved locally for future use (no re-download needed)

