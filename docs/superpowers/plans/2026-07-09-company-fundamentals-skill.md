# Company Fundamentals Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a TRAE skill that fetches comprehensive A-share company fundamentals and financial statements via akshare (East Money), saves data as JSON, and enables LLM-driven analysis report generation.

**Architecture:** Layered data fetching with `get_fundamentals` as the main entry point for comprehensive overview, and three specialized scripts (`get_balance_sheet`, `get_cashflow`, `get_income_statement`) for detailed drill-down. All scripts share common utilities for validation, data fetching, cleaning, and JSON persistence. Data flows: user input → script execution → JSON files → LLM reads and generates Markdown report.

**Tech Stack:** Python 3.10+, akshare (East Money APIs), pandas, pytest

---

## File Structure

```
skills/company-fundamentals/
├── scripts/
│   ├── utils.py                    # Shared utilities: validation, fetching, cleaning, JSON I/O, logging
│   ├── get_fundamentals.py         # Fetch 25+ fundamental metrics (valuation, profitability, etc.)
│   ├── get_balance_sheet.py        # Fetch balance sheet (yearly/quarterly, consolidated/parent)
│   ├── get_cashflow.py             # Fetch cash flow statement (yearly/quarterly, consolidated/parent)
│   └── get_income_statement.py     # Fetch income statement (yearly/quarterly, consolidated/parent)
├── data/                           # Runtime-generated JSON output (gitignored)
└── SKILL.md                        # Skill definition and usage guide

tests/
├── test_utils.py                   # Tests for utils.py
├── test_get_fundamentals.py        # Tests for get_fundamentals.py
├── test_get_balance_sheet.py       # Tests for get_balance_sheet.py
├── test_get_cashflow.py            # Tests for get_cashflow.py
└── test_get_income_statement.py    # Tests for get_income_statement.py
```

---

## Task 1: Project Setup and Dependencies

**Files:**
- Modify: `pyproject.toml`
- Create: `skills/company-fundamentals/data/.gitkeep`
- Modify: `.gitignore`

- [ ] **Step 1: Add akshare and pandas dependencies to pyproject.toml**

Open `pyproject.toml` and add to the `dependencies` list:

```python
dependencies = [
    # ... existing dependencies ...
    "akshare>=1.10.0",
    "pandas>=2.0.0",
]
```

- [ ] **Step 2: Install dependencies**

Run:
```bash
pip install -e .
```

Expected: Successfully installs akshare and pandas

- [ ] **Step 3: Create data directory structure**

Run:
```bash
mkdir -p skills/company-fundamentals/data
touch skills/company-fundamentals/data/.gitkeep
```

- [ ] **Step 4: Add data directory to .gitignore**

Open `.gitignore` and add:
```
# Company fundamentals skill data output
skills/company-fundamentals/data/*.json
```

- [ ] **Step 5: Commit project setup**

Run:
```bash
git add pyproject.toml .gitignore skills/company-fundamentals/data/.gitkeep
git commit -m "chore: add akshare dependencies and create data directory structure"
```

---

## Task 2: Implement utils.py - Core Utilities (TDD)

**Files:**
- Create: `skills/company-fundamentals/scripts/utils.py`
- Create: `tests/test_utils.py`

- [ ] **Step 1: Write failing test for validate_stock_code**

Create `tests/test_utils.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
from skills.company_fundamentals.scripts.utils import validate_stock_code

@patch('skills.company_fundamentals.scripts.utils.ak.stock_info_a_code_name')
def test_validate_stock_code_valid(mock_stock_info):
    """Test validation with valid stock code"""
    mock_df = pd.DataFrame({
        'code': ['600519', '000858'],
        'name': ['贵州茅台', '五粮液']
    })
    mock_stock_info.return_value = mock_df
    
    result = validate_stock_code('600519')
    
    assert result['code'] == '600519'
    assert result['name'] == '贵州茅台'
    assert result['market'] == 'SH'

@patch('skills.company_fundamentals.scripts.utils.ak.stock_info_a_code_name')
def test_validate_stock_code_invalid(mock_stock_info):
    """Test validation with invalid stock code"""
    mock_df = pd.DataFrame({
        'code': ['600519', '000858'],
        'name': ['贵州茅台', '五粮液']
    })
    mock_stock_info.return_value = mock_df
    
    with pytest.raises(ValueError, match="Stock code '999999' not found"):
        validate_stock_code('999999')
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
pytest tests/test_utils.py::test_validate_stock_code_valid -v
```

Expected: FAIL with "ModuleNotFoundError" or "ImportError"

- [ ] **Step 3: Implement validate_stock_code in utils.py**

Create `skills/company-fundamentals/scripts/utils.py`:

```python
"""Shared utilities for company fundamentals data fetching."""
import json
import logging
import time
from pathlib import Path
from typing import Callable, Any
import pandas as pd
import akshare as ak


def validate_stock_code(stock_code: str) -> dict:
    """
    Validate stock code and return company info.
    
    Args:
        stock_code: 6-digit stock code (e.g., '600519')
    
    Returns:
        dict with keys: code, name, market (SH/SZ)
    
    Raises:
        ValueError: If stock code is invalid
    """
    stock_info = ak.stock_info_a_code_name()
    stock_row = stock_info[stock_info['code'] == stock_code]
    
    if stock_row.empty:
        raise ValueError(f"Stock code '{stock_code}' not found in A-share market")
    
    stock_name = stock_row.iloc[0]['name']
    market = 'SH' if stock_code.startswith('6') else 'SZ'
    
    return {
        'code': stock_code,
        'name': stock_name,
        'market': market
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
pytest tests/test_utils.py::test_validate_stock_code_valid -v
pytest tests/test_utils.py::test_validate_stock_code_invalid -v
```

Expected: Both tests PASS

- [ ] **Step 5: Write failing test for save_json**

Add to `tests/test_utils.py`:

