---
name: data-analyzer
description: "Analyze financial data and generate structured reports with optional data visualizations. Supports conversational data analysis, report drafting, and iterative chart generation with VLM critique."
compatibility: "Python 3.12+, matplotlib, seaborn"
allowed-tools: "web_search web_fetch read_file write_file execute task_tool"
---

# Data Analyzer Skill

## Overview
Financial data analysis skill based on FinSight's DataAnalyzer architecture. Guides the agent through a structured three-phase workflow:
1. **Data Analysis & Research** — Collect and analyze financial data from web and local sources
2. **Report Drafting** — Generate structured, data-driven reports
3. **Chart Generation (Optional)** — Create publication-quality visualizations with iterative refinement

## When to Use
- User asks for financial data analysis
- User requests investment research reports
- User needs data-driven financial insights with visualizations
- User wants to explore trends in financial metrics, stock performance, or economic indicators

## Phase 1: Data Collection & Analysis

### 1.1 Identify Analysis Scope
- Clarify the user's question and break it into sub-questions
- Determine what data is needed: stock prices, financial statements, macro indicators, sector comparisons, etc.

### 1.2 Collect Data
Use the appropriate tools to gather financial data:
- **`web_search`** — Find relevant financial data, news, and source URLs
- **`web_fetch`** — Read specific financial pages (e.g., Yahoo Finance, SEC filings, company investor relations pages)
- **`read_file` / `list_dir` / `grep`** — Access local financial data files (CSV, JSON, Excel)
- **`execute`** — Run Python code for data processing, transformation, and analysis

### 1.3 Process & Analyze
- Format collected data systematically before analysis
- Use Python (pandas, numpy) for data cleaning, aggregation, and computation
- Break down complex analysis tasks into smaller sub-questions
- Always validate data quality and note any missing or inconsistent values

## Phase 2: Report Drafting

### 2.1 Structure the Report
Generate structured reports in JSON format:
```json
{
  "title": "Report Title",
  "content": "Full report content in markdown"
}
```

### 2.2 Report Sections
The report should include:
- **Executive Summary** — Key takeaways and overall assessment
- **Detailed Analysis** — In-depth examination of the data with supporting evidence
- **Key Findings** — Bullet-point summary of important insights
- **Conclusions** — Final recommendations or observations

### 2.3 Chart Placeholders
- Use standard markdown image syntax `![chart description](images/chart_name.png)` where charts should appear
- Example: `![Revenue Trend](images/revenue_trend.png)`
- Support multiple target languages (Chinese/English) based on user preference

### 2.4 Source Citation
- Always cite data sources with URLs
- Be explicit about data limitations, time ranges, and assumptions
- Maintain data integrity — **never fabricate financial data**

## Phase 3: Chart Generation (Optional)

### 3.1 Parse Chart Requirements
- Identify all markdown image references from the drafted report
- For each chart, determine: chart type, data to visualize, title, and axes

### 3.2 Iterative Code → Execute → Critique Cycle
For each chart, follow this iterative process (up to 3 iterations):

1. **Generate Python Code** — Write matplotlib/seaborn code to create the chart
2. **Execute Code** — Use the `execute` tool to run the code, saving the chart to `images/`
3. **Critique & Refine** — Review the output for:
   - Correct data representation
   - Readable labels and legends
   - Appropriate chart type for the data
   - Professional appearance

### 3.3 Code Requirements
- Ensure `plt.savefig('filename.png')` is included in every chart script
- Chart filenames should be **descriptive and short** (e.g., `revenue_trend.png`, `pe_comparison.png`)
- Save all charts to the `images/` directory
- Use the following custom color palette:
  ```python
  palette = ["#8B0000", "#FF2A2A", "#FF6A4D", "#FFDAB9", "#FFF5E6", "#FFE4B5", "#A0522D", "#5C2E1F"]
  ```

### 3.4 Chart Descriptions
- Generate a description/caption for each chart (< 100 words)
- Descriptions should explain what the chart shows and highlight key takeaways

## Key Guidelines

| Guideline | Detail |
|-----------|--------|
| **Cite Sources** | Always include source URLs for all data used |
| **Data Limitations** | Be explicit about data gaps, time range constraints, and methodology limitations |
| **Chart Code** | Always include `plt.savefig('filename.png')` before `plt.show()` |
| **Filenames** | Keep chart filenames descriptive but short; use underscores for spaces |
| **Data Integrity** | Never fabricate or manipulate financial data to support a narrative |
| **Reproducibility** | Code should be self-contained and reproducible |

## Output Format

The final deliverable is a markdown report with:

```markdown
# [Report Title]

## Executive Summary
[Key takeaways...]

## Analysis

[Detailed analysis with data points and insights...]

![Chart Title](images/chart_name.png)

*Chart description (< 100 words)*

## Key Findings
- Finding 1
- Finding 2
- ...

## Conclusions
[Summary and recommendations...]

---
*Sources: [Source 1 URL], [Source 2 URL], ...*
*Data as of: [Date]*
```

- Charts embedded via markdown image syntax `![...](images/...)` with actual image paths
- Each chart is accompanied by a brief description/caption
- Inline citations `[1]`, `[2]` reference the sources section at the bottom
