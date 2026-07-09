"""获取资产负债表数据（年/季度，合并+母公司）"""
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
    获取股票的资产负债表数据。
    
    Args:
        stock_code: 6位股票代码
        years: 历史数据年数
        output_dir: JSON 输出目录
    
    Returns:
        包含4个数据集的字典：consolidated_yearly, consolidated_quarterly,
        parent_yearly, parent_quarterly
    """
    if output_dir is None:
        output_dir = Path('skills/company-fundamentals/data')
    
    stock_info = validate_stock_code(stock_code)
    logger.info(f"正在获取 {stock_info['name']} ({stock_code}) 的资产负债表，{years} 年")
    
    result = {}
    
    # 获取合并资产负债表
    try:
        # 年度数据
        yearly_df = fetch_with_retry(
            ak.stock_balance_sheet_by_report_em,
            symbol=stock_code
        )
        if not yearly_df.empty:
            yearly_df = clean_financial_data(yearly_df)
            # 过滤年度数据（12月31日的报告）
            yearly_data = [r for r in yearly_df.to_dict('records') 
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
            
            # 季度数据（所有报告期）
            quarterly_data = yearly_df.head(years * 4).to_dict('records')
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
            result['consolidated_yearly'] = {'error': '无数据'}
            result['consolidated_quarterly'] = {'error': '无数据'}
            
    except Exception as e:
        logger.error(f"获取合并资产负债表失败: {e}")
        result['consolidated_yearly'] = {'error': str(e)}
        result['consolidated_quarterly'] = {'error': str(e)}
    
    # 获取母公司资产负债表（如果可用）
    try:
        # 注：akshare 可能不直接支持母公司报表，这里使用相同数据作为占位
        # 实际使用时可能需要调整 API 调用
        if 'consolidated_yearly' in result and 'data' in result['consolidated_yearly']:
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
        else:
            result['parent_yearly'] = {'error': '无数据'}
            result['parent_quarterly'] = {'error': '无数据'}
            
    except Exception as e:
        logger.error(f"获取母公司资产负债表失败: {e}")
        result['parent_yearly'] = {'error': str(e)}
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
    parser.add_argument('--output-dir', type=Path,
                       default=Path('skills/company-fundamentals/data'),
                       help='输出目录')
    args = parser.parse_args()
    
    get_balance_sheet(args.stock_code, args.years, args.output_dir)
