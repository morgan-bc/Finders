#!/usr/bin/env python3
"""获取资产负债表数据（完整字段，中文保存）"""

import argparse
import sys

from utils import (
    get_tushare_api,
    normalize_stock_code,
    save_json,
    get_date_range,
    safe_float
)

# tushare 英文字段 -> 中文字段名 完整映射
FIELD_MAP = {
    'ts_code': '股票代码',
    'ann_date': '公告日期',
    'f_ann_date': '实际公告日期',
    'end_date': '报告期',
    'report_type': '报表类型',
    'comp_type': '公司类型',
    'end_type': '报告期类型',
    'total_share': '期末总股本',
    'cap_rese': '资本公积金',
    'undistr_porfit': '未分配利润',
    'surplus_rese': '盈余公积金',
    'special_rese': '专项储备',
    'money_cap': '货币资金',
    'trad_asset': '交易性金融资产',
    'notes_receiv': '应收票据',
    'accounts_receiv': '应收账款',
    'oth_receiv': '其他应收款',
    'prepayment': '预付款项',
    'div_receiv': '应收股利',
    'int_receiv': '应收利息',
    'inventories': '存货',
    'amor_exp': '待摊费用',
    'nca_within_1y': '一年内到期的非流动资产',
    'sett_rsrv': '结算备付金',
    'loanto_oth_bank_fi': '拆出资金',
    'premium_receiv': '应收保费',
    'reinsur_receiv': '应收分保账款',
    'reinsur_res_receiv': '应收分保合同准备金',
    'pur_resale_fa': '买入返售金融资产',
    'oth_cur_assets': '其他流动资产',
    'total_cur_assets': '流动资产合计',
    'fa_avail_for_sale': '可供出售金融资产',
    'htm_invest': '持有至到期投资',
    'lt_eqt_invest': '长期股权投资',
    'invest_real_estate': '投资性房地产',
    'time_deposits': '定期存款',
    'oth_assets': '其他资产',
    'lt_rec': '长期应收款',
    'fix_assets': '固定资产',
    'cip': '在建工程',
    'const_materials': '工程物资',
    'fixed_assets_disp': '固定资产清理',
    'produc_bio_assets': '生产性生物资产',
    'oil_and_gas_assets': '油气资产',
    'intan_assets': '无形资产',
    'r_and_d': '研发支出',
    'goodwill': '商誉',
    'lt_amor_exp': '长期待摊费用',
    'defer_tax_assets': '递延所得税资产',
    'decr_in_disbur': '发放贷款及垫款',
    'oth_nca': '其他非流动资产',
    'total_nca': '非流动资产合计',
    'cash_reser_cb': '现金及存放中央银行款项',
    'depos_in_oth_bfi': '存放同业和其它金融机构款项',
    'prec_metals': '贵金属',
    'deriv_assets': '衍生金融资产',
    'rr_reins_une_prem': '应收分保未到期责任准备金',
    'rr_reins_outstd_cla': '应收分保未决赔款准备金',
    'rr_reins_lins_liab': '应收分保寿险责任准备金',
    'rr_reins_lthins_liab': '应收分保长期健康险责任准备金',
    'refund_depos': '存出保证金',
    'ph_pledge_loans': '保户质押贷款',
    'refund_cap_depos': '存出资本保证金',
    'indep_acct_assets': '独立账户资产',
    'client_depos': '客户资金存款',
    'client_prov': '客户备付金',
    'transac_seat_fee': '交易席位费',
    'invest_as_receiv': '应收款项类投资',
    'total_assets': '资产总计',
    'lt_borr': '长期借款',
    'st_borr': '短期借款',
    'cb_borr': '向中央银行借款',
    'depos_ib_deposits': '吸收存款及同业存放',
    'loan_oth_bank': '拆入资金',
    'trading_fl': '交易性金融负债',
    'notes_payable': '应付票据',
    'acct_payable': '应付账款',
    'adv_receipts': '预收款项',
    'sold_for_repur_fa': '卖出回购金融资产款',
    'comm_payable': '应付手续费及佣金',
    'payroll_payable': '应付职工薪酬',
    'taxes_payable': '应交税费',
    'int_payable': '应付利息',
    'div_payable': '应付股利',
    'oth_payable': '其他应付款',
    'acc_exp': '预提费用',
    'deferred_inc': '递延收益',
    'st_bonds_payable': '应付短期债券',
    'payable_to_reinsurer': '应付分保账款',
    'rsrv_reins_une_prem': '未到期责任准备金',
    'rsrv_reins_outstd_cla': '未决赔款准备金',
    'rsrv_reins_lins_liab': '寿险责任准备金',
    'rsrv_reins_lthins_liab': '长期健康险责任准备金',
    'insur_reserv': '保险责任准备金',
    'poly_reserve': '保户红利准备金',
    'policymoney': '保户储金',
    'invest_payable': '应付款项类投资',
    'total_cur_liab': '流动负债合计',
    'lt_payable': '长期应付款',
    'spec_payable': '专项应付款',
    'est_liab': '预计负债',
    'defer_tax_liab': '递延所得税负债',
    'defer_inc_non_cur_liab': '递延收益-非流动负债',
    'oth_ncl': '其他非流动负债',
    'total_ncl': '非流动负债合计',
    'total_liab': '负债合计',
    'paidin_cap': '实收资本(或股本)',
    'withdrawn_surplus': '减:库存股',
    'undist_porfit_parent': '未分配利润(母公司)',
    'minority_int': '少数股东权益',
    'total_hldr_eqy_exc_min_int': '股东权益合计(不含少数股东权益)',
    'total_hldr_eqy_inc_min_int': '股东权益合计(含少数股东权益)',
    'total_liab_hldr_eqy': '负债和股东权益总计',
}


def get_balance_sheet(pro, ts_code, years=5):
    """获取资产负债表完整数据"""
    try:
        start_date, end_date = get_date_range(years)

        df = pro.balancesheet(
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date
        )

        if df.empty:
            return []

        # 将英文列名重命名为中文
        df = df.rename(columns=FIELD_MAP)

        # 转换为字典列表，安全处理数值
        records = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                val = row[col]
                if col in ('股票代码', '公告日期', '实际公告日期', '报告期', '报表类型', '公司类型', '报告期类型'):
                    record[col] = str(val) if val is not None else None
                else:
                    record[col] = safe_float(val)
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
        print(f"报告期: {latest.get('报告期')}")
        total_assets = latest.get('资产总计') or 0
        total_liab = latest.get('负债合计') or 0
        total_equity = latest.get('股东权益合计(不含少数股东权益)') or 0
        print(f"资产总计: {total_assets / 10000:.2f} 亿元")
        print(f"负债合计: {total_liab / 10000:.2f} 亿元")
        print(f"股东权益(不含少数): {total_equity / 10000:.2f} 亿元")
        print(f"货币资金: {(latest.get('货币资金') or 0) / 10000:.2f} 亿元")
        print(f"应收账款: {(latest.get('应收账款') or 0) / 10000:.2f} 亿元")
        print(f"存货: {(latest.get('存货') or 0) / 10000:.2f} 亿元")
        print(f"固定资产: {(latest.get('固定资产') or 0) / 10000:.2f} 亿元")
        print(f"短期借款: {(latest.get('短期借款') or 0) / 10000:.2f} 亿元")
        print(f"长期借款: {(latest.get('长期借款') or 0) / 10000:.2f} 亿元")


if __name__ == '__main__':
    main()
