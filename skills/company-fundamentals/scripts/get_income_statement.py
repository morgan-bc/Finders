#!/usr/bin/env python3
"""获取利润表数据（完整字段，中文保存）"""

import argparse
import sys

from utils import (
    get_tushare_api,
    normalize_stock_code,
    save_json,
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
    'basic_eps': '基本每股收益',
    'diluted_eps': '稀释每股收益',
    'total_revenue': '营业总收入',
    'revenue': '营业收入',
    'int_income': '利息收入',
    'prem_earned': '已赚保费',
    'comm_income': '手续费及佣金收入',
    'n_commis_income': '手续费及佣金净收入',
    'n_oth_income': '其他经营净收益',
    'n_oth_b_income': '其他业务净收益',
    'prem_income': '保险业务收入',
    'out_prem': '分出保费',
    'une_prem_reser': '提取未到期责任准备金',
    'reins_income': '分保费收入',
    'n_sec_tb_income': '代理买卖证券业务净收入',
    'n_sec_uw_income': '证券承销业务净收入',
    'n_asset_mg_income': '受托客户资产管理业务净收入',
    'oth_b_income': '其他业务收入',
    'fv_value_chg_gain': '公允价值变动净收益',
    'invest_income': '投资净收益',
    'ass_invest_income': '对联营企业和合营企业的投资收益',
    'forex_gain': '汇兑净收益',
    'total_cogs': '营业总成本',
    'oper_cost': '营业成本',
    'int_exp': '利息支出',
    'comm_exp': '手续费及佣金支出',
    'biz_tax_surchg': '营业税金及附加',
    'sell_exp': '销售费用',
    'admin_exp': '管理费用',
    'fin_exp': '财务费用',
    'assets_impair_loss': '资产减值损失',
    'prem_refund': '退保金',
    'compens_payout': '赔付总支出',
    'reser_insur_liab': '提取保险责任准备金',
    'div_payt': '保户红利支出',
    'reins_exp': '分保费用',
    'oper_exp': '营业支出',
    'compens_payout_refu': '摊回赔付支出',
    'insur_reser_refu': '摊回保险责任准备金',
    'reins_cost_refund': '摊回分保费用',
    'other_bus_cost': '其他业务成本',
    'operate_profit': '营业利润',
    'non_oper_income': '营业外收入',
    'non_oper_exp': '营业外支出',
    'nca_disploss': '非流动资产处置净损失',
    'total_profit': '利润总额',
    'income_tax': '所得税费用',
    'n_income': '净利润(含少数股东损益)',
    'n_income_attr_p': '净利润(不含少数股东损益)',
    'minority_gain': '少数股东损益',
    'oth_compr_income': '其他综合收益',
    't_compr_income': '综合收益总额',
    'compr_inc_attr_p': '归属于母公司(或股东)的综合收益总额',
    'compr_inc_attr_m_s': '归属于少数股东的综合收益总额',
    'ebit': '息税前利润',
    'ebitda': '息税折旧摊销前利润',
    'insurance_exp': '保险业务支出',
    'undist_profit': '年初未分配利润',
    'distable_profit': '可分配利润',
    'rd_exp': '研发费用',
    'fin_exp_int_exp': '财务费用:利息费用',
    'fin_exp_int_inc': '财务费用:利息收入',
    'transfer_surplus_rese': '盈余公积转入',
    'transfer_housing_imprest': '住房周转金转入',
    'transfer_oth': '其他转入',
    'adj_lossgain': '调整以前年度损益',
    'withdra_legal_surplus': '提取法定盈余公积',
    'withdra_legal_pubwelfare': '提取法定公益金',
    'withdra_reserve_fund': '提取储备基金',
    'withdra_enterprise_expansion': '提取企业发展基金',
    'withdra_loss_reserve': '提取损失准备',
    'withdra_others': '提取其他',
    'dividend_payable': '应付优先股股利',
    'common_dividend': '应付普通股股利',
    'dividend_paid_to_shares': '转作股本的普通股股利',
    'undist_profit_parent': '未分配利润(母公司)',
}


def get_income_statement(pro, ts_code, start_date, end_date):
    """获取利润表完整数据"""
    try:
        df = pro.income(
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
        print(f"获取利润表失败: {e}")
        return []


def main():
    parser = argparse.ArgumentParser(description='获取利润表数据')
    parser.add_argument('stock_code', help='股票代码（如 600519.SH 或 600519）')
    parser.add_argument('--start_date', required=True, help='开始日期（YYYYMMDD格式）')
    parser.add_argument('--end_date', required=True, help='结束日期（YYYYMMDD格式）')

    args = parser.parse_args()

    # 初始化 API
    pro = get_tushare_api()

    # 标准化股票代码
    ts_code = normalize_stock_code(args.stock_code)
    print(f"正在获取 {ts_code} 的利润表数据...")

    # 获取数据
    income_data = get_income_statement(pro, ts_code, args.start_date, args.end_date)

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
        print(f"报告期: {latest.get('报告期')}")
        revenue = latest.get('营业收入') or 0
        oper_cost = latest.get('营业成本') or 0
        operate_profit = latest.get('营业利润') or 0
        total_profit = latest.get('利润总额') or 0
        n_income = latest.get('净利润(不含少数股东损益)') or 0
        print(f"营业收入: {revenue / 100000000:.2f} 亿元")
        print(f"营业成本: {oper_cost / 100000000:.2f} 亿元")
        print(f"营业利润: {operate_profit / 100000000:.2f} 亿元")
        print(f"利润总额: {total_profit / 100000000:.2f} 亿元")
        print(f"净利润(不含少数): {n_income / 100000000:.2f} 亿元")
        print(f"基本每股收益: {latest.get('基本每股收益') or 0:.2f} 元")
        print(f"销售费用: {(latest.get('销售费用') or 0) / 100000000:.2f} 亿元")
        print(f"管理费用: {(latest.get('管理费用') or 0) / 100000000:.2f} 亿元")
        print(f"研发费用: {(latest.get('研发费用') or 0) / 100000000:.2f} 亿元")
        print(f"财务费用: {(latest.get('财务费用') or 0) / 100000000:.2f} 亿元")


if __name__ == '__main__':
    main()
