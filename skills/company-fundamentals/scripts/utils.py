#!/usr/bin/env python3
"""工具函数模块"""

import os
import json
from datetime import datetime, timedelta
from pathlib import Path

import tushare as ts
import pandas as pd


def get_tushare_api(token=None):
    """获取 tushare API 实例"""
    if token is None:
        token = os.getenv('TUSHARE_TOKEN')
        if not token:
            raise ValueError("请设置 TUSHARE_TOKEN 环境变量或传入 token 参数")
    return ts.pro_api(token)


def normalize_stock_code(code):
    """标准化股票代码为 tushare 格式（带交易所后缀）"""
    code = code.strip().upper()
    
    # 如果已经带后缀，直接返回
    if code.endswith('.SH') or code.endswith('.SZ') or code.endswith('.BJ'):
        return code
    
    # 根据代码规则添加后缀
    # 上海证券交易所：600xxx, 601xxx, 603xxx, 688xxx
    # 深圳证券交易所：000xxx, 002xxx, 300xxx
    # 北京证券交易所：8xxxxx, 4xxxxx
    
    if code.startswith(('600', '601', '603', '688')):
        return f"{code}.SH"
    elif code.startswith(('000', '002', '300')):
        return f"{code}.SZ"
    elif code.startswith(('8', '4')):
        return f"{code}.BJ"
    else:
        # 默认尝试深交所
        return f"{code}.SZ"


def get_workspace_data_dir():
    """获取工作空间数据目录"""
    workspace = os.getenv('FINDERS_WORKSPACE', str(Path.home() / '.finders' / 'workspace'))
    data_dir = Path(workspace) / 'data'
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def save_json(data, filename):
    """保存数据为 JSON 文件"""
    data_dir = get_workspace_data_dir()
    filepath = data_dir / filename
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    return filepath


def load_json(filename):
    """从 JSON 文件加载数据"""
    data_dir = get_workspace_data_dir()
    filepath = data_dir / filename
    if not filepath.exists():
        return None
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_date_range(years=5):
    """获取日期范围"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=years * 365)
    return start_date.strftime('%Y%m%d'), end_date.strftime('%Y%m%d')


def df_to_dict(df):
    """将 DataFrame 转换为字典列表"""
    if df is None or df.empty:
        return []
    return df.to_dict('records')


def safe_float(value, default=0.0):
    """安全的浮点数转换"""
    try:
        if pd.isna(value):
            return default
        return float(value)
    except (ValueError, TypeError):
        return default


def format_number(value, decimals=2):
    """格式化数字显示"""
    if value is None or pd.isna(value):
        return "N/A"
    return f"{value:,.{decimals}f}"
