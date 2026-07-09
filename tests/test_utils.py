"""Tests for company-fundamentals utilities."""
import importlib.machinery
import json
import logging
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pandas as pd
import pytest

# Load utils module directly by file path (company-fundamentals has hyphen, not a valid package name)
_utils_path = Path(__file__).resolve().parent.parent / 'skills' / 'company-fundamentals' / 'scripts' / 'utils.py'
_loader = importlib.machinery.SourceFileLoader('company_fundamentals_utils', str(_utils_path))
_utils_module = _loader.load_module()
sys.modules['company_fundamentals_utils'] = _utils_module

validate_stock_code = _utils_module.validate_stock_code
save_json = _utils_module.save_json
fetch_with_retry = _utils_module.fetch_with_retry
clean_financial_data = _utils_module.clean_financial_data
setup_logger = _utils_module.setup_logger


def test_validate_stock_code_valid():
    """Test validation of valid stock code."""
    mock_stock_list = pd.DataFrame({
        'code': ['600519', '000001', '300750'],
        'name': ['贵州茅台', '平安银行', '宁德时代']
    })

    with patch.object(_utils_module.ak, 'stock_info_a_code_name', return_value=mock_stock_list):
        result = validate_stock_code('600519')

    assert result['code'] == '600519'
    assert result['name'] == '贵州茅台'
    assert result['market'] == 'SH'


def test_validate_stock_code_invalid():
    """Test validation of invalid stock code."""
    mock_stock_list = pd.DataFrame({
        'code': ['600519', '000001', '300750'],
        'name': ['贵州茅台', '平安银行', '宁德时代']
    })

    with patch.object(_utils_module.ak, 'stock_info_a_code_name', return_value=mock_stock_list):
        with pytest.raises(ValueError, match="Invalid stock code"):
            validate_stock_code('999999')


def test_save_json():
    """Test JSON file saving with proper encoding."""
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = Path(tmpdir) / 'subdir' / 'test.json'
        data = {'name': '贵州茅台', 'value': 123.45, 'null_value': None}

        save_json(data, filepath)

        assert filepath.exists()

        with open(filepath, 'r', encoding='utf-8') as f:
            loaded = json.load(f)

        assert loaded == data
        assert loaded['name'] == '贵州茅台'


def test_fetch_with_retry_success():
    """Test successful data fetch without retries."""
    mock_func = Mock(return_value='success_data')

    result = fetch_with_retry(mock_func, max_retries=3, param1='value1')

    assert result == 'success_data'
    mock_func.assert_called_once_with(param1='value1')


def test_fetch_with_retry_retry_then_success():
    """Test fetch that fails initially but succeeds after retries."""
    mock_func = Mock(side_effect=[
        Exception('Network error'),
        Exception('Timeout'),
        'success_data'
    ])

    result = fetch_with_retry(mock_func, max_retries=3, param1='value1')

    assert result == 'success_data'
    assert mock_func.call_count == 3


def test_fetch_with_retry_all_retries_fail():
    """Test fetch that fails after all retries."""
    mock_func = Mock(side_effect=Exception('Persistent error'))

    with pytest.raises(Exception, match='Persistent error'):
        fetch_with_retry(mock_func, max_retries=3, param1='value1')

    assert mock_func.call_count == 3


def test_clean_financial_data():
    """Test financial data cleaning."""
    df = pd.DataFrame({
        'date': ['2024-01-15', '2024/02/20', '20240325'],
        'value': [100.5, float('nan'), 200.3],
        'name': ['test1', 'test2', float('nan')]
    })

    cleaned = clean_financial_data(df)

    # Check NaN converted to None
    assert cleaned['value'].iloc[1] is None
    assert cleaned['name'].iloc[2] is None

    # Check date standardization (YYYY-MM-DD format)
    assert cleaned['date'].iloc[0] == '2024-01-15'
    assert cleaned['date'].iloc[1] == '2024-02-20'
    assert cleaned['date'].iloc[2] == '2024-03-25'


def test_setup_logger():
    """Test logger setup with unified format."""
    logger = setup_logger('test_script')

    assert isinstance(logger, logging.Logger)
    assert logger.name == 'test_script'
    assert logger.level == logging.INFO

    # Check that logger has handlers
    assert len(logger.handlers) > 0
