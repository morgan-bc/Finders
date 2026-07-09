---
name: company-fundamentals
description: "分析A股公司基本面数据，使用 akshare（东方财富数据源）。提供综合财务分析，包括估值指标、财务报表，并生成详细报告。使用 get_fundamentals 获取概览，然后使用 get_balance_sheet/get_cashflow/get_income_statement 进行详细分析。"
compatibility: "Python 3.10+, akshare, pandas"
allowed-tools: "read_file write_file execute web_search"
---

# 公司基本面分析 Skill

## 概述

本 Skill 使用 akshare 数据源（东方财富）为 A 股公司提供全面的基本面分析。采用分层方法：
1. 首先使用 `get_fundamentals` 获取综合概览
2. 根据需要深入分析特定财务报表
3. 生成详细的分析报告

## 使用时机

- 用户要求分析公司基本面
- 用户想要分析财务健康状况、估值或业绩
- 用户需要财务报表（资产负债表、现金流量表、利润表）
- 用户请求对 A 股公司进行投资研究

## 工作流程

### 步骤 0：解析股票代码（如需要）

如果用户提供公司名称而非股票代码：
1. 使用 `web_search` 查找股票代码
   - 搜索查询：`"{公司名称} A股 股票代码"`
2. 从搜索结果中提取股票代码
3. 将股票代码传递给脚本

示例：
- 用户："分析贵州茅台的基本面"
- LLM：`web_search("贵州茅台 A股 股票代码")` → "600519"
- LLM：使用 "600519" 执行 `get_fundamentals.py`

### 步骤 1：获取综合基本面（始终从这里开始）

运行 `get_fundamentals.py` 获取概览数据：

```bash
python skills/company-fundamentals/scripts/get_fundamentals.py <股票代码>
```

提供以下信息：
- 公司概况（名称、行业、市值）
- 估值指标（PE、PEG、PB、EPS）
- 股息与风险（股息率、Beta）
- 价格区间（52周高低点、移动平均线）
- 盈利能力（收入、利润率、EBITDA）
- 回报率（ROE、ROA）
- 财务健康（负债率、流动性、自由现金流）

读取生成的 `{股票代码}_fundamentals.json` 了解公司情况。

### 步骤 2：根据需要深入分析（可选）

根据初步分析，调用特定工具获取详细数据：

**资产负债表分析：**
```bash
python skills/company-fundamentals/scripts/get_balance_sheet.py <股票代码> --years 5
```

需要分析以下情况时使用：
- 资产构成和质量
- 债务结构和到期情况
- 营运资金管理
- 财务杠杆趋势

**现金流量表分析：**
```bash
python skills/company-fundamentals/scripts/get_cashflow.py <股票代码> --years 5
```

需要分析以下情况时使用：
- 经营现金流质量
- 资本支出模式
- 自由现金流生成
- 现金流可持续性

**利润表分析：**
```bash
python skills/company-fundamentals/scripts/get_income_statement.py <股票代码> --years 5
```

需要分析以下情况时使用：
- 收入增长趋势
- 成本结构和利润率
- 利润质量和可持续性
- 每股收益趋势

### 步骤 3：生成分析报告

收集数据后，按照以下结构生成综合报告：

#### 报告结构

1. **执行摘要**
   - 关键发现和投资论点
   - 整体评估（看涨/中性/看跌）

2. **公司概览**
   - 业务描述
   - 行业地位和竞争优势
   - 近期发展

3. **估值分析**
   - 当前估值指标与历史对比
   - 与行业同行比较
   - 公允价值评估

4. **财务表现**
   - 收入和利润趋势
   - 利润率分析
   - 回报指标（ROE、ROA）

5. **财务健康**
   - 资产负债表强度
   - 债务分析
   - 流动性状况

6. **现金流量分析**
   - 经营现金流质量
   - 自由现金流生成
   - 资本配置

7. **风险与机遇**
   - 关键风险
   - 增长催化剂
   - 行业趋势

8. **结论与建议**
   - 投资论点总结
   - 可操作的洞察

9. **关键指标汇总表**
   - 组织好的 Markdown 表格，包含所有关键指标

## 数据文件位置

所有中间数据保存在 `skills/company-fundamentals/data/` 目录：
- `{股票代码}_fundamentals.json` - 综合基本面
- `{股票代码}_balance_sheet_*.json` - 资产负债表数据（4个文件）
- `{股票代码}_cashflow_*.json` - 现金流量表数据（4个文件）
- `{股票代码}_income_statement_*.json` - 利润表数据（4个文件）

## 重要说明

- 始终从 `get_fundamentals` 开始获取概览
- 仅在需要更深入分析时才深入挖掘
- 数据源是通过 akshare 获取的东方财富
- 所有数据仅适用于 A 股公司
- 默认历史周期为 5 年（可通过 --years 参数配置）
- 在调用脚本之前，使用 `web_search` 将公司名称解析为股票代码
