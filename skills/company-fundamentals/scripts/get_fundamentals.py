"""获取公司综合基本面数据"""
import argparse
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd
import akshare as ak

sys.path.insert(0, str(Path(__file__).parent))
from utils import validate_stock_code, save_json, fetch_with_retry, clean_financial_data, setup_logger

logger = setup_logger(__name__)


def get_fundamentals(stock_code: str, output_dir: Path = None) -> dict:
    """
    获取股票的综合基本面数据。
    
    Args:
        stock_code: 6位股票代码
        output_dir: JSON 输出目录
    
    Returns:
        包含所有基本面数据的字典
    """
    if output_dir is None:
        output_dir = Path('skills/company-fundamentals/data')
    
    stock_info = validate_stock_code(stock_code)
    logger.info(f"正在获取 {stock_info['name']} ({stock_code}) 的基本面数据")
    
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
    
    # 1. 获取个股信息（总市值、行业等）
    try:
        stock_individual = fetch_with_retry(
            ak.stock_individual_info_em,
            symbol=stock_code
        )
        for _, row in stock_individual.iterrows():
            indicator = str(row['item'])
            value = row['value']
            
            if indicator == '总市值':
                result['company_profile']['market_cap'] = float(value) if value else None
            elif indicator == '行业':
                result['company_profile']['industry'] = value
            elif indicator == '市盈率(动态)':
                result['valuation']['pe_ratio_ttm'] = float(value) if value else None
            elif indicator == '市净率':
                result['valuation']['price_to_book'] = float(value) if value else None
            elif indicator == '总股本':
                result['company_profile']['total_shares'] = float(value) if value else None
            elif indicator == '流通股':
                result['company_profile']['float_shares'] = float(value) if value else None
    except Exception as e:
        logger.error(f"获取个股信息失败: {e}")
    
    # 2. 获取财务分析指标
    try:
        financial = fetch_with_retry(
            ak.stock_financial_abstract_ths,
            symbol=stock_code,
            indicator="按年度"
        )
        if not financial.empty:
            latest = financial.iloc[0]
            result['returns']['return_on_equity'] = _safe_float(latest.get('净资产收益率'))
            result['profitability']['gross_profit_margin'] = _safe_float(latest.get('销售毛利率'))
            result['profitability']['net_profit_margin'] = _safe_float(latest.get('销售净利率'))
            result['financial_health']['debt_to_equity'] = _safe_float(latest.get('资产负债率'))
    except Exception as e:
        logger.error(f"获取财务指标失败: {e}")
    
    # 3. 获取实时行情（PE、PB等）
    try:
        spot = fetch_with_retry(ak.stock_zh_a_spot_em)
        row = spot[spot['代码'] == stock_code]
        if not row.empty:
            r = row.iloc[0]
            result['valuation']['pe_ratio_ttm'] = _safe_float(r.get('市盈率-动态'))
            result['valuation']['price_to_book'] = _safe_float(r.get('市净率'))
            result['company_profile']['market_cap'] = _safe_float(r.get('总市值'))
            result['price_range']['current_price'] = _safe_float(r.get('最新价'))
            result['price_range']['week_52_high'] = _safe_float(r.get('52最高'))
            result['price_range']['week_52_low'] = _safe_float(r.get('52最低'))
            result['price_range']['day_60_average'] = _safe_float(r.get('60日涨跌幅'))
    except Exception as e:
        logger.error(f"获取实时行情失败: {e}")
    
    # 4. 获取历史价格数据计算均线
    try:
        price_data = fetch_with_retry(
            ak.stock_zh_a_hist,
            symbol=stock_code,
            period="daily",
            adjust="qfq"
        )
        if not price_data.empty:
            close = price_data['收盘'].astype(float)
            result['price_range']['day_50_average'] = round(float(close.tail(50).mean()), 2)
            result['price_range']['day_200_average'] = round(float(close.tail(200).mean()), 2)
            
            recent_252 = close.tail(252)
            result['price_range']['week_52_high'] = round(float(recent_252.max()), 2)
            result['price_range']['week_52_low'] = round(float(recent_252.min()), 2)
    except Exception as e:
        logger.error(f"获取历史价格失败: {e}")
    
    # 5. 获取利润表数据（计算利润率等）
    try:
        profit = fetch_with_retry(
            ak.stock_profit_sheet_by_report_em,
            symbol=stock_code
        )
        if not profit.empty:
            latest = profit.iloc[0]
            result['profitability']['revenue_ttm'] = _safe_float(latest.get('TOTAL_OPERATE_INCOME'))
            result['profitability']['operating_profit'] = _safe_float(latest.get('OPERATE_PROFIT'))
            result['profitability']['net_income'] = _safe_float(latest.get('NETPROFIT'))
            result['profitability']['ebitda'] = _safe_float(latest.get('TOTAL_PROFIT'))
            
            revenue = _safe_float(latest.get('TOTAL_OPERATE_INCOME'))
            net_income = _safe_float(latest.get('NETPROFIT'))
            if revenue and net_income and revenue != 0:
                result['profitability']['profit_margin'] = round(net_income / revenue * 100, 2)
    except Exception as e:
        logger.error(f"获取利润表数据失败: {e}")
    
    # 6. 获取资产负债表数据（计算流动比率等）
    try:
        balance = fetch_with_retry(
            ak.stock_balance_sheet_by_report_em,
            symbol=stock_code
        )
        if not balance.empty:
            latest = balance.iloc[0]
            result['financial_health']['total_assets'] = _safe_float(latest.get('TOTAL_ASSETS'))
            result['financial_health']['total_liabilities'] = _safe_float(latest.get('TOTAL_LIABILITIES'))
            result['financial_health']['total_equity'] = _safe_float(latest.get('TOTAL_EQUITY'))
            result['financial_health']['current_assets'] = _safe_float(latest.get('TOTAL_CURRENT_ASSETS'))
            result['financial_health']['current_liabilities'] = _safe_float(latest.get('TOTAL_CURRENT_LIABILITIES'))
            
            current_assets = _safe_float(latest.get('TOTAL_CURRENT_ASSETS'))
            current_liab = _safe_float(latest.get('TOTAL_CURRENT_LIABILITIES'))
            if current_assets and current_liab and current_liab != 0:
                result['financial_health']['current_ratio'] = round(current_assets / current_liab, 2)
            
            total_debt = _safe_float(latest.get('TOTAL_LIABILITIES'))
            total_equity = _safe_float(latest.get('TOTAL_EQUITY'))
            if total_debt and total_equity and total_equity != 0:
                result['financial_health']['debt_to_equity'] = round(total_debt / total_equity * 100, 2)
    except Exception as e:
        logger.error(f"获取资产负债表数据失败: {e}")
    
    # 7. 获取现金流量表数据（计算自由现金流）
    try:
        cashflow = fetch_with_retry(
            ak.stock_cash_flow_sheet_by_report_em,
            symbol=stock_code
        )
        if not cashflow.empty:
            latest = cashflow.iloc[0]
            result['financial_health']['operating_cash_flow'] = _safe_float(
                latest.get('NETCASH_OPERATE'))
            result['financial_health']['investing_cash_flow'] = _safe_float(
                latest.get('NETCASH_INVEST'))
            result['financial_health']['financing_cash_flow'] = _safe_float(
                latest.get('NETCASH_FINANCE'))
            
            op_cf = _safe_float(latest.get('NETCASH_OPERATE'))
            # 自由现金流 ≈ 经营现金流 - 资本支出
            if op_cf:
                result['financial_health']['free_cash_flow'] = op_cf
    except Exception as e:
        logger.error(f"获取现金流量表数据失败: {e}")
    
    # 8. 获取股息数据
    try:
        dividend = fetch_with_retry(
            ak.stock_history_dividend_detail,
            symbol=stock_code,
            indicator="分红"
        )
        if not dividend.empty:
            result['dividend_risk']['has_dividend'] = True
            result['dividend_risk']['recent_dividends'] = dividend.head(5).to_dict('records')
        else:
            result['dividend_risk']['has_dividend'] = False
    except Exception as e:
        logger.error(f"获取股息数据失败: {e}")
    
    # 保存 JSON
    output_file = output_dir / f"{stock_code}_fundamentals.json"
    save_json(result, output_file)
    logger.info(f"基本面数据已保存到 {output_file}")
    
    return result


def _safe_float(value) -> float | None:
    """安全转换为 float，处理 None 和无效值"""
    if value is None:
        return None
    try:
        v = float(value)
        return v if pd.notna(v) else None
    except (ValueError, TypeError):
        return None


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='获取公司基本面数据')
    parser.add_argument('stock_code', help='股票代码（如 600519）')
    parser.add_argument('--output-dir', type=Path,
                       default=Path('skills/company-fundamentals/data'),
                       help='输出目录')
    args = parser.parse_args()
    
    get_fundamentals(args.stock_code, args.output_dir)
