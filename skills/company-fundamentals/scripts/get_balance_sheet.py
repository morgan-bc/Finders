#!/usr/bin/env python3
"""获取资产负债表数据"""

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


def get_balance_sheet(pro, ts_code, years=5):
    """获取资产负债表数据"""
    try:
        start_date, end_date = get_date_range(years)
        
        df = pro.balancesheet(
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
            fields='ts_code,ann_date,end_date,report_type,total_assets,total_liab,total_hldr_eqy_exc_min_int,money_cap,notes_receiv,accounts_receiv,inventories,fix_assets,intang_assets,goodwill,short_term_loan,long_term_loan,bonds_payable'
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
                'total_assets': safe_float(row.get('total_assets')),
                'total_liab': safe_float(row.get('total_liab')),
                'total_equity': safe_float(row.get('total_hldr_eqy_exc_min_int')),
                'money_cap': safe_float(row.get('money_cap')),
                'accounts_receiv': safe_float(row.get('accounts_receiv')),
                'inventories': safe_float(row.get('inventories')),
                'fix_assets': safe_float(row.get('fix_assets')),
                'intang_assets': safe_float(row.get('intang_assets')),
                'goodwill': safe_float(row.get('goodwill')),
                'short_term_loan': safe_float(row.get('short_term_loan')),
                'long_term_loan': safe_float(row.get('long_term_loan')),
                'bonds_payable': safe_float(row.get('bonds_payable'))
            }
            records.append(record)
        
        return records
    except Exception as e:
        print(f"获取资产负债表失败: {e}")
        return []


def main():
    parser = argparse.ArgumentParser(description='获取资产负债表数据')
    parser.add_argument('stock_code', help='股票代码（如 600519.SH 或 600519）')
    parser.add_argument('--token', help='Tushare API token')
    parser.add_argument('--years', type=int, default=5, help='历史数据年数（默认5年）')
    
    args = parser.parse_args()
    
    # 初始化 API
    pro = get_tushare_api(args.token)
    
    # 标准化股票代码
    ts_code = normalize_stock_code(args.stock_code)
    print(f"正在获取 {ts_code} 的资产负债表数据...")
    
    # 获取数据
    balance_sheet_data = get_balance_sheet(pro, ts_code, args.years)
    
    if not balance_sheet_data:
        print("未获取到资产负债表数据")
        sys.exit(1)
    
    # 保存数据
    filename = f"{ts_code.replace('.', '_')}_balance_sheet.json"
    filepath = save_json(balance_sheet_data, filename)
    
    print(f"\n数据已保存到: {filepath}")
    print(f"共获取 {len(balance_sheet_data)} 期数据")
    
    # 显示最新一期数据
    if balance_sheet_data:
        latest = balance_sheet_data[0]
        print("\n=== 最新资产负债表摘要 ===")
        print(f"报告期: {latest.get('end_date')}")
        print(f"总资产: {latest.get('total_assets') / 10000:.2f} 亿元")
        print(f"总负债: {latest.get('total_liab') / 10000:.2f} 亿元")
        print(f"净资产: {latest.get('total_equity') / 10000:.2f} 亿元")
        print(f"货币资金: {latest.get('money_cap') / 10000:.2f} 亿元")
        print(f"应收账款: {latest.get('accounts_receiv') / 10000:.2f} 亿元")
        print(f"存货: {latest.get('inventories') / 10000:.2f} 亿元")
        print(f"固定资产: {latest.get('fix_assets') / 10000:.2f} 亿元")
        print(f"短期借款: {latest.get('short_term_loan') / 10000:.2f} 亿元")
        print(f"长期借款: {latest.get('long_term_loan') / 10000:.2f} 亿元")


if __name__ == '__main__':
    main()
