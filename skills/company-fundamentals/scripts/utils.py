"""Shared utilities for company fundamentals analysis scripts."""
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import akshare as ak
import pandas as pd


def validate_stock_code(stock_code: str) -> dict:
    """
    Validate stock code via akshare.

    Args:
        stock_code: Stock code to validate (e.g., '600519')

    Returns:
        dict with keys: code, name, market

    Raises:
        ValueError: If stock code is invalid
    """
    stock_list = ak.stock_info_a_code_name()

    # Find the stock in the list
    match = stock_list[stock_list['code'] == stock_code]

    if match.empty:
        raise ValueError(f"Invalid stock code: {stock_code}")

    stock_name = match.iloc[0]['name']

    # Determine market based on code prefix
    if stock_code.startswith('6'):
        market = 'SH'
    elif stock_code.startswith(('0', '3')):
        market = 'SZ'
    else:
        market = 'OTHER'

    return {
        'code': stock_code,
        'name': stock_name,
        'market': market
    }


def save_json(data: dict, filepath: Path) -> None:
    """
    Save data as JSON with proper encoding.

    Args:
        data: Dictionary to save
        filepath: Path to save the JSON file
    """
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def fetch_with_retry(func: Callable, max_retries: int = 3, **kwargs) -> Any:
    """
    Fetch data with exponential backoff retry.

    Args:
        func: Function to call
        max_retries: Maximum number of retry attempts (default: 3)
        **kwargs: Arguments to pass to the function

    Returns:
        Result from the function call

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
                # Exponential backoff: 1s, 2s, 4s
                sleep_time = 2 ** attempt
                time.sleep(sleep_time)

    raise last_exception


def _parse_date(value: str) -> str | None:
    """Try to parse a date string in multiple formats, return YYYY-MM-DD or None."""
    if not isinstance(value, str):
        return None
    for fmt in ('%Y-%m-%d', '%Y/%m/%d', '%Y%m%d', '%Y-%m-%d %H:%M:%S'):
        try:
            return datetime.strptime(value, fmt).strftime('%Y-%m-%d')
        except (ValueError, TypeError):
            continue
    return None


def clean_financial_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean financial data for JSON serialization.

    - Convert NaN to None
    - Standardize date formats to YYYY-MM-DD

    Args:
        df: DataFrame to clean

    Returns:
        Cleaned DataFrame
    """
    df = df.copy()

    # Standardize date columns: detect columns that look like dates
    for col in df.columns:
        if df[col].dtype == 'object' or str(df[col].dtype) == 'str':
            # Check if most non-null values look like dates
            sample = df[col].dropna().head(5)
            if sample.empty:
                continue
            date_like_count = sum(
                1 for v in sample
                if isinstance(v, str) and len(v) >= 8 and v.replace('-', '').replace('/', '').isdigit()
            )
            if date_like_count > len(sample) / 2:
                df[col] = df[col].apply(_parse_date)

    # Convert to object dtype and replace NaN/NaT with None
    df = df.astype(object).where(pd.notnull(df), None)

    return df


def setup_logger(script_name: str) -> logging.Logger:
    """
    Setup logger with unified format.

    Args:
        script_name: Name of the script (used as logger name)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(script_name)
    logger.setLevel(logging.INFO)

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Create console handler
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)

    # Add handler to logger
    logger.addHandler(handler)

    return logger
