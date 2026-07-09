"""获取资产负债表数据（年/季度，合并+母公司）"""
import argparse
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd
import akshare as ak

sys.path.insert(0, str(Path(__file__).parent))
from utils import validate_stock_code, save_json, fetch_with_retry, clean_financial_data, setup_logger, get_data_dir

logger = setup_logger(__name__)


def get_balance_sheet(stock_code: str, years: int = 5, frequency: str = 'both', output_dir: Path = None) -> dict:
    """
    获取股票的资产负债表数据。
    
    Args:
        stock_code: 6位股票代码
        years: 历史数据年数
        frequency: 数据频率 - 'yearly'(年度), 'quarterly'(季度), 'both'(两者)
        output_dir: JSON 输出目录
    
    Returns:
        包含数据集的字典
    """
    if output_dir is None:
        output_dir = get_data_dir()
    
    stock_info = validate_stock_code(stock_code)
    logger.info(f"正在获取 {stock_info['name']} ({stock_code}) 的资产负债表，{years} 年，频率: {frequency}")
    
    result = {}
    fetch_yearly = frequency in ('yearly', 'both')
    fetch_quarterly = frequency in ('quarterly', 'both')
    
    # 获取合并资产负债表
    try:
        df = fetch_with_retry(
            ak.stock_balance_sheet_by_report_em,
            symbol=stock_code
        )
        if not df.empty:
            df = clean_financial_data(df)
            
            # 年度数据
            if fetch_yearly:
                yearly_data = [r for r in df.to_dict('records') 
                              if r.get('REPORT_DATE', '').endswith('12-31')][:years]
                result['consolidated_yearly'] = {
                    'stock_code': stock_code,
                    'stock_name': stock_info['name'],
                    'report_type': 'consolidated',
                    'frequency': 'yearly',
                    'years': years,
                    'fetch_time': datetime.now().isoformat(),
                    'data': yearly_data
                }
            
            # 季度数据
            if fetch_quarterly:
                quarterly_data = df.head(years * 4).to_dict('records')
                result['consolidated_quarterly'] = {
                    'stock_code': stock_code,
                    'stock_name': stock_info['name'],
                    'report_type': 'consolidated',
                    'frequency': 'quarterly',
                    'years': years,
                    'fetch_time': datetime.now().isoformat(),
                    'data': quarterly_data
                }
        else:
            if fetch_yearly:
                result['consolidated_yearly'] = {'error': '无数据'}
            if fetch_quarterly:
                result['consolidated_quarterly'] = {'error': '无数据'}
            
    except Exception as e:
        logger.error(f"获取合并资产负债表失败: {e}")
        if fetch_yearly:
            result['consolidated_yearly'] = {'error': str(e)}
        if fetch_quarterly:
            result['consolidated_quarterly'] = {'error': str(e)}
    
    # 获取母公司资产负债表
    try:
        if fetch_yearly and 'consolidated_yearly' in result and 'data' in result['consolidated_yearly']:
            result['parent_yearly'] = {
                'stock_code': stock_code,
                'stock_name': stock_info['name'],
                'report_type': 'parent',
                'frequency': 'yearly',
                'years': years,
                'fetch_time': datetime.now().isoformat(),
                'data': result['consolidated_yearly']['data'],
                'note': '母公司报表数据暂不可用，使用合并报表数据代替'
            }
        if fetch_quarterly and 'consolidated_quarterly' in result and 'data' in result['consolidated_quarterly']:
            result['parent_quarterly'] = {
                'stock_code': stock_code,
                'stock_name': stock_info['name'],
                'report_type': 'parent',
                'frequency': 'quarterly',
                'years': years,
                'fetch_time': datetime.now().isoformat(),
                'data': result['consolidated_quarterly']['data'],
                'note': '母公司报表数据暂不可用，使用合并报表数据代替'
            }
            
    except Exception as e:
        logger.error(f"获取母公司资产负债表失败: {e}")
        if fetch_yearly:
            result['parent_yearly'] = {'error': str(e)}
        if fetch_quarterly:
            result['parent_quarterly'] = {'error': str(e)}
    
    # 保存所有4个 JSON 文件
    for key, data in result.items():
        output_file = output_dir / f"{stock_code}_balance_sheet_{key}.json"
        save_json(data, output_file)
        logger.info(f"已保存 {key} 资产负债表到 {output_file}")
    
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='获取资产负债表数据')
    parser.add_argument('stock_code', help='股票代码（如 600519）')
    parser.add_argument('--years', type=int, default=5, help='年数（默认: 5）')
    parser.add_argument('--frequency', choices=['yearly', 'quarterly', 'both'], default='both',
                       help='数据频率: yearly(年度), quarterly(季度), both(两者，默认)')
    parser.add_argument('--output-dir', type=Path,
                       default=None,
                       help='输出目录（默认：FINDERS_WORKSPACE/data）')
    args = parser.parse_args()
    
    get_balance_sheet(args.stock_code, args.years, args.frequency, args.output_dir)
