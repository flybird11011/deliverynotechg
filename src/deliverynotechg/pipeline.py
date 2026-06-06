import os
import shutil
import sys
import time

from .customer_excel import create_customer_excel
from .pdf_contact import (
    add_contact_to_pdf,
    extract_company_name_from_pdf,
    extract_handling_units_from_pdf,
    find_contact_in_excel,
    find_hu_info_in_excel,
    _is_english_company_pdf,
    update_pdf_with_hu_info,
)


def _configure_stdout():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def _find_export_excel_candidates(directory="."):
    candidates = []
    for filename in os.listdir(directory):
        lower_name = filename.lower()
        if lower_name.startswith("export_") and lower_name.endswith(".xlsx"):
            candidates.append(os.path.join(directory, filename))
    return sorted(candidates)


def _find_hu_info_from_exports(handling_units, export_excel_paths):
    if not handling_units:
        return None, None

    expected_units = {str(unit).strip() for unit in handling_units if str(unit).strip()}

    for excel_path in export_excel_paths:
        if not os.path.exists(excel_path):
            continue

        hu_info = find_hu_info_in_excel(handling_units, excel_path)
        matched_units = {
            str(item.get("handling_unit", "")).strip()
            for item in hu_info.get("hu_info_list", [])
            if item.get("handling_unit")
        }

        if matched_units and matched_units == expected_units:
            return hu_info, excel_path

    return None, None


def process_pdf_files():
    excel_path = "customer_combined.xlsx"
    hu_excel_paths = _find_export_excel_candidates(".")

    os.makedirs("output", exist_ok=True)
    os.makedirs("archive", exist_ok=True)

    pdf_files = [f for f in os.listdir(".") if f.lower().endswith(".pdf")]

    if not pdf_files:
        print("当前目录没有 PDF 文件")
        return

    print(f"找到 {len(pdf_files)} 个 PDF 文件")
    time_suffix = time.strftime("%H%M")

    for pdf_filename in pdf_files:
        pdf_path = pdf_filename
        print(f"\n处理文件: {pdf_path}")

        try:
            company_name = extract_company_name_from_pdf(pdf_path)
            if company_name:
                if company_name.get("chinese"):
                    print(f"从 PDF 提取的中文公司名: {company_name['chinese']}")
                if company_name.get("english"):
                    print(f"从 PDF 提取的英文公司名: {company_name['english']}")
            else:
                print("未从 PDF 提取到公司名称")

            contact_info = find_contact_in_excel(company_name, excel_path)

            handling_units = extract_handling_units_from_pdf(pdf_path)
            print(f"从 PDF 提取的搬运单元号: {handling_units}")

            hu_info = None
            if handling_units and hu_excel_paths:
                hu_info, matched_hu_excel = _find_hu_info_from_exports(handling_units, hu_excel_paths)
                if hu_info:
                    print(f"匹配成功的 HU Excel: {os.path.basename(matched_hu_excel)}")
                    print(f"匹配到的 HU 记录数: {len(hu_info.get('hu_info_list', []))}")
                    print(f"Total Weight 求和: {hu_info.get('total_weight_sum', 0.0)}")
                else:
                    print("未找到能完整匹配当前搬运单元号的 EXPORT_*.xlsx 文件")
            elif handling_units and not hu_excel_paths:
                print("未找到任何 EXPORT_*.xlsx 文件")

            name_without_ext = os.path.splitext(pdf_filename)[0]
            output_pdf = f"output/{name_without_ext}_{time_suffix}_with_contact.pdf"
            temp_pdf = f"output/{name_without_ext}_{time_suffix}_temp.pdf"

            if contact_info:
                print(f"匹配到的联系人: {contact_info['contact']}")
                print(f"匹配到的电话: {contact_info['mobile']}")

                is_english_company = _is_english_company_pdf(pdf_path, company_name)
                add_contact_to_pdf(pdf_path, temp_pdf, contact_info, is_english_company)
                print("已成功把联系人信息写入 PDF")
            else:
                shutil.copy(pdf_path, temp_pdf)
                print("未找到匹配的联系人信息，已直接复制 PDF")

            if hu_info:
                update_pdf_with_hu_info(temp_pdf, output_pdf, hu_info)
                os.remove(temp_pdf)
                print(f"已更新搬运单元和重量信息，输出文件: {output_pdf}")
            else:
                os.rename(temp_pdf, output_pdf)
                print(f"已保存新文件: {output_pdf}")

            archive_path = f"archive/{name_without_ext}_{time_suffix}.pdf"
            max_retries = 3
            for i in range(max_retries):
                try:
                    shutil.move(pdf_path, archive_path)
                    print(f"已将原 PDF 移动到: {archive_path}")
                    break
                except PermissionError:
                    if i < max_retries - 1:
                        time.sleep(1)
                        print(f"文件被占用，重试中 ({i + 1}/{max_retries})...")
                    else:
                        print(f"无法移动文件 {pdf_path}，可能被其他程序占用")
        except Exception as e:
            print(f"处理文件 {pdf_path} 时发生错误: {str(e)}")


def main():
    _configure_stdout()

    excel_file = "customer_combined.xlsx"

    if not os.path.exists(excel_file):
        print(f"{excel_file} 不存在，正在创建...")
        create_customer_excel()
        print(f"{excel_file} 创建完成")
    else:
        print(f"{excel_file} 已存在，跳过创建")

    print("\n正在处理 PDF 文件...")
    process_pdf_files()
    print("\n完成")
