#!/usr/bin/env python3
"""获取公司综合基本面数据"""

import argparse
import sys
from datetime import datetime

from utils import (
    get_tushare_api,
    normalize_stock_code,
    save_json,
    get_date_range,
    safe_float,
    format_number
)


def get_stock_basic(pro, ts_code):
    """获取股票基本信息"""
    try:
        df = pro.stock_basic(ts_code=ts_code, fields='ts_code,name,industry,market,list_date')
        if df.empty:
            return None
        return df.iloc[0].to_dict()
    except Exception as e:
        print(f"获取股票基本信息失败: {e}")
        return None


def get_daily_basic(pro, ts_code):
    """获取每日基本面指标（PE、PB、市值等）"""
    try:
        # 获取最新交易日的数据
        df = pro.daily_basic(ts_code=ts_code, fields='ts_code,trade_date,pe,pe_ttm,pb,ps,ps_ttm,dv_ratio,dv_tts,total_mv,circ_mv')
        if df.empty:
            return None
        
        # 取最新一条记录
        latest = df.iloc[0].to_dict()
        return {
            'pe': safe_float(latest.get('pe')),
            'pe_ttm': safe_float(latest.get('pe_ttm')),
            'pb': safe_float(latest.get('pb')),
            'ps': safe_float(latest.get('ps')),
            'ps_ttm': safe_float(latest.get('ps_ttm')),
            'dv_ratio': safe_float(latest.get('dv_ratio')),  # 股息率
            'total_mv': safe_float(latest.get('total_mv')),  # 总市值（万元）
            'circ_mv': safe_float(latest.get('circ_mv')),    # 流通市值（万元）
            'trade_date': latest.get('trade_date')
        }
    except Exception as e:
        print(f"获取每日指标失败: {e}")
        return None


def get_financial_indicators(pro, ts_code, years=5):
    """获取财务指标数据"""
    try:
        start_date, end_date = get_date_range(years)
        
        # 获取财务指标
        df = pro.fina_indicator(
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
            fields='ts_code,ann_date,end_date,eps,dt_eps,bps,roe,roa,gross_profit_margin,net_profit_margin,debt_to_assets,current_ratio,quick_ratio,op_yoy,dt_netprofit_yoy,or_yoy'
        )
        
        if df.empty:
            return None
        
        # 取最新一期数据
        latest = df.iloc[0].to_dict()
        return {
            'eps': safe_float(latest.get('eps')),
            'bps': safe_float(latest.get('bps')),
            'roe': safe_float(latest.get('roe')),
            'roa': safe_float(latest.get('roa')),
            'gross_profit_margin': safe_float(latest.get('gross_profit_margin')),
            'net_profit_margin': safe_float(latest.get('net_profit_margin')),
            'debt_to_assets': safe_float(latest.get('debt_to_assets')),
            'current_ratio': safe_float(latest.get('current_ratio')),
            'quick_ratio': safe_float(latest.get('quick_ratio')),
            'op_yoy': safe_float(latest.get('op_yoy')),  # 营业收入同比增长
            'dt_netprofit_yoy': safe_float(latest.get('dt_netprofit_yoy')),  # 净利润同比增长
            'or_yoy': safe_float(latest.get('or_yoy')),  # 营业收入同比增长
            'end_date': latest.get('end_date')
        }
    except Exception as e:
        print(f"获取财务指标失败: {e}")
        return None


def get_income_summary(pro, ts_code, years=5):
    """获取利润表摘要"""
    try:
        start_date, end_date = get_date_range(years)
        
        df = pro.income(
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
            fields='ts_code,ann_date,end_date,revenue,operate_profit,total_profit,n_income,n_income_attr_p'
        )
        
        if df.empty:
            return None
        
        # 取最新一期数据
        latest = df.iloc[0].to_dict()
        return {
            'revenue': safe_float(latest.get('revenue')),
            'operate_profit': safe_float(latest.get('operate_profit')),
            'total_profit': safe_float(latest.get('total_profit')),
            'net_income': safe_float(latest.get('n_income')),
            'net_income_attr_p': safe_float(latest.get('n_income_attr_p')),
            'end_date': latest.get('end_date')
        }
    except Exception as e:
        print(f"获取利润表摘要失败: {e}")
        return None


def get_balance_sheet_summary(pro, ts_code, years=5):
    """获取资产负债表摘要"""
    try:
        start_date, end_date = get_date_range(years)
        
        df = pro.balancesheet(
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
            fields='ts_code,ann_date,end_date,total_assets,total_liab,total_hldr_eqy_exc_min_int'
        )
        
        if df.empty:
            return None
        
        # 取最新一期数据
        latest = df.iloc[0].to_dict()
        return {
            'total_assets': safe_float(latest.get('total_assets')),
            'total_liab': safe_float(latest.get('total_liab')),
            'total_equity': safe_float(latest.get('total_hldr_eqy_exc_min_int')),
            'end_date': latest.get('end_date')
        }
    except Exception as e:
        print(f"获取资产负债表摘要失败: {e}")
        return None