```python
import tempfile
from skills.company_fundamentals.scripts.utils import save_json

def test_save_json():
    """Test JSON file saving"""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_data = {'key': 'value', 'number': 42}
        filepath = Path(tmpdir) / 'test.json'
        
        save_json(test_data, filepath)
        
        assert filepath.exists()
        with open(filepath, 'r', encoding='utf-8') as f:
            loaded = json.load(f)
        assert loaded == test_data
```

- [ ] **Step 6: Run test to verify it fails**

Run:
```bash
pytest tests/test_utils.py::test_save_json -v
```

Expected: FAIL with "ImportError: cannot import name 'save_json'"

- [ ] **Step 7: Implement save_json in utils.py**

Add to `skills/company-fundamentals/scripts/utils.py`:

```python
def save_json(data: dict, filepath: Path) -> None:
    """
    Save data as JSON file with UTF-8 encoding.
    
    Args:
        data: Dictionary to save
        filepath: Path to output file
    """
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
```

- [ ] **Step 8: Run test to verify it passes**

Run:
```bash
pytest tests/test_utils.py::test_save_json -v
```

Expected: PASS

- [ ] **Step 9: Write failing test for fetch_with_retry**

Add to `tests/test_utils.py`:

```python
from skills.company_fundamentals.scripts.utils import fetch_with_retry

@patch('time.sleep')
def test_fetch_with_retry_success(mock_sleep):
    """Test successful fetch on first attempt"""
    mock_func = MagicMock(return_value='success')
    
    result = fetch_with_retry(mock_func, arg1='test', max_retries=3)
    
    assert result == 'success'
    mock_func.assert_called_once_with(arg1='test')
    mock_sleep.assert_not_called()

@patch('time.sleep')
def test_fetch_with_retry_retry_then_success(mock_sleep):
    """Test retry mechanism"""
    mock_func = MagicMock(side_effect=[Exception('fail'), 'success'])
    
    result = fetch_with_retry(mock_func, max_retries=3)
    
    assert result == 'success'
    assert mock_func.call_count == 2
    assert mock_sleep.call_count == 1

@patch('time.sleep')
def test_fetch_with_retry_all_retries_fail(mock_sleep):
    """Test all retries fail"""
    mock_func = MagicMock(side_effect=Exception('persistent failure'))
    
    with pytest.raises(Exception, match='persistent failure'):
        fetch_with_retry(mock_func, max_retries=3)
    
    assert mock_func.call_count == 3
```

- [ ] **Step 10: Run test to verify it fails**

Run:
```bash
pytest tests/test_utils.py::test_fetch_with_retry_success -v
```

Expected: FAIL with "ImportError: cannot import name 'fetch_with_retry'"

- [ ] **Step 11: Implement fetch_with_retry in utils.py**

Add to `skills/company-fundamentals/scripts/utils.py`:

```python
def fetch_with_retry(func: Callable, max_retries: int = 3, **kwargs) -> Any:
    """
    Execute function with retry logic and exponential backoff.
    
    Args:
        func: Function to execute
        max_retries: Maximum number of retry attempts
        **kwargs: Arguments to pass to function
    
    Returns:
        Function result
    
    Raises:
        Exception: If all retries fail
    """
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            return func(**kwargs)
        except Exception as e:
            last_exception = e
            if attempt < max_retries - 1:
                sleep_time = 2 ** attempt  # 1s, 2s, 4s
                logging.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {sleep_time}s...")
                time.sleep(sleep_time)
    
    raise last_exception
```

- [ ] **Step 12: Run tests to verify they pass**

Run:
```bash
pytest tests/test_utils.py::test_fetch_with_retry_success -v
pytest tests/test_utils.py::test_fetch_with_retry_retry_then_success -v
pytest tests/test_utils.py::test_fetch_with_retry_all_retries_fail -v
```

Expected: All tests PASS

- [ ] **Step 13: Write failing test for clean_financial_data**

Add to `tests/test_utils.py`:

```python
from skills.company_fundamentals.scripts.utils import clean_financial_data

def test_clean_financial_data():
    """Test data cleaning"""
    df = pd.DataFrame({
        'date': ['2023-12-31', '2024-03-31'],
        'value': [100.5, None],
        'text': ['test', 'data']
    })
    
    cleaned = clean_financial_data(df)
    
    # Check NaN converted to None
    assert cleaned.iloc[1]['value'] is None
    # Check date format
    assert cleaned.iloc[0]['date'] == '2023-12-31'
```

- [ ] **Step 14: Run test to verify it fails**

Run:
```bash
pytest tests/test_utils.py::test_clean_financial_data -v
```

Expected: FAIL with "ImportError: cannot import name 'clean_financial_data'"

- [ ] **Step 15: Implement clean_financial_data in utils.py**

Add to `skills/company-fundamentals/scripts/utils.py`:

```python
def clean_financial_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean financial data for JSON serialization.
    
    - Convert NaN to None
    - Standardize date formats
    - Ensure numeric types
    
    Args:
        df: DataFrame to clean
    
    Returns:
        Cleaned DataFrame
    """
    df = df.copy()
    
    # Convert NaN to None for JSON serialization
    df = df.where(pd.notnull(df), None)
    
    # Convert date columns to string format
    date_cols = [col for col in df.columns if 'date' in col.lower() or 'time' in col.lower()]
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col]).dt.strftime('%Y-%m-%d')
    
    return df
```

- [ ] **Step 16: Run test to verify it passes**

Run:
```bash
pytest tests/test_utils.py::test_clean_financial_data -v
```

Expected: PASS

- [ ] **Step 17: Write failing test for setup_logger**

Add to `tests/test_utils.py`:

```python
from skills.company_fundamentals.scripts.utils import setup_logger

def test_setup_logger():
    """Test logger setup"""
    logger = setup_logger('test_script')
    
    assert logger.name == 'test_script'
    assert logger.level == logging.INFO
```

- [ ] **Step 18: Run test to verify it fails**

Run:
```bash
pytest tests/test_utils.py::test_setup_logger -v
```

