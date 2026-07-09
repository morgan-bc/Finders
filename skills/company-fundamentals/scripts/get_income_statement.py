"""获取利润表数据（年/季度，合并+母公司）"""
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
    获取股票的利润表数据。
    
    Args:
        stock_code: 6位股票代码
        years: 历史数据年数
        output_dir: JSON 输出目录
    
    Returns:
        包含4个数据集的字典
    """
    if output_dir is None:
        output_dir = Path('skills/company-fundamentals/data')
    
    stock_info = validate_stock_code(stock_code)
    logger.info(f"正在获取 {stock_info['name']} ({stock_code}) 的利润表，{years} 年")
    
    result = {}
    
    # 获取合并利润表
    try:
        income_df = fetch_with_retry(
            ak.stock_profit_sheet_by_report_em,
            symbol=stock_code
        )
        
        if not income_df.empty:
            income_df = clean_financial_data(income_df)
            
            # 年度数据（12月31日的报告）
            yearly_data = [r for r in income_df.to_dict('records') 
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
            quarterly_data = income_df.head(years * 4).to_dict('records')
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
        logger.error(f"获取合并利润表失败: {e}")
        result['consolidated_yearly'] = {'error': str(e)}
        result['consolidated_quarterly'] = {'error': str(e)}
    
    # 获取母公司利润表
    try:
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
        logger.error(f"获取母公司利润表失败: {e}")
        result['parent_yearly'] = {'error': str(e)}
        result['parent_quarterly'] = {'error': str(e)}
    
    # 保存所有4个 JSON 文件
    for key, data in result.items():
        output_file = output_dir / f"{stock_code}_income_statement_{key}.json"
        save_json(data, output_file)
        logger.info(f"已保存 {key} 利润表到 {output_file}")
    
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='获取利润表数据')
    parser.add_argument('stock_code', help='股票代码（如 600519）')
    parser.add_argument('--years', type=int, default=5, help='年数（默认: 5）')
    parser.add_argument('--output-dir', type=Path,
                       default=Path('skills/company-fundamentals/data'),
                       help='输出目录')
    args = parser.parse_args()
    
    get_income_statement(args.stock_code, args.years, args.output_dir)