def get_cashflow_summary(pro, ts_code, years=5):
    """获取现金流量表摘要"""
    try:
        start_date, end_date = get_date_range(years)
        
        df = pro.cashflow(
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
            fields='ts_code,ann_date,end_date,n_cashflow_act,n_cashflow_inv_act,n_cash_flows_fnc_act'
        )
        
        if df.empty:
            return None
        
        # 取最新一期数据
        latest = df.iloc[0].to_dict()
        return {
            'operating_cashflow': safe_float(latest.get('n_cashflow_act')),
            'investing_cashflow': safe_float(latest.get('n_cashflow_inv_act')),
            'financing_cashflow': safe_float(latest.get('n_cash_flows_fnc_act')),
            'end_date': latest.get('end_date')
        }
    except Exception as e:
        print(f"获取现金流量表摘要失败: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description='获取公司综合基本面数据')
    parser.add_argument('stock_code', help='股票代码（如 600519.SH 或 600519）')
    parser.add_argument('--token', help='Tushare API token')
    parser.add_argument('--years', type=int, default=5, help='历史数据年数（默认5年）')
    
    args = parser.parse_args()
    
    # 初始化 API
    pro = get_tushare_api(args.token)
    
    # 标准化股票代码
    ts_code = normalize_stock_code(args.stock_code)
    print(f"正在获取 {ts_code} 的基本面数据...")
    
    # 获取各项数据
    print("获取股票基本信息...")
    basic_info = get_stock_basic(pro, ts_code)
    if not basic_info:
        print("无法获取股票基本信息，请检查股票代码是否正确")
        sys.exit(1)
    
    print("获取每日指标...")
    daily_basic = get_daily_basic(pro, ts_code)
    
    print("获取财务指标...")
    financial_indicators = get_financial_indicators(pro, ts_code, args.years)
    
    print("获取利润表摘要...")
    income_summary = get_income_summary(pro, ts_code, args.years)
    
    print("获取资产负债表摘要...")
    balance_summary = get_balance_sheet_summary(pro, ts_code, args.years)
    
    print("获取现金流量表摘要...")
    cashflow_summary = get_cashflow_summary(pro, ts_code, args.years)
    
    # 整合数据
    fundamentals = {
        'stock_code': ts_code,
        'update_time': datetime.now().isoformat(),
        'basic_info': basic_info,
        'valuation': daily_basic,
        'financial_indicators': financial_indicators,
        'income_summary': income_summary,
        'balance_summary': balance_summary,
        'cashflow_summary': cashflow_summary
    }
    
    # 保存数据
    filename = f"{ts_code.replace('.', '_')}_fundamentals.json"
    filepath = save_json(fundamentals, filename)
    
    print(f"\n数据已保存到: {filepath}")
    print("\n=== 基本面概览 ===")
    print(f"公司名称: {basic_info.get('name')}")
    print(f"所属行业: {basic_info.get('industry')}")
    
    if daily_basic:
        print(f"\n估值指标:")
        print(f"  PE (TTM): {format_number(daily_basic.get('pe_ttm'))}")
        print(f"  PB: {format_number(daily_basic.get('pb'))}")
        print(f"  股息率: {format_number(daily_basic.get('dv_ratio'))}%")
        print(f"  总市值: {format_number(daily_basic.get('total_mv') / 10000)}亿元")
    
    if financial_indicators:
        print(f"\n盈利能力:")
        print(f"  ROE: {format_number(financial_indicators.get('roe'))}%")
        print(f"  ROA: {format_number(financial_indicators.get('roa'))}%")
        print(f"  毛利率: {format_number(financial_indicators.get('gross_profit_margin'))}%")
        print(f"  净利率: {format_number(financial_indicators.get('net_profit_margin'))}%")
        print(f"\n成长能力:")
        print(f"  营收同比增长: {format_number(financial_indicators.get('or_yoy'))}%")
        print(f"  净利润同比增长: {format_number(financial_indicators.get('dt_netprofit_yoy'))}%")
    
    if balance_summary:
        print(f"\n财务健康:")
        print(f"  总资产: {format_number(balance_summary.get('total_assets') / 10000)}亿元")
        print(f"  总负债: {format_number(balance_summary.get('total_liab') / 10000)}亿元")
        print(f"  净资产: {format_number(balance_summary.get('total_equity') / 10000)}亿元")
    
    if cashflow_summary:
        print(f"\n现金流量:")
        print(f"  经营现金流: {format_number(cashflow_summary.get('operating_cashflow') / 10000)}亿元")
        print(f"  投资现金流: {format_number(cashflow_summary.get('investing_cashflow') / 10000)}亿元")
        print(f"  筹资现金流: {format_number(cashflow_summary.get('financing_cashflow') / 10000)}亿元")


if __name__ == '__main__':
    main()