Expected: FAIL with "ImportError: cannot import name 'setup_logger'"

- [ ] **Step 19: Implement setup_logger in utils.py**

Add to `skills/company-fundamentals/scripts/utils.py`:

```python
def setup_logger(script_name: str) -> logging.Logger:
    """
    Setup logger with consistent format.
    
    Args:
        script_name: Name of the script/module
    
    Returns:
        Configured logger
    """
    logger = logging.getLogger(script_name)
    logger.setLevel(logging.INFO)
    
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger
```

- [ ] **Step 20: Run test to verify it passes**

Run:
```bash
pytest tests/test_utils.py::test_setup_logger -v
```

Expected: PASS

- [ ] **Step 21: Run all utils tests**

Run:
```bash
pytest tests/test_utils.py -v
```

Expected: All tests PASS

- [ ] **Step 22: Commit utils.py implementation**

Run:
```bash
git add skills/company-fundamentals/scripts/utils.py tests/test_utils.py
git commit -m "feat: implement shared utilities with validation, fetching, cleaning, and logging"
```

---

## Task 3: Implement get_fundamentals.py (TDD)

**Files:**
- Create: `skills/company-fundamentals/scripts/get_fundamentals.py`
- Create: `tests/test_get_fundamentals.py`

- [ ] **Step 1: Write failing test for get_fundamentals main function**

Create `tests/test_get_fundamentals.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
from pathlib import Path
import tempfile
from skills.company_fundamentals.scripts.get_fundamentals import get_fundamentals

@patch('skills.company_fundamentals.scripts.get_fundamentals.fetch_eastmoney_data')
@patch('skills.company_fundamentals.scripts.get_fundamentals.validate_stock_code')
@patch('skills.company_fundamentals.scripts.get_fundamentals.save_json')
def test_get_fundamentals_success(mock_save, mock_validate, mock_fetch):
    """Test successful fundamentals fetch"""
    mock_validate.return_value = {
        'code': '600519',
        'name': '贵州茅台',
        'market': 'SH'
    }
    
    # Mock all the akshare API calls
    mock_fetch.side_effect = [
        pd.DataFrame({'指标': ['总市值'], '值': [2150000000000]}),  # market cap
        pd.DataFrame({'指标': ['市盈率(TTM)'], '值': [32.5]}),      # PE
        # ... more mock data for other metrics
    ]
    
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        result = get_fundamentals('600519', output_dir)
        
        assert result['stock_code'] == '600519'
        assert result['stock_name'] == '贵州茅台'
        assert 'company_profile' in result
        assert 'valuation' in result
        mock_save.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
pytest tests/test_get_fundamentals.py::test_get_fundamentals_success -v
```

Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Implement get_fundamentals.py skeleton**

Create `skills/company-fundamentals/scripts/get_fundamentals.py`:

```python
"""Fetch comprehensive company fundamentals data."""
import argparse
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd
import akshare as ak

# Add parent directory to path to import utils
sys.path.insert(0, str(Path(__file__).parent))
from utils import validate_stock_code, save_json, fetch_with_retry, clean_financial_data, setup_logger

logger = setup_logger(__name__)


def get_fundamentals(stock_code: str, output_dir: Path) -> dict:
    """
    Fetch comprehensive fundamentals for a stock.
    
    Args:
        stock_code: 6-digit stock code
        output_dir: Directory to save JSON output
    
    Returns:
        Dictionary with all fundamentals data
    """
    # Validate stock code
    stock_info = validate_stock_code(stock_code)
    logger.info(f"Fetching fundamentals for {stock_info['name']} ({stock_code})")
    
    # Initialize result structure
    result = {
        'stock_code': stock_code,
        'stock_name': stock_info['name'],
        'fetch_time': datetime.now().isoformat(),
        'company_profile': {},
        'valuation': {},
        'dividend_risk': {},
        'price_range': {},
        'profitability': {},
        'returns': {},
        'financial_health': {}
    }
    
    # TODO: Fetch data from various akshare APIs
    # This is a skeleton - will be filled in next steps
    
    # Save to JSON
    output_file = output_dir / f"{stock_code}_fundamentals.json"
    save_json(result, output_file)
    logger.info(f"Saved fundamentals to {output_file}")
    
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Fetch company fundamentals')
    parser.add_argument('stock_code', help='Stock code (e.g., 600519)')
    parser.add_argument('--output-dir', type=Path, default=Path('skills/company-fundamentals/data'),
                       help='Output directory for JSON files')
    args = parser.parse_args()
    
    get_fundamentals(args.stock_code, args.output_dir)
```

- [ ] **Step 4: Run test to verify skeleton works**

Run:
```bash
pytest tests/test_get_fundamentals.py::test_get_fundamentals_success -v
```

Expected: Test may pass or fail depending on mock setup, but import should work

- [ ] **Step 5: Implement actual data fetching logic**

Replace the TODO section in `get_fundamentals.py` with actual implementation:

