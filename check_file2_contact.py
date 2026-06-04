import pandas as pd

file3 = "PT AR001_BP_Contact_Person and Relationships V4 20260225.xlsx"

df3 = pd.read_excel(file3, sheet_name='Contact Person loading template', header=None)

print("=== 文件3 - 查看所有列的表头 ===")
for j in range(len(df3.columns)):
    val7 = df3.iloc[7, j]
    if pd.notna(val7):
        print(f"列{j}: {str(val7)[:60]}")

print("\n=== 查看行8的部分数据 ===")
for j in range(len(df3.columns)):
    val8 = df3.iloc[8, j]
    if pd.notna(val8):
        print(f"列{j}: {str(val8)[:60]}")