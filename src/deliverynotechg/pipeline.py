import os
import shutil
import time

from .customer_excel import create_customer_excel
from .pdf_contact import (
    add_contact_to_pdf,
    extract_company_name_from_pdf,
    extract_handling_units_from_pdf,
    find_contact_in_excel,
    find_hu_info_in_excel,
    update_pdf_with_hu_info,
)


def process_pdf_files():
    excel_path = "customer_combined.xlsx"
    hu_excel_path = "EXPORT_20260604132137-hu.xlsx"

    os.makedirs("output", exist_ok=True)
    os.makedirs("archive", exist_ok=True)

    pdf_files = [f for f in os.listdir(".") if f.lower().endswith(".pdf")]

    if not pdf_files:
        print("褰撳墠鐩綍娌℃湁PDF鏂囦欢")
        return

    print(f"鎵惧埌 {len(pdf_files)} 涓狿DF鏂囦欢")

    time_suffix = time.strftime("%H%M")

    for pdf_filename in pdf_files:
        pdf_path = pdf_filename
        print(f"\n澶勭悊鏂囦欢: {pdf_path}")

        try:
            company_name = extract_company_name_from_pdf(pdf_path)
            if company_name:
                if company_name.get("chinese"):
                    print(f"浠嶱DF鎻愬彇鐨勪腑鏂囧叕鍙稿悕绉? {company_name['chinese']}")
                if company_name.get("english"):
                    print(f"浠嶱DF鎻愬彇鐨勮嫳鏂囧叕鍙稿悕绉? {company_name['english']}")
            else:
                print("鏈粠PDF鎻愬彇鍒板叕鍙稿悕绉?")

            contact_info = find_contact_in_excel(company_name, excel_path)

            handling_units = extract_handling_units_from_pdf(pdf_path)
            print(f"浠嶱DF鎻愬彇鐨勬惉杩愬崟鍏冨彿鐮? {handling_units}")

            hu_info = None
            if handling_units and os.path.exists(hu_excel_path):
                hu_info = find_hu_info_in_excel(handling_units, hu_excel_path)
                print(f"鍖归厤鍒扮殑HU淇℃伅鏁伴噺: {len(hu_info.get('hu_info_list', []))}")
                print(f"Total Weight鎬诲拰: {hu_info.get('total_weight_sum', 0.0)}")
            elif not os.path.exists(hu_excel_path):
                print(f"鏈壘鍒癏U Excel鏂囦欢: {hu_excel_path}")

            name_without_ext = os.path.splitext(pdf_filename)[0]
            output_pdf = f"output/{name_without_ext}_{time_suffix}_with_contact.pdf"
            temp_pdf = f"output/{name_without_ext}_{time_suffix}_temp.pdf"

            if contact_info:
                print(f"鎵惧埌鐨勮仈绯讳汉: {contact_info['contact']}")
                print(f"鎵惧埌鐨勭數璇? {contact_info['mobile']}")

                is_english_company = company_name and company_name.get("english") and not company_name.get("chinese")

                add_contact_to_pdf(pdf_path, temp_pdf, contact_info, is_english_company)
                print(f"宸叉垚鍔熸坊鍔犺仈绯讳俊鎭埌PDF")
            else:
                shutil.copy(pdf_path, temp_pdf)
                print("鏈壘鍒板尮閰嶇殑鑱旂郴浜轰俊鎭?")

            if hu_info:
                update_pdf_with_hu_info(temp_pdf, output_pdf, hu_info)
                os.remove(temp_pdf)
                print(f"宸叉垚鍔熸洿鏂版惉杩愬崟鍏冧俊鎭埌PDF锛屾柊鏂囦欢淇濆瓨涓? {output_pdf}")
            else:
                os.rename(temp_pdf, output_pdf)
                print(f"鏂版枃浠朵繚瀛樹负: {output_pdf}")

            archive_path = f"archive/{name_without_ext}_{time_suffix}.pdf"
            max_retries = 3
            for i in range(max_retries):
                try:
                    shutil.move(pdf_path, archive_path)
                    print(f"宸插皢鍘烶DF鏂囦欢绉诲姩鍒? {archive_path}")
                    break
                except PermissionError:
                    if i < max_retries - 1:
                        time.sleep(1)
                        print(f"鏂囦欢琚崰鐢紝閲嶈瘯涓?({i + 1}/{max_retries})...")
                    else:
                        print(f"鏃犳硶绉诲姩鏂囦欢 {pdf_path}锛屾枃浠跺彲鑳借鍏朵粬绋嬪簭鍗犵敤")
        except Exception as e:
            print(f"澶勭悊鏂囦欢 {pdf_path} 鏃跺彂鐢熼敊璇? {str(e)}")


def main():
    excel_file = "customer_combined.xlsx"

    if not os.path.exists(excel_file):
        print(f"{excel_file} 涓嶅瓨鍦紝姝ｅ湪鍒涘缓...")
        create_customer_excel()
        print(f"{excel_file} 鍒涘缓瀹屾垚")
    else:
        print(f"{excel_file} 宸插瓨鍦紝璺宠繃鍒涘缓")

    print("\n姝ｅ湪澶勭悊PDF鏂囦欢...")
    process_pdf_files()
    print("\n瀹屾垚锛?")