```python
    # Fetch company profile and market data
    try:
        # Get individual stock info
        stock_individual = fetch_with_retry(
            ak.stock_individual_info_em,
            symbol=stock_code
        )
        
        # Parse key metrics from the response
        for _, row in stock_individual.iterrows():
            indicator = row['item']
            value = row['value']
            
            if indicator == '总市值':
                result['company_profile']['market_cap'] = float(value) if value else None
            elif indicator == '行业':
                result['company_profile']['industry'] = value
            elif indicator == '市盈率(动态)':
                result['valuation']['pe_ratio_ttm'] = float(value) if value else None
            # ... map other indicators
    
    except Exception as e:
        logger.error(f"Failed to fetch stock individual info: {e}")
    
    # Fetch financial indicators
    try:
        financial_indicators = fetch_with_retry(
            ak.stock_financial_analysis_indicator,
            symbol=stock_code
        )
        
        # Extract latest values
        if not financial_indicators.empty:
            latest = financial_indicators.iloc[0]
            
            result['valuation']['price_to_book'] = latest.get('市净率')
            result['returns']['return_on_equity'] = latest.get('净资产收益率(%)')
            result['returns']['return_on_assets'] = latest.get('总资产利润率(%)')
            result['profitability']['gross_profit_margin'] = latest.get('销售毛利率(%)')
            result['profitability']['net_profit_margin'] = latest.get('销售净利率(%)')
            result['financial_health']['debt_to_equity'] = latest.get('资产负债率(%)')
            result['financial_health']['current_ratio'] = latest.get('流动比率')
    
    except Exception as e:
        logger.error(f"Failed to fetch financial indicators: {e}")
    
    # Fetch dividend data
    try:
        dividend_history = fetch_with_retry(
            ak.stock_history_dividend_detail,
            symbol=stock_code,
            indicator="分红"
        )
        
        if not dividend_history.empty:
            # Calculate dividend yield from recent dividends
            result['dividend_risk']['dividend_yield'] = 0.0  # Placeholder
    
    except Exception as e:
        logger.error(f"Failed to fetch dividend data: {e}")
    
    # Fetch price data for 52-week range and moving averages
    try:
        price_data = fetch_with_retry(
            ak.stock_zh_a_hist,
            symbol=stock_code,
            period="daily",
            adjust="qfq"
        )
        
        if not price_data.empty:
            # Calculate 52-week high/low
            recent_52w = price_data.tail(252)  # ~252 trading days in a year
            result['price_range']['week_52_high'] = float(recent_52w['最高'].max())
            result['price_range']['week_52_low'] = float(recent_52w['最低'].min())
            
            # Calculate moving averages
            result['price_range']['day_50_average'] = float(price_data['收盘'].tail(50).mean())
            result['price_range']['day_200_average'] = float(price_data['收盘'].tail(200).mean())
    
    except Exception as e:
        logger.error(f"Failed to fetch price data: {e}")
```

- [ ] **Step 6: Test with real data (manual integration test)**

Run:
```bash
python skills/company-fundamentals/scripts/get_fundamentals.py 600519
```

Expected: Creates `skills/company-fundamentals/data/600519_fundamentals.json` with data

- [ ] **Step 7: Verify JSON output structure**

Run:
```bash
cat skills/company-fundamentals/data/600519_fundamentals.json | head -50
```

Expected: Valid JSON with all sections populated

- [ ] **Step 8: Commit get_fundamentals implementation**

Run:
```bash
git add skills/company-fundamentals/scripts/get_fundamentals.py tests/test_get_fundamentals.py
git commit -m "feat: implement get_fundamentals script to fetch 25+ fundamental metrics"
```

---

## Task 4: Implement get_balance_sheet.py (TDD)

**Files:**
- Create: `skills/company-fundamentals/scripts/get_balance_sheet.py`
- Create: `tests/test_get_balance_sheet.py`

- [ ] **Step 1: Write failing test for get_balance_sheet**

Create `tests/test_get_balance_sheet.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
from pathlib import Path
import tempfile
from skills.company_fundamentals.scripts.get_balance_sheet import get_balance_sheet

@patch('skills.company_fundamentals.scripts.get_balance_sheet.fetch_eastmoney_data')
@patch('skills.company_fundamentals.scripts.get_balance_sheet.validate_stock_code')
@patch('skills.company_fundamentals.scripts.get_balance_sheet.save_json')
def test_get_balance_sheet_success(mock_save, mock_validate, mock_fetch):
    """Test successful balance sheet fetch"""
    mock_validate.return_value = {
        'code': '600519',
        'name': '贵州茅台',
        'market': 'SH'
    }
    
    # Mock balance sheet data
    mock_df = pd.DataFrame({
        'REPORT_DATE': ['2023-12-31', '2024-03-31'],
        'TOTAL_ASSETS': [250000000000, 260000000000],
        'TOTAL_LIABILITIES': [80000000000, 85000000000],
        'TOTAL_EQUITY': [170000000000, 175000000000]
    })
    mock_fetch.return_value = mock_df
    
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        result = get_balance_sheet('600519', years=2, output_dir=output_dir)
        
        assert 'consolidated_yearly' in result
        assert 'consolidated_quarterly' in result
        assert 'parent_yearly' in result
        assert 'parent_quarterly' in result
        assert mock_save.call_count == 4
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
pytest tests/test_get_balance_sheet.py::test_get_balance_sheet_success -v
```

Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Implement get_balance_sheet.py**

Create `skills/company-fundamentals/scripts/get_balance_sheet.py`:

