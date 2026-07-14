#!/usr/bin/env python3
"""获取利润表数据"""

import argparse
import sys

from utils import (
    get_tushare_api,
    normalize_stock_code,
    save_json,
    get_date_range,
    df_to_dict,
    safe_float
)


def get_income_statement(pro, ts_code, years=5):
    """获取利润表数据"""
    try:
        start_date, end_date = get_date_range(years)
        
        df = pro.income(
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
            fields='ts_code,ann_date,end_date,report_type,revenue,operate_profit,total_profit,n_income,n_income_attr_p,basic_eps,diluted_eps,operate_exp,total_cogs,sell_exp,manage_exp,research_exp,finance_exp,interest_exp,fee_exp'
        )
        
        if df.empty:
            return []
        
        # 转换数据
        records = []
        for _, row in df.iterrows():
            record = {
                'end_date': row.get('end_date'),
                'ann_date': row.get('ann_date'),
                'report_type': row.get('report_type'),
                'revenue': safe_float(row.get('revenue')),
                'operate_profit': safe_float(row.get('operate_profit')),
                'total_profit': safe_float(row.get('total_profit')),
                'net_income': safe_float(row.get('n_income')),
                'net_income_attr_p': safe_float(row.get('n_income_attr_p')),
                'basic_eps': safe_float(row.get('basic_eps')),
                'diluted_eps': safe_float(row.get('diluted_eps')),
                'operate_exp': safe_float(row.get('operate_exp')),
                'total_cogs': safe_float(row.get('total_cogs')),
                'sell_exp': safe_float(row.get('sell_exp')),
                'manage_exp': safe_float(row.get('manage_exp')),
                'research_exp': safe_float(row.get('research_exp')),
                'finance_exp': safe_float(row.get('finance_exp'))
            }
            records.append(record)
        
        return records
    except Exception as e:
        print(f"获取利润表失败: {e}")
        return []


def main():
    parser = argparse.ArgumentParser(description='获取利润表数据')
    parser.add_argument('stock_code', help='股票代码（如 600519.SH 或 600519）')
    parser.add_argument('--token', help='Tushare API token')
    parser.add_argument('--years', type=int, default=5, help='历史数据年数（默认5年）')
    
    args = parser.parse_args()
    
    # 初始化 API
    pro = get_tushare_api(args.token)
    
    # 标准化股票代码
    ts_code = normalize_stock_code(args.stock_code)
    print(f"正在获取 {ts_code} 的利润表数据...")
    
    # 获取数据
    income_data = get_income_statement(pro, ts_code, args.years)
    
    if not income_data:
        print("未获取到利润表数据")
        sys.exit(1)
    
    # 保存数据
    filename = f"{ts_code.replace('.', '_')}_income_statement.json"
    filepath = save_json(income_data, filename)
    
    print(f"\n数据已保存到: {filepath}")
    print(f"共获取 {len(income_data)} 期数据")
    
    # 显示最新一期数据
    if income_data:
        latest = income_data[0]
        print("\n=== 最新利润表摘要 ===")
        print(f"报告期: {latest.get('end_date')}")
        print(f"营业收入: {latest.get('revenue') / 10000:.2f} 亿元")
        print(f"营业成本: {latest.get('total_cogs') / 10000:.2f} 亿元")
        print(f"营业利润: {latest.get('operate_profit') / 10000:.2f} 亿元")
        print(f"利润总额: {latest.get('total_profit') / 10000:.2f} 亿元")
        print(f"净利润: {latest.get('net_income') / 10000:.2f} 亿元")
        print(f"归母净利润: {latest.get('net_income_attr_p') / 10000:.2f} 亿元")
        print(f"基本每股收益: {latest.get('basic_eps'):.2f} 元")
        print(f"销售费用: {latest.get('sell_exp') / 10000:.2f} 亿元")
        print(f"管理费用: {latest.get('manage_exp') / 10000:.2f} 亿元")
        print(f"研发费用: {latest.get('research_exp') / 10000:.2f} 亿元")
        print(f"财务费用: {latest.get('finance_exp') / 10000:.2f} 亿元")


if __name__ == '__main__':
    main()
