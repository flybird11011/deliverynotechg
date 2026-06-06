import pandas as pd


def create_customer_excel():
    file1 = "PT AR001 BP_Customer Master V5 20260226.xlsx"
    file2 = "PT International Address - Customer V4 20260225.xlsx"
    file3 = "PT AR001_BP_Contact_Person and Relationships V4 20260225.xlsx"

    df1 = pd.read_excel(file1, sheet_name="General Data")
    df2 = pd.read_excel(file2, sheet_name="Sheet1")
    df3 = pd.read_excel(file3, sheet_name="Contact Person loading template")

    customer_data = []

    for _, row in df2.iterrows():
        customer_number = str(row["Customer Number"]) if pd.notna(row["Customer Number"]) else ""
        if not customer_number:
            continue

        chinese_name = str(row["Name"]) if pd.notna(row["Name"]) else ""

        english_name = ""
        for _, row1 in df1.iterrows():
            if str(row1["CUSTOMER"]) == customer_number:
                english_name = str(row1["NAME_ORG1"]) if pd.notna(row1["NAME_ORG1"]) else ""
                break

        contact = ""
        mobile = ""
        for _, row3 in df3.iterrows():
            if str(row3["Customer Number"]) == customer_number:
                contact = str(row3["Notes Mobile Number"]) if pd.notna(row3["Notes Mobile Number"]) else ""
                mobile = str(row3["Mobile number"]) if pd.notna(row3["Mobile number"]) else ""
                if mobile.endswith(".0"):
                    mobile = mobile[:-2]
                break

        customer_data.append(
            {
                "customer_number": customer_number,
                "english_name": english_name,
                "chinese_name": chinese_name,
                "contact": contact,
                "mobile": mobile,
            }
        )

    result_df = pd.DataFrame(customer_data)
    result_df.to_excel("customer_combined.xlsx", index=False)
    print(f"已创建 customer_combined.xlsx，共 {len(result_df)} 条记录")