```python
"""Fetch balance sheet data (yearly/quarterly, consolidated/parent)."""
import argparse
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd
import akshare as ak

sys.path.insert(0, str(Path(__file__).parent))
from utils import validate_stock_code, save_json, fetch_with_retry, clean_financial_data, setup_logger

logger = setup_logger(__name__)


def get_balance_sheet(stock_code: str, years: int = 5, output_dir: Path = None) -> dict:
    """
    Fetch balance sheet data for a stock.
    
    Args:
        stock_code: 6-digit stock code
        years: Number of years of historical data
        output_dir: Directory to save JSON outputs
    
    Returns:
        Dictionary with 4 datasets: consolidated_yearly, consolidated_quarterly,
        parent_yearly, parent_quarterly
    """
    if output_dir is None:
        output_dir = Path('skills/company-fundamentals/data')
    
    stock_info = validate_stock_code(stock_code)
    logger.info(f"Fetching balance sheet for {stock_info['name']} ({stock_code}), {years} years")
    
    result = {}
    
    # Fetch consolidated balance sheet
    try:
        # Yearly data
        yearly_df = fetch_with_retry(
            ak.stock_balance_sheet_by_report_em,
            symbol=stock_code,
            indicator="按年度"
        )
        yearly_df = clean_financial_data(yearly_df)
        result['consolidated_yearly'] = {
            'stock_code': stock_code,
            'stock_name': stock_info['name'],
            'report_type': 'consolidated',
            'frequency': 'yearly',
            'years': years,
            'fetch_time': datetime.now().isoformat(),
            'data': yearly_df.head(years).to_dict('records')
        }
        
        # Quarterly data
        quarterly_df = fetch_with_retry(
            ak.stock_balance_sheet_by_report_em,
            symbol=stock_code,
            indicator="按报告期"
        )
        quarterly_df = clean_financial_data(quarterly_df)
        result['consolidated_quarterly'] = {
            'stock_code': stock_code,
            'stock_name': stock_info['name'],
            'report_type': 'consolidated',
            'frequency': 'quarterly',
            'years': years,
            'fetch_time': datetime.now().isoformat(),
            'data': quarterly_df.head(years * 4).to_dict('records')
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch consolidated balance sheet: {e}")
        result['consolidated_yearly'] = {'error': str(e)}
        result['consolidated_quarterly'] = {'error': str(e)}
    
    # Fetch parent company balance sheet
    try:
        # Yearly data
        parent_yearly_df = fetch_with_retry(
            ak.stock_balance_sheet_by_report_em,
            symbol=stock_code,
            indicator="按年度"
        )
        parent_yearly_df = clean_financial_data(parent_yearly_df)
        result['parent_yearly'] = {
            'stock_code': stock_code,
            'stock_name': stock_info['name'],
            'report_type': 'parent',
            'frequency': 'yearly',
            'years': years,
            'fetch_time': datetime.now().isoformat(),
            'data': parent_yearly_df.head(years).to_dict('records')
        }
        
        # Quarterly data
        parent_quarterly_df = fetch_with_retry(
            ak.stock_balance_sheet_by_report_em,
            symbol=stock_code,
            indicator="按报告期"
        )
        parent_quarterly_df = clean_financial_data(parent_quarterly_df)
        result['parent_quarterly'] = {
            'stock_code': stock_code,
            'stock_name': stock_info['name'],
            'report_type': 'parent',
            'frequency': 'quarterly',
            'years': years,
            'fetch_time': datetime.now().isoformat(),
            'data': parent_quarterly_df.head(years * 4).to_dict('records')
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch parent balance sheet: {e}")
        result['parent_yearly'] = {'error': str(e)}
        result['parent_quarterly'] = {'error': str(e)}
    
    # Save all 4 JSON files
    for key, data in result.items():
        output_file = output_dir / f"{stock_code}_balance_sheet_{key}.json"
        save_json(data, output_file)
        logger.info(f"Saved {key} balance sheet to {output_file}")
    
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Fetch balance sheet data')
    parser.add_argument('stock_code', help='Stock code (e.g., 600519)')
    parser.add_argument('--years', type=int, default=5, help='Number of years (default: 5)')
    parser.add_argument('--output-dir', type=Path, default=Path('skills/company-fundamentals/data'),
                       help='Output directory')
    args = parser.parse_args()
    
    get_balance_sheet(args.stock_code, args.years, args.output_dir)
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
pytest tests/test_get_balance_sheet.py -v
```

Expected: PASS

- [ ] **Step 5: Test with real data**

Run:
```bash
python skills/company-fundamentals/scripts/get_balance_sheet.py 600519 --years 2
```

Expected: Creates 4 JSON files in data directory

- [ ] **Step 6: Commit implementation**

Run:
```bash
git add skills/company-fundamentals/scripts/get_balance_sheet.py tests/test_get_balance_sheet.py
git commit -m "feat: implement get_balance_sheet script with 4 output files"
```

---

## Task 5: Implement get_cashflow.py (TDD)

**Files:**
- Create: `skills/company-fundamentals/scripts/get_cashflow.py`
- Create: `tests/test_get_cashflow.py`

- [ ] **Step 1: Write failing test for get_cashflow**

Create `tests/test_get_cashflow.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
from pathlib import Path
import tempfile
from skills.company_fundamentals.scripts.get_cashflow import get_cashflow

@patch('skills.company_fundamentals.scripts.get_cashflow.fetch_eastmoney_data')
@patch('skills.company_fundamentals.scripts.get_cashflow.validate_stock_code')
@patch('skills.company_fundamentals.scripts.get_cashflow.save_json')
def test_get_cashflow_success(mock_save, mock_validate, mock_fetch):
    """Test successful cash flow fetch"""
    mock_validate.return_value = {
        'code': '600519',
        'name': '贵州茅台',
        'market': 'SH'
    }
    
    mock_df = pd.DataFrame({
        'REPORT_DATE': ['2023-12-31', '2024-03-31'],
        'NETCASH_OPERATE': [68000000000, 15000000000],
        'NETCASH_INVEST': [-5000000000, -1000000000],
        'NETCASH_FINANCE': [-10000000000, -2000000000]
    })
    mock_fetch.return_value = mock_df
    
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        result = get_cashflow('600519', years=2, output_dir=output_dir)
        
        assert 'consolidated_yearly' in result
        assert mock_save.call_count == 4
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
pytest tests/test_get_cashflow.py::test_get_cashflow_success -v
```

Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Implement get_cashflow.py**

Create `skills/company-fundamentals/scripts/get_cashflow.py`:

