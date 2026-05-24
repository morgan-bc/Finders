---
name: dcf-valuation
description: Performs discounted cash flow (DCF) valuation analysis to estimate intrinsic value per share.
---

# DCF Valuation Skill

## Step 1: Gather Financial Data
Call get_financials for cash flow history and key metrics.

## Step 2: Calculate FCF Growth Rate
Calculate 5-year FCF CAGR from historical data.

## Step 3: Estimate Discount Rate (WACC)
Use sector-appropriate WACC range.

## Step 4: Project Future Cash Flows
Apply growth rate with decay for Years 1-5 + Terminal value.

## Step 5: Calculate Present Value
Discount all FCFs to get Enterprise Value.
