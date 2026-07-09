"""共享工具模块：验证、数据获取、清洗、JSON I/O、日志"""
import json
import logging
import os
import time
from pathlib import Path
from typing import Callable, Any
import pandas as pd
import akshare as ak


def get_data_dir() -> Path:
    """
    获取数据存储目录。
    
    优先使用 FINDERS_WORKSPACE 环境变量，默认为 ~/.finders/workspace
    
    Returns:
        Path: 数据目录路径 (FINDERS_WORKSPACE/data)
    """
    workspace = os.environ.get("FINDERS_WORKSPACE")
    if workspace:
        base_dir = Path(workspace).expanduser().resolve()
    else:
        base_dir = Path.home() / ".finders" / "workspace"
    
    data_dir = base_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def validate_stock_code(stock_code: str) -> dict:
    """
    验证股票代码并返回公司信息。
    
    Args:
        stock_code: 6位股票代码（如 '600519'）
    
    Returns:
        dict: 包含 code, name, market 的字典
        
    Raises:
        ValueError: 当股票代码无效时
    """
    stock_info = ak.stock_info_a_code_name()
    stock_row = stock_info[stock_info['code'] == stock_code]
    
    if stock_row.empty:
        raise ValueError(f"股票代码 '{stock_code}' 在A股市场中不存在")
    
    stock_name = stock_row.iloc[0]['name']
    market = 'SH' if stock_code.startswith('6') else 'SZ'
    
    return {
        'code': stock_code,
        'name': stock_name,
        'market': market
    }


def save_json(data: dict, filepath: Path) -> None:
    """
    保存数据为 JSON 文件（UTF-8 编码）。
    
    Args:
        data: 要保存的字典
        filepath: 输出文件路径
    """
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def fetch_with_retry(func: Callable, max_retries: int = 3, **kwargs) -> Any:
    """
    执行函数，带重试逻辑和指数退避。
    
    Args:
        func: 要执行的函数
        max_retries: 最大重试次数
        **kwargs: 传递给函数的参数
    
    Returns:
        函数返回值
        
    Raises:
        Exception: 如果所有重试都失败
    """
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            return func(**kwargs)
        except Exception as e:
            last_exception = e
            if attempt < max_retries - 1:
                sleep_time = 2 ** attempt  # 1s, 2s, 4s
                logging.warning(f"第 {attempt + 1} 次尝试失败: {e}。{sleep_time}秒后重试...")
                time.sleep(sleep_time)
    
    raise last_exception


def clean_financial_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    清洗财务数据以便 JSON 序列化。
    
    - 将 NaN 转换为 None
    - 标准化日期格式
    - 确保数值类型
    
    Args:
        df: 要清洗的 DataFrame
    
    Returns:
        清洗后的 DataFrame
    """
    df = df.copy()
    
    # 将 NaN 转换为 None 以便 JSON 序列化
    df = df.where(pd.notnull(df), None)
    
    # 将日期列转换为字符串格式
    date_cols = [col for col in df.columns if 'date' in col.lower() or 'time' in col.lower()]
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col]).dt.strftime('%Y-%m-%d')
    
    return df


def setup_logger(script_name: str) -> logging.Logger:
    """
    设置日志记录器，使用一致的格式。
    
    Args:
        script_name: 脚本/模块名称
    
    Returns:
        配置好的日志记录器
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