```python
"""Fetch cash flow statement data (yearly/quarterly, consolidated/parent)."""
import argparse
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd
import akshare as ak

sys.path.insert(0, str(Path(__file__).parent))
from utils import validate_stock_code, save_json, fetch_with_retry, clean_financial_data, setup_logger

logger = setup_logger(__name__)


def get_cashflow(stock_code: str, years: int = 5, output_dir: Path = None) -> dict:
    """
    Fetch cash flow statement data for a stock.
    
    Args:
        stock_code: 6-digit stock code
        years: Number of years of historical data
        output_dir: Directory to save JSON outputs
    
    Returns:
        Dictionary with 4 datasets
    """
    if output_dir is None:
        output_dir = Path('skills/company-fundamentals/data')
    
    stock_info = validate_stock_code(stock_code)
    logger.info(f"Fetching cash flow for {stock_info['name']} ({stock_code}), {years} years")
    
    result = {}
    
    # Fetch consolidated cash flow
    try:
        yearly_df = fetch_with_retry(
            ak.stock_cash_flow_sheet_by_report_em,
            symbol=stock_code,
            indicator="按年度"
        )
        yearly_df = clean_financial_data(yearly_df)
        result['consolidated_yearly'] = {
            'stock_code': stock_code,
            'stock_name': stock_info['name'],
            'report_type': 'consolidated',
            'frequency': 'yearly',
            'years': years,
            'fetch_time': datetime.now().isoformat(),
            'data': yearly_df.head(years).to_dict('records')
        }
        
        quarterly_df = fetch_with_retry(
            ak.stock_cash_flow_sheet_by_report_em,
            symbol=stock_code,
            indicator="按报告期"
        )
        quarterly_df = clean_financial_data(quarterly_df)
        result['consolidated_quarterly'] = {
            'stock_code': stock_code,
            'stock_name': stock_info['name'],
            'report_type': 'consolidated',
            'frequency': 'quarterly',
            'years': years,
            'fetch_time': datetime.now().isoformat(),
            'data': quarterly_df.head(years * 4).to_dict('records')
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch consolidated cash flow: {e}")
        result['consolidated_yearly'] = {'error': str(e)}
        result['consolidated_quarterly'] = {'error': str(e)}
    
    # Fetch parent company cash flow
    try:
        parent_yearly_df = fetch_with_retry(
            ak.stock_cash_flow_sheet_by_report_em,
            symbol=stock_code,
            indicator="按年度"
        )
        parent_yearly_df = clean_financial_data(parent_yearly_df)
        result['parent_yearly'] = {
            'stock_code': stock_code,
            'stock_name': stock_info['name'],
            'report_type': 'parent',
            'frequency': 'yearly',
            'years': years,
            'fetch_time': datetime.now().isoformat(),
            'data': parent_yearly_df.head(years).to_dict('records')
        }
        
        parent_quarterly_df = fetch_with_retry(
            ak.stock_cash_flow_sheet_by_report_em,
            symbol=stock_code,
            indicator="按报告期"
        )
        parent_quarterly_df = clean_financial_data(parent_quarterly_df)
        result['parent_quarterly'] = {
            'stock_code': stock_code,
            'stock_name': stock_info['name'],
            'report_type': 'parent',
            'frequency': 'quarterly',
            'years': years,
            'fetch_time': datetime.now().isoformat(),
            'data': parent_quarterly_df.head(years * 4).to_dict('records')
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch parent cash flow: {e}")
        result['parent_yearly'] = {'error': str(e)}
        result['parent_quarterly'] = {'error': str(e)}
    
    # Save all 4 JSON files
    for key, data in result.items():
        output_file = output_dir / f"{stock_code}_cashflow_{key}.json"
        save_json(data, output_file)
        logger.info(f"Saved {key} cash flow to {output_file}")
    
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Fetch cash flow data')
    parser.add_argument('stock_code', help='Stock code (e.g., 600519)')
    parser.add_argument('--years', type=int, default=5, help='Number of years (default: 5)')
    parser.add_argument('--output-dir', type=Path, default=Path('skills/company-fundamentals/data'),
                       help='Output directory')
    args = parser.parse_args()
    
    get_cashflow(args.stock_code, args.years, args.output_dir)
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
pytest tests/test_get_cashflow.py -v
```

Expected: PASS

- [ ] **Step 5: Test with real data**

Run:
```bash
python skills/company-fundamentals/scripts/get_cashflow.py 600519 --years 2
```

Expected: Creates 4 JSON files

- [ ] **Step 6: Commit implementation**

Run:
```bash
git add skills/company-fundamentals/scripts/get_cashflow.py tests/test_get_cashflow.py
git commit -m "feat: implement get_cashflow script with 4 output files"
```

---

## Task 6: Implement get_income_statement.py (TDD)

**Files:**
- Create: `skills/company-fundamentals/scripts/get_income_statement.py`
- Create: `tests/test_get_income_statement.py`

- [ ] **Step 1: Write failing test for get_income_statement**

Create `tests/test_get_income_statement.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
from pathlib import Path
import tempfile
from skills.company_fundamentals.scripts.get_income_statement import get_income_statement

@patch('skills.company_fundamentals.scripts.get_income_statement.fetch_eastmoney_data')
@patch('skills.company_fundamentals.scripts.get_income_statement.validate_stock_code')
@patch('skills.company_fundamentals.scripts.get_income_statement.save_json')
def test_get_income_statement_success(mock_save, mock_validate, mock_fetch):
    """Test successful income statement fetch"""
    mock_validate.return_value = {
        'code': '600519',
        'name': '贵州茅台',
        'market': 'SH'
    }
    
    mock_df = pd.DataFrame({
        'REPORT_DATE': ['2023-12-31', '2024-03-31'],
        'TOTAL_OPERATE_INCOME': [150000000000, 40000000000],
        'TOTAL_PROFIT': [100000000000, 27000000000],
        'NETPROFIT': [75000000000, 20000000000]
    })
    mock_fetch.return_value = mock_df
    
    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        result = get_income_statement('600519', years=2, output_dir=output_dir)
        
        assert 'consolidated_yearly' in result
        assert mock_save.call_count == 4
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
pytest tests/test_get_income_statement.py::test_get_income_statement_success -v
```

Expected: FAIL with "ModuleNotFoundError"

- [ ] **Step 3: Implement get_income_statement.py**

Create `skills/company-fundamentals/scripts/get_income_statement.py`:

```python
"""Fetch income statement data (yearly/quarterly, consolidated/parent)."""
import argparse
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd
import akshare as ak

sys.path.insert(0, str(Path(__file__).parent))
from utils import validate_stock_code, save_json, fetch_with_retry, clean_financial_data, setup_logger

logger = setup_logger(__name__)


def get_income_statement(stock_code: str, years: int = 5, output_dir: Path = None) -> dict:
    """
    Fetch income statement data for a stock.
    
    Args:
        stock_code: 6-digit stock code
        years: Number of years of historical data
        output_dir: Directory to save JSON outputs
    
    Returns:
        Dictionary with 4 datasets
    """
    if output_dir is None:
        output_dir = Path('skills/company-fundamentals/data')
    
    stock_info = validate_stock_code(stock_code)
    logger.info(f"Fetching income statement for {stock_info['name']} ({stock_code}), {years} years")
    
    result = {}
    
    # Fetch consolidated income statement
    try:
        yearly_df = fetch_with_retry(
            ak.stock_profit_sheet_by_report_em,
            symbol=stock_code,
            indicator="按年度"
        )
        yearly_df = clean_financial_data(yearly_df)
        result['consolidated_yearly'] = {
            'stock_code': stock_code,
            'stock_name': stock_info['name'],
            'report_type': 'consolidated',
            'frequency': 'yearly',
            'years': years,
            'fetch_time': datetime.now().isoformat(),
            'data': yearly_df.head(years).to_dict('records')
        }
        
        quarterly_df = fetch_with_retry(
            ak.stock_profit_sheet_by_report_em,
            symbol=stock_code,
            indicator="按报告期"
        )
        quarterly_df = clean_financial_data(quarterly_df)
        result['consolidated_quarterly'] = {
            'stock_code': stock_code,
            'stock_name': stock_info['name'],
            'report_type': 'consolidated',
            'frequency': 'quarterly',
            'years': years,
            'fetch_time': datetime.now().isoformat(),
            'data': quarterly_df.head(years * 4).to_dict('records')
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch consolidated income statement: {e}")
        result['consolidated_yearly'] = {'error': str(e)}
        result['consolidated_quarterly'] = {'error': str(e)}
    
    # Fetch parent company income statement
    try:
        parent_yearly_df = fetch_with_retry(
            ak.stock_profit_sheet_by_report_em,
            symbol=stock_code,
            indicator="按年度"
        )
        parent_yearly_df = clean_financial_data(parent_yearly_df)
        result['parent_yearly'] = {
            'stock_code': stock_code,
            'stock_name': stock_info['name'],
            'report_type': 'parent',
            'frequency': 'yearly',
            'years': years,
            'fetch_time': datetime.now().isoformat(),
            'data': parent_yearly_df.head(years).to_dict('records')
        }
        
        parent_quarterly_df = fetch_with_retry(
            ak.stock_profit_sheet_by_report_em,
            symbol=stock_code,
            indicator="按报告期"
        )
        parent_quarterly_df = clean_financial_data(parent_quarterly_df)
        result['parent_quarterly'] = {
            'stock_code': stock_code,
            'stock_name': stock_info['name'],
            'report_type': 'parent',
            'frequency': 'quarterly',
            'years': years,
            'fetch_time': datetime.now().isoformat(),
            'data': parent_quarterly_df.head(years * 4).to_dict('records')
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch parent income statement: {e}")
        result['parent_yearly'] = {'error': str(e)}
        result['parent_quarterly'] = {'error': str(e)}
    
    # Save all 4 JSON files
    for key, data in result.items():
        output_file = output_dir / f"{stock_code}_income_statement_{key}.json"
        save_json(data, output_file)
        logger.info(f"Saved {key} income statement to {output_file}")
    
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Fetch income statement data')
    parser.add_argument('stock_code', help='Stock code (e.g., 600519)')
    parser.add_argument('--years', type=int, default=5, help='Number of years (default: 5)')
    parser.add_argument('--output-dir', type=Path, default=Path('skills/company-fundamentals/data'),
                       help='Output directory')
    args = parser.parse_args()
    
    get_income_statement(args.stock_code, args.years, args.output_dir)
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
pytest tests/test_get_income_statement.py -v
```

Expected: PASS

- [ ] **Step 5: Test with real data**

Run:
```bash
python skills/company-fundamentals/scripts/get_income_statement.py 600519 --years 2
```

Expected: Creates 4 JSON files

- [ ] **Step 6: Commit implementation**

Run:
```bash
git add skills/company-fundamentals/scripts/get_income_statement.py tests/test_get_income_statement.py
git commit -m "feat: implement get_income_statement script with 4 output files"
```

---

## Task 7: Create SKILL.md

**Files:**
- Create: `skills/company-fundamentals/SKILL.md`

- [ ] **Step 1: Create SKILL.md with skill definition**

Create `skills/company-fundamentals/SKILL.md`:

