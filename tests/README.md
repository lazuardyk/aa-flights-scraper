# Tests Directory

This directory contains test files and sample data for the AA CPP scraper.

## Files

- `test_parser.py` - Test script that validates the parser using saved responses
- `award_pricing_response.json` - Sample award pricing response from AA API
- `revenue_pricing_response.json` - Sample revenue pricing response from AA API
- `test_output.json` - Expected output from test_parser.py
- `test.json`, `test_parallel.json` - Additional test output files

## Running Tests

From the project root directory:

```bash
python tests/test_parser.py
```

This will:
1. Load the sample JSON responses
2. Parse and merge the data
3. Calculate CPP values
4. Output results to `tests/test_output.json`

## Sample Data

The sample responses are from a real search:
- Route: LAX → JFK
- Date: December 15, 2025
- Passengers: 1
- Class: Economy (COACH)
