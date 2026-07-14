#!/usr/bin/env python3
"""获取现金流量表数据（完整字段，中文保存）"""

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
    'comp_type': '公司类型',
    'report_type': '报表类型',
    'end_type': '报告期类型',
    'net_profit': '净利润',
    'finan_exp': '财务费用',
    'c_fr_sale_sg': '销售商品提供劳务收到的现金',
    'recp_tax_rends': '收到的税费返还',
    'n_depos_incr_fi': '客户存款和同业存放款项净增加额',
    'n_incr_loans_cb': '向中央银行借款净增加额',
    'n_inc_borr_oth_fi': '向其他金融机构拆入资金净增加额',
    'prem_fr_orig_contr': '收到原保险合同保费取得的现金',
    'n_incr_insured_dep': '保户储金净增加额',
    'n_reinsur_prem': '收到再保业务现金净额',
    'n_incr_disp_tfa': '处置交易性金融资产净增加额',
    'ifc_cash_incr': '收取利息和手续费净增加额',
    'n_incr_disp_faas': '处置可供出售金融资产净增加额',
    'n_incr_loans_oth_bank': '拆入资金净增加额',
    'n_cap_incr_repur': '回购业务资金净增加额',
    'c_fr_oth_operate_a': '收到其他与经营活动有关的现金',
    'c_inf_fr_operate_a': '经营活动现金流入小计',
    'c_paid_goods_s': '购买商品接受劳务支付的现金',
    'c_paid_to_for_empl': '支付给职工以及为职工支付的现金',
    'c_paid_for_taxes': '支付的各项税费',
    'n_incr_clt_loan_adv': '客户贷款及垫款净增加额',
    'n_incr_dep_cbob': '存放央行和同业款项净增加额',
    'c_pay_claims_orig_inco': '支付原保险合同赔付款项的现金',
    'pay_handling_chrg': '支付手续费的现金',
    'pay_comm_insur_plcy': '支付保单红利的现金',
    'oth_cash_pay_oper_act': '支付其他与经营活动有关的现金',
    'st_cash_out_act': '经营活动现金流出小计',
    'n_cashflow_act': '经营活动产生的现金流量净额',
    'oth_recp_ral_inv_act': '收到其他与投资活动有关的现金',
    'c_disp_withdrwl_invest': '收回投资收到的现金',
    'c_recp_return_invest': '取得投资收益收到的现金',
    'n_recp_disp_fiolta': '处置固定资产无形资产和其他长期资产收回的现金净额',
    'n_recp_disp_sobu': '处置子公司及其他营业单位收到的现金净额',
    'stot_inflows_inv_act': '投资活动现金流入小计',
    'c_pay_acq_const_fiolta': '购建固定资产无形资产和其他长期资产支付的现金',
    'c_paid_invest': '投资支付的现金',
    'n_disp_subs_oth_biz': '取得子公司及其他营业单位支付的现金净额',
    'oth_pay_ral_inv_act': '支付其他与投资活动有关的现金',
    'n_incr_pledge_loan': '质押贷款净增加额',
    'stot_out_inv_act': '投资活动现金流出小计',
    'n_cashflow_inv_act': '投资活动产生的现金流量净额',
    'c_recp_borrow': '取得借款收到的现金',
    'proc_issue_bonds': '发行债券收到的现金',
    'oth_cash_recp_ral_fnc_act': '收到其他与筹资活动有关的现金',
    'stot_cash_in_fnc_act': '筹资活动现金流入小计',
    'free_cashflow': '企业自由现金流量',
    'c_prepay_amt_borr': '偿还债务支付的现金',
    'c_pay_dist_dpcp_int_exp': '分配股利利润或偿付利息支付的现金',
    'incl_dvd_profit_paid_sc_ms': '子公司支付给少数股东的股利利润',
    'oth_cashpay_ral_fnc_act': '支付其他与筹资活动有关的现金',
    'stot_cashout_fnc_act': '筹资活动现金流出小计',
    'n_cash_flows_fnc_act': '筹资活动产生的现金流量净额',
    'eff_fx_flu_cash': '汇率变动对现金的影响',
    'n_incr_cash_cash_equ': '现金及现金等价物净增加额',
    'c_cash_equ_beg_period': '期初现金及现金等价物余额',
    'c_cash_equ_end_period': '期末现金及现金等价物余额',
    'c_recp_cap_contrib': '吸收投资收到的现金',
    'incl_cash_recv_sca': '其中:子公司吸收少数股东投资收到的现金',
    'unconfirmed_invest_loss': '未确认投资损失',
    'plus:dep_restr_cash': '加:受到限制的存款',
    'plus:cap_rese': '加:资本公积',
    'plus:surplus_rese': '加:盈余公积',
    'plus:undist_profit': '加:未分配利润',
    'less:withdra_legal_surplus': '减:提取法定盈余公积',
    'less:withdra_legal_pubwelfare': '减:提取法定公益金',
    'less:withdra_reserve_fund': '减:提取储备基金',
    'less:withdra_enterprise_expansion': '减:提取企业发展基金',
    'less:withdra_loss_reserve': '减:提取损失准备',
    'less:withdra_others': '减:提取其他',
    'less:dividend_payable': '减:应付优先股股利',
    'less:common_dividend': '减:应付普通股股利',
    'less:dividend_paid_to_shares': '减:转作股本的普通股股利',
}


def get_cashflow(pro, ts_code, years=5):
    """获取现金流量表完整数据"""
    try:
        start_date, end_date = get_date_range(years)

        df = pro.cashflow(
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
                if col in ('股票代码', '公告日期', '实际公告日期', '报告期', '公司类型', '报表类型', '报告期类型'):
                    record[col] = str(val) if val is not None else None
                else:
                    record[col] = safe_float(val)
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
        print(f"报告期: {latest.get('报告期')}")
        print(f"经营活动产生的现金流量净额: {(latest.get('经营活动产生的现金流量净额') or 0) / 10000:.2f} 亿元")
        print(f"投资活动产生的现金流量净额: {(latest.get('投资活动产生的现金流量净额') or 0) / 10000:.2f} 亿元")
        print(f"筹资活动产生的现金流量净额: {(latest.get('筹资活动产生的现金流量净额') or 0) / 10000:.2f} 亿元")
        print(f"销售商品提供劳务收到的现金: {(latest.get('销售商品提供劳务收到的现金') or 0) / 10000:.2f} 亿元")
        print(f"支付给职工以及为职工支付的现金: {(latest.get('支付给职工以及为职工支付的现金') or 0) / 10000:.2f} 亿元")
        print(f"购建固定资产无形资产和其他长期资产支付的现金: {(latest.get('购建固定资产无形资产和其他长期资产支付的现金') or 0) / 10000:.2f} 亿元")
        print(f"分配股利利润或偿付利息支付的现金: {(latest.get('分配股利利润或偿付利息支付的现金') or 0) / 10000:.2f} 亿元")


if __name__ == '__main__':
    main()