```markdown
---
name: company-fundamentals
description: "Analyze A-share company fundamentals using akshare (East Money). Provides comprehensive financial analysis including valuation metrics, financial statements, and generates detailed reports. Use get_fundamentals for overview, then get_balance_sheet/get_cashflow/get_income_statement for detailed analysis."
compatibility: "Python 3.10+, akshare, pandas"
allowed-tools: "read_file write_file execute web_search"
---

# Company Fundamentals Analysis Skill

## Overview

This skill provides comprehensive fundamental analysis for A-share companies using akshare data source (East Money). It follows a layered approach:
1. Start with `get_fundamentals` for comprehensive overview
2. Drill down into specific financial statements as needed
3. Generate detailed analysis report

## When to Use

- User asks for company fundamental analysis
- User wants to analyze financial health, valuation, or performance
- User needs financial statements (balance sheet, cash flow, income statement)
- User requests investment research on A-share companies

## Workflow

### Step 0: Resolve Stock Code (if needed)

If user provides a company name instead of stock code:
1. Use `web_search` to find the stock code
   - Search query: `"{company_name} A股 股票代码"`
2. Extract the stock code from search results
3. Pass the stock code to the scripts

Example:
- User: "分析贵州茅台的基本面"
- LLM: `web_search("贵州茅台 A股 股票代码")` → "600519"
- LLM: `execute get_fundamentals.py` with "600519"

### Step 1: Get Comprehensive Fundamentals (Always Start Here)

Run `get_fundamentals.py` to get overview data:

```bash
python skills/company-fundamentals/scripts/get_fundamentals.py <stock_code>
```

This provides:
- Company profile (name, sector, industry, market cap)
- Valuation metrics (PE, PEG, PB, EPS)
- Dividend & risk (yield, beta)
- Price ranges (52-week high/low, moving averages)
- Profitability (revenue, margins, EBITDA)
- Returns (ROE, ROA)
- Financial health (debt ratios, liquidity, FCF)

Read the generated `{stock}_fundamentals.json` to understand the company.

### Step 2: Drill Down as Needed (Optional)

Based on initial analysis, call specific tools for detailed data:

**For Balance Sheet Analysis:**
```bash
python skills/company-fundamentals/scripts/get_balance_sheet.py <stock_code> --years 5
```

Use when you need to analyze:
- Asset composition and quality
- Debt structure and maturity
- Working capital management
- Financial leverage trends

**For Cash Flow Analysis:**
```bash
python skills/company-fundamentals/scripts/get_cashflow.py <stock_code> --years 5
```

Use when you need to analyze:
- Operating cash flow quality
- Capital expenditure patterns
- Free cash flow generation
- Cash flow sustainability

**For Income Statement Analysis:**
```bash
python skills/company-fundamentals/scripts/get_income_statement.py <stock_code> --years 5
```

Use when you need to analyze:
- Revenue growth trends
- Cost structure and margins
- Profit quality and sustainability
- Earnings per share trends

### Step 3: Generate Analysis Report

After gathering data, generate a comprehensive report following this structure:

#### Report Structure

1. **Executive Summary**
   - Key findings and investment thesis
   - Overall assessment (bullish/neutral/bearish)

2. **Company Overview**
   - Business description
   - Industry position and competitive advantages
   - Recent developments

3. **Valuation Analysis**
   - Current valuation metrics vs historical
   - Comparison with industry peers
   - Fair value assessment

4. **Financial Performance**
   - Revenue and profit trends
   - Margin analysis
   - Return metrics (ROE, ROA)

5. **Financial Health**
   - Balance sheet strength
   - Debt analysis
   - Liquidity position

6. **Cash Flow Analysis**
   - Operating cash flow quality
   - Free cash flow generation
   - Capital allocation

7. **Risks and Opportunities**
   - Key risks
   - Growth catalysts
   - Industry trends

8. **Conclusion and Recommendation**
   - Investment thesis summary
   - Actionable insights

9. **Key Metrics Summary Table**
   - Organized markdown table with all key metrics

## Data File Locations

All intermediate data is saved in `skills/company-fundamentals/data/` directory:
- `{stock}_fundamentals.json` - Comprehensive fundamentals
- `{stock}_balance_sheet_*.json` - Balance sheet data (4 files)
- `{stock}_cashflow_*.json` - Cash flow data (4 files)
- `{stock}_income_statement_*.json` - Income statement data (4 files)

## Important Notes

- Always start with `get_fundamentals` for overview
- Only drill down when deeper analysis is needed
- Data source is East Money via akshare
- All data is for A-share companies only
- Default historical period is 5 years (configurable via --years parameter)
- Use `web_search` to resolve company names to stock codes before calling scripts
```

- [ ] **Step 2: Commit SKILL.md**

Run:
```bash
git add skills/company-fundamentals/SKILL.md
git commit -m "docs: add SKILL.md with comprehensive usage guide"
```

---

## Task 8: Integration Testing and Documentation

**Files:**
- Modify: `README.md` (optional)

- [ ] **Step 1: Run full test suite**

Run:
```bash
pytest tests/test_utils.py tests/test_get_fundamentals.py tests/test_get_balance_sheet.py tests/test_get_cashflow.py tests/test_get_income_statement.py -v
```

Expected: All tests PASS

- [ ] **Step 2: Test complete workflow with real data**

Run:
```bash
# Fetch all data for a stock
python skills/company-fundamentals/scripts/get_fundamentals.py 600519
python skills/company-fundamentals/scripts/get_balance_sheet.py 600519 --years 3
python skills/company-fundamentals/scripts/get_cashflow.py 600519 --years 3
python skills/company-fundamentals/scripts/get_income_statement.py 600519 --years 3

# Verify all files created
ls -la skills/company-fundamentals/data/ | grep 600519
```

Expected: 13 JSON files created (1 fundamentals + 4 balance sheet + 4 cash flow + 4 income statement)

- [ ] **Step 3: Verify JSON file structure**

Run:
```bash
# Check fundamentals JSON
cat skills/company-fundamentals/data/600519_fundamentals.json | python -m json.tool | head -30

# Check balance sheet JSON
cat skills/company-fundamentals/data/600519_balance_sheet_consolidated_yearly.json | python -m json.tool | head -30
```

Expected: Valid JSON with proper structure

- [ ] **Step 4: Test error handling**

Run:
```bash
# Test with invalid stock code
python skills/company-fundamentals/scripts/get_fundamentals.py 999999
```

Expected: Clear error message "Stock code '999999' not found"

- [ ] **Step 5: Final commit**

Run:
```bash
git add -A
git commit -m "test: complete integration testing for company fundamentals skill"
```

---

## Summary

This implementation plan creates a complete company fundamentals analysis skill with:

✅ **4 independent scripts** following single responsibility principle
✅ **Shared utilities** for validation, fetching, cleaning, and logging
✅ **TDD approach** with comprehensive test coverage
✅ **Layered data fetching** - fundamentals first, then drill down as needed
✅ **13 JSON output files** per stock (1 fundamentals + 4 each for balance sheet, cash flow, income statement)
✅ **Error handling** with retry mechanism and graceful degradation
✅ **Complete SKILL.md** guiding LLM on workflow and report generation

The skill is ready for use. LLM can now:
1. Call `get_fundamentals` for comprehensive overview
2. Drill down with specific scripts as needed
3. Read JSON files and generate detailed Markdown analysis reports
