import pandas as pd

file1 = "PT AR001 BP_Customer Master V5 20260226.xlsx"
df1 = pd.read_excel(file1, sheet_name='General Data', header=None)

print("=== General Data 工作表结构 ===")
print(f"总行数: {len(df1)}, 总列数: {len(df1.columns)}")
print("\n=== 前20行数据 ===")
for i in range(min(20, len(df1))):
    non_nan_vals = []
    for j in range(len(df1.columns)):
        val = df1.iloc[i, j]
        if pd.notna(val):
            non_nan_vals.append(f"列{j}:{str(val)[:30]}")
    if non_nan_vals:
        print(f"行{i}: {', '.join(non_nan_vals)}")