import pandas as pd

df = pd.read_excel('customer_combined.xlsx')
print("生成的Excel文件包含以下列:", df.columns.tolist())
print("\n数据预览:")
print(df.head(10).to_string())
print(f"\n共 {len(df)} 条记录")