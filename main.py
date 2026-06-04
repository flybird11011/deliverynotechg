import os
import subprocess

def main():
    excel_file = "customer_combined.xlsx"
    
    if not os.path.exists(excel_file):
        print(f"{excel_file} 不存在，正在创建...")
        subprocess.run(["python", "create_customer_excel.py"], check=True)
        print(f"{excel_file} 创建完成")
    else:
        print(f"{excel_file} 已存在，跳过创建")
    
    print("\n正在运行 find_and_add_contact.py...")
    subprocess.run(["python", "find_and_add_contact.py"], check=True)
    print("完成！")

if __name__ == "__main__":
    main()