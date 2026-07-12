import tushare as ts

pro = ts.pro_api("1dfe1bf3595200492579865423ab7b108babe0fde0c4ae95af208fff")

df = pro.cashflow(ts_code='002460.SZ', start_date='20230101', end_date='20251231')
print(df)
df.to_csv("workdir/cashflow.csv", index=False)
