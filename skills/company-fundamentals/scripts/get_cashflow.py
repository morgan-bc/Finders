#!/usr/bin/env python3
"""获取现金流量表数据"""

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


def get_cashflow(pro, ts_code, years=5):
    """获取现金流量表数据"""
    try:
        start_date, end_date = get_date_range(years)
        
        df = pro.cashflow(
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
            fields='ts_code,ann_date,end_date,report_type,n_cashflow_act,n_cashflow_inv_act,n_cash_flows_fnc_act,c_fr_sale_sg,c_pay_dist_emp,c_pay_for_invest,c_pay_for_interest,c_fr_borrow_debt,c_fr_issue_bond,c_pay_dist_div_porfit_int'
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
                'operating_cashflow': safe_float(row.get('n_cashflow_act')),
                'investing_cashflow': safe_float(row.get('n_cashflow_inv_act')),
                'financing_cashflow': safe_float(row.get('n_cash_flows_fnc_act')),
                'cash_from_sales': safe_float(row.get('c_fr_sale_sg')),
                'cash_to_employees': safe_float(row.get('c_pay_dist_emp')),
                'cash_for_invest': safe_float(row.get('c_pay_for_invest')),
                'cash_for_interest': safe_float(row.get('c_pay_for_interest')),
                'cash_from_borrow': safe_float(row.get('c_fr_borrow_debt')),
                'cash_from_bond': safe_float(row.get('c_fr_issue_bond')),
                'cash_for_dividend': safe_float(row.get('c_pay_dist_div_porfit_int'))
            }
            records.append(record)
        
        return records
    except Exception as e:
        print(f"获取现金流量表失败: {e}")
        return []


def main():
    parser = argparse.ArgumentParser(description='获取现金流量表数据')
    parser.add_argument('stock_code', help='股票代码（如 600519.SH 或 600519）')
    parser.add_argument('--token', help='Tushare API token')
    parser.add_argument('--years', type=int, default=5, help='历史数据年数（默认5年）')
    
    args = parser.parse_args()
    
    # 初始化 API
    pro = get_tushare_api(args.token)
    
    # 标准化股票代码
    ts_code = normalize_stock_code(args.stock_code)
    print(f"正在获取 {ts_code} 的现金流量表数据...")
    
    # 获取数据
    cashflow_data = get_cashflow(pro, ts_code, args.years)
    
    if not cashflow_data:
        print("未获取到现金流量表数据")
        sys.exit(1)
    
    # 保存数据
    filename = f"{ts_code.replace('.', '_')}_cashflow.json"
    filepath = save_json(cashflow_data, filename)
    
    print(f"\n数据已保存到: {filepath}")
    print(f"共获取 {len(cashflow_data)} 期数据")
    
    # 显示最新一期数据
    if cashflow_data:
        latest = cashflow_data[0]
        print("\n=== 最新现金流量表摘要 ===")
        print(f"报告期: {latest.get('end_date')}")
        print(f"经营活动现金流净额: {latest.get('operating_cashflow') / 10000:.2f} 亿元")
        print(f"投资活动现金流净额: {latest.get('investing_cashflow') / 10000:.2f} 亿元")
        print(f"筹资活动现金流净额: {latest.get('financing_cashflow') / 10000:.2f} 亿元")
        print(f"销售商品收到现金: {latest.get('cash_from_sales') / 10000:.2f} 亿元")
        print(f"支付给职工现金: {latest.get('cash_to_employees') / 10000:.2f} 亿元")
        print(f"投资支付现金: {latest.get('cash_for_invest') / 10000:.2f} 亿元")
        print(f"分配股利利润利息: {latest.get('cash_for_dividend') / 10000:.2f} 亿元")


if __name__ == '__main__':
    main()
