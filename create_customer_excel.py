import pandas as pd

file1 = "PT AR001 BP_Customer Master V5 20260226.xlsx"
file2 = "PT International Address - Customer V4 20260225.xlsx"
file3 = "PT AR001_BP_Contact_Person and Relationships V4 20260225.xlsx"

df1 = pd.read_excel(file1, sheet_name='General Data', header=None)
df2 = pd.read_excel(file2, sheet_name='International Address Versions', header=None)
df3 = pd.read_excel(file3, sheet_name='Contact Person loading template', header=None)

header_row_2 = 4
data_start_row_2 = 8

customer_data = []
for i in range(data_start_row_2, len(df2)):
    kunr = str(df2.iloc[i, 0])
    if kunr.strip() == 'nan' or kunr.strip() == '':
        continue
    
    chinese_name = str(df2.iloc[i, 3]) if pd.notna(df2.iloc[i, 3]) else ''
    customer_data.append({
        'customer_number': kunr,
        'chinese_name': chinese_name
    })

data_start_row_3 = 8

contact_dict = {}
for i in range(data_start_row_3, len(df3)):
    kunr = str(df3.iloc[i, 0])
    if kunr.strip() == 'nan' or kunr.strip() == '':
        continue
    
    notes_mobile = str(df3.iloc[i, 24]) if pd.notna(df3.iloc[i, 24]) else ''
    mobile = str(df3.iloc[i, 23]) if pd.notna(df3.iloc[i, 23]) else ''
    
    if kunr not in contact_dict:
        contact_dict[kunr] = {'contact': notes_mobile, 'mobile': mobile}

data_start_row_1 = 8

english_name_dict = {}
for i in range(data_start_row_1, len(df1)):
    kunr = str(df1.iloc[i, 0])
    if kunr.strip() == 'nan' or kunr.strip() == '':
        continue
    
    english_name = str(df1.iloc[i, 3]) if pd.notna(df1.iloc[i, 3]) else ''
    english_name_dict[kunr] = english_name

final_data = []
for customer in customer_data:
    kunr = customer['customer_number']
    final_data.append({
        'customer_number': kunr,
        'english_name': english_name_dict.get(kunr, ''),
        'chinese_name': customer['chinese_name'],
        'contact': contact_dict.get(kunr, {}).get('contact', ''),
        'mobile': contact_dict.get(kunr, {}).get('mobile', '')
    })

result_df = pd.DataFrame(final_data)
result_df.to_excel('customer_combined.xlsx', index=False)
print("已创建 customer_combined.xlsx")