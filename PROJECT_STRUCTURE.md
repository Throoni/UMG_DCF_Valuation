# Project Structure Overview

## Improved Organization

The project has been reorganized for better maintainability and professional structure:

### Root Level
- **`main.py`** - Entry point for running the model
- **`config.py`** - Configuration and assumptions (stays at root for easy access)
- **`requirements.txt`** - Python dependencies
- **`README.md`** - Main documentation
- **`.gitignore`** - Git ignore rules

### Source Code (`src/`)
All main modules are now organized in the `src/` directory:
- `data_collection.py` - Data fetching from Yahoo Finance and company IR
- `financial_analysis.py` - Financial statement normalization and ratio analysis
- `dcf_model.py` - Core DCF calculations (projections, WACC, terminal value)
- `valuation_analysis.py` - Sensitivity and scenario analysis
- `excel_generator.py` - Excel output generation
- `audit_system.py` - Validation and audit system

### Utilities (`utils/`)
Reusable utility functions:
- `data_validation.py` - Financial data validation functions
- `formatting.py` - Excel formatting utilities

### Tests (`tests/`)
Test suite for validation:
- `test_integration.py` - Integration tests

### Data Directories
- `data/raw/` - Raw collected data (gitignored)
- `data/processed/` - Processed financials (gitignored)

### Output Directory
- `outputs/` - Generated Excel files (gitignored)

## Benefits of New Structure

1. **Better Organization**: Source code separated from configuration and documentation
2. **Scalability**: Easy to add new modules without cluttering root directory
3. **Professional**: Follows Python project best practices
4. **Maintainability**: Clear separation of concerns
5. **Import Clarity**: All source modules in one location

## Running the Model

The entry point remains the same:
```bash
python main.py
```

All imports have been updated to work with the new structure.

